"""Tests for CurrentUserMiddleware and get_current_user."""

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

import prototype.middleware as _mw
from prototype.middleware import CurrentUserMiddleware, get_current_user


class CurrentUserMiddlewareTest(TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_middleware_stores_user(self):
        request = self.rf.get("/")
        request.user = AnonymousUser()
        sentinel = object()
        mw = CurrentUserMiddleware(get_response=lambda r: sentinel)
        result = mw(request)
        self.assertIs(result, sentinel)
        self.assertEqual(get_current_user(), request.user)

    def test_get_current_user_returns_none_without_request(self):
        if hasattr(_mw._user, "value"):
            del _mw._user.value
        self.assertIsNone(get_current_user())
