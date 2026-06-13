"""Dagster maintenance jobs: backup, DuckDB export, and integrity check.

These are standalone @job definitions (not asset-based) so they run
headlessly via execute_in_process() without touching the existing asset graph.
"""

from __future__ import annotations

import gzip
import json
import os
import subprocess
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import django
from dagster import job, op

if TYPE_CHECKING:
    from django.db.models import QuerySet

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prototype.settings")
django.setup()

_BASE_CONFIG_SCHEMA = {"run_id": int, "output_dir": str}
_BACKUP_CONFIG_SCHEMA = {"run_id": int, "output_dir": str, "dump_format": str}

# ---------------------------------------------------------------------------
# backup_job
# ---------------------------------------------------------------------------


def _is_sqlite(engine: str) -> bool:
    engine_lower = engine.lower()
    return "sqlite" in engine_lower or "spatialite" in engine_lower


def _backup_sqlite(
    context,
    db: dict,
    output_dir: str,
    timestamp: str,
) -> Path:
    """Copy the SQLite file into a gzip-compressed backup."""
    import shutil

    db_path = Path(str(db["NAME"]))
    if not db_path.exists():
        msg = f"SQLite database file not found: {db_path}"
        raise FileNotFoundError(msg)

    output_path = Path(output_dir) / f"backup_{timestamp}.sqlite3.gz"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    context.log.info("Backing up SQLite database %s", db_path)
    with db_path.open("rb") as src, gzip.open(output_path, "wb") as dst:
        shutil.copyfileobj(src, dst)

    return output_path


_PG_FORMAT_FLAGS = {
    "custom": "-Fc",
    "plain": "-Fp",
}
_PG_FORMAT_EXTENSIONS = {
    "custom": ".dump.gz",
    "plain": ".sql.gz",
}


def _backup_postgres(
    context,
    db: dict,
    output_dir: str,
    timestamp: str,
    dump_format: str = "custom",
) -> Path:
    """Run pg_dump and gzip the output."""
    ext = _PG_FORMAT_EXTENSIONS.get(dump_format, ".dump.gz")
    output_path = Path(output_dir) / f"backup_{timestamp}{ext}"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PGPASSWORD"] = str(db.get("PASSWORD", ""))

    format_flag = _PG_FORMAT_FLAGS.get(dump_format, "-Fc")
    dump_cmd = [
        "pg_dump",
        "-h",
        str(db.get("HOST", "localhost")),
        "-p",
        str(db.get("PORT", 5432)),
        "-U",
        str(db.get("USER", "")),
        "--no-password",  # fail rather than prompt; password comes from PGPASSWORD
        format_flag,
        str(db["NAME"]),
    ]
    context.log.info(
        "Running pg_dump for database %s (format=%s)", db["NAME"], dump_format
    )

    proc = subprocess.run(  # noqa: S603 — dump_cmd built from settings, no user-controlled input
        dump_cmd,
        capture_output=True,
        env=env,
        check=True,
    )

    with gzip.open(output_path, "wb") as gz_file:
        gz_file.write(proc.stdout)

    return output_path


@op(config_schema=_BACKUP_CONFIG_SCHEMA)
def run_pg_dump(context) -> str:
    """Back up the configured database (SQLite copy or pg_dump) to output_dir."""
    from django.conf import settings

    db = settings.DATABASES["default"]
    engine: str = db.get("ENGINE", "")
    output_dir: str = context.op_config["output_dir"]
    dump_format: str = context.op_config.get("dump_format", "custom")
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    if _is_sqlite(engine):
        output_path = _backup_sqlite(context, db, output_dir, timestamp)
    else:
        output_path = _backup_postgres(
            context, db, output_dir, timestamp, dump_format
        )

    context.log.info(
        "Backup written to %s (%d bytes)",
        output_path,
        output_path.stat().st_size,
    )
    return str(output_path)


@job(name="backup_job")
def backup_job() -> None:
    """Dagster job that runs a database backup."""
    run_pg_dump()


# ---------------------------------------------------------------------------
# duckdb_export_job
# ---------------------------------------------------------------------------


def _get_queryset(model, cfg) -> QuerySet:
    """Return a values() queryset filtered to the configured fields."""
    if cfg.include_fields:
        return model.objects.values(*cfg.include_fields)
    if cfg.exclude_fields:
        fields = [
            f.name
            for f in model._meta.get_fields()
            if hasattr(f, "column") and f.name not in cfg.exclude_fields
        ]
        return model.objects.values(*fields)
    return model.objects.values()


def _coerce_df_columns(df) -> None:
    """Coerce non-serialisable column values (e.g. geometry WKB) to strings in-place."""
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(
                lambda v: (
                    str(v)
                    if v is not None
                    and not isinstance(v, (str, int, float, bool))
                    else v
                )
            )


