"""DRF serializers for field_data models."""

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import (
    Campaign,
    ExposureType,
    Layer,
    Location,
    Sample,
    SampleType,
    StudyArea,
    Transect,
)


class ExposureTypeSerializer(serializers.ModelSerializer):
    """Serializer for ExposureType lookup values."""

    class Meta:
        """Serializer metadata."""

        model = ExposureType
        fields = ["id", "main_type", "abbreviation", "name_en", "name_ger"]


class SampleTypeSerializer(serializers.ModelSerializer):
    """Serializer for SampleType lookup values."""

    class Meta:
        """Serializer metadata."""

        model = SampleType
        fields = ["id", "word", "label"]


class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for Campaign records."""

    class Meta:
        """Serializer metadata."""

        model = Campaign
        fields = ["id", "label", "project", "date_start", "date_end", "season"]


class StudyAreaGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for StudyArea — geometry is the MultiPolygonField."""

    class Meta:
        """Serializer metadata."""

        model = StudyArea
        geo_field = "geometry"
        fields = [
            "id",
            "label",
            "project",
            "climate_koeppen",
            "ecozone_schultz",
        ]


class TransectSerializer(serializers.ModelSerializer):
    """Serializer for Transect records."""

    class Meta:
        """Serializer metadata."""

        model = Transect
        fields = ["id", "identifier", "study_area", "campaign", "description"]


class LayerSerializer(serializers.ModelSerializer):
    """Serializer for stratigraphic Layer records."""

    class Meta:
        """Serializer metadata."""

        model = Layer
        fields = [
            "id",
            "identifier",
            "location",
            "depth_top",
            "depth_bottom",
        ]


class SampleSerializer(serializers.ModelSerializer):
    """Serializer for Sample records, including computed depth_mid."""

    depth_mid = serializers.ReadOnlyField()

    class Meta:
        """Serializer metadata."""

        model = Sample
        fields = [
            "id",
            "identifier",
            "igsn",
            "project",
            "location",
            "layer",
            "type",
            "date",
            "depth_top",
            "depth_bottom",
            "depth_mid",
            "material",
            "description",
            "created_at",
            "modified_at",
        ]


class LocationGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for Location — geometry is the PointField."""

    class Meta:
        """Serializer metadata."""

        model = Location
        geo_field = "location"
        fields = [
            "id",
            "identifier",
            "data_source",
            "location_type",
            "date_of_record",
            "easting",
            "northing",
            "altitude",
            "gps_accuracy",
            "positioning_method",
            "sampling",
            "liner",
            "gradient_upslope",
            "gradient_downslope",
            "slope_aspect",
            "exposure_type",
            "project",
            "campaign",
            "study_site",
            "transect",
            "created_at",
            "modified_at",
        ]


class LocationFlatSerializer(serializers.ModelSerializer):
    """Flat JSON serializer for Location — longitude/latitude as plain floats."""

    longitude = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()

    def get_longitude(self, obj: Location) -> float | None:
        """Return the WGS-84 longitude of the location point."""
        return obj.location.x if obj.location else None

    def get_latitude(self, obj: Location) -> float | None:
        """Return the WGS-84 latitude of the location point."""
        return obj.location.y if obj.location else None

    class Meta:
        """Serializer metadata."""

        model = Location
        fields = [
            "id",
            "identifier",
            "data_source",
            "location_type",
            "date_of_record",
            "longitude",
            "latitude",
            "altitude",
            "gps_accuracy",
            "positioning_method",
            "sampling",
            "liner",
            "gradient_upslope",
            "gradient_downslope",
            "slope_aspect",
            "exposure_type",
            "project",
            "campaign",
            "study_site",
            "transect",
            "created_at",
            "modified_at",
        ]
