"""Tests for CosmogenicNuclideDating model, admin, and API (tech debt A13).

Previously had zero coverage anywhere in the suite despite being one of the
largest models in the app (~45 fields) with a 6-tab custom admin. Mirrors
the pattern already used for LuminescenceDating (test_luminescence.py) and
GrainSize (test_api.py).
"""

from __future__ import annotations

from typing import ClassVar

from django.contrib import admin as django_admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import RestrictedError
from django.test import SimpleTestCase, TestCase
from guardian.shortcuts import assign_perm
from rest_framework.test import APIClient

from analysis.admin import CosmogenicNuclideDatingAdmin
from analysis.models import CosmogenicNuclideDating, current_year
from field_data.models import Location, Sample
from prototype.models import Project

# ===========================================================================
# Shared fixture
# ===========================================================================


class _CosmogenicSetup(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="cosmo_user", password="pw")
        cls.project = Project.objects.create(
            title="Cosmogenic Project", label="CNP01", status="ACTIVE"
        )
        cls.location = Location.objects.create(
            identifier="CNP_LOC",
            data_source="internal",
            project=cls.project,
        )
        cls.sample = Sample.objects.create(
            identifier="CNP_S01",
            project=cls.project,
            location=cls.location,
        )
        cls.dating = CosmogenicNuclideDating.objects.create(
            sample=cls.sample,
            lab_id="CRONUS-2024-001",
            nuclide="10Be",
        )


# ===========================================================================
# __str__ edge cases
# ===========================================================================


class CosmogenicNuclideDatingStrSimpleTest(SimpleTestCase):
    """Tests that do not need a DB -- build instances via __new__."""

    def _make(self, pk: object, lab_id: str, nuclide: str):
        obj = CosmogenicNuclideDating.__new__(CosmogenicNuclideDating)
        obj.pk = pk
        obj.lab_id = lab_id
        obj.nuclide = nuclide
        return obj

    def test_str_with_lab_id_and_nuclide(self):
        obj = self._make(1, "CRONUS-2024-001", "10Be")
        self.assertEqual(str(obj), "CRONUS-2024-001 (10Be)")

    def test_str_empty_lab_id_uses_pk(self):
        obj = self._make(5, "", "26Al")
        self.assertEqual(str(obj), "ID-5 (26Al)")

    def test_str_empty_nuclide_shows_unknown(self):
        obj = self._make(3, "CRONUS-X", "")
        self.assertEqual(str(obj), "CRONUS-X (Unknown)")

    def test_str_unsaved_no_lab_id(self):
        obj = self._make(None, "", "")
        self.assertEqual(str(obj), "Unsaved (Unknown)")


class CosmogenicNuclideDatingStrDBTest(_CosmogenicSetup):
    def test_str_with_saved_object(self):
        self.assertEqual(str(self.dating), "CRONUS-2024-001 (10Be)")


# ===========================================================================
# year_of_publication validators (mirrors LuminescenceDating -- this model
# already uses the correct unbound max_value_current_year validator, unlike
# LuminescenceDating did before A6's fix)
# ===========================================================================


class CosmogenicNuclideDatingYearValidatorTest(_CosmogenicSetup):
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


class CosmogenicNuclideDatingFieldsTest(_CosmogenicSetup):
    def test_only_sample_required(self):
        d = CosmogenicNuclideDating.objects.create(sample=self.sample)
        self.assertIsNotNone(d.pk)

    def test_decimal_fields_nullable(self):
        d = CosmogenicNuclideDating.objects.create(sample=self.sample)
        for field_name in (
            "nuclide_concentration",
            "exposure_age",
            "burial_age",
            "denudation_rate",
            "production_rate",
            "topographic_shielding",
            "error_total",
        ):
            self.assertIsNone(
                getattr(d, field_name), msg=f"{field_name} should be None"
            )

    def test_raw_data_nullable(self):
        d = CosmogenicNuclideDating.objects.create(sample=self.sample)
        self.assertIsNone(d.raw_data)

    def test_nuclide_choices_complete(self):
        choices = dict(CosmogenicNuclideDating.NUCLIDE_CHOICES)
        for expected in ("10Be", "26Al", "36Cl", "3He", "21Ne", "14C"):
            self.assertIn(expected, choices)

    def test_mineral_choices_complete(self):
        choices = dict(CosmogenicNuclideDating.MINERAL_CHOICES)
        for expected in ("qtz", "fsp", "px", "ol", "cc", "wr", "other"):
            self.assertIn(expected, choices)

    def test_approach_choices_complete(self):
        choices = dict(CosmogenicNuclideDating.APPROACH_CHOICES)
        for expected in ("exposure", "burial", "denudation"):
            self.assertIn(expected, choices)

    def test_scaling_choices_complete(self):
        choices = dict(CosmogenicNuclideDating.SCALING_CHOICES)
        for expected in ("LSD", "LSDn", "St", "Lm", "Du", "De"):
            self.assertIn(expected, choices)

    def test_default_published_is_false(self):
        d = CosmogenicNuclideDating.objects.create(sample=self.sample)
        self.assertFalse(d.published)

    def test_default_thesis_is_none_string(self):
        d = CosmogenicNuclideDating.objects.create(sample=self.sample)
        self.assertEqual(d.thesis, "None")

    def test_sample_fk_restrict_on_delete(self):
        s = Sample.objects.create(
            identifier="CNP_RESTRICT_S",
            project=self.project,
            location=self.location,
        )
        CosmogenicNuclideDating.objects.create(sample=s)
        with self.assertRaises(RestrictedError):
            s.delete()


