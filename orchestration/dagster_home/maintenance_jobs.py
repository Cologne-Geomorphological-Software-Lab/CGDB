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
    from collections.abc import Callable

    import duckdb
    import pandas as pd
    from dagster import JobDefinition, OpExecutionContext
    from django.db.models import Model, QuerySet

    from orchestration.models import DuckDBTableConfig

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prototype.settings")
django.setup()

_BASE_CONFIG_SCHEMA = {"run_id": int, "output_dir": str}
_BACKUP_CONFIG_SCHEMA = {"run_id": int, "output_dir": str, "dump_format": str}


def _record_result_file(run_id: int, output_path: Path) -> None:
    """Attach the op's output file to its MaintenanceRun.

    Each op knows its own output path directly, so it writes result_file
    itself rather than the daemon's run-status sensor trying to reconstruct
    it after the fact from Dagster's event log.
    """
    from orchestration.models import MaintenanceRun

    MaintenanceRun.objects.filter(pk=run_id).update(
        result_file=f"maintenance/{output_path.name}"
    )


# ---------------------------------------------------------------------------
# backup_job
# ---------------------------------------------------------------------------


def _is_sqlite(engine: str) -> bool:
    engine_lower = engine.lower()
    return "sqlite" in engine_lower or "spatialite" in engine_lower


