from django.contrib.auth.models import User
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm


@receiver(post_save)
def assign_permissions_to_creator(sender, instance, created, **kwargs):
    """Assigns all object-related permissions to the creator when the object is newly created."""
    if created and hasattr(instance, "created_by") and isinstance(instance.created_by, User):

        user = instance.created_by

        perms = [
            f"view_{instance._meta.model_name}",
            f"change_{instance._meta.model_name}",
            f"delete_{instance._meta.model_name}",
        ]

        def assign_perms() -> None:
            for perm in perms:
                assign_perm(perm, user, instance)

        transaction.on_commit(assign_perms)
