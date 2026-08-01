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


def _sync_maintenance_run(
    context: RunStatusSensorContext, status: str
) -> None:
    """Write the given status onto the MaintenanceRun tagged on this Dagster run."""
    run_id = context.dagster_run.tags.get(_MAINTENANCE_RUN_TAG)
    if run_id is None:
        return

    from orchestration.models import MaintenanceRun

    updated = MaintenanceRun.objects.filter(pk=run_id).update(
        status=status, finished_at=datetime.now(UTC)
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
