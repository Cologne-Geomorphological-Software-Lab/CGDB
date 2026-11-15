"""Test-only settings using SpatiaLite (no PostgreSQL/PostGIS needed)."""

import os
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

# Static / media – uploads go to per-process temp dirs (conftest.py removes
# them after the session) so that FileField test artifacts never accumulate
# in the source tree. Defined here rather than in conftest.py: pytest-django
# loads these settings before conftest's pytest_configure runs. Only the
# paths are set; the storage creates the directories on the first upload, so
# merely importing these settings (mypy's django-stubs plugin does) leaves
# nothing behind. The two directories are siblings, as the protected-media
# system check requires.
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
STATIC_ROOT = ""
_TEST_TMP = Path(tempfile.gettempdir())
MEDIA_ROOT = str(_TEST_TMP / f"cgdb_test_media_{os.getpid()}")
PROTECTED_MEDIA_ROOT = str(_TEST_TMP / f"cgdb_test_protected_{os.getpid()}")
STATICFILES_DIRS = []
