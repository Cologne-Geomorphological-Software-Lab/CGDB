"""Tests for AuthTokenAdmin's permission lockdown.

Architecture-review fix (F4): AuthTokenAdmin displays every user's plaintext
bearer token in the changelist and previously had no explicit has_*_permission
overrides -- relying only on the sidebar hiding it from non-superusers, which
is UI-only. Without these overrides, any staff user granted view/change
permission on TokenProxy (e.g. accidentally, via Django's standard per-app
user permissions widget) would get full API-impersonation access to every
user's token. These tests confirm the lockdown mirrors the pattern already
used by MaintenanceRunAdmin/DuckDBTableConfigAdmin (orchestration/admin.py).
"""

from typing import TYPE_CHECKING, cast

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from rest_framework.authtoken.models import TokenProxy

from prototype.admin import AuthTokenAdmin

if TYPE_CHECKING:
    from prototype.mixins import AuthenticatedHttpRequest


class AuthTokenAdminPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="tok_super", password="pw", email="ts@test.com"
        )
        # Staff (not superuser) -- the realistic threat model from F4.
        cls.staff_user = User.objects.create_user(
            username="tok_staff", password="pw", email="tst@test.com",
            is_staff=True,
        )

    def setUp(self):
        self.site = AdminSite()
        self.admin = AuthTokenAdmin(TokenProxy, self.site)
        self.factory = RequestFactory()

    def _request(self, user: User) -> "AuthenticatedHttpRequest":
        request = self.factory.get("/")
        request.user = user
        return cast("AuthenticatedHttpRequest", request)

    def test_superuser_has_module_perms(self):
        self.assertTrue(self.admin.has_module_perms(self._request(self.superuser)))

    def test_staff_user_denied_module_perms(self):
        self.assertFalse(self.admin.has_module_perms(self._request(self.staff_user)))

    def test_superuser_has_view_permission(self):
        self.assertTrue(self.admin.has_view_permission(self._request(self.superuser)))

    def test_staff_user_denied_view_permission(self):
        self.assertFalse(self.admin.has_view_permission(self._request(self.staff_user)))

    def test_superuser_has_add_permission(self):
        self.assertTrue(self.admin.has_add_permission(self._request(self.superuser)))

    def test_staff_user_denied_add_permission(self):
        self.assertFalse(self.admin.has_add_permission(self._request(self.staff_user)))

    def test_superuser_has_change_permission(self):
        self.assertTrue(self.admin.has_change_permission(self._request(self.superuser)))

    def test_staff_user_denied_change_permission(self):
        self.assertFalse(
            self.admin.has_change_permission(self._request(self.staff_user))
        )

    def test_superuser_has_delete_permission(self):
        self.assertTrue(self.admin.has_delete_permission(self._request(self.superuser)))

    def test_staff_user_denied_delete_permission(self):
        self.assertFalse(
            self.admin.has_delete_permission(self._request(self.staff_user))
        )


class AuthTokenAdminChangelistAccessTests(TestCase):
    """Integration tests: even a staff user granted the Django-level
    'view_tokenproxy' permission (the exact accidental-grant scenario F4
    describes) must still be denied by the admin's own has_view_permission,
    not just the sidebar."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="tok_super2", password="pw", email="ts2@test.com"
        )
        cls.staff_user = User.objects.create_user(
            username="tok_staff2", password="pw", email="tst2@test.com",
            is_staff=True,
        )

    def _grant_view_tokenproxy(self, user: User) -> None:
        from django.contrib.auth.models import Permission

        perm = Permission.objects.get(
            content_type__app_label="authtoken", codename="view_tokenproxy"
        )
        user.user_permissions.add(perm)

    def test_superuser_can_access_authtoken_changelist(self):
        self.client.force_login(self.superuser)
        url = reverse("admin:authtoken_tokenproxy_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_staff_user_with_django_permission_still_denied(self):
        """A staff user is already past admin_view's login gate, so a denied
        has_view_permission surfaces as changelist_view's own
        PermissionDenied, which Django's exception middleware converts to a
        403 response (unlike the anonymous/non-staff case, which never
        reaches the view at all and gets a 302-to-login instead)."""
        self._grant_view_tokenproxy(self.staff_user)
        self.client.force_login(self.staff_user)
        url = reverse("admin:authtoken_tokenproxy_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_staff_user_without_permission_denied(self):
        self.client.force_login(self.staff_user)
        url = reverse("admin:authtoken_tokenproxy_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
