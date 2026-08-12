"""Tests for the IsProjectMember and ProjectPathPermission DRF permission classes."""

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from guardian.shortcuts import assign_perm

from field_data.models import Location
from prototype.api_permissions import (
    CountingScopedPermission,
    IsProjectMember,
    MeasurementScopedPermission,
    ProjectPathPermission,
    SampleScopedPermission,
    _is_literature_object,
)
from prototype.models import Project


class _Obj:
    """Minimal stub for permission target objects."""


def _make_request(user):
    r = RequestFactory().get("/")
    r.user = user
    return r


class IsLiteratureObjectTest(TestCase):
    """Architecture-review fix (F22): _is_literature_object() replaced the
    old getattr(obj, "data_source", None) == "literature" fallback with an
    explicit allowlist (_LITERATURE_ELIGIBLE_MODELS), so an object merely
    *presenting* a matching data_source attribute isn't enough on its own —
    it must also be a model the exception is actually meant to cover."""

    def test_location_with_literature_data_source_is_eligible(self):
        loc = Location(data_source="literature")
        self.assertTrue(_is_literature_object(loc))

    def test_location_with_internal_data_source_is_not_eligible(self):
        loc = Location(data_source="internal")
        self.assertFalse(_is_literature_object(loc))

    def test_non_location_object_is_never_eligible_even_if_it_looks_like_one(self):
        obj = _Obj()
        obj.data_source = "literature"
        self.assertFalse(_is_literature_object(obj))

    def test_object_with_no_data_source_attribute_is_not_eligible(self):
        self.assertFalse(_is_literature_object(_Obj()))


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

    def test_literature_location_allowed_without_project(self):
        """A real Location (the only model on the literature allowlist —
        see F22) with no project is still allowed, matching the pre-fix
        behavior for the one model this exception actually exists for."""
        obj = Location(data_source="literature")
        self.assertTrue(
            self.perm.has_object_permission(
                _make_request(self.user), None, obj
            )
        )

    def test_non_location_literature_lookalike_without_project_denied(self):
        """Architecture-review fix (F22) regression: before the explicit
        allowlist, any object with no resolvable project fell through to
        getattr(obj, "data_source", None) == "literature" — which any
        object presenting that attribute could satisfy, whether or not it
        was actually a model this exception was meant to cover. Must now
        be denied since _Obj isn't Location."""
        obj = _Obj()
        obj.data_source = "literature"
        self.assertFalse(
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


class ProjectPathPermissionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="path_admin", password="pw"
        )
        cls.user = User.objects.create_user(username="path_user", password="pw")
        cls.other = User.objects.create_user(
            username="path_other", password="pw"
        )
        cls.project = Project.objects.create(
            title="Path Project", label="PTP01", status="ACTIVE"
        )

    def setUp(self):
        assign_perm("prototype.view_project", self.user, self.project)

    # --- has_permission ---

    def test_authenticated_user_passes(self):
        perm = ProjectPathPermission()
        self.assertTrue(perm.has_permission(_make_request(self.user), None))

    def test_unauthenticated_user_denied(self):
        from unittest.mock import MagicMock

        anon = MagicMock()
        anon.is_authenticated = False
        r = RequestFactory().get("/")
        r.user = anon
        perm = ProjectPathPermission()
        self.assertFalse(perm.has_permission(r, None))

    # --- SampleScopedPermission: single-hop path.sample.project ---

    def test_sample_scoped_allows_member(self):
        sample = _Obj()
        sample.project = self.project
        obj = _Obj()
        obj.sample = sample
        perm = SampleScopedPermission()
        self.assertTrue(
            perm.has_object_permission(_make_request(self.user), None, obj)
        )

    def test_sample_scoped_denies_non_member(self):
        sample = _Obj()
        sample.project = self.project
        obj = _Obj()
        obj.sample = sample
        perm = SampleScopedPermission()
        self.assertFalse(
            perm.has_object_permission(_make_request(self.other), None, obj)
        )

    # --- CountingScopedPermission: two-hop path.counting.sample.project ---

    def test_counting_scoped_allows_member(self):
        sample = _Obj()
        sample.project = self.project
        counting = _Obj()
        counting.sample = sample
        obj = _Obj()
        obj.counting = counting
        perm = CountingScopedPermission()
        self.assertTrue(
            perm.has_object_permission(_make_request(self.user), None, obj)
        )

    def test_counting_scoped_denies_non_member(self):
        sample = _Obj()
        sample.project = self.project
        counting = _Obj()
        counting.sample = sample
        obj = _Obj()
        obj.counting = counting
        perm = CountingScopedPermission()
        self.assertFalse(
            perm.has_object_permission(_make_request(self.other), None, obj)
        )

    # --- MeasurementScopedPermission: two-hop path.measurement.sample.project ---

    def test_measurement_scoped_allows_member(self):
        sample = _Obj()
        sample.project = self.project
        measurement = _Obj()
        measurement.sample = sample
        obj = _Obj()
        obj.measurement = measurement
        perm = MeasurementScopedPermission()
        self.assertTrue(
            perm.has_object_permission(_make_request(self.user), None, obj)
        )

    # --- superuser / missing project / broken chain ---

    def test_superuser_always_allowed(self):
        perm = SampleScopedPermission()
        self.assertTrue(
            perm.has_object_permission(
                _make_request(self.superuser), None, _Obj()
            )
        )

    def test_broken_chain_non_location_literature_lookalike_denied(self):
        """Architecture-review fix (F22) regression: same as
        IsProjectMemberTest's — a broken traversal chain landing on an
        object that merely presents data_source="literature" must be
        denied unless that object is actually Location."""
        obj = _Obj()
        obj.data_source = "literature"
        perm = SampleScopedPermission()
        self.assertFalse(
            perm.has_object_permission(_make_request(self.user), None, obj)
        )

    def test_broken_chain_non_literature_denied(self):
        obj = _Obj()
        obj.data_source = "internal"
        perm = SampleScopedPermission()
        self.assertFalse(
            perm.has_object_permission(_make_request(self.user), None, obj)
        )
