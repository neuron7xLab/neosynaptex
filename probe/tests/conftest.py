"""Test fixtures & sys.path wiring for probe tests.

The probe package lives in ``probe/src/probe/`` and imports
``neosynaptex`` as a sibling module that lives at the neosynaptex repo
root (single-file module: ``<repo>/neosynaptex.py``). When running
``pytest`` from inside ``probe/``, neither path is on ``sys.path`` by
default. We inject both here so tests work regardless of whether the
probe has been installed via ``pip install -e`` or not.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROBE_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _PROBE_DIR.parent

for p in (_PROBE_DIR / "src", _REPO_ROOT):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)
