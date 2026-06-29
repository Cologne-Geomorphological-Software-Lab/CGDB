"""Django app configuration for the geodata app."""

from django.apps import AppConfig


class GeoDataConfig(AppConfig):
    """App config for global geodata layers: Geomorphon, Landform, WorldCover."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "geodata"
