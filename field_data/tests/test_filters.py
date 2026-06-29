"""Tests for field_data FilterSet definitions."""

from django.test import TestCase

from field_data.filters import LocationFilter, SampleFilter
from field_data.models import Location, Sample


class LocationFilterTest(TestCase):
    def test_filter_instantiates(self):
        f = LocationFilter(queryset=Location.objects.none())
        self.assertIsNotNone(f)

    def test_study_area_label_set(self):
        self.assertEqual(
            LocationFilter.base_filters["study_site__study_area"].label,
            "Study area",
        )

    def test_filter_fields(self):
        f = LocationFilter(queryset=Location.objects.none())
        self.assertIn("exposure_type", f.filters)
        self.assertIn("identifier", f.filters)


class SampleFilterTest(TestCase):
    def test_filter_instantiates(self):
        f = SampleFilter(queryset=Sample.objects.none())
        self.assertIsNotNone(f)

    def test_filter_fields(self):
        f = SampleFilter(queryset=Sample.objects.none())
        self.assertIn("processor", f.filters)
        self.assertIn("type", f.filters)
