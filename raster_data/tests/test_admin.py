"""Integration tests for RasterSceneAdmin's "Recompute metadata from file" action."""

from __future__ import annotations

import os
import tempfile
from typing import TYPE_CHECKING, ClassVar
from unittest import mock

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import Permission, User
from django.contrib.gis.gdal import GDALRaster
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from guardian.shortcuts import assign_perm

from prototype.models import Project
from raster_data.models import DataSource, RasterScene

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse


def _remove_if_exists(path: str) -> None:
    if os.path.exists(path):  # noqa: PTH110
        os.remove(path)  # noqa: PTH107


def _make_geotiff(path: str, *, nr_of_bands: int = 2) -> None:
    """Write a tiny synthetic 4326 GeoTIFF with a known extent to *path*."""
    raster = GDALRaster(
        {
            "driver": "GTiff",
            "name": path,
            "width": 4,
            "height": 4,
            "srid": 4326,
            "origin": [6.0, 52.0],
            "scale": [0.5, -0.5],
            "nr_of_bands": nr_of_bands,
        }
    )
    del raster


class RecomputeMetadataActionTest(TestCase):
    project: ClassVar[Project]
    superuser: ClassVar[User]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.project = Project.objects.create(
            title="Raster Admin Test", label="RAT01", status="ACTIVE"
        )
        cls.superuser = User.objects.create_superuser(
            "raster_admin", "ra@test.com", "pw"
        )

    def setUp(self) -> None:
        self.client.force_login(self.superuser)
        fd, self.tif_path = tempfile.mkstemp(suffix=".tif")
        os.close(fd)

    def tearDown(self) -> None:
        if os.path.exists(self.tif_path):  # noqa: PTH110
            os.remove(self.tif_path)  # noqa: PTH107

    def _run_action(self, scene_ids: list[int]) -> _MonkeyPatchedWSGIResponse:
        url = reverse("admin:raster_data_rasterscene_changelist")
        data = {
            "action": "recompute_metadata_from_file",
            ACTION_CHECKBOX_NAME: [str(pk) for pk in scene_ids],
        }
        return self.client.post(url, data, follow=True)

    def test_updates_metadata_from_valid_corpus_path_file(self) -> None:
        _make_geotiff(self.tif_path)
        scene = RasterScene.objects.create(
            project=self.project, corpus_path=self.tif_path
        )
        response = self._run_action([scene.pk])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recomputed metadata for 1 of 1 scene(s).")

        scene.refresh_from_db()
        self.assertEqual(scene.crs, "EPSG:4326")
        self.assertEqual(scene.n_bands, 2)
        assert scene.spatial_bbox is not None
        self.assertEqual(
            scene.spatial_bbox.extent, (6.0, 50.0, 8.0, 52.0)
        )

    def test_skips_missing_corpus_path_with_warning(self) -> None:
        scene = RasterScene.objects.create(
            project=self.project,
            corpus_path="/no/such/path/does_not_exist.tif",
        )
        response = self._run_action([scene.pk])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "is not reachable from this server")

        scene.refresh_from_db()
        self.assertEqual(scene.crs, "")
        self.assertIsNone(scene.n_bands)

    def test_skips_record_with_no_file_or_corpus_path(self) -> None:
        scene = RasterScene.objects.create(project=self.project)
        response = self._run_action([scene.pk])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no file or corpus_path set")

    def test_reports_error_for_non_raster_file(self) -> None:
        with open(self.tif_path, "w") as fh:  # noqa: PTH123
            fh.write("not a raster")
        scene = RasterScene.objects.create(
            project=self.project, corpus_path=self.tif_path
        )
        response = self._run_action([scene.pk])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Could not open")

        scene.refresh_from_db()
        self.assertEqual(scene.crs, "")

    def test_mixed_selection_reports_partial_success(self) -> None:
        _make_geotiff(self.tif_path)
        good_scene = RasterScene.objects.create(
            project=self.project, corpus_path=self.tif_path
        )
        bad_scene = RasterScene.objects.create(
            project=self.project,
            corpus_path="/no/such/path/does_not_exist.tif",
        )
        response = self._run_action([good_scene.pk, bad_scene.pk])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recomputed metadata for 1 of 2 scene(s).")

        good_scene.refresh_from_db()
        bad_scene.refresh_from_db()
        self.assertEqual(good_scene.crs, "EPSG:4326")
        self.assertEqual(bad_scene.crs, "")

    def test_selection_over_cap_is_rejected_without_processing(self) -> None:
        """tech debt R7: each file is opened synchronously in the request/
        worker thread - an oversized selection must be rejected up front,
        not partially processed until a timeout."""
        _make_geotiff(self.tif_path)
        scene = RasterScene.objects.create(
            project=self.project, corpus_path=self.tif_path
        )
        with mock.patch("raster_data.admin._MAX_RECOMPUTE_SCENES", 0):
            response = self._run_action([scene.pk])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "processes at most 0 at a time")

        scene.refresh_from_db()
        self.assertEqual(
            scene.crs, "", "scene must be untouched when the cap is exceeded"
        )

    def test_recompute_avoids_n_plus_one_for_data_source(self) -> None:
        """tech debt R7: every message_user() call that reports a per-scene
        warning/error formats the scene via RasterScene.__str__, which reads
        self.data_source.name - without select_related, that's one extra
        query per such scene. Using scenes with a missing corpus_path (the
        "not reachable" warning path) reliably exercises __str__, unlike a
        successful recompute, which never formats the scene at all."""
        data_source = DataSource.objects.create(name="Sentinel-2")
        scenes = [
            RasterScene.objects.create(
                project=self.project,
                corpus_path=f"/no/such/path/does_not_exist_{i}.tif",
                data_source=data_source,
            )
            for i in range(3)
        ]
        url = reverse("admin:raster_data_rasterscene_changelist")
        data = {
            "action": "recompute_metadata_from_file",
            ACTION_CHECKBOX_NAME: [str(s.pk) for s in scenes],
        }
        # follow=False: only capture the POST that runs the action itself -
        # following the redirect would also capture the changelist page's
        # own (separate, pre-existing, out-of-scope-for-R7) re-render query.
        # The N+1 signature is a per-row "WHERE data_source.id = <pk>"
        # lookup, not just any query mentioning the table (autocomplete_
        # fields and list_filter already issue their own unrelated bulk
        # "SELECT ... ORDER BY name" query regardless of this fix).
        with CaptureQueriesContext(connection) as ctx:
            self.client.post(url, data, follow=False)
        per_row_lookup_marker = 'raster_data_datasource"."id" = '
        per_row_lookups = [
            q
            for q in ctx.captured_queries
            if per_row_lookup_marker in q["sql"]
        ]
        self.assertEqual(
            per_row_lookups,
            [],
            "select_related('data_source') should make the 3 scenes' "
            f"data_source come from the JOIN, not per-row lookups: {per_row_lookups}",
        )


