import logging

# ==============================================================================
# SECURITY SETTINGS
# ==============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY is loaded from local_settings.py

ALLOWED_HOSTS = []

# SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 3600  # 1 hour
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


DEBUG = True


def get_secret_key():
    pass


try:
    SECRET_KEY = get_secret_key()
except Exception as e:
    logging.error(f"Error while loading SECRET_KEY: {e}")
    raise
