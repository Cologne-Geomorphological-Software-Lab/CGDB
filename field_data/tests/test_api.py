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

import pytest
from django.contrib.auth.models import User
from django.contrib.gis.geos import GEOSGeometry
from django.test import Client, TestCase
from guardian.shortcuts import assign_perm
from rest_framework.test import APIClient

from analysis.models import GrainSize, LuminescenceDating
from bibliography.models import Author, Reference
from field_data.models import Location, Sample, StudyArea, Transect
from prototype.models import Project

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse

    class _TestClient(Client):
        """Narrow, correctly-typed view of APIClient for use in tests."""

        def force_authenticate(self, user: object = ...) -> None: ...
        def get(  # type: ignore[override]
            self, path: str, data: object = ..., **extra: object
        ) -> _MonkeyPatchedWSGIResponse: ...
        def post(  # type: ignore[override]
            self, path: str, data: object = ..., **extra: object
        ) -> _MonkeyPatchedWSGIResponse: ...
        def patch(  # type: ignore[override]
            self, path: str, data: object = ..., **extra: object
        ) -> _MonkeyPatchedWSGIResponse: ...

_STUDY_AREA_WKT = "POLYGON ((6.0 50.0, 8.0 50.0, 8.0 52.0, 6.0 52.0, 6.0 50.0))"
_TRANSECT_WKT = "MULTILINESTRING ((6.0 50.0, 6.5 50.5))"

_NEW_POLYGON_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[[10.0, 50.0], [12.0, 50.0], [12.0, 52.0], [10.0, 52.0], [10.0, 50.0]]],
}
_SELF_INTERSECTING_POLYGON_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[[0.0, 0.0], [2.0, 2.0], [2.0, 0.0], [0.0, 2.0], [0.0, 0.0]]],
}
_NEW_MULTILINESTRING_GEOJSON = {
    "type": "MultiLineString",
    "coordinates": [[[10.0, 50.0], [10.5, 50.5]]],
}
_NEW_POINT_GEOJSON = {"type": "Point", "coordinates": [7.0, 51.0]}


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


class LocationMapActionCountsTest(_BaseApiTest):
    """sample_count/luminescence_count/grain_size_count on /locations/map/.

    Regression coverage for the switch from joined Count(..., distinct=True)
    annotations (which fan out across sample/luminescence/grain_size joins)
    to independent Subquery counts — multiple samples, with more than one
    luminescence/grain-size record on one of them, is exactly the shape that
    would expose a join-fan-out miscount if the Subquery rewrite got the
    correlated lookup path wrong.
    """

    location: ClassVar[Location]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.location = Location.objects.create(
            identifier="LMC_LOC", data_source="internal", project=cls.project
        )
        cls.location.easting = 6.5
        cls.location.northing = 51.0
        cls.location.save()

        sample_a = Sample.objects.create(
            identifier="LMC_S01", project=cls.project, location=cls.location
        )
        Sample.objects.create(
            identifier="LMC_S02", project=cls.project, location=cls.location
        )
        LuminescenceDating.objects.create(sample=sample_a)
        LuminescenceDating.objects.create(sample=sample_a)
        GrainSize.objects.create(sample=sample_a, method="L")

    def test_counts_are_not_inflated_by_join_fan_out(self) -> None:
        resp = self.client.get("/api/v1/locations/map/")
        assert resp.status_code == 200
        feature = next(
            f
            for f in resp.json()["features"]
            if f["properties"]["identifier"] == "LMC_LOC"
        )
        props = feature["properties"]
        assert props["sample_count"] == 2
        assert props["luminescence_count"] == 2
        assert props["grain_size_count"] == 1

    def test_location_with_no_samples_has_zero_counts(self) -> None:
        Location.objects.create(
            identifier="LMC_EMPTY",
            data_source="internal",
            project=self.project,
            easting=6.6,
            northing=51.1,
        )
        resp = self.client.get("/api/v1/locations/map/")
        feature = next(
            f
            for f in resp.json()["features"]
            if f["properties"]["identifier"] == "LMC_EMPTY"
        )
        props = feature["properties"]
        assert props["sample_count"] == 0
        assert props["luminescence_count"] == 0
        assert props["grain_size_count"] == 0


