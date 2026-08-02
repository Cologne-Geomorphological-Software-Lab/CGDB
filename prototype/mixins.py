"""Admin permission mixins for project-based and object-level access control."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.db.models import Q, QuerySet
from guardian.shortcuts import get_objects_for_user

from prototype.models import Project

if TYPE_CHECKING:
    from django.db.models import Field
    from django.forms import ModelChoiceField
    from django.http import HttpRequest


def _has_data_source_field(model: type) -> bool:
    """Return True only when the model has a real database field named data_source."""
    try:
        model._meta.get_field("data_source")
    except FieldDoesNotExist:
        return False
    else:
        return True


def _accessible_projects(user: object) -> QuerySet:
    """Return projects for which the user has view_project permission."""
    return get_objects_for_user(
        user,
        "prototype.view_project",
        klass=Project,
        use_groups=True,
        any_perm=False,
        with_superuser=False,
        accept_global_perms=False,
    )


def _addable_projects(user: object) -> QuerySet:
    """Projects where the user has add_project permission (can create data within)."""
    return get_objects_for_user(
        user,
        "prototype.add_project",
        klass=Project,
        use_groups=True,
        any_perm=False,
        with_superuser=False,
        accept_global_perms=False,
    )


AUDIT_READONLY_FIELDS = [
    "created_at",
    "created_by",
    "modified_at",
    "updated_by",
]


def _project_scoped_queryset(
    request: HttpRequest,
    admin_model: type[Any],
    field_name: str,
    related_model: type[Any],
    project_lookup: str,
) -> QuerySet:
    """Restrict a FK field's admin choices to add_project-permitted projects.

    Always also includes the object's *current* value for this field (found
    via the change view's object_id in the URL) even when the user can't
    newly "add" there — otherwise editing a record without touching this
    field could fail with a spurious "select a valid choice" error.

    *field_name* is the FK field on *admin_model* (e.g. "project",
    "study_area"); *related_model* is what it points at; *project_lookup* is
    the path from *related_model* back to Project ("pk" when related_model
    already is Project itself, otherwise an ORM lookup like "project" or
    "location__project").
    """
    addable_ids = _addable_projects(request.user).values_list("id", flat=True)
    allowed = related_model.objects.filter(
        **{f"{project_lookup}__in": addable_ids}
    )
    object_id = (
        request.resolver_match.kwargs.get("object_id")
        if request.resolver_match
        else None
    )
    if object_id:
        current_id = (
            admin_model.objects.filter(pk=object_id)
            .values_list(f"{field_name}_id", flat=True)
            .first()
        )
        if current_id is not None:
            allowed = allowed | related_model.objects.filter(pk=current_id)
    return allowed.distinct()


class CreatedUpdatedModelAdminMixin:
    """Sets created_by and updated_by on save. Use as a base for admin classes that manage BaseModel objects."""

    def save_model(
        self,
        request: HttpRequest,
        obj: object,
        form: object,
        change: bool,
    ) -> None:
        """Set created_by on insert and updated_by on every save."""
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


class ProjectBasedPermissionMixin:
    """Mixin for admin classes that need project-based permissions.

    Literature data (data_source='literature') is visible to all users but
    editable only by superusers.
    """

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Return only objects belonging to projects the user may view."""
        if request.user.is_superuser:
            return super().get_queryset(request)

        accessible_project_ids = _accessible_projects(
            request.user,
        ).values_list("id", flat=True)
        qs = super().get_queryset(request)

        if _has_data_source_field(self.model):
            return qs.filter(
                Q(project_id__in=accessible_project_ids)
                | Q(data_source="literature"),
            )
        return qs.filter(project_id__in=accessible_project_ids)

    def formfield_for_foreignkey(
        self, db_field: Field, request: HttpRequest, **kwargs: object
    ) -> ModelChoiceField | None:
        """Scope the "project" field's choices to add_project-permitted projects.

        Also restricts the *add* form's project dropdown, which had no
        restriction at all before this.
        """
        if db_field.name == "project" and not request.user.is_superuser:
            kwargs["queryset"] = _project_scoped_queryset(
                request, self.model, "project", Project, "pk"
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Allow add only when the user has add_project permission on at least one project."""
        if request.user.is_superuser:
            return True
        return _addable_projects(request.user).exists()

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Allow change only when the user has change_project on the object's project.

        This only ever checks the object's project *before* an edit — see
        save_model() below, which is what actually blocks reparenting the
        object into a project the user has no add_project permission on.
        """
        if obj is None:
            return True
        if request.user.is_superuser:
            return True

        if hasattr(obj, "data_source") and obj.data_source == "literature":
            return False

        if hasattr(obj, "project") and obj.project:
            return request.user.has_perm(
                "prototype.change_project",
                obj.project,
            )

        return super().has_change_permission(request, obj)

    def has_view_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Allow view only when the user has view_project on the object's project."""
        if obj is None:
            return True
        if request.user.is_superuser:
            return True

        if hasattr(obj, "project") and obj.project:
            return request.user.has_perm("prototype.view_project", obj.project)

        return super().has_view_permission(request, obj)

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Allow delete only when the user has delete_project on the object's project."""
        if obj is None:
            return True
        if request.user.is_superuser:
            return True

        if hasattr(obj, "data_source") and obj.data_source == "literature":
            return False

        if hasattr(obj, "project") and obj.project:
            return request.user.has_perm(
                "prototype.delete_project",
                obj.project,
            )

        return super().has_delete_permission(request, obj)

    def save_model(
        self,
        request: HttpRequest,
        obj: object,
        form: object,
        change: bool,
    ) -> None:
        """Reject a save that reparents obj into a project the user can't add to.

        has_change_permission() above only ever sees the object's project
        *before* the edit — this is the check that actually looks at the
        form's new value. formfield_for_foreignkey() already keeps the
        project dropdown from offering an unauthorized project in the first
        place; this is the server-side backstop for direct POSTs.
        """
        if change and not request.user.is_superuser:
            old_project = getattr(
                self.model.objects.get(pk=obj.pk), "project", None
            )
            new_project = getattr(obj, "project", None)
            if (
                new_project is not None
                and new_project != old_project
                and not request.user.has_perm(
                    "prototype.add_project", new_project
                )
            ):
                msg = "You do not have permission to move this record into that project."
                raise PermissionDenied(msg)
        super().save_model(request, obj, form, change)


class GuardianPermissionMixin:
    """Generic Guardian permission mixin for any model.

    Provides object-level permission checking for models that inherit from BaseModel
    and use Guardian permissions.
    """

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Return only objects the user has object-level view permission for."""
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

        return qs.filter(
            id__in=accessible_objects.values_list("id", flat=True),
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Allow add when the user has the model-level add permission."""
        if request.user.is_superuser:
            return True
        add_perm = f"{self.opts.app_label}.add_{self.opts.model_name}"
        return request.user.has_perm(add_perm)

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Allow change when the user has object-level change permission."""
        if obj is None:
            return True
        change_perm = f"{self.opts.app_label}.change_{self.opts.model_name}"
        return request.user.has_perm(change_perm, obj)

    def has_view_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Allow view when the user has object-level view permission."""
        if obj is None:
            return True
        view_perm = f"{self.opts.app_label}.view_{self.opts.model_name}"
        return request.user.has_perm(view_perm, obj)

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Allow delete when the user has object-level delete permission."""
        if obj is None:
            return True
        delete_perm = f"{self.opts.app_label}.delete_{self.opts.model_name}"
        return request.user.has_perm(delete_perm, obj)


class NestedProjectPermissionMixin:
    """Mixin for admin classes where the project relationship is nested.

    For example, layer.location.project. Set project_path to the ORM lookup path.
    """

    project_path = None

    def get_project_filter_path(self) -> str:
        """Return the ORM filter keyword for filtering by accessible project IDs."""
        if self.project_path:
            return f"{self.project_path}_id__in"
        msg = "project_path must be defined or get_project_filter_path must be overridden"
        raise NotImplementedError(msg)

    def get_project_from_obj(self, obj: object) -> object:
        """Traverse project_path attributes on obj and return the project instance."""
        if self.project_path:
            current_obj = obj
            for attr in self.project_path.split("__"):
                if current_obj is None:
                    return None
                current_obj = getattr(current_obj, attr, None)
            return current_obj
        msg = "project_path must be defined or get_project_from_obj must be overridden"
        raise NotImplementedError(msg)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Return only objects reachable through the nested project the user may view."""
        if request.user.is_superuser:
            return super().get_queryset(request)

        accessible_project_ids = _accessible_projects(
            request.user,
        ).values_list("id", flat=True)
        qs = super().get_queryset(request)
        filter_kwargs = {
            self.get_project_filter_path(): accessible_project_ids,
        }
        return qs.filter(**filter_kwargs)

    def formfield_for_foreignkey(
        self, db_field: Field, request: HttpRequest, **kwargs: object
    ) -> ModelChoiceField | None:
        """Scope project_path's anchor field to add_project-permitted projects.

        E.g. for project_path="study_area__project", restricts the
        "study_area" field to study areas whose own project is addable.
        Derived entirely from project_path — no per-subclass code needed.
        """
        path_parts = (self.project_path or "").split("__")
        if (
            self.project_path
            and db_field.name == path_parts[0]
            and not request.user.is_superuser
        ):
            kwargs["queryset"] = _project_scoped_queryset(
                request,
                self.model,
                path_parts[0],
                db_field.related_model,
                "__".join(path_parts[1:]),
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Allow add only when the user has add_project permission on at least one project."""
        if request.user.is_superuser:
            return True
        return _addable_projects(request.user).exists()

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Allow change when the user has change_project on the nested project.

        This only ever checks the pre-edit object — see save_model() below,
        which is what actually blocks reparenting the object into a project
        the user has no add_project permission on.
        """
        if obj is None:
            return True
        if request.user.is_superuser:
            return True
        project = self.get_project_from_obj(obj)
        if project:
            return request.user.has_perm("prototype.change_project", project)
        return super().has_change_permission(request, obj)

    def has_view_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Allow view when the user has view_project on the nested project."""
        if obj is None:
            return True
        if request.user.is_superuser:
            return True
        project = self.get_project_from_obj(obj)
        if project:
            return request.user.has_perm("prototype.view_project", project)
        return super().has_view_permission(request, obj)

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Allow delete when the user has delete_project on the nested project."""
        if obj is None:
            return True
        if request.user.is_superuser:
            return True
        project = self.get_project_from_obj(obj)
        if project:
            return request.user.has_perm("prototype.delete_project", project)
        return super().has_delete_permission(request, obj)

    def save_model(
        self,
        request: HttpRequest,
        obj: object,
        form: object,
        change: bool,
    ) -> None:
        """Reject a save that reparents obj into a project the user can't add to.

        See ProjectBasedPermissionMixin.save_model — same shape, resolving
        old/new project via get_project_from_obj() instead of a bare project
        attribute.
        """
        if change and not request.user.is_superuser:
            old_project = self.get_project_from_obj(
                self.model.objects.get(pk=obj.pk)
            )
            new_project = self.get_project_from_obj(obj)
            if (
                new_project is not None
                and new_project != old_project
                and not request.user.has_perm(
                    "prototype.add_project", new_project
                )
            ):
                msg = "You do not have permission to move this record into that project."
                raise PermissionDenied(msg)
        super().save_model(request, obj, form, change)


class HybridProjectPermissionMixin:
    """Mixin for models with both a direct project FK and an indirect one through location.

    For example, Sample which can have project or location.project.
    """

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Return objects accessible via either a direct or location-level project FK."""
        if request.user.is_superuser:
            return super().get_queryset(request)

        accessible_project_ids = _accessible_projects(
            request.user,
        ).values_list("id", flat=True)
        qs = super().get_queryset(request)
        return qs.filter(
            Q(project_id__in=accessible_project_ids)
            | Q(location__project_id__in=accessible_project_ids),
        )

    def formfield_for_foreignkey(
        self, db_field: Field, request: HttpRequest, **kwargs: object
    ) -> ModelChoiceField | None:
        """Scope the direct "project" field's choices to add_project-permitted projects.

        The indirect "location" field is scoped by SampleAdmin's own
        formfield_for_foreignkey override (field_data/admin.py) instead —
        Location isn't native to this app, and that override already exists.
        """
        if db_field.name == "project" and not request.user.is_superuser:
            kwargs["queryset"] = _project_scoped_queryset(
                request, self.model, "project", Project, "pk"
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Allow add only when the user has add_project permission on at least one project."""
        if request.user.is_superuser:
            return True
        return _addable_projects(request.user).exists()

    def _get_project(self, obj: object) -> object:
        if hasattr(obj, "project") and obj.project:
            return obj.project
        if (
            hasattr(obj, "location")
            and obj.location
            and hasattr(obj.location, "project")
        ):
            return obj.location.project
        return None

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Allow change when the user has change_project on the resolved project."""
        if obj is None:
            return True
        if request.user.is_superuser:
            return True
        project = self._get_project(obj)
        if project:
            return request.user.has_perm("prototype.change_project", project)
        return super().has_change_permission(request, obj)

    def has_view_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Allow view when the user has view_project on the resolved project."""
        if obj is None:
            return True
        if request.user.is_superuser:
            return True
        project = self._get_project(obj)
        if project:
            return request.user.has_perm("prototype.view_project", project)
        return super().has_view_permission(request, obj)

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Allow delete when the user has delete_project on the resolved project."""
        if obj is None:
            return True
        if request.user.is_superuser:
            return True
        project = self._get_project(obj)
        if project:
            return request.user.has_perm("prototype.delete_project", project)
        return super().has_delete_permission(request, obj)

    def save_model(
        self,
        request: HttpRequest,
        obj: object,
        form: object,
        change: bool,
    ) -> None:
        """Reject a save that reparents obj into a project the user can't add to.

        See ProjectBasedPermissionMixin.save_model — same shape, resolving
        old/new project via _get_project() instead of a bare project
        attribute.
        """
        if change and not request.user.is_superuser:
            old_project = self._get_project(self.model.objects.get(pk=obj.pk))
            new_project = self._get_project(obj)
            if (
                new_project is not None
                and new_project != old_project
                and not request.user.has_perm(
                    "prototype.add_project", new_project
                )
            ):
                msg = "You do not have permission to move this record into that project."
                raise PermissionDenied(msg)
        super().save_model(request, obj, form, change)
