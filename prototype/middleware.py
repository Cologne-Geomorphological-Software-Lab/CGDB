from __future__ import annotations

import threading

from django.http import HttpRequest, HttpResponse

_user = threading.local()


class CurrentUserMiddleware:
    def __init__(self, get_response: object) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        _user.value = request.user
        return self.get_response(request)


def get_current_user() -> object | None:
    return getattr(_user, "value", None)
