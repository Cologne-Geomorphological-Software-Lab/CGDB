"""Admin interface for maintenance runs and DuckDB table configuration."""

from __future__ import annotations

import platform
import subprocess
import sys
from typing import TYPE_CHECKING

from django.contrib import admin, messages
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from prototype.mixins import CreatedUpdatedModelAdminMixin

from .models import DuckDBTableConfig, MaintenanceRun

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.forms import ModelForm
    from django.http import HttpRequest


def _fire_maintenance_subprocess(run: MaintenanceRun) -> None:
    """Launch manage.py run_maintenance_job as a detached background process."""
    from django.conf import settings

    manage_py = str(settings.BASE_DIR / "manage.py")
    cmd = [
        sys.executable,
        manage_py,
        "run_maintenance_job",
        run.job_type,
        "--run-id",
        str(run.pk),
    ]

    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if platform.system() == "Windows":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    else:
        kwargs["start_new_session"] = True
        kwargs["close_fds"] = True

    subprocess.Popen(cmd, **kwargs)  # noqa: S603 — cmd is fully static; no user-controlled input


@admin.register(MaintenanceRun)
class MaintenanceRunAdmin(CreatedUpdatedModelAdminMixin, ModelAdmin):
    """Admin for the MaintenanceRun model — superuser access only."""

    list_display = [
        "job_type_display",
        "dump_format_display",
        "status_display",
        "triggered_by",
        "started_at",
        "finished_at",
        "download_link",
    ]
    readonly_fields = [
        "id",
        "status",
        "started_at",
        "finished_at",
        "log",
        "result_file",
        "download_link",
        "created_at",
        "created_by",
        "modified_at",
        "updated_by",
    ]
    list_filter = ["job_type", "status"]
    actions = ["trigger_maintenance_job"]

    # ------------------------------------------------------------------
    # Permission lockdown: superuser only
    # ------------------------------------------------------------------

    def has_module_perms(self, request: HttpRequest) -> bool:
        """Grant module-level access to superusers only."""
        return request.user.is_superuser

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Grant add permission to superusers only."""
        return request.user.is_superuser

    def has_change_permission(
        self, request: HttpRequest, _obj: object = None
    ) -> bool:
        """Grant change permission to superusers only."""
        return request.user.is_superuser

    def has_delete_permission(
        self, request: HttpRequest, _obj: object = None
    ) -> bool:
        """Grant delete permission to superusers only."""
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, _obj: object = None
    ) -> bool:
        """Grant view permission to superusers only."""
        return request.user.is_superuser

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    @display(description="Job Type")
    def job_type_display(self, obj: MaintenanceRun) -> str:
        """Return the human-readable job type label."""
        return obj.get_job_type_display()

    @display(description="Dump Format")
    def dump_format_display(self, obj: MaintenanceRun) -> str:
        """Return the dump format label, or a dash for non-backup jobs."""
        if obj.job_type != "backup":
            return "—"
        return obj.get_dump_format_display()

    @display(
        label={
            "pending": "warning",
            "running": "info",
            "success": "success",
            "failed": "danger",
        },
        description="Status",
    )
    def status_display(self, obj: MaintenanceRun) -> str:
        """Return the status value used for the colored label badge."""
        return obj.status

    @display(description="Download")
    def download_link(self, obj: MaintenanceRun) -> str:
        """Return an HTML download link when a result file is attached."""
        if obj.result_file:
            return format_html(
                '<a href="{}" download>Download</a>', obj.result_file.url
            )
        return "—"

    # ------------------------------------------------------------------
    # Admin action
    # ------------------------------------------------------------------

    @admin.action(description="Trigger selected maintenance job(s)")
    def trigger_maintenance_job(
        self, request: HttpRequest, queryset: QuerySet
    ) -> None:
        """Dispatch pending runs as background subprocesses."""
        if not request.user.is_superuser:
            self.message_user(
                request,
                "Only superusers can trigger maintenance jobs.",
                messages.ERROR,
            )
            return

        triggered = 0
        for run in queryset.filter(status="pending"):
            _fire_maintenance_subprocess(run)
            triggered += 1

        if triggered:
            self.message_user(
                request,
                f"{triggered} maintenance job(s) dispatched in background.",
                messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                "No pending runs in selection — only pending runs can be triggered.",
                messages.WARNING,
            )

    def save_model(
        self,
        request: HttpRequest,
        obj: MaintenanceRun,
        form: ModelForm,
        change: bool,
    ) -> None:
        """Set triggered_by to the current user on creation."""
        if not obj.pk:
            obj.triggered_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DuckDBTableConfig)
class DuckDBTableConfigAdmin(CreatedUpdatedModelAdminMixin, ModelAdmin):
    """Admin for the DuckDBTableConfig model — superuser access only."""

    list_display = ["app_label", "model_name", "role"]
    list_filter = ["role", "app_label"]
    list_editable = ["role"]
    search_fields = ["app_label", "model_name"]
    ordering = ["app_label", "model_name"]
    readonly_fields = ["created_at", "created_by", "modified_at", "updated_by"]

    # ------------------------------------------------------------------
    # Permission lockdown: superuser only
    # ------------------------------------------------------------------

    def has_module_perms(self, request: HttpRequest) -> bool:
        """Grant module-level access to superusers only."""
        return request.user.is_superuser

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Grant add permission to superusers only."""
        return request.user.is_superuser

    def has_change_permission(
        self, request: HttpRequest, _obj: object = None
    ) -> bool:
        """Grant change permission to superusers only."""
        return request.user.is_superuser

    def has_delete_permission(
        self, request: HttpRequest, _obj: object = None
    ) -> bool:
        """Grant delete permission to superusers only."""
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, _obj: object = None
    ) -> bool:
        """Grant view permission to superusers only."""
        return request.user.is_superuser
