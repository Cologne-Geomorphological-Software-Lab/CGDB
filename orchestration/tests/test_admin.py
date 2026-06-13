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
    _fire_maintenance_subprocess,
)
from orchestration.models import DuckDBTableConfig, IntegrityIssue, MaintenanceRun


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

    def test_trigger_action_fires_subprocess_for_pending_runs(self):
        run = MaintenanceRun.objects.create(job_type="integrity", status="pending")
        request = self._request(self.superuser)

        with patch(
            "orchestration.admin._fire_maintenance_subprocess"
        ) as mock_fire:
            self.admin.trigger_maintenance_job(
                request, MaintenanceRun.objects.filter(pk=run.pk)
            )
            mock_fire.assert_called_once_with(run)

    def test_trigger_action_skips_non_pending_runs(self):
        run = MaintenanceRun.objects.create(job_type="backup", status="running")
        request = self._request(self.superuser)

        with patch(
            "orchestration.admin._fire_maintenance_subprocess"
        ) as mock_fire:
            self.admin.trigger_maintenance_job(
                request, MaintenanceRun.objects.filter(pk=run.pk)
            )
            mock_fire.assert_not_called()

    def test_trigger_action_denied_for_non_superuser(self):
        run = MaintenanceRun.objects.create(job_type="backup", status="pending")
        request = self._request(self.regular_user)

        with patch(
            "orchestration.admin._fire_maintenance_subprocess"
        ) as mock_fire:
            self.admin.trigger_maintenance_job(
                request, MaintenanceRun.objects.filter(pk=run.pk)
            )
            mock_fire.assert_not_called()

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

    def test_download_link_returns_dash_when_no_file(self):
        run = MaintenanceRun(job_type="backup")
        result = self.admin.download_link(run)
        self.assertEqual(result, "—")

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


class FireMaintenanceSubprocessTests(TestCase):
    def test_popen_called_with_correct_args(self):
        run = MaintenanceRun(pk=42, job_type="integrity")

        with patch("orchestration.admin.subprocess.Popen") as mock_popen, patch(
            "orchestration.admin.sys.executable", "/usr/bin/python"
        ):
            _fire_maintenance_subprocess(run)
            args = mock_popen.call_args.args[0]

        self.assertIn("run_maintenance_job", args)
        self.assertIn("integrity", args)
        self.assertIn("--run-id", args)
        self.assertIn("42", args)

    def test_popen_stdout_stderr_devnull(self):
        import subprocess

        run = MaintenanceRun(pk=1, job_type="backup")

        with patch("orchestration.admin.subprocess.Popen") as mock_popen:
            _fire_maintenance_subprocess(run)
            kwargs = mock_popen.call_args.kwargs

        self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)


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
