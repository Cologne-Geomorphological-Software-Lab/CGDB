"""Maintenance results (backups, exports, reports) live in protected storage.

They hold the whole database, password hashes included. Under MEDIA_ROOT a
web server serving /media/ could hand them to anyone who guesses the
timestamped file name; in protected storage only a superuser can fetch them,
through the permission-checked view.
"""

import json
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from orchestration.admin import _submit_maintenance_run
from orchestration.models import MaintenanceRun
from orchestration.paths import maintenance_output_dir
from prototype.storage import ProtectedFileSystemStorage
from prototype.tests.roles import give_role


class MaintenanceResultStorageTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="mr_root", password="pw", email="root@test.com"
        )
        cls.staff = give_role(
            User.objects.create_user(
                username="mr_staff", password="pw", is_staff=True
            )
        )

    def setUp(self):
        self.maint_run = MaintenanceRun.objects.create(job_type="backup")
        self.maint_run.result_file.save(
            "backup.sql.gz", SimpleUploadedFile("backup.sql.gz", b"dump")
        )
        self.addCleanup(lambda: self.maint_run.result_file.delete(save=False))

    def test_result_file_is_stored_outside_media_root(self):
        self.assertIsInstance(
            self.maint_run.result_file.storage, ProtectedFileSystemStorage
        )
        path = Path(self.maint_run.result_file.path)
        self.assertTrue(
            path.is_relative_to(Path(settings.PROTECTED_MEDIA_ROOT).resolve())
        )
        self.assertFalse(
            path.is_relative_to(Path(settings.MEDIA_ROOT).resolve())
        )

    def test_result_file_url_is_the_protected_view(self):
        self.assertTrue(self.maint_run.result_file.url.startswith("/files/maintenance/"))

    def test_only_superusers_can_fetch_results(self):
        url = self.maint_run.result_file.url
        self.client.force_login(self.superuser)
        response = self.client.get(url)
        response.close()  # release the file handle (Windows locks open files)
        self.assertEqual(response.status_code, 200)
        # A Principal Investigator has every model permission, still no access.
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 404)


class MaintenanceOutputDirTest(TestCase):
    def test_output_dir_is_under_protected_media_root(self):
        self.assertEqual(
            maintenance_output_dir(),
            Path(settings.PROTECTED_MEDIA_ROOT) / "maintenance",
        )

    def test_admin_trigger_sends_jobs_to_the_protected_dir(self):
        run = MaintenanceRun.objects.create(job_type="integrity")
        with patch("orchestration.admin.subprocess.run") as subprocess_run:
            _submit_maintenance_run(run)
        argv = subprocess_run.call_args.args[0]
        config = json.loads(argv[argv.index("--config-json") + 1])
        op_config = next(iter(config["ops"].values()))["config"]
        self.assertEqual(op_config["output_dir"], str(maintenance_output_dir()))
