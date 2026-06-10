"""Django admin registrations and configuration for the prototype app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group, Permission, User
from guardian.shortcuts import assign_perm, remove_perm
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
)
from unfold.decorators import display

from .mixins import GuardianPermissionMixin
from .models import (
    Project,
    ProjectUserObjectPermission,
    Researcher,
    ResearchGroup,
)

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.forms import Field
    from django.http import HttpRequest


class PermissionBasedModelAdmin(
    GuardianPermissionMixin,
    admin.ModelAdmin,
):
    """Base admin class with object-level Guardian permissions."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Allow add when the user holds the model-level add permission."""
        if request.user.is_superuser:
            return True
        add_perm = f"{self.opts.app_label}.add_{self.opts.model_name}"
        return request.user.has_perm(add_perm)

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


_PERMISSION_LABELS = {
    "view_project": "View data",
    "add_project": "Add data",
    "change_project": "Edit data",
    "delete_project": "Delete data",
}

_MEMBER_PERMS = ["view_project", "add_project", "change_project"]


class ProjectUserObjectPermissionInline(TabularInline):
    """Inline editor for per-user object permissions on a Project."""

    model = ProjectUserObjectPermission
    extra = 1
    tab = True
    verbose_name = "User Permission"
    verbose_name_plural = "User Permissions"
    autocomplete_fields = ["user"]
    fields = ["user", "permission", "permission_label"]
    readonly_fields = ["permission_label"]
    ordering = [
        "user__last_name",
        "user__first_name",
        "permission__codename",
    ]

    @display(description="Access level")
    def permission_label(self, obj: ProjectUserObjectPermission) -> str:
        """Return a human-readable access level label for the permission codename."""
        return _PERMISSION_LABELS.get(
            obj.permission.codename,
            obj.permission.codename,
        )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Return the queryset with user and permission pre-fetched."""
        return (
            super().get_queryset(request).select_related("user", "permission")
        )

    def formfield_for_foreignkey(
        self,
        db_field: object,
        request: HttpRequest,
        **kwargs: object,
    ) -> Field | None:
        """Restrict the permission dropdown to project-level prototype permissions."""
        if db_field.name == "permission":
            kwargs["queryset"] = Permission.objects.filter(
                content_type__app_label="prototype",
                content_type__model="project",
            ).order_by("codename")
        return super().formfield_for_foreignkey(
            db_field,
            request,
            **kwargs,
        )

    def has_add_permission(
        self,
        request: HttpRequest,
        _obj: object | None = None,
    ) -> bool:
        """Allow add only for superusers."""
        return request.user.is_superuser

    def has_change_permission(
        self,
        request: HttpRequest,
        _obj: object | None = None,
    ) -> bool:
        """Allow change only for superusers."""
        return request.user.is_superuser

    def has_delete_permission(
        self,
        request: HttpRequest,
        _obj: object | None = None,
    ) -> bool:
        """Allow delete only for superusers."""
        return request.user.is_superuser

    def has_view_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        """Allow view for superusers or users with change_project on the project."""
        return request.user.is_superuser or (
            obj is not None
            and request.user.has_perm("prototype.change_project", obj)
        )


class ResearchGroupAdmin(PermissionBasedModelAdmin, ModelAdmin):
    """Admin for ResearchGroup with object-level Guardian permissions."""

    change_form_show_cancel_button = True
    list_display = ["label", "head_of_group", "created_at"]
    search_fields = ["label"]
    list_filter = ["created_at"]
    readonly_fields = [
        "created_at",
        "created_by",
        "modified_at",
        "updated_by",
    ]


class ResearcherAdmin(PermissionBasedModelAdmin, ModelAdmin):
    """Admin for Researcher with object-level Guardian permissions."""

    change_form_show_cancel_button = True
    list_display = ["user", "academic_rank", "display_researcher"]
    search_fields = [
        "user__username",
        "user__first_name",
        "user__last_name",
    ]
    list_filter = ["academic_rank"]
    readonly_fields = [
        "created_at",
        "created_by",
        "modified_at",
        "updated_by",
    ]

    @display(header=True, description="Researcher")
    def display_researcher(self, obj: Researcher) -> list:
        """Return a display triple of [full name, position, initials] for the Researcher."""
        if obj.user:
            initials = "".join(
                n[0].upper()
                for n in [obj.user.first_name, obj.user.last_name]
                if n
            )
            return [
                obj.user.get_full_name(),
                obj.get_position_display() or "",
                initials or "?",
            ]
        return [str(obj), "", "?"]


class ProjectAdmin(PermissionBasedModelAdmin, ModelAdmin):
    """Admin for Project with Guardian permissions and member permission syncing."""

    save_on_top = True
    change_form_show_cancel_button = True
    compressed_fields = True
    warn_unsaved_form = True
    list_display = [
        "title",
        "label",
        "colored_status",
        "start_date",
        "public",
    ]
    search_fields = ["title", "label", "description"]
    readonly_fields = [
        "id",
        "created_at",
        "created_by",
        "modified_at",
        "updated_by",
    ]
    autocomplete_fields = [
        "principal_investigator",
        "associated_investigator",
        "research_group",
        "members",
    ]
    list_filter = [
        ("status", ChoicesDropdownFilter),
        ("start_date", RangeDateFilter),
    ]
    list_filter_sheet = False
    list_filter_submit = True
    inlines = [ProjectUserObjectPermissionInline]

    def save_related(
        self,
        request: HttpRequest,
        form: object,
        formsets: object,
        change: bool,
    ) -> None:
        """Save related objects then sync Guardian permissions for project members."""
        super().save_related(request, form, formsets, change)
        self._sync_member_permissions(form.instance)

    def _sync_member_permissions(self, project: object) -> None:
        """Sync Guardian object-permissions to match the current members M2M.

        Called after save_related so that project.members already reflects the
        new state saved by the form. Reads the old permission state from
        ProjectUserObjectPermission to compute the diff.
        """
        new_members = set(project.members.all())

        existing_user_ids = set(
            ProjectUserObjectPermission.objects.filter(
                content_object=project,
                permission__codename__in=_MEMBER_PERMS,
            ).values_list("user", flat=True),
        )
        existing_member_users = set(
            User.objects.filter(pk__in=existing_user_ids),
        )

        for user in new_members:
            for perm in _MEMBER_PERMS:
                assign_perm(perm, user, project)

        creator = project.created_by
        for user in existing_member_users - new_members:
            if user != creator:
                for perm in _MEMBER_PERMS:
                    remove_perm(perm, user, project)

    @display(
        label={
            "ACTIVE": "success",
            "COMPLETED": "info",
            "PAUSED": "warning",
            "CANCELLED": "danger",
        },
        description="Status",
    )
    def colored_status(self, obj: Project) -> str:
        """Return the project status string for the colored label display."""
        return obj.status

    fieldsets = (
        (
            "Project",
            {
                "classes": ["tab"],
                "fields": (
                    "id",
                    ("title", "label"),
                    "subtitle",
                    ("status", "public"),
                    ("start_date", "deadline"),
                    "parent",
                    ("created_by", "created_at"),
                    ("updated_by", "modified_at"),
                ),
            },
        ),
        (
            "Team",
            {
                "classes": ["tab"],
                "fields": (
                    "principal_investigator",
                    "associated_investigator",
                    "research_group",
                    "members",
                ),
            },
        ),
        (
            "Description",
            {
                "classes": ["tab"],
                "fields": ("description",),
            },
        ),
    )


# ---------------------------------------------------------------------------
# Django Auth — User and Group
# ---------------------------------------------------------------------------


class GroupAdmin(DjangoGroupAdmin, ModelAdmin):
    """Unfold-styled admin for Django's built-in Group model."""

    search_fields = ["name"]
    list_display = ["name"]
    filter_horizontal = ["permissions"]


