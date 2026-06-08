import pytest


@pytest.fixture(autouse=True)
def _isolated_media_root(settings, tmp_path):
    """Redirect MEDIA_ROOT to a per-test temp dir so FileField uploads never land in the source tree."""
    settings.MEDIA_ROOT = str(tmp_path)
