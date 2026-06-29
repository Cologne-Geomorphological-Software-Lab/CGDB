"""Management command to import Murphy Landform Regions from a GeoJSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand, CommandError

from geodata.models import Landform

if TYPE_CHECKING:
    from argparse import ArgumentParser

BATCH_SIZE = 500
DEFAULT_SOURCE = "Murphy Landform Regions ESRI 2022"


def _str(val: object, max_len: int = 255) -> str:
    """Return val as a trimmed string, empty string for None."""
    if val is None:
        return ""
    return str(val)[:max_len]


class Command(BaseCommand):
    """Import Murphy Landform Regions from a GeoJSON file into the Landform table."""

    help = (
        "Import Murphy Landform Regions from a GeoJSON file. "
        "Clears existing rows unless --no-clear is passed."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Register CLI arguments."""
        parser.add_argument(
            "geojson",
            type=Path,
            help="Path to the landforms GeoJSON file.",
        )
        parser.add_argument(
            "--source",
            default=DEFAULT_SOURCE,
            help=f'Value for the source field (default: "{DEFAULT_SOURCE}").',
        )
        parser.add_argument(
            "--no-clear",
            action="store_true",
            help="Skip truncating the table before import (append instead).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=BATCH_SIZE,
            help=f"Rows per bulk_create call (default: {BATCH_SIZE}).",
        )

    def handle(self, *_args: object, **options: object) -> None:
        """Run the import."""
        path: Path = options["geojson"]  # type: ignore[assignment]
        if not path.exists():
            msg = f"File not found: {path}"
            raise CommandError(msg)

        self.stdout.write(f"Reading {path} …")
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)

        features = data.get("features", [])
        total = len(features)
        self.stdout.write(f"  {total:,} features found.")

        if not options["no_clear"]:
            deleted, _ = Landform.objects.all().delete()
            self.stdout.write(f"  Cleared {deleted:,} existing rows.")

        source: str = options["source"]  # type: ignore[assignment]
        batch_size: int = options["batch_size"]  # type: ignore[assignment]
        batch: list[Landform] = []
        created = 0
        skipped = 0

        for _i, feat in enumerate(features):
            props = feat.get("properties") or {}
            geom_json = feat.get("geometry")

            if geom_json is None:
                skipped += 1
                continue

            try:
                geometry = GEOSGeometry(json.dumps(geom_json), srid=4326)
            except Exception:  # noqa: BLE001
                skipped += 1
                continue

            batch.append(
                Landform(
                    geometry=geometry,
                    brid_nam=_str(props.get("BridNam"), 500),
                    name_str=_str(props.get("NameStr")),
                    division=_str(props.get("Division")),
                    province=_str(props.get("Province")),
                    section=_str(props.get("Section")),
                    continent=_str(props.get("Continent"), 100),
                    murphy_code=_str(props.get("MurphyCode"), 10),
                    structure=props.get("Structure"),
                    moist_dry=props.get("MoistDry"),
                    topog=props.get("Topog"),
                    process=props.get("process"),
                    glaciate=_str(props.get("Glaciate"), 100),
                    volcanism=_str(props.get("Volcanism")),
                    volc_name=_str(props.get("VolcName")) or None,
                    si_vol_num=_str(props.get("SI_Vol_Num"), 50) or None,
                    vol_reg=_str(props.get("Vol_Reg")) or None,
                    vol_prov=_str(props.get("Vol_Prov")) or None,
                    plate_1=_str(props.get("Plate_1"), 100),
                    plate_2=_str(props.get("Plate_2"), 100),
                    plate_3=_str(props.get("Plate_3"), 100),
                    plate_4=_str(props.get("Plate_4"), 100),
                    plate_5=_str(props.get("Plate_5"), 100),
                    notes=_str(props.get("notes"), 10000),
                    area_geo=props.get("AREA_GEO"),
                    shape_length=props.get("Shape_Length"),
                    shape_area=props.get("Shape_Area"),
                    source=source,
                )
            )

            if len(batch) >= batch_size:
                Landform.objects.bulk_create(batch)
                created += len(batch)
                batch = []
                self.stdout.write(
                    f"  {created:,}/{total:,} imported …", ending="\r"
                )
                self.stdout.flush()

        if batch:
            Landform.objects.bulk_create(batch)
            created += len(batch)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {created:,} rows imported, {skipped:,} skipped."
            )
        )
