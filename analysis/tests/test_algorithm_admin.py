"""Tests for AlgorithmForm's upload validation (tech debt A21).

Algorithm.file accepts an arbitrary uploaded script/executable and
previously had no size or extension validation - a weaker guard than
GrainSizeImportForm.clean_file's, despite being the more sensitive upload.
These tests exercise AlgorithmForm directly (unit-level, matching the
pattern of GrainSizeImportForm not having its own dedicated admin-POST
test) rather than through the admin's HTTP layer.
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.utils.datastructures import MultiValueDict

from analysis.admin import AlgorithmForm


def _make_form(filename: str, size: int, language: str = "Python"):
    upload = SimpleUploadedFile(filename, b"x" * size)
    return AlgorithmForm(
        data={"name": "Algo", "version": "1.0", "programming_language": language},
        files=MultiValueDict({"file": [upload]}),
    )


class AlgorithmFormExtensionTest(SimpleTestCase):
    def test_matching_extension_is_valid(self):
        form = _make_form("script.py", 100, "Python")
        self.assertTrue(form.is_valid(), form.errors)

    def test_mismatched_extension_is_rejected(self):
        form = _make_form("script.exe", 100, "Python")
        self.assertFalse(form.is_valid())
        self.assertIn("does not match", str(form.errors))

    def test_r_extension_is_valid_for_r_language(self):
        form = _make_form("script.r", 100, "R")
        self.assertTrue(form.is_valid(), form.errors)

    def test_matlab_extension_is_valid_for_matlab_language(self):
        form = _make_form("script.m", 100, "MATLAB")
        self.assertTrue(form.is_valid(), form.errors)

    def test_julia_extension_is_valid_for_julia_language(self):
        form = _make_form("script.jl", 100, "Julia")
        self.assertTrue(form.is_valid(), form.errors)

    def test_other_language_skips_extension_check(self):
        """"Other" has no single matching extension, so anything is allowed."""
        form = _make_form("script.whatever", 100, "Other")
        self.assertTrue(form.is_valid(), form.errors)


class AlgorithmFormSizeTest(SimpleTestCase):
    def test_file_within_size_cap_is_valid(self):
        form = _make_form("script.py", 1024, "Python")
        self.assertTrue(form.is_valid(), form.errors)

    def test_file_over_size_cap_is_rejected(self):
        form = _make_form("script.py", 11 * 1024 * 1024, "Python")
        self.assertFalse(form.is_valid())
        self.assertIn("exceeds maximum allowed size", str(form.errors))

    def test_missing_file_is_valid(self):
        """file is optional (blank=True, null=True) - validation only runs when present."""
        form = AlgorithmForm(
            data={
                "name": "Algo",
                "version": "1.0",
                "programming_language": "Python",
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
