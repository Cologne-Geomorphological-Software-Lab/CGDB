"""Tests for Dagster maintenance jobs.

Integrity and dispatcher tests run via execute_in_process (DagsterInstance.ephemeral).
Backup tests exercise the _backup_sqlite helper directly to avoid file-lock hangs
that occur when Dagster teardown competes with the SQLite test DB.
"""

import gzip
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from dagster import DagsterInstance

from orchestration.dagster_home.maintenance_jobs import (
    _PG_FORMAT_EXTENSIONS,
    _PG_FORMAT_FLAGS,
    _backup_postgres,
    _backup_sqlite,
    backup_job,
    get_job_for_type,
    integrity_check_job,
)
from orchestration.models import IntegrityIssue, MaintenanceRun


def _run_config(output_dir: str, run_id: int = 1) -> dict:
    return {
        "ops": {
            "<OP>": {
                "config": {"run_id": run_id, "output_dir": output_dir}
            }
        }
    }


@pytest.mark.django_db
class TestIntegrityCheckJob:
    def _make_run(self) -> MaintenanceRun:
        return MaintenanceRun.objects.create(job_type="integrity")

    def _cfg(self, run: MaintenanceRun, tmp_path) -> dict:
        return {
            "ops": {
                "run_integrity_checks": {
                    "config": {"run_id": run.pk, "output_dir": str(tmp_path)}
                }
            }
        }

    def test_job_succeeds(self, tmp_path):
        run = self._make_run()
        result = integrity_check_job.execute_in_process(
            run_config=self._cfg(run, tmp_path),
            instance=DagsterInstance.ephemeral(),
        )
        assert result.success

    def test_output_file_created(self, tmp_path):
        run = self._make_run()
        integrity_check_job.execute_in_process(
            run_config=self._cfg(run, tmp_path),
            instance=DagsterInstance.ephemeral(),
        )
        files = list(tmp_path.glob("integrity_*.json"))
        assert len(files) == 1

    def test_output_file_is_valid_json(self, tmp_path):
        run = self._make_run()
        integrity_check_job.execute_in_process(
            run_config=self._cfg(run, tmp_path),
            instance=DagsterInstance.ephemeral(),
        )
        output_file = next(tmp_path.glob("integrity_*.json"))
        data = json.loads(output_file.read_text())
        assert "orphan_samples" in data
        assert "missing_geometries" in data
        assert "guardian_maintenance_permissions" in data

    def test_output_contains_count_keys(self, tmp_path):
        run = self._make_run()
        integrity_check_job.execute_in_process(
            run_config=self._cfg(run, tmp_path),
            instance=DagsterInstance.ephemeral(),
        )
        output_file = next(tmp_path.glob("integrity_*.json"))
        data = json.loads(output_file.read_text())
        assert "count" in data["orphan_samples"]
        assert "count" in data["missing_geometries"]

    def test_integrity_issues_created(self, tmp_path):
        run = self._make_run()
        integrity_check_job.execute_in_process(
            run_config=self._cfg(run, tmp_path),
            instance=DagsterInstance.ephemeral(),
        )
        # Guardian summary issue is always created
        assert IntegrityIssue.objects.filter(
            run=run, check_type="guardian_maintenance_permissions"
        ).exists()

    def test_integrity_issues_idempotent(self, tmp_path):
        run = self._make_run()
        cfg = self._cfg(run, tmp_path)
        integrity_check_job.execute_in_process(
            run_config=cfg, instance=DagsterInstance.ephemeral()
        )
        count_first = IntegrityIssue.objects.filter(run=run).count()
        integrity_check_job.execute_in_process(
            run_config=cfg, instance=DagsterInstance.ephemeral()
        )
        count_second = IntegrityIssue.objects.filter(run=run).count()
        assert count_first == count_second


class TestBackupSQLiteHelper:
    """Tests for _backup_sqlite helper — no Dagster overhead, no file-lock risk."""

    def _make_db(self, path: Path) -> Path:
        conn = sqlite3.connect(str(path))
        conn.execute("CREATE TABLE dummy (id INTEGER PRIMARY KEY)")
        conn.close()
        return path

    def test_output_file_created(self, tmp_path):
        db_file = self._make_db(tmp_path / "source.sqlite3")
        out_dir = tmp_path / "out"
        context = MagicMock()

        db = {"NAME": str(db_file)}
        result_path = _backup_sqlite(context, db, str(out_dir), "20250101_120000")

        assert result_path.exists()
        assert result_path.name == "backup_20250101_120000.sqlite3.gz"

    def test_output_is_valid_gzip_of_sqlite(self, tmp_path):
        db_file = self._make_db(tmp_path / "source.sqlite3")
        out_dir = tmp_path / "out"
        context = MagicMock()

        result_path = _backup_sqlite(
            context, {"NAME": str(db_file)}, str(out_dir), "20250101_120000"
        )

        with gzip.open(result_path, "rb") as f:
            header = f.read(16)
        assert header[:6] == b"SQLite"

    def test_raises_if_db_file_missing(self, tmp_path):
        context = MagicMock()
        with pytest.raises(FileNotFoundError):
            _backup_sqlite(
                context,
                {"NAME": str(tmp_path / "nonexistent.sqlite3")},
                str(tmp_path / "out"),
                "20250101_120000",
            )

    def test_backup_job_is_registered(self):
        """Smoke test: job object is importable and has the expected name."""
        assert backup_job.name == "backup_job"


