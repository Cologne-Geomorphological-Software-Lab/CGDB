# mypy: ignore-errors
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

# Django migration RunPython functions always take schema_editor even when unused
schema_editor  # noqa

# Django system-checks framework calls this by keyword even when unused (see ARG001 noqa)
app_configs  # noqa

# TYPE_CHECKING-only stub method parameters (`...` bodies) — never referenced,
# that's the point of a type-only Protocol/subclass stub
credentials  # noqa

# TYPE_CHECKING-only imports referenced solely inside string-literal cast()
# calls (e.g. cast("Iterable[bytes]", ...)) — real usage, invisible to
# vulture's AST-only analysis since it doesn't resolve forward-ref strings
Iterable  # noqa
StreamingHttpResponse  # noqa
TestResponse  # noqa
_FieldsetSpec  # noqa
