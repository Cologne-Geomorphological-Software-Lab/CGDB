"""Middleware for storing the current authenticated user in thread-local state."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

_user = threading.local()


class CurrentUserMiddleware:
    """Middleware that stores the current request user in a thread-local variable."""

    def __init__(self, get_response: object) -> None:
        """Store the next middleware or view callable."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Set the current user for this thread, then call the next handler."""
        _user.value = request.user
        return self.get_response(request)


def get_current_user() -> object | None:
    """Return the user attached to the current request, or None outside a request."""
    return getattr(_user, "value", None)
