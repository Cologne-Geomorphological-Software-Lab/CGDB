"""Regression tests for a base-class-ordering bug in project-scoped admins.

Several admin classes across field_data and analysis listed their
project-permission mixin (ProjectBasedPermissionMixin /
NestedProjectPermissionMixin / HybridProjectPermissionMixin) AFTER
django.contrib.admin.ModelAdmin in their base classes, e.g.::

    class StudyAreaAdmin(ExportMixin, ModelAdmin, ProjectBasedPermissionMixin):
        ...

Because Python resolves methods left-to-right through the MRO, ModelAdmin's
own unfiltered get_queryset()/has_*_permission() were used instead of the
mixin's, silently disabling project-based access control: any user with a
group-granted, non-project-scoped Django permission (e.g. "view_location")
could see and edit every object across every project via /admin/.

These tests guard against that bug reappearing — for any model, not just the
ones it was found on — by inspecting the real admin registry rather than a
hand-built test double (unlike test_mixins.py, which tests the mixins'
*logic* in isolation and would not have caught a wiring mistake like this).
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from field_data.admin import LocationAdmin
from field_data.models import Location
from guardian.shortcuts import assign_perm
from prototype.models import Project

_PROJECT_MIXIN_NAMES = {
    "ProjectBasedPermissionMixin",
    "NestedProjectPermissionMixin",
    "HybridProjectPermissionMixin",
}
_DJANGO_BASE_NAMES = {"ModelAdmin", "BaseModelAdmin"}
_PERMISSION_METHODS = (
    "get_queryset",
    "has_view_permission",
    "has_change_permission",
    "has_add_permission",
    "has_delete_permission",
)


class AdminMixinWiringTest(TestCase):
    """Every registered admin using a project-permission mixin must actually use it."""

    def test_project_permission_methods_are_not_shadowed_by_modeladmin(self) -> None:
        """No project-scoped admin's permission methods may resolve to plain ModelAdmin.

        This is the exact invariant the ordering bug violated: Django's base
        ModelAdmin/BaseModelAdmin must never be the class that "wins" the MRO
        lookup for get_queryset/has_*_permission when a project-permission
        mixin is also present in the bases.
        """
        checked_labels = []
        for model, admin_instance in admin.site._registry.items():
            cls = type(admin_instance)
            mro_names = [base.__name__ for base in cls.__mro__]
            if not any(name in mro_names for name in _PROJECT_MIXIN_NAMES):
                continue
            checked_labels.append(model._meta.label)
            for method_name in _PERMISSION_METHODS:
                method = getattr(cls, method_name)
                owner = method.__qualname__.split(".")[0]
                assert owner not in _DJANGO_BASE_NAMES, (
                    f"{cls.__name__}.{method_name} resolves to Django's "
                    f"{owner} instead of a project-permission mixin — base "
                    f"class order is broken for {model._meta.label}. The "
                    "mixin must be listed before ModelAdmin in the class's "
                    "bases."
                )

        # Sanity check: make sure this test actually exercised real admin
        # classes and did not silently pass because nothing matched.
        assert len(checked_labels) >= 16, (
            "Expected at least 16 project-scoped admin classes to be "
            f"checked, only found {len(checked_labels)}: {checked_labels}"
        )


class LocationAdminProjectScopingTest(TestCase):
    """Concrete behavioral check for the admin class the bug was found on."""

    def test_get_queryset_excludes_other_projects_locations(self) -> None:
        """A user may only see Locations belonging to projects they can view."""
        user = User.objects.create_user(username="scoped_user")
        own_project = Project.objects.create(
            title="Own Project", label="OWN", status="ACTIVE"
        )
        other_project = Project.objects.create(
            title="Other Project", label="OTH", status="ACTIVE"
        )
        assign_perm("view_project", user, own_project)

        own_location = Location.objects.create(
            project=own_project, identifier="own-location"
        )
        Location.objects.create(
            project=other_project, identifier="other-location"
        )

        request = RequestFactory().get("/admin/field_data/location/")
        request.user = user

        location_admin = LocationAdmin(Location, admin.site)
        visible = location_admin.get_queryset(request)

        assert list(visible) == [own_location]

    def test_has_change_permission_denies_other_projects_object(self) -> None:
        """A user without change_project on an object's project cannot edit it."""
        user = User.objects.create_user(username="scoped_user_2")
        own_project = Project.objects.create(
            title="Own Project 2", label="OWN2", status="ACTIVE"
        )
        other_project = Project.objects.create(
            title="Other Project 2", label="OTH2", status="ACTIVE"
        )
        assign_perm("view_project", user, own_project)
        assign_perm("change_project", user, own_project)

        foreign_location = Location.objects.create(
            project=other_project, identifier="foreign-location"
        )

        request = RequestFactory().get("/admin/field_data/location/")
        request.user = user

        location_admin = LocationAdmin(Location, admin.site)
        assert (
            location_admin.has_change_permission(request, foreign_location)
            is False
        )