class TestBackupPostgresFormats:
    """Unit tests for pg format flag/extension mapping — no subprocess calls."""

    def test_custom_format_flag(self):
        assert _PG_FORMAT_FLAGS["custom"] == "-Fc"

    def test_plain_format_flag(self):
        assert _PG_FORMAT_FLAGS["plain"] == "-Fp"

    def test_custom_format_extension(self):
        assert _PG_FORMAT_EXTENSIONS["custom"] == ".dump.gz"

    def test_plain_format_extension(self):
        assert _PG_FORMAT_EXTENSIONS["plain"] == ".sql.gz"

    def test_backup_postgres_uses_plain_extension(self, tmp_path):
        """_backup_postgres with 'plain' format produces a .sql.gz filename."""
        import unittest.mock as mock

        context = mock.MagicMock()
        db = {
            "NAME": "testdb",
            "HOST": "localhost",
            "PORT": 5432,
            "USER": "user",
            "PASSWORD": "pw",
        }

        fake_output = b"-- SQL dump content"
        mock_proc = mock.MagicMock()
        mock_proc.stdout = fake_output

        with mock.patch("subprocess.run", return_value=mock_proc):
            result = _backup_postgres(context, db, str(tmp_path), "20250101_120000", "plain")

        assert result.name.endswith(".sql.gz")
        assert result.exists()

    def test_backup_postgres_uses_custom_extension(self, tmp_path):
        """_backup_postgres with 'custom' format produces a .dump.gz filename."""
        import unittest.mock as mock

        context = mock.MagicMock()
        db = {
            "NAME": "testdb",
            "HOST": "localhost",
            "PORT": 5432,
            "USER": "user",
            "PASSWORD": "pw",
        }

        fake_output = b"\x50\x47\x44\x4d"  # fake pg_dump custom header bytes
        mock_proc = mock.MagicMock()
        mock_proc.stdout = fake_output

        with mock.patch("subprocess.run", return_value=mock_proc):
            result = _backup_postgres(context, db, str(tmp_path), "20250101_120000", "custom")

        assert result.name.endswith(".dump.gz")
        assert result.exists()


class TestIsSQLite:
    def test_spatialite_detected(self):
        from orchestration.dagster_home.maintenance_jobs import _is_sqlite
        assert _is_sqlite("django.contrib.gis.db.backends.spatialite")

    def test_sqlite3_detected(self):
        from orchestration.dagster_home.maintenance_jobs import _is_sqlite
        assert _is_sqlite("django.db.backends.sqlite3")

    def test_postgis_not_detected(self):
        from orchestration.dagster_home.maintenance_jobs import _is_sqlite
        assert not _is_sqlite("django.contrib.gis.db.backends.postgis")

    def test_postgresql_not_detected(self):
        from orchestration.dagster_home.maintenance_jobs import _is_sqlite
        assert not _is_sqlite("django.db.backends.postgresql")


class TestGetJobForType:
    def test_returns_backup_job(self):
        assert get_job_for_type("backup") is backup_job

    def test_returns_integrity_job(self):
        assert get_job_for_type("integrity") is integrity_check_job

    def test_raises_for_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown maintenance job type"):
            get_job_for_type("unknown")


# ===========================================================================
# _get_queryset — queryset field selection
# ===========================================================================


