"""Django admin for geodata models (Geomorphon, Landform, WorldCover)."""

from __future__ import annotations

from django.contrib.gis import admin
from unfold.admin import ModelAdmin

from prototype.mixins import CreatedUpdatedModelAdminMixin

from .models import Geomorphon, Landform, WorldCover


class GeoDataModelAdmin(
    CreatedUpdatedModelAdminMixin, ModelAdmin, admin.GISModelAdmin
):
    """Base admin for geodata models: Unfold styling + GIS map widget + audit fields."""

    readonly_fields = ("created_at", "modified_at", "created_by", "updated_by")


@admin.register(Geomorphon)
class GeomorphonAdmin(GeoDataModelAdmin):
    """Admin for Geomorphon terrain form polygons."""

    list_display = (
        "geomorphon_class",
        "source",
        "resolution_m",
        "study_area",
        "created_at",
    )
    list_filter = ("geomorphon_class", "study_area")
    search_fields = ("source",)
    autocomplete_fields = ("study_area",)


@admin.register(Landform)
class LandformAdmin(GeoDataModelAdmin):
    """Admin for Murphy Landform region polygons."""

    list_display = (
        "name_str",
        "murphy_code",
        "division",
        "continent",
        "created_at",
    )
    list_filter = ("continent",)
    search_fields = (
        "name_str",
        "brid_nam",
        "murphy_code",
        "division",
        "province",
    )
    fieldsets = (
        (
            None,
            {
                "fields": ("geometry", "source"),
            },
        ),
        (
            "Classification",
            {
                "fields": (
                    "murphy_code",
                    "brid_nam",
                    "name_str",
                    "division",
                    "province",
                    "section",
                    "continent",
                ),
            },
        ),
        (
            "Codes",
            {
                "fields": (
                    "structure",
                    "moist_dry",
                    "topog",
                    "process",
                    "glaciate",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Volcanism",
            {
                "fields": (
                    "volcanism",
                    "volc_name",
                    "si_vol_num",
                    "vol_reg",
                    "vol_prov",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Tectonics",
            {
                "fields": (
                    "plate_1",
                    "plate_2",
                    "plate_3",
                    "plate_4",
                    "plate_5",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Geometry metrics",
            {
                "fields": ("area_geo", "shape_length", "shape_area", "notes"),
                "classes": ("collapse",),
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "modified_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(WorldCover)
class WorldCoverAdmin(GeoDataModelAdmin):
    """Admin for ESA WorldCover land cover polygons."""

    list_display = ("landcover_class", "year", "source", "created_at")
    list_filter = ("landcover_class", "year")
    search_fields = ("source",)
