"""Django app configuration for the analysis app."""

from django.apps import AppConfig


class AnalysisConfig(AppConfig):
    """App config for geochronological and sedimentological analysis."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "analysis"