@pytest.mark.django_db
class TestGetQueryset:
    """Tests for the _get_queryset helper extracted from export_to_duckdb."""

    from orchestration.dagster_home.maintenance_jobs import _get_queryset

    def _make_cfg(self, include_fields=None, exclude_fields=None):
        cfg = MagicMock()
        cfg.include_fields = include_fields or []
        cfg.exclude_fields = exclude_fields or []
        return cfg

    def test_include_fields_limits_columns(self):
        from orchestration.dagster_home.maintenance_jobs import _get_queryset
        from prototype.models import Project

        Project.objects.create(title="P1", label="L1", status="ACTIVE")
        cfg = self._make_cfg(include_fields=["title"])
        rows = list(_get_queryset(Project, cfg))
        assert rows
        assert "title" in rows[0]
        assert "label" not in rows[0]

    def test_exclude_fields_removes_columns(self):
        from orchestration.dagster_home.maintenance_jobs import _get_queryset
        from prototype.models import Project

        Project.objects.create(title="P2", label="L2", status="ACTIVE")
        cfg = self._make_cfg(exclude_fields=["description"])
        rows = list(_get_queryset(Project, cfg))
        assert rows
        assert "description" not in rows[0]
        assert "title" in rows[0]

    def test_no_fields_returns_all_columns(self):
        from orchestration.dagster_home.maintenance_jobs import _get_queryset
        from prototype.models import Project

        Project.objects.create(title="P3", label="L3", status="ACTIVE")
        cfg = self._make_cfg()
        rows = list(_get_queryset(Project, cfg))
        assert rows
        assert "title" in rows[0]
        assert "label" in rows[0]


# ===========================================================================
# _coerce_df_columns — type coercion
# ===========================================================================


class TestCoerceDfColumns:
    """Tests for the _coerce_df_columns helper."""

    def test_non_serialisable_object_coerced_to_str(self):
        import pandas as pd

        from orchestration.dagster_home.maintenance_jobs import _coerce_df_columns

        class Opaque:
            def __str__(self):
                return "opaque"

        df = pd.DataFrame({"val": [Opaque()]})
        _coerce_df_columns(df)
        assert df["val"][0] == "opaque"

    def test_none_values_kept_as_none(self):
        import pandas as pd

        from orchestration.dagster_home.maintenance_jobs import _coerce_df_columns

        df = pd.DataFrame({"val": [None]})
        _coerce_df_columns(df)
        assert df["val"][0] is None

    def test_strings_not_coerced(self):
        import pandas as pd

        from orchestration.dagster_home.maintenance_jobs import _coerce_df_columns

        df = pd.DataFrame({"val": ["hello"]})
        _coerce_df_columns(df)
        assert df["val"][0] == "hello"

    def test_integers_not_coerced(self):
        import pandas as pd

        from orchestration.dagster_home.maintenance_jobs import _coerce_df_columns

        df = pd.DataFrame({"val": pd.array([42], dtype="int64")})
        _coerce_df_columns(df)
        assert df["val"][0] == 42

    def test_mixed_column_coerces_only_opaque(self):
        import pandas as pd

        from orchestration.dagster_home.maintenance_jobs import _coerce_df_columns

        class Opaque:
            def __str__(self):
                return "x"

        df = pd.DataFrame({"val": ["keep", Opaque(), None]})
        _coerce_df_columns(df)
        assert df["val"][0] == "keep"
        assert df["val"][1] == "x"
        # pandas may store None as NaN in object columns after apply()
        assert df["val"][2] is None or pd.isna(df["val"][2])


# ===========================================================================
# _export_model_table — per-table export logic
# ===========================================================================


@pytest.mark.django_db
class TestExportModelTable:
    """Tests for the _export_model_table helper."""

    def _make_cfg(self, app_label="prototype", model_name="Project"):
        cfg = MagicMock()
        cfg.app_label = app_label
        cfg.model_name = model_name
        cfg.include_fields = []
        cfg.exclude_fields = []
        return cfg

    def test_exports_rows_calls_conn_execute(self):
        """_export_model_table calls conn.execute with CREATE TABLE SQL on non-empty table."""
        from orchestration.dagster_home.maintenance_jobs import _export_model_table
        from prototype.models import Project

        Project.objects.create(title="ExpT", label="ET01", status="ACTIVE")
        cfg = self._make_cfg()
        conn = MagicMock()
        context = MagicMock()

        _export_model_table(conn, cfg, Project, context)

        conn.execute.assert_called_once()
        sql = conn.execute.call_args[0][0]
        assert "CREATE TABLE prototype__project" in sql

    def test_empty_table_skipped(self):
        from orchestration.dagster_home.maintenance_jobs import _export_model_table
        from prototype.models import Project

        Project.objects.all().delete()
        cfg = self._make_cfg()
        conn = MagicMock()
        context = MagicMock()

        _export_model_table(conn, cfg, Project, context)

        conn.execute.assert_not_called()
        context.log.info.assert_called_with(
            "Table %s is empty, skipping", "prototype__project"
        )

    def test_exception_logged_not_raised(self):
        from orchestration.dagster_home.maintenance_jobs import _export_model_table
        from prototype.models import Project

        Project.objects.create(title="ErrT", label="ER01", status="ACTIVE")
        cfg = self._make_cfg()
        conn = MagicMock()
        conn.execute.side_effect = RuntimeError("db error")
        context = MagicMock()

        _export_model_table(conn, cfg, Project, context)  # must not raise

        context.log.error.assert_called_once()
