"""Django app configuration for the laboratory app."""

from django.apps import AppConfig


class LaboratoryConfig(AppConfig):
    """App config for devices, methods, manufacturers, and accessories."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "laboratory"
