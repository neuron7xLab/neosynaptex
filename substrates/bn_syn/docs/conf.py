from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))  # for top-level tools/ package used by bnsyn.qa

project = "BN-Syn"
author = "BN-Syn Contributors"
copyright = f"{datetime.now().year}, {author}"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]

autosummary_generate = True

autodoc_typehints = "description"
autodoc_typehints_description_target = "all"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}

napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_param = True
napoleon_use_rtype = True

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

templates_path = ["api/_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = ["api/_static"]
html_title = "BN-Syn Documentation"
html_theme_options = {
    "sidebar_hide_name": True,
}

nitpicky = False

os.environ.setdefault("PYTHONUTF8", "1")
