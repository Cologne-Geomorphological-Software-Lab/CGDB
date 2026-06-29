"""Tests for analysis forms."""

from django.test import TestCase

from analysis.forms import GrainSizeForm


class GrainSizeFormTest(TestCase):
    def test_form_instantiates(self):
        form = GrainSizeForm()
        self.assertIsNotNone(form.helper)

    def test_required_fields_present(self):
        form = GrainSizeForm()
        for field in [
            "sample",
            "sample_weight",
            "method",
            "classes",
            "measured_data",
        ]:
            self.assertIn(field, form.fields)
