from django.apps import AppConfig


class PrototypeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "prototype"
    verbose_name = "Core Management"

    def ready(self):
        import prototype.signals  # noqa: F401
