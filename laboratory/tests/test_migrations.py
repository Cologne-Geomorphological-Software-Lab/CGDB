"""Tests for the LBG9 data migration (laboratory 0006-0008).

Converts AccessoryParameter.method from free-text CharField to
ForeignKey(Method). Runs the actual migration sequence against a real
schema (not just the backfill function in isolation) to prove the
rename -> add -> backfill -> drop sequence preserves matching data and
leaves genuinely unmatched text as NULL rather than guessing or crashing.
"""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

_MIGRATE_FROM = [
    ("laboratory", "0005_alter_accessory_options_alter_device_options_and_more")
]
_MIGRATE_TO = [("laboratory", "0008_remove_accessoryparameter_method_legacy")]


class AccessoryParameterMethodBackfillTest(TransactionTestCase):
    """Exercises the real migration sequence via MigrationExecutor."""

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(_MIGRATE_FROM)

        old_apps = executor.loader.project_state(_MIGRATE_FROM).apps
        Device = old_apps.get_model("laboratory", "Device")
        Accessory = old_apps.get_model("laboratory", "Accessory")
        Method = old_apps.get_model("laboratory", "Method")
        AccessoryParameter = old_apps.get_model("laboratory", "AccessoryParameter")

        device = Device.objects.create(name="Backfill Device")
        accessory = Accessory.objects.create(device=device, name="Backfill Accessory")
        Method.objects.create(name="SAR")

        AccessoryParameter.objects.create(
            method="sar",  # lowercase - proves the match is case-insensitive
            accessory=accessory,
            parameter_name="matching",
            parameter_value="1",
        )
        AccessoryParameter.objects.create(
            method="  SAR  ",  # surrounding whitespace - proves it's stripped
            accessory=accessory,
            parameter_name="matching_padded",
            parameter_value="1",
        )
        AccessoryParameter.objects.create(
            method="Some Retired Method",  # no matching Method row
            accessory=accessory,
            parameter_name="unmatched",
            parameter_value="2",
        )
        AccessoryParameter.objects.create(
            method="",  # blank - must not crash the backfill
            accessory=accessory,
            parameter_name="blank",
            parameter_value="3",
        )

        # Re-fetch a fresh executor: applying migrations mutates the loader's
        # graph state, so the same instance can't be trusted for the second migrate().
        executor = MigrationExecutor(connection)
        executor.migrate(_MIGRATE_TO)
        self.new_apps = executor.loader.project_state(_MIGRATE_TO).apps

    def tearDown(self):
        # Bring the schema back to the latest migration so later tests in
        # the run see the expected final schema.
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_case_insensitive_match_is_backfilled(self):
        AccessoryParameter = self.new_apps.get_model(
            "laboratory", "AccessoryParameter"
        )
        Method = self.new_apps.get_model("laboratory", "Method")
        param = AccessoryParameter.objects.get(parameter_name="matching")
        self.assertEqual(param.method_id, Method.objects.get(name="SAR").pk)

    def test_whitespace_is_stripped_before_matching(self):
        AccessoryParameter = self.new_apps.get_model(
            "laboratory", "AccessoryParameter"
        )
        Method = self.new_apps.get_model("laboratory", "Method")
        param = AccessoryParameter.objects.get(parameter_name="matching_padded")
        self.assertEqual(param.method_id, Method.objects.get(name="SAR").pk)

    def test_unmatched_text_is_left_null(self):
        AccessoryParameter = self.new_apps.get_model(
            "laboratory", "AccessoryParameter"
        )
        param = AccessoryParameter.objects.get(parameter_name="unmatched")
        self.assertIsNone(param.method_id)

    def test_blank_text_is_left_null_without_crashing(self):
        AccessoryParameter = self.new_apps.get_model(
            "laboratory", "AccessoryParameter"
        )
        param = AccessoryParameter.objects.get(parameter_name="blank")
        self.assertIsNone(param.method_id)

    def test_method_legacy_column_is_dropped(self):
        AccessoryParameter = self.new_apps.get_model(
            "laboratory", "AccessoryParameter"
        )
        field_names = {f.name for f in AccessoryParameter._meta.get_fields()}
        self.assertNotIn("method_legacy", field_names)
