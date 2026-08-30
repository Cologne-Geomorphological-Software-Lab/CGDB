"""Regression tests for the app's two `fields = "__all__"` serializers.

tech debt A19: LuminescenceDatingSerializer and CosmogenicNuclideDating
Serializer deliberately use fields = "__all__" (see their docstrings) to
avoid transcribing ~50/~45 near-identical numeric columns. That convenience
means any new model field silently becomes API-visible with zero review
gate. Pinning the exact field count here turns a silent expansion into a
visible, deliberate diff when a maintainer adds a field to either model.
"""

from typing import cast

from django.test import SimpleTestCase

from analysis.serializers import (
    CosmogenicNuclideDatingSerializer,
    LuminescenceDatingSerializer,
)


class AllFieldsSerializerCountTest(SimpleTestCase):
    def test_luminescence_dating_field_count(self):
        serializer = cast(
            LuminescenceDatingSerializer, LuminescenceDatingSerializer()
        )
        fields = serializer.fields
        self.assertEqual(
            len(fields),
            59,
            "LuminescenceDatingSerializer's field count changed - a model "
            "field was added/removed. Update this count deliberately "
            f"(current fields: {sorted(fields)}).",
        )

    def test_cosmogenic_nuclide_dating_field_count(self):
        serializer = cast(
            CosmogenicNuclideDatingSerializer,
            CosmogenicNuclideDatingSerializer(),
        )
        fields = serializer.fields
        self.assertEqual(
            len(fields),
            43,
            "CosmogenicNuclideDatingSerializer's field count changed - a "
            "model field was added/removed. Update this count "
            f"deliberately (current fields: {sorted(fields)}).",
        )
