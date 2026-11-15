"""Tests for the protected file storage, its download view and system checks."""

from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from guardian.shortcuts import assign_perm

from field_data.models import FieldPhoto, Location
from prototype import protected_media
from prototype.checks import (
    check_no_protected_files_in_media_root,
    check_protected_media_root,
    check_protected_media_server,
)
from prototype.models import Project
from prototype.protected_media import ProtectedFileRule, is_safe_name
from prototype.storage import ProtectedFileSystemStorage, protected_storage
from prototype.tests.roles import give_role

_PHOTO_RULE = {
    "field_photos/": ProtectedFileRule(
        model="field_data.FieldPhoto",
        field="file",
        project_paths=(
            "content_object__project",
            "content_object__location__project",
        ),
    )
}


class ProtectedStorageTest(SimpleTestCase):
    def test_url_points_at_the_permission_checked_view(self):
        self.assertEqual(
            protected_storage.url("field_photos/a b.jpg"),
            "/files/field_photos/a%20b.jpg",
        )

    def test_location_follows_protected_media_root(self):
        storage = ProtectedFileSystemStorage()
        with override_settings(PROTECTED_MEDIA_ROOT="/srv/cgdb/protected"):
            self.assertEqual(
                Path(storage.location), Path("/srv/cgdb/protected").resolve()
            )

    def test_unsafe_names_are_rejected(self):
        for name in ["", "../secret", "a/../../b", "/etc/passwd", "a\\b", "a\x00"]:
            self.assertFalse(is_safe_name(name), name)
        self.assertTrue(is_safe_name("field_photos/2026/photo.jpg"))


@patch.dict(protected_media.RULES, _PHOTO_RULE, clear=True)
class ProtectedMediaViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(title="P", label="P")
        cls.other = Project.objects.create(title="O", label="O")
        cls.location = Location.objects.create(
            identifier="PM-1", project=cls.project, data_source="internal"
        )
        cls.photo = FieldPhoto.objects.create(
            content_object=cls.location,
            file=SimpleUploadedFile("photo.jpg", b"jpeg-bytes"),
        )
        cls.name = cls.photo.file.name
        cls.member = cls._staff("pm_member", role="Viewer")
        assign_perm("view_project", cls.member, cls.project)
        cls.outsider = cls._staff("pm_outsider", role="Viewer")
        assign_perm("view_project", cls.outsider, cls.other)
        cls.no_role = cls._staff("pm_no_role", role=None)
        assign_perm("view_project", cls.no_role, cls.project)
        cls.superuser = User.objects.create_superuser(
            username="pm_root", password="pw", email="root@test.com"
        )

    @classmethod
    def _staff(cls, name, role):
        user = User.objects.create_user(
            username=name, password="pw", is_staff=True
        )
        if role:
            give_role(user, role)
        return user

    def _get(self, user, name=None):
        if user is not None:
            self.client.force_login(user)
        return self.client.get(f"/files/{name or self.name}")

    def test_member_with_role_downloads_the_file(self):
        response = self._get(self.member)
        self.assertEqual(response.status_code, 200)
        # Iterating a streaming response yields its body chunks.
        body = b"".join(response)
        self.assertEqual(body, b"jpeg-bytes")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_superuser_downloads_the_file(self):
        self.assertEqual(self._get(self.superuser).status_code, 200)

    def test_user_without_project_access_gets_404(self):
        self.assertEqual(self._get(self.outsider).status_code, 404)

    def test_member_without_role_gets_404(self):
        self.assertEqual(self._get(self.no_role).status_code, 404)

    def test_anonymous_user_is_sent_to_login(self):
        response = self._get(None)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_unknown_prefix_missing_owner_and_traversal_give_404(self):
        for name in [
            "elsewhere/photo.jpg",
            "field_photos/not-owned-by-anyone.jpg",
            "field_photos/../../settings.py",
        ]:
            self.assertEqual(self._get(self.superuser, name).status_code, 404)

    @override_settings(PROTECTED_MEDIA_SERVER="x-sendfile")
    def test_x_sendfile_hands_the_path_to_the_web_server(self):
        response = self._get(self.member)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Sendfile"], self.photo.file.path)
        self.assertEqual(response.content, b"")
        self.assertIn("attachment", response["Content-Disposition"])

    @override_settings(
        PROTECTED_MEDIA_SERVER="x-accel-redirect",
        PROTECTED_MEDIA_ACCEL_PREFIX="/internal/",
    )
    def test_x_accel_redirect_hands_the_name_to_nginx(self):
        response = self._get(self.member)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Accel-Redirect"], f"/internal/{self.name}")
        self.assertEqual(response.content, b"")


class ProtectedMediaChecksTest(SimpleTestCase):
    def _ids(self, messages):
        return [m.id for m in messages]

    @override_settings(PROTECTED_MEDIA_ROOT="")
    def test_missing_root_is_an_error(self):
        self.assertEqual(
            self._ids(check_protected_media_root(app_configs=None)),
            ["prototype.E001"],
        )

    def test_root_inside_media_or_static_root_is_an_error(self):
        with override_settings(
            MEDIA_ROOT="/srv/media", PROTECTED_MEDIA_ROOT="/srv/media/private"
        ):
            self.assertEqual(
                self._ids(check_protected_media_root(app_configs=None)),
                ["prototype.E002"],
            )
        with override_settings(
            STATIC_ROOT="/srv/static", PROTECTED_MEDIA_ROOT="/srv/static"
        ):
            self.assertEqual(
                self._ids(check_protected_media_root(app_configs=None)),
                ["prototype.E002"],
            )

    def test_root_beside_media_root_is_fine(self):
        with override_settings(
            MEDIA_ROOT="/srv/media", PROTECTED_MEDIA_ROOT="/srv/protected"
        ):
            self.assertEqual(check_protected_media_root(app_configs=None), [])

    def test_server_mode_must_be_known_and_complete(self):
        with override_settings(PROTECTED_MEDIA_SERVER="apache"):
            self.assertEqual(
                self._ids(check_protected_media_server(app_configs=None)),
                ["prototype.E003"],
            )
        with override_settings(
            PROTECTED_MEDIA_SERVER="x-accel-redirect",
            PROTECTED_MEDIA_ACCEL_PREFIX="",
        ):
            self.assertEqual(
                self._ids(check_protected_media_server(app_configs=None)),
                ["prototype.E004"],
            )
        self.assertEqual(check_protected_media_server(app_configs=None), [])

    @patch.dict(protected_media.RULES, _PHOTO_RULE, clear=True)
    def test_protected_files_left_in_media_root_are_reported(self):
        import tempfile

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self.assertEqual(
                    check_no_protected_files_in_media_root(app_configs=None),
                    [],
                )
                leftover = Path(media_root) / "field_photos" / "old.jpg"
                leftover.parent.mkdir()
                leftover.write_bytes(b"x")
                self.assertEqual(
                    self._ids(
                        check_no_protected_files_in_media_root(app_configs=None)
                    ),
                    ["prototype.W001"],
                )

    def test_checks_are_registered_with_django(self):
        from django.core.checks import run_checks

        with override_settings(PROTECTED_MEDIA_SERVER="apache"):
            ids = self._ids(run_checks(tags=["security"]))
        self.assertIn("prototype.E003", ids)
