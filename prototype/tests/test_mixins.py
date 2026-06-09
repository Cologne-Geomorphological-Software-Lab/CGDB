"""Tests for prototype permission mixins.

Each mixin is exercised via a concrete ModelAdmin subclass instantiated
with a real AdminSite so that self.opts is correctly populated.

Tested mixins:
- CreatedUpdatedModelAdminMixin
- ProjectBasedPermissionMixin
- NestedProjectPermissionMixin
- HybridProjectPermissionMixin
- GuardianPermissionMixin
"""
from unittest.mock import MagicMock

from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from guardian.shortcuts import assign_perm

from field_data.models import Location, Sample
from prototype.mixins import (
    CreatedUpdatedModelAdminMixin,
    GuardianPermissionMixin,
    HybridProjectPermissionMixin,
    NestedProjectPermissionMixin,
    ProjectBasedPermissionMixin,
)
from prototype.models import Project


# ---------------------------------------------------------------------------
# Concrete admin classes for testing
# ---------------------------------------------------------------------------

class _LocationProjectAdmin(ProjectBasedPermissionMixin, ModelAdmin):
    """Tests ProjectBasedPermissionMixin on Location (which has a direct project FK)."""


class _SampleAdmin(HybridProjectPermissionMixin, ModelAdmin):
    pass


class _LocationAdmin(NestedProjectPermissionMixin, ModelAdmin):
    project_path = "project"


class _GuardianAdmin(GuardianPermissionMixin, ModelAdmin):
    pass


class _CreatedUpdatedAdmin(CreatedUpdatedModelAdminMixin, ModelAdmin):
    pass


def _make_request(user):
    rf = RequestFactory()
    request = rf.get("/")
    request.user = user
    return request


# ===========================================================================
# Shared fixture
# ===========================================================================


class _MixinSetup(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="mixin_admin", password="pw"
        )
        cls.regular_user = User.objects.create_user(
            username="mixin_regular", password="pw"
        )
        cls.other_user = User.objects.create_user(
            username="mixin_other", password="pw"
        )
        cls.project = Project.objects.create(
            title="Mixin Test Project", label="MXP01", status="ACTIVE"
        )
        cls.project2 = Project.objects.create(
            title="Mixin Test Project 2", label="MXP02", status="ACTIVE"
        )
        cls.loc1 = Location.objects.create(
            identifier="MXP_LOC1", data_source="internal", project=cls.project
        )
        cls.loc2 = Location.objects.create(
            identifier="MXP_LOC2", data_source="internal", project=cls.project2
        )

    def setUp(self):
        # Assign guardian permission fresh for each test (not in setUpTestData
        # because guardian permissions interact with transactions).
        assign_perm("prototype.view_project", self.regular_user, self.project)
        assign_perm("prototype.change_project", self.regular_user, self.project)
        assign_perm("prototype.delete_project", self.regular_user, self.project)

        self.site = AdminSite()
        self.project_admin = _LocationProjectAdmin(Location, self.site)
        self.guardian_admin = _GuardianAdmin(Project, self.site)
        self.sample_admin = _SampleAdmin(Sample, self.site)


# ===========================================================================
# CreatedUpdatedModelAdminMixin
# ===========================================================================


class CreatedUpdatedMixinTest(_MixinSetup):

    def _make_admin(self):
        return _CreatedUpdatedAdmin(Project, self.site)

    def test_save_new_object_sets_created_by(self):
        admin_obj = self._make_admin()
        request = _make_request(self.regular_user)
        obj = Project(title="New", label="NEW01", status="ACTIVE")
        # obj.pk is None → new object
        admin_obj.save_model(request, obj, form=None, change=False)
        self.assertEqual(obj.created_by, self.regular_user)

    def test_save_new_object_sets_updated_by(self):
        admin_obj = self._make_admin()
        request = _make_request(self.regular_user)
        obj = Project(title="New2", label="NEW02", status="ACTIVE")
        admin_obj.save_model(request, obj, form=None, change=False)
        self.assertEqual(obj.updated_by, self.regular_user)

    def test_save_existing_object_does_not_change_created_by(self):
        admin_obj = self._make_admin()
        request = _make_request(self.regular_user)
        # obj already has a PK and a different created_by
        self.project.created_by = self.other_user
        self.project.save()
        admin_obj.save_model(request, self.project, form=None, change=True)
        self.project.refresh_from_db()
        self.assertEqual(self.project.created_by, self.other_user)

    def test_save_existing_object_updates_updated_by(self):
        admin_obj = self._make_admin()
        request = _make_request(self.regular_user)
        admin_obj.save_model(request, self.project, form=None, change=True)
        self.project.refresh_from_db()
        self.assertEqual(self.project.updated_by, self.regular_user)


# ===========================================================================
# ProjectBasedPermissionMixin – get_queryset
# ===========================================================================


