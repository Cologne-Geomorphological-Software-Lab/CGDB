"""Django admin for geodata models (Landform)."""

from __future__ import annotations

from django.contrib.gis import admin
from unfold.admin import ModelAdmin

from prototype.mixins import (
    AUDIT_READONLY_FIELDS,
    CreatedUpdatedModelAdminMixin,
)

from .models import Landform


class GeoDataModelAdmin(
    CreatedUpdatedModelAdminMixin, ModelAdmin, admin.GISModelAdmin
):
    """Base admin for geodata models: Unfold styling + GIS map widget + audit fields."""

    readonly_fields = AUDIT_READONLY_FIELDS


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
