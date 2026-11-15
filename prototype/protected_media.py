"""Permission-checked delivery of protected uploads.

Every FileField that stores project data or maintenance results uses
prototype.storage.ProtectedFileSystemStorage. Its files live outside
MEDIA_ROOT and are only ever sent through protected_media_view(), which
looks up the record that owns the file and applies the same rule as the
admin and the API (prototype.access): the role must allow viewing the model,
and the user must be allowed to view the record's project.

The upload_to prefix of each protected FileField maps to a rule in RULES.
A file under an unknown prefix, a file no record owns, and a file the user
may not see all answer 404, so the response never reveals whether a file
exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, Http404, HttpResponse
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_GET

from prototype.access import (
    has_model_perm,
    has_project_perm,
    is_superuser,
    resolve_project,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.db.models import Model
    from django.db.models.fields.files import FieldFile
    from django.http import HttpRequest
    from django.http.response import HttpResponseBase

    from prototype.models import Project


SERVER_MODES = ("django", "x-sendfile", "x-accel-redirect")


@dataclass(frozen=True)
class ProtectedFileRule:
    """Who may download the files stored under one upload_to prefix.

    model:           "app_label.ModelName" of the record that owns the file
    field:           name of its FileField
    project_paths:   dunder paths from the record to its project (see
                     prototype.access.resolve_project)
    project_resolver: alternative to project_paths for owners that can't be
                     reached by a fixed path (e.g. a generic relation)
    superuser_only:  for maintenance results such as database backups
    needs_project:   False for records that don't belong to a project; then
                     the role permission alone decides
    """

    model: str
    field: str
    project_paths: tuple[str, ...] = ()
    project_resolver: Callable[[Model], Project | None] | None = None
    superuser_only: bool = False
    needs_project: bool = True


# upload_to prefix (with trailing slash) -> rule. Filled in as the FileFields
# move to the protected storage.
RULES: dict[str, ProtectedFileRule] = {}


def is_safe_name(name: str) -> bool:
    """Reject names that could escape the storage root or are malformed."""
    if not name or "\\" in name or "\x00" in name:
        return False
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts


def rule_for(name: str) -> ProtectedFileRule | None:
    """Return the rule of the longest prefix that *name* starts with."""
    matches = [prefix for prefix in RULES if name.startswith(prefix)]
    if not matches:
        return None
    return RULES[max(matches, key=len)]


def _owner(name: str) -> tuple[ProtectedFileRule, Model] | None:
    """Return the rule for *name* and the record that owns the file."""
    rule = rule_for(name) if is_safe_name(name) else None
    if rule is None:
        return None
    model = apps.get_model(rule.model)
    owner = model._default_manager.filter(**{rule.field: name}).first()
    return None if owner is None else (rule, owner)


def _may_view(user: object, rule: ProtectedFileRule, owner: Model) -> bool:
    """Apply "role AND project" (prototype.access) to the owning record."""
    if is_superuser(user):
        return True
    if rule.superuser_only or not has_model_perm(user, "view", type(owner)):
        return False
    if not rule.needs_project:
        return True
    project = (
        rule.project_resolver(owner)
        if rule.project_resolver is not None
        else resolve_project(owner, rule.project_paths)
    )
    return project is not None and has_project_perm(user, "view", project)


def permitted_file(user: object, name: str) -> FieldFile | None:
    """Return the stored file *name* if *user* may download it, else None."""
    found = _owner(name)
    if found is None:
        return None
    rule, owner = found
    if not _may_view(user, rule, owner):
        return None
    field_file: FieldFile = getattr(owner, rule.field)
    return field_file


def serve(field_file: FieldFile) -> HttpResponseBase:
    """Hand a permitted file to the client as a download.

    How depends on PROTECTED_MEDIA_SERVER (see settings.py). Every variant
    forces a download and forbids content sniffing, so an uploaded HTML or
    SVG file can't run in the site's origin.
    """
    mode = settings.PROTECTED_MEDIA_SERVER
    filename = PurePosixPath(field_file.name or "").name
    response: HttpResponseBase
    if mode == "django":
        response = FileResponse(
            field_file.open("rb"), as_attachment=True, filename=filename
        )
    elif mode == "x-sendfile":
        response = HttpResponse(content_type="application/octet-stream")
        response["X-Sendfile"] = field_file.path
    elif mode == "x-accel-redirect":
        response = HttpResponse(content_type="application/octet-stream")
        prefix = settings.PROTECTED_MEDIA_ACCEL_PREFIX.rstrip("/")
        response["X-Accel-Redirect"] = f"{prefix}/{field_file.name}"
    else:
        msg = f"Unknown PROTECTED_MEDIA_SERVER {mode!r}."
        raise ImproperlyConfigured(msg)
    disposition = content_disposition_header(
        as_attachment=True, filename=filename
    )
    if disposition:
        response["Content-Disposition"] = disposition
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_GET
def protected_media_view(request: HttpRequest, name: str) -> HttpResponseBase:
    """Serve one protected file to a user who may see it, 404 otherwise."""
    field_file = permitted_file(request.user, name)
    if (
        field_file is None
        or not field_file.name
        or not field_file.storage.exists(field_file.name)
    ):
        raise Http404
    return serve(field_file)
