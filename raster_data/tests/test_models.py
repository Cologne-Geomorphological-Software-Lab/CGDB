"""Unit tests for raster_data models."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import ClassVar

from django.contrib.gis.geos import GEOSGeometry
from django.db import IntegrityError
from django.test import TestCase, override_settings

from prototype.models import Project
from raster_data.models import DataSource, RasterDataset, RasterScene

_BBOX_WKT = "POLYGON ((6.0 50.0, 8.0 50.0, 8.0 52.0, 6.0 52.0, 6.0 50.0))"


class DataSourceTest(TestCase):
    def test_str(self) -> None:
        ds = DataSource(name="Sentinel-2 L2A")
        assert str(ds) == "Sentinel-2 L2A"

    def test_unique_name(self) -> None:
        DataSource.objects.create(name="S2")
        with self.assertRaises(IntegrityError):
            DataSource.objects.create(name="S2")

    def test_band_descriptions_defaults_to_empty_list(self) -> None:
        ds = DataSource.objects.create(name="DEM")
        assert ds.band_descriptions == []


class RasterSceneTest(TestCase):
    project: ClassVar[Project]
    data_source: ClassVar[DataSource]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.project = Project.objects.create(
            title="Raster Project", label="RP01", status="ACTIVE"
        )
        cls.data_source = DataSource.objects.create(
            name="Sentinel-2 L2A", provider="ESA"
        )

    def _scene(self, **kwargs: object) -> RasterScene:
        defaults = {
            "project": self.project,
            "data_source": self.data_source,
            "n_bands": 4,
            "resolution_m": 10.0,
        }
        defaults.update(kwargs)
        return RasterScene.objects.create(**defaults)

    def test_effective_path_prefers_corpus_path(self) -> None:
        scene = self._scene(corpus_path="corpus/scenes/s2_001.tif")
        assert scene.effective_path == "corpus/scenes/s2_001.tif"

    def test_effective_path_falls_back_to_file_name(self) -> None:
        scene = self._scene(corpus_path="")
        assert scene.effective_path == ""

    def test_str_includes_data_source_name(self) -> None:
        scene = self._scene(corpus_path="corpus/scenes/s2_001.tif")
        assert "Sentinel-2 L2A" in str(scene)

    def test_str_without_data_source(self) -> None:
        scene = self._scene(data_source=None, corpus_path="corpus/scenes/x.tif")
        assert "—" in str(scene)

    def test_cloud_cover_validator_accepts_valid(self) -> None:
        scene = self._scene(cloud_cover_pct=42.5)
        scene.full_clean()

    def test_spatial_bbox_stored_as_polygon(self) -> None:
        geom = GEOSGeometry(_BBOX_WKT, srid=4326)
        scene = self._scene(spatial_bbox=geom)
        reloaded = RasterScene.objects.get(pk=scene.pk)
        assert reloaded.spatial_bbox is not None

    def test_classification_fields_optional(self) -> None:
        scene = self._scene()
        assert scene.n_classes is None
        assert scene.class_names == []

    def test_classification_fields_stored(self) -> None:
        scene = self._scene(n_classes=5, class_names=["forest", "water", "urban", "crops", "bare"])
        reloaded = RasterScene.objects.get(pk=scene.pk)
        assert reloaded.n_classes == 5
        assert reloaded.class_names[0] == "forest"

    def test_spatial_intersection_finds_overlapping_scene(self) -> None:
        geom_a = GEOSGeometry(_BBOX_WKT, srid=4326)
        inner_wkt = "POLYGON ((6.5 50.5, 7.5 50.5, 7.5 51.5, 6.5 51.5, 6.5 50.5))"
        geom_b = GEOSGeometry(inner_wkt, srid=4326)
        scene_a = self._scene(spatial_bbox=geom_a, corpus_path="a.tif")
        self._scene(spatial_bbox=geom_b, corpus_path="b.tif")
        hits = RasterScene.objects.filter(
            spatial_bbox__intersects=scene_a.spatial_bbox
        )
        assert hits.count() == 2


@override_settings(
    RASTER_CORPUS_ROOT=Path(tempfile.gettempdir()) / "cgdb_corpus_test"
)
class RasterSceneCorpusPathValidationTest(TestCase):
    """Architecture-review fix (F6): corpus_path must not let a
    project-scoped user point at an arbitrary server filesystem path.

    Narrows RASTER_CORPUS_ROOT to a real, restrictive value for this class
    only — the global test-settings default is deliberately permissive (see
    prototype/test_settings.py) so the rest of the suite's pre-existing,
    arbitrary corpus_path fixtures aren't affected by this check.
    """

    project: ClassVar[Project]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.project = Project.objects.create(
            title="Corpus Validation Project", label="CVP01", status="ACTIVE"
        )

    def test_relative_corpus_path_under_root_is_allowed(self) -> None:
        """A relative path is resolved against RASTER_CORPUS_ROOT itself --
        one that stays under the root must keep working."""
        scene = RasterScene.objects.create(
            project=self.project, corpus_path="corpus/scenes/relative.tif"
        )
        assert scene.corpus_path == "corpus/scenes/relative.tif"

    def test_relative_corpus_path_traversal_is_rejected(self) -> None:
        """A relative value with enough ".." segments walks past
        RASTER_CORPUS_ROOT and must be rejected the same as an absolute
        path outside it -- this is the exploit F6 exists to close."""
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            RasterScene.objects.create(
                project=self.project,
                corpus_path="../../../../../../../../etc/passwd",
            )
        assert not RasterScene.objects.filter(
            corpus_path="../../../../../../../../etc/passwd"
        ).exists()

    def test_absolute_corpus_path_under_configured_root_is_allowed(self) -> None:
        from django.conf import settings

        allowed = str(Path(settings.RASTER_CORPUS_ROOT) / "scenes" / "ok.tif")
        scene = RasterScene.objects.create(
            project=self.project, corpus_path=allowed
        )
        assert scene.corpus_path == allowed

    def test_absolute_corpus_path_outside_configured_root_is_rejected(self) -> None:
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            RasterScene.objects.create(
                project=self.project,
                corpus_path="/etc/passwd",
            )
        assert not RasterScene.objects.filter(
            corpus_path="/etc/passwd"
        ).exists()

    def test_path_traversal_out_of_root_is_rejected(self) -> None:
        """corpus_path="<root>/../../etc/passwd" must not escape the root
        via ".." segments -- resolve() normalizes these before the check."""
        from django.conf import settings
        from django.core.exceptions import ValidationError

        escaping = str(
            Path(settings.RASTER_CORPUS_ROOT) / ".." / ".." / "etc" / "passwd"
        )
        with self.assertRaises(ValidationError):
            RasterScene.objects.create(project=self.project, corpus_path=escaping)

    def test_blank_corpus_path_is_unaffected(self) -> None:
        scene = RasterScene.objects.create(project=self.project, corpus_path="")
        assert scene.corpus_path == ""


class RasterDatasetTest(TestCase):
    project: ClassVar[Project]
    scene: ClassVar[RasterScene]
    dataset: ClassVar[RasterDataset]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.project = Project.objects.create(
            title="Dataset Project", label="DS01", status="ACTIVE"
        )
        cls.scene = RasterScene.objects.create(project=cls.project)
        cls.dataset = RasterDataset.objects.create(
            project=cls.project,
            name="Test Dataset",
            slug="test-dataset",
        )

    def test_str(self) -> None:
        assert str(self.dataset) == "Test Dataset"

    def test_unique_slug(self) -> None:
        with self.assertRaises(IntegrityError):
            RasterDataset.objects.create(
                project=self.project,
                name="Other",
                slug="test-dataset",
            )

    def test_add_scene(self) -> None:
        self.dataset.scenes.add(self.scene)
        assert self.dataset.scenes.count() == 1
        self.dataset.scenes.remove(self.scene)

    def test_scene_count_via_reverse(self) -> None:
        self.dataset.scenes.add(self.scene)
        assert self.scene.datasets.filter(pk=self.dataset.pk).exists()
        self.dataset.scenes.remove(self.scene)
