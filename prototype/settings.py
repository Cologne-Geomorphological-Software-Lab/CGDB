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

from django.templatetags.static import static

from .unfold_settings import UNFOLD as unfold_settings

BASE_DIR = Path(__file__).resolve().parent.parent


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
    # CGDB Apps
    "prototype",
    "field_data",
    "analysis",
    "bibliography",
    "laboratory",
    "orchestration",
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
# DJANGO EXTENSIONS & THIRD PARTY APPS
# ==============================================================================

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# File Upload Settings
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB in bytes
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB in bytes

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Unfold Admin Interface
UNFOLD = unfold_settings
UNFOLD["STYLES"] = [lambda request: static("/css/dj_map.css")]


# ==============================================================================
# LOCAL SETTINGS OVERRIDE
# ==============================================================================

try:
    from .local_settings import (
        ALLOWED_HOSTS,
        CSRF_COOKIE_SECURE,
        DATABASES,
        DEBUG,
        MEDIA_ROOT,
        MEDIA_URL,
        SECRET_KEY,
        SECURE_HSTS_INCLUDE_SUBDOMAINS,
        SECURE_HSTS_PRELOAD,
        SECURE_HSTS_SECONDS,
        SECURE_SSL_REDIRECT,
        SESSION_COOKIE_SECURE,
        STATIC_ROOT,
        STATIC_URL,
        STATICFILES_DIRS,
    )

    try:
        from .local_settings import DAGSTER_URL
    except ImportError:
        DAGSTER_URL = None
except ImportError:
    import logging
    logging.warning("local_settings.py not imported.")
