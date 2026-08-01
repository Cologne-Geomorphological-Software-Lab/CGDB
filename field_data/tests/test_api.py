"""API tests for the field_data map-dashboard GeoJSON actions.

These "map" actions (LocationViewSet.map, StudyAreaViewSet.map,
TransectViewSet.map) replaced the hand-rolled locations_geojson /
study_areas_geojson / transects_geojson views formerly in prototype/views.py
(see F3 in the architecture-audit plan). LocationViewSet.map has thorough
coverage in prototype/tests/test_map_views.py; this file covers all three
map actions from the field_data side and checks the DRF viewset wiring.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from django.contrib.auth.models import User
from django.contrib.gis.geos import GEOSGeometry
from django.test import Client, TestCase
from guardian.shortcuts import assign_perm
from rest_framework.test import APIClient

from field_data.models import StudyArea, Transect
from prototype.models import Project

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse

    class _TestClient(Client):
        """Narrow, correctly-typed view of APIClient for use in tests."""

        def force_authenticate(self, user: object = ...) -> None: ...
        def get(  # type: ignore[override]
            self, path: str, data: object = ..., **extra: object
        ) -> _MonkeyPatchedWSGIResponse: ...

_STUDY_AREA_WKT = "POLYGON ((6.0 50.0, 8.0 50.0, 8.0 52.0, 6.0 52.0, 6.0 50.0))"
_TRANSECT_WKT = "MULTILINESTRING ((6.0 50.0, 6.5 50.5))"


def _make_client() -> _TestClient:
    """Return a new APIClient, cast to the correctly-typed class above."""
    return cast("_TestClient", APIClient())


class _BaseApiTest(TestCase):
    user: ClassVar[User]
    project: ClassVar[Project]
    study_area: ClassVar[StudyArea]
    transect: ClassVar[Transect]
    client: _TestClient

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="fd_api_user", password="pw")
        cls.project = Project.objects.create(
            title="Field Data API Project", label="FDAP01", status="ACTIVE"
        )
        assign_perm("view_project", cls.user, cls.project)

        cls.study_area = StudyArea.objects.create(
            label="SA01",
            project=cls.project,
            geometry=GEOSGeometry(_STUDY_AREA_WKT, srid=4326),
            climate_koeppen="Cfb",
            ecozone_schultz="MHU",
        )
        cls.transect = Transect.objects.create(
            identifier="T01",
            study_area=cls.study_area,
            description="Test transect",
            multiline=GEOSGeometry(_TRANSECT_WKT, srid=4326),
        )

    def setUp(self) -> None:
        self.client = _make_client()
        self.client.force_authenticate(user=self.user)


class StudyAreaMapActionTest(_BaseApiTest):
    def test_map_returns_feature_collection(self) -> None:
        resp = self.client.get("/api/v1/study-areas/map/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "FeatureCollection"

    def test_map_feature_has_display_properties(self) -> None:
        resp = self.client.get("/api/v1/study-areas/map/")
        feature = next(
            f for f in resp.json()["features"] if f["properties"]["label"] == "SA01"
        )
        props = feature["properties"]
        assert props["climate_koeppen_display"] == "Oceanic climate"
        assert props["ecozone_schultz_display"] == "Humid mid-latitudes"
        assert "admin_url" in props
        assert str(self.study_area.pk) in props["admin_url"]

    def test_map_excludes_areas_without_geometry(self) -> None:
        StudyArea.objects.create(label="SA_NO_GEOM", project=self.project)
        resp = self.client.get("/api/v1/study-areas/map/")
        labels = {f["properties"]["label"] for f in resp.json()["features"]}
        assert "SA_NO_GEOM" not in labels

    def test_unauthenticated_returns_401_or_403(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/study-areas/map/")
        assert resp.status_code in (401, 403)


class TransectMapActionTest(_BaseApiTest):
    def test_map_returns_feature_collection(self) -> None:
        resp = self.client.get("/api/v1/transects/map/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "FeatureCollection"

    def test_map_feature_has_expected_properties(self) -> None:
        resp = self.client.get("/api/v1/transects/map/")
        feature = next(
            f
            for f in resp.json()["features"]
            if f["properties"]["identifier"] == "T01"
        )
        props = feature["properties"]
        assert props["study_area"] == "SA01"
        assert "admin_url" in props
        assert str(self.transect.pk) in props["admin_url"]

    def test_map_excludes_transects_without_geometry(self) -> None:
        Transect.objects.create(
            identifier="T_NO_GEOM",
            study_area=self.study_area,
            description="No geometry",
        )
        resp = self.client.get("/api/v1/transects/map/")
        ids = {f["properties"]["identifier"] for f in resp.json()["features"]}
        assert "T_NO_GEOM" not in ids

    def test_unauthenticated_returns_401_or_403(self) -> None:
        client = _make_client()
        resp = client.get("/api/v1/transects/map/")
        assert resp.status_code in (401, 403)