def _backup_sqlite(
    log: Callable[[str], None],
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

    log(f"Backing up SQLite database {db_path}")
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
    log: Callable[[str], None],
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
    log(f"Running pg_dump for database {db['NAME']} (format={dump_format})")

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
def run_pg_dump(context) -> str:  # noqa: ANN001 — Dagster 1.12.8 errors if this param is type-annotated
    """Back up the configured database (SQLite copy or pg_dump) to output_dir."""
    from django.conf import settings

    db = settings.DATABASES["default"]
    engine: str = db.get("ENGINE", "")
    output_dir: str = context.op_config["output_dir"]
    dump_format: str = context.op_config.get("dump_format", "custom")
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    if _is_sqlite(engine):
        output_path = _backup_sqlite(
            context.log.info, db, output_dir, timestamp
        )
    else:
        output_path = _backup_postgres(
            context.log.info, db, output_dir, timestamp, dump_format
        )

    context.log.info(
        "Backup written to %s (%d bytes)",
        output_path,
        output_path.stat().st_size,
    )
    _record_result_file(context.op_config["run_id"], output_path)
    return str(output_path)


@job(name="backup_job")
def backup_job() -> None:
    """Dagster job that runs a database backup."""
    run_pg_dump()


# ---------------------------------------------------------------------------
# duckdb_export_job
# ---------------------------------------------------------------------------


def _get_queryset(model: type[Model], cfg: DuckDBTableConfig) -> QuerySet:
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


def _coerce_df_columns(df: pd.DataFrame) -> None:
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


_EXPORT_CHUNK_SIZE = 10_000


def _export_model_table(
    conn: duckdb.DuckDBPyConnection,
    cfg: DuckDBTableConfig,
    model: type[Model],
    context: OpExecutionContext,
) -> bool:
    """Export one model's queryset to a DuckDB table, in chunks; log and swallow errors.

    Iterates via .iterator(chunk_size=...) and writes one DataFrame chunk
    at a time (CREATE TABLE on the first non-empty chunk, INSERT for the
    rest) instead of materializing list(qs) + one giant DataFrame — memory
    use is bounded by chunk size, not total row count, for any "fact"-role
    table (see DuckDBTableConfig.ROLES) that grows large.

    Returns True on success (including an intentionally-empty table),
    False if the export raised - the caller uses this to track how many
    configured tables actually made it into the export, since a per-table
    error here would otherwise be silently invisible in the job's overall
    "success" status.
    """
    import duckdb
    import pandas as pd

    table_name = f"{cfg.app_label}__{cfg.model_name.lower()}"
    table_created = False

    def _write_chunk(rows: list) -> None:
        nonlocal table_created
        df = pd.DataFrame.from_records(rows)
        _coerce_df_columns(df)
        if not table_created:
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")  # noqa: S608  # nosec B608 — table_name derived from Django model metadata (app_label/model_name), not user input
            table_created = True
            return
        try:
            conn.execute(f"INSERT INTO {table_name} SELECT * FROM df")  # noqa: S608  # nosec B608 — see above
        except duckdb.ConversionException:
            # tech debt O4: CREATE TABLE inferred the schema from only the
            # first chunk - a sparse/all-NULL column there (e.g. inferred
            # as INTEGER from all-None values) can't hold this chunk's real
            # values (e.g. strings). Rebuild the table so far via UNION ALL
            # BY NAME, which lets DuckDB promote the column to a common
            # type instead of failing the whole export. Only paid when this
            # mismatch actually happens — the common case (consistent types
            # across chunks) stays a single INSERT.
            conn.execute(
                f"CREATE OR REPLACE TABLE {table_name} AS "  # noqa: S608  # nosec B608 — see above
                f"SELECT * FROM {table_name} UNION ALL BY NAME SELECT * FROM df"
            )

    try:
        qs = _get_queryset(model, cfg)
        total_rows = 0
        chunk: list = []
        for row in qs.iterator(chunk_size=_EXPORT_CHUNK_SIZE):
            chunk.append(row)
            if len(chunk) >= _EXPORT_CHUNK_SIZE:
                _write_chunk(chunk)
                total_rows += len(chunk)
                chunk = []
        if chunk:
            _write_chunk(chunk)
            total_rows += len(chunk)

        if not table_created:
            context.log.info("Table %s is empty, skipping", table_name)
            return True
        context.log.info(
            "Exported %d rows to table %s", total_rows, table_name
        )
    except Exception:  # noqa: BLE001
        context.log.error(
            "Failed to export %s.%s:\n%s",
            cfg.app_label,
            cfg.model_name,
            traceback.format_exc(),
        )
        return False
    return True


def _check_export_failures(
    context: OpExecutionContext, attempted: int, failed_tables: list[str]
) -> None:
    """Log and, if every configured table failed, raise.

    Extracted from export_to_duckdb as a plain function (same pattern as
    _export_model_table/_get_queryset/_coerce_df_columns) so this logic is
    directly unit-testable without going through Dagster's op-invocation
    machinery, which doesn't pass a real context.log/context.op_config
    through to a bare direct-invocation mock.
    """
    if failed_tables:
        context.log.error(
            "DuckDB export: %d of %d configured table(s) failed: %s",
            len(failed_tables),
            attempted,
            ", ".join(failed_tables),
        )
    if attempted and len(failed_tables) == attempted:
        # Every configured table failed - the file this op returns would be
        # an empty/near-empty DuckDB database with no export actually
        # having succeeded. Raise so the run reports failure instead of a
        # misleading "success".
        msg = f"DuckDB export failed for all {attempted} configured table(s); see log for per-table errors."
        raise RuntimeError(msg)


@op(config_schema=_BASE_CONFIG_SCHEMA)
def export_to_duckdb(context) -> str:  # noqa: ANN001 — Dagster 1.12.8 errors if this param is type-annotated
    """Export configured Django model tables to a DuckDB file."""
    import duckdb
    from django.apps import apps

    from orchestration.models import DuckDBTableConfig

    output_dir: str = context.op_config["output_dir"]
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_path = Path(output_dir) / f"cgdb_{timestamp}.duckdb"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(output_path))
    attempted = 0
    failed_tables: list[str] = []
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
        attempted += 1
        if not _export_model_table(conn, cfg, model, context):
            failed_tables.append(f"{cfg.app_label}.{cfg.model_name}")

    conn.close()
    _check_export_failures(context, attempted, failed_tables)

    context.log.info("DuckDB export written to %s", output_path)
    _record_result_file(context.op_config["run_id"], output_path)
    return str(output_path)


@job(name="duckdb_export_job")
def duckdb_export_job() -> None:
    """Dagster job that exports Django models to DuckDB."""
    export_to_duckdb()


# ---------------------------------------------------------------------------
# integrity_check_job
# ---------------------------------------------------------------------------


_INTEGRITY_CHECK_CHUNK_SIZE = 10_000