class ProjectBasedPermissionMixinQuerysetTest(_MixinSetup):

    def test_superuser_sees_all_locations(self):
        request = _make_request(self.superuser)
        qs = self.project_admin.get_queryset(request)
        self.assertIn(self.loc1, qs)
        self.assertIn(self.loc2, qs)

    def test_regular_user_sees_only_permitted_location(self):
        request = _make_request(self.regular_user)
        qs = self.project_admin.get_queryset(request)
        self.assertIn(self.loc1, qs)
        self.assertNotIn(self.loc2, qs)

    def test_user_without_permission_sees_nothing(self):
        request = _make_request(self.other_user)
        qs = self.project_admin.get_queryset(request)
        self.assertNotIn(self.loc1, qs)
        self.assertNotIn(self.loc2, qs)

    def test_literature_location_visible_to_all(self):
        from field_data.admin import LocationAdmin
        from django.contrib.gis import admin as gis_admin
        loc_admin = LocationAdmin(Location, self.site)
        # Create a literature location (no project)
        from bibliography.models import Author, Reference
        author = Author.objects.create(last_name="Test", first_name="T")
        ref = Reference.objects.create(
            title="Lit Ref", lead_author=author, abstract="x", type="Paper"
        )
        lit_loc = Location.objects.create(
            identifier="LIT_MX01",
            data_source="literature",
            reference=ref,
        )
        request = _make_request(self.other_user)
        qs = loc_admin.get_queryset(request)
        self.assertIn(lit_loc, qs)


# ===========================================================================
# ProjectBasedPermissionMixin – has_*_permission
# ===========================================================================


class ProjectBasedPermissionMixinPermTest(_MixinSetup):

    def test_has_change_permission_no_obj_returns_true(self):
        request = _make_request(self.regular_user)
        self.assertTrue(self.project_admin.has_change_permission(request, obj=None))

    def test_has_change_permission_with_project_checks_guardian(self):
        request = _make_request(self.regular_user)
        self.assertTrue(
            self.project_admin.has_change_permission(request, obj=self.loc1)
        )

    def test_has_change_permission_denied_without_perm(self):
        request = _make_request(self.other_user)
        self.assertFalse(
            self.project_admin.has_change_permission(request, obj=self.loc1)
        )

    def test_has_delete_permission_denied_without_perm(self):
        request = _make_request(self.other_user)
        self.assertFalse(
            self.project_admin.has_delete_permission(request, obj=self.loc1)
        )

    def test_has_delete_permission_granted_with_perm(self):
        request = _make_request(self.regular_user)
        self.assertTrue(
            self.project_admin.has_delete_permission(request, obj=self.loc1)
        )


# ===========================================================================
# NestedProjectPermissionMixin
# ===========================================================================


class NestedProjectPermissionMixinTest(_MixinSetup):

    def setUp(self):
        super().setUp()
        self.loc_admin = _LocationAdmin(Location, self.site)

    def test_get_project_filter_path(self):
        self.assertEqual(
            self.loc_admin.get_project_filter_path(), "project_id__in"
        )

    def test_get_project_from_obj_single_level(self):
        loc = Location(project=self.project)
        result = self.loc_admin.get_project_from_obj(loc)
        self.assertEqual(result, self.project)

    def test_get_project_from_obj_with_none_field(self):
        loc = Location(project=None)
        result = self.loc_admin.get_project_from_obj(loc)
        self.assertIsNone(result)

    def test_get_project_filter_path_without_project_path_raises(self):
        class _NoPP(NestedProjectPermissionMixin, ModelAdmin):
            project_path = None
        admin_obj = _NoPP(Location, self.site)
        with self.assertRaises(NotImplementedError):
            admin_obj.get_project_filter_path()

    def test_two_level_traversal(self):
        class _TwoLevel(NestedProjectPermissionMixin, ModelAdmin):
            project_path = "location__project"
        admin_obj = _TwoLevel(Sample, self.site)
        loc = MagicMock()
        loc.project = self.project
        sample = MagicMock()
        sample.location = loc
        result = admin_obj.get_project_from_obj(sample)
        self.assertEqual(result, self.project)

    def test_two_level_traversal_with_none_intermediate(self):
        class _TwoLevel(NestedProjectPermissionMixin, ModelAdmin):
            project_path = "location__project"
        admin_obj = _TwoLevel(Sample, self.site)
        sample = MagicMock()
        sample.location = None
        result = admin_obj.get_project_from_obj(sample)
        self.assertIsNone(result)


# ===========================================================================
# HybridProjectPermissionMixin
# ===========================================================================


class HybridProjectPermissionMixinTest(_MixinSetup):

    def setUp(self):
        super().setUp()
        self.internal_loc = Location.objects.create(
            identifier="HYB_LOC",
            data_source="internal",
            project=self.project,
        )
        self.sample_direct = Sample.objects.create(
            identifier="HYB_S_DIRECT",
            project=self.project,
        )
        self.sample_via_loc = Sample.objects.create(
            identifier="HYB_S_VIA_LOC",
            location=self.internal_loc,
        )

    def test_queryset_includes_direct_project_sample(self):
        request = _make_request(self.regular_user)
        qs = self.sample_admin.get_queryset(request)
        self.assertIn(self.sample_direct, qs)

    def test_queryset_includes_location_project_sample(self):
        request = _make_request(self.regular_user)
        qs = self.sample_admin.get_queryset(request)
        self.assertIn(self.sample_via_loc, qs)

    def test_user_without_perm_sees_nothing(self):
        request = _make_request(self.other_user)
        qs = self.sample_admin.get_queryset(request)
        self.assertNotIn(self.sample_direct, qs)

    def test_has_change_permission_with_direct_project(self):
        request = _make_request(self.regular_user)
        self.assertTrue(
            self.sample_admin.has_change_permission(request, obj=self.sample_direct)
        )


