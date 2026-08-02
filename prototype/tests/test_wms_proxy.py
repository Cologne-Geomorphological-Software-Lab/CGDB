"""Tests for prototype.views.wms_proxy's hostname/scheme whitelist."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class WmsProxyTest(TestCase):
    def setUp(self) -> None:
        # The view is wrapped in staff_member_required.
        self.user = User.objects.create_user(
            username="wms_user", password="pw", is_staff=True
        )
        self.client = Client()
        self.client.login(username="wms_user", password="pw")
        self.url = reverse("wms_proxy")

    def test_non_whitelisted_host_returns_403(self) -> None:
        resp = self.client.get(self.url, {"url": "https://evil.example.com/wms"})
        self.assertEqual(resp.status_code, 403)

    def test_lookalike_host_returns_403(self) -> None:
        """A prefix match without a dot boundary must not sneak past the whitelist."""
        resp = self.client.get(
            self.url, {"url": "https://evilservices.bgr.de/wms"}
        )
        self.assertEqual(resp.status_code, 403)

    def test_userinfo_host_confusion_returns_403(self) -> None:
        """urlparse().hostname must resolve the real host, not the userinfo part."""
        resp = self.client.get(
            self.url, {"url": "https://services.bgr.de@evil.example.com/wms"}
        )
        self.assertEqual(resp.status_code, 403)

    def test_disallowed_scheme_on_whitelisted_host_returns_403(self) -> None:
        """A whitelisted hostname alone isn't enough — the scheme must be http(s) too."""
        resp = self.client.get(self.url, {"url": "ftp://services.bgr.de/wms"})
        self.assertEqual(resp.status_code, 403)

    def test_file_scheme_on_whitelisted_host_returns_403(self) -> None:
        resp = self.client.get(
            self.url, {"url": "file://services.bgr.de/etc/passwd"}
        )
        self.assertEqual(resp.status_code, 403)

    @patch("urllib.request.urlopen")
    def test_valid_https_whitelisted_url_is_proxied(
        self, mock_urlopen: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b"<xml>ok</xml>"
        mock_response.headers = {"Content-Type": "text/xml"}
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        resp = self.client.get(
            self.url,
            {"url": "https://services.bgr.de/wms?REQUEST=GetFeatureInfo"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"<xml>ok</xml>")
        mock_urlopen.assert_called_once()

    def test_missing_url_param_returns_403(self) -> None:
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)
