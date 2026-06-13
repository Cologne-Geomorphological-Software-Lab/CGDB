"""Tests for orchestration models: MaintenanceRun and DuckDBTableConfig."""

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from orchestration.models import DuckDBTableConfig, IntegrityIssue, MaintenanceRun


class MaintenanceRunModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testuser", password="pw")

    def test_default_status_is_pending(self):
        run = MaintenanceRun.objects.create(job_type="backup")
        self.assertEqual(run.status, "pending")

    def test_started_at_and_finished_at_nullable(self):
        run = MaintenanceRun.objects.create(job_type="integrity")
        self.assertIsNone(run.started_at)
        self.assertIsNone(run.finished_at)

    def test_triggered_by_nullable(self):
        run = MaintenanceRun.objects.create(job_type="duckdb")
        self.assertIsNone(run.triggered_by)

    def test_triggered_by_set_null_on_user_delete(self):
        user = User.objects.create_user(username="todelete", password="pw")
        run = MaintenanceRun.objects.create(job_type="backup", triggered_by=user)
        user.delete()
        run.refresh_from_db()
        self.assertIsNone(run.triggered_by)

    def test_str_pending(self):
        run = MaintenanceRun.objects.create(job_type="backup")
        self.assertIn("Backup", str(run))
        self.assertIn("pending", str(run))

    def test_str_with_started_at(self):
        from datetime import datetime, timezone

        started = datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc)
        run = MaintenanceRun.objects.create(
            job_type="integrity", status="running", started_at=started
        )
        self.assertIn("Integrity Check", str(run))
        self.assertIn("running", str(run))

    def test_all_job_type_choices(self):
        for code, _ in MaintenanceRun.JOB_TYPES:
            run = MaintenanceRun.objects.create(job_type=code)
            self.assertEqual(run.job_type, code)

    def test_all_status_choices(self):
        for code, _ in MaintenanceRun.STATUSES:
            run = MaintenanceRun.objects.create(job_type="backup", status=code)
            self.assertEqual(run.status, code)

    def test_log_defaults_to_empty_string(self):
        run = MaintenanceRun.objects.create(job_type="backup")
        self.assertEqual(run.log, "")

    def test_result_file_nullable(self):
        run = MaintenanceRun.objects.create(job_type="backup")
        self.assertFalse(run.result_file)

    def test_default_dump_format_is_custom(self):
        run = MaintenanceRun.objects.create(job_type="backup")
        self.assertEqual(run.dump_format, "custom")

    def test_dump_format_plain(self):
        run = MaintenanceRun.objects.create(job_type="backup", dump_format="plain")
        run.refresh_from_db()
        self.assertEqual(run.dump_format, "plain")

    def test_dump_format_choices(self):
        codes = [code for code, _ in MaintenanceRun.DUMP_FORMATS]
        self.assertIn("custom", codes)
        self.assertIn("plain", codes)


class IntegrityIssueModelTests(TestCase):
    def setUp(self):
        self.run = MaintenanceRun.objects.create(job_type="integrity")

    def test_create_issue(self):
        issue = IntegrityIssue.objects.create(
            run=self.run,
            check_type="orphan_samples",
            object_id=42,
            description="Sample 'X' has no location.",
        )
        self.assertEqual(issue.check_type, "orphan_samples")
        self.assertEqual(issue.object_id, 42)

    def test_object_id_nullable(self):
        issue = IntegrityIssue.objects.create(
            run=self.run,
            check_type="guardian_maintenance_permissions",
            object_id=None,
            description="0 objects have guardian permissions.",
        )
        self.assertIsNone(issue.object_id)

    def test_related_name_issues(self):
        IntegrityIssue.objects.create(
            run=self.run, check_type="orphan_samples", description="a"
        )
        IntegrityIssue.objects.create(
            run=self.run, check_type="missing_geometries", description="b"
        )
        self.assertEqual(self.run.issues.count(), 2)

    def test_cascade_delete(self):
        extra_run = MaintenanceRun.objects.create(job_type="integrity")
        issue = IntegrityIssue.objects.create(
            run=extra_run, check_type="orphan_samples", description="x"
        )
        issue_pk = issue.pk
        extra_run.delete()
        self.assertEqual(IntegrityIssue.objects.filter(pk=issue_pk).count(), 0)

    def test_str(self):
        issue = IntegrityIssue.objects.create(
            run=self.run,
            check_type="orphan_samples",
            object_id=7,
            description="Sample has no location.",
        )
        self.assertIn("orphan_samples", str(issue))
        self.assertIn("7", str(issue))


class DuckDBTableConfigModelTests(TestCase):
    # Use app_label/model_name pairs NOT in the default seed list to avoid
    # UNIQUE constraint conflicts with the post_migrate signal data.

    def test_create_basic_config(self):
        cfg = DuckDBTableConfig.objects.create(
            app_label="orchestration", model_name="MaintenanceRun", role="fact"
        )
        self.assertEqual(cfg.app_label, "orchestration")
        self.assertEqual(cfg.role, "fact")

    def test_default_role_is_dim(self):
        cfg = DuckDBTableConfig.objects.create(
            app_label="orchestration", model_name="DuckDBTableConfig"
        )
        self.assertEqual(cfg.role, "dim")

    def test_unique_together_enforced(self):
        DuckDBTableConfig.objects.create(
            app_label="orchestration", model_name="MaintenanceRun", role="fact"
        )
        with self.assertRaises(IntegrityError):
            DuckDBTableConfig.objects.create(
                app_label="orchestration", model_name="MaintenanceRun", role="dim"
            )

    def test_str(self):
        cfg = DuckDBTableConfig.objects.create(
            app_label="orchestration", model_name="MaintenanceRun", role="exclude"
        )
        self.assertEqual(str(cfg), "orchestration.MaintenanceRun (exclude)")

    def test_include_fields_defaults_to_empty_list(self):
        cfg = DuckDBTableConfig.objects.create(
            app_label="orchestration", model_name="DuckDBTableConfig"
        )
        self.assertEqual(cfg.include_fields, [])

    def test_exclude_fields_defaults_to_empty_list(self):
        cfg = DuckDBTableConfig.objects.create(
            app_label="orchestration", model_name="DuckDBTableConfig"
        )
        self.assertEqual(cfg.exclude_fields, [])

    def test_include_fields_stored_as_list(self):
        cfg = DuckDBTableConfig.objects.create(
            app_label="orchestration",
            model_name="MaintenanceRun",
            include_fields=["id", "job_type"],
        )
        cfg.refresh_from_db()
        self.assertEqual(cfg.include_fields, ["id", "job_type"])
