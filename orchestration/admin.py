"""Admin interface for maintenance runs and DuckDB table configuration."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

from django.contrib import admin, messages
from django.db.models import Count
from django.http import FileResponse, Http404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from prototype.mixins import (
    AUDIT_READONLY_FIELDS,
    CreatedUpdatedModelAdminMixin,
)

from .models import DuckDBTableConfig, IntegrityIssue, MaintenanceRun

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.forms import ModelForm
    from django.urls import URLPattern

    from prototype.mixins import AuthenticatedHttpRequest

# Maps check_type to (app_label, model_name) for admin change-page links
_CHECK_TYPE_MODEL_MAP: dict[str, tuple[str, str]] = {
    "orphan_samples": ("field_data", "sample"),
    "missing_geometries": ("field_data", "location"),
}

# Maps check_type to a filtered changelist URL suffix
_CHECK_TYPE_CHANGELIST_FILTER: dict[str, str] = {
    "orphan_samples": "location__isnull=True",
    "missing_geometries": "location__isnull=True",
}

# Human-readable labels per check type for the summary column
_CHECK_TYPE_LABELS: dict[str, str] = {
    "orphan_samples": "Orphans",
    "missing_geometries": "Missing geometry",
    "guardian_maintenance_permissions": "Guardian",
}


def _submit_maintenance_run(run: MaintenanceRun) -> None:
    """Launch a maintenance job via the dagster-daemon's DefaultRunLauncher.

    Shells out to `dagster job launch` rather than calling
    DagsterInstance.submit_run() directly: submit_run() requires a real
    BaseWorkspaceRequestContext (a loaded code location), which is too
    heavyweight to construct inline in a Django admin request — the CLI
    resolves the workspace itself.

    tech debt O10: dagster.yaml configures no run_coordinator, only
    run_launcher: DefaultRunLauncher - runs are launched directly, not
    queued (a prior version of this docstring incorrectly claimed
    QueuedRunCoordinator was configured; it isn't, deliberately - see
    dagster.yaml's own comment on why concurrency-limited queueing isn't
    needed yet). This call is still non-blocking on the job's actual
    execution because DefaultRunLauncher itself launches the run in a
    separate process and returns, not because of any queue.

    Unlike the old detached subprocess.Popen (which could silently fail to
    even start), this call is checked — a submission failure (bad config,
    unreachable Postgres run-storage, code-location import error) raises
    CalledProcessError with the CLI's stderr, which the caller surfaces to
    the admin instead of claiming "dispatched" regardless.
    """
    from django.conf import settings

    # tech debt O5: job_type -> op_name/job_name lives in maintenance_jobs.py
    # (single source of truth - see its OP_NAME_BY_JOB_TYPE/JOB_NAME_BY_JOB_TYPE
    # docstring). Imported lazily, matching run_maintenance_job.py's own
    # deferred import of that module - it calls django.setup() at import
    # time, which admin.py's module-load time is the wrong place for.
    from orchestration.dagster_home.maintenance_jobs import (
        JOB_NAME_BY_JOB_TYPE,
        OP_NAME_BY_JOB_TYPE,
    )

    dagster_home = str(settings.BASE_DIR / "orchestration" / "dagster_home")
    env = os.environ.copy()
    env.setdefault("DAGSTER_HOME", dagster_home)

    output_dir = Path(settings.MEDIA_ROOT) / "maintenance"
    op_config: dict = {"run_id": run.pk, "output_dir": str(output_dir)}
    if run.job_type == "backup":
        op_config["dump_format"] = run.dump_format or "custom"

    cmd = [
        sys.executable,
        "-m",
        "dagster",
        "job",
        "launch",
        "-m",
        "orchestration.dagster_home.repository",
        "-j",
        JOB_NAME_BY_JOB_TYPE[run.job_type],
        "--config-json",
        json.dumps(
            {"ops": {OP_NAME_BY_JOB_TYPE[run.job_type]: {"config": op_config}}}
        ),
        "--tags",
        json.dumps({"maintenance_run_id": str(run.pk)}),
    ]
    subprocess.run(  # noqa: S603 — cmd is built from static parts and this run's own pk/dump_format, no external user input
        cmd,
        env=env,
        check=True,
        capture_output=True,
        timeout=60,
    )


def _mark_run_failed(run: MaintenanceRun, log: str) -> None:
    """Record a maintenance run as failed with the given log text."""
    run.status = "failed"
    run.log = log
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "log", "finished_at"])


def _run_one_maintenance_job(run: MaintenanceRun) -> bool:
    """Mark run running, submit it, and record success/failure. Returns True if triggered."""
    run.status = "running"
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at"])
    try:
        _submit_maintenance_run(run)
    except (subprocess.SubprocessError, OSError) as exc:
        # SubprocessError covers CalledProcessError/TimeoutExpired
        # (submission ran but failed/hung); OSError covers the subprocess
        # never starting at all (e.g. FileNotFoundError, PermissionError)
        # -- without this broader catch, that case would crash the whole
        # admin action instead of marking just this run as failed and
        # continuing with the rest.
        stderr = getattr(exc, "stderr", None) or b""
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        _mark_run_failed(run, stderr or str(exc))
        return False
    except Exception:  # noqa: BLE001
        # tech debt O7: anything unanticipated (e.g. a bad job_type, a
        # JSON-serialization bug) must not escape this loop either - the
        # same "one run doesn't fail the whole selection" guarantee as the
        # SubprocessError/OSError case above, just for the errors we
        # didn't specifically expect. Marked as failed with the full
        # traceback logged (not just str(exc)) since these are, by
        # definition, unanticipated.
        _mark_run_failed(run, traceback.format_exc())
        return False
    return True


class IntegrityIssueInline(TabularInline):
    """Read-only inline showing integrity issues found during a run."""

    model = IntegrityIssue
    fields = ["check_type", "description", "admin_link"]
    readonly_fields = ["check_type", "description", "admin_link"]
    extra = 0
    can_delete = False

    def has_add_permission(
        self, _request: AuthenticatedHttpRequest, _obj: object = None
    ) -> bool:
        """Disallow adding issues manually."""
        return False

    @display(description="Object")
    def admin_link(self, obj: IntegrityIssue) -> str:
        """Return an admin change-page link for the affected object, if applicable."""
        if obj.object_id is None:
            return "—"
        entry = _CHECK_TYPE_MODEL_MAP.get(obj.check_type)
        if entry is None:
            return str(obj.object_id)
        app_label, model_name = entry
        url = reverse(
            f"admin:{app_label}_{model_name}_change", args=[obj.object_id]
        )
        return format_html('<a href="{}">View →</a>', url)


@admin.register(MaintenanceRun)
class MaintenanceRunAdmin(CreatedUpdatedModelAdminMixin, ModelAdmin):
    """Admin for the MaintenanceRun model — superuser access only."""

    list_fullwidth = True
    list_display = [
        "job_type_display",
        "dump_format_display",
        "status_display",
        "triggered_by",
        "started_at",
        "finished_at",
        "issues_summary",
        "download_link",
    ]
    readonly_fields = [
        "id",
        "status",
        "triggered_by",
        "started_at",
        "finished_at",
        "log",
        "result_file",
        "download_link",
        *AUDIT_READONLY_FIELDS,
    ]
    list_filter = ["job_type", "status"]
    actions = ["trigger_maintenance_job"]
    inlines = [IntegrityIssueInline]

    # ------------------------------------------------------------------
    # Permission lockdown: superuser only
    # ------------------------------------------------------------------

    def has_module_perms(self, request: AuthenticatedHttpRequest) -> bool:
        """Grant module-level access to superusers only."""
        return request.user.is_superuser

    def has_add_permission(self, request: AuthenticatedHttpRequest) -> bool:
        """Grant add permission to superusers only."""
        return request.user.is_superuser

    def has_change_permission(
        self, request: AuthenticatedHttpRequest, _obj: object = None
    ) -> bool:
        """Grant change permission to superusers only."""
        return request.user.is_superuser

    def has_delete_permission(
        self, request: AuthenticatedHttpRequest, _obj: object = None
    ) -> bool:
        """Grant delete permission to superusers only."""
        return request.user.is_superuser

    def has_view_permission(
        self, request: AuthenticatedHttpRequest, _obj: object = None
    ) -> bool:
        """Grant view permission to superusers only."""
        return request.user.is_superuser

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    @display(description="Job Type")
    def job_type_display(self, obj: MaintenanceRun) -> str:
        """Return the human-readable job type label."""
        return obj.get_job_type_display()  # pyright: ignore[reportAttributeAccessIssue]  # Django-generated choices-field accessor; no mypy-plugin support in basedpyright

    @display(description="Dump Format")
    def dump_format_display(self, obj: MaintenanceRun) -> str:
        """Return the dump format label, or a dash for non-backup jobs."""
        if obj.job_type != "backup":
            return "—"
        return obj.get_dump_format_display()  # pyright: ignore[reportAttributeAccessIssue]  # Django-generated choices-field accessor; no mypy-plugin support in basedpyright

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

    @display(description="Issues")
    def issues_summary(self, obj: MaintenanceRun) -> str:
        """Return per-check-type counts with links to filtered changelists."""
        if obj.job_type != "integrity" or obj.status != "success":
            return "—"

        counts: dict[str, int] = {
            r["check_type"]: r["n"]
            for r in obj.issues.values(  # pyright: ignore[reportAttributeAccessIssue]  # reverse FK related_name accessor; no mypy-plugin support in basedpyright
                "check_type"
            ).annotate(n=Count("id"))
        }

        parts: list[str] = []
        for check_type, label in _CHECK_TYPE_LABELS.items():
            n = counts.get(check_type, 0)
            filter_suffix = _CHECK_TYPE_CHANGELIST_FILTER.get(check_type)
            model_entry = _CHECK_TYPE_MODEL_MAP.get(check_type)
            if filter_suffix and model_entry:
                app_label, model_name = model_entry
                url = (
                    reverse(f"admin:{app_label}_{model_name}_changelist")
                    + f"?{filter_suffix}"
                )
                parts.append(
                    format_html('<a href="{}">{}: {}</a>', url, label, n)
                )
            else:
                parts.append(format_html("{}: {}", label, n))

        return format_html(" · ".join(["{}"] * len(parts)), *parts)

    @display(description="Download")
    def download_link(self, obj: MaintenanceRun) -> str:
        """Return an HTML download link when a result file is attached.

        Routed through `download_result` rather than `obj.result_file.url`
        directly — in production Django doesn't serve MEDIA_URL at all (see
        prototype/urls.py), so a raw `.url` link relies entirely on the
        reverse proxy happening to gate /media/, which nothing enforces.
        Result files are full database backups; this must stay superuser-only
        regardless of how the proxy is configured.
        """
        if obj.result_file:
            url = reverse(
                "admin:orchestration_maintenancerun_download", args=[obj.pk]
            )
            return format_html('<a href="{}" download>Download</a>', url)
        return "—"

    def get_urls(self) -> list[URLPattern]:
        """Add a superuser-gated download route alongside the default admin URLs."""
        custom_urls = [
            path(
                "<int:object_id>/download/",
                self.admin_site.admin_view(self.download_result),
                name="orchestration_maintenancerun_download",
            ),
        ]
        return custom_urls + super().get_urls()

    def download_result(
        self, request: AuthenticatedHttpRequest, object_id: int
    ) -> FileResponse:
        """Stream a maintenance run's result file, superuser-only.

        `admin_view()` already enforces staff-login; `has_view_permission`
        above restricts the changelist/changeform to superusers, but that
        check must be repeated here explicitly since this is a separate
        view, not covered by ModelAdmin's own permission plumbing.
        """
        if not request.user.is_superuser:
            raise Http404
        run = self.get_object(request, str(object_id))
        if run is None or not run.result_file:
            raise Http404
        filename = run.result_file.name.rsplit("/", 1)[-1]
        return FileResponse(
            run.result_file.open("rb"), as_attachment=True, filename=filename
        )

    # ------------------------------------------------------------------
    # Admin action
    # ------------------------------------------------------------------

    @admin.action(description="Trigger selected maintenance job(s)")
    def trigger_maintenance_job(
        self, request: AuthenticatedHttpRequest, queryset: QuerySet
    ) -> None:
        """Launch pending runs directly via the dagster-daemon's DefaultRunLauncher."""
        if not request.user.is_superuser:
            self.message_user(
                request,
                "Only superusers can trigger maintenance jobs.",
                messages.ERROR,
            )
            return

        results = [
            _run_one_maintenance_job(run)
            for run in queryset.filter(status="pending")
        ]
        triggered = sum(results)
        failed = len(results) - triggered
        self._report_trigger_results(request, triggered, failed)

    def _report_trigger_results(
        self, request: AuthenticatedHttpRequest, triggered: int, failed: int
    ) -> None:
        """Summarize a trigger_maintenance_job run as one or more admin messages."""
        if triggered:
            self.message_user(
                request,
                f"{triggered} maintenance job(s) submitted to the dagster queue.",
                messages.SUCCESS,
            )
        if failed:
            self.message_user(
                request,
                f"{failed} maintenance job(s) failed to submit — see their log field.",
                messages.ERROR,
            )
        if not triggered and not failed:
            self.message_user(
                request,
                "No pending runs in selection — only pending runs can be triggered.",
                messages.WARNING,
            )

    def save_model(
        self,
        request: AuthenticatedHttpRequest,
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

    list_fullwidth = True
    list_display = ["app_label", "model_name", "role"]
    list_filter = ["role", "app_label"]
    list_editable = ["role"]
    search_fields = ["app_label", "model_name"]
    ordering = ["app_label", "model_name"]
    readonly_fields = AUDIT_READONLY_FIELDS

    # ------------------------------------------------------------------
    # Permission lockdown: superuser only
    # ------------------------------------------------------------------

    def has_module_perms(self, request: AuthenticatedHttpRequest) -> bool:
        """Grant module-level access to superusers only."""
        return request.user.is_superuser

    def has_add_permission(self, request: AuthenticatedHttpRequest) -> bool:
        """Grant add permission to superusers only."""
        return request.user.is_superuser

    def has_change_permission(
        self, request: AuthenticatedHttpRequest, _obj: object = None
    ) -> bool:
        """Grant change permission to superusers only."""
        return request.user.is_superuser

    def has_delete_permission(
        self, request: AuthenticatedHttpRequest, _obj: object = None
    ) -> bool:
        """Grant delete permission to superusers only."""
        return request.user.is_superuser

    def has_view_permission(
        self, request: AuthenticatedHttpRequest, _obj: object = None
    ) -> bool:
        """Grant view permission to superusers only."""
        return request.user.is_superuser
