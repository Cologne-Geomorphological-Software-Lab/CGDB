"""Unit tests for field_data.utils — no DB required."""

from urllib.parse import urlencode

from django.http import QueryDict
from django.test import SimpleTestCase

from field_data.utils import extract_sample_pk_from_get


def _q(query_string: str) -> QueryDict:
    return QueryDict(query_string)


class ExtractSamplePkTest(SimpleTestCase):

    # --- direct ?sample= ---

    def test_sample_param_returns_value(self):
        self.assertEqual(extract_sample_pk_from_get(_q("sample=42")), "42")

    def test_sample_param_non_digit_returns_none(self):
        self.assertIsNone(extract_sample_pk_from_get(_q("sample=abc")))

    def test_sample_param_empty_returns_none(self):
        self.assertIsNone(extract_sample_pk_from_get(_q("sample=")))

    # --- ?sample__id__exact= ---

    def test_sample_id_exact_returns_value(self):
        self.assertEqual(
            extract_sample_pk_from_get(_q("sample__id__exact=7")), "7"
        )

    def test_sample_id_exact_non_digit_returns_none(self):
        self.assertIsNone(
            extract_sample_pk_from_get(_q("sample__id__exact=xyz"))
        )

    # --- priority: ?sample= wins over ?sample__id__exact= ---

    def test_sample_takes_priority_over_id_exact(self):
        self.assertEqual(
            extract_sample_pk_from_get(_q("sample=3&sample__id__exact=7")), "3"
        )

    # --- ?_changelist_filters=sample__id__exact%3D… ---

    def test_changelist_filters_encoded(self):
        qs = urlencode({"_changelist_filters": "sample__id__exact=9"})
        self.assertEqual(extract_sample_pk_from_get(_q(qs)), "9")

    def test_changelist_filters_non_digit_returns_none(self):
        qs = urlencode({"_changelist_filters": "sample__id__exact=bad"})
        self.assertIsNone(extract_sample_pk_from_get(_q(qs)))

    def test_changelist_filters_missing_key_returns_none(self):
        qs = urlencode({"_changelist_filters": "other_param=5"})
        self.assertIsNone(extract_sample_pk_from_get(_q(qs)))

    # --- no relevant params ---

    def test_empty_returns_none(self):
        self.assertIsNone(extract_sample_pk_from_get(_q("")))

    def test_unrelated_params_returns_none(self):
        self.assertIsNone(extract_sample_pk_from_get(_q("foo=bar&page=2")))
