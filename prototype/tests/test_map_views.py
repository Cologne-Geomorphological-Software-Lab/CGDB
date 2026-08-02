"""Tests for the map dashboard view and its DRF-backed GeoJSON overlays.

Covers:
- map_dashboard: authentication redirect, HTTP 200 for staff
- LocationViewSet.map ("/api/v1/locations/map/"): structure, permission
  filtering, geometry exclusion — this action replaced the old hand-rolled
  locations_geojson view (see F3 in the architecture-audit plan).
"""

from __future__ import annotations

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from guardian.shortcuts import assign_perm

from bibliography.models import Author, Reference
from field_data.models import Location
from prototype.models import Project

_LOCATIONS_MAP_URL = "/api/v1/locations/map/"


def _make_point_location(
    identifier: str,
    project: object = None,
    data_source: str = "internal",
    with_geometry: bool = True,
):
    """Helper: create a Location; set easting/northing so save() builds the PointField."""
    loc = Location(
        identifier=identifier,
        data_source=data_source,
        project=project,
    )
    if with_geometry:
        loc.easting = 10.0
        loc.northing = 50.0
    loc.save()
    return loc


class MapDashboardAuthTest(TestCase):
    """GET /map/ — authentication and basic response."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username="map_staff", password="pw", is_staff=True
        )

    def test_unauthenticated_redirects_to_login(self):
        resp = Client().get("/map/")
        self.assertIn(resp.status_code, (301, 302))
        self.assertIn("login", resp["Location"])

    def test_staff_gets_200(self):
        c = Client()
        c.login(username="map_staff", password="pw")
        resp = c.get("/map/")
        self.assertEqual(resp.status_code, 200)

    def test_response_contains_map_div(self):
        c = Client()
        c.login(username="map_staff", password="pw")
        resp = c.get("/map/")
        self.assertContains(resp, 'id="cgdb-map"')

    def test_map_page_has_no_local_dashboard_tab_bar(self):
        """The map page is a standalone page, not a Dashboard sub-tab."""
        c = Client()
        c.login(username="map_staff", password="pw")
        resp = c.get("/map/")
        self.assertNotContains(resp, "Overview")

    def test_sidebar_links_to_map_dashboard(self):
        """The main Unfold sidebar links to the map page (not a Dashboard tab)."""
        c = Client()
        c.login(username="map_staff", password="pw")
        resp = c.get(reverse("admin:index"))
        self.assertContains(resp, reverse("map_dashboard"))

    def test_geojson_urls_point_at_drf_endpoints(self):
        """The injected GEOJSON_URLS must resolve to the new DRF map endpoints."""
        c = Client()
        c.login(username="map_staff", password="pw")
        resp = c.get("/map/")
        self.assertContains(resp, "/api/v1/locations/map/")
        self.assertContains(resp, "/api/v1/study-areas/map/")
        self.assertContains(resp, "/api/v1/transects/map/")
        self.assertContains(resp, "/api/v1/landforms/")


class LocationsMapAuthTest(TestCase):
    """GET /api/v1/locations/map/ — authentication."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username="geo_staff", password="pw", is_staff=True
        )

    def test_unauthenticated_returns_401_or_403(self):
        resp = Client().get(_LOCATIONS_MAP_URL)
        self.assertIn(resp.status_code, (401, 403))

    def test_authenticated_gets_200(self):
        c = Client()
        c.login(username="geo_staff", password="pw")
        resp = c.get(_LOCATIONS_MAP_URL)
        self.assertEqual(resp.status_code, 200)

    def test_content_type_is_json(self):
        c = Client()
        c.login(username="geo_staff", password="pw")
        resp = c.get(_LOCATIONS_MAP_URL)
        self.assertIn("application/json", resp["Content-Type"])


