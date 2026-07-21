"""API tests for raster_data ViewSets and manifest action."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from django.contrib.auth.models import User
from django.contrib.gis.geos import GEOSGeometry, Polygon
from django.test import Client, TestCase
from guardian.shortcuts import assign_perm
from rest_framework.test import APIClient

from prototype.models import Project
from raster_data.models import DataSource, RasterDataset, RasterScene

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse

    class _TestClient(Client):
        """Narrow, correctly-typed view of APIClient for use in tests.

        APIClient's real MRO (APIRequestFactory before Client) makes
        basedpyright infer .get()/.post() as returning a WSGIRequest instead
        of a response — this subclass (type-checking only) pins the types we
        actually rely on in these tests, while still satisfying mypy's check
        that `self.client` remains a `Client` (as declared by TestCase).
        """

        def force_authenticate(self, user: object = ...) -> None: ...
        def get(  # type: ignore[override]
            self, path: str, data: object = ..., **extra: object
        ) -> _MonkeyPatchedWSGIResponse: ...
        def post(  # type: ignore[override]
            self, path: str, data: object = ..., **extra: object
        ) -> _MonkeyPatchedWSGIResponse: ...

_BBOX_WKT = "POLYGON ((6.0 50.0, 8.0 50.0, 8.0 52.0, 6.0 52.0, 6.0 50.0))"


def _make_client() -> _TestClient:
    """Return a new APIClient, cast to the correctly-typed class above."""
    return cast("_TestClient", APIClient())


class _BaseApiTest(TestCase):
    user: ClassVar[User]
    project: ClassVar[Project]
    ds: ClassVar[DataSource]
    scene: ClassVar[RasterScene]
    dataset: ClassVar[RasterDataset]
    client: _TestClient

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="api_user", password="pw")
        cls.project = Project.objects.create(
            title="API Project", label="AP01", status="ACTIVE"
        )
        assign_perm("view_project", cls.user, cls.project)

        cls.ds = DataSource.objects.create(name="Sentinel-2 L2A", provider="ESA")
        cls.scene = RasterScene.objects.create(
            project=cls.project,
            data_source=cls.ds,
            corpus_path="corpus/scenes/s2_001.tif",
            n_bands=4,
        )
        cls.dataset = RasterDataset.objects.create(
            project=cls.project,
            name="Global Corpus 2024",
            slug="global-corpus-2024",
        )

    def setUp(self) -> None:
        self.client = _make_client()
        self.client.force_authenticate(user=self.user)


class DataSourceViewSetTest(_BaseApiTest):
    def test_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/data-sources/")
        assert resp.status_code == 200

    def test_list_contains_data_source(self) -> None:
        resp = self.client.get("/api/v1/data-sources/")
        names = [item["name"] for item in resp.json()["results"]]
        assert "Sentinel-2 L2A" in names

    def test_detail_returns_200(self) -> None:
        resp = self.client.get(f"/api/v1/data-sources/{self.ds.pk}/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Sentinel-2 L2A"

    def test_unauthenticated_returns_403(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/data-sources/")
        assert resp.status_code in (401, 403)


class RasterSceneViewSetTest(_BaseApiTest):
    def test_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/raster-scenes/")
        assert resp.status_code == 200

    def test_list_contains_scene(self) -> None:
        resp = self.client.get("/api/v1/raster-scenes/")
        paths = [item["corpus_path"] for item in resp.json()["results"]]
        assert "corpus/scenes/s2_001.tif" in paths

    def test_detail_contains_effective_path(self) -> None:
        resp = self.client.get(f"/api/v1/raster-scenes/{self.scene.pk}/")
        assert resp.status_code == 200
        assert resp.json()["effective_path"] == "corpus/scenes/s2_001.tif"


class RasterDatasetManifestTest(_BaseApiTest):
    def test_manifest_unauthenticated_returns_403(self) -> None:
        client = _make_client()
        resp = client.get(f"/api/v1/raster-datasets/{self.dataset.pk}/manifest/")
        assert resp.status_code in (401, 403)

    def test_empty_manifest_has_empty_scenes(self) -> None:
        resp = self.client.get(f"/api/v1/raster-datasets/{self.dataset.pk}/manifest/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scenes"] == []

    def test_manifest_with_scene(self) -> None:
        self.dataset.scenes.add(self.scene)
        resp = self.client.get(f"/api/v1/raster-datasets/{self.dataset.pk}/manifest/")
        data = resp.json()
        assert len(data["scenes"]) == 1
        entry = data["scenes"][0]
        assert entry["path"] == "corpus/scenes/s2_001.tif"
        assert entry["data_source_name"] == "Sentinel-2 L2A"
        assert entry["n_bands"] == 4
        self.dataset.scenes.remove(self.scene)

    def test_manifest_contains_name_and_slug(self) -> None:
        resp = self.client.get(f"/api/v1/raster-datasets/{self.dataset.pk}/manifest/")
        data = resp.json()
        assert data["name"] == "Global Corpus 2024"
        assert data["slug"] == "global-corpus-2024"

    def test_dataset_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/raster-datasets/")
        assert resp.status_code == 200

    def test_manifest_scene_has_spatial_bbox_wkt(self) -> None:
        scene_with_bbox = RasterScene.objects.create(
            project=self.project,
            data_source=self.ds,
            corpus_path="corpus/scenes/s2_bbox.tif",
            spatial_bbox=cast("Polygon", GEOSGeometry(_BBOX_WKT, srid=4326)),
        )
        self.dataset.scenes.add(scene_with_bbox)
        resp = self.client.get(f"/api/v1/raster-datasets/{self.dataset.pk}/manifest/")
        entry = next(e for e in resp.json()["scenes"] if "bbox" in e["path"])
        assert entry["spatial_bbox_wkt"] is not None
        assert "POLYGON" in entry["spatial_bbox_wkt"]
        self.dataset.scenes.remove(scene_with_bbox)
        scene_with_bbox.delete()


class RasterSceneCreateTest(_BaseApiTest):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        assign_perm("add_project", cls.user, cls.project)

    def test_create_scene_returns_201(self) -> None:
        resp = self.client.post(
            "/api/v1/raster-scenes/",
            {
                "project": self.project.pk,
                "data_source": self.ds.pk,
                "corpus_path": "/corpus/scenes/new.tif",
                "n_bands": 4,
                "resolution_m": 10.0,
                "crs": "EPSG:32632",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert RasterScene.objects.filter(corpus_path="/corpus/scenes/new.tif").exists()

    def test_create_scene_with_bbox_wkt(self) -> None:
        resp = self.client.post(
            "/api/v1/raster-scenes/",
            {
                "project": self.project.pk,
                "corpus_path": "/corpus/scenes/bbox.tif",
                "spatial_bbox_wkt": _BBOX_WKT,
            },
            format="json",
        )
        assert resp.status_code == 201
        scene = RasterScene.objects.get(corpus_path="/corpus/scenes/bbox.tif")
        assert scene.spatial_bbox is not None

    def test_create_scene_invalid_wkt_returns_400(self) -> None:
        resp = self.client.post(
            "/api/v1/raster-scenes/",
            {
                "project": self.project.pk,
                "corpus_path": "/corpus/scenes/bad.tif",
                "spatial_bbox_wkt": "NOT A POLYGON",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_create_scene_without_add_perm_returns_403(self) -> None:
        other_user = User.objects.create_user(username="noperms", password="pw")
        assign_perm("view_project", other_user, self.project)
        client = _make_client()
        client.force_authenticate(user=other_user)
        resp = client.post(
            "/api/v1/raster-scenes/",
            {"project": self.project.pk, "corpus_path": "/corpus/x.tif"},
            format="json",
        )
        assert resp.status_code == 403


class RasterDatasetCreateTest(_BaseApiTest):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        assign_perm("add_project", cls.user, cls.project)

    def test_create_dataset_returns_201(self) -> None:
        resp = self.client.post(
            "/api/v1/raster-datasets/",
            {
                "project": self.project.pk,
                "name": "Created Dataset",
                "slug": "created-dataset",
                "description": "Test",
                "scene_ids": [self.scene.pk],
            },
            format="json",
        )
        assert resp.status_code == 201
        ds = RasterDataset.objects.get(slug="created-dataset")
        assert ds.scenes.filter(pk=self.scene.pk).exists()

    def test_create_dataset_empty_scenes(self) -> None:
        resp = self.client.post(
            "/api/v1/raster-datasets/",
            {
                "project": self.project.pk,
                "name": "Empty Dataset",
                "slug": "empty-dataset",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert RasterDataset.objects.get(slug="empty-dataset").scenes.count() == 0

    def test_create_dataset_without_add_perm_returns_403(self) -> None:
        other_user = User.objects.create_user(username="noperms2", password="pw")
        assign_perm("view_project", other_user, self.project)
        client = _make_client()
        client.force_authenticate(user=other_user)
        resp = client.post(
            "/api/v1/raster-datasets/",
            {"project": self.project.pk, "name": "X", "slug": "x-ds"},
            format="json",
        )
        assert resp.status_code == 403
