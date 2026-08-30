"""Custom DRF permission classes for project-based access control."""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

# Architecture-review fix (F22): explicit allowlist of models the
# "literature data is public" exception applies to, rather than
# getattr(obj, "data_source", None) == "literature" happening to return
# False for every other scoped model only because they lack that field.
# That was fail-open-shaped: it silently relied on no *current* model in
# the traversal chain both having a null project link and a
# coincidentally-named data_source field — the same "traverse to find
# project, fall back on a missing link" shape as the admin-layer IDOR this
# project already fixed once. Add a model here only when it genuinely has
# its own data_source field with a "literature" value.
_LITERATURE_ELIGIBLE_MODELS = frozenset({"Location"})


def _is_literature_object(obj: object) -> bool:
    """Return True only for objects the literature exception is meant to cover."""
    return (
        type(obj).__name__ in _LITERATURE_ELIGIBLE_MODELS
        and getattr(obj, "data_source", None) == "literature"
    )


class IsProjectMember(BasePermission):
    """Object-level permission: user must have view_project on the object's project.

    Traverses .project or .location.project to find the owning project.
    Objects with data_source='literature' are accessible to all authenticated users.
    """

    def has_permission(self, request: Request, _view: object) -> bool:
        """Return True if the request carries an authenticated user."""
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(
        self, request: Request, _view: object, obj: object
    ) -> bool:
        """Return True if the user may access this specific object."""
        if request.user.is_superuser:
            return True

        # Direct project FK (e.g. Location, Sample, Campaign)
        project = getattr(obj, "project", None)

        # Nested via location (e.g. Layer → location.project)
        if project is None:
            location = getattr(obj, "location", None)
            if location is not None:
                project = getattr(location, "project", None)

        if project is None:
            # Literature locations are public to all authenticated users
            return _is_literature_object(obj)

        return request.user.has_perm("prototype.view_project", project)


class ProjectPathPermission(BasePermission):
    """Object-level permission: resolves the owning Project by traversing a path.

    The path is a dunder-separated attribute chain (e.g. "sample",
    "counting__sample"). Subclass and set project_path. Mirrors
    IsProjectMember's traversal for models that reach their Project through
    a chain of FKs rather than a direct .project or .location.project.
    """

    project_path: str = ""

    def has_permission(self, request: Request, _view: object) -> bool:
        """Return True if the request carries an authenticated user."""
        return bool(request.user and request.user.is_authenticated)

    def _resolve_project(self, obj: object) -> object | None:
        """Walk project_path's attribute chain and return the Project, or None."""
        current = obj
        for attr in self.project_path.split("__"):
            current = getattr(current, attr, None)
            if current is None:
                return None
        return getattr(current, "project", None)

    def has_object_permission(
        self, request: Request, _view: object, obj: object
    ) -> bool:
        """Return True if the user may access this specific object."""
        if request.user.is_superuser:
            return True

        project = self._resolve_project(obj)
        if project is None:
            return _is_literature_object(obj)

        return request.user.has_perm("prototype.view_project", project)


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
