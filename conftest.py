"""Project-level pytest configuration.

On Windows, OSGeo4W GDAL/GEOS/PROJ DLLs must be registered via
os.add_dll_directory() *before* Django/GeoDjango is set up, otherwise
ctypes cannot resolve transitive dependencies (WinError 127).

pytest_configure runs before pytest-django calls django.setup(), so
this is the right hook to place the DLL directory registration.

prototype/test_settings.py creates a temporary MEDIA_ROOT and
PROTECTED_MEDIA_ROOT per session, so that FileField uploads do not
accumulate inside the source tree; pytest_sessionfinish removes them. (The
settings must create them: pytest-django loads the settings before this
file's pytest_configure runs, so an environment variable set here comes too
late.)
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


def pytest_configure(config) -> None:
    """Register OSGeo4W DLLs before Django setup."""
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


def pytest_sessionfinish(session, exitstatus) -> None:
    """Remove the temporary media directories created by test_settings.py."""
    from django.conf import settings

    for name in ("MEDIA_ROOT", "PROTECTED_MEDIA_ROOT"):
        path = str(getattr(settings, name, "") or "")
        if Path(path).name.startswith("cgdb_test_"):
            shutil.rmtree(path, ignore_errors=True)


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
