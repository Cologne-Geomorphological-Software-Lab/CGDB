"""Tests for ReferenceAdmin's object-level permission checks (tech debt LBG17).

has_delete_permission used to fall back to Django's default (a blanket
model-level check) while has_change_permission was already object-scoped -
a user granted only the blanket delete_reference permission could delete
any Reference row, not just ones they can change.
"""

from __future__ import annotations

from django.contrib import admin as django_admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from guardian.shortcuts import assign_perm

from bibliography.admin import ReferenceAdmin
from bibliography.models import Author, Reference


def _make_request(user: object):
    request = RequestFactory().get("/")
    request.user = user
    return request


class ReferenceAdminDeletePermissionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(first_name="A", last_name="Uthor")
        cls.reference = Reference.objects.create(
            title="Löss und Paläoböden",
            year=2020,
            lead_author=cls.author,
            abstract="Ein Abstract.",
            type="Paper",
        )
        cls.scoped_user = User.objects.create_user(
            username="lbg17_scoped", password="pw"
        )
        cls.unscoped_user = User.objects.create_user(
            username="lbg17_unscoped", password="pw"
        )
        cls.superuser = User.objects.create_superuser(
            "lbg17_super", "s@test.com", "pw"
        )

    def setUp(self):
        self.admin_instance = ReferenceAdmin(Reference, django_admin.site)

    def test_delete_denied_without_object_permission(self):
        request = _make_request(self.unscoped_user)
        self.assertFalse(
            self.admin_instance.has_delete_permission(
                request, obj=self.reference
            )
        )

    def test_delete_granted_with_object_permission(self):
        assign_perm(
            "bibliography.delete_reference", self.scoped_user, self.reference
        )
        request = _make_request(self.scoped_user)
        self.assertTrue(
            self.admin_instance.has_delete_permission(
                request, obj=self.reference
            )
        )

    def test_delete_permission_on_one_reference_does_not_grant_another(self):
        """The exact gap this fix closes: a per-object grant must not act
        like a blanket model-level permission."""
        other_reference = Reference.objects.create(
            title="Andere Arbeit",
            year=2021,
            lead_author=self.author,
            abstract="x",
            type="Paper",
        )
        assign_perm(
            "bibliography.delete_reference", self.scoped_user, self.reference
        )
        request = _make_request(self.scoped_user)
        self.assertFalse(
            self.admin_instance.has_delete_permission(
                request, obj=other_reference
            )
        )

    def test_delete_no_obj_returns_true(self):
        """obj=None (changelist-level access check) is unaffected."""
        request = _make_request(self.unscoped_user)
        self.assertTrue(
            self.admin_instance.has_delete_permission(request, obj=None)
        )

    def test_delete_superuser_always_true(self):
        request = _make_request(self.superuser)
        self.assertTrue(
            self.admin_instance.has_delete_permission(
                request, obj=self.reference
            )
        )
