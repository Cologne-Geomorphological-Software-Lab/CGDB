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
from django.test import SimpleTestCase, TestCase

from analysis.models import (
    Counting,
    GenericMeasurement,
    GrainSize,
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
        cls.user = User.objects.create_user(username="aext_user", password="pw")
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
        cls.method = Method.objects.create(name="XRF Analysis", category="CHEM")
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


# ===========================================================================
# Counting.__str__
# ===========================================================================


class CountingStrTest(_AnalysisExtSetup):

    def test_str_returns_sample_str(self):
        counting = Counting.objects.create(
            sample=self.sample, type="Percent"
        )
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
        counting = Counting.objects.create(sample=self.sample, type="Absolute numbers")
        pollen = Pollen.objects.create(name="Betula", token="BET")
        pc = PollenCount.objects.create(counting=counting, pollen=pollen, number=42)
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
        uploaded = SimpleUploadedFile("testdata.txt", b"content", content_type="text/plain")
        rm = RawMeasurement.objects.create(
            project=self.project,
            device=self.device,
            researcher=self.researcher,
            file=uploaded,
        )
        # Django may append a suffix to avoid name collisions; check stem and extension
        name = rm.filename()
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
