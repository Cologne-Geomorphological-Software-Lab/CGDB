"""Tests for prototype core models.

Covers: Researcher.__str__, ResearchGroup.__str__, Project.__str__,
Country.__str__, Province.__str__ (field_data geo models tested here
because they are simple enough for SimpleTestCase).
"""

from __future__ import annotations

from django.contrib.auth.models import Group, User
from django.test import RequestFactory, SimpleTestCase, TestCase

from field_data.models import Country, Province
from prototype.middleware import CurrentUserMiddleware
from prototype.models import Project, Researcher, ResearchGroup

# ===========================================================================
# Researcher.__str__
# ===========================================================================


class ResearcherStrTest(SimpleTestCase):
    """Unit tests for Researcher.__str__ – no DB required."""

    def _make_researcher(self, last_name: str, first_name: str):
        user = User(last_name=last_name, first_name=first_name)
        r = Researcher()
        r.user = user
        return r

    def test_str_normal_user(self):
        r = self._make_researcher("Schmidt", "Anna")
        self.assertEqual(str(r), "Schmidt, Anna")

    def test_str_empty_names(self):
        r = self._make_researcher("", "")
        self.assertEqual(str(r), ", ")

    def test_str_with_none_user_raises(self):
        """Documented bug: Researcher.__str__ raises AttributeError when user is None."""
        r = Researcher()
        r.user = None
        with self.assertRaises(AttributeError):
            str(r)


# ===========================================================================
# ResearchGroup.__str__
# ===========================================================================


class ResearchGroupStrTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="rg_model_u", password="pw"
        )
        cls.researcher = Researcher.objects.create(
            user=cls.user, academic_rank="D", position="WiMa"
        )
        cls.auth_group = Group.objects.create(name="RG Model Test Group")
        cls.rg = ResearchGroup.objects.create(
            label="AG Geomorphologie",
            head_of_group=cls.researcher,
            auth_group=cls.auth_group,
        )

    def test_str_returns_label(self):
        self.assertEqual(str(self.rg), "AG Geomorphologie")

    def test_str_with_empty_label(self):
        rg = ResearchGroup(label="")
        self.assertEqual(str(rg), "")


# ===========================================================================
# Project.__str__
# ===========================================================================


class ProjectStrTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(
            title="Löss-Stratigraphie Nordrhein-Westfalen",
            label="CGDB-2024",
            status="ACTIVE",
        )

    def test_str_returns_label(self):
        self.assertEqual(str(self.project), "CGDB-2024")

    def test_str_with_umlauts_in_label(self):
        p = Project(label="Löss-Projekt")
        self.assertEqual(str(p), "Löss-Projekt")


# ===========================================================================
# Country.__str__ / Province.__str__
# ===========================================================================


class CountryStrTest(SimpleTestCase):
    """Unit tests via __new__ – no DB required."""

    def _make_country(self, name: str, pk: int | None = None):
        c = Country.__new__(Country)
        c.name = name
        c.pk = pk
        c.id = pk
        return c

    def test_str_with_name(self):
        c = self._make_country("Germany")
        self.assertEqual(str(c), "Germany")

    def test_str_with_none_name_uses_id(self):
        c = self._make_country(None, pk=42)
        self.assertEqual(str(c), "Country 42")


class ProvinceStrTest(SimpleTestCase):
    """Unit tests via __new__ – no DB required."""

    def _make_province(self, name: str, pk: int | None = None):
        p = Province.__new__(Province)
        p.name = name
        p.pk = pk
        p.id = pk
        return p

    def test_str_with_name(self):
        p = self._make_province("Bayern")
        self.assertEqual(str(p), "Bayern")

    def test_str_with_none_name_uses_id(self):
        p = self._make_province(None, pk=7)
        self.assertEqual(str(p), "Province 7")


# ===========================================================================
# BaseModel.save() — audit trail (created_by/updated_by)
# ===========================================================================


class BaseModelAuditTrailTest(TestCase):
    """BaseModel.save() sets created_by/updated_by from CurrentUserMiddleware's
    thread-local state — the F1 fix for records created outside the admin
    (e.g. via the DRF API), which previously got NULL silently."""

    @classmethod
    def setUpTestData(cls):
        cls.user_a = User.objects.create_user(
            username="audit_user_a", password="pw"
        )
        cls.user_b = User.objects.create_user(
            username="audit_user_b", password="pw"
        )

    def _set_current_user(self, user):
        request = RequestFactory().get("/")
        request.user = user
        CurrentUserMiddleware(lambda _r: None)(request)

    def test_created_by_and_updated_by_set_on_create(self):
        self._set_current_user(self.user_a)
        project = Project.objects.create(
            title="Audit Project", label="AUD01", status="ACTIVE"
        )
        self.assertEqual(project.created_by, self.user_a)
        self.assertEqual(project.updated_by, self.user_a)

    def test_updated_by_changes_on_resave_created_by_unchanged(self):
        self._set_current_user(self.user_a)
        project = Project.objects.create(
            title="Audit Project 2", label="AUD02", status="ACTIVE"
        )
        self._set_current_user(self.user_b)
        project.title = "Renamed"
        project.save()
        project.refresh_from_db()
        self.assertEqual(project.created_by, self.user_a)
        self.assertEqual(project.updated_by, self.user_b)

    def test_no_current_user_leaves_fields_none(self):
        """Saves outside any request (shell, migration) get NULL, not an error."""
        project = Project.objects.create(
            title="Audit Project 3", label="AUD03", status="ACTIVE"
        )
        self.assertIsNone(project.created_by)
        self.assertIsNone(project.updated_by)
