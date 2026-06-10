"""Django app configuration for the prototype app."""

from django.apps import AppConfig


class PrototypeConfig(AppConfig):
    """App config for core models, permissions, views, and admin configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "prototype"
    verbose_name = "Core Management"

    def ready(self) -> None:
        """Connect signal handlers on app startup."""
        import prototype.signals  # noqa: F401