@op(config_schema=_BASE_CONFIG_SCHEMA)
def run_integrity_checks(context) -> str:  # noqa: ANN001 — Dagster 1.12.8 errors if this param is type-annotated
    """Run data integrity checks and write a JSON report to output_dir.

    tech debt O3: the queries feeding orphan_samples/missing_geometries are
    chunked via .iterator(chunk_size=...) and their IntegrityIssue rows are
    written via bulk_create in the same chunks, matching the pattern
    _export_model_table already established for the DuckDB export op - the
    JSON report still needs the full id list in memory (it's part of the
    report's contents), but the DB round-trips are now bounded per chunk
    instead of one INSERT per row.
    """
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
    run.issues.all().delete()  # pyright: ignore[reportAttributeAccessIssue]  # reverse FK related_name accessor; no mypy-plugin support in basedpyright — idempotent: clear any previous issues for this run

    results: dict = {}

    # Check 1: Orphan Samples (sample with no location)
    Sample = apps.get_model("field_data", "Sample")
    orphan_qs = Sample.objects.filter(location__isnull=True).values_list(
        "id", "identifier"
    )
    orphan_ids = []
    orphan_issues: list = []
    for sid, identifier in orphan_qs.iterator(
        chunk_size=_INTEGRITY_CHECK_CHUNK_SIZE
    ):
        orphan_ids.append((sid, identifier))
        orphan_issues.append(
            IntegrityIssue(
                run=run,
                check_type="orphan_samples",
                object_id=sid,
                description=f"Sample '{identifier}' (id={sid}) has no location assigned.",
            )
        )
        if len(orphan_issues) >= _INTEGRITY_CHECK_CHUNK_SIZE:
            IntegrityIssue.objects.bulk_create(orphan_issues)
            orphan_issues = []
    if orphan_issues:
        IntegrityIssue.objects.bulk_create(orphan_issues)
    results["orphan_samples"] = {"count": len(orphan_ids), "ids": orphan_ids}
    context.log.info("Orphan samples (no location): %d", len(orphan_ids))

    # Check 2: Locations missing geometry
    Location = apps.get_model("field_data", "Location")
    missing_geom_qs = Location.objects.filter(
        location__isnull=True
    ).values_list("id", flat=True)
    missing_geom = []
    missing_geom_issues: list = []
    for lid in missing_geom_qs.iterator(
        chunk_size=_INTEGRITY_CHECK_CHUNK_SIZE
    ):
        missing_geom.append(lid)
        missing_geom_issues.append(
            IntegrityIssue(
                run=run,
                check_type="missing_geometries",
                object_id=lid,
                description=f"Location id={lid} has no geometry (location field is null).",
            )
        )
        if len(missing_geom_issues) >= _INTEGRITY_CHECK_CHUNK_SIZE:
            IntegrityIssue.objects.bulk_create(missing_geom_issues)
            missing_geom_issues = []
    if missing_geom_issues:
        IntegrityIssue.objects.bulk_create(missing_geom_issues)
    results["missing_geometries"] = {
        "count": len(missing_geom),
        "ids": missing_geom,
    }
    context.log.info("Locations missing geometry: %d", len(missing_geom))

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
    _record_result_file(run_id, output_path)
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

# tech debt O5: single source of truth for job_type -> op_name/job_name,
# previously duplicated in two different styles across orchestration/admin.py
# and run_maintenance_job.py - a rename in one silently desynced the other.
# Both now import these instead of hand-rolling their own copy.
OP_NAME_BY_JOB_TYPE = {
    "backup": "run_pg_dump",
    "duckdb": "export_to_duckdb",
    "integrity": "run_integrity_checks",
}
JOB_NAME_BY_JOB_TYPE = {
    "backup": "backup_job",
    "duckdb": "duckdb_export_job",
    "integrity": "integrity_check_job",
}


def get_job_for_type(job_type: str) -> JobDefinition:
    """Return the Dagster JobDefinition for the given job_type key."""
    if job_type not in _JOB_MAP:
        msg = f"Unknown maintenance job type: {job_type!r}"
        raise ValueError(msg)
    return _JOB_MAP[job_type]
