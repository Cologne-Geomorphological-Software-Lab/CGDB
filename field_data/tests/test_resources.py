"""Import/export round-trip tests for field_data's 6 wired resource classes.

tech debt FD9: none of LocationResource, CountryResource, ProvinceResource,
ExposureTypeResource, SampleTypeResource, or SiteResource had any test
coverage of an actual import/export round-trip - exactly how FD6's bug
(LayerResource referencing a nonexistent field) went unnoticed. Each test
here exports real rows to a tablib.Dataset, deletes the originals, and
re-imports the dataset, asserting the re-import is error-free and recreates
equivalent rows - the same path a maintainer exercises via the admin's
"Export"/"Import" actions.
"""

from typing import TYPE_CHECKING

from django.test import TestCase

from field_data.models import (
    Campaign,
    Country,
    ExposureType,
    Location,
    Province,
    SampleType,
    Site,
    StudyArea,
)
from field_data.resources import (
    CountryResource,
    ExposureTypeResource,
    LocationResource,
    ProvinceResource,
    SampleTypeResource,
    SiteResource,
)
from prototype.models import Project

if TYPE_CHECKING:
    _RoundTripBase = TestCase
else:
    _RoundTripBase = object


class _RoundTripMixin(_RoundTripBase):
    """Shared export -> delete -> import round-trip helper."""

    def _round_trip(self, resource_class, queryset):
        resource = resource_class()
        dataset = resource.export(queryset)
        self.assertGreater(len(dataset), 0)

        queryset.model.objects.filter(
            pk__in=list(queryset.values_list("pk", flat=True))
        ).delete()

        result = resource.import_data(dataset, raise_errors=True)
        self.assertFalse(result.has_errors())
        return result


class CountryResourceTest(_RoundTripMixin, TestCase):
    def test_round_trip(self):
        Country.objects.create(name="Testland", iso_code="TST")
        self._round_trip(CountryResource, Country.objects.all())
        self.assertTrue(Country.objects.filter(iso_code="TST").exists())


class ProvinceResourceTest(_RoundTripMixin, TestCase):
    def test_round_trip(self):
        country = Country.objects.create(name="Provinceland", iso_code="PRV")
        Province.objects.create(name="Test Province", country=country)
        self._round_trip(ProvinceResource, Province.objects.all())
        self.assertTrue(Province.objects.filter(name="Test Province").exists())


class ExposureTypeResourceTest(_RoundTripMixin, TestCase):
    def test_round_trip(self):
        ExposureType.objects.create(
            main_type="O",
            abbreviation="OC",
            name_ger="Aufschluss",
            name_en="Outcrop",
        )
        self._round_trip(ExposureTypeResource, ExposureType.objects.all())
        self.assertTrue(
            ExposureType.objects.filter(abbreviation="OC").exists()
        )


class SampleTypeResourceTest(_RoundTripMixin, TestCase):
    def test_round_trip(self):
        SampleType.objects.create(word="Bulk sediment", label="BLK")
        self._round_trip(SampleTypeResource, SampleType.objects.all())
        self.assertTrue(SampleType.objects.filter(label="BLK").exists())


class SiteResourceTest(_RoundTripMixin, TestCase):
    def test_round_trip(self):
        project = Project.objects.create(
            title="Site Resource Project", label="SRP01", status="ACTIVE"
        )
        study_area = StudyArea.objects.create(label="SA_RES01", project=project)
        Site.objects.create(label="SITE_RES01", study_area=study_area)
        self._round_trip(SiteResource, Site.objects.all())
        self.assertTrue(Site.objects.filter(label="SITE_RES01").exists())


class LocationResourceTest(_RoundTripMixin, TestCase):
    def test_round_trip(self):
        project = Project.objects.create(
            title="Location Resource Project", label="LRP01", status="ACTIVE"
        )
        campaign = Campaign.objects.create(label="CAMP_RES01", project=project)
        exposure_type = ExposureType.objects.create(
            main_type="B",
            abbreviation="BH",
            name_ger="Bohrung",
            name_en="Borehole",
        )
        Location.objects.create(
            identifier="LOC_RES01",
            data_source="internal",
            project=project,
            campaign=campaign,
            exposure_type=exposure_type,
            altitude=1200.5,
        )
        self._round_trip(LocationResource, Location.objects.all())
        restored = Location.objects.get(identifier="LOC_RES01")
        self.assertEqual(restored.project, project)
        self.assertEqual(restored.campaign, campaign)
        self.assertEqual(restored.exposure_type, exposure_type)
        self.assertEqual(restored.altitude, 1200.5)
