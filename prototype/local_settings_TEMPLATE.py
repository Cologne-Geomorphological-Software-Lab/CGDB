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

# settings.py already serves a development checkout: STATIC_URL "/static/",
# the project's static/ directory in STATICFILES_DIRS, uploads under media/.
# In production, point STATIC_ROOT (the collectstatic target) and MEDIA_ROOT
# at the directories the web server serves. Keep static/ in
# STATICFILES_DIRS: it holds the logo and the stylesheet that gives the
# geometry widget its height.
# STATIC_ROOT = "/srv/cgdb/staticfiles"
# MEDIA_ROOT = "/srv/cgdb/media"

# Uploads and backups that need a permission check (see
# docs/source/operations/protected-files.md). Must lie outside every
# directory the web server serves; the default is protected_media/ in the
# project directory.
# PROTECTED_MEDIA_ROOT = "/srv/cgdb/protected_media"
# PROTECTED_MEDIA_SERVER = "django"  # or "x-sendfile" / "x-accel-redirect"


# SECURITY WARNING: Do not set DEBUG = True in production!
DEBUG = False


def get_secret_key():
    raise NotImplementedError(
        "You must implement get_secret_key(), for example loading from an environment variable, a file, or another secure source."
    )


# Example: SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

try:
    SECRET_KEY = get_secret_key()
except Exception:
    logging.error("Error while loading SECRET_KEY.")
    raise
