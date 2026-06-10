"""Test-only settings using SpatiaLite (no PostgreSQL/PostGIS needed)."""

from .settings import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
        "NAME": ":memory:",
    }
}

SPATIALITE_LIBRARY_PATH = "C:/OSGeo4W/bin/mod_spatialite.dll"

SECRET_KEY = "test-secret-key-not-for-production"
DEBUG = True

# Suppress password hashing overhead in tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

import os

# Static / media – uploads go to an isolated temp dir created by conftest.py
# so that FileField test artifacts never accumulate in the source tree.
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
STATIC_ROOT = ""
MEDIA_ROOT = os.environ.get("CGDB_TEST_MEDIA_ROOT", "")
STATICFILES_DIRS = []
