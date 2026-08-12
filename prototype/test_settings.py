"""Test-only settings using SpatiaLite (no PostgreSQL/PostGIS needed)."""

import tempfile
from pathlib import Path

from .settings import *  # noqa: F403

# Existing tests construct RasterScene.corpus_path with arbitrary absolute
# placeholder values (tempfile.mkstemp() paths, "/corpus/..." strings,
# deliberately-nonexistent paths) that were never meant to exercise the F6
# corpus-root restriction — default to the drive/filesystem root here so
# every absolute path trivially passes containment. The dedicated test for
# the restriction itself (RasterSceneCorpusPathValidationTest) narrows this
# back down via @override_settings.
RASTER_CORPUS_ROOT = Path(tempfile.gettempdir()).anchor

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
        "NAME": ":memory:",
    },
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
