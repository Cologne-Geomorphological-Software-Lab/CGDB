"""Tests for the field_data system checks (field_data/checks.py)."""

from unittest.mock import patch

from django.contrib.gis.gdal import GDALException
from django.contrib.gis.geos import Point
from django.test import SimpleTestCase

from field_data.checks import check_coordinate_transform


class CoordinateTransformCheckTest(SimpleTestCase):
    def test_passes_with_a_working_proj(self):
        self.assertEqual(check_coordinate_transform(), [])

    def test_reports_an_error_when_the_transform_fails(self):
        with patch.object(
            Point, "transform", side_effect=GDALException("OGR failure.")
        ):
            (error,) = check_coordinate_transform()
        self.assertEqual(error.id, "field_data.E001")
        self.assertIn("EPSG:32634", error.msg)
        self.assertIn("OGR failure.", error.msg)
