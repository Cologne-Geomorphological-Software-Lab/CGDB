# vulture whitelist — false positives
# pytest hook parameters (required by pytest API, cannot be renamed)
config  # pytest_configure hook parameter
session  # pytest_sessionfinish hook parameter
exitstatus  # pytest_sessionfinish hook parameter

# Django local settings override — intentional star import suppressor
ALLOWED_HOSTS  # noqa
CSRF_COOKIE_SECURE  # noqa
SECRET_KEY  # noqa
SECURE_HSTS_INCLUDE_SUBDOMAINS  # noqa
SECURE_HSTS_PRELOAD  # noqa
SECURE_HSTS_SECONDS  # noqa
SECURE_SSL_REDIRECT  # noqa
SESSION_COOKIE_SECURE  # noqa
STATIC_ROOT  # noqa
STATIC_URL  # noqa
STATICFILES_DIRS  # noqa

# GIS admin — imported for side effects (registers GIS admin classes)
gis_admin  # noqa
