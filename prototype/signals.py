from django.contrib.auth.models import User
from django.db import transaction
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm

from prototype.models import BaseModel


@receiver(post_migrate)
def setup_permission_groups(sender: type, **_kwargs: object) -> None:
    """Create/update predefined permission groups after every migrate run.

    Filtered to the prototype app so it only fires once per migrate, not once
    per installed app. The lazy import avoids circular-import issues at startup.
    """
    if sender.name != "prototype":
        return
    from prototype.permissions import create_permission_groups

    create_permission_groups()


@receiver(post_save)
def assign_permissions_to_creator(
    sender: type,
    instance: object,
    created: bool,
    **_kwargs: object,
) -> None:
    """Assigns all object-related permissions to the creator when the object is newly created."""
    if not issubclass(sender, BaseModel):
        return
    if not (
        created
        and hasattr(instance, "created_by")
        and isinstance(instance.created_by, User)
    ):
        return

    user = instance.created_by
    perms = [
        f"view_{instance._meta.model_name}",
        f"change_{instance._meta.model_name}",
        f"delete_{instance._meta.model_name}",
        f"add_{instance._meta.model_name}",
    ]

    def assign_perms() -> None:
        for perm in perms:
            assign_perm(perm, user, instance)

    transaction.on_commit(assign_perms)
