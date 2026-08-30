"""DRF serializers for field_data models."""

from typing import Any

from django.contrib.gis.geos import GEOSGeometry
from django.urls import reverse
from rest_framework import serializers
from rest_framework_gis.fields import GeometryField
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


def _validate_geom_type(value: GEOSGeometry, expected: str) -> None:
    """Raise ValidationError unless *value* is geometrically valid and of *expected* type.

    rest_framework_gis's GeometryField accepts any GeoJSON geometry type —
    this narrows it to what the target model field actually stores, and
    rejects self-intersecting/otherwise-invalid geometry before it ever
    reaches the database.
    """
    if value.geom_type != expected:
        msg = f"Expected a {expected}, got {value.geom_type}."
        raise serializers.ValidationError(msg)
    if not value.valid:
        raise serializers.ValidationError(value.valid_reason)


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
            "province",
            "climate_koeppen",
            "ecozone_schultz",
        ]


class StudyAreaMapSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for the map dashboard's StudyArea overlay.

    Property keys match those the map dashboard's popup JS reads:
    project, climate_koeppen_display, ecozone_schultz_display, admin_url.
    """

    project = serializers.StringRelatedField()
    climate_koeppen_display = serializers.SerializerMethodField()
    ecozone_schultz_display = serializers.SerializerMethodField()
    admin_url = serializers.SerializerMethodField()

    class Meta:
        """Serializer metadata."""

        model = StudyArea
        geo_field = "geometry"
        fields = [
            "id",
            "label",
            "project",
            "climate_koeppen",
            "climate_koeppen_display",
            "ecozone_schultz",
            "ecozone_schultz_display",
            "admin_url",
        ]

    def get_climate_koeppen_display(self, obj: StudyArea) -> str:
        """Return the human-readable Köppen climate label."""
        return obj.get_climate_koeppen_display()  # pyright: ignore[reportAttributeAccessIssue]  # Django-generated choices-field accessor; no mypy-plugin support in basedpyright

    def get_ecozone_schultz_display(self, obj: StudyArea) -> str:
        """Return the human-readable Schultz ecozone label."""
        return obj.get_ecozone_schultz_display()  # pyright: ignore[reportAttributeAccessIssue]  # Django-generated choices-field accessor; no mypy-plugin support in basedpyright

    def get_admin_url(self, obj: StudyArea) -> str:
        """Return the admin change-form URL for this study area."""
        return reverse("admin:field_data_studyarea_change", args=[obj.pk])


class StudyAreaWriteSerializer(serializers.ModelSerializer):
    """Create/update serializer for StudyArea — accepts GeoJSON geometry.

    Unlike raster_data's WriteSerializer convention (a hand-typed WKT
    string, since a human fills that in), this accepts a GeoJSON geometry
    object directly, matching what OpenLayers' GeoJSON.writeGeometryObject()
    produces on the map dashboard's edit round-trip.
    """

    geometry = GeometryField()

    class Meta:
        """Serializer metadata."""

        model = StudyArea
        fields = [
            "id",
            "label",
            "project",
            "province",
            "climate_koeppen",
            "ecozone_schultz",
            "geometry",
        ]

    def validate_geometry(self, value: GEOSGeometry) -> GEOSGeometry:
        """Reject anything that isn't a valid Polygon."""
        _validate_geom_type(value, "Polygon")
        return value


class TransectSerializer(serializers.ModelSerializer):
    """Serializer for Transect records."""

    class Meta:
        """Serializer metadata."""

        model = Transect
        fields = ["id", "identifier", "study_area", "campaign", "description"]


class TransectMapSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for the map dashboard's Transect overlay.

    Transect's plain TransectSerializer above has no geometry field —
    this one carries the multiline geometry plus the map popup's property keys.
    """

    study_area = serializers.StringRelatedField()
    campaign = serializers.SerializerMethodField()
    admin_url = serializers.SerializerMethodField()

    class Meta:
        """Serializer metadata."""

        model = Transect
        geo_field = "multiline"
        fields = ["id", "identifier", "study_area", "campaign", "admin_url"]

    def get_campaign(self, obj: Transect) -> str | None:
        """Return the campaign label, or None if unset."""
        return obj.campaign.label if obj.campaign else None

    def get_admin_url(self, obj: Transect) -> str:
        """Return the admin change-form URL for this transect."""
        return reverse("admin:field_data_transect_change", args=[obj.pk])


class TransectWriteSerializer(serializers.ModelSerializer):
    """Create/update serializer for Transect — accepts GeoJSON geometry."""

    multiline = GeometryField()

    class Meta:
        """Serializer metadata."""

        model = Transect
        fields = [
            "id",
            "identifier",
            "study_area",
            "campaign",
            "description",
            "multiline",
        ]

    def validate_multiline(self, value: GEOSGeometry) -> GEOSGeometry:
        """Reject anything that isn't a valid MultiLineString."""
        _validate_geom_type(value, "MultiLineString")
        return value


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


class LocationMapSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for the map dashboard's Location overlay.

    Property keys match those the map dashboard's popup JS reads:
    project, location_type_display, campaign, exposure_type, sample_count,
    luminescence_count, grain_size_count, admin_url. The count fields are
    expected to be annotated onto the queryset by the caller (see
    LocationViewSet.map).
    """

    project = serializers.StringRelatedField()
    campaign = serializers.SerializerMethodField()
    exposure_type = serializers.SerializerMethodField()
    location_type_display = serializers.SerializerMethodField()
    sample_count = serializers.IntegerField(read_only=True)
    luminescence_count = serializers.IntegerField(read_only=True)
    grain_size_count = serializers.IntegerField(read_only=True)
    admin_url = serializers.SerializerMethodField()

    class Meta:
        """Serializer metadata."""

        model = Location
        geo_field = "location"
        fields = [
            "id",
            "identifier",
            "project",
            "data_source",
            "location_type",
            "location_type_display",
            "campaign",
            "date_of_record",
            "altitude",
            "exposure_type",
            "sample_count",
            "luminescence_count",
            "grain_size_count",
            "admin_url",
        ]

    def get_campaign(self, obj: Location) -> str | None:
        """Return the campaign label, or None if unset."""
        return obj.campaign.label if obj.campaign else None

    def get_exposure_type(self, obj: Location) -> str | None:
        """Return the exposure type's English name, or None if unset."""
        return obj.exposure_type.name_en if obj.exposure_type else None

    def get_location_type_display(self, obj: Location) -> str:
        """Return the human-readable location type label."""
        return obj.get_location_type_display()  # pyright: ignore[reportAttributeAccessIssue]  # Django-generated choices-field accessor; no mypy-plugin support in basedpyright

    def get_admin_url(self, obj: Location) -> str:
        """Return the admin change-form URL for this location."""
        return reverse("admin:field_data_location_change", args=[obj.pk])


class LocationWriteSerializer(serializers.ModelSerializer):
    """Update-only serializer for Location — reshapes an existing marker.

    Location.save() always recomputes `location` from `easting`/`northing`/
    `srid` (field_data/models.py), so writing straight to `location` would
    get silently discarded on the next save from any other caller (import
    scripts, the admin form). Instead, .update() back-converts the incoming
    GeoJSON point into easting/northing in the record's own srid, keeping
    "coordinates are the source of truth" intact end to end.
    """

    location = GeometryField()

    class Meta:
        """Serializer metadata."""

        model = Location
        fields = ["id", "location"]

    def validate_location(self, value: GEOSGeometry) -> GEOSGeometry:
        """Reject anything that isn't a valid Point."""
        _validate_geom_type(value, "Point")
        return value

    def update(
        self, instance: Location, validated_data: dict[str, Any]
    ) -> Location:
        """Back-convert the new point into easting/northing, then save()."""
        point = validated_data["location"]
        if point.srid != instance.srid:
            point.transform(instance.srid)
        instance.easting = point.x
        instance.northing = point.y
        instance.save()  # recomputes .location from easting/northing, runs clean()
        return instance
