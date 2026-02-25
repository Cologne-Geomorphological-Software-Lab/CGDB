# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(".."))
# Pfad zum Projekt-Root (da, wo manage.py liegt)
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

# Django-Settings setzen
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prototype.settings")

import django

django.setup()

os.environ["DJANGO_SETTINGS_MODULE"] = "prototype.settings"
django.setup()

project = "CGDB"
copyright = "2026, Dennis Handy, W. Marijn Van der Meij"
author = "Dennis Handy, W. Marijn Van der Meij"
release = "1.1.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # For Google and NumPy style docstrings
    "sphinx.ext.viewcode",  # Optional: to include links to source code
    "sphinx_rtd_theme",
]

templates_path = ["_templates"]
exclude_patterns = ["migrations"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]

html_theme = "sphinx_rtd_theme"
