"""Tests for the move_protected_media management command.

Installations before 2.0.2 kept uploads and backups under MEDIA_ROOT. The
command moves them to the same relative paths under PROTECTED_MEDIA_ROOT,
where the FileFields now look for them.
"""

import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings


class MoveProtectedMediaTest(SimpleTestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.media = Path(tmp.name) / "media"
        self.protected = Path(tmp.name) / "protected"
        self.media.mkdir()
        override = override_settings(
            MEDIA_ROOT=str(self.media), PROTECTED_MEDIA_ROOT=str(self.protected)
        )
        override.enable()
        self.addCleanup(override.disable)

    def _put(self, root, relative, content=b"data"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def _call(self, *args):
        out = StringIO()
        call_command("move_protected_media", *args, stdout=out)
        return out.getvalue()

    def test_moves_protected_files_and_keeps_public_ones(self):
        self._put(self.media, "field_photos/a.jpg", b"photo")
        self._put(self.media, "maintenance/backup_1.sqlite3.gz", b"dump")
        self._put(self.media, "unrelated/logo.png", b"logo")

        output = self._call()

        self.assertEqual(
            (self.protected / "field_photos/a.jpg").read_bytes(), b"photo"
        )
        self.assertEqual(
            (self.protected / "maintenance/backup_1.sqlite3.gz").read_bytes(),
            b"dump",
        )
        self.assertFalse((self.media / "field_photos").exists())
        self.assertFalse((self.media / "maintenance").exists())
        # Files outside the protected prefixes stay where they are.
        self.assertTrue((self.media / "unrelated/logo.png").exists())
        self.assertIn("Moved 2 file(s)", output)

    def test_dry_run_changes_nothing(self):
        source = self._put(self.media, "analysis/raw_data/r.bin")
        output = self._call("--dry-run")
        self.assertTrue(source.exists())
        self.assertFalse(self.protected.exists())
        self.assertIn("analysis/raw_data/r.bin", output)
        self.assertIn("Would move 1 file(s)", output)

    def test_second_run_finds_nothing_to_move(self):
        self._put(self.media, "field_photos/a.jpg")
        self._call()
        self.assertIn("Nothing to move", self._call())

    def test_identical_copy_at_the_target_completes_the_move(self):
        """An interrupted earlier run may have copied without deleting."""
        source = self._put(self.media, "field_photos/a.jpg", b"same")
        self._put(self.protected, "field_photos/a.jpg", b"same")
        self._call()
        self.assertFalse(source.exists())
        self.assertEqual(
            (self.protected / "field_photos/a.jpg").read_bytes(), b"same"
        )

    def test_different_file_at_the_target_aborts_before_moving_anything(self):
        first = self._put(self.media, "field_photos/a.jpg", b"new")
        second = self._put(self.media, "field_photos/b.jpg", b"other")
        target = self._put(self.protected, "field_photos/a.jpg", b"old")
        with self.assertRaisesMessage(CommandError, "field_photos/a.jpg"):
            self._call()
        self.assertTrue(first.exists())
        self.assertTrue(second.exists())
        self.assertFalse((self.protected / "field_photos/b.jpg").exists())
        self.assertEqual(target.read_bytes(), b"old")

    def test_missing_media_root_is_nothing_to_move(self):
        with override_settings(MEDIA_ROOT=str(self.media / "does-not-exist")):
            self.assertIn("Nothing to move", self._call())

    def test_empty_media_root_means_the_working_directory_like_django(self):
        """Django's FileSystemStorage stores uploads relative to the current
        directory when MEDIA_ROOT is empty, so that's where they are."""
        import os

        self._put(self.media, "field_photos/cwd.jpg", b"cwd")
        cwd = Path.cwd()
        os.chdir(self.media)
        self.addCleanup(os.chdir, cwd)
        with override_settings(MEDIA_ROOT=""):
            self._call()
        self.assertEqual(
            (self.protected / "field_photos/cwd.jpg").read_bytes(), b"cwd"
        )
