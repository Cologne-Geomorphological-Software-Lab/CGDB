"""Signal handlers for the orchestration app."""

from django.db.models.signals import post_migrate
from django.dispatch import receiver

_DEFAULT_DUCKDB_CONFIGS = [
    ("field_data", "Sample", "fact"),
    ("analysis", "LuminescenceDating", "dim"),
    ("analysis", "RadiocarbonDating", "dim"),
    ("analysis", "GrainSize", "dim"),
    ("analysis", "GenericMeasurement", "dim"),
    ("analysis", "Counting", "dim"),
    ("field_data", "Location", "dim"),
    ("field_data", "Layer", "dim"),
    ("field_data", "Campaign", "dim"),
    ("field_data", "StudyArea", "dim"),
    ("prototype", "Project", "dim"),
    ("bibliography", "Reference", "dim"),
    ("laboratory", "Device", "dim"),
    ("laboratory", "Method", "dim"),
]


@receiver(post_migrate)
def populate_default_duckdb_config(sender: type, **_kwargs: object) -> None:
    """Seed default DuckDBTableConfig entries after orchestration migrations run.

    Filtered to the orchestration app so it fires once per migrate, not once
    per installed app. Uses get_or_create to be idempotent.
    """
    if sender.name != "orchestration":
        return

    from orchestration.models import DuckDBTableConfig

    for app_label, model_name, role in _DEFAULT_DUCKDB_CONFIGS:
        DuckDBTableConfig.objects.get_or_create(
            app_label=app_label,
            model_name=model_name,
            defaults={"role": role},
        )