def _export_model_table(conn, cfg, model, context) -> None:
    """Export one model's queryset to a DuckDB table; log and swallow errors."""
    import pandas as pd

    try:
        qs = _get_queryset(model, cfg)
        df = pd.DataFrame.from_records(list(qs))
        table_name = f"{cfg.app_label}__{cfg.model_name.lower()}"

        if df.empty:
            context.log.info("Table %s is empty, skipping", table_name)
            return

        _coerce_df_columns(df)
        conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")  # noqa: S608
        context.log.info("Exported %d rows to table %s", len(df), table_name)
    except Exception:  # noqa: BLE001
        context.log.error(
            "Failed to export %s.%s:\n%s",
            cfg.app_label,
            cfg.model_name,
            traceback.format_exc(),
        )


@op(config_schema=_BASE_CONFIG_SCHEMA)
def export_to_duckdb(context) -> str:
    """Export configured Django model tables to a DuckDB file."""
    import duckdb
    from django.apps import apps

    from orchestration.models import DuckDBTableConfig

    output_dir: str = context.op_config["output_dir"]
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_path = Path(output_dir) / f"cgdb_{timestamp}.duckdb"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(output_path))
    for cfg in DuckDBTableConfig.objects.exclude(role="exclude"):
        try:
            model = apps.get_model(cfg.app_label, cfg.model_name)
        except LookupError:
            context.log.warning(
                "Model %s.%s not found, skipping",
                cfg.app_label,
                cfg.model_name,
            )
            continue
        _export_model_table(conn, cfg, model, context)

    conn.close()
    context.log.info("DuckDB export written to %s", output_path)
    return str(output_path)


@job(name="duckdb_export_job")
def duckdb_export_job() -> None:
    """Dagster job that exports Django models to DuckDB."""
    export_to_duckdb()


# ---------------------------------------------------------------------------
# integrity_check_job
# ---------------------------------------------------------------------------


@op(config_schema=_BASE_CONFIG_SCHEMA)
def run_integrity_checks(context) -> str:
    """Run data integrity checks and write a JSON report to output_dir."""
    from django.apps import apps
    from django.contrib.contenttypes.models import ContentType
    from guardian.models import UserObjectPermission

    from orchestration.models import IntegrityIssue, MaintenanceRun

    output_dir: str = context.op_config["output_dir"]
    run_id: int = context.op_config["run_id"]
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"integrity_{timestamp}.json"
    output_path = Path(output_dir) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    run = MaintenanceRun.objects.get(pk=run_id)
    run.issues.all().delete()  # idempotent: clear any previous issues for this run

    results: dict = {}

    # Check 1: Orphan Samples (sample with no location)
    Sample = apps.get_model("field_data", "Sample")
    orphan_ids = list(
        Sample.objects.filter(location__isnull=True).values_list(
            "id", "identifier"
        )
    )
    results["orphan_samples"] = {"count": len(orphan_ids), "ids": orphan_ids}
    context.log.info("Orphan samples (no location): %d", len(orphan_ids))
    for sid, identifier in orphan_ids:
        IntegrityIssue.objects.create(
            run=run,
            check_type="orphan_samples",
            object_id=sid,
            description=f"Sample '{identifier}' (id={sid}) has no location assigned.",
        )

    # Check 2: Locations missing geometry
    Location = apps.get_model("field_data", "Location")
    missing_geom = list(
        Location.objects.filter(location__isnull=True).values_list(
            "id", flat=True
        )
    )
    results["missing_geometries"] = {
        "count": len(missing_geom),
        "ids": missing_geom,
    }
    context.log.info("Locations missing geometry: %d", len(missing_geom))
    for lid in missing_geom:
        IntegrityIssue.objects.create(
            run=run,
            check_type="missing_geometries",
            object_id=lid,
            description=f"Location id={lid} has no geometry (location field is null).",
        )

    # Check 3: Guardian permission count for MaintenanceRun objects
    ct = ContentType.objects.get_for_model(MaintenanceRun)
    guardian_count = (
        UserObjectPermission.objects.filter(content_type=ct)
        .values("object_pk")
        .distinct()
        .count()
    )
    results["guardian_maintenance_permissions"] = {
        "object_count": guardian_count
    }
    context.log.info(
        "MaintenanceRun objects with guardian permissions: %d", guardian_count
    )
    IntegrityIssue.objects.create(
        run=run,
        check_type="guardian_maintenance_permissions",
        object_id=None,
        description=(
            f"{guardian_count} MaintenanceRun object(s) have"
            " guardian object permissions assigned."
        ),
    )

    output_path.write_text(json.dumps(results, indent=2, default=str))
    context.log.info("Integrity report written to %s", output_path)
    return str(output_path)


@job(name="integrity_check_job")
def integrity_check_job() -> None:
    """Dagster job that runs integrity checks and produces a JSON report."""
    run_integrity_checks()


# ---------------------------------------------------------------------------
# Job dispatcher
# ---------------------------------------------------------------------------

_JOB_MAP = {
    "backup": backup_job,
    "duckdb": duckdb_export_job,
    "integrity": integrity_check_job,
}


def get_job_for_type(job_type: str) -> object:
    """Return the Dagster JobDefinition for the given job_type key."""
    if job_type not in _JOB_MAP:
        msg = f"Unknown maintenance job type: {job_type!r}"
        raise ValueError(msg)
    return _JOB_MAP[job_type]
