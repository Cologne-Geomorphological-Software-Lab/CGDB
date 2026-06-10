"""Tests for GrainSize._reclassify().

These are pure unit tests — no DB access. A GrainSize instance is built
in memory by setting .classes and .measured_data directly.

Boundary thresholds (µm):
  clay        < 2
  fine_silt   2 – < 6.3
  medium_silt 6.3 – < 20
  coarse_silt 20 – < 63
  fine_sand   63 – < 200
  medium_sand 200 – < 630
  coarse_sand 630 – < 2000
  (>= 2000 is not assigned to any fraction)
"""

import json

from django.test import SimpleTestCase

from analysis.models import GrainSize


def _make_grain_size(classes: list, measured_data: list):
    """Return an unsaved GrainSize with the given classes and measured_data."""
    gs = GrainSize.__new__(GrainSize)
    gs.classes = classes
    gs.measured_data = measured_data
    return gs


class ReclassifyClassificationTest(SimpleTestCase):
    """_reclassify() routes each class value to the correct fraction."""

    def test_all_clay(self):
        gs = _make_grain_size([0.5, 1.0, 1.9], [30.0, 40.0, 30.0])
        gs._reclassify()
        self.assertAlmostEqual(gs.clay, 100.0)
        self.assertAlmostEqual(gs.fine_silt, 0.0)
        self.assertAlmostEqual(gs.medium_silt, 0.0)
        self.assertAlmostEqual(gs.coarse_silt, 0.0)
        self.assertAlmostEqual(gs.fine_sand, 0.0)
        self.assertAlmostEqual(gs.medium_sand, 0.0)
        self.assertAlmostEqual(gs.coarse_sand, 0.0)

    def test_all_fine_silt(self):
        gs = _make_grain_size([2.0, 4.0, 6.2], [20.0, 50.0, 30.0])
        gs._reclassify()
        self.assertAlmostEqual(gs.clay, 0.0)
        self.assertAlmostEqual(gs.fine_silt, 100.0)

    def test_all_medium_silt(self):
        gs = _make_grain_size([6.3, 10.0, 19.9], [10.0, 50.0, 40.0])
        gs._reclassify()
        self.assertAlmostEqual(gs.medium_silt, 100.0)

    def test_all_coarse_silt(self):
        gs = _make_grain_size([20.0, 40.0, 62.9], [10.0, 60.0, 30.0])
        gs._reclassify()
        self.assertAlmostEqual(gs.coarse_silt, 100.0)

    def test_all_fine_sand(self):
        gs = _make_grain_size([63.0, 100.0, 199.9], [10.0, 70.0, 20.0])
        gs._reclassify()
        self.assertAlmostEqual(gs.fine_sand, 100.0)

    def test_all_medium_sand(self):
        gs = _make_grain_size([200.0, 400.0, 629.9], [20.0, 50.0, 30.0])
        gs._reclassify()
        self.assertAlmostEqual(gs.medium_sand, 100.0)

    def test_all_coarse_sand(self):
        gs = _make_grain_size([630.0, 1000.0, 1999.9], [30.0, 40.0, 30.0])
        gs._reclassify()
        self.assertAlmostEqual(gs.coarse_sand, 100.0)

    def test_all_fractions_present_equal_weights(self):
        """One representative class per fraction, equal weight → each ~14.29%."""
        classes = [1.0, 4.0, 10.0, 40.0, 100.0, 300.0, 1000.0]
        measured_data = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        gs = _make_grain_size(classes, measured_data)
        gs._reclassify()
        expected = 100.0 / 7.0
        self.assertAlmostEqual(gs.clay, expected, places=5)
        self.assertAlmostEqual(gs.fine_silt, expected, places=5)
        self.assertAlmostEqual(gs.medium_silt, expected, places=5)
        self.assertAlmostEqual(gs.coarse_silt, expected, places=5)
        self.assertAlmostEqual(gs.fine_sand, expected, places=5)
        self.assertAlmostEqual(gs.medium_sand, expected, places=5)
        self.assertAlmostEqual(gs.coarse_sand, expected, places=5)

    def test_boundary_value_exactly_2_is_fine_silt_not_clay(self):
        """class_value == 2.0 fails the < 2 check and lands in fine_silt."""
        gs = _make_grain_size([2.0], [100.0])
        gs._reclassify()
        self.assertAlmostEqual(gs.clay, 0.0)
        self.assertAlmostEqual(gs.fine_silt, 100.0)

    def test_boundary_value_exactly_63_is_fine_sand_not_coarse_silt(self):
        gs = _make_grain_size([63.0], [100.0])
        gs._reclassify()
        self.assertAlmostEqual(gs.coarse_silt, 0.0)
        self.assertAlmostEqual(gs.fine_sand, 100.0)

    def test_values_at_or_above_2000_are_not_classified(self):
        """Classes >= 2000 µm are included in total but not in any fraction."""
        gs = _make_grain_size([1.0, 2000.0], [100.0, 100.0])
        gs._reclassify()
        total_fractions = (
            gs.clay
            + gs.fine_silt
            + gs.medium_silt
            + gs.coarse_silt
            + gs.fine_sand
            + gs.medium_sand
            + gs.coarse_sand
        )
        self.assertAlmostEqual(gs.clay, 50.0)
        self.assertAlmostEqual(total_fractions, 50.0)


