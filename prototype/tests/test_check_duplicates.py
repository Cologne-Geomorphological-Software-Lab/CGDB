"""Tests for the check_duplicates management command (#256, #285)."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from analysis.models import Counting, Pollen, PollenCount
from field_data.models import Location, Sample
from prototype.models import Project


class CheckDuplicatesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(
            title="Dup Project", label="DUP01", status="ACTIVE"
        )

    def _run(self) -> str:
        out = StringIO()
        call_command("check_duplicates", stdout=out)
        return out.getvalue()

    def test_reports_nothing_on_clean_data(self):
        Location.objects.create(
            identifier="DUP-01", data_source="internal", project=self.project
        )
        self.assertIn("No duplicates found", self._run())

    def test_lists_duplicate_locations_and_pollen_counts(self):
        # bulk_create skips save() and therefore the validation that now
        # stops these duplicates from being entered.
        Location.objects.bulk_create(
            [
                Location(
                    identifier="DUP-02",
                    data_source="internal",
                    project=self.project,
                ),
                Location(
                    identifier="DUP-02",
                    data_source="internal",
                    project=self.project,
                ),
            ]
        )
        location = Location.objects.create(
            identifier="DUP-03", data_source="internal", project=self.project
        )
        sample = Sample.objects.create(
            identifier="DUP-S01", project=self.project, location=location
        )
        counting = Counting.objects.create(
            sample=sample, type="Absolute numbers"
        )
        pollen = Pollen.objects.create(name="Betula", token="BET")
        PollenCount.objects.bulk_create(
            [
                PollenCount(counting=counting, pollen=pollen, number=1),
                PollenCount(counting=counting, pollen=pollen, number=2),
            ]
        )
        output = self._run()
        self.assertIn("Location 'DUP-02' appears 2 times", output)
        self.assertIn("Taxon Betula is counted 2 times", output)
        self.assertIn("2 duplicate group(s)", output)
