"""Django app configuration for the orchestration app."""

from django.apps import AppConfig


class OrchestrationConfig(AppConfig):
    """App config for data orchestration and pipeline scheduling."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "orchestration"
    verbose_name = "Data Orchestration"

    def ready(self) -> None:
        """Connect signal handlers when the app is ready."""
        import orchestration.signals  # noqa: F401
