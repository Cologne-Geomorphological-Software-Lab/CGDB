"""Unit tests for raster_data.gdal_metadata's GDAL-based metadata extraction."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest
from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.gdal.error import GDALException

from raster_data.gdal_metadata import RasterMetadataError, read_raster_metadata


def _make_geotiff(
    path: str, *, srid: int, origin: tuple[float, float], scale: tuple[float, float],
    width: int = 4, height: int = 4, nr_of_bands: int = 2,
) -> None:
    """Write a tiny synthetic GeoTIFF with known georeferencing to *path*."""
    raster = GDALRaster(
        {
            "driver": "GTiff",
            "name": path,
            "width": width,
            "height": height,
            "srid": srid,
            "origin": list(origin),
            "scale": list(scale),
            "nr_of_bands": nr_of_bands,
        }
    )
    del raster  # flush/close so the file is fully written before reopening


@pytest.fixture
def tif_path() -> Iterator[str]:
    fd, path = tempfile.mkstemp(suffix=".tif")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestReadRasterMetadata:
    def test_reads_crs_bbox_and_band_count(self, tif_path: str) -> None:
        _make_geotiff(
            tif_path, srid=4326, origin=(6.0, 52.0), scale=(0.5, -0.5),
            width=4, height=4, nr_of_bands=3,
        )
        metadata = read_raster_metadata(tif_path)
        assert metadata.crs == "EPSG:4326"
        assert metadata.n_bands == 3
        assert metadata.spatial_bbox.extent == pytest.approx((6.0, 50.0, 8.0, 52.0))

    def test_reprojects_non_wgs84_raster_to_wgs84_bbox(self, tif_path: str) -> None:
        # UTM Zone 32N (EPSG:32632) — origin/scale in metres, not degrees.
        _make_geotiff(
            tif_path, srid=32632, origin=(500000.0, 5600000.0), scale=(1000.0, -1000.0),
            width=4, height=4,
        )
        metadata = read_raster_metadata(tif_path)
        assert metadata.crs == "EPSG:32632"
        # Reprojected extent should land somewhere in central Europe, not in
        # raw UTM metre coordinates.
        minx, miny, maxx, maxy = metadata.spatial_bbox.extent
        assert 0 < minx < 20
        assert 40 < miny < 60

    def test_raises_on_nonexistent_file(self) -> None:
        with pytest.raises(RasterMetadataError):
            read_raster_metadata("/no/such/file/does_not_exist.tif")

    def test_raises_on_non_raster_file(self, tif_path: str) -> None:
        with open(tif_path, "w") as fh:  # noqa: PTH123
            fh.write("this is not a raster file")
        with pytest.raises(RasterMetadataError):
            read_raster_metadata(tif_path)

    def test_wraps_gdalexception_from_post_open_attribute_read(
        self, tif_path: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """tech debt R3: GDALException raised by GDAL *after* a successful
        open (e.g. reading .bands) must still surface as RasterMetadataError,
        not propagate uncaught and abort the admin action's whole batch."""
        _make_geotiff(
            tif_path, srid=4326, origin=(6.0, 52.0), scale=(0.5, -0.5),
        )

        def _raise(self: GDALRaster) -> list[object]:
            msg = "simulated GDAL failure reading band count"
            raise GDALException(msg)

        monkeypatch.setattr(GDALRaster, "bands", property(_raise))
        with pytest.raises(RasterMetadataError):
            read_raster_metadata(tif_path)
