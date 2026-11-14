"""Project-based access checks shared by the admin, the REST API and imports.

Access to project data needs two permissions: the model permission from
the user's role group (what the user may do with this kind of record) and
the object permission on the project (which project's data). Every write or
read of project-owned data is decided here, so the admin
mixins (prototype.mixins), the DRF permission classes
(prototype.api_permissions), the import resources and the API views apply
the same rules instead of each re-implementing them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from guardian.shortcuts import get_objects_for_user

from prototype.models import Project

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.db.models import Model, QuerySet


# Models whose records can be literature data (data_source="literature"):
# visible to every authenticated user, editable only by superusers, and not
# owned by a single project. Add a model here only when it has its own
# data_source CharField with a "literature" value — a model that merely lacks
# a project link must not be treated as public by accident.
LITERATURE_ELIGIBLE_MODELS = frozenset({"Location"})


def is_superuser(user: object) -> bool:
    """Return True for an authenticated superuser."""
    return bool(getattr(user, "is_superuser", False))


def accessible_projects(user: object) -> QuerySet[Project]:
    """Return the projects on which *user* holds view_project.

    Object permissions only: a global view_project permission does not open
    every project, and superusers are handled by the callers.
    """
    return get_objects_for_user(
        user,
        "prototype.view_project",
        klass=Project,
        use_groups=True,
        any_perm=False,
        with_superuser=False,
        accept_global_perms=False,
    )


def addable_projects(user: object) -> QuerySet[Project]:
    """Return the projects on which *user* holds add_project."""
    return get_objects_for_user(
        user,
        "prototype.add_project",
        klass=Project,
        use_groups=True,
        any_perm=False,
        with_superuser=False,
        accept_global_perms=False,
    )


def scope_to_accessible_projects[T: Model](
    user: object, qs: QuerySet[T], lookup: str = "project"
) -> QuerySet[T]:
    """Restrict *qs* to rows whose project (reached via *lookup*) the user may view."""
    if is_superuser(user):
        return qs
    project_ids = accessible_projects(user).values_list("id", flat=True)
    return qs.filter(**{f"{lookup}__in": project_ids})


def resolve_project(obj: object, paths: Iterable[str]) -> Project | None:
    """Follow each dunder path from *obj* and return the first project found.

    Each path names the full attribute chain ending at the project, e.g.
    "project", "location__project" or "sample__location__project". A missing
    or unset link on the way yields None for that path, never an error.
    """
    for path in paths:
        current: object = obj
        for attr in path.split("__"):
            current = getattr(current, attr, None)
            if current is None:
                break
        if current is not None:
            return current  # type: ignore[return-value]
    return None


def is_literature(obj: object) -> bool:
    """Return True only for literature records of an eligible model."""
    return (
        type(obj).__name__ in LITERATURE_ELIGIBLE_MODELS
        and getattr(obj, "data_source", None) == "literature"
    )


def has_model_perm(user: object, action: str, model: type[Model]) -> bool:
    """Return True if the user's role allows *action* on *model*.

    Model-level permissions come from the role and domain groups
    (prototype.permissions). They are the first half of every check on
    project data; the project permission is the second.
    """
    if is_superuser(user):
        return True
    opts = model._meta
    has_perm = getattr(user, "has_perm", None)
    return bool(
        has_perm and has_perm(f"{opts.app_label}.{action}_{opts.model_name}")
    )


def has_project_perm(user: object, action: str, project: Project) -> bool:
    """Return True if *user* may perform *action* on data of *project*.

    *action* is one of view, add, change, delete and maps to the matching
    Guardian object permission on the project.
    """
    if is_superuser(user):
        return True
    has_perm = getattr(user, "has_perm", None)
    return bool(has_perm and has_perm(f"prototype.{action}_project", project))


_DENIED_MESSAGES = {
    "view": "You do not have permission to view data in this project.",
    "add": "You do not have permission to add data to this project.",
    "change": "You do not have permission to change data in this project.",
    "delete": "You do not have permission to delete data in this project.",
}


def require_project_perm(
    user: object,
    action: str,
    project: Project | None,
    msg: str | None = None,
    *,
    model: type[Model] | None = None,
) -> None:
    """Raise PermissionDenied unless *user* may perform *action* on *project*.

    With *model*, the user's role must also allow *action* on that model.
    A missing project denies (fail closed) for everyone but superusers. DRF
    turns the exception into a 403 with *msg* as its detail.
    """
    if is_superuser(user):
        return
    if (
        project is None
        or (model is not None and not has_model_perm(user, action, model))
        or not has_project_perm(user, action, project)
    ):
        raise PermissionDenied(msg or _DENIED_MESSAGES[action])
