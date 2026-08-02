"""Test-only settings using PostGIS, to catch PostGIS/SpatiaLite SQL divergence.

Run against the docker-compose ``postgis`` service (see repo-root
``docker-compose.yml``):

    docker compose up -d postgis
    DJANGO_SETTINGS_MODULE=prototype.test_settings_postgis pytest -m gis

Production runs PostGIS; the default test suite (``prototype.test_settings``)
runs against in-memory SpatiaLite for speed. Tests that touch GIS-specific SQL
(raw queries, vendor-specific ORM functions, vector tiles) should be marked
``@pytest.mark.gis`` and run under both settings modules so a PostGIS-only bug
can't ship unnoticed again.
"""

from __future__ import annotations

import os

from .test_settings import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("CGDB_TEST_PG_NAME", "cgdb_test"),
        "USER": os.environ.get("CGDB_TEST_PG_USER", "cgdb"),
        "PASSWORD": os.environ.get("CGDB_TEST_PG_PASSWORD", "cgdb"),
        "HOST": os.environ.get("CGDB_TEST_PG_HOST", "localhost"),
        "PORT": os.environ.get("CGDB_TEST_PG_PORT", "5433"),
    },
}
