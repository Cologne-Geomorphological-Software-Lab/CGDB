"""Tests for the run_maintenance_job management command."""

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from orchestration.models import MaintenanceRun


def _make_mock_result(success: bool = True, events: list | None = None):
    result = MagicMock()
    result.success = success
    result.all_events = events or []
    return result


class RunMaintenanceJobCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(username="admin", password="pw")

    def _run_command(self, job_type: str, run: MaintenanceRun, mock_result=None):
        if mock_result is None:
            mock_result = _make_mock_result(success=True)

        mock_job = MagicMock()
        mock_job.execute_in_process.return_value = mock_result

        with patch("dagster.DagsterInstance") as mock_instance_cls, patch(
            "orchestration.dagster_home.maintenance_jobs.get_job_for_type",
            return_value=mock_job,
        ):
            mock_instance_cls.get.return_value = MagicMock()
            call_command("run_maintenance_job", job_type, "--run-id", str(run.pk))

        return mock_job

    def test_raises_for_nonexistent_run_id(self):
        with self.assertRaises(CommandError):
            call_command("run_maintenance_job", "backup", "--run-id", "99999")

    def test_status_set_to_running_then_success(self):
        run = MaintenanceRun.objects.create(job_type="integrity")
        self._run_command("integrity", run)
        run.refresh_from_db()
        self.assertEqual(run.status, "success")
        self.assertIsNotNone(run.started_at)
        self.assertIsNotNone(run.finished_at)

    def test_status_set_to_failed_on_job_failure(self):
        run = MaintenanceRun.objects.create(job_type="backup")
        self._run_command("backup", run, mock_result=_make_mock_result(success=False))
        run.refresh_from_db()
        self.assertEqual(run.status, "failed")

    def test_status_set_to_failed_on_exception(self):
        run = MaintenanceRun.objects.create(job_type="duckdb")
        mock_job = MagicMock()
        mock_job.execute_in_process.side_effect = RuntimeError("boom")

        with patch("dagster.DagsterInstance") as mock_instance_cls, patch(
            "orchestration.dagster_home.maintenance_jobs.get_job_for_type",
            return_value=mock_job,
        ):
            mock_instance_cls.get.return_value = MagicMock()
            call_command("run_maintenance_job", "duckdb", "--run-id", str(run.pk))

        run.refresh_from_db()
        self.assertEqual(run.status, "failed")
        self.assertIn("RuntimeError", run.log)

    def test_log_populated_from_events(self):
        event = MagicMock()
        event.message = "Job started"
        event.level = MagicMock()
        event.level.value = "INFO"

        run = MaintenanceRun.objects.create(job_type="integrity")
        self._run_command(
            "integrity", run, mock_result=_make_mock_result(events=[event])
        )
        run.refresh_from_db()
        self.assertIn("Job started", run.log)

    def test_finished_at_always_set(self):
        run = MaintenanceRun.objects.create(job_type="backup")
        self._run_command("backup", run, mock_result=_make_mock_result(success=False))
        run.refresh_from_db()
        self.assertIsNotNone(run.finished_at)

    def test_execute_in_process_called_with_correct_run_config(self):
        run = MaintenanceRun.objects.create(job_type="integrity")
        mock_job = self._run_command("integrity", run)
        call_args = mock_job.execute_in_process.call_args
        run_config = call_args.kwargs.get("run_config") or call_args.args[0]
        ops_config = run_config["ops"]["run_integrity_checks"]["config"]
        self.assertEqual(ops_config["run_id"], run.pk)

    def test_dump_format_passed_in_run_config(self):
        run = MaintenanceRun.objects.create(job_type="backup", dump_format="plain")
        mock_job = self._run_command("backup", run)
        call_args = mock_job.execute_in_process.call_args
        run_config = call_args.kwargs.get("run_config") or call_args.args[0]
        ops_config = run_config["ops"]["run_pg_dump"]["config"]
        self.assertEqual(ops_config["dump_format"], "plain")

    def test_dump_format_defaults_to_custom(self):
        run = MaintenanceRun.objects.create(job_type="backup")
        mock_job = self._run_command("backup", run)
        call_args = mock_job.execute_in_process.call_args
        run_config = call_args.kwargs.get("run_config") or call_args.args[0]
        ops_config = run_config["ops"]["run_pg_dump"]["config"]
        self.assertEqual(ops_config["dump_format"], "custom")

    def test_result_file_attached_when_output_file_exists(self):
        import tempfile
        from pathlib import Path

        run = MaintenanceRun.objects.create(job_type="integrity")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Management command writes to MEDIA_ROOT/maintenance/
            maintenance_dir = Path(tmpdir) / "maintenance"
            maintenance_dir.mkdir()
            fake_file = maintenance_dir / "integrity_20250101_120000.json"
            fake_file.write_text("{}")

            mock_job = MagicMock()
            mock_job.execute_in_process.return_value = _make_mock_result(success=True)

            with patch("dagster.DagsterInstance") as mock_instance_cls, patch(
                "orchestration.dagster_home.maintenance_jobs.get_job_for_type",
                return_value=mock_job,
            ), patch("django.conf.settings.MEDIA_ROOT", tmpdir):
                mock_instance_cls.get.return_value = MagicMock()
                call_command(
                    "run_maintenance_job", "integrity", "--run-id", str(run.pk)
                )

        run.refresh_from_db()
        self.assertIn("integrity_", run.result_file.name)
