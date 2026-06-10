"""Tests for GrainSize.from_file() – the .$av file parser.

Happy-path, error-handling and integration tests.
Temporary files are created with tempfile and cleaned up via addCleanup.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from django.test import SimpleTestCase, TestCase

from analysis.models import GrainSize
from field_data.models import Location, Sample
from prototype.models import Project


def _make_sample():
    """Return an unsaved Sample instance usable as a FK target in memory."""
    return Sample(identifier="TEMP", project=None)


# ---------------------------------------------------------------------------
# Helper: write a temporary .$av-style file
# ---------------------------------------------------------------------------


def _make_av_file(content: str) -> Path:
    """Write content to a temporary file and return its Path."""
    fd, path = tempfile.mkstemp(suffix=".av")
    with os.fdopen(fd, "w", encoding="latin-1") as f:
        f.write(content)
    return Path(path)


MINIMAL_AV = """\
[#Bindiam]
10.0
20.0
[#Binheight]
50.0
50.0
[Size0]
Obs=150.5
[SizeStats]
Mean=15.0
Mode=12.0
Median=14.0
SD=3.5
Skew=0.2
Kurtosis=2.8
FWMean=15.1
FWMedian=14.2
FWSD=3.6
FWSkew=0.3
FWKurt=2.9
"""


# ===========================================================================
# Happy-path tests – no DB needed
# ===========================================================================


class GrainSizeFromFileHappyPathTest(SimpleTestCase):

    def setUp(self):
        self.path = _make_av_file(MINIMAL_AV)
        self.addCleanup(os.unlink, self.path)
        self.sample = _make_sample()
        self.method = "L"

    def _parse(self, content: str | None = None):
        if content is not None:
            path = _make_av_file(content)
            self.addCleanup(os.unlink, path)
        else:
            path = self.path
        return GrainSize.from_file(path, self.sample, self.method)

    def test_classes_parsed_correctly(self):
        gs = self._parse()
        self.assertEqual(gs.classes, [10.0, 20.0])

    def test_measured_data_parsed_correctly(self):
        gs = self._parse()
        self.assertEqual(gs.measured_data, [50.0, 50.0])

    def test_concentration_single_obs(self):
        gs = self._parse()
        self.assertAlmostEqual(gs.sample_concentration, 150.5)

    def test_concentration_mean_of_multiple_obs(self):
        content = (
            "[#Bindiam]\n10.0\n[#Binheight]\n100.0\n"
            "[Size0]\nObs=100.0\n[Size1]\nObs=200.0\n"
        )
        gs = self._parse(content)
        self.assertAlmostEqual(gs.sample_concentration, 150.0)

    def test_stats_mean_parsed(self):
        gs = self._parse()
        self.assertAlmostEqual(gs.mean, 15.0)

    def test_stats_mode_parsed(self):
        gs = self._parse()
        self.assertAlmostEqual(gs.mode, 12.0)

    def test_stats_median_parsed(self):
        gs = self._parse()
        self.assertAlmostEqual(gs.median, 14.0)

    def test_stats_sd_parsed(self):
        gs = self._parse()
        self.assertAlmostEqual(gs.std, 3.5)

    def test_stats_skew_parsed(self):
        gs = self._parse()
        self.assertAlmostEqual(gs.skew, 0.2)

    def test_stats_kurtosis_parsed(self):
        gs = self._parse()
        self.assertAlmostEqual(gs.kurtosis, 2.8)

    def test_stats_fwmean_parsed(self):
        gs = self._parse()
        self.assertAlmostEqual(gs.fwmean, 15.1)

    def test_stats_fwmedian_parsed(self):
        gs = self._parse()
        self.assertAlmostEqual(gs.fwmedian, 14.2)

    def test_stats_fwsd_parsed(self):
        gs = self._parse()
        self.assertAlmostEqual(gs.fwsd, 3.6)

    def test_stats_fwskew_parsed(self):
        gs = self._parse()
        self.assertAlmostEqual(gs.fwskew, 0.3)

    def test_stats_fwkurt_parsed(self):
        gs = self._parse()
        self.assertAlmostEqual(gs.fwkurt, 2.9)

    def test_returns_grainsize_instance(self):
        gs = self._parse()
        self.assertIsInstance(gs, GrainSize)

    def test_sample_and_method_assigned(self):
        gs = self._parse()
        self.assertIs(gs.sample, self.sample)
        self.assertEqual(gs.method, self.method)

    def test_unknown_block_is_ignored(self):
        content = MINIMAL_AV + "[UNKNOWN_BLOCK]\nsome_garbage_data\n"
        gs = self._parse(content)
        # Must not raise; known fields still parsed correctly
        self.assertEqual(gs.classes, [10.0, 20.0])


# ===========================================================================
# Error-handling tests
# ===========================================================================


class GrainSizeFromFileErrorHandlingTest(SimpleTestCase):

    def _parse(self, content: str):
        path = _make_av_file(content)
        self.addCleanup(os.unlink, path)
        return GrainSize.from_file(path, _make_sample(), "L")

    def test_missing_size_block_raises_value_error(self):
        content = (
            "[#Bindiam]\n10.0\n[#Binheight]\n50.0\n[SizeStats]\nMean=5.0\n"
        )
        with self.assertRaises(ValueError) as cm:
            self._parse(content)
        self.assertIn("concentration", str(cm.exception).lower())

    def test_size_block_without_obs_raises_value_error(self):
        content = (
            "[#Bindiam]\n10.0\n[#Binheight]\n50.0\n[Size0]\nSomething=42\n"
        )
        with self.assertRaises(ValueError):
            self._parse(content)

    def test_invalid_float_in_bindiam_is_skipped(self):
        content = "[#Bindiam]\n10.0\nNaN_value\n20.0\n[#Binheight]\n50.0\n50.0\n[Size0]\nObs=100\n"
        gs = self._parse(content)
        self.assertEqual(gs.classes, [10.0, 20.0])

    def test_invalid_float_in_binheight_is_skipped(self):
        content = "[#Bindiam]\n10.0\n20.0\n[#Binheight]\n50.0\ninvalid\n50.0\n[Size0]\nObs=100\n"
        gs = self._parse(content)
        self.assertEqual(gs.measured_data, [50.0, 50.0])

    def test_invalid_float_in_sizestats_is_skipped(self):
        content = (
            "[#Bindiam]\n10.0\n[#Binheight]\n50.0\n"
            "[Size0]\nObs=100\n"
            "[SizeStats]\nMean=not_a_float\n"
        )
        gs = self._parse(content)
        self.assertIsNone(gs.mean)

    def test_missing_stats_fields_remain_none(self):
        content = "[#Bindiam]\n10.0\n[#Binheight]\n50.0\n[Size0]\nObs=100\n"
        gs = self._parse(content)
        for attr in (
            "mean",
            "mode",
            "median",
            "std",
            "skew",
            "kurtosis",
            "fwmean",
            "fwmedian",
            "fwsd",
            "fwskew",
            "fwkurt",
        ):
            self.assertIsNone(getattr(gs, attr), msg=f"{attr} should be None")

    def test_latin1_encoding_does_not_raise(self):
        # Write bytes that are valid latin-1 but not UTF-8
        fd, path = tempfile.mkstemp(suffix=".av")
        self.addCleanup(os.unlink, path)
        with os.fdopen(fd, "wb") as f:
            f.write(
                b"[#Bindiam]\n10.0\n[#Binheight]\n50.0\n[Size0]\nObs=100\n"
                b"# Ger\xe4t: Mastersizer\n"  # "Gerät" in latin-1
            )
        gs = GrainSize.from_file(Path(path), _make_sample(), "L")
        self.assertEqual(gs.classes, [10.0])


# ===========================================================================
# Integration test – requires DB
# ===========================================================================


class GrainSizeFromFileIntegrationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(
            title="GS From File Project", label="GSFF01", status="ACTIVE"
        )
        cls.location = Location.objects.create(
            identifier="GSFF_LOC",
            data_source="internal",
            project=cls.project,
        )
        cls.sample = Sample.objects.create(
            identifier="GSFF_S01",
            project=cls.project,
            location=cls.location,
        )

    def test_from_file_returns_unsaved_instance(self):
        path = _make_av_file(MINIMAL_AV)
        self.addCleanup(os.unlink, path)
        gs = GrainSize.from_file(path, self.sample, "L")
        self.assertIsNone(gs.pk)

    def test_from_file_can_be_saved(self):
        path = _make_av_file(MINIMAL_AV)
        self.addCleanup(os.unlink, path)
        gs = GrainSize.from_file(path, self.sample, "L")
        gs.save()
        self.assertTrue(GrainSize.objects.filter(sample=self.sample).exists())

    def test_save_triggers_reclassify(self):
        # classes: one clay (<2µm) and one fine_sand (63-200µm) value
        content = (
            "[#Bindiam]\n1.0\n100.0\n"
            "[#Binheight]\n40.0\n60.0\n"
            "[Size0]\nObs=10\n"
        )
        path = _make_av_file(content)
        self.addCleanup(os.unlink, path)
        gs = GrainSize.from_file(path, self.sample, "L")
        gs.save()
        saved = GrainSize.objects.get(pk=gs.pk)
        self.assertAlmostEqual(saved.clay, 40.0)
        self.assertAlmostEqual(saved.fine_sand, 60.0)
