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
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

_TEST_MEDIA_ROOT: str | None = None


def pytest_configure(config) -> None:
    """Register OSGeo4W DLLs and create an isolated MEDIA_ROOT before Django setup."""
    global _TEST_MEDIA_ROOT

    # -- OSGeo4W DLL registration (Windows only) --
    _osgeo_bin = Path("C:/OSGeo4W/bin")
    if sys.platform == "win32" and _osgeo_bin.exists():
        _bin_str = str(_osgeo_bin)
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(_bin_str)
        if _bin_str not in os.environ.get("PATH", ""):
            os.environ["PATH"] = (
                _bin_str + os.pathsep + os.environ.get("PATH", "")
            )
        os.environ.setdefault("PROJ_LIB", "C:/OSGeo4W/share/proj")

    # -- Isolated media root --
    # Set an env var so test_settings.py can pick it up before Django initialises.
    _TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="cgdb_test_media_")
    os.environ["CGDB_TEST_MEDIA_ROOT"] = _TEST_MEDIA_ROOT


def pytest_sessionfinish(session, exitstatus) -> None:
    """Remove the temporary MEDIA_ROOT after the test session completes."""
    if _TEST_MEDIA_ROOT:
        shutil.rmtree(_TEST_MEDIA_ROOT, ignore_errors=True)


@pytest.fixture(autouse=True)
def _reset_current_user_thread_local() -> Iterator[None]:
    """Reset CurrentUserMiddleware's thread-local between every test.

    Any test that issues a real HTTP request (Client.get/post, not just
    force_authenticate) runs the full middleware stack, including
    CurrentUserMiddleware — which stores request.user in a thread-local
    that otherwise outlives the test's DB transaction rollback. Without
    this reset, a later test's plain .objects.create() calls can silently
    pick up a stale, now-deleted user as created_by/updated_by (BaseModel.save()),
    causing FK integrity errors far from the test that actually caused them.
    """
    from prototype.middleware import _user

    _user.value = None
    yield
    _user.value = None