class UserAdmin(DjangoUserAdmin, ModelAdmin):
    """Unfold-styled admin for Django's built-in User model."""

    compressed_fields = True
    change_form_show_cancel_button = True
    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    ]
    search_fields = ["username", "first_name", "last_name", "email"]
    readonly_fields = ["date_joined", "last_login"]
    autocomplete_fields = ["groups"]
    filter_horizontal = ["user_permissions"]
    fieldsets = (
        (
            "Account",
            {
                "classes": ["tab"],
                "fields": (
                    "username",
                    ("first_name", "last_name"),
                    "email",
                    ("is_active", "is_staff", "is_superuser"),
                    ("date_joined", "last_login"),
                ),
            },
        ),
        (
            "Password",
            {
                "classes": ["tab"],
                "fields": ("password",),
            },
        ),
        (
            "Groups",
            {
                "classes": ["tab"],
                "description": (
                    "Assign pre-built permission groups. "
                    "Use the management command 'create_permission_groups' to create them."
                ),
                "fields": ("groups",),
            },
        ),
        (
            "Individual Permissions",
            {
                "classes": ["tab"],
                "description": "Only use this for permissions not covered by a group.",
                "fields": ("user_permissions",),
            },
        ),
    )


admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)

# ---------------------------------------------------------------------------
# CGDB models
# ---------------------------------------------------------------------------

admin.site.register(ResearchGroup, ResearchGroupAdmin)
admin.site.register(Researcher, ResearcherAdmin)
admin.site.register(Project, ProjectAdmin)
