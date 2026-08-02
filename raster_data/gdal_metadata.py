"""Read real georeferencing metadata off a raster file via GDAL.

Uses django.contrib.gis.gdal.GDALRaster rather than rasterio: the project
already carefully wires a single GDAL install via OSGeo4W (see
prototype/settings.py's GDAL_LIBRARY_PATH setup) — rasterio bundles its own
GDAL, risking a second, differently-versioned GDAL loading in the same
process. GDALRaster is already a transitive Django dependency, so this adds
no new package.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.geos import GEOSException, Polygon

_SRID_WGS84 = 4326


class RasterMetadataError(Exception):
    """Raised when a file can't be read as a georeferenced raster."""


@dataclass
class RasterMetadata:
    """Georeferencing metadata read off a raster file."""

    crs: str
    spatial_bbox: Polygon
    n_bands: int


def read_raster_metadata(path: str) -> RasterMetadata:
    """Read CRS, WGS-84 bounding box, and band count from a raster file on disk.

    Raises RasterMetadataError if the file can't be opened as a raster, or
    has no identifiable coordinate reference system.
    """
    try:
        raster = GDALRaster(path)
    except (GDALException, OSError) as exc:
        msg = f"Could not open {path!r} as a raster: {exc}"
        raise RasterMetadataError(msg) from exc

    srs = raster.srs
    if srs is None or srs.srid is None:
        msg = f"{path!r} has no identifiable coordinate reference system."
        raise RasterMetadataError(msg)

    bbox = Polygon.from_bbox(raster.extent)
    bbox.srid = srs.srid
    if srs.srid != _SRID_WGS84:
        try:
            bbox.transform(_SRID_WGS84)
        except GEOSException as exc:
            msg = f"Could not reproject {path!r}'s extent to WGS-84: {exc}"
            raise RasterMetadataError(msg) from exc

    return RasterMetadata(
        crs=f"EPSG:{srs.srid}",
        spatial_bbox=bbox,
        n_bands=len(raster.bands),
    )
