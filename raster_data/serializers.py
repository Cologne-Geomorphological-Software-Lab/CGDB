"""DRF serializers for raster_data models."""

from __future__ import annotations

from typing import Any

from django.contrib.gis.geos import GEOSException, GEOSGeometry
from rest_framework import serializers

from .models import DataSource, RasterDataset, RasterScene


class DataSourceSerializer(serializers.ModelSerializer):
    """Serializer for data source / sensor / product descriptions."""

    class Meta:
        """Fields exposed for DataSource."""

        model = DataSource
        fields = [
            "id",
            "name",
            "provider",
            "platform",
            "product_type",
            "typical_resolution_m",
            "temporal_resolution_days",
            "band_descriptions",
            "url",
            "notes",
        ]


class RasterSceneSerializer(serializers.ModelSerializer):
    """Read serializer for georeferenced raster scenes."""

    data_source_name = serializers.CharField(
        source="data_source.name",
        read_only=True,
        default=None,
    )
    spatial_bbox_wkt = serializers.SerializerMethodField()
    effective_path = serializers.CharField(read_only=True)

    class Meta:
        """Fields exposed for RasterScene."""

        model = RasterScene
        fields = [
            "id",
            "project",
            "data_source",
            "data_source_name",
            "effective_path",
            "corpus_path",
            "acquisition_date",
            "n_bands",
            "resolution_m",
            "cloud_cover_pct",
            "crs",
            "spatial_bbox_wkt",
            "n_classes",
            "class_names",
            "notes",
        ]

    def get_spatial_bbox_wkt(self, obj: RasterScene) -> str | None:
        """Return the spatial bbox as WKT, or None if unset."""
        return obj.spatial_bbox.wkt if obj.spatial_bbox else None


class RasterDatasetSerializer(serializers.ModelSerializer):
    """Read serializer for named raster datasets."""

    scene_count = serializers.SerializerMethodField()

    class Meta:
        """Fields exposed for RasterDataset."""

        model = RasterDataset
        fields = [
            "id",
            "project",
            "name",
            "slug",
            "description",
            "scene_count",
            "created_at",
            "modified_at",
        ]

    def get_scene_count(self, obj: RasterDataset) -> int:
        """Return the number of scenes in this dataset."""
        return obj.scenes.count()


class _ManifestSceneSerializer(serializers.ModelSerializer):
    """Scene representation used by the dataset manifest action."""

    data_source_name = serializers.CharField(
        source="data_source.name",
        read_only=True,
        default=None,
    )
    path = serializers.CharField(source="effective_path", read_only=True)
    spatial_bbox_wkt = serializers.SerializerMethodField()

    class Meta:
        """Fields exposed in a manifest entry."""

        model = RasterScene
        fields = [
            "id",
            "path",
            "data_source_name",
            "n_bands",
            "n_classes",
            "class_names",
            "acquisition_date",
            "resolution_m",
            "crs",
            "spatial_bbox_wkt",
        ]

    def get_spatial_bbox_wkt(self, obj: RasterScene) -> str | None:
        """Return the spatial bbox as WKT, or None if unset."""
        return obj.spatial_bbox.wkt if obj.spatial_bbox else None


class RasterSceneWriteSerializer(serializers.ModelSerializer):
    """Write serializer for registering raster scenes via the API."""

    spatial_bbox_wkt = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        write_only=True,
        help_text="WGS-84 bounding box as a WKT POLYGON string.",
    )

    class Meta:
        """Fields accepted when creating a RasterScene."""

        model = RasterScene
        fields = [
            "project",
            "data_source",
            "corpus_path",
            "acquisition_date",
            "n_bands",
            "resolution_m",
            "cloud_cover_pct",
            "crs",
            "spatial_bbox_wkt",
            "n_classes",
            "class_names",
            "notes",
        ]

    def validate_spatial_bbox_wkt(
        self, value: str | None
    ) -> GEOSGeometry | None:
        """Parse and validate the WKT bounding box, if provided."""
        if not value:
            return None
        try:
            geom = GEOSGeometry(value, srid=4326)
        except (GEOSException, ValueError) as exc:
            raise serializers.ValidationError(str(exc)) from exc
        if geom.geom_type != "Polygon":
            msg = "spatial_bbox_wkt must be a POLYGON."
            raise serializers.ValidationError(msg)
        return geom

    def create(self, validated_data: dict[str, Any]) -> RasterScene:
        """Create a RasterScene, converting spatial_bbox_wkt to a geometry."""
        spatial_bbox = validated_data.pop("spatial_bbox_wkt", None)
        instance = RasterScene(**validated_data)
        if spatial_bbox is not None:
            instance.spatial_bbox = spatial_bbox
        instance.save()
        return instance


class RasterDatasetWriteSerializer(serializers.ModelSerializer):
    """Write serializer for creating named raster datasets via the API."""

    scene_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=RasterScene.objects.all(),
        write_only=True,
        required=False,
        source="scenes",
        help_text="List of RasterScene PKs to include in this dataset.",
    )

    class Meta:
        """Fields accepted when creating a RasterDataset."""

        model = RasterDataset
        fields = ["project", "name", "slug", "description", "scene_ids"]

    def create(self, validated_data: dict[str, Any]) -> RasterDataset:
        """Create a RasterDataset and attach any requested scenes."""
        scenes = validated_data.pop("scenes", [])
        dataset = RasterDataset.objects.create(**validated_data)
        if scenes:
            dataset.scenes.set(scenes)
        return dataset
