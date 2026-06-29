"""Geodata models for global classification layers.

One polygon dataset used as a map overlay and accessible via the REST API:
- Landform: Murphy Landform Regions of the World
"""

from __future__ import annotations

from django.contrib.gis.db import models

from prototype.models import BaseModel

# ------------------------------------------------------------------------------
# Landform
# ------------------------------------------------------------------------------


class Landform(BaseModel):
    """Murphy Landform Regions of the World polygon.

    Stores all attributes from the original GeoJSON dataset verbatim.
    Global dataset — not scoped to a StudyArea.
    """

    geometry = models.MultiPolygonField(
        srid=4326,
        help_text="Polygon boundary of this landform region.",
    )
    brid_nam = models.CharField(
        max_length=500,
        blank=True,
        help_text="Full hierarchical name (BridNam), e.g. 'Canadian Archipelago and Greenland Northern Mountains'.",
    )
    name_str = models.CharField(
        max_length=255,
        blank=True,
        help_text="Short region name (NameStr).",
    )
    division = models.CharField(
        max_length=255,
        blank=True,
        help_text="Division within the continent.",
    )
    province = models.CharField(
        max_length=255,
        blank=True,
        help_text="Province within the division.",
    )
    section = models.CharField(
        max_length=255,
        blank=True,
        help_text="Section within the province (often empty).",
    )
    continent = models.CharField(
        max_length=100,
        blank=True,
        help_text="Continent name.",
    )
    murphy_code = models.CharField(
        max_length=10,
        blank=True,
        help_text="Murphy landform code, e.g. 'SPwd'.",
    )
    structure = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Structural geology code.",
    )
    moist_dry = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Moisture regime code.",
    )
    topog = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Topography code.",
    )
    process = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Dominant geomorphological process code.",
    )
    glaciate = models.CharField(
        max_length=100,
        blank=True,
        help_text="Glaciation history, e.g. 'Wisconsin Wurm'.",
    )
    volcanism = models.CharField(
        max_length=255,
        blank=True,
        help_text="Volcanism description.",
    )
    volc_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Volcanic feature name (VolcName).",
    )
    si_vol_num = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Smithsonian Institution volcano number (SI_Vol_Num).",
    )
    vol_reg = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Volcanic region (Vol_Reg).",
    )
    vol_prov = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Volcanic province (Vol_Prov).",
    )
    plate_1 = models.CharField(
        max_length=100, blank=True, help_text="Primary tectonic plate."
    )
    plate_2 = models.CharField(max_length=100, blank=True)
    plate_3 = models.CharField(max_length=100, blank=True)
    plate_4 = models.CharField(max_length=100, blank=True)
    plate_5 = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    area_geo = models.FloatField(
        null=True,
        blank=True,
        help_text="Geographic area from source dataset (AREA_GEO).",
    )
    shape_length = models.FloatField(
        null=True,
        blank=True,
        help_text="Shape length from source dataset (Shape_Length).",
    )
    shape_area = models.FloatField(
        null=True,
        blank=True,
        help_text="Shape area from source dataset (Shape_Area).",
    )
    source = models.CharField(
        max_length=255,
        blank=True,
        help_text='Dataset version, e.g. "Murphy Landform Regions ESRI 2022".',
    )

    class Meta:
        """Model metadata."""

        verbose_name = "Landform"
        verbose_name_plural = "Landforms"
        ordering = ["continent", "division", "province"]

    def __str__(self) -> str:
        """Return string representation."""
        return self.brid_nam or self.name_str or f"Landform {self.pk}"
