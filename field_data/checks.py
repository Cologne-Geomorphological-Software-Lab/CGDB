"""System check for the coordinate transform behind Location.save().

A PROJ installation that cannot find its data directory, for example because
PROJ_DATA points at another program's copy, fails only when a location with
a non-WGS 84 CRS is saved. This check reports it at startup instead (#249).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.gis.gdal import GDALException
from django.contrib.gis.geos import Point
from django.core.checks import Error, Tags, register

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.apps import AppConfig
    from django.core.checks import CheckMessage

_PROBE_SRID = 32634  # UTM zone 34N, the case reported in #249
_WGS84 = 4326


def check_coordinate_transform(
    app_configs: Sequence[AppConfig] | None = None,  # noqa: ARG001 — Django's checks framework calls this by keyword (app_configs=...)
    **_kwargs: object,
) -> list[CheckMessage]:
    """PROJ must be able to transform a UTM point to WGS 84."""
    try:
        Point(500000, 5200000, srid=_PROBE_SRID).transform(_WGS84)
    except GDALException as exc:
        return [
            Error(
                f"PROJ cannot transform coordinates from EPSG:{_PROBE_SRID} "
                f"to WGS 84: {exc}",
                hint=(
                    "Check the PROJ installation and the PROJ_DATA and "
                    "PROJ_LIB environment variables. Saving a location with "
                    "a CRS other than WGS 84 fails until this works."
                ),
                id="field_data.E001",
            )
        ]
    return []


def register_checks() -> None:
    """Register the field_data checks (called from FieldDataConfig.ready)."""
    register(check_coordinate_transform, Tags.compatibility)
