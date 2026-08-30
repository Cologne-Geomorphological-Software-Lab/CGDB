"""Tests for remaining analysis models.

Covers: RadiocarbonDating, Counting, Pollen, PollenCount, GenericMeasurement,
MicroXRFMeasurement, MicroXRFElementMap __str__ methods;
RawMeasurement.filename(), RawProcessing.processed_filename();
GrainSize.save() integration (reclassify triggered, no-data path).
"""

from decimal import Decimal
from unittest.mock import MagicMock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import RestrictedError
from django.test import SimpleTestCase, TestCase

from analysis.models import (
    Counting,
    CosmogenicNuclideDating,
    GenericMeasurement,
    GrainSize,
    LuminescenceDating,
    MeasurementSeries,
    MicroXRFElementMap,
    MicroXRFMeasurement,
    Parameter,
    Pollen,
    PollenCount,
    RadiocarbonDating,
    RawMeasurement,
    RawProcessing,
)
from field_data.models import Location, Sample
from laboratory.models import Device, Method
from prototype.models import Project, Researcher


class _AnalysisExtSetup(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="aext_user", password="pw"
        )
        cls.researcher = Researcher.objects.create(
            user=cls.user, academic_rank="D", position="WiMa"
        )
        cls.project = Project.objects.create(
            title="Other Analysis Project", label="OAP01", status="ACTIVE"
        )
        cls.location = Location.objects.create(
            identifier="OAP_LOC",
            data_source="internal",
            project=cls.project,
        )
        cls.sample = Sample.objects.create(
            identifier="OAP_S01",
            project=cls.project,
            location=cls.location,
        )
        cls.device = Device.objects.create(name="XRF Device")
        cls.method = Method.objects.create(
            name="XRF Analysis", category="CHEM"
        )
        cls.parameter = Parameter.objects.create(
            name="Iron", token="Fe", unit="mg/kg"
        )


# ===========================================================================
# RadiocarbonDating.__str__
# ===========================================================================


class RadiocarbonDatingStrTest(_AnalysisExtSetup):

    def test_str_format(self):
        dating = RadiocarbonDating.objects.create(
            sample=self.sample,
            lab="Poznań",
            lab_id="Poz-12345",
            age=Decimal("12.500"),
        )
        self.assertEqual(str(dating), "Poz-12345 (12.500 ka)")

    def test_str_with_none_age(self):
        dating = RadiocarbonDating.objects.create(
            sample=self.sample,
            lab="Poznań",
            lab_id="Poz-99999",
            age=None,
        )
        result = str(dating)
        self.assertIn("Poz-99999", result)
        self.assertIn("undated", result)


class RadiocarbonDatingQualityTest(_AnalysisExtSetup):

    def test_default_data_quality_is_pending(self):
        dating = RadiocarbonDating.objects.create(
            sample=self.sample, lab="Poznań", lab_id="Poz-00001"
        )
        self.assertEqual(dating.data_quality, "pending")

    def test_data_quality_and_quality_note_can_be_set(self):
        dating = RadiocarbonDating.objects.create(
            sample=self.sample,
            lab="Poznań",
            lab_id="Poz-00002",
            data_quality="rejected",
            quality_note="Contamination suspected.",
        )
        dating.refresh_from_db()
        self.assertEqual(dating.data_quality, "rejected")
        self.assertEqual(dating.quality_note, "Contamination suspected.")


# ===========================================================================
# Counting.__str__
# ===========================================================================


class CountingStrTest(_AnalysisExtSetup):

    def test_str_returns_sample_str(self):
        counting = Counting.objects.create(sample=self.sample, type="Percent")
        self.assertEqual(str(counting), str(self.sample))


# ===========================================================================
# Pollen.__str__
# ===========================================================================


class PollenStrTest(SimpleTestCase):

    def test_str_returns_latin_name(self):
        p = Pollen.__new__(Pollen)
        p.name = "Quercus robur"
        self.assertEqual(str(p), "Quercus robur")


