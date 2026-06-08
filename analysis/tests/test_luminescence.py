"""Tests for LuminescenceDating model.

Covers: __str__ edge-cases, year_of_publication validators,
required/optional fields, choices, defaults, FK protect-on-delete.
"""
import datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import RestrictedError
from django.test import SimpleTestCase, TestCase

from analysis.models import LuminescenceDating, current_year, max_value_current_year
from field_data.models import Location, Sample
from prototype.models import Project


# ===========================================================================
# Shared fixture
# ===========================================================================


class _LuminescenceSetup(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="lum_user", password="pw")
        cls.project = Project.objects.create(
            title="Luminescence Project", label="LP01", status="ACTIVE"
        )
        cls.location = Location.objects.create(
            identifier="LUM_LOC",
            data_source="internal",
            project=cls.project,
        )
        cls.sample = Sample.objects.create(
            identifier="LUM_S01",
            project=cls.project,
            location=cls.location,
        )
        cls.dating = LuminescenceDating.objects.create(
            sample=cls.sample,
            laboratory_id="CLL-2024-001",
            mineral="Quartz",
        )


# ===========================================================================
# __str__ edge cases (some via SimpleTestCase + __new__)
# ===========================================================================


class LuminescenceDatingStrSimpleTest(SimpleTestCase):
    """Tests that do not need a DB – build instances via __new__."""

    def _make(self, pk, lab_id, mineral):
        obj = LuminescenceDating.__new__(LuminescenceDating)
        obj.pk = pk
        obj.laboratory_id = lab_id
        obj.mineral = mineral
        return obj

    def test_str_with_lab_id_and_mineral(self):
        obj = self._make(1, "CLL-2024-001", "Quartz")
        self.assertEqual(str(obj), "CLL-2024-001 Quartz")

    def test_str_empty_lab_id_uses_pk(self):
        obj = self._make(5, "", "Feldspar")
        self.assertEqual(str(obj), "ID-5 Feldspar")

    def test_str_empty_mineral_shows_unknown(self):
        obj = self._make(3, "CLL-X", "")
        self.assertEqual(str(obj), "CLL-X Unknown")

    def test_str_unsaved_no_lab_id(self):
        obj = self._make(None, "", "")
        self.assertEqual(str(obj), "Unsaved Unknown")

    def test_str_unsaved_with_lab_id(self):
        obj = self._make(None, "CLL-TEMP", "Polymineral")
        self.assertEqual(str(obj), "CLL-TEMP Polymineral")


class LuminescenceDatingStrDBTest(_LuminescenceSetup):

    def test_str_with_saved_object(self):
        self.assertEqual(str(self.dating), "CLL-2024-001 Quartz")


# ===========================================================================
# year_of_publication validators
# ===========================================================================


class MaxValueCurrentYearFunctionTest(SimpleTestCase):
    """Tests for the standalone max_value_current_year validator function."""

    def test_accepts_current_year(self):
        max_value_current_year(current_year())  # must not raise

    def test_rejects_future_year(self):
        with self.assertRaises(ValidationError):
            max_value_current_year(current_year() + 1)

    def test_accepts_past_year(self):
        max_value_current_year(2000)  # must not raise

    def test_current_year_returns_int(self):
        self.assertIsInstance(current_year(), int)

    def test_current_year_matches_today(self):
        self.assertEqual(current_year(), datetime.date.today().year)


class LuminescenceDatingYearValidatorTest(_LuminescenceSetup):

    def test_year_below_1984_fails_validation(self):
        self.dating.year_of_publication = 1983
        with self.assertRaises(ValidationError) as cm:
            self.dating.full_clean()
        self.assertIn("year_of_publication", cm.exception.message_dict)

    def test_year_1984_passes_validation(self):
        self.dating.year_of_publication = 1984
        self.dating.full_clean()  # must not raise

    def test_year_current_year_passes_validation(self):
        self.dating.year_of_publication = current_year()
        self.dating.full_clean()  # must not raise

    def test_year_future_fails_validation(self):
        self.dating.year_of_publication = current_year() + 1
        with self.assertRaises(ValidationError) as cm:
            self.dating.full_clean()
        self.assertIn("year_of_publication", cm.exception.message_dict)


# ===========================================================================
# Required / optional fields, defaults, choices
# ===========================================================================


class LuminescenceDatingFieldsTest(_LuminescenceSetup):

    def test_only_sample_required(self):
        d = LuminescenceDating.objects.create(sample=self.sample)
        self.assertIsNotNone(d.pk)

    def test_decimal_fields_nullable(self):
        d = LuminescenceDating.objects.create(sample=self.sample)
        for field_name in (
            "luminescence_age", "age_error", "dose_rate", "dose_rate_error",
            "palaeodose_value", "palaeodose_error", "g_value", "g_value_error",
        ):
            self.assertIsNone(getattr(d, field_name), msg=f"{field_name} should be None")

    def test_mineral_choices_complete(self):
        choices = dict(LuminescenceDating.CHOICES_MINERAL)
        for expected in ("Quartz", "Feldspar", "Polymineral", "Other"):
            self.assertIn(expected, choices)

    def test_dating_approach_choices_complete(self):
        choices = dict(LuminescenceDating.CHOICES_DATING_APPROACH)
        for expected in ("Burial dating", "Exposure dating", "Other"):
            self.assertIn(expected, choices)

    def test_default_published_is_false(self):
        d = LuminescenceDating.objects.create(sample=self.sample)
        self.assertFalse(d.published)

    def test_default_fading_correction_is_false(self):
        d = LuminescenceDating.objects.create(sample=self.sample)
        self.assertFalse(d.fading_correction)

    def test_default_thesis_is_none_string(self):
        d = LuminescenceDating.objects.create(sample=self.sample)
        self.assertEqual(d.thesis, "None")

    def test_sample_fk_restrict_on_delete(self):
        s = Sample.objects.create(
            identifier="LUM_RESTRICT_S",
            project=self.project,
            location=self.location,
        )
        LuminescenceDating.objects.create(sample=s)
        with self.assertRaises(RestrictedError):
            s.delete()
