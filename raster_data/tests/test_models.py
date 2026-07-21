"""Unit tests for raster_data models."""

from __future__ import annotations

from typing import ClassVar

from django.contrib.gis.geos import GEOSGeometry
from django.db import IntegrityError
from django.test import TestCase

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
