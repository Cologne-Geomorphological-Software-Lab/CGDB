"""Project-level pytest configuration.

On Windows, OSGeo4W GDAL/GEOS/PROJ DLLs must be registered via
os.add_dll_directory() *before* Django/GeoDjango is set up, otherwise
ctypes cannot resolve transitive dependencies (WinError 127).

pytest_configure runs before pytest-django calls django.setup(), so
this is the right hook to place the DLL directory registration.
"""
import os
import sys
from pathlib import Path


def pytest_configure(config):
    _osgeo_bin = Path("C:/OSGeo4W/bin")
    if sys.platform == "win32" and _osgeo_bin.exists():
        _bin_str = str(_osgeo_bin)
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(_bin_str)
        if _bin_str not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _bin_str + os.pathsep + os.environ.get("PATH", "")
        os.environ.setdefault("PROJ_LIB", "C:/OSGeo4W/share/proj")
