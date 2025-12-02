from django.db.models import Q
from guardian.shortcuts import get_objects_for_user

from prototype.models import Project


class ProjectBasedPermissionMixin:
    """Mixin for admin classes that need project-based permissions.

    This mixin filters objects based on the user's project permissions,
    allowing literature data to be visible to all users.
    """

    def get_queryset(self, request):
        """Filter queryset based on user's project permissions."""
        if request.user.is_superuser:
            return super().get_queryset(request)

        accessible_projects = get_objects_for_user(
            request.user,
            "prototype.view_project", 
            klass=Project,
            use_groups=True,
            any_perm=False,
            with_superuser=False,
            accept_global_perms=False,
        )

        accessible_project_ids = accessible_projects.values_list("id", flat=True)

        qs = super().get_queryset(request)

        if hasattr(self.model, "data_source"):
            return qs.filter(
                Q(project_id__in=accessible_project_ids) | Q(data_source="literature")
            )
        else:
            return qs.filter(project_id__in=accessible_project_ids)

    def has_change_permission(self, request, obj=None):
        """Check change permission for project-based objects."""
        if obj is None:
            return True

        if hasattr(obj, "data_source") and obj.data_source == "literature":
            return True

        if hasattr(obj, "project") and obj.project:
            return request.user.has_perm("prototype.change_project", obj.project)

        return super().has_change_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        """Check view permission for project-based objects."""
        if obj is None:
            return True

        if hasattr(obj, "project") and obj.project:
            return request.user.has_perm("prototype.view_project", obj.project)

        return super().has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Check delete permission for project-based objects."""
        if obj is None:
            return True

        if hasattr(obj, "data_source") and obj.data_source == "literature":
            return request.user.is_superuser

        if hasattr(obj, "project") and obj.project:
            return request.user.has_perm("prototype.delete_project", obj.project)

        return super().has_delete_permission(request, obj)


class GuardianPermissionMixin:
    """Generic Guardian permission mixin for any model.

    This mixin provides generic object-level permission checking
    for models that inherit from BaseModel and use Guardian permissions.
    """

    def get_queryset(self, request):
        """Filter queryset based on user permissions."""
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label
        view_perm = f"{app_label}.view_{model_name}"

        accessible_objects = get_objects_for_user(
            request.user,
            view_perm,
            klass=self.model,
            use_groups=True,
            any_perm=False,
            with_superuser=False,
            accept_global_perms=False,
        )

        return qs.filter(id__in=accessible_objects.values_list("id", flat=True))

    def has_change_permission(self, request, obj=None):
        """Check change permission using Guardian."""
        if obj is None:
            return True
        change_perm = f"{self.opts.app_label}.change_{self.opts.model_name}"
        return request.user.has_perm(change_perm, obj)

    def has_view_permission(self, request, obj=None):
        """Check view permission using Guardian."""
        if obj is None:
            return True
        view_perm = f"{self.opts.app_label}.view_{self.opts.model_name}"
        return request.user.has_perm(view_perm, obj)

    def has_delete_permission(self, request, obj=None):
        """Check delete permission using Guardian."""
        if obj is None:
            return True
        delete_perm = f"{self.opts.app_label}.delete_{self.opts.model_name}"
        return request.user.has_perm(delete_perm, obj)

    def has_add_permission(self, request, obj=None):
        """Check add permission using Guardian."""
        add_perm = f"{self.opts.app_label}.add_{self.opts.model_name}"
        return request.user.has_perm(add_perm, obj)


class NestedProjectPermissionMixin:
    """Mixin for admin classes where project relationship is nested (e.g., site.study_area.project).

    This mixin handles cases where the model doesn't have a direct project relationship,
    but accesses it through a nested relationship.
    """

    project_path = None

    def get_project_filter_path(self):
        """Get the filter path to the project field. Override this method in subclasses."""
        if self.project_path:
            return f"{self.project_path}_id__in"
        raise NotImplementedError(
            "project_path must be defined or get_project_filter_path must be overridden"
        )

    def get_project_from_obj(self, obj):
        """Get the project from an object. Override this method in subclasses."""
        if self.project_path:
            current_obj = obj
            for attr in self.project_path.split("__"):
                if current_obj is None:
                    return None
                current_obj = getattr(current_obj, attr, None)
            return current_obj
        raise NotImplementedError(
            "project_path must be defined or get_project_from_obj must be overridden"
        )

    def get_queryset(self, request):
        """Filter queryset based on user's nested project permissions."""
        if request.user.is_superuser:
            return super().get_queryset(request)

        accessible_projects = get_objects_for_user(
            request.user,
            "prototype.view_project",  
            klass=Project,
            use_groups=True,
            any_perm=False,
            with_superuser=False,
            accept_global_perms=False,
        )

        accessible_project_ids = accessible_projects.values_list("id", flat=True)

        qs = super().get_queryset(request)

        filter_kwargs = {self.get_project_filter_path(): accessible_project_ids}
        return qs.filter(**filter_kwargs)

    def has_change_permission(self, request, obj=None):
        """Check change permission for nested project-based objects."""
        if obj is None:
            return True

        project = self.get_project_from_obj(obj)
        if project:
            return request.user.has_perm("prototype.change_project", project)

        return super().has_change_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        """Check view permission for nested project-based objects."""
        if obj is None:
            return True

        project = self.get_project_from_obj(obj)
        if project:
            return request.user.has_perm("prototype.view_project", project)

        return super().has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Check delete permission for nested project-based objects."""
        if obj is None:
            return True

        project = self.get_project_from_obj(obj)
        if project:
            return request.user.has_perm("prototype.delete_project", project)

        return super().has_delete_permission(request, obj)


class HybridProjectPermissionMixin:
    """Mixin for admin classes with both direct and indirect project relationships.

    This mixin handles cases where the model can have either a direct project relationship
    or an indirect one through another model (like Sample which can have project or location.project).
    """

    def get_queryset(self, request):
        """Filter queryset based on user's hybrid project permissions."""
        if request.user.is_superuser:
            return super().get_queryset(request)

        accessible_projects = get_objects_for_user(
            request.user,
            "prototype.view_project",  
            klass=Project,
            use_groups=True,
            any_perm=False,
            with_superuser=False,
            accept_global_perms=False,
        )

        accessible_project_ids = accessible_projects.values_list("id", flat=True)

        qs = super().get_queryset(request)

        return qs.filter(
            Q(project_id__in=accessible_project_ids)
            | Q(location__project_id__in=accessible_project_ids)
        )

    def has_change_permission(self, request, obj=None):
        """Check change permission for hybrid project-based objects."""
        if obj is None:
            return True

        if hasattr(obj, "project") and obj.project:
            return request.user.has_perm("prototype.change_project", obj.project)

        if (
            hasattr(obj, "location")
            and obj.location
            and hasattr(obj.location, "project")
            and obj.location.project
        ):
            return request.user.has_perm(
                "prototype.change_project", obj.location.project
            )

        return super().has_change_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        """Check view permission for hybrid project-based objects."""
        if obj is None:
            return True

        if hasattr(obj, "project") and obj.project:
            return request.user.has_perm("prototype.view_project", obj.project)

        if (
            hasattr(obj, "location")
            and obj.location
            and hasattr(obj.location, "project")
            and obj.location.project
        ):
            return request.user.has_perm("prototype.view_project", obj.location.project)

        return super().has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Check delete permission for hybrid project-based objects."""
        if obj is None:
            return True

        if hasattr(obj, "project") and obj.project:
            return request.user.has_perm("prototype.delete_project", obj.project)

        if (
            hasattr(obj, "location")
            and obj.location
            and hasattr(obj.location, "project")
            and obj.location.project
        ):
            return request.user.has_perm(
                "prototype.delete_project", obj.location.project
            )

        return super().has_delete_permission(request, obj)