class LocationsMapStructureTest(TestCase):
    """GeoJSON structure is a valid FeatureCollection."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="geo_su", password="pw"
        )
        cls.project = Project.objects.create(
            title="GeoJSON Test Project", label="GJP01", status="ACTIVE"
        )
        cls.loc = _make_point_location("GJ_LOC1", project=cls.project)

    def test_type_is_feature_collection(self):
        c = Client()
        c.login(username="geo_su", password="pw")
        data = json.loads(c.get(_LOCATIONS_MAP_URL).content)
        self.assertEqual(data["type"], "FeatureCollection")

    def test_features_is_list(self):
        c = Client()
        c.login(username="geo_su", password="pw")
        data = json.loads(c.get(_LOCATIONS_MAP_URL).content)
        self.assertIsInstance(data["features"], list)

    def test_feature_has_geometry(self):
        c = Client()
        c.login(username="geo_su", password="pw")
        data = json.loads(c.get(_LOCATIONS_MAP_URL).content)
        feature = next(
            f
            for f in data["features"]
            if f["properties"]["identifier"] == "GJ_LOC1"
        )
        self.assertEqual(feature["geometry"]["type"], "Point")
        self.assertEqual(len(feature["geometry"]["coordinates"]), 2)

    def test_feature_properties_keys(self):
        """Property keys must match what the map dashboard's popup JS reads.

        Note: "id" is placed at the top-level Feature.id by GeoFeatureModelSerializer
        (per the GeoJSON spec), not inside properties — the popup JS never reads
        properties.id, so this is a harmless structural difference from the old
        hand-rolled view, which duplicated "id" inside properties too.
        """
        c = Client()
        c.login(username="geo_su", password="pw")
        data = json.loads(c.get(_LOCATIONS_MAP_URL).content)
        feature = next(
            f
            for f in data["features"]
            if f["properties"]["identifier"] == "GJ_LOC1"
        )
        self.assertIn("id", feature)
        props = feature["properties"]
        for key in (
            "identifier",
            "project",
            "data_source",
            "location_type_display",
            "sample_count",
            "luminescence_count",
            "grain_size_count",
            "admin_url",
        ):
            self.assertIn(key, props, msg=f"Missing property: {key}")

    def test_admin_url_points_to_change_page(self):
        c = Client()
        c.login(username="geo_su", password="pw")
        data = json.loads(c.get(_LOCATIONS_MAP_URL).content)
        feature = next(
            f
            for f in data["features"]
            if f["properties"]["identifier"] == "GJ_LOC1"
        )
        self.assertIn(str(self.loc.id), feature["properties"]["admin_url"])
        self.assertIn("change", feature["properties"]["admin_url"])


class LocationsMapPermissionTest(TestCase):
    """Locations are filtered by Guardian project permissions."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="geo_perm_su", password="pw"
        )
        cls.user_a = User.objects.create_user(
            username="geo_user_a", password="pw", is_staff=True
        )
        cls.user_no_perm = User.objects.create_user(
            username="geo_user_none", password="pw", is_staff=True
        )

        cls.project_a = Project.objects.create(
            title="Geo Perm Project A", label="GPA01", status="ACTIVE"
        )
        cls.project_b = Project.objects.create(
            title="Geo Perm Project B", label="GPB01", status="ACTIVE"
        )

        cls.loc_a = _make_point_location("GEO_A", project=cls.project_a)
        cls.loc_b = _make_point_location("GEO_B", project=cls.project_b)

        # Literature location (no project)
        author = Author.objects.create(last_name="Geo", first_name="Test")
        ref = Reference.objects.create(
            title="Geo Lit Ref", lead_author=author, abstract="x", type="Paper"
        )
        cls.loc_lit = Location.objects.create(
            identifier="GEO_LIT",
            data_source="literature",
            reference=ref,
            easting=5.0,
            northing=45.0,
        )
        cls.loc_lit.save()

    def setUp(self):
        assign_perm("prototype.view_project", self.user_a, self.project_a)

    def _fetch(self, user: object):
        c = Client()
        c.login(username=user.username, password="pw")
        return json.loads(c.get(_LOCATIONS_MAP_URL).content)["features"]

    def _ids(self, features: object):
        return {f["properties"]["identifier"] for f in features}

    def test_superuser_sees_all_locations(self):
        ids = self._ids(self._fetch(self.superuser))
        self.assertIn("GEO_A", ids)
        self.assertIn("GEO_B", ids)

    def test_user_with_view_project_sees_own_project_locations(self):
        ids = self._ids(self._fetch(self.user_a))
        self.assertIn("GEO_A", ids)

    def test_user_does_not_see_other_project_locations(self):
        ids = self._ids(self._fetch(self.user_a))
        self.assertNotIn("GEO_B", ids)

    def test_literature_locations_visible_to_all(self):
        for user in (self.user_a, self.user_no_perm):
            ids = self._ids(self._fetch(user))
            self.assertIn(
                "GEO_LIT",
                ids,
                msg=f"{user.username} should see literature locations",
            )

    def test_user_without_any_perm_sees_only_literature(self):
        features = self._fetch(self.user_no_perm)
        ids = self._ids(features)
        self.assertNotIn("GEO_A", ids)
        self.assertNotIn("GEO_B", ids)
        self.assertIn("GEO_LIT", ids)


class LocationsMapGeometryTest(TestCase):
    """Locations without geometry are excluded from the GeoJSON output."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="geo_geom_su", password="pw"
        )
        cls.project = Project.objects.create(
            title="Geo Geom Project", label="GGP01", status="ACTIVE"
        )
        cls.loc_with_geom = _make_point_location(
            "GEO_WITH_GEOM", project=cls.project, with_geometry=True
        )
        # Create location without coordinates — PointField stays NULL
        cls.loc_no_geom = Location.objects.create(
            identifier="GEO_NO_GEOM",
            data_source="internal",
            project=cls.project,
        )

    def test_location_with_geometry_is_included(self):
        c = Client()
        c.login(username="geo_geom_su", password="pw")
        data = json.loads(c.get(_LOCATIONS_MAP_URL).content)
        ids = {f["properties"]["identifier"] for f in data["features"]}
        self.assertIn("GEO_WITH_GEOM", ids)

    def test_location_without_geometry_is_excluded(self):
        c = Client()
        c.login(username="geo_geom_su", password="pw")
        data = json.loads(c.get(_LOCATIONS_MAP_URL).content)
        ids = {f["properties"]["identifier"] for f in data["features"]}
        self.assertNotIn("GEO_NO_GEOM", ids)
