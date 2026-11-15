"""The cache, and with it the API throttle counters, is shared by all processes.

With a per-process cache (LocMemCache) every web server process counts
requests separately and a restart resets the counters, so the login limit
of 10 attempts per hour became 10 per process.
"""

import importlib

from django.conf import settings
from django.db import connection
from django.test import TestCase, override_settings

_DB_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cgdb_cache_migration_test",
    }
}


class CacheSettingsTest(TestCase):
    def test_default_cache_is_shared_between_processes(self):
        self.assertEqual(
            settings.CACHES["default"]["BACKEND"],
            "django.core.cache.backends.db.DatabaseCache",
        )

    @override_settings(CACHES=_DB_CACHE)
    def test_migration_creates_the_cache_table(self):
        migration = importlib.import_module(
            "prototype.migrations.0006_create_cache_table"
        )
        migration.create_cache_table(apps=None, schema_editor=None)
        self.assertIn(
            "cgdb_cache_migration_test", connection.introspection.table_names()
        )
