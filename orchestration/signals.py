"""Signal handlers for the orchestration app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.apps import apps as django_apps
from django.core.checks import Error, register
from django.db.models.signals import post_migrate
from django.dispatch import receiver

if TYPE_CHECKING:
    from django.apps import AppConfig

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
def populate_default_duckdb_config(
    sender: AppConfig, **_kwargs: object
) -> None:
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


@register()
def check_duckdb_config_models_exist(
    app_configs: object,  # noqa: ARG001 — Django's checks framework calls this by keyword (app_configs=...)
    **_kwargs: object,
) -> list[Error]:
    """Verify every (app_label, model_name) pair in _DEFAULT_DUCKDB_CONFIGS still resolves.

    tech debt O13: previously a rename/removal of one of these models
    elsewhere only surfaced as a runtime warning the next time the DuckDB
    export op ran (dagster_home.maintenance_jobs.export_to_duckdb's
    LookupError handling), not at `manage.py check`/CI time.
    """
    errors = []
    for app_label, model_name, _role in _DEFAULT_DUCKDB_CONFIGS:
        try:
            django_apps.get_model(app_label, model_name)
        except LookupError:
            errors.append(
                Error(
                    f"_DEFAULT_DUCKDB_CONFIGS references "
                    f"{app_label}.{model_name}, which does not exist.",
                    hint=(
                        "Update or remove this entry in "
                        "orchestration/signals.py._DEFAULT_DUCKDB_CONFIGS."
                    ),
                    obj="orchestration.signals",
                    id="orchestration.E001",
                )
            )
    return errors
