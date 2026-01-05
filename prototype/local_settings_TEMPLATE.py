import logging

# ==============================================================================
# SECURITY SETTINGS
# ==============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY is loaded from local_settings.py

ALLOWED_HOSTS = []

SECURE_SSL_REDIRECT = True  # Set to False for local development without HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

DATABASES = {
    "default": {
        "ENGINE": "",
        "HOST": "",
        "NAME": "",
        "PORT": "",
        "USER": "",
        "PASSWORD": "",
    },
}

# ==============================================================================
# STATIC FILES & MEDIA
# ==============================================================================

STATIC_URL = ""
STATIC_ROOT = ""
STATICFILES_DIRS = []

MEDIA_URL = ""
MEDIA_ROOT = ""

# ==============================================================================
# DATA ORCHESTRATION (OPTIONAL)
# ==============================================================================

# Dagster Web UI URL (uncomment to enable Dagster link in admin sidebar)
DAGSTER_URL = None  # Disabled by default
# DAGSTER_URL = "http://localhost:3000"  # Development
# DAGSTER_URL = "https://dagster.your-domain.com"  # Production


# SECURITY WARNING: Do not set DEBUG = True in production!
DEBUG = False


def get_secret_key():
    raise NotImplementedError(
        "You must implement get_secret_key(), for example loading from an environment variable, a file, or another secure source."
    )


# Example: SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

try:
    SECRET_KEY = get_secret_key()
except Exception as e:
    logging.error("Error while loading SECRET_KEY.")
    raise
