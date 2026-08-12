"""Tests for orchestration admin: permissions, actions, and display helpers."""

from unittest.mock import MagicMock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from orchestration.admin import (
    DuckDBTableConfigAdmin,
    IntegrityIssueInline,
    MaintenanceRunAdmin,
    _submit_maintenance_run,
)
from orchestration.models import DuckDBTableConfig, IntegrityIssue, MaintenanceRun
from prototype.middleware import CurrentUserMiddleware


class MaintenanceRunAdminPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="pw", email="s@test.com"
        )
        cls.regular_user = User.objects.create_user(
            username="regular", password="pw", email="r@test.com"
        )

    def setUp(self):
        self.site = AdminSite()
        self.admin = MaintenanceRunAdmin(MaintenanceRun, self.site)
        self.factory = RequestFactory()

    def _request(self, user: User) -> object:
        request = self.factory.get("/")
        request.user = user
        return request

    def test_superuser_has_add_permission(self):
        self.assertTrue(self.admin.has_add_permission(self._request(self.superuser)))

    def test_regular_user_denied_add_permission(self):
        self.assertFalse(self.admin.has_add_permission(self._request(self.regular_user)))

    def test_superuser_has_change_permission(self):
        self.assertTrue(self.admin.has_change_permission(self._request(self.superuser)))

    def test_regular_user_denied_change_permission(self):
        self.assertFalse(self.admin.has_change_permission(self._request(self.regular_user)))

    def test_superuser_has_delete_permission(self):
        self.assertTrue(self.admin.has_delete_permission(self._request(self.superuser)))

    def test_regular_user_denied_delete_permission(self):
        self.assertFalse(self.admin.has_delete_permission(self._request(self.regular_user)))

    def test_superuser_has_view_permission(self):
        self.assertTrue(self.admin.has_view_permission(self._request(self.superuser)))

    def test_regular_user_denied_view_permission(self):
        self.assertFalse(self.admin.has_view_permission(self._request(self.regular_user)))


class MaintenanceRunAdminActionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="pw", email="s@test.com"
        )
        cls.regular_user = User.objects.create_user(
            username="regular", password="pw", email="r@test.com"
        )

    def setUp(self):
        self.site = AdminSite()
        self.admin = MaintenanceRunAdmin(MaintenanceRun, self.site)
        self.factory = RequestFactory()

    def _request(self, user: User) -> object:
        request = self.factory.post("/")
        request.user = user
        request._messages = MagicMock()
        return request

    def test_trigger_action_submits_pending_runs(self):
        run = MaintenanceRun.objects.create(job_type="integrity", status="pending")
        request = self._request(self.superuser)

        with patch("orchestration.admin._submit_maintenance_run") as mock_submit:
            self.admin.trigger_maintenance_job(
                request, MaintenanceRun.objects.filter(pk=run.pk)
            )
            mock_submit.assert_called_once_with(run)

    def test_trigger_action_marks_run_running_before_submit(self):
        run = MaintenanceRun.objects.create(job_type="integrity", status="pending")
        request = self._request(self.superuser)

        with patch("orchestration.admin._submit_maintenance_run"):
            self.admin.trigger_maintenance_job(
                request, MaintenanceRun.objects.filter(pk=run.pk)
            )
        run.refresh_from_db()
        self.assertEqual(run.status, "running")
        self.assertIsNotNone(run.started_at)

    def test_trigger_action_marks_run_failed_on_submit_error(self):
        import subprocess

        run = MaintenanceRun.objects.create(job_type="integrity", status="pending")
        request = self._request(self.superuser)
        error = subprocess.CalledProcessError(
            1, ["dagster"], stderr=b"boom: code location failed to load"
        )

        with patch(
            "orchestration.admin._submit_maintenance_run", side_effect=error
        ):
            self.admin.trigger_maintenance_job(
                request, MaintenanceRun.objects.filter(pk=run.pk)
            )
        run.refresh_from_db()
        self.assertEqual(run.status, "failed")
        self.assertIn("code location failed to load", run.log)
        self.assertIsNotNone(run.finished_at)

    def test_trigger_action_marks_run_failed_when_subprocess_cannot_start(self):
        """The subprocess never launching at all (e.g. broken venv, missing
        interpreter) must be caught too, not just a launch that ran and
        failed -- FileNotFoundError/OSError previously propagated uncaught,
        crashing the whole admin action instead of marking just this run
        as failed."""
        run = MaintenanceRun.objects.create(job_type="integrity", status="pending")
        request = self._request(self.superuser)
        error = FileNotFoundError("no such file or directory: 'dagster'")

        with patch(
            "orchestration.admin._submit_maintenance_run", side_effect=error
        ):
            self.admin.trigger_maintenance_job(
                request, MaintenanceRun.objects.filter(pk=run.pk)
            )
        run.refresh_from_db()
        self.assertEqual(run.status, "failed")
        self.assertIn("no such file or directory", run.log)
        self.assertIsNotNone(run.finished_at)

    def test_trigger_action_skips_non_pending_runs(self):
        run = MaintenanceRun.objects.create(job_type="backup", status="running")
        request = self._request(self.superuser)

        with patch("orchestration.admin._submit_maintenance_run") as mock_submit:
            self.admin.trigger_maintenance_job(
                request, MaintenanceRun.objects.filter(pk=run.pk)
            )
            mock_submit.assert_not_called()

    def test_trigger_action_denied_for_non_superuser(self):
        run = MaintenanceRun.objects.create(job_type="backup", status="pending")
        request = self._request(self.regular_user)

        with patch("orchestration.admin._submit_maintenance_run") as mock_submit:
            self.admin.trigger_maintenance_job(
                request, MaintenanceRun.objects.filter(pk=run.pk)
            )
            mock_submit.assert_not_called()

    def test_save_model_sets_triggered_by_on_create(self):
        request = self._request(self.superuser)
        run = MaintenanceRun(job_type="backup")
        form = MagicMock()
        self.admin.save_model(request, run, form, change=False)
        self.assertEqual(run.triggered_by, self.superuser)

    def test_save_model_does_not_overwrite_triggered_by_on_update(self):
        other_user = User.objects.create_user(username="other", password="pw")
        run = MaintenanceRun.objects.create(
            job_type="backup", triggered_by=other_user
        )
        request = self._request(self.superuser)
        form = MagicMock()
        self.admin.save_model(request, run, form, change=True)
        # triggered_by should not change on update
        self.assertEqual(run.triggered_by, other_user)

    def test_save_model_sets_both_triggered_by_and_created_by(self):
        """F1 regression: MaintenanceRunAdmin's explicit triggered_by and
        BaseModel.save()'s created_by/updated_by (via CurrentUserMiddleware's
        thread-local state) must both end up set after a real save_model
        call, not just triggered_by."""
        request = self._request(self.superuser)
        CurrentUserMiddleware(lambda _r: None)(request)
        run = MaintenanceRun(job_type="backup")
        form = MagicMock()
        self.admin.save_model(request, run, form, change=False)
        self.assertEqual(run.triggered_by, self.superuser)
        self.assertEqual(run.created_by, self.superuser)
        self.assertEqual(run.updated_by, self.superuser)

    def test_download_link_returns_dash_when_no_file(self):
        run = MaintenanceRun(job_type="backup")
        result = self.admin.download_link(run)
        self.assertEqual(result, "—")

    def test_download_link_points_at_admin_view_not_raw_media_url(self):
        """Architecture-review fix: the link must route through the
        superuser-gated admin download view, not obj.result_file.url
        directly -- Django doesn't serve MEDIA_URL at all in production
        (see prototype/urls.py), so a raw .url link relies entirely on the
        reverse proxy happening to gate /media/, which nothing enforces."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        run = MaintenanceRun.objects.create(job_type="backup")
        run.result_file.save(
            "backup.sql.gz", SimpleUploadedFile("backup.sql.gz", b"dump-bytes")
        )
        try:
            result = self.admin.download_link(run)
            expected_url = reverse(
                "admin:orchestration_maintenancerun_download", args=[run.pk]
            )
            self.assertIn(expected_url, result)
            self.assertNotIn(run.result_file.url, result)
        finally:
            run.result_file.delete(save=False)

    def test_status_display_returns_status_value(self):
        run = MaintenanceRun(job_type="backup", status="success")
        self.assertEqual(self.admin.status_display(run), "success")


class DuckDBTableConfigAdminPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="pw", email="s@test.com"
        )
        cls.regular_user = User.objects.create_user(
            username="regular", password="pw", email="r@test.com"
        )

    def setUp(self):
        self.site = AdminSite()
        self.admin = DuckDBTableConfigAdmin(DuckDBTableConfig, self.site)
        self.factory = RequestFactory()

    def _request(self, user: User) -> object:
        request = self.factory.get("/")
        request.user = user
        return request

    def test_superuser_has_add_permission(self):
        self.assertTrue(self.admin.has_add_permission(self._request(self.superuser)))

    def test_regular_user_denied_add_permission(self):
        self.assertFalse(self.admin.has_add_permission(self._request(self.regular_user)))

    def test_superuser_has_view_permission(self):
        self.assertTrue(self.admin.has_view_permission(self._request(self.superuser)))

    def test_regular_user_denied_view_permission(self):
        self.assertFalse(self.admin.has_view_permission(self._request(self.regular_user)))


class SubmitMaintenanceRunTests(TestCase):
    def test_launch_command_targets_correct_job_and_repository(self):
        run = MaintenanceRun(pk=42, job_type="integrity")

        with patch("orchestration.admin.subprocess.run") as mock_run, patch(
            "orchestration.admin.sys.executable", "/usr/bin/python"
        ):
            _submit_maintenance_run(run)
            args = mock_run.call_args.args[0]

        self.assertIn("job", args)
        self.assertIn("launch", args)
        self.assertIn("orchestration.dagster_home.repository", args)
        self.assertIn("integrity_check_job", args)

    def test_launch_command_config_json_carries_run_id(self):
        import json

        run = MaintenanceRun(pk=42, job_type="integrity")

        with patch("orchestration.admin.subprocess.run") as mock_run:
            _submit_maintenance_run(run)
            args = mock_run.call_args.args[0]

        config_json = args[args.index("--config-json") + 1]
        config = json.loads(config_json)
        self.assertEqual(
            config["ops"]["run_integrity_checks"]["config"]["run_id"], 42
        )

    def test_launch_command_tags_carry_maintenance_run_id(self):
        import json

        run = MaintenanceRun(pk=7, job_type="backup", dump_format="plain")

        with patch("orchestration.admin.subprocess.run") as mock_run:
            _submit_maintenance_run(run)
            args = mock_run.call_args.args[0]

        tags_json = args[args.index("--tags") + 1]
        tags = json.loads(tags_json)
        self.assertEqual(tags["maintenance_run_id"], "7")

    def test_backup_dump_format_included_in_op_config(self):
        import json

        run = MaintenanceRun(pk=7, job_type="backup", dump_format="plain")

        with patch("orchestration.admin.subprocess.run") as mock_run:
            _submit_maintenance_run(run)
            args = mock_run.call_args.args[0]

        config_json = args[args.index("--config-json") + 1]
        config = json.loads(config_json)
        self.assertEqual(
            config["ops"]["run_pg_dump"]["config"]["dump_format"], "plain"
        )

    def test_run_called_with_check_true_and_timeout(self):
        run = MaintenanceRun(pk=1, job_type="duckdb")

        with patch("orchestration.admin.subprocess.run") as mock_run:
            _submit_maintenance_run(run)
            kwargs = mock_run.call_args.kwargs

        self.assertTrue(kwargs["check"])
        self.assertIsNotNone(kwargs.get("timeout"))

    def test_submission_failure_propagates_called_process_error(self):
        import subprocess

        run = MaintenanceRun(pk=1, job_type="backup")
        error = subprocess.CalledProcessError(1, ["dagster"], stderr=b"boom")

        with patch("orchestration.admin.subprocess.run", side_effect=error):
            with self.assertRaises(subprocess.CalledProcessError):
                _submit_maintenance_run(run)


class AdminChangelistAccessTests(TestCase):
    """Integration tests: superuser can access pages, regular user cannot."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="pw", email="s@test.com"
        )
        cls.regular_user = User.objects.create_user(
            username="regular", password="pw", email="r@test.com"
        )

    def test_superuser_can_access_maintenancerun_changelist(self):
        self.client.force_login(self.superuser)
        url = reverse("admin:orchestration_maintenancerun_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_regular_user_redirected_from_maintenancerun_changelist(self):
        self.client.force_login(self.regular_user)
        url = reverse("admin:orchestration_maintenancerun_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_superuser_can_access_duckdbtableconfig_changelist(self):
        self.client.force_login(self.superuser)
        url = reverse("admin:orchestration_duckdbtableconfig_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_regular_user_redirected_from_duckdbtableconfig_changelist(self):
        self.client.force_login(self.regular_user)
        url = reverse("admin:orchestration_duckdbtableconfig_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


class MaintenanceRunDownloadViewTests(TestCase):
    """Integration tests for the F1 architecture-review fix: the result-file
    download route must be reachable only by superusers, regardless of how
    the reverse proxy is configured for /media/ in production."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="dl_super", password="pw", email="dls@test.com"
        )
        # Staff (not superuser) -- the realistic threat model: someone with
        # *some* admin access, granted (even accidentally, per F4) view
        # permission on the wrong model, but not full superuser rights.
        cls.regular_user = User.objects.create_user(
            username="dl_regular", password="pw", email="dlr@test.com",
            is_staff=True,
        )

    def setUp(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.run = MaintenanceRun.objects.create(job_type="backup")
        self.run.result_file.save(
            "backup.sql.gz", SimpleUploadedFile("backup.sql.gz", b"dump-bytes")
        )
        self.addCleanup(lambda: self.run.result_file.delete(save=False))
        self.url = reverse(
            "admin:orchestration_maintenancerun_download", args=[self.run.pk]
        )

    def test_superuser_can_download(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"dump-bytes")

    def test_regular_user_gets_404_not_the_file(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_cannot_download(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (302, 403, 404))

    def test_superuser_gets_404_when_run_has_no_file(self):
        run = MaintenanceRun.objects.create(job_type="integrity")
        url = reverse(
            "admin:orchestration_maintenancerun_download", args=[run.pk]
        )
        self.client.force_login(self.superuser)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_superuser_gets_404_for_nonexistent_run(self):
        url = reverse(
            "admin:orchestration_maintenancerun_download", args=[999999]
        )
        self.client.force_login(self.superuser)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class IntegrityIssueInlineTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="super_inline", password="pw", email="si@test.com"
        )
        self.run = MaintenanceRun.objects.create(
            job_type="integrity", status="success"
        )
        self.issue_with_obj = IntegrityIssue.objects.create(
            run=self.run,
            check_type="orphan_samples",
            object_id=99,
            description="Sample 'X' has no location.",
        )
        self.issue_no_obj = IntegrityIssue.objects.create(
            run=self.run,
            check_type="guardian_maintenance_permissions",
            object_id=None,
            description="0 objects have guardian permissions.",
        )
        self.site = AdminSite()
        self.inline = IntegrityIssueInline(MaintenanceRun, self.site)
        self.factory = RequestFactory()

    def _request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_has_no_add_permission(self):
        request = self._request(self.superuser)
        self.assertFalse(self.inline.has_add_permission(request))

    def test_admin_link_with_object_id(self):
        link = self.inline.admin_link(self.issue_with_obj)
        self.assertIn("View →", link)
        self.assertIn("/field_data/sample/", link)

    def test_admin_link_without_object_id(self):
        link = self.inline.admin_link(self.issue_no_obj)
        self.assertEqual(link, "—")

    def test_admin_link_unknown_check_type(self):
        issue = IntegrityIssue(
            run=self.run, check_type="unknown_check", object_id=5, description="x"
        )
        link = self.inline.admin_link(issue)
        self.assertEqual(link, "5")


class IssuesSummaryDisplayTests(TestCase):
    def setUp(self):
        self.run_integrity = MaintenanceRun.objects.create(
            job_type="integrity", status="success"
        )
        IntegrityIssue.objects.create(
            run=self.run_integrity,
            check_type="orphan_samples",
            object_id=1,
            description="a",
        )
        IntegrityIssue.objects.create(
            run=self.run_integrity,
            check_type="orphan_samples",
            object_id=2,
            description="b",
        )
        IntegrityIssue.objects.create(
            run=self.run_integrity,
            check_type="guardian_maintenance_permissions",
            description="0 objects.",
        )
        self.run_backup = MaintenanceRun.objects.create(
            job_type="backup", status="success"
        )
        self.run_pending = MaintenanceRun.objects.create(
            job_type="integrity", status="pending"
        )
        self.site = AdminSite()
        self.admin = MaintenanceRunAdmin(MaintenanceRun, self.site)

    def test_dash_for_non_integrity_run(self):
        result = self.admin.issues_summary(self.run_backup)
        self.assertEqual(result, "—")

    def test_dash_for_non_success_integrity_run(self):
        result = self.admin.issues_summary(self.run_pending)
        self.assertEqual(result, "—")

    def test_shows_orphan_count(self):
        result = self.admin.issues_summary(self.run_integrity)
        self.assertIn("2", result)
        self.assertIn("Orphans", result)

    def test_shows_link_to_orphan_changelist(self):
        result = self.admin.issues_summary(self.run_integrity)
        self.assertIn("field_data/sample/", result)
        self.assertIn("location__isnull=True", result)

    def test_shows_guardian_count(self):
        result = self.admin.issues_summary(self.run_integrity)
        self.assertIn("Guardian", result)
