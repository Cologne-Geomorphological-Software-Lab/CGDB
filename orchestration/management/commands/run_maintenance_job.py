"""Management command: run a maintenance job headlessly via Dagster."""

from __future__ import annotations

import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    """Run a Dagster maintenance job headlessly and update the MaintenanceRun record."""

    help = "Run a Dagster maintenance job headlessly and update the MaintenanceRun record."

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

        job_type: str = options["job_type"]
        run_pk: int = options["run_id"]

        try:
            run = MaintenanceRun.objects.get(pk=run_pk)
        except MaintenanceRun.DoesNotExist as exc:
            msg = f"MaintenanceRun with pk={run_pk} does not exist."
            raise CommandError(msg) from exc

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        run.save(update_fields=["status", "started_at"])

        output_dir = Path(settings.MEDIA_ROOT) / "maintenance"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Set DAGSTER_HOME before any Dagster import so DagsterInstance.get()
            # picks up dagster.yaml from the correct directory.
            dagster_home = str(
                settings.BASE_DIR / "orchestration" / "dagster_home"
            )
            os.environ.setdefault("DAGSTER_HOME", dagster_home)

            from dagster import DagsterInstance

            from orchestration.dagster_home.maintenance_jobs import (
                get_job_for_type,
            )

            instance = DagsterInstance.get()
            job_def = get_job_for_type(job_type)

            op_name = {
                "backup": "run_pg_dump",
                "duckdb": "export_to_duckdb",
                "integrity": "run_integrity_checks",
            }[job_type]

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
            run.finished_at = datetime.now(timezone.utc)
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
