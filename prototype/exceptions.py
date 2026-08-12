"""Custom DRF exception handling.

DRF's default exception handler only translates Http404, DRF's own
PermissionDenied, and rest_framework.exceptions.APIException subclasses --
it does not know about django.core.exceptions.ValidationError. Several
models in this project raise that from clean()/save() (e.g.
field_data.models.Location, whose coordinate-bounds check runs on every
save()), so without this handler, a validation failure surfaces as an
unhandled 500 instead of DRF's standard {"field": ["message"]} 400 shape.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import exception_handler as _drf_default_handler


def exception_handler(exc: Exception, context: dict) -> object:
    """Translate a Django ValidationError into DRF's standard 400 shape.

    Any other exception is delegated to DRF's default handler unchanged.
    """
    if isinstance(exc, DjangoValidationError):
        detail = getattr(exc, "message_dict", None) or exc.messages
        exc = DRFValidationError(detail=detail)
    return _drf_default_handler(exc, context)
