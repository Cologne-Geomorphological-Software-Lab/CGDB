"""File storage for uploads that only permitted users may download.

Files live under settings.PROTECTED_MEDIA_ROOT, which no web server serves.
A file's URL always points at the permission-checked view
(prototype.protected_media), never at a public media path, so a FileField
using this storage cannot leak through a forgotten link or a /media/ alias.
"""

from __future__ import annotations

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.signals import setting_changed
from django.urls import reverse
from django.utils.functional import cached_property


class ProtectedFileSystemStorage(FileSystemStorage):
    """FileSystemStorage rooted at PROTECTED_MEDIA_ROOT with permission-checked URLs."""

    def __init__(self) -> None:
        """Follow PROTECTED_MEDIA_ROOT, also when tests override it."""
        super().__init__()
        setting_changed.connect(self._reset_location)

    @cached_property
    def base_location(self) -> str:
        """Return the configured protected root instead of MEDIA_ROOT."""
        return str(settings.PROTECTED_MEDIA_ROOT)

    def _reset_location(self, *, setting: str, **_kwargs: object) -> None:
        """Drop the cached location when PROTECTED_MEDIA_ROOT changes."""
        if setting == "PROTECTED_MEDIA_ROOT":
            self.__dict__.pop("base_location", None)
            self.__dict__.pop("location", None)

    def url(self, name: str | None) -> str:
        """Return the URL of the permission-checked download view for *name*."""
        if not name:
            msg = "This file has no name."
            raise ValueError(msg)
        return reverse("protected_media", args=[name])


protected_storage = ProtectedFileSystemStorage()


def get_protected_storage() -> ProtectedFileSystemStorage:
    """Return the shared protected storage.

    FileFields reference this callable rather than the instance, so their
    migrations record a stable import path instead of a serialized storage.
    """
    return protected_storage


__all__ = ["ProtectedFileSystemStorage", "get_protected_storage"]
