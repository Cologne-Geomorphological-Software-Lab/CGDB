from django.contrib import admin
from guardian.shortcuts import assign_perm
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .mixins import GuardianPermissionMixin
from .models import Project, ProjectUserObjectPermission, Researcher, ResearchGroup


class PermissionBasedModelAdmin(GuardianPermissionMixin, admin.ModelAdmin):
    """The base class inherits object-level permissions for data objects via Guardian."""

    def has_add_permission(self, request, obj=None):

        add_perm = f"{self.opts.app_label}.add_{self.opts.model_name}"
        return request.user.has_perm(add_perm, obj)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user

        super().save_model(request, obj, form, change)

        # view/change/delete are handled by the post_save signal in prototype/signals.py.
        # Only add_* is assigned here as the signal does not cover it.
        if not change and obj.pk:
            from django.db import transaction

            def assign_add_permission() -> None:
                assign_perm(f"add_{self.opts.model_name}", request.user, obj)

            transaction.on_commit(assign_add_permission)


class ProjectUserObjectPermissionInline(TabularInline):
    model = ProjectUserObjectPermission
    extra = 0
    fields = ["user", "permission"]
    tab = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user", "permission")


class ResearchGroupAdmin(PermissionBasedModelAdmin, ModelAdmin):
    change_form_show_cancel_button = True
    list_display = ["label", "head_of_group", "created_at"]
    search_fields = ["label"]
    list_filter = ["created_at"]
    readonly_fields = ["created_at", "created_by", "modified_at", "updated_by"]


class ResearcherAdmin(PermissionBasedModelAdmin, ModelAdmin):
    change_form_show_cancel_button = True
    list_display = ["user", "academic_rank", "display_researcher"]
    search_fields = ["user__username", "user__first_name", "user__last_name"]
    list_filter = ["academic_rank"]
    readonly_fields = ["created_at", "created_by", "modified_at", "updated_by"]

    @display(header=True, description="Researcher")
    def display_researcher(self, obj):
        if obj.user:
            initials = "".join(
                n[0].upper() for n in [obj.user.first_name, obj.user.last_name] if n
            )
            return [obj.user.get_full_name(), obj.get_position_display() or "", initials or "?"]
        return [str(obj), "", "?"]


class ProjectAdmin(PermissionBasedModelAdmin, ModelAdmin):
    save_on_top = True
    change_form_show_cancel_button = True
    list_display = ["title", "label", "colored_status", "start_date", "public"]
    search_fields = ["title", "label", "description"]
    list_filter = ["status", "public", "start_date", "created_at"]
    readonly_fields = ["created_at", "created_by", "modified_at", "updated_by"]
    filter_horizontal = [
        "principal_investigator",
        "associated_investigator",
        "research_group",
    ]
    inlines = [ProjectUserObjectPermissionInline]

    @display(
        label={"ACTIVE": "success", "COMPLETED": "info", "PAUSED": "warning", "CANCELLED": "danger"},
        description="Status",
    )
    def colored_status(self, obj):
        return obj.status


# Register the models
admin.site.register(ResearchGroup, ResearchGroupAdmin)
admin.site.register(Researcher, ResearcherAdmin)
admin.site.register(Project, ProjectAdmin)
