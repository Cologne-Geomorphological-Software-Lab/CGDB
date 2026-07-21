"""Models for raster data management: data sources, scenes, and datasets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.gis.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

from prototype.models import BaseModel

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager


class DataSource(BaseModel):
    """Describes the origin, sensor, or product of a raster dataset.

    Examples: "Sentinel-2 L2A", "Copernicus DEM 30m", "Landsat 9 OLI".
    """

    name = models.CharField(max_length=200, unique=True)
    provider = models.CharField(max_length=200, blank=True)
    platform = models.CharField(max_length=200, blank=True)
    product_type = models.CharField(max_length=200, blank=True)
    typical_resolution_m = models.FloatField(null=True, blank=True)
    temporal_resolution_days = models.FloatField(
        null=True,
        blank=True,
        help_text="Revisit interval in days. Null for static products (e.g. DEM).",
    )
    band_descriptions = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Ordered list of band descriptions, "
            'e.g. ["Blue (490 nm)", "Green (560 nm)"].'
        ),
    )
    url = models.URLField(
        blank=True, help_text="Link to product documentation."
    )
    notes = models.TextField(blank=True)

    class Meta:
        """Model metadata."""

        verbose_name = "Data Source"
        verbose_name_plural = "Data Sources"
        ordering = ["name"]

    def __str__(self) -> str:
        """Return the data source name."""
        return self.name


class RasterScene(BaseModel):
    """A georeferenced raster TIFF — spectral, elevation, classification, or any raster.

    Classification rasters (formerly called label rasters) are represented here too:
    populate n_classes and class_names to describe their thematic content.
    """

    if TYPE_CHECKING:
        datasets: RelatedManager[RasterDataset]

    project = models.ForeignKey(
        "prototype.Project",
        on_delete=models.CASCADE,
        related_name="raster_scenes",
    )
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="raster_scenes",
    )
    file = models.FileField(
        upload_to="raster_data/scenes/",
        blank=True,
        help_text=(
            "Blob stored in Django media. "
            "Leave blank if the file lives on an external filesystem."
        ),
    )
    corpus_path = models.CharField(
        max_length=1000,
        blank=True,
        help_text="Path for manifest export. Takes precedence over file.name when set.",
    )
    acquisition_date = models.DateField(null=True, blank=True)
    n_bands = models.PositiveSmallIntegerField(null=True, blank=True)
    resolution_m = models.FloatField(
        null=True,
        blank=True,
        help_text="Actual ground sampling distance of this file in metres.",
    )
    cloud_cover_pct = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
    )
    crs = models.CharField(
        max_length=50,
        blank=True,
        help_text='Coordinate reference system, e.g. "EPSG:32632".',
    )
    spatial_bbox = models.PolygonField(
        srid=4326,
        null=True,
        blank=True,
        help_text="WGS-84 bounding box of the raster.",
    )
    # Optional: only relevant for classification rasters
    n_classes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Number of distinct classes — for classification rasters only.",
    )
    class_names = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of class names — for classification rasters only.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        """Model metadata."""

        verbose_name = "Raster Scene"
        verbose_name_plural = "Raster Scenes"
        ordering = ["-acquisition_date", "data_source"]

    def __str__(self) -> str:
        """Return the data source name paired with the effective path."""
        path = self.effective_path or str(self.pk)
        source = self.data_source.name if self.data_source else "—"
        return f"{source} | {path}"

    @property
    def effective_path(self) -> str:
        """Return corpus_path if set, else the FileField name."""
        return self.corpus_path or self.file.name or ""


class RasterDataset(BaseModel):
    """A named, curated collection of raster scenes.

    Provides a stable reference to a specific set of scenes for reproducibility.
    Associated rasters (e.g. spatially overlapping classification rasters) are
    discovered at query time via spatial intersection — not stored explicitly.
    """

    project = models.ForeignKey(
        "prototype.Project",
        on_delete=models.CASCADE,
        related_name="raster_datasets",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=120,
        unique=True,
        help_text="URL-safe identifier used in manifest endpoints.",
    )
    description = models.TextField(blank=True)
    scenes = models.ManyToManyField(
        RasterScene,
        blank=True,
        related_name="datasets",
    )

    class Meta:
        """Model metadata."""

        verbose_name = "Raster Dataset"
        verbose_name_plural = "Raster Datasets"
        ordering = ["-modified_at", "-created_at"]

    def __str__(self) -> str:
        """Return the dataset name."""
        return self.name
