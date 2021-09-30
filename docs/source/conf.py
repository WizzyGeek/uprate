# type: ignore
# ^ This file should not linted as it is a config file.

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

from pathlib import Path

# -- Project information -----------------------------------------------------

project = 'Uprate'
copyright = '2021, WizzyGeek'
author = 'WizzyGeek'

# The full version, including alpha/beta/rc tags

try:
    from uprate import __version__ as release
except (ModuleNotFoundError, ImportError):
    release = None

    with (Path(__file__).parents[2] / "pyproject.toml").open("r") as f:
        for i in f.readlines():
            if "version" in i:
                release = i.split("=")[1].strip('" \n')
                break

if release is None: # fail early
    raise RuntimeError("Could not get uprate's version")


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "myst_parser",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx_copybutton"
]

autodoc_member_order = 'bysource'

napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}


# MyST extensions
myst_enable_extensions = [
    "colon_fence"
]

suppress_warnings = ["myst.header"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relat ive to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

html_theme = 'furo'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_logo = "_static/uprate_icon.png"

html_theme_options = {
    "dark_css_variables": {
        "color-api-keyword": "#40ffff",
        "color-background-primary": "#0c0e11",
        "color-background-secondary": "#020202"
    }
}

_up_static = Path(__file__).parent / "_static"

# Use css files in _static if present,
# This will only happen in a dev environment where
# scss is being watched.
def _up_css_path(file: str) -> str:
    if (_up_static / file).is_file():
        return file
    return "css/" + file

def setup(app):
    app.add_css_file(_up_css_path("custom.css"))
