"""Integration tests for RasterSceneAdmin's "Recompute metadata from file" action."""

from __future__ import annotations

import os
import tempfile
from typing import TYPE_CHECKING, ClassVar

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import Permission, User
from django.contrib.gis.gdal import GDALRaster
from django.test import TestCase
from django.urls import reverse
from guardian.shortcuts import assign_perm

from prototype.models import Project
from raster_data.models import RasterScene

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse


def _make_geotiff(path: str) -> None:
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
            "nr_of_bands": 2,
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
