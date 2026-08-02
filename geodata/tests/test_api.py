"""API tests for the geodata LandformViewSet."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

import pytest
from django.contrib.auth.models import User
from django.contrib.gis.geos import GEOSGeometry
from django.test import Client, TestCase
from rest_framework.test import APIClient

from geodata.models import Landform

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse

    class _TestClient(Client):
        """Narrow, correctly-typed view of APIClient for use in tests."""

        def force_authenticate(self, user: object = ...) -> None: ...
        def get(  # type: ignore[override]
            self, path: str, data: object = ..., **extra: object
        ) -> _MonkeyPatchedWSGIResponse: ...

_MULTIPOLYGON_WKT = (
    "MULTIPOLYGON (((6.0 50.0, 8.0 50.0, 8.0 52.0, 6.0 52.0, 6.0 50.0)))"
)


def _make_client() -> _TestClient:
    """Return a new APIClient, cast to the correctly-typed class above."""
    return cast("_TestClient", APIClient())


class _BaseApiTest(TestCase):
    user: ClassVar[User]
    landform: ClassVar[Landform]
    client: _TestClient

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="api_user", password="pw")
        cls.landform = Landform.objects.create(
            geometry=GEOSGeometry(_MULTIPOLYGON_WKT, srid=4326),
            brid_nam="Test Region",
            continent="Europe",
            murphy_code="TR",
        )

    def setUp(self) -> None:
        self.client = _make_client()
        self.client.force_authenticate(user=self.user)


class LandformListTest(_BaseApiTest):
    def test_list_returns_200(self) -> None:
        resp = self.client.get("/api/v1/landforms/")
        assert resp.status_code == 200

    def test_list_contains_landform_without_geometry(self) -> None:
        resp = self.client.get("/api/v1/landforms/")
        results = resp.json()["results"]
        names = [item["brid_nam"] for item in results]
        assert "Test Region" in names
        assert "geometry" not in results[0]

    def test_unauthenticated_returns_401_or_403(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/landforms/")
        assert resp.status_code in (401, 403)


class LandformDetailTest(_BaseApiTest):
    def test_detail_returns_200_with_full_geometry(self) -> None:
        resp = self.client.get(f"/api/v1/landforms/{self.landform.pk}/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "Feature"
        assert data["geometry"]["type"] == "MultiPolygon"
        assert data["properties"]["brid_nam"] == "Test Region"


@pytest.mark.gis
class LandformBboxTest(_BaseApiTest):
    def test_valid_bbox_returns_feature_collection(self) -> None:
        resp = self.client.get("/api/v1/landforms/?bbox=6.0,50.0,8.0,52.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1
        feature = data["features"][0]
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "MultiPolygon"
        assert feature["properties"] == {
            "id": self.landform.pk,
            "murphy_code": "TR",
            "name_str": self.landform.name_str,
            "division": self.landform.division,
            "province": self.landform.province,
            "continent": "Europe",
        }

    def test_bbox_outside_landform_returns_empty_features(self) -> None:
        resp = self.client.get("/api/v1/landforms/?bbox=60.0,10.0,61.0,11.0")
        assert resp.status_code == 200
        assert resp.json()["features"] == []

    def test_invalid_bbox_returns_400(self) -> None:
        resp = self.client.get("/api/v1/landforms/?bbox=not,a,valid,bbox")
        assert resp.status_code == 400

    def test_bbox_with_wrong_part_count_returns_400(self) -> None:
        resp = self.client.get("/api/v1/landforms/?bbox=6.0,50.0")
        assert resp.status_code == 400

    def test_bbox_with_min_greater_than_max_returns_400(self) -> None:
        resp = self.client.get("/api/v1/landforms/?bbox=8.0,52.0,6.0,50.0")
        assert resp.status_code == 400
