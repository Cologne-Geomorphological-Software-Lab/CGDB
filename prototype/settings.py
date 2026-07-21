"""Django settings for CGDB (Cologne Geomorphological Database).

This configuration supports the consolidated app structure:
- prototype: Core management and organisation models
- field_data: Field campaigns, locations, samples (includes former geodata)
- analysis: All analytical methods (includes paleobotany, geochronology, sedimentology)
- bibliography: Literature management
- laboratory: Equipment and procedures

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.templatetags.static import static

from .unfold_settings import UNFOLD as unfold_settings

BASE_DIR = Path(__file__).resolve().parent.parent

# GeoDjango on Windows: point to OSGeo4W if present.
# The add_dll_directory handle must be stored at module level — if it is
# garbage-collected, Python removes OSGeo4W from the DLL search path, which
# causes GDAL's transitive dependencies (PROJ, GEOS, OpenSSL) to go missing
# when the spatialite backend is first loaded during django.setup().
# Storing _gdal_lib keeps the ctypes handle alive so Windows does not unload
# the DLL between settings import and the first real GDAL call in libgdal.py.
_osgeo_bin = Path("C:/OSGeo4W/bin")
_osgeo_dll_handle = (
    None  # keeps add_dll_directory alive for the process lifetime
)
_gdal_lib = (
    None  # keeps CDLL handle alive; prevents dependency re-resolution failure
)
if os.name == "nt" and _osgeo_bin.exists():
    _osgeo_bin_str = str(_osgeo_bin)
    if hasattr(os, "add_dll_directory"):
        _osgeo_dll_handle = os.add_dll_directory(_osgeo_bin_str)
    if _osgeo_bin_str not in os.environ.get("PATH", ""):
        os.environ["PATH"] = (
            _osgeo_bin_str + os.pathsep + os.environ.get("PATH", "")
        )
    GDAL_LIBRARY_PATH = str(_osgeo_bin / "gdal311.dll")
    GEOS_LIBRARY_PATH = str(_osgeo_bin / "geos_c.dll")
    os.environ["PROJ_LIB"] = "C:/OSGeo4W/share/proj"
    import ctypes as _ctypes

    _gdal_lib = _ctypes.CDLL(GDAL_LIBRARY_PATH)


# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.",
        "NAME": "",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    },
}


# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================

INSTALLED_APPS = [
    # Unfold Admin
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "unfold.contrib.import_export",
    "unfold.contrib.guardian",
    # Django Core Apps
    "django.contrib.admin",
    "django.contrib.admindocs",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    # Third Party Apps
    "guardian",
    "import_export",
    "django_filters",
    "crispy_forms",
    "docs",
    # REST API
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_gis",
    "drf_spectacular",
    # CGDB Apps
    "prototype",
    "field_data",
    "analysis",
    "bibliography",
    "laboratory",
    "orchestration",
    "geodata",
    "raster_data",
]

# ==============================================================================
# MIDDLEWARE CONFIGURATION
# ==============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.admindocs.middleware.XViewMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ==============================================================================
# AUTHENTICATION & AUTHORIZATION
# ==============================================================================

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
]


ANONYMOUS_USER_ID = -1


LOGIN_URL = "login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]


# ==============================================================================
# URL & TEMPLATE CONFIGURATION
# ==============================================================================

ROOT_URLCONF = "prototype.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "prototype.wsgi.application"

# ==============================================================================
# INTERNATIONALIZATION
# ==============================================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ==============================================================================
# CACHING
# ==============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "cgdb-cache",
    }
}

# ==============================================================================
# LOGGING
# ==============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "prototype": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "field_data": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "analysis": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ==============================================================================
# DJANGO REST FRAMEWORK
# ==============================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "CGDB API",
    "DESCRIPTION": "Cologne Geomorphological Database REST API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # drf-spectacular defaults SERVE_PERMISSIONS to AllowAny, silently
    # overriding REST_FRAMEWORK's DEFAULT_PERMISSION_CLASSES for the schema
    # and Swagger UI views. Keep it consistent with the rest of the API.
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticated"],
}

# ==============================================================================
# DJANGO EXTENSIONS & THIRD PARTY APPS
# ==============================================================================

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# File Upload Settings
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB in bytes
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB in bytes

# Crispy Forms — unfold_crispy is provided by django-unfold (no extra package needed)
CRISPY_ALLOWED_TEMPLATE_PACKS = ["unfold_crispy"]
CRISPY_TEMPLATE_PACK = "unfold_crispy"

# Unfold Admin Interface
UNFOLD = unfold_settings
UNFOLD["STYLES"] = [
    lambda request: static("css/styles.css"),
    lambda request: static("css/dj_map.css"),
]


# ==============================================================================
# LOCAL SETTINGS OVERRIDE
# ==============================================================================

DEBUG = False
ALLOWED_HOSTS: list[str] = []
DAGSTER_URL = None

try:
    from .local_settings import *  # noqa: F401, F403
except ImportError:
    import logging

    logging.warning("local_settings.py not found; running with locked-down defaults.")

if not globals().get("SECRET_KEY"):
    raise ImproperlyConfigured(
        "SECRET_KEY is not set. Add it to prototype/local_settings.py."
    )

DOCS_ROOT = os.path.join(BASE_DIR, "docs/_build/html")
DOCS_ACCESS = "public"