class _WritePermissionApiTest(_BaseApiTest):
    """Adds a second user with add_project/change_project on self.project.

    self.user (from _BaseApiTest) only has view_project — the "read but
    can't write" case. self.editor has full write permissions.
    """

    editor: ClassVar[User]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.editor = User.objects.create_user(username="fd_api_editor", password="pw")
        assign_perm("add_project", cls.editor, cls.project)
        assign_perm("change_project", cls.editor, cls.project)
        assign_perm("view_project", cls.editor, cls.project)

    def _client_for(self, user: User) -> _TestClient:
        client = _make_client()
        client.force_authenticate(user=user)
        return client


class StudyAreaWriteTest(_WritePermissionApiTest):
    def test_create_with_add_permission_succeeds(self) -> None:
        resp = self._client_for(self.editor).post(
            "/api/v1/study-areas/",
            {"label": "SA_NEW", "project": self.project.pk, "geometry": _NEW_POLYGON_GEOJSON},
            format="json",
        )
        assert resp.status_code == 201
        assert StudyArea.objects.filter(label="SA_NEW").exists()

    def test_create_without_add_permission_returns_403(self) -> None:
        resp = self._client_for(self.user).post(
            "/api/v1/study-areas/",
            {"label": "SA_DENIED", "project": self.project.pk, "geometry": _NEW_POLYGON_GEOJSON},
            format="json",
        )
        assert resp.status_code == 403
        assert not StudyArea.objects.filter(label="SA_DENIED").exists()

    def test_update_with_change_permission_succeeds(self) -> None:
        resp = self._client_for(self.editor).patch(
            f"/api/v1/study-areas/{self.study_area.pk}/",
            {"geometry": _NEW_POLYGON_GEOJSON},
            format="json",
        )
        assert resp.status_code == 200
        self.study_area.refresh_from_db()
        assert self.study_area.geometry.geom_type == "Polygon"

    def test_update_without_change_permission_returns_403(self) -> None:
        resp = self._client_for(self.user).patch(
            f"/api/v1/study-areas/{self.study_area.pk}/",
            {"geometry": _NEW_POLYGON_GEOJSON},
            format="json",
        )
        assert resp.status_code == 403

    def test_update_self_intersecting_polygon_returns_400(self) -> None:
        resp = self._client_for(self.editor).patch(
            f"/api/v1/study-areas/{self.study_area.pk}/",
            {"geometry": _SELF_INTERSECTING_POLYGON_GEOJSON},
            format="json",
        )
        assert resp.status_code == 400
        assert "geometry" in resp.json()


class TransectWriteTest(_WritePermissionApiTest):
    def test_create_with_add_permission_succeeds(self) -> None:
        resp = self._client_for(self.editor).post(
            "/api/v1/transects/",
            {
                "identifier": "T_NEW",
                "study_area": self.study_area.pk,
                "description": "New transect",
                "multiline": _NEW_MULTILINESTRING_GEOJSON,
            },
            format="json",
        )
        assert resp.status_code == 201
        assert Transect.objects.filter(identifier="T_NEW").exists()

    def test_create_without_add_permission_returns_403(self) -> None:
        resp = self._client_for(self.user).post(
            "/api/v1/transects/",
            {
                "identifier": "T_DENIED",
                "study_area": self.study_area.pk,
                "description": "Denied",
                "multiline": _NEW_MULTILINESTRING_GEOJSON,
            },
            format="json",
        )
        assert resp.status_code == 403
        assert not Transect.objects.filter(identifier="T_DENIED").exists()

    def test_update_with_change_permission_succeeds(self) -> None:
        resp = self._client_for(self.editor).patch(
            f"/api/v1/transects/{self.transect.pk}/",
            {"multiline": _NEW_MULTILINESTRING_GEOJSON},
            format="json",
        )
        assert resp.status_code == 200
        self.transect.refresh_from_db()
        assert self.transect.multiline.geom_type == "MultiLineString"

    def test_update_without_change_permission_returns_403(self) -> None:
        resp = self._client_for(self.user).patch(
            f"/api/v1/transects/{self.transect.pk}/",
            {"multiline": _NEW_MULTILINESTRING_GEOJSON},
            format="json",
        )
        assert resp.status_code == 403


