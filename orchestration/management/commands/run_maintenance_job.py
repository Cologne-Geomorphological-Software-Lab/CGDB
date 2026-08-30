"""Management command: run a maintenance job headlessly via Dagster.

Manual fallback only. The admin's "Trigger selected maintenance job(s)"
action no longer calls this command — it launches the run directly via
`dagster job launch` and DefaultRunLauncher (see
orchestration.admin._submit_maintenance_run; no run_coordinator is
configured in dagster.yaml, so this isn't a queue), and status/log/
result_file are now written by the ops themselves plus the run-status
sensors in orchestration/dagster_home/sensors.py, not by this command.
Kept as a synchronous, in-process way to run a job by hand (e.g. if the
daemon is unavailable) without needing a Dagster CLI/daemon round-trip.
"""

from __future__ import annotations

import os
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    """Run a Dagster maintenance job synchronously, in-process (manual fallback)."""

    help = (
        "Run a Dagster maintenance job synchronously, in-process, and update "
        "the MaintenanceRun record directly. Manual fallback only — the admin "
        "action submits to the dagster-daemon queue instead (see "
        "orchestration.admin._submit_maintenance_run)."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Register job_type positional arg and --run-id option."""
        parser.add_argument(
            "job_type",
            choices=["backup", "duckdb", "integrity"],
            help="Type of maintenance job to run.",
        )
        parser.add_argument(
            "--run-id",
            type=int,
            required=True,
            help="Primary key of the MaintenanceRun instance to update.",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Execute the maintenance job and update the run record."""
        from orchestration.models import MaintenanceRun

        job_type = cast("str", options["job_type"])
        run_pk = cast("int", options["run_id"])

        try:
            run = MaintenanceRun.objects.get(pk=run_pk)
        except MaintenanceRun.DoesNotExist as exc:
            msg = f"MaintenanceRun with pk={run_pk} does not exist."
            raise CommandError(msg) from exc

        run.status = "running"
        run.started_at = datetime.now(UTC)
        run.save(update_fields=["status", "started_at"])

        output_dir = Path(settings.MEDIA_ROOT) / "maintenance"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # DAGSTER_HOME: where dagster.yaml lives (project source, read-only).
            # Run storage itself is PostgreSQL (DAGSTER_PG_* env vars, see
            # dagster.yaml) — must already be set in the environment.
            dagster_home = str(
                settings.BASE_DIR / "orchestration" / "dagster_home"
            )
            os.environ.setdefault("DAGSTER_HOME", dagster_home)

            from dagster import DagsterInstance

            from orchestration.dagster_home.maintenance_jobs import (
                OP_NAME_BY_JOB_TYPE,
                get_job_for_type,
            )

            instance = DagsterInstance.get()
            job_def = get_job_for_type(job_type)

            op_name = OP_NAME_BY_JOB_TYPE[job_type]

            op_config: dict = {
                "run_id": run.pk,
                "output_dir": str(output_dir),
            }
            if job_type == "backup":
                op_config["dump_format"] = run.dump_format or "custom"

            result = job_def.execute_in_process(
                run_config={"ops": {op_name: {"config": op_config}}},
                instance=instance,
            )

            log_lines = []
            for e in result.all_events:
                msg = getattr(e, "message", None)
                if msg:
                    level = getattr(e, "level", None)
                    prefix = level.value if level is not None else "INFO"
                    log_lines.append(f"{prefix}: {msg}")
            run.log = "\n".join(log_lines)

            if result.success:
                output_file = _find_latest_output(job_type, output_dir)
                if output_file:
                    run.result_file.name = f"maintenance/{output_file.name}"
                run.status = "success"
            else:
                run.status = "failed"

        except Exception:
            run.status = "failed"
            run.log = traceback.format_exc()

        finally:
            run.finished_at = datetime.now(UTC)
            run.save(
                update_fields=["status", "finished_at", "log", "result_file"]
            )


def _find_latest_output(job_type: str, output_dir: Path) -> Path | None:
    """Return the most recently created output file matching the job type's prefix."""
    prefix_map = {
        "backup": "backup_",
        "duckdb": "cgdb_",
        "integrity": "integrity_",
    }
    prefix = prefix_map[job_type]
    candidates = sorted(
        output_dir.glob(f"{prefix}*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None
