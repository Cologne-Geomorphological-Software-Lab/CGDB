"""Tests for DRF throttling (architecture-review fix F7).

The login endpoint (ThrottledObtainAuthToken, prototype/api_views.py) gets
its own "login" throttle scope, deliberately much tighter than the general
"anon"/"user" rates in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] -- meant to
slow down credential-stuffing against that one endpoint specifically.

The rate is overridden down to something small and fast via
unittest.mock.patch.object on ScopedRateThrottle.THROTTLE_RATES directly,
not @override_settings(REST_FRAMEWORK=...): DRF's SimpleRateThrottle sets
`THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES` as a plain class
attribute at module-import time (rest_framework/throttling.py:66). DRF's
setting_changed signal handler reloads api_settings' own lazy attributes,
but never re-assigns that already-copied class attribute -- so once
anything else in the test session has imported rest_framework.throttling
(near-guaranteed before this file's tests run), @override_settings silently
stops affecting the rate actually enforced. Patching the class attribute
directly sidesteps that entirely.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

# DRF's THROTTLE_RATES is set from api_settings at import time with no type
# annotation basedpyright can see (unstubbed library) — it's always a dict at
# runtime.
_PRODUCTION_RATES = cast("dict[str, str]", ScopedRateThrottle.THROTTLE_RATES)
_FAST_LOGIN_RATE = {**_PRODUCTION_RATES, "login": "2/min"}


@patch.object(ScopedRateThrottle, "THROTTLE_RATES", _FAST_LOGIN_RATE)
class LoginThrottleTest(TestCase):
    def setUp(self) -> None:
        # Throttle counters are cache-backed (LocMemCache) and persist
        # across tests within one process -- start each test from zero.
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="throttle_user", password="correct-horse-battery"
        )
        self.url = reverse("api_token_auth")

    def tearDown(self) -> None:
        cache.clear()

    def _login_attempt(self, password: str = "wrong-password"):
        return self.client.post(
            self.url,
            {"username": "throttle_user", "password": password},
            format="json",
        )

    def test_requests_within_rate_are_not_throttled(self) -> None:
        for _ in range(2):  # rate is 2/min
            resp = self._login_attempt()
            assert resp.status_code != 429

    def test_requests_over_rate_return_429(self) -> None:
        for _ in range(2):
            self._login_attempt()
        resp = self._login_attempt()
        assert resp.status_code == 429

    def test_throttle_applies_regardless_of_credential_validity(self) -> None:
        """The whole point is slowing down credential-stuffing -- the limit
        must trip on repeated attempts even with a valid password, not just
        on failed ones."""
        for _ in range(2):
            self._login_attempt(password="correct-horse-battery")
        resp = self._login_attempt(password="correct-horse-battery")
        assert resp.status_code == 429

    def test_successful_login_within_rate_returns_token(self) -> None:
        resp = self._login_attempt(password="correct-horse-battery")
        assert resp.status_code == 200
        assert "token" in resp.json()


class LoginThrottleProductionRateTest(TestCase):
    """Confirms the real, unpatched production rate ("login": "10/hour")
    is what's actually wired up -- the class above only proves the
    throttling *mechanism* works, using a patched rate for speed."""

    def test_production_login_rate_is_ten_per_hour(self) -> None:
        from prototype.api_views import ThrottledObtainAuthToken

        assert ThrottledObtainAuthToken.throttle_scope == "login"
        rates = cast("dict[str, str]", ScopedRateThrottle.THROTTLE_RATES)
        assert rates["login"] == "10/hour"
