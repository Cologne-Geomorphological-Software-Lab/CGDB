"""Tests for the import_landforms management command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.contrib.gis.geos import GEOSGeometry
from django.core.management import call_command

from geodata.models import Landform

_POLY_A = {
    "type": "MultiPolygon",
    "coordinates": [
        [[[6.0, 50.0], [8.0, 50.0], [8.0, 52.0], [6.0, 52.0], [6.0, 50.0]]],
    ],
}
_POLY_B = {
    "type": "MultiPolygon",
    "coordinates": [
        [[[10.0, 20.0], [11.0, 20.0], [11.0, 21.0], [10.0, 21.0], [10.0, 20.0]]],
    ],
}


def _feature(geometry: dict | None, **props: object) -> dict:
    return {"type": "Feature", "geometry": geometry, "properties": props}


def _write_geojson(tmp_path: Path, features: list[dict]) -> Path:
    path = tmp_path / "landforms.geojson"
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}),
        encoding="utf-8",
    )
    return path


@pytest.mark.django_db
def test_import_creates_landforms(tmp_path: Path) -> None:
    """Valid features are imported, one Landform row per feature."""
    geojson = _write_geojson(
        tmp_path,
        [
            _feature(_POLY_A, BridNam="Region A", Continent="Europe"),
            _feature(_POLY_B, BridNam="Region B", Continent="Asia"),
        ],
    )
    call_command("import_landforms", str(geojson))
    assert Landform.objects.count() == 2
    assert set(Landform.objects.values_list("brid_nam", flat=True)) == {
        "Region A",
        "Region B",
    }


@pytest.mark.django_db
def test_import_skips_feature_with_null_geometry(tmp_path: Path) -> None:
    """A feature with geometry=None is skipped, not imported, no crash."""
    geojson = _write_geojson(
        tmp_path,
        [
            _feature(_POLY_A, BridNam="Region A"),
            _feature(None, BridNam="No Geometry"),
        ],
    )
    call_command("import_landforms", str(geojson))
    assert Landform.objects.count() == 1
    assert Landform.objects.get().brid_nam == "Region A"


@pytest.mark.django_db
def test_import_skips_feature_with_malformed_geometry(tmp_path: Path) -> None:
    """A structurally invalid geometry (GDALException, not GEOSException) is
    skipped gracefully rather than crashing the whole import."""
    geojson = _write_geojson(
        tmp_path,
        [
            _feature(_POLY_A, BridNam="Region A"),
            _feature(
                {"type": "Polygon", "coordinates": "garbage"},
                BridNam="Malformed Region",
            ),
        ],
    )
    call_command("import_landforms", str(geojson))
    assert Landform.objects.count() == 1
    assert Landform.objects.get().brid_nam == "Region A"


@pytest.mark.django_db
def test_import_logs_skip_reason_for_null_geometry(tmp_path: Path) -> None:
    """tech debt LBG14: a skipped feature must log which one and why, not
    just a bare final count."""
    from io import StringIO

    geojson = _write_geojson(
        tmp_path, [_feature(None, BridNam="No Geometry Region")]
    )
    err = StringIO()
    call_command("import_landforms", str(geojson), stderr=err)
    output = err.getvalue()
    assert "No Geometry Region" in output
    assert "no geometry" in output


@pytest.mark.django_db
def test_import_logs_skip_reason_for_malformed_geometry(
    tmp_path: Path,
) -> None:
    from io import StringIO

    geojson = _write_geojson(
        tmp_path,
        [
            _feature(
                {"type": "Polygon", "coordinates": "garbage"},
                BridNam="Malformed Region",
            )
        ],
    )
    err = StringIO()
    call_command("import_landforms", str(geojson), stderr=err)
    output = err.getvalue()
    assert "Malformed Region" in output
    assert "invalid geometry" in output


@pytest.mark.django_db
def test_import_failure_rolls_back_the_whole_batch(tmp_path: Path) -> None:
    """tech debt LBG15: a failure partway through must not leave the table
    cleared or partially repopulated - the previous data must survive
    untouched."""
    from unittest.mock import patch

    Landform.objects.create(
        geometry=GEOSGeometry(json.dumps(_POLY_A), srid=4326),
        brid_nam="Pre-existing Row",
    )
    geojson = _write_geojson(
        tmp_path,
        [
            _feature(_POLY_A, BridNam="A"),
            _feature(_POLY_B, BridNam="B"),
        ],
    )
    with patch.object(
        Landform.objects, "bulk_create", side_effect=RuntimeError("boom")
    ):
        with pytest.raises(RuntimeError):
            call_command("import_landforms", str(geojson))

    assert Landform.objects.count() == 1
    assert Landform.objects.get().brid_nam == "Pre-existing Row"


@pytest.mark.django_db
def test_import_default_clears_existing_rows(tmp_path: Path) -> None:
    """Without --no-clear, pre-existing rows are truncated before import."""
    Landform.objects.create(
        geometry=GEOSGeometry(json.dumps(_POLY_A), srid=4326),
        brid_nam="Stale Row",
    )
    geojson = _write_geojson(tmp_path, [_feature(_POLY_B, BridNam="Fresh Row")])
    call_command("import_landforms", str(geojson))
    assert Landform.objects.count() == 1
    assert Landform.objects.get().brid_nam == "Fresh Row"


@pytest.mark.django_db
def test_import_no_clear_appends_to_existing_rows(tmp_path: Path) -> None:
    """--no-clear preserves existing rows and appends the new ones."""
    Landform.objects.create(
        geometry=GEOSGeometry(json.dumps(_POLY_A), srid=4326),
        brid_nam="Existing Row",
    )
    geojson = _write_geojson(tmp_path, [_feature(_POLY_B, BridNam="New Row")])
    call_command("import_landforms", str(geojson), "--no-clear")
    assert Landform.objects.count() == 2
    assert set(Landform.objects.values_list("brid_nam", flat=True)) == {
        "Existing Row",
        "New Row",
    }


@pytest.mark.django_db
def test_import_respects_batch_size_boundary(tmp_path: Path) -> None:
    """batch_size=1 forces a bulk_create per feature; all rows still land."""
    geojson = _write_geojson(
        tmp_path,
        [
            _feature(_POLY_A, BridNam="A"),
            _feature(_POLY_B, BridNam="B"),
            _feature(_POLY_A, BridNam="C"),
        ],
    )
    call_command("import_landforms", str(geojson), "--batch-size", "1")
    assert Landform.objects.count() == 3


@pytest.mark.django_db
def test_import_custom_source_value_propagates(tmp_path: Path) -> None:
    """--source overrides the default source value on every imported row."""
    geojson = _write_geojson(tmp_path, [_feature(_POLY_A, BridNam="A")])
    call_command("import_landforms", str(geojson), "--source", "Custom Source v1")
    assert Landform.objects.get().source == "Custom Source v1"


@pytest.mark.django_db
def test_import_reads_process_and_notes_in_pascal_case(tmp_path: Path) -> None:
    """tech debt LBG16: process/notes must read the source's PascalCase keys
    (Process/Notes), matching every other property in this file -- the old
    lowercase lookups left both columns empty on every import. process is a
    PositiveSmallIntegerField (a process code), like its Structure/MoistDry/
    Topog siblings -- not free text."""
    geojson = _write_geojson(
        tmp_path,
        [
            _feature(
                _POLY_A,
                BridNam="Region A",
                Process=3,
                Notes="Field-verified 2022",
            ),
        ],
    )
    call_command("import_landforms", str(geojson))
    landform = Landform.objects.get()
    assert landform.process == 3
    assert landform.notes == "Field-verified 2022"


@pytest.mark.django_db
def test_import_missing_file_raises_command_error(tmp_path: Path) -> None:
    """A nonexistent geojson path raises CommandError, not a raw exception."""
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("import_landforms", str(tmp_path / "does_not_exist.geojson"))
