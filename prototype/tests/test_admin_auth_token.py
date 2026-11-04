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

from rest_framework.authtoken.models import Token, TokenProxy

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


class AuthTokenAdminObjectLookupTests(TestCase):
    """TokenProxy.pk is the user id, while the concrete Token is keyed on
    `key`. The admin's URLs and object lookup have to agree on the user id."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="tok_super3", password="pw", email="ts3@test.com"
        )
        cls.staff_user = User.objects.create_user(
            username="tok_staff3", password="pw", email="tst3@test.com",
            is_staff=True,
        )
        # A user id that differs from the superuser's, so that a lookup using
        # the wrong user can't pass by accident.
        cls.owner = User.objects.create_user(
            username="tok_owner", password="pw", email="to@test.com"
        )
        cls.token = Token.objects.create(user=cls.owner)

    def _url(self, name: str, *args: object) -> str:
        return reverse(f"admin:authtoken_tokenproxy_{name}", args=args)

    def test_changelist_links_use_user_id_not_key(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self._url("changelist"))
        self.assertContains(response, self._url("change", self.owner.pk))
        self.assertNotContains(response, self._url("change", self.token.key))

    def test_change_view_opens_by_user_id(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self._url("change", self.owner.pk))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self._url("delete", self.owner.pk))

    def test_key_is_not_accepted_in_url(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self._url("change", self.token.key))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("admin:index"))

    def test_delete_confirmation_names_the_token(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self._url("delete", self.owner.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["object"].pk, self.owner.pk)

    def test_delete_view_removes_token(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            self._url("delete", self.owner.pk), {"post": "yes"}
        )
        self.assertRedirects(
            response, self._url("changelist"), fetch_redirect_response=False
        )
        self.assertFalse(Token.objects.filter(user=self.owner).exists())

    def test_deleted_token_no_longer_authenticates(self):
        headers = {"Authorization": f"Token {self.token.key}"}
        url = reverse("api_v1:project-list")
        self.assertEqual(self.client.get(url, headers=headers).status_code, 200)

        self.client.force_login(self.superuser)
        self.client.post(self._url("delete", self.owner.pk), {"post": "yes"})
        self.client.logout()

        # DRF derives the status from the first authentication class. With
        # SessionAuthentication first, that's 403 rather than 401, so the
        # detail is what shows the token itself was rejected.
        response = self.client.get(url, headers=headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Invalid token.")

    def test_delete_keeps_the_user_and_other_tokens(self):
        other = Token.objects.create(user=self.staff_user)
        self.client.force_login(self.superuser)
        self.client.post(self._url("delete", self.owner.pk), {"post": "yes"})
        self.assertTrue(User.objects.filter(pk=self.owner.pk).exists())
        self.assertTrue(Token.objects.filter(pk=other.pk).exists())

    def test_no_bulk_actions_offered(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self._url("changelist"))
        self.assertNotContains(response, 'name="action"')

    def test_staff_user_cannot_delete(self):
        from django.contrib.auth.models import Permission

        self.staff_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="authtoken",
                codename="delete_tokenproxy",
            )
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            self._url("delete", self.owner.pk), {"post": "yes"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Token.objects.filter(user=self.owner).exists())