# ===========================================================================
# has_add_permission — checks add_project, not view_project
# ===========================================================================


class HasAddPermissionTest(_MixinSetup):
    """has_add_permission returns True only when the user has add_project on at
    least one project via Guardian (object-level), regardless of view_project."""

    def setUp(self):
        super().setUp()
        # regular_user gets view/change/delete in _MixinSetup.setUp but NOT add_project.
        # Confirm that: has_add_permission must be False until add_project is granted.
        self.loc_admin = _LocationProjectAdmin(Location, self.site)
        self.nested_admin = _LocationAdmin(Location, self.site)

    def test_has_add_false_without_add_project(self):
        """User with only view/change/delete on a project cannot add objects."""
        request = _make_request(self.regular_user)
        self.assertFalse(self.loc_admin.has_add_permission(request))

    def test_has_add_true_with_add_project(self):
        """User with add_project on at least one project can add objects."""
        assign_perm("prototype.add_project", self.regular_user, self.project)
        request = _make_request(self.regular_user)
        self.assertTrue(self.loc_admin.has_add_permission(request))

    def test_superuser_always_can_add(self):
        request = _make_request(self.superuser)
        self.assertTrue(self.loc_admin.has_add_permission(request))

    def test_user_without_any_perm_cannot_add(self):
        request = _make_request(self.other_user)
        self.assertFalse(self.loc_admin.has_add_permission(request))

    def test_nested_mixin_has_add_false_without_add_project(self):
        request = _make_request(self.regular_user)
        self.assertFalse(self.nested_admin.has_add_permission(request))

    def test_nested_mixin_has_add_true_with_add_project(self):
        assign_perm("prototype.add_project", self.regular_user, self.project)
        request = _make_request(self.regular_user)
        self.assertTrue(self.nested_admin.has_add_permission(request))

    def test_hybrid_mixin_has_add_false_without_add_project(self):
        request = _make_request(self.regular_user)
        self.assertFalse(self.sample_admin.has_add_permission(request))

    def test_hybrid_mixin_has_add_true_with_add_project(self):
        assign_perm("prototype.add_project", self.regular_user, self.project)
        request = _make_request(self.regular_user)
        self.assertTrue(self.sample_admin.has_add_permission(request))

    def test_view_only_perm_does_not_grant_add(self):
        """Regression: view_project alone must NOT be sufficient for has_add_permission."""
        # regular_user already has view_project (from _MixinSetup.setUp) but NOT add_project.
        request = _make_request(self.regular_user)
        self.assertFalse(self.loc_admin.has_add_permission(request))
        self.assertFalse(self.nested_admin.has_add_permission(request))
        self.assertFalse(self.sample_admin.has_add_permission(request))


# ===========================================================================
# GuardianPermissionMixin
# ===========================================================================


class GuardianPermissionMixinTest(_MixinSetup):

    def test_superuser_sees_all_via_guardian_mixin(self):
        request = _make_request(self.superuser)
        qs = self.guardian_admin.get_queryset(request)
        self.assertIn(self.project, qs)
        self.assertIn(self.project2, qs)

    def test_regular_user_sees_only_objects_with_view_perm(self):
        request = _make_request(self.regular_user)
        qs = self.guardian_admin.get_queryset(request)
        self.assertIn(self.project, qs)
        self.assertNotIn(self.project2, qs)

    def test_has_change_permission_with_guardian_perm(self):
        request = _make_request(self.regular_user)
        self.assertTrue(
            self.guardian_admin.has_change_permission(request, obj=self.project)
        )

    def test_has_change_permission_without_guardian_perm(self):
        request = _make_request(self.other_user)
        self.assertFalse(
            self.guardian_admin.has_change_permission(request, obj=self.project)
        )

    def test_has_delete_permission_with_guardian_perm(self):
        request = _make_request(self.regular_user)
        self.assertTrue(
            self.guardian_admin.has_delete_permission(request, obj=self.project)
        )

    def test_has_delete_permission_without_guardian_perm(self):
        request = _make_request(self.other_user)
        self.assertFalse(
            self.guardian_admin.has_delete_permission(request, obj=self.project)
        )

    def test_has_view_permission_with_guardian_perm(self):
        request = _make_request(self.regular_user)
        self.assertTrue(
            self.guardian_admin.has_view_permission(request, obj=self.project)
        )

    def test_has_view_permission_without_guardian_perm(self):
        request = _make_request(self.other_user)
        self.assertFalse(
            self.guardian_admin.has_view_permission(request, obj=self.project)
        )
