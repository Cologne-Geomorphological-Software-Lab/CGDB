"""Django app configuration for the bibliography app."""

from django.apps import AppConfig


class BibliographyConfig(AppConfig):
    """App config for literature reference management."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "bibliography"