# ===========================================================================
# PollenCount.__str__
# ===========================================================================


class PollenCountStrTest(_AnalysisExtSetup):

    def test_str_format(self):
        counting = Counting.objects.create(
            sample=self.sample, type="Absolute numbers"
        )
        pollen = Pollen.objects.create(name="Betula", token="BET")
        pc = PollenCount.objects.create(
            counting=counting, pollen=pollen, number=42
        )
        expected = f"{counting} - {pollen}"
        self.assertEqual(str(pc), expected)


# ===========================================================================
# GenericMeasurement.__str__
# ===========================================================================


class GenericMeasurementStrTest(_AnalysisExtSetup):

    def test_str_format(self):
        gm = GenericMeasurement.objects.create(
            sample=self.sample,
            method=self.method,
            parameter=self.parameter,
            value=123.4,
        )
        result = str(gm)
        self.assertIn(str(self.sample), result)
        self.assertIn(str(self.method), result)
        self.assertIn(str(self.parameter), result)


class GenericMeasurementSeriesFieldTest(_AnalysisExtSetup):
    """tech debt A12: measurement_series (formerly PascalCase
    "MeasurementSeries") must round-trip through the pinned db_column
    without Django or the DB ever seeing a mismatch."""

    def test_field_is_snake_case_and_persists(self):
        self.assertFalse(
            hasattr(GenericMeasurement, "MeasurementSeries"),
            "old PascalCase field name should no longer exist",
        )
        series = MeasurementSeries.objects.create(datetime="2024-01-01T00:00:00Z")
        gm = GenericMeasurement.objects.create(
            sample=self.sample,
            method=self.method,
            parameter=self.parameter,
            value=1.0,
            measurement_series=series,
        )
        gm.refresh_from_db()
        self.assertEqual(gm.measurement_series, series)


# ===========================================================================
# MicroXRFMeasurement.__str__
# ===========================================================================


class MicroXRFMeasurementStrTest(_AnalysisExtSetup):

    def test_str_format(self):
        m = MicroXRFMeasurement.objects.create(
            sample=self.sample,
            measurement_date="2024-05-10",
        )
        result = str(m)
        self.assertIn("MicroXRF", result)
        self.assertIn(str(self.sample), result)
        self.assertIn("2024-05-10", result)

    def test_str_with_none_date(self):
        m = MicroXRFMeasurement.objects.create(
            sample=self.sample,
            measurement_date=None,
        )
        result = str(m)
        self.assertIn("MicroXRF", result)
        self.assertIn("None", result)


# ===========================================================================
# MicroXRFElementMap.__str__
# ===========================================================================


class MicroXRFElementMapStrTest(_AnalysisExtSetup):

    def test_str_format(self):
        measurement = MicroXRFMeasurement.objects.create(sample=self.sample)
        elem_map = MicroXRFElementMap(
            measurement=measurement,
            element="Fe",
            raster_file="microxrf_raster/test.tif",
        )
        result = str(elem_map)
        self.assertIn("Fe", result)
        self.assertIn("map", result)


# ===========================================================================
# RawMeasurement.filename()
# ===========================================================================


class RawMeasurementFilenameTest(_AnalysisExtSetup):

    def test_filename_with_file(self):
        uploaded = SimpleUploadedFile(
            "testdata.txt", b"content", content_type="text/plain"
        )
        rm = RawMeasurement.objects.create(
            project=self.project,
            device=self.device,
            researcher=self.researcher,
            file=uploaded,
        )
        # Django may append a suffix to avoid name collisions; check stem and extension
        name = rm.filename()
        assert name is not None
        self.assertTrue(name.startswith("testdata"))
        self.assertTrue(name.endswith(".txt"))

    def test_filename_without_file(self):
        rm = RawMeasurement.__new__(RawMeasurement)
        rm.file = None
        self.assertIsNone(rm.filename())


