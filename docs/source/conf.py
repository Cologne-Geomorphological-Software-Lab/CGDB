"""Sphinx configuration for the CGDB documentation.

Pages are written in Markdown (MyST). The model reference uses autodoc, so
Django is set up with the project settings; a prototype/local_settings.py
with a SECRET_KEY must exist (CI writes a throwaway one).
"""

import os
import sys
import tomllib
from pathlib import Path

import django
from docutils import nodes
from docutils.parsers.rst import roles

# Some docstrings use Django admindocs roles such as :model:; render them
# as literal text instead of failing the build.
roles.register_generic_role("model", nodes.literal)

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prototype.settings")
django.setup()

with (ROOT_DIR / "pyproject.toml").open("rb") as f:
    _pyproject = tomllib.load(f)

# -- Project information -----------------------------------------------------

project = "CGDB"
author = "Dennis Handy, W. Marijn Van der Meij"
copyright = f"2026, {author}"
release = _pyproject["project"]["version"]
version = release

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_rtd_theme",
]

source_suffix = {".md": "markdown"}
root_doc = "index"
exclude_patterns = ["_build", "build"]

myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 3

autodoc_member_order = "bysource"
autodoc_default_options = {"members": True, "undoc-members": False}
# Model docstrings list their fields under "Attributes:"; as :ivar: entries
# they don't collide with the field attributes autodoc documents itself.
napoleon_use_ivar = True
# Same for "Methods:" sections, which would otherwise repeat save()/clean().
napoleon_custom_sections = [("Methods", "params_style")]

# -- HTML output -------------------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_title = f"CGDB {release}"
html_logo = None
html_theme_options = {"navigation_depth": 3}
html_context = {
    "display_github": True,
    "github_user": "Cologne-Geomorphological-Software-Lab",
    "github_repo": "CGDB",
    "github_version": "main",
    "conf_py_path": "/docs/source/",
}
