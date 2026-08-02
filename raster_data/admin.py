"""Django admin for raster_data models."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from django.contrib import admin, messages
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

if TYPE_CHECKING:
    from django.contrib.admin.options import _FieldsetSpec
    from django.db.models import QuerySet
    from django.http import HttpRequest

from prototype.mixins import (
    AUDIT_READONLY_FIELDS,
    CreatedUpdatedModelAdminMixin,
    ProjectBasedPermissionMixin,
)

from .gdal_metadata import RasterMetadataError, read_raster_metadata
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

    actions = ["recompute_metadata_from_file"]
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

    def _local_path_for(
        self, request: HttpRequest, scene: RasterScene
    ) -> str | None:
        """Return a locally readable path for scene's file, or None (with a message)."""
        if scene.file:
            try:
                return scene.file.path
            except NotImplementedError:
                self.message_user(
                    request,
                    f"{scene}: file storage backend has no local path — skipped.",
                    messages.WARNING,
                )
                return None
        if scene.corpus_path:
            if not Path(scene.corpus_path).exists():
                self.message_user(
                    request,
                    f"{scene}: corpus_path {scene.corpus_path!r} is not "
                    "reachable from this server — skipped.",
                    messages.WARNING,
                )
                return None
            return scene.corpus_path
        self.message_user(
            request,
            f"{scene}: no file or corpus_path set — skipped.",
            messages.WARNING,
        )
        return None

    @admin.action(description="Recompute metadata from file")
    def recompute_metadata_from_file(
        self, request: HttpRequest, queryset: QuerySet[RasterScene]
    ) -> None:
        """Overwrite crs/spatial_bbox/n_bands with values read from each file via GDAL.

        Reports per-record success/failure through the admin messages
        framework rather than failing the whole batch on one bad file —
        selections routinely mix uploaded files, external corpus_path
        records, and the occasional corrupt or non-raster file.
        """
        total = queryset.count()
        success_count = 0
        for scene in queryset:
            path = self._local_path_for(request, scene)
            if path is None:
                continue

            try:
                metadata = read_raster_metadata(path)
            except RasterMetadataError as exc:
                self.message_user(request, f"{scene}: {exc}", messages.ERROR)
                continue

            scene.crs = metadata.crs
            scene.spatial_bbox = metadata.spatial_bbox
            scene.n_bands = metadata.n_bands
            scene.save()
            success_count += 1

        if success_count:
            self.message_user(
                request,
                f"Recomputed metadata for {success_count} of {total} scene(s).",
                messages.SUCCESS,
            )


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
