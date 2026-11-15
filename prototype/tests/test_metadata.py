"""The release version is stated the same way everywhere (#209).

pyproject.toml (read by importlib.metadata, uv build and the docs),
CITATION.cff (read by GitHub and Zenodo) and the newest released section of
CHANGELOG.md must name the same version, so tag and package can't drift
apart again.
"""

import re
import tomllib
from pathlib import Path

from django.test import SimpleTestCase

_ROOT = Path(__file__).resolve().parents[2]


def _pyproject_version() -> str:
    with (_ROOT / "pyproject.toml").open("rb") as file:
        return tomllib.load(file)["project"]["version"]


def _citation_version() -> str:
    text = (_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*\"?([^\"\s]+)\"?\s*$", text, re.MULTILINE)
    assert match, "CITATION.cff has no version line"
    return match.group(1)


def _latest_changelog_version() -> str:
    text = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(r"^## \[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)
    assert match, "CHANGELOG.md has no released version section"
    return match.group(1)


class ReleaseVersionTest(SimpleTestCase):
    def test_version_is_semantic(self):
        self.assertRegex(_pyproject_version(), r"^\d+\.\d+\.\d+$")

    def test_pyproject_and_citation_agree(self):
        self.assertEqual(_pyproject_version(), _citation_version())

    def test_latest_changelog_section_is_the_current_version(self):
        self.assertEqual(_pyproject_version(), _latest_changelog_version())
