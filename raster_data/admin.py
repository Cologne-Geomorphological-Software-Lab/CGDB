"""Django admin for raster_data models."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

if TYPE_CHECKING:
    from django.contrib.admin.options import _FieldsetSpec

from prototype.mixins import (
    AUDIT_READONLY_FIELDS,
    CreatedUpdatedModelAdminMixin,
    ProjectBasedPermissionMixin,
)

from .models import DataSource, RasterDataset, RasterScene


class RasterDataModelAdmin(CreatedUpdatedModelAdminMixin, ModelAdmin):
    """Base admin for raster_data models: Unfold styling + audit fields."""

    readonly_fields = AUDIT_READONLY_FIELDS


@admin.register(DataSource)
class DataSourceAdmin(RasterDataModelAdmin):
    """Admin for data source / sensor / product descriptions."""

    list_display = (
        "name",
        "provider",
        "platform",
        "product_type",
        "typical_resolution_m",
        "temporal_resolution_days",
    )
    list_filter = ("provider", "product_type")
    search_fields = ("name", "provider", "platform", "product_type")
    fieldsets = cast(
        "_FieldsetSpec",
        (
            (
                None,
                {"fields": ["name", "provider", "platform", "product_type"]},
            ),
            (
                "Resolution & Bands",
                {
                    "fields": [
                        "typical_resolution_m",
                        "temporal_resolution_days",
                        "band_descriptions",
                    ]
                },
            ),
            (
                "Reference",
                {"fields": ["url", "notes"]},
            ),
            (
                "Audit",
                {"fields": AUDIT_READONLY_FIELDS, "classes": ["collapse"]},
            ),
        ),
    )


@admin.register(RasterScene)
class RasterSceneAdmin(ProjectBasedPermissionMixin, RasterDataModelAdmin):
    """Admin for georeferenced raster scenes of any kind."""

    list_display = (
        "data_source",
        "acquisition_date",
        "n_bands",
        "resolution_m",
        "n_classes",
        "crs",
        "file_link",
        "project",
    )
    list_filter = ("data_source", "project", "crs")
    search_fields = ("corpus_path", "file", "crs")
    autocomplete_fields = ("data_source",)
    fieldsets = cast(
        "_FieldsetSpec",
        (
            (
                "Identification",
                {"fields": ["project", "data_source", "acquisition_date"]},
            ),
            (
                "File",
                {"fields": ["file", "corpus_path"]},
            ),
            (
                "Technical Metadata",
                {
                    "fields": [
                        "n_bands",
                        "resolution_m",
                        "cloud_cover_pct",
                        "crs",
                    ]
                },
            ),
            (
                "Classification (optional)",
                {
                    "fields": ["n_classes", "class_names"],
                    "classes": ["collapse"],
                },
            ),
            (
                "Spatial",
                {"fields": ["spatial_bbox"]},
            ),
            (
                "Notes",
                {"fields": ["notes"]},
            ),
            (
                "Audit",
                {"fields": AUDIT_READONLY_FIELDS, "classes": ["collapse"]},
            ),
        ),
    )

    @display(description="File")
    def file_link(self, obj: RasterScene) -> str:
        """Return a link to the uploaded file, or the corpus path as fallback."""
        if obj.file:
            return format_html(
                '<a href="{}">{}</a>', obj.file.url, obj.file.name
            )
        return obj.corpus_path or "—"


@admin.register(RasterDataset)
class RasterDatasetAdmin(ProjectBasedPermissionMixin, RasterDataModelAdmin):
    """Admin for named, curated raster datasets."""

    list_display = (
        "name",
        "slug",
        "scene_count",
        "project",
    )
    list_filter = ("project",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("scenes",)
    fieldsets = cast(
        "_FieldsetSpec",
        (
            (
                "Identity",
                {"fields": ["project", "name", "slug", "description"]},
            ),
            (
                "Scenes",
                {"fields": ["scenes"]},
            ),
            (
                "Audit",
                {"fields": AUDIT_READONLY_FIELDS, "classes": ["collapse"]},
            ),
        ),
    )

    @display(description="Scenes")
    def scene_count(self, obj: RasterDataset) -> int:
        """Return the number of scenes in this dataset."""
        return obj.scenes.count()
