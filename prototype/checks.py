"""System checks for the protected file storage.

Protected uploads are only safe while no web server can reach their
directory. These checks catch the configurations that would undo that: a
PROTECTED_MEDIA_ROOT inside MEDIA_ROOT or STATIC_ROOT, an unknown delivery
mode, and protected files left behind under MEDIA_ROOT by an older version.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.checks import Error, Tags, register
from django.core.checks import Warning as CheckWarning

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.apps import AppConfig
    from django.core.checks import CheckMessage


def _resolved(value: object) -> Path | None:
    """Return *value* as an absolute path, or None when it is unset."""
    if not value:
        return None
    return Path(str(value)).resolve()


def check_protected_media_root(
    app_configs: Sequence[AppConfig] | None = None,  # noqa: ARG001 — Django's checks framework calls this by keyword (app_configs=...)
    **_kwargs: object,
) -> list[CheckMessage]:
    """PROTECTED_MEDIA_ROOT must be set and lie outside every served directory."""
    protected = _resolved(getattr(settings, "PROTECTED_MEDIA_ROOT", None))
    if protected is None:
        return [
            Error(
                "PROTECTED_MEDIA_ROOT is not set.",
                hint="Set it to a directory no web server serves.",
                id="prototype.E001",
            )
        ]
    errors: list[CheckMessage] = []
    for name in ("MEDIA_ROOT", "STATIC_ROOT"):
        served = _resolved(getattr(settings, name, None))
        if served is not None and protected.is_relative_to(served):
            errors.append(
                Error(
                    f"PROTECTED_MEDIA_ROOT ({protected}) lies inside "
                    f"{name} ({served}).",
                    hint=(
                        "A web server serving that directory would hand out "
                        "protected files without any permission check. Move "
                        "PROTECTED_MEDIA_ROOT outside it."
                    ),
                    id="prototype.E002",
                )
            )
    return errors


def check_protected_media_server(
    app_configs: Sequence[AppConfig] | None = None,  # noqa: ARG001 — Django's checks framework calls this by keyword (app_configs=...)
    **_kwargs: object,
) -> list[CheckMessage]:
    """PROTECTED_MEDIA_SERVER must name a supported delivery mode."""
    from prototype.protected_media import SERVER_MODES

    mode = getattr(settings, "PROTECTED_MEDIA_SERVER", "django")
    if mode not in SERVER_MODES:
        return [
            Error(
                f"PROTECTED_MEDIA_SERVER is {mode!r}.",
                hint=f"Use one of: {', '.join(SERVER_MODES)}.",
                id="prototype.E003",
            )
        ]
    if mode == "x-accel-redirect" and not getattr(
        settings, "PROTECTED_MEDIA_ACCEL_PREFIX", ""
    ):
        return [
            Error(
                "PROTECTED_MEDIA_SERVER is 'x-accel-redirect' but "
                "PROTECTED_MEDIA_ACCEL_PREFIX is empty.",
                hint="Set it to the nginx internal location of PROTECTED_MEDIA_ROOT.",
                id="prototype.E004",
            )
        ]
    return []


def check_no_protected_files_in_media_root(
    app_configs: Sequence[AppConfig] | None = None,  # noqa: ARG001 — Django's checks framework calls this by keyword (app_configs=...)
    **_kwargs: object,
) -> list[CheckMessage]:
    """Warn about protected files still lying under MEDIA_ROOT.

    Versions before 2.0.2 stored them there. Until they are moved, a web
    server serving MEDIA_ROOT can still hand them out.
    """
    from prototype.protected_media import RULES

    media_root = _resolved(getattr(settings, "MEDIA_ROOT", None))
    if media_root is None or not media_root.is_dir():
        return []
    leftovers = [
        prefix
        for prefix in RULES
        if (media_root / prefix).is_dir()
        and any(p.is_file() for p in (media_root / prefix).rglob("*"))
    ]
    if not leftovers:
        return []
    return [
        CheckWarning(
            "Protected files still lie under MEDIA_ROOT in: "
            f"{', '.join(sorted(leftovers))}.",
            hint=(
                "Move them to the same relative paths under "
                "PROTECTED_MEDIA_ROOT."
            ),
            id="prototype.W001",
        )
    ]


def register_checks() -> None:
    """Register the checks above; called from PrototypeConfig.ready()."""
    register(check_protected_media_root, Tags.security)
    register(check_protected_media_server, Tags.security)
    register(
        check_no_protected_files_in_media_root, Tags.security, deploy=True
    )
