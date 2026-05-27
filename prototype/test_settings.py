"""Test-only settings using SpatiaLite (no PostgreSQL/PostGIS needed)."""
from .settings import *  # noqa: F401, F403

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

# Static / media are irrelevant for tests
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
STATIC_ROOT = ""
MEDIA_ROOT = ""
STATICFILES_DIRS = []
