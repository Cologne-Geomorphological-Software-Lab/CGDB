# ruff: noqa: INP001 - not a package module; the Dockerfile copies this file to prototype/local_settings.py
"""Settings for the Docker demo (compose.demo.yml). Not for production.

Copied to prototype/local_settings.py in the image. The demo runs with DEBUG
on, because DEBUG=False requires HTTPS settings (prototype/settings.py) and
the demo serves plain HTTP on localhost. Values come from environment
variables set in compose.demo.yml.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("CGDB_DATA_DIR", "/data"))


def _secret_key() -> str:
    """Return DJANGO_SECRET_KEY, or the key the entrypoint stored in the data volume."""
    key = os.environ.get("DJANGO_SECRET_KEY", "")
    if key:
        return key
    key_file = DATA_DIR / "secret_key"
    return (
        key_file.read_text(encoding="utf-8").strip()
        if key_file.exists()
        else ""
    )


def _list(name: str, default: str) -> list[str]:
    return [
        item.strip()
        for item in os.environ.get(name, default).split(",")
        if item.strip()
    ]


SECRET_KEY = _secret_key()
DEBUG = True

ALLOWED_HOSTS = _list("CGDB_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = _list(
    "CGDB_CSRF_TRUSTED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
)

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "HOST": os.environ.get("CGDB_DB_HOST", "db"),
        "PORT": os.environ.get("CGDB_DB_PORT", "5432"),
        "NAME": os.environ.get("CGDB_DB_NAME", "cgdb"),
        "USER": os.environ.get("CGDB_DB_USER", "cgdb"),
        "PASSWORD": os.environ.get("CGDB_DB_PASSWORD", "cgdb"),
    }
}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = DATA_DIR / "media"
PROTECTED_MEDIA_ROOT = DATA_DIR / "protected_media"
