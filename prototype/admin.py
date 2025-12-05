from django.contrib import admin
from guardian.shortcuts import assign_perm
from unfold.admin import ModelAdmin, TabularInline

from .mixins import GuardianPermissionMixin
from .models import Project, ProjectUserObjectPermission, Researcher, ResearchGroup


class PermissionBasedModelAdmin(GuardianPermissionMixin, admin.ModelAdmin):
    """The base class inherits object-level permissions for data objects via Guardian.
    """


    def has_add_permission(self, request, obj=None):

        add_perm = f"{self.opts.app_label}.add_{self.opts.model_name}"
        return request.user.has_perm(add_perm, obj)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user

        super().save_model(request, obj, form, change)

        if not change and obj.pk:
            from django.db import transaction

            def assign_permissions():
                model_name = self.opts.model_name
                assign_perm(f"view_{model_name}", request.user, obj)
                assign_perm(f"change_{model_name}", request.user, obj)
                assign_perm(f"delete_{model_name}", request.user, obj)
                assign_perm(f"add_{model_name}", request.user, obj)

            transaction.on_commit(assign_permissions)


class ProjectUserObjectPermissionInline(TabularInline):
    model = ProjectUserObjectPermission
    extra = 0
    fields = ["user", "permission"]
    tab = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user", "permission")


class ResearchGroupAdmin(PermissionBasedModelAdmin, ModelAdmin):
    list_display = ["label", "head_of_group", "created_at"]
    search_fields = ["label"]
    list_filter = ["created_at"]
    readonly_fields = ["created_at", "created_by"]


class ResearcherAdmin(PermissionBasedModelAdmin, ModelAdmin):
    list_display = ["user", "academic_rank", "get_full_name"]
    search_fields = ["user__username", "user__first_name", "user__last_name"]
    list_filter = ["academic_rank"]

    def get_full_name(self, obj):
        return obj.user.get_full_name()

    get_full_name.short_description = "Full Name"


class ProjectAdmin(PermissionBasedModelAdmin, ModelAdmin):
    list_display = ["title", "label", "status", "start_date", "public"]
    search_fields = ["title", "label", "description"]
    list_filter = ["status", "public", "start_date", "created_at"]
    readonly_fields = ["created_at", "created_by"]
    filter_horizontal = [
        "principal_investigator",
        "associated_investigator",
        "research_group",
    ]
    inlines = [ProjectUserObjectPermissionInline]


# Register the models
admin.site.register(ResearchGroup, ResearchGroupAdmin)
admin.site.register(Researcher, ResearcherAdmin)
admin.site.register(Project, ProjectAdmin)
