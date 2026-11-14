"""Test helper: put a user into one of the role groups.

Access to project data needs a role permission and a project permission
(prototype.access). Tests about project scoping give their users the
"Principal Investigator" role, which allows every action on every domain
model, so that the project permissions alone decide the outcome. Tests about
the roles themselves pick the role they examine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import Group

from prototype.permissions import create_permission_groups

if TYPE_CHECKING:
    from django.contrib.auth.models import User


def give_role(user: User, role: str = "Principal Investigator") -> User:
    """Add *user* to the role group *role* and return the user.

    Creates the groups first: the post_migrate handler can run before every
    app's permissions exist, so a fresh test database may lack some of them.
    """
    create_permission_groups()
    user.groups.add(Group.objects.get(name=role))
    # ModelBackend caches permissions on the instance; drop the cache so the
    # new group takes effect for this object too.
    for cache in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
        if hasattr(user, cache):
            delattr(user, cache)
    return user
