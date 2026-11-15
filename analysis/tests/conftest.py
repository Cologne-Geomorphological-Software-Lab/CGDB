import pytest


@pytest.fixture(autouse=True)
def _isolated_media_root(settings, tmp_path):
    """Redirect both media roots to per-test temp dirs.

    FileField uploads then never land in the source tree. The two are
    siblings, as the protected-media system check requires.
    """
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.PROTECTED_MEDIA_ROOT = str(tmp_path / "protected")
