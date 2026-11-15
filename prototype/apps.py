"""Django app configuration for the prototype app."""

from django.apps import AppConfig


class PrototypeConfig(AppConfig):
    """App config for core models, permissions, views, and admin configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "prototype"
    verbose_name = "Core Management"

    def ready(self) -> None:
        """Connect signal handlers and register system checks on startup."""
        import prototype.signals  # noqa: F401
        from prototype.checks import register_checks
        from prototype.vite_dev_server import start_if_appropriate

        register_checks()
        start_if_appropriate()