# ===========================================================================
# RawProcessing.processed_filename()
# ===========================================================================


class RawProcessingFilenameTest(_AnalysisExtSetup):

    def test_processed_filename_with_file(self):
        rp = RawProcessing.__new__(RawProcessing)
        mock_file = MagicMock()
        mock_file.name = "analysis/processed_data/result.csv"
        rp.processed_file = mock_file
        self.assertEqual(rp.processed_filename(), "result.csv")

    def test_processed_filename_without_file(self):
        rp = RawProcessing.__new__(RawProcessing)
        rp.processed_file = None
        self.assertIsNone(rp.processed_filename())


# ===========================================================================
# GrainSize.save() – integration
# ===========================================================================


class GrainSizeSaveIntegrationTest(_AnalysisExtSetup):

    def test_save_triggers_reclassify(self):
        gs = GrainSize.objects.create(
            sample=self.sample,
            method="L",
            classes=[1.0, 70.0],
            measured_data=[40.0, 60.0],
        )
        self.assertAlmostEqual(gs.clay, 40.0)
        self.assertAlmostEqual(gs.fine_sand, 60.0)

    def test_save_without_measured_data_skips_reclassify(self):
        gs = GrainSize.objects.create(
            sample=self.sample,
            method="L",
            classes=[1.0, 70.0],
            measured_data=None,
        )
        self.assertIsNone(gs.clay)
        self.assertIsNone(gs.fine_sand)


# ===========================================================================
# Sample FK on_delete=RESTRICT — consistency across all 7 measurement models
# (tech debt A3: 3 of these used to be CASCADE, silently destroying data on
# Sample deletion instead of blocking it like the other 4).
# ===========================================================================


class SampleDeletionProtectionTest(_AnalysisExtSetup):
    """Deleting a Sample must be blocked while any measurement references it,
    consistently across every measurement model, not just some of them."""

    def _make_sample(self, identifier: str):
        from field_data.models import Sample

        return Sample.objects.create(
            identifier=identifier, project=self.project, location=self.location
        )

    def test_counting_restricts_sample_deletion(self):
        s = self._make_sample("A3_COUNTING")
        Counting.objects.create(sample=s, type="Percent")
        with self.assertRaises(RestrictedError):
            s.delete()

    def test_luminescence_dating_restricts_sample_deletion(self):
        s = self._make_sample("A3_LUM")
        LuminescenceDating.objects.create(sample=s)
        with self.assertRaises(RestrictedError):
            s.delete()

    def test_radiocarbon_dating_restricts_sample_deletion(self):
        s = self._make_sample("A3_RADIOCARBON")
        RadiocarbonDating.objects.create(
            sample=s, lab="Poznań", lab_id="Poz-A3", age=Decimal("12.500")
        )
        with self.assertRaises(RestrictedError):
            s.delete()

    def test_cosmogenic_nuclide_dating_restricts_sample_deletion(self):
        s = self._make_sample("A3_COSMOGENIC")
        CosmogenicNuclideDating.objects.create(sample=s)
        with self.assertRaises(RestrictedError):
            s.delete()

    def test_generic_measurement_restricts_sample_deletion(self):
        s = self._make_sample("A3_GENERIC")
        GenericMeasurement.objects.create(
            sample=s, method=self.method, parameter=self.parameter, value=1.0
        )
        with self.assertRaises(RestrictedError):
            s.delete()

    def test_grain_size_restricts_sample_deletion(self):
        s = self._make_sample("A3_GRAINSIZE")
        GrainSize.objects.create(sample=s, method="L", measured_data=None)
        with self.assertRaises(RestrictedError):
            s.delete()

    def test_microxrf_measurement_restricts_sample_deletion(self):
        s = self._make_sample("A3_MICROXRF")
        MicroXRFMeasurement.objects.create(sample=s)
        with self.assertRaises(RestrictedError):
            s.delete()
