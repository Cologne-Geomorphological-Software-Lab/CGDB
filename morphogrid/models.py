from django.contrib.gis.db import models as geo_models
from django.db import models

from prototype.models import BaseModel


# --- GridCell ---
class GridCell(BaseModel):
    """Represents a single, static cell in the global grid system."""

    grid_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="The unique, human-readable identifier for this grid cell (S2 token).",
    )
    s2_token = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="The S2 cell token (e.g., '1/123456789abcdef').",
    )
    s2_level = models.IntegerField(
        db_index=True,
        help_text="The S2 cell level (0-30). Higher levels mean smaller cells.",
    )
    footprint = geo_models.PolygonField(
        srid=4326,
        help_text="The exact geographic polygon of this grid cell.",
    )

    class Meta:
        ordering = ["grid_id"]
        verbose_name_plural = "Grid Cells"

    def __str__(self):
        return f"Grid Cell ({self.grid_id})"

    def has_datacube(self):
        return hasattr(self, "datacube") and self.datacube is not None


# --- DataCube ---
class DataCube(BaseModel):
    cell = models.OneToOneField(
        "GridCell",
        on_delete=models.CASCADE,
        related_name="datacube",
        help_text="Die Grid-Zelle, zu der dieser DataCube gehört.",
    )

    class Meta:
        ordering = ["cell__grid_id"]
        verbose_name_plural = "Data Cubes"

    def __str__(self):
        return f"DataCube für {self.cell.grid_id}"


class CubeLayer(BaseModel):
    """Single STORED raster layer within a DataCube (primary data only)."""

    PRIMARY_LAYER_TYPES = [
        ("s2_b01", "Sentinel-2 Band 1 (Coastal)"),
        ("s2_b02", "Sentinel-2 Band 2 (Blue)"),
        ("s2_b03", "Sentinel-2 Band 3 (Green)"),
        ("s2_b04", "Sentinel-2 Band 4 (Red)"),
        ("s2_b05", "Sentinel-2 Band 5 (Red Edge 1)"),
        ("s2_b06", "Sentinel-2 Band 6 (Red Edge 2)"),
        ("s2_b07", "Sentinel-2 Band 7 (Red Edge 3)"),
        ("s2_b08", "Sentinel-2 Band 8 (NIR)"),
        ("s2_b8a", "Sentinel-2 Band 8A (Narrow NIR)"),
        ("s2_b09", "Sentinel-2 Band 9 (Water Vapor)"),
        ("s2_b11", "Sentinel-2 Band 11 (SWIR 1)"),
        ("s2_b12", "Sentinel-2 Band 12 (SWIR 2)"),
        ("elevation", "Elevation (SRTM)"),
    ]
    cube = models.ForeignKey(DataCube, on_delete=models.CASCADE, related_name="layers")
    layer_type = models.CharField(max_length=50, choices=PRIMARY_LAYER_TYPES)
    layer_file = models.FileField(upload_to="cubes/%Y/%m/")
    acquisition_date = models.DateField()
    acquisition_group = models.CharField(max_length=100, blank=True)
    resolution_m = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "datacubes_layer"
        unique_together = [["cube", "layer_type", "acquisition_date"]]
        indexes = [
            models.Index(fields=["acquisition_group"]),
            models.Index(fields=["layer_type"]),
        ]

    def __str__(self):
        return f"{self.cube} - {self.get_layer_type_display()} ({self.acquisition_date})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
