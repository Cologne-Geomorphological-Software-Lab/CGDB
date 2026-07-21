"""Django app configuration for the raster_data app."""

from django.apps import AppConfig


class RasterDataConfig(AppConfig):
    """App config for raster datasets: scenes, labels, pairs, and datasets."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "raster_data"
    verbose_name = "Raster Data"
