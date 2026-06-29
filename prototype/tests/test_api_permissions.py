"""Tests for the IsProjectMember DRF permission class."""

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from guardian.shortcuts import assign_perm

from prototype.api_permissions import IsProjectMember
from prototype.models import Project


class _Obj:
    """Minimal stub for permission target objects."""


def _make_request(user):
    r = RequestFactory().get("/")
    r.user = user
    return r


class IsProjectMemberTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="perm_admin", password="pw"
        )
        cls.user = User.objects.create_user(
            username="perm_user", password="pw"
        )
        cls.other = User.objects.create_user(
            username="perm_other", password="pw"
        )
        cls.project = Project.objects.create(
            title="Perm Project", label="PP01", status="ACTIVE"
        )

    def setUp(self):
        assign_perm("prototype.view_project", self.user, self.project)
        self.perm = IsProjectMember()

    # --- has_permission ---

    def test_authenticated_user_passes(self):
        self.assertTrue(
            self.perm.has_permission(_make_request(self.user), None)
        )

    def test_unauthenticated_user_denied(self):
        from unittest.mock import MagicMock

        anon = MagicMock()
        anon.is_authenticated = False
        r = RequestFactory().get("/")
        r.user = anon
        self.assertFalse(self.perm.has_permission(r, None))

    # --- has_object_permission: superuser ---

    def test_superuser_always_allowed(self):
        self.assertTrue(
            self.perm.has_object_permission(
                _make_request(self.superuser), None, _Obj()
            )
        )

    # --- has_object_permission: direct project FK ---

    def test_user_with_perm_on_direct_project(self):
        obj = _Obj()
        obj.project = self.project
        self.assertTrue(
            self.perm.has_object_permission(
                _make_request(self.user), None, obj
            )
        )

    def test_user_without_perm_on_direct_project(self):
        obj = _Obj()
        obj.project = self.project
        self.assertFalse(
            self.perm.has_object_permission(
                _make_request(self.other), None, obj
            )
        )

    # --- has_object_permission: nested location.project ---

    def test_user_with_perm_via_location_project(self):
        location = _Obj()
        location.project = self.project
        obj = _Obj()
        obj.location = location
        self.assertTrue(
            self.perm.has_object_permission(
                _make_request(self.user), None, obj
            )
        )

    # --- has_object_permission: no project ---

    def test_literature_object_allowed_without_project(self):
        obj = _Obj()
        obj.data_source = "literature"
        self.assertTrue(
            self.perm.has_object_permission(
                _make_request(self.user), None, obj
            )
        )

    def test_non_literature_object_without_project_denied(self):
        obj = _Obj()
        obj.data_source = "internal"
        self.assertFalse(
            self.perm.has_object_permission(
                _make_request(self.user), None, obj
            )
        )

    def test_object_with_no_attributes_denied(self):
        self.assertFalse(
            self.perm.has_object_permission(
                _make_request(self.user), None, _Obj()
            )
        )