# ===========================================================================
# Admin: colored @display methods
# ===========================================================================


class CosmogenicNuclideDatingAdminDisplayTest(_CosmogenicSetup):
    """A ModelAdmin instance holds non-deepcopy-safe refs (unfold module
    internals), so it can't be a setUpTestData class attribute -- Django
    deep-copies those per test method. Build it fresh in setUp instead."""

    def setUp(self):
        self.admin_instance = CosmogenicNuclideDatingAdmin(
            CosmogenicNuclideDating, django_admin.site
        )

    def test_colored_nuclide_returns_nuclide_value(self):
        self.assertEqual(self.admin_instance.colored_nuclide(self.dating), "10Be")

    def test_colored_approach_returns_approach_value(self):
        self.dating.dating_approach = "exposure"
        self.assertEqual(
            self.admin_instance.colored_approach(self.dating), "exposure"
        )

    def test_colored_exposure_age_shows_dash_when_absent(self):
        self.assertEqual(
            self.admin_instance.colored_exposure_age(self.dating), "—"
        )

    def test_colored_exposure_age_formats_value_without_error(self):
        self.dating.exposure_age = 12.5
        self.assertEqual(
            self.admin_instance.colored_exposure_age(self.dating), "12.5"
        )

    def test_colored_exposure_age_includes_external_error(self):
        self.dating.exposure_age = 12.5
        self.dating.exposure_age_error_external = 0.8
        self.assertEqual(
            self.admin_instance.colored_exposure_age(self.dating), "12.5 ± 0.8"
        )


# ===========================================================================
# API: read-only, sample-scoped viewset smoke test
# ===========================================================================


class CosmogenicNuclideDatingViewSetTest(TestCase):
    member: ClassVar[User]
    non_member: ClassVar[User]
    project: ClassVar[Project]
    dating: ClassVar[CosmogenicNuclideDating]

    @classmethod
    def setUpTestData(cls):
        cls.member = User.objects.create_user(
            username="cosmo_api_member", password="pw"
        )
        cls.non_member = User.objects.create_user(
            username="cosmo_api_non_member", password="pw"
        )
        cls.project = Project.objects.create(
            title="Cosmogenic API Project", label="CAP01", status="ACTIVE"
        )
        assign_perm("view_project", cls.member, cls.project)
        location = Location.objects.create(
            identifier="CAP_LOC", data_source="internal", project=cls.project
        )
        sample = Sample.objects.create(
            identifier="CAP_S01", project=cls.project, location=location
        )
        cls.dating = CosmogenicNuclideDating.objects.create(
            sample=sample, lab_id="CRONUS-API-001", nuclide="26Al"
        )

    def test_member_sees_cosmogenic_dating(self) -> None:
        client = APIClient()
        client.force_authenticate(user=self.member)
        resp = client.get("/api/v1/cosmogenic-nuclide-datings/")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["results"]]
        assert self.dating.pk in ids

    def test_non_member_detail_returns_403_or_404(self) -> None:
        client = APIClient()
        client.force_authenticate(user=self.non_member)
        resp = client.get(
            f"/api/v1/cosmogenic-nuclide-datings/{self.dating.pk}/"
        )
        assert resp.status_code in (403, 404)

    def test_unauthenticated_returns_401_or_403(self) -> None:
        client = APIClient()
        resp = client.get("/api/v1/cosmogenic-nuclide-datings/")
        assert resp.status_code in (401, 403)
