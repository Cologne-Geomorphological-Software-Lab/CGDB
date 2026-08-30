"""Tests for GrainSizeResource (tech debt A7).

Originally GrainSizeResource omitted raw_data, classes, measured_data, and
source - a CSV bulk import silently dropped provenance data that the
single-record admin upload path (GrainSizeAdmin.process_file) captures, and
the record was stuck reporting source="manual" even though it came from a
file. These tests exercise the resource directly, matching the pattern used
for field_data's resources (tech debt FD9).
"""

from django.test import TestCase

from analysis.models import GrainSize, RawMeasurement
from analysis.resources import GrainSizeResource
from field_data.models import Sample
from laboratory.models import Device
from prototype.models import Project, Researcher


class GrainSizeResourceImportTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(
            title="GrainSize Resource Project", label="GSR01", status="ACTIVE"
        )
        cls.sample = Sample.objects.create(
            identifier="GSR_SAMPLE01", project=cls.project
        )
        cls.device = Device.objects.create(name="GSR Device")
        cls.researcher = Researcher.objects.create(academic_rank="D")
        cls.raw_measurement = RawMeasurement.objects.create(
            project=cls.project,
            device=cls.device,
            researcher=cls.researcher,
        )
        cls.raw_measurement.sample.add(cls.sample)

    def _import(self, headers, row):
        import tablib

        dataset = tablib.Dataset(headers=headers)
        dataset.append(row)
        result = GrainSizeResource().import_data(dataset, raise_errors=True)
        self.assertFalse(result.has_errors())
        return GrainSize.objects.get(sample=self.sample)

    def test_raw_data_classes_and_measured_data_are_imported(self):
        """tech debt A7: these 3 fields used to be silently dropped on CSV import."""
        gs = self._import(
            [
                "sample",
                "raw_data",
                "method",
                "classes",
                "measured_data",
            ],
            [
                self.sample.identifier,
                self.raw_measurement.pk,
                "L",
                "[1.0, 2.0]",
                "[50.0, 50.0]",
            ],
        )
        self.assertEqual(gs.raw_data, self.raw_measurement)
        self.assertEqual(gs.classes, [1.0, 2.0])
        self.assertEqual(gs.measured_data, [50.0, 50.0])

    def test_source_is_forced_to_file_regardless_of_csv_content(self):
        """tech debt A7: source is system-managed (editable=False) - a CSV
        column can never claim manual entry for a bulk-imported row."""
        gs = self._import(
            ["sample", "method"],
            [self.sample.identifier, "C"],
        )
        self.assertEqual(gs.source, "file")
