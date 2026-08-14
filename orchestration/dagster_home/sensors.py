"""Run-status sensors that sync MaintenanceRun with the real Dagster run status.

Runs submitted via `dagster job launch` (see orchestration/admin.py's
_submit_maintenance_run) are tagged with maintenance_run_id. These sensors
watch for SUCCESS/FAILURE on any run carrying that tag and write the result
back onto the corresponding MaintenanceRun row — the bookkeeping that used
to live in the now-retired run_maintenance_job management command, which
had first-hand knowledge of the run because it executed it in-process.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import django
from dagster import (
    DagsterRunStatus,
    DefaultSensorStatus,
    RunStatusSensorContext,
    run_status_sensor,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prototype.settings")
django.setup()

_MAINTENANCE_RUN_TAG = "maintenance_run_id"


_LOG_CHAR_LIMIT = 20_000


def _summarize_events(context: RunStatusSensorContext) -> str:
    """Build a MaintenanceRun.log-style summary from Dagster's event log.

    Mirrors the "LEVEL: message" format the retired run_maintenance_job
    command produced from result.all_events, so admins see the same shape
    of log regardless of whether the daemon or the manual fallback command
    executed the job.
    """
    entries = context.instance.all_logs(context.dagster_run.run_id)
    log_lines = [
        f"{entry.level}: {entry.message}" for entry in entries if entry.message
    ]
    summary = "\n".join(log_lines)
    if len(summary) > _LOG_CHAR_LIMIT:
        summary = summary[-_LOG_CHAR_LIMIT:]
    return summary


def _sync_maintenance_run(
    context: RunStatusSensorContext, status: str
) -> None:
    """Write the given status and a log summary onto the tagged MaintenanceRun."""
    run_id = context.dagster_run.tags.get(_MAINTENANCE_RUN_TAG)
    if run_id is None:
        return

    from orchestration.models import MaintenanceRun

    updated = MaintenanceRun.objects.filter(pk=run_id).update(
        status=status,
        finished_at=datetime.now(UTC),
        log=_summarize_events(context),
    )
    if not updated:
        context.log.warning(
            "run-status sensor: MaintenanceRun pk=%s not found (dagster run %s)",
            run_id,
            context.dagster_run.run_id,
        )


@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    default_status=DefaultSensorStatus.RUNNING,
)
def maintenance_run_success_sensor(context: RunStatusSensorContext) -> None:
    """Mark the tagged MaintenanceRun as successful."""
    _sync_maintenance_run(context, status="success")


@run_status_sensor(
    run_status=DagsterRunStatus.FAILURE,
    default_status=DefaultSensorStatus.RUNNING,
)
def maintenance_run_failure_sensor(context: RunStatusSensorContext) -> None:
    """Mark the tagged MaintenanceRun as failed."""
    _sync_maintenance_run(context, status="failed")