class LocationWriteTest(_WritePermissionApiTest):
    location: ClassVar[Location]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.location = Location(
            identifier="LOC01", project=cls.project, data_source="internal"
        )
        cls.location.easting = 6.0
        cls.location.northing = 50.0
        cls.location.save()

    def test_update_round_trips_easting_northing(self) -> None:
        """PATCHing location must update easting/northing, not just the point.

        Location.save() always recomputes .location from easting/northing —
        a naive write straight to .location would get silently overwritten
        on the next unrelated save() by any other caller.
        """
        resp = self._client_for(self.editor).patch(
            f"/api/v1/locations/{self.location.pk}/",
            {"location": _NEW_POINT_GEOJSON},
            format="json",
        )
        assert resp.status_code == 200
        self.location.refresh_from_db()
        assert self.location.easting == pytest.approx(7.0)
        assert self.location.northing == pytest.approx(51.0)

        # Survives an unrelated save() from another caller (e.g. the admin
        # form, an import script) — proves easting/northing is genuinely
        # the source of truth now, not just momentarily matching.
        self.location.save()
        self.location.refresh_from_db()
        assert self.location.location.x == pytest.approx(7.0)
        assert self.location.location.y == pytest.approx(51.0)

    def test_update_without_change_permission_returns_403(self) -> None:
        resp = self._client_for(self.user).patch(
            f"/api/v1/locations/{self.location.pk}/",
            {"location": _NEW_POINT_GEOJSON},
            format="json",
        )
        assert resp.status_code == 403

    def test_literature_location_cannot_be_edited(self) -> None:
        author = Author.objects.create(last_name="Geo", first_name="Test")
        reference = Reference.objects.create(
            title="Geo Lit Ref", lead_author=author, abstract="x", type="Paper"
        )
        self.location.data_source = "literature"
        self.location.project = None  # literature locations have no owning project
        self.location.reference = reference
        self.location.save()

        resp = self._client_for(self.editor).patch(
            f"/api/v1/locations/{self.location.pk}/",
            {"location": _NEW_POINT_GEOJSON},
            format="json",
        )
        assert resp.status_code == 403


class ReparentingSecurityTest(_WritePermissionApiTest):
    """A PATCH that changes project/study_area must be checked against the
    *target* project too, not just the object's current one.

    self.editor has add/change/view on self.project only — never on
    other_project — for every test in this class.
    """

    other_project: ClassVar[Project]
    other_study_area: ClassVar[StudyArea]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.other_project = Project.objects.create(
            title="Other Project", label="OTHP01", status="ACTIVE"
        )
        cls.other_study_area = StudyArea.objects.create(
            label="OTH_SA01",
            project=cls.other_project,
            geometry=GEOSGeometry(_STUDY_AREA_WKT, srid=4326),
        )

    def test_study_area_reparent_without_add_on_target_returns_403(self) -> None:
        resp = self._client_for(self.editor).patch(
            f"/api/v1/study-areas/{self.study_area.pk}/",
            {"project": self.other_project.pk},
            format="json",
        )
        assert resp.status_code == 403
        self.study_area.refresh_from_db()
        assert self.study_area.project.pk == self.project.pk

    def test_study_area_reparent_with_add_on_target_succeeds(self) -> None:
        assign_perm("add_project", self.editor, self.other_project)
        resp = self._client_for(self.editor).patch(
            f"/api/v1/study-areas/{self.study_area.pk}/",
            {"project": self.other_project.pk},
            format="json",
        )
        assert resp.status_code == 200
        self.study_area.refresh_from_db()
        assert self.study_area.project.pk == self.other_project.pk

    def test_transect_reparent_without_add_on_target_returns_403(self) -> None:
        resp = self._client_for(self.editor).patch(
            f"/api/v1/transects/{self.transect.pk}/",
            {"study_area": self.other_study_area.pk},
            format="json",
        )
        assert resp.status_code == 403
        self.transect.refresh_from_db()
        assert self.transect.study_area.pk == self.study_area.pk

    def test_transect_reparent_with_add_on_target_succeeds(self) -> None:
        assign_perm("add_project", self.editor, self.other_project)
        resp = self._client_for(self.editor).patch(
            f"/api/v1/transects/{self.transect.pk}/",
            {"study_area": self.other_study_area.pk},
            format="json",
        )
        assert resp.status_code == 200
        self.transect.refresh_from_db()
        assert self.transect.study_area.pk == self.other_study_area.pk
