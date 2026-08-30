"""Tests for orchestration signals: DuckDB default config seeding."""

from typing import TYPE_CHECKING, cast
from unittest.mock import patch

from django.test import TestCase

from orchestration.models import DuckDBTableConfig
from orchestration.signals import (
    _DEFAULT_DUCKDB_CONFIGS,
    check_duckdb_config_models_exist,
    populate_default_duckdb_config,
)

if TYPE_CHECKING:
    from django.apps import AppConfig


class FakeAppConfig:
    """Minimal stand-in for an AppConfig used in signal tests."""

    def __init__(self, name: str):
        self.name = name


def _fake_app_config(name: str) -> "AppConfig":
    return cast("AppConfig", FakeAppConfig(name))


class PopulateDefaultDuckDBConfigTests(TestCase):
    def test_seeding_creates_all_default_configs(self):
        DuckDBTableConfig.objects.all().delete()
        populate_default_duckdb_config(sender=_fake_app_config("orchestration"))
        self.assertEqual(
            DuckDBTableConfig.objects.count(), len(_DEFAULT_DUCKDB_CONFIGS)
        )

    def test_seeding_is_idempotent(self):
        populate_default_duckdb_config(sender=_fake_app_config("orchestration"))
        populate_default_duckdb_config(sender=_fake_app_config("orchestration"))
        self.assertEqual(
            DuckDBTableConfig.objects.count(), len(_DEFAULT_DUCKDB_CONFIGS)
        )

    def test_sample_is_seeded_as_fact(self):
        DuckDBTableConfig.objects.all().delete()
        populate_default_duckdb_config(sender=_fake_app_config("orchestration"))
        cfg = DuckDBTableConfig.objects.get(app_label="field_data", model_name="Sample")
        self.assertEqual(cfg.role, "fact")

    def test_dimension_models_are_seeded_as_dim(self):
        DuckDBTableConfig.objects.all().delete()
        populate_default_duckdb_config(sender=_fake_app_config("orchestration"))
        dim_configs = DuckDBTableConfig.objects.filter(role="dim")
        self.assertEqual(dim_configs.count(), len(_DEFAULT_DUCKDB_CONFIGS) - 1)

    def test_signal_ignored_for_other_apps(self):
        DuckDBTableConfig.objects.all().delete()
        populate_default_duckdb_config(sender=_fake_app_config("prototype"))
        self.assertEqual(DuckDBTableConfig.objects.count(), 0)

    def test_existing_roles_not_overwritten(self):
        DuckDBTableConfig.objects.all().delete()
        DuckDBTableConfig.objects.create(
            app_label="field_data", model_name="Sample", role="exclude"
        )
        populate_default_duckdb_config(sender=_fake_app_config("orchestration"))
        cfg = DuckDBTableConfig.objects.get(app_label="field_data", model_name="Sample")
        # get_or_create should not overwrite the manually set role
        self.assertEqual(cfg.role, "exclude")


class CheckDuckDBConfigModelsExistTests(TestCase):
    """tech debt O13: a renamed/removed model referenced in
    _DEFAULT_DUCKDB_CONFIGS must be visible at `manage.py check`/CI time,
    not just as a runtime warning the next time the DuckDB export op runs."""

    def test_real_config_list_has_no_errors(self):
        errors = check_duckdb_config_models_exist(app_configs=None)
        self.assertEqual(errors, [])

    def test_nonexistent_model_is_reported(self):
        with patch(
            "orchestration.signals._DEFAULT_DUCKDB_CONFIGS",
            [("field_data", "NoSuchModel", "dim")],
        ):
            errors = check_duckdb_config_models_exist(app_configs=None)
        self.assertEqual(len(errors), 1)
        self.assertIn("field_data.NoSuchModel", errors[0].msg)
        self.assertEqual(errors[0].id, "orchestration.E001")

    def test_nonexistent_app_label_is_reported(self):
        with patch(
            "orchestration.signals._DEFAULT_DUCKDB_CONFIGS",
            [("no_such_app", "Sample", "dim")],
        ):
            errors = check_duckdb_config_models_exist(app_configs=None)
        self.assertEqual(len(errors), 1)

    def test_valid_and_invalid_entries_mixed(self):
        with patch(
            "orchestration.signals._DEFAULT_DUCKDB_CONFIGS",
            [
                ("field_data", "Sample", "fact"),
                ("field_data", "NoSuchModel", "dim"),
            ],
        ):
            errors = check_duckdb_config_models_exist(app_configs=None)
        self.assertEqual(len(errors), 1)
        self.assertIn("NoSuchModel", errors[0].msg)
