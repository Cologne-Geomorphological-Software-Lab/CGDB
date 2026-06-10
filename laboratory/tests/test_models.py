"""Tests for laboratory models.

Covers: __str__ for all models, Method choices, Calibration str with
em-dash, Firmware str, AccessoryParameter str.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from laboratory.models import (
    Accessory,
    AccessoryParameter,
    Calibration,
    Device,
    Firmware,
    Manufacturer,
    Method,
)
from prototype.models import Researcher


class _LabSetup(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manufacturer = Manufacturer.objects.create(
            name="Malvern Panalytical",
            website="https://www.malvernpanalytical.com",
        )
        cls.device = Device.objects.create(
            name="Mastersizer 3000",
            manufacturer=cls.manufacturer,
            token="MS3K",
        )
        cls.accessory = Accessory.objects.create(
            device=cls.device,
            name="Hydro EV",
        )
        cls.method = Method.objects.create(
            name="Laser Diffraction",
            category="PHY",
            laboratory="PHY",
            available=True,
        )
        cls.user = User.objects.create_user(
            username="lab_model_user", password="pw"
        )
        cls.researcher = Researcher.objects.create(
            user=cls.user, academic_rank="D", position="WiMa"
        )
        cls.calibration = Calibration.objects.create(
            device=cls.device,
            date="2024-03-15",
            researcher=cls.researcher,
        )
        cls.firmware = Firmware.objects.create(
            device=cls.device,
            version="3.40",
            installation_date="2024-01-01",
        )
        cls.param = AccessoryParameter.objects.create(
            method="dispersion",
            accessory=cls.accessory,
            parameter_name="pump_speed",
            parameter_value="2500",
            parameter_unit="rpm",
        )


# ===========================================================================
# Manufacturer
# ===========================================================================


class ManufacturerStrTest(_LabSetup):

    def test_str_returns_name(self):
        self.assertEqual(str(self.manufacturer), "Malvern Panalytical")


# ===========================================================================
# Device
# ===========================================================================


class DeviceStrTest(_LabSetup):

    def test_str_returns_name(self):
        self.assertEqual(str(self.device), "Mastersizer 3000")

    def test_str_without_manufacturer(self):
        d = Device.objects.create(name="Standalone Device")
        self.assertEqual(str(d), "Standalone Device")


# ===========================================================================
# Accessory
# ===========================================================================


class AccessoryStrTest(_LabSetup):

    def test_str_format(self):
        self.assertEqual(str(self.accessory), "Mastersizer 3000 - Hydro EV")


# ===========================================================================
# AccessoryParameter
# ===========================================================================


class AccessoryParameterStrTest(_LabSetup):

    def test_str_format(self):
        self.assertEqual(str(self.param), "Hydro EV - pump_speed: 2500")


# ===========================================================================
# Method
# ===========================================================================


class MethodStrTest(_LabSetup):

    def test_str_returns_name(self):
        self.assertEqual(str(self.method), "Laser Diffraction")

    def test_category_choices_are_valid(self):
        choices = dict(Method.CATEGORY_CHOICES)
        self.assertIn("CHEM", choices)
        self.assertIn("PHY", choices)
        self.assertIn("CHRO", choices)

    def test_laboratory_choices_are_valid(self):
        choices = dict(Method.LABORATORY_CHOICES)
        self.assertIn("PHY", choices)
        self.assertIn("CLL", choices)
        self.assertIn("EX", choices)

    def test_available_default_true(self):
        m = Method.objects.create(name="Default Method", category="CHEM")
        self.assertTrue(m.available)


# ===========================================================================
# Calibration
# ===========================================================================


class CalibrationStrTest(_LabSetup):

    def test_str_format(self):
        # Note: em-dash "–" as defined in Calibration.__str__
        result = str(self.calibration)
        self.assertIn("Mastersizer 3000", result)
        self.assertIn("2024-03-15", result)
        self.assertIn("–", result)


# ===========================================================================
# Firmware
# ===========================================================================


class FirmwareStrTest(_LabSetup):

    def test_str_format(self):
        self.assertEqual(str(self.firmware), "Mastersizer 3000 - 3.40")
