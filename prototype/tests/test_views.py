"""Tests for prototype views: stat_data() and _build_monthly_performance().

Uses an empty DB so all counts start at zero – avoids ZeroDivisionError path
being masked by leftover data.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from guardian.shortcuts import assign_perm

from analysis.models import GrainSize
from field_data.models import Location, Sample
from prototype.models import Project
from prototype.views import (
    _build_monthly_performance,
    dashboard_callback,
    stat_data,
)


class _ViewSetup(TestCase):
    """Empty-DB baseline – no setUpTestData needed."""


# ===========================================================================
# stat_data()
# ===========================================================================


class StatDataStructureTest(_ViewSetup):

    def test_returns_dict_with_project_key(self):
        result = stat_data()
        self.assertIn("project", result)

    def test_project_key_has_four_entries(self):
        result = stat_data()
        self.assertEqual(len(result["project"]), 4)

    def test_project_tile_titles(self):
        result = stat_data()
        titles = [tile["title"] for tile in result["project"]]
        self.assertIn("Projects", titles)
        self.assertIn("Locations", titles)
        self.assertIn("Samples", titles)
        self.assertIn("Measurements", titles)

    def test_project_tile_metric_is_string(self):
        result = stat_data()
        for tile in result["project"]:
            self.assertIsInstance(tile["metric"], str)

    def test_performance_key_exists(self):
        result = stat_data()
        self.assertIn("performance", result)

    def test_performance_has_three_entries(self):
        result = stat_data()
        self.assertEqual(len(result["performance"]), 3)

    def test_zero_objects_no_division_error(self):
        # Empty DB → no ZeroDivisionError
        result = stat_data()
        footer = result["project"][0]["footer"]
        self.assertIn("0", footer)

    def test_project_count_reflects_db(self):
        Project.objects.create(
            title="Count Test", label="CT01", status="ACTIVE"
        )
        result = stat_data()
        projects_tile = next(
            t for t in result["project"] if t["title"] == "Projects"
        )
        self.assertEqual(projects_tile["metric"], "1")


# ===========================================================================
# _build_monthly_performance()
# ===========================================================================


class BuildMonthlyPerformanceTest(_ViewSetup):

    def test_returns_12_entries(self):
        result = _build_monthly_performance([Project])
        self.assertEqual(len(result), 12)

    def test_each_entry_is_list_of_two(self):
        result = _build_monthly_performance([Project])
        for entry in result:
            self.assertEqual(len(entry), 2)

    def test_labels_are_strings(self):
        result = _build_monthly_performance([Project])
        for entry in result:
            self.assertIsInstance(entry[0], str)

    def test_counts_are_integers(self):
        result = _build_monthly_performance([Project])
        for entry in result:
            self.assertIsInstance(entry[1], int)

    def test_last_entry_is_current_month(self):
        today = timezone.now()
        result = _build_monthly_performance([Project])
        last_label = result[-1][0]
        month_name = today.strftime("%B")
        year = str(today.year)
        self.assertIn(month_name, last_label)
        self.assertIn(year, last_label)

    def test_oldest_entry_is_11_months_ago(self):
        from dateutil.relativedelta import relativedelta

        today = timezone.now()
        oldest = today - relativedelta(months=11)
        result = _build_monthly_performance([Project])
        first_label = result[0][0]
        month_name = oldest.strftime("%B")
        self.assertIn(month_name, first_label)

    def test_current_month_count_reflected(self):
        Project.objects.create(
            title="Perf Test", label="PT01", status="ACTIVE"
        )
        result = _build_monthly_performance([Project])
        self.assertGreaterEqual(result[-1][1], 1)

    def test_multiple_model_classes_summed(self):
        project = Project.objects.create(
            title="Multi Perf", label="MP01", status="ACTIVE"
        )
        location = Location.objects.create(
            identifier="PERF_LOC",
            data_source="internal",
            project=project,
        )
        Sample.objects.create(
            identifier="PERF_S01",
            project=project,
            location=location,
        )
        result = _build_monthly_performance([Location, Sample])
        self.assertGreaterEqual(result[-1][1], 2)


# ===========================================================================
# stat_data() project scoping (architecture-review fix F14)
# ===========================================================================


class StatDataProjectScopingTest(_ViewSetup):
    """A staff user with view_project on only one of two projects must not
    see the other project's data reflected in the dashboard's aggregate
    counts -- previously every query here ran unfiltered."""

    def setUp(self):
        self.visible_project = Project.objects.create(
            title="Visible Project", label="VIS01", status="ACTIVE"
        )
        self.hidden_project = Project.objects.create(
            title="Hidden Project", label="HID01", status="ACTIVE"
        )
        self.staff_user = User.objects.create_user(
            username="dash_staff", password="pw", is_staff=True
        )
        assign_perm("view_project", self.staff_user, self.visible_project)

        self.visible_location = Location.objects.create(
            identifier="VIS_LOC",
            project=self.visible_project,
            data_source="internal",
        )
        Location.objects.create(
            identifier="HID_LOC",
            project=self.hidden_project,
            data_source="internal",
        )

    def _project_metric(self, result, title):
        tile = next(t for t in result["project"] if t["title"] == title)
        return int(tile["metric"])

    def test_superuser_sees_all_projects(self):
        superuser = User.objects.create_superuser(
            username="dash_super", password="pw"
        )
        result = stat_data(user=superuser)
        self.assertEqual(self._project_metric(result, "Projects"), 2)
        self.assertEqual(self._project_metric(result, "Locations"), 2)

    def test_none_user_is_unscoped_like_before(self):
        """dashboard_callback's request=None case must keep the pre-fix
        (unscoped) behavior, not silently show zero data."""
        result = stat_data(user=None)
        self.assertEqual(self._project_metric(result, "Projects"), 2)

    def test_scoped_staff_user_sees_only_accessible_project(self):
        result = stat_data(user=self.staff_user)
        self.assertEqual(self._project_metric(result, "Projects"), 1)
        self.assertEqual(self._project_metric(result, "Locations"), 1)

    def test_scoped_staff_user_with_no_permissions_sees_zero(self):
        no_access_user = User.objects.create_user(
            username="dash_noaccess", password="pw", is_staff=True
        )
        result = stat_data(user=no_access_user)
        self.assertEqual(self._project_metric(result, "Projects"), 0)
        self.assertEqual(self._project_metric(result, "Locations"), 0)

    def test_location_breakdown_excludes_inaccessible_project(self):
        result = stat_data(user=self.staff_user)
        total_in_breakdown = sum(
            row["n"] for row in result["location_breakdown"]
        )
        self.assertEqual(total_in_breakdown, 1)

    def test_literature_locations_stay_visible_when_scoped(self):
        """Literature-sourced data has no owning project and stays visible
        to all staff, matching the same exception used elsewhere (API
        querysets, admin get_queryset overrides)."""
        from bibliography.models import Author, Reference

        author = Author.objects.create(last_name="Geo", first_name="Test")
        reference = Reference.objects.create(
            title="Lit Ref", lead_author=author, abstract="x", type="Paper"
        )
        Location.objects.create(
            identifier="LIT_LOC", data_source="literature", reference=reference
        )
        result = stat_data(user=self.staff_user)
        # 1 accessible internal location + 1 literature location.
        self.assertEqual(self._project_metric(result, "Locations"), 2)

    def test_dashboard_callback_scopes_by_request_user(self):
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        request.user = self.staff_user
        context = {}
        dashboard_callback(request=request, context=context)
        self.assertEqual(self._project_metric(context, "Projects"), 1)


# ===========================================================================
# dashboard_callback()
# ===========================================================================


class DashboardCallbackTest(_ViewSetup):

    def test_dashboard_callback_merges_stat_data(self):
        context = {}
        dashboard_callback(request=None, context=context)
        self.assertIn("project", context)
        self.assertIn("performance", context)

    def test_dashboard_callback_returns_context(self):
        context = {"existing_key": "existing_value"}
        returned = dashboard_callback(request=None, context=context)
        self.assertIs(returned, context)
        self.assertIn("existing_key", returned)