class RasterSceneAdminNonSuperuserAccessTest(TestCase):
    """Regression test for a field-name collision in ProjectBasedPermissionMixin.

    RasterScene.data_source is a ForeignKey, but the mixin's literature-
    detection heuristic used to treat any field literally named
    "data_source" as the literature-marker CharField convention, filtering
    with Q(data_source="literature") — a ValueError against a ForeignKey.
    Every non-superuser hit this on the plain changelist, with no need for
    any data_source value to be set on a scene.
    """

    project: ClassVar[Project]
    staff_user: ClassVar[User]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.project = Project.objects.create(
            title="Scoped Raster Project", label="SRP01", status="ACTIVE"
        )
        cls.staff_user = User.objects.create_user(
            username="raster_scoped_staff",
            password="pw",
            email="rss@test.com",
            is_staff=True,
        )
        cls.staff_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="raster_data",
                codename="view_rasterscene",
            )
        )
        assign_perm("view_project", cls.staff_user, cls.project)

    def test_project_scoped_staff_user_can_load_changelist(self) -> None:
        RasterScene.objects.create(project=self.project)
        self.client.force_login(self.staff_user)
        url = reverse("admin:raster_data_rasterscene_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class LocalPathPrecedenceTest(TestCase):
    """tech debt R2: for a scene with both corpus_path and file set,
    _local_path_for (used by "Recompute metadata from file") must read the
    same physical file RasterScene.effective_path treats as authoritative
    (corpus_path first) - not silently read the other one."""

    project: ClassVar[Project]
    superuser: ClassVar[User]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.project = Project.objects.create(
            title="Precedence Test Project", label="RPT01", status="ACTIVE"
        )
        cls.superuser = User.objects.create_superuser(
            "precedence_admin", "pa@test.com", "pw"
        )

    def setUp(self) -> None:
        self.client.force_login(self.superuser)

    def test_recompute_reads_corpus_path_not_file_when_both_set(self) -> None:
        from django.core.files.uploadedfile import SimpleUploadedFile

        fd, corpus_tif_path = tempfile.mkstemp(suffix=".tif")
        os.close(fd)
        self.addCleanup(lambda: _remove_if_exists(corpus_tif_path))
        _make_geotiff(corpus_tif_path, nr_of_bands=2)

        fd2, file_field_tif_path = tempfile.mkstemp(suffix=".tif")
        os.close(fd2)
        self.addCleanup(lambda: _remove_if_exists(file_field_tif_path))
        _make_geotiff(file_field_tif_path, nr_of_bands=5)

        with open(file_field_tif_path, "rb") as fh:  # noqa: PTH123
            scene = RasterScene.objects.create(
                project=self.project,
                corpus_path=corpus_tif_path,
                file=SimpleUploadedFile("file_field.tif", fh.read()),
            )
        self.addCleanup(lambda: scene.file.delete(save=False))

        url = reverse("admin:raster_data_rasterscene_changelist")
        data = {
            "action": "recompute_metadata_from_file",
            ACTION_CHECKBOX_NAME: [str(scene.pk)],
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)

        scene.refresh_from_db()
        self.assertEqual(
            scene.n_bands,
            2,
            "recompute read file (5 bands) instead of corpus_path (2 bands) "
            "- effective_path prefers corpus_path, _local_path_for must too.",
        )
