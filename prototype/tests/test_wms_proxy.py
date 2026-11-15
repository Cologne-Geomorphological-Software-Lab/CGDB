"""Tests for prototype.views.wms_proxy's hostname/scheme whitelist."""

from __future__ import annotations

from http.client import HTTPMessage
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


def _upstream(body: bytes, content_type: str) -> MagicMock:
    """A stand-in for the upstream WMS response (a context manager)."""
    response = MagicMock()
    response.read.side_effect = lambda size=-1: body if size < 0 else body[:size]
    response.headers = {"Content-Type": content_type}
    response.__enter__.return_value = response
    return response


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

    @patch("prototype.views._WMS_OPENER.open")
    def test_valid_https_whitelisted_url_is_proxied(
        self, mock_open: MagicMock
    ) -> None:
        mock_open.return_value = _upstream(b"<xml>ok</xml>", "text/xml")

        resp = self._proxy()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"<xml>ok</xml>")
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        mock_open.assert_called_once()

    @patch("prototype.views._WMS_OPENER.open")
    def test_gml_with_charset_is_proxied(self, mock_open: MagicMock) -> None:
        mock_open.return_value = _upstream(
            b"<gml/>", "application/vnd.ogc.gml; charset=UTF-8"
        )
        resp = self._proxy()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp["Content-Type"], "application/vnd.ogc.gml; charset=UTF-8"
        )

    @patch("prototype.views._WMS_OPENER.open")
    def test_html_response_is_not_passed_through(
        self, mock_open: MagicMock
    ) -> None:
        """An HTML answer would run in this site's origin if passed through."""
        mock_open.return_value = _upstream(b"<script>x</script>", "text/html")
        self.assertEqual(self._proxy().status_code, 502)

    @patch("prototype.views._WMS_OPENER.open")
    def test_oversized_response_is_rejected(self, mock_open: MagicMock) -> None:
        from prototype.views import _WMS_MAX_BYTES

        mock_open.return_value = _upstream(
            b"x" * (_WMS_MAX_BYTES + 1), "text/xml"
        )
        self.assertEqual(self._proxy().status_code, 502)

    @patch("prototype.views._WMS_OPENER.open")
    def test_redirect_answer_gives_502(self, mock_open: MagicMock) -> None:
        import urllib.error

        mock_open.side_effect = urllib.error.HTTPError(
            "https://services.bgr.de/wms", 302, "Found", HTTPMessage(), BytesIO()
        )
        self.assertEqual(self._proxy().status_code, 502)

    def test_opener_does_not_follow_redirects(self) -> None:
        """A whitelisted host must not be able to send the proxy elsewhere."""
        import urllib.request

        from prototype.views import _WMS_OPENER

        # OpenerDirector.handlers is real but missing from the type stubs.
        handlers = getattr(_WMS_OPENER, "handlers")  # noqa: B009
        handler = next(
            h
            for h in handlers
            if isinstance(h, urllib.request.HTTPRedirectHandler)
        )
        request = urllib.request.Request("https://services.bgr.de/wms")
        self.assertIsNone(
            handler.redirect_request(
                request,
                BytesIO(),
                302,
                "Found",
                HTTPMessage(),
                "http://127.0.0.1/admin",
            )
        )

    def _proxy(self):
        return self.client.get(
            self.url,
            {"url": "https://services.bgr.de/wms?REQUEST=GetFeatureInfo"},
        )

    def test_missing_url_param_returns_403(self) -> None:
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)
