"""Tests for prototype views: stat_data() and _build_monthly_performance().

Uses an empty DB so all counts start at zero – avoids ZeroDivisionError path
being masked by leftover data.
"""

from django.test import TestCase
from django.utils import timezone

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

    def test_performance_has_two_entries(self):
        result = stat_data()
        self.assertEqual(len(result["performance"]), 2)

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
