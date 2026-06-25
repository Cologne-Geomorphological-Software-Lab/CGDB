"""Custom DRF permission classes for project-based access control."""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request


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
            return getattr(obj, "data_source", None) == "literature"

        return request.user.has_perm("prototype.view_project", project)
