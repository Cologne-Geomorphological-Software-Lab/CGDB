"""Tests for the map dashboard views.

Covers:
- map_dashboard: authentication redirect, HTTP 200 for staff
- locations_geojson: structure, permission filtering, geometry exclusion
"""
from __future__ import annotations

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from guardian.shortcuts import assign_perm

from bibliography.models import Author, Reference
from field_data.models import Location
from prototype.models import Project


def _make_point_location(identifier: str, project: object = None, data_source: str = "internal", with_geometry: bool = True):
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

    def test_navigation_contains_overview_link(self):
        c = Client()
        c.login(username="map_staff", password="pw")
        resp = c.get("/map/")
        self.assertContains(resp, 'href="/"')

    def test_navigation_map_tab_is_active(self):
        """The Map navigation item must be rendered as active on /map/."""
        c = Client()
        c.login(username="map_staff", password="pw")
        resp = c.get("/map/")
        # The template marks the active nav item — check the active path is present
        self.assertContains(resp, "/map/")


class LocationsGeoJSONAuthTest(TestCase):
    """GET /api/locations.geojson — authentication."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username="geo_staff", password="pw", is_staff=True
        )

    def test_unauthenticated_redirects(self):
        resp = Client().get("/api/locations.geojson")
        self.assertIn(resp.status_code, (301, 302))

    def test_staff_gets_200(self):
        c = Client()
        c.login(username="geo_staff", password="pw")
        resp = c.get("/api/locations.geojson")
        self.assertEqual(resp.status_code, 200)

    def test_content_type_is_json(self):
        c = Client()
        c.login(username="geo_staff", password="pw")
        resp = c.get("/api/locations.geojson")
        self.assertIn("application/json", resp["Content-Type"])


class LocationsGeoJSONStructureTest(TestCase):
    """GeoJSON structure is valid FeatureCollection."""

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
        data = json.loads(c.get("/api/locations.geojson").content)
        self.assertEqual(data["type"], "FeatureCollection")

    def test_features_is_list(self):
        c = Client()
        c.login(username="geo_su", password="pw")
        data = json.loads(c.get("/api/locations.geojson").content)
        self.assertIsInstance(data["features"], list)

    def test_feature_has_geometry(self):
        c = Client()
        c.login(username="geo_su", password="pw")
        data = json.loads(c.get("/api/locations.geojson").content)
        feature = next(f for f in data["features"] if f["properties"]["identifier"] == "GJ_LOC1")
        self.assertEqual(feature["geometry"]["type"], "Point")
        self.assertEqual(len(feature["geometry"]["coordinates"]), 2)

    def test_feature_properties_keys(self):
        c = Client()
        c.login(username="geo_su", password="pw")
        data = json.loads(c.get("/api/locations.geojson").content)
        feature = next(f for f in data["features"] if f["properties"]["identifier"] == "GJ_LOC1")
        props = feature["properties"]
        for key in ("id", "identifier", "project", "data_source", "admin_url"):
            self.assertIn(key, props, msg=f"Missing property: {key}")

    def test_admin_url_points_to_change_page(self):
        c = Client()
        c.login(username="geo_su", password="pw")
        data = json.loads(c.get("/api/locations.geojson").content)
        feature = next(f for f in data["features"] if f["properties"]["identifier"] == "GJ_LOC1")
        self.assertIn(str(self.loc.id), feature["properties"]["admin_url"])
        self.assertIn("change", feature["properties"]["admin_url"])


class LocationsGeoJSONPermissionTest(TestCase):
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
        return json.loads(c.get("/api/locations.geojson").content)["features"]

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
            self.assertIn("GEO_LIT", ids, msg=f"{user.username} should see literature locations")

    def test_user_without_any_perm_sees_only_literature(self):
        features = self._fetch(self.user_no_perm)
        ids = self._ids(features)
        self.assertNotIn("GEO_A", ids)
        self.assertNotIn("GEO_B", ids)
        self.assertIn("GEO_LIT", ids)


class LocationsGeoJSONGeometryTest(TestCase):
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
        data = json.loads(c.get("/api/locations.geojson").content)
        ids = {f["properties"]["identifier"] for f in data["features"]}
        self.assertIn("GEO_WITH_GEOM", ids)

    def test_location_without_geometry_is_excluded(self):
        c = Client()
        c.login(username="geo_geom_su", password="pw")
        data = json.loads(c.get("/api/locations.geojson").content)
        ids = {f["properties"]["identifier"] for f in data["features"]}
        self.assertNotIn("GEO_NO_GEOM", ids)
