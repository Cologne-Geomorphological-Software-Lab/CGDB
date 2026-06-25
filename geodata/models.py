"""Geodata models for global classification layers.

Three polygon datasets used as map overlays and accessible via the REST API:
- Geomorphon: terrain form classification (Jasiewicz & Stepinski 2013)
- Landform: Murphy Landform Regions of the World
- WorldCover: ESA WorldCover 10m land cover (v100/v200)
"""

from __future__ import annotations

from django.contrib.gis.db import models

from prototype.models import BaseModel

# ------------------------------------------------------------------------------
# Geomorphon
# ------------------------------------------------------------------------------

GEOMORPHON_CLASSES = [
    (1, "Flat"),
    (2, "Peak"),
    (3, "Ridge"),
    (4, "Shoulder"),
    (5, "Spur"),
    (6, "Slope"),
    (7, "Hollow"),
    (8, "Footslope"),
    (9, "Valley"),
    (10, "Pit"),
]


class Geomorphon(BaseModel):
    """Terrain form polygon derived from a DEM via geomorphon analysis.

    Each polygon represents a contiguous area of a single terrain class.
    Optionally scoped to a StudyArea when derived from local DEMs.
    """

    geometry = models.MultiPolygonField(
        srid=4326,
        help_text="Polygon extent of this terrain form class.",
    )
    geomorphon_class = models.IntegerField(
        choices=GEOMORPHON_CLASSES,
        help_text="Terrain form class (1–10) after Jasiewicz & Stepinski (2013).",
    )
    source = models.CharField(
        max_length=255,
        help_text='Source DEM and tool, e.g. "SRTM 30m via GRASS r.geomorphon".',
    )
    study_area = models.ForeignKey(
        "field_data.StudyArea",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="geomorphons",
        help_text="Optional: StudyArea this geomorphon layer was derived for.",
    )
    resolution_m = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Pixel resolution of the source DEM in metres.",
    )

    class Meta:
        """Model metadata."""

        verbose_name = "Geomorphon"
        verbose_name_plural = "Geomorphons"
        ordering = ["geomorphon_class"]

    def __str__(self) -> str:
        """Return string representation."""
        label = dict(GEOMORPHON_CLASSES).get(
            self.geomorphon_class, str(self.geomorphon_class)
        )
        return f"{label} ({self.source})"


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


# ------------------------------------------------------------------------------
# WorldCover
# ------------------------------------------------------------------------------

WORLDCOVER_CLASSES = [
    (10, "Tree cover"),
    (20, "Shrubland"),
    (30, "Grassland"),
    (40, "Cropland"),
    (50, "Built-up"),
    (60, "Bare / sparse vegetation"),
    (70, "Snow and Ice"),
    (80, "Permanent water bodies"),
    (90, "Herbaceous wetland"),
    (95, "Mangroves"),
    (100, "Moss and lichen"),
]


class WorldCover(BaseModel):
    """ESA WorldCover 10m land cover polygon.

    Code 0 (No data) is excluded at import time.
    """

    geometry = models.MultiPolygonField(
        srid=4326,
        help_text="Polygon extent of this land cover class.",
    )
    landcover_class = models.IntegerField(
        choices=WORLDCOVER_CLASSES,
        help_text="ESA WorldCover class code (10–100).",
    )
    year = models.PositiveSmallIntegerField(
        help_text="Product year: 2020 (v100) or 2021 (v200).",
    )
    source = models.CharField(
        max_length=255,
        default="ESA WorldCover v200 2021",
        help_text="Dataset version string.",
    )

    class Meta:
        """Model metadata."""

        verbose_name = "WorldCover"
        verbose_name_plural = "WorldCover"
        ordering = ["landcover_class"]

    def __str__(self) -> str:
        """Return string representation."""
        label = dict(WORLDCOVER_CLASSES).get(
            self.landcover_class, str(self.landcover_class)
        )
        return f"{label} ({self.year})"
