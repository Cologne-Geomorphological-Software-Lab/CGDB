"""DRF serializers for analysis models."""

from rest_framework import serializers

from .models import (
    GRAIN_SIZE_INPUT_FIELDS,
    GRAIN_SIZE_STATS_FIELDS,
    Algorithm,
    CosmogenicNuclideDating,
    Counting,
    DistributionError,
    GenericMeasurement,
    GrainSize,
    LuminescenceDating,
    MeasurementSeries,
    MicroXRFElementMap,
    MicroXRFMeasurement,
    Parameter,
    Pollen,
    PollenCount,
    RadiocarbonDating,
    RawMeasurement,
    RawProcessing,
    samples_outside_project,
    validate_distribution,
)


class AlgorithmSerializer(serializers.ModelSerializer):
    """Serializer for Algorithm records."""

    class Meta:
        """Serializer metadata."""

        model = Algorithm
        fields = [
            "id",
            "name",
            "version",
            "description",
            "link",
            "programming_language",
        ]


class RawMeasurementSerializer(serializers.ModelSerializer):
    """Serializer for RawMeasurement records."""

    def validate(self, attrs: dict) -> dict:
        """Every sample must belong to the measurement's project (#244)."""
        project = attrs.get("project", getattr(self.instance, "project", None))
        samples = attrs.get("sample")
        if project is not None and samples:
            foreign = samples_outside_project(samples, project)
            if foreign:
                raise serializers.ValidationError(
                    {
                        "sample": (
                            "These samples do not belong to project "
                            f"{project}: {', '.join(foreign)}."
                        )
                    }
                )
        return attrs

    class Meta:
        """Serializer metadata."""

        model = RawMeasurement
        fields = [
            "id",
            "project",
            "sample",
            "device",
            "accessories",
            "researcher",
            "description",
            "created_at",
            "modified_at",
        ]


class RawProcessingSerializer(serializers.ModelSerializer):
    """Serializer for RawProcessing records."""

    class Meta:
        """Serializer metadata."""

        model = RawProcessing
        fields = [
            "id",
            "raw_measurement",
            "processing_description",
            "processed_by",
            "processing_date",
            "preparation_algorithm",
            "evaluation_algorithm",
            "publication",
            "created_at",
            "modified_at",
        ]


class CountingSerializer(serializers.ModelSerializer):
    """Serializer for Counting records."""

    class Meta:
        """Serializer metadata."""

        model = Counting
        fields = [
            "id",
            "sample",
            "raw_data",
            "type",
            "created_at",
            "modified_at",
        ]


class PollenSerializer(serializers.ModelSerializer):
    """Serializer for Pollen species records."""

    class Meta:
        """Serializer metadata."""

        model = Pollen
        fields = [
            "id",
            "name",
            "token",
            "name_en",
            "name_german",
            "name_nor",
        ]


class PollenCountSerializer(serializers.ModelSerializer):
    """Serializer for PollenCount records."""

    class Meta:
        """Serializer metadata."""

        model = PollenCount
        fields = [
            "id",
            "counting",
            "pollen",
            "number",
            "created_at",
            "modified_at",
        ]


class LuminescenceDatingSerializer(serializers.ModelSerializer):
    """Serializer for LuminescenceDating records.

    fields = "__all__" is a deliberate exception to this app's usual explicit
    field lists: this model has ~50 near-identical numeric dose/error columns
    (see analysis/models.py), and transcribing them would be pure
    copy-transcription risk with no access-control benefit (read-only viewset).
    """

    class Meta:
        """Serializer metadata."""

        model = LuminescenceDating
        fields = "__all__"


class RadiocarbonDatingSerializer(serializers.ModelSerializer):
    """Serializer for RadiocarbonDating records."""

    class Meta:
        """Serializer metadata."""

        model = RadiocarbonDating
        fields = [
            "id",
            "sample",
            "raw_data",
            "lab",
            "lab_id",
            "age",
            "age_error",
            "data_quality",
            "quality_note",
            "created_at",
            "modified_at",
        ]


class CosmogenicNuclideDatingSerializer(serializers.ModelSerializer):
    """Serializer for CosmogenicNuclideDating records.

    fields = "__all__": same rationale as LuminescenceDatingSerializer above
    — this model has ~45 numeric fields covering concentration, age,
    denudation, production rate, shielding, and error-budget columns.
    """

    class Meta:
        """Serializer metadata."""

        model = CosmogenicNuclideDating
        fields = "__all__"


class ParameterSerializer(serializers.ModelSerializer):
    """Serializer for Parameter records."""

    class Meta:
        """Serializer metadata."""

        model = Parameter
        fields = [
            "id",
            "name",
            "token",
            "unit",
            "minimal_limit",
            "maximal_limit",
            "classes",
        ]


class MeasurementSeriesSerializer(serializers.ModelSerializer):
    """Serializer for MeasurementSeries records."""

    class Meta:
        """Serializer metadata."""

        model = MeasurementSeries
        fields = ["id", "datetime"]


class GenericMeasurementSerializer(serializers.ModelSerializer):
    """Serializer for GenericMeasurement records."""

    class Meta:
        """Serializer metadata."""

        model = GenericMeasurement
        fields = [
            "id",
            "sample",
            "raw_data",
            "measurement_series",
            "sample_weight",
            "method",
            "parameter",
            "value",
            "error",
            "created_at",
            "modified_at",
        ]


class GrainSizeSerializer(serializers.ModelSerializer):
    """Serializer for GrainSize records."""

    def validate(self, attrs: dict) -> dict:
        """Check the distribution lists like the admin form does (#282)."""
        classes = attrs.get("classes", getattr(self.instance, "classes", None))
        measured = attrs.get(
            "measured_data", getattr(self.instance, "measured_data", None)
        )
        if classes is not None and measured is not None:
            try:
                validate_distribution(classes, measured)
            except DistributionError as exc:
                raise serializers.ValidationError(
                    {exc.field: str(exc)}
                ) from exc
        return attrs

    class Meta:
        """Serializer metadata."""

        model = GrainSize
        fields = [
            "id",
            *GRAIN_SIZE_INPUT_FIELDS,
            "source",
            *GRAIN_SIZE_STATS_FIELDS,
            "created_at",
            "modified_at",
        ]


class MicroXRFMeasurementSerializer(serializers.ModelSerializer):
    """Serializer for MicroXRFMeasurement records."""

    class Meta:
        """Serializer metadata."""

        model = MicroXRFMeasurement
        fields = [
            "id",
            "sample",
            "measurement_date",
            "method",
            "notes",
            "created_at",
            "modified_at",
        ]


class MicroXRFElementMapSerializer(serializers.ModelSerializer):
    """Serializer for MicroXRFElementMap records."""

    class Meta:
        """Serializer metadata."""

        model = MicroXRFElementMap
        fields = [
            "id",
            "measurement",
            "element",
            "raster_file",
            "unit",
            "created_at",
            "modified_at",
        ]
