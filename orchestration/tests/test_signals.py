"""Tests for orchestration signals: DuckDB default config seeding."""

from django.test import TestCase

from orchestration.models import DuckDBTableConfig
from orchestration.signals import _DEFAULT_DUCKDB_CONFIGS, populate_default_duckdb_config


class FakeAppConfig:
    """Minimal stand-in for an AppConfig used in signal tests."""

    def __init__(self, name: str):
        self.name = name


class PopulateDefaultDuckDBConfigTests(TestCase):
    def test_seeding_creates_all_default_configs(self):
        DuckDBTableConfig.objects.all().delete()
        populate_default_duckdb_config(sender=FakeAppConfig("orchestration"))
        self.assertEqual(
            DuckDBTableConfig.objects.count(), len(_DEFAULT_DUCKDB_CONFIGS)
        )

    def test_seeding_is_idempotent(self):
        populate_default_duckdb_config(sender=FakeAppConfig("orchestration"))
        populate_default_duckdb_config(sender=FakeAppConfig("orchestration"))
        self.assertEqual(
            DuckDBTableConfig.objects.count(), len(_DEFAULT_DUCKDB_CONFIGS)
        )

    def test_sample_is_seeded_as_fact(self):
        DuckDBTableConfig.objects.all().delete()
        populate_default_duckdb_config(sender=FakeAppConfig("orchestration"))
        cfg = DuckDBTableConfig.objects.get(app_label="field_data", model_name="Sample")
        self.assertEqual(cfg.role, "fact")

    def test_dimension_models_are_seeded_as_dim(self):
        DuckDBTableConfig.objects.all().delete()
        populate_default_duckdb_config(sender=FakeAppConfig("orchestration"))
        dim_configs = DuckDBTableConfig.objects.filter(role="dim")
        self.assertEqual(dim_configs.count(), len(_DEFAULT_DUCKDB_CONFIGS) - 1)

    def test_signal_ignored_for_other_apps(self):
        DuckDBTableConfig.objects.all().delete()
        populate_default_duckdb_config(sender=FakeAppConfig("prototype"))
        self.assertEqual(DuckDBTableConfig.objects.count(), 0)

    def test_existing_roles_not_overwritten(self):
        DuckDBTableConfig.objects.all().delete()
        DuckDBTableConfig.objects.create(
            app_label="field_data", model_name="Sample", role="exclude"
        )
        populate_default_duckdb_config(sender=FakeAppConfig("orchestration"))
        cfg = DuckDBTableConfig.objects.get(app_label="field_data", model_name="Sample")
        # get_or_create should not overwrite the manually set role
        self.assertEqual(cfg.role, "exclude")
