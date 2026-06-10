"""Django app configuration for the field_data app."""

from django.apps import AppConfig


class FieldDataConfig(AppConfig):
    """App config for campaigns, locations, samples, and layers."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "field_data"
