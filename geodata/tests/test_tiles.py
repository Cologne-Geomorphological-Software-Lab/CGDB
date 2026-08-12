"""Tests for the PostGIS-only landform vector tile endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

import pytest
from django.contrib.auth.models import User
from django.contrib.gis.geos import GEOSGeometry
from django.test import Client, TestCase

from geodata.models import Landform

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse

    class _TestClient(Client):
        def login(self, **credentials: object) -> bool: ...
        def get(  # type: ignore[override]
            self, path: str, data: object = ..., **extra: object
        ) -> _MonkeyPatchedWSGIResponse: ...


# Covers most of Europe at low zoom — intersects the fixture polygon below.
_TILE_URL = "/api/v1/landforms/tiles/2/2/1.mvt"
_MULTIPOLYGON_WKT = (
    "MULTIPOLYGON (((6.0 50.0, 8.0 50.0, 8.0 52.0, 6.0 52.0, 6.0 50.0)))"
)


class _BaseTileTest(TestCase):
    user: ClassVar[User]
    client: _TestClient

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="tile_user", password="pw")
        Landform.objects.create(
            geometry=GEOSGeometry(_MULTIPOLYGON_WKT, srid=4326),
            brid_nam="Test Region",
            continent="Europe",
            murphy_code="TR",
        )

    def setUp(self) -> None:
        self.client = cast("_TestClient", Client())
        self.client.login(username="tile_user", password="pw")


@pytest.mark.postgis_only
class LandformTileTest(_BaseTileTest):
    """Requires PostGIS — run with DJANGO_SETTINGS_MODULE=prototype.test_settings_postgis."""

    def test_tile_intersecting_fixture_returns_protobuf(self) -> None:
        resp = self.client.get(_TILE_URL)
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/x-protobuf"
        assert len(resp.content) > 0

    def test_tile_with_no_data_returns_empty_but_valid_response(self) -> None:
        # z/x/y for a tile far from the fixture geometry (mid-Pacific).
        resp = self.client.get("/api/v1/landforms/tiles/2/0/2.mvt")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/x-protobuf"

    def test_cache_control_header_present(self) -> None:
        resp = self.client.get(_TILE_URL)
        assert "max-age" in resp["Cache-Control"]


class LandformTileSpatialiteGuardTest(_BaseTileTest):
    """Runs against the default (SpatiaLite) test settings — no gis marker."""

    def test_non_postgres_backend_returns_501(self) -> None:
        resp = self.client.get(_TILE_URL)
        assert resp.status_code == 501

    def test_unauthenticated_returns_403_not_a_login_redirect(self) -> None:
        """Architecture-review fix (F18): landform_tile used to rely on
        Django's @login_required, which redirects (302) to LOGIN_URL on
        failure -- the wrong shape for a binary tile endpoint consumed by a
        map library, and inconsistent with every other authenticated
        endpoint in this API returning a plain 401/403. The auth check now
        runs (and returns 403) before the PostGIS-vendor check, so this is
        verifiable without a real PostGIS backend."""
        anon = cast("_TestClient", Client())
        resp = anon.get(_TILE_URL)
        assert resp.status_code == 403
