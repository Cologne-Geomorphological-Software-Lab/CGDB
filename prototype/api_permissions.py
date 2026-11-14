"""Custom DRF permission classes for project-based access control.

The rules themselves live in prototype.access, shared with the admin.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from rest_framework.permissions import BasePermission, DjangoModelPermissions

from prototype.access import has_project_perm, is_literature, resolve_project

if TYPE_CHECKING:
    from rest_framework.request import Request

    from prototype.models import Project


class RoleModelPermission(DjangoModelPermissions):
    """The user's role must allow the request's action on the view's model.

    The first half of "role AND project": put it before the project-level
    permission class of every viewset whose model is in the role groups.
    Unlike DRF's DjangoModelPermissions, reading needs the view permission
    too, so a user without any role group cannot read project data either.
    """

    perms_map: ClassVar[dict[str, list[str]]] = {
        **DjangoModelPermissions.perms_map,
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
    }


class IsProjectMember(BasePermission):
    """Object-level permission: user must have view_project on the object's project.

    Traverses .project or .location.project to find the owning project.
    Literature records (see prototype.access.LITERATURE_ELIGIBLE_MODELS) are
    accessible to all authenticated users.
    """

    project_paths: tuple[str, ...] = ("project", "location__project")

    def has_permission(self, request: Request, _view: object) -> bool:
        """Return True if the request carries an authenticated user."""
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(
        self, request: Request, _view: object, obj: object
    ) -> bool:
        """Return True if the user may access this specific object."""
        if request.user.is_superuser:
            return True

        project = self._resolve_project(obj)
        if project is None:
            return is_literature(obj)

        return has_project_perm(request.user, "view", project)

    def _resolve_project(self, obj: object) -> Project | None:
        """Return the project that owns *obj*, or None."""
        return resolve_project(obj, self.project_paths)


class ProjectPathPermission(IsProjectMember):
    """Object-level permission: resolves the owning Project by traversing a path.

    The path is a dunder-separated attribute chain (e.g. "sample",
    "counting__sample") leading to an object with a .project. Subclass and
    set project_path. Mirrors IsProjectMember for models that reach their
    Project through a chain of FKs rather than a direct .project or
    .location.project.
    """

    project_path: str = ""

    def _resolve_project(self, obj: object) -> Project | None:
        """Walk project_path, then take that object's .project."""
        return resolve_project(obj, (f"{self.project_path}__project",))


class SampleScopedPermission(ProjectPathPermission):
    """Project-path permission for models with a direct .sample FK."""

    project_path = "sample"


class CountingScopedPermission(ProjectPathPermission):
    """Project-path permission for models reached via .counting.sample."""

    project_path = "counting__sample"


class RawMeasurementScopedPermission(ProjectPathPermission):
    """Project-path permission for models reached via .raw_measurement."""

    project_path = "raw_measurement"


class MeasurementScopedPermission(ProjectPathPermission):
    """Project-path permission for models reached via .measurement.sample."""

    project_path = "measurement__sample"
