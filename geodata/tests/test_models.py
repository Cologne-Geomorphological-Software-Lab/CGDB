"""Unit tests for geodata models."""

from __future__ import annotations

from django.contrib.gis.geos import GEOSGeometry
from django.test import TestCase

from geodata.models import Landform

_MULTIPOLYGON_WKT = (
    "MULTIPOLYGON (((6.0 50.0, 8.0 50.0, 8.0 52.0, 6.0 52.0, 6.0 50.0)))"
)
_OVERLAPPING_WKT = (
    "MULTIPOLYGON (((6.5 50.5, 7.5 50.5, 7.5 51.5, 6.5 51.5, 6.5 50.5)))"
)


def _landform(**kwargs: object) -> Landform:
    defaults: dict[str, object] = {
        "geometry": GEOSGeometry(_MULTIPOLYGON_WKT, srid=4326)
    }
    defaults.update(kwargs)
    return Landform.objects.create(**defaults)


class LandformStrTest(TestCase):
    def test_str_prefers_brid_nam(self) -> None:
        landform = _landform(brid_nam="Canadian Archipelago", name_str="CA")
        assert str(landform) == "Canadian Archipelago"

    def test_str_falls_back_to_name_str_when_no_brid_nam(self) -> None:
        landform = _landform(name_str="CA")
        assert str(landform) == "CA"

    def test_str_falls_back_to_pk_when_no_names(self) -> None:
        landform = _landform()
        assert str(landform) == f"Landform {landform.pk}"


class LandformFieldsTest(TestCase):
    def test_geometry_round_trips_as_multipolygon(self) -> None:
        landform = _landform()
        reloaded = Landform.objects.get(pk=landform.pk)
        assert reloaded.geometry is not None
        assert reloaded.geometry.geom_type == "MultiPolygon"

    def test_optional_numeric_fields_default_to_none(self) -> None:
        landform = _landform()
        assert landform.structure is None
        assert landform.moist_dry is None
        assert landform.topog is None
        assert landform.process is None
        assert landform.area_geo is None
        assert landform.shape_length is None
        assert landform.shape_area is None

    def test_optional_char_fields_default_to_empty_string(self) -> None:
        landform = _landform()
        assert landform.brid_nam == ""
        assert landform.division == ""
        assert landform.continent == ""

    def test_numeric_fields_stored(self) -> None:
        landform = _landform(
            structure=1, moist_dry=2, topog=3, process=4,
            area_geo=123.4, shape_length=5.6, shape_area=7.8,
        )
        reloaded = Landform.objects.get(pk=landform.pk)
        assert reloaded.structure == 1
        assert reloaded.area_geo == 123.4

    def test_ordering_by_continent_division_province(self) -> None:
        _landform(continent="B", division="X", province="1")
        _landform(continent="A", division="Y", province="2")
        _landform(continent="A", division="X", province="3")
        continents = list(
            Landform.objects.values_list("continent", "division", "province")
        )
        assert continents == sorted(continents)


class LandformSpatialTest(TestCase):
    def test_intersects_lookup_finds_overlapping_landform(self) -> None:
        a = _landform(name_str="A")
        _landform(geometry=GEOSGeometry(_OVERLAPPING_WKT, srid=4326), name_str="B")
        hits = Landform.objects.filter(geometry__intersects=a.geometry)
        assert hits.count() == 2

    def test_intersects_lookup_excludes_disjoint_landform(self) -> None:
        far_wkt = "MULTIPOLYGON (((60.0 10.0, 61.0 10.0, 61.0 11.0, 60.0 11.0, 60.0 10.0)))"
        a = _landform(name_str="A")
        _landform(geometry=GEOSGeometry(far_wkt, srid=4326), name_str="Far")
        hits = Landform.objects.filter(geometry__intersects=a.geometry)
        assert hits.count() == 1