class ReclassifyReturnValueTest(SimpleTestCase):
    """_reclassify() return tuple has the documented order."""

    def test_return_tuple_order(self):
        """Return order: (fine_silt, medium_silt, coarse_silt, fine_sand, medium_sand, coarse_sand, clay)."""
        classes = [1.0, 4.0, 10.0, 40.0, 100.0, 300.0, 1000.0]
        measured_data = [7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0]
        gs = _make_grain_size(classes, measured_data)
        result = gs._reclassify()
        total = sum(measured_data)
        self.assertEqual(len(result), 7)
        (
            fine_silt,
            medium_silt,
            coarse_silt,
            fine_sand,
            medium_sand,
            coarse_sand,
            clay,
        ) = result
        self.assertAlmostEqual(clay, 7.0 / total * 100, places=5)
        self.assertAlmostEqual(fine_silt, 6.0 / total * 100, places=5)
        self.assertAlmostEqual(medium_silt, 5.0 / total * 100, places=5)
        self.assertAlmostEqual(coarse_silt, 4.0 / total * 100, places=5)
        self.assertAlmostEqual(fine_sand, 3.0 / total * 100, places=5)
        self.assertAlmostEqual(medium_sand, 2.0 / total * 100, places=5)
        self.assertAlmostEqual(coarse_sand, 1.0 / total * 100, places=5)

    def test_fractions_sum_to_100_when_all_classes_under_2000(self):
        classes = [1.0, 4.0, 10.0, 40.0, 100.0, 300.0, 1000.0]
        measured_data = [10.0, 20.0, 15.0, 25.0, 5.0, 15.0, 10.0]
        gs = _make_grain_size(classes, measured_data)
        gs._reclassify()
        total_fractions = (
            gs.clay
            + gs.fine_silt
            + gs.medium_silt
            + gs.coarse_silt
            + gs.fine_sand
            + gs.medium_sand
            + gs.coarse_sand
        )
        self.assertAlmostEqual(total_fractions, 100.0, places=5)


class ReclassifyInputHandlingTest(SimpleTestCase):
    """_reclassify() handles different input types for measured_data."""

    def test_json_string_is_parsed_before_processing(self):
        gs = _make_grain_size([1.0, 4.0], "[60.0, 40.0]")
        gs._reclassify()
        self.assertAlmostEqual(gs.clay, 60.0)
        self.assertAlmostEqual(gs.fine_silt, 40.0)

    def test_json_string_is_converted_to_list(self):
        gs = _make_grain_size([1.0], "[100.0]")
        gs._reclassify()
        self.assertIsInstance(gs.measured_data, list)

    def test_list_input_passes_through(self):
        gs = _make_grain_size([1.0], [100.0])
        gs._reclassify()
        self.assertAlmostEqual(gs.clay, 100.0)

    def test_dict_input_raises_type_error(self):
        gs = _make_grain_size([1.0], {"a": 1.0})
        with self.assertRaises(TypeError):
            gs._reclassify()

    def test_integer_input_raises_type_error(self):
        gs = _make_grain_size([1.0], 42)
        with self.assertRaises(TypeError):
            gs._reclassify()

    def test_none_input_raises_type_error(self):
        gs = _make_grain_size([1.0], None)
        with self.assertRaises(TypeError):
            gs._reclassify()


class ReclassifyZeroTotalTest(SimpleTestCase):
    """_reclassify() raises ValueError when measured_data sums to zero."""

    def test_all_zeros_raises(self):
        gs = _make_grain_size([1.0, 4.0, 10.0], [0.0, 0.0, 0.0])
        with self.assertRaises(ValueError) as cm:
            gs._reclassify()
        self.assertIn("zero", str(cm.exception).lower())

    def test_single_zero_raises(self):
        gs = _make_grain_size([1.0], [0.0])
        with self.assertRaises(ValueError):
            gs._reclassify()

    def test_nonzero_data_does_not_raise(self):
        gs = _make_grain_size([1.0], [1.0])
        gs._reclassify()  # Must not raise
        self.assertAlmostEqual(gs.clay, 100.0)
