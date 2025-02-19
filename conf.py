"""Sphinx configuration."""

project = "SSB Project CLI"
author = "Statistics Norway"
copyright = "2022, Statistics Norway"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_click",
    "myst_parser",
]
source_suffix = [".md", ".rst"]
autodoc_typehints = "description"
html_theme = "furo"
