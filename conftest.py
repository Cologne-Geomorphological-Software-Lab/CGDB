"""Project-level pytest configuration.

On Windows, OSGeo4W GDAL/GEOS/PROJ DLLs must be registered via
os.add_dll_directory() *before* Django/GeoDjango is set up, otherwise
ctypes cannot resolve transitive dependencies (WinError 127).

pytest_configure runs before pytest-django calls django.setup(), so
this is the right hook to place the DLL directory registration.

A temporary MEDIA_ROOT is created per session so that FileField uploads
do not accumulate inside the source tree. It is cleaned up automatically
in pytest_sessionfinish.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

_TEST_MEDIA_ROOT: str | None = None


def pytest_configure(config) -> None:
    global _TEST_MEDIA_ROOT

    # -- OSGeo4W DLL registration (Windows only) --
    _osgeo_bin = Path("C:/OSGeo4W/bin")
    if sys.platform == "win32" and _osgeo_bin.exists():
        _bin_str = str(_osgeo_bin)
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(_bin_str)
        if _bin_str not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _bin_str + os.pathsep + os.environ.get("PATH", "")
        os.environ.setdefault("PROJ_LIB", "C:/OSGeo4W/share/proj")

    # -- Isolated media root --
    # Set an env var so test_settings.py can pick it up before Django initialises.
    _TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="cgdb_test_media_")
    os.environ["CGDB_TEST_MEDIA_ROOT"] = _TEST_MEDIA_ROOT


def pytest_sessionfinish(session, exitstatus) -> None:
    if _TEST_MEDIA_ROOT:
        shutil.rmtree(_TEST_MEDIA_ROOT, ignore_errors=True)
