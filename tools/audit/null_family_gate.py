"""Mandatory auditor gate around the null-family screening result.

The null-family screening protocol (``run_null_family_screening.py``)
is the top-level falsification budget for the Delta-h + surrogate line.
Its verdicts are:

* ``NULL_FAMILY_SELECTED``   -- an admissible null was found. OK.
* ``NO_ADMISSIBLE_NULL_FOUND`` -- no null survived preflight. BLOCKING.
* ``IMPLEMENTATION_BLOCKED`` -- protocol could not run. BLOCKING.

Until this patch the auditor orchestrator did not include the null
screening in its ``TOOLS`` registry at all; a missing gate silently
passed. This module exposes a single ``run_check()`` entry point that:

1. Reads the cached screening result written by the canonical runner.
2. Returns ``(0, msg)`` iff the verdict is ``NULL_FAMILY_SELECTED``.
3. Returns ``(2, msg)`` on every other path -- including
   "results file does not exist", because a missing mandatory gate
   is a FAIL, not a skip (see ``contracts/fail_closed.py``).

Callers in the auditor wire this tool with ``mandatory=True``; the
auditor's mandatory-skip semantics convert any import failure or
absence into a blocking FAIL.
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Any

__all__ = ["run_check", "RESULTS_JSON_ENV", "DEFAULT_RESULTS_JSON"]

# Canonical on-disk location produced by ``run_null_family_screening.py``.
DEFAULT_RESULTS_JSON = pathlib.Path("evidence/replications/hrv_null_screening") / (
    "null_screening_results.json"
)

# Tests and CI can override the path via this environment variable; that
# keeps the gate side-effect-free and deterministic under tmp paths.
RESULTS_JSON_ENV = "NEOSYNAPTEX_NULL_SCREENING_RESULTS"


def _resolve_results_path() -> pathlib.Path:
    override = os.environ.get(RESULTS_JSON_ENV)
    if override:
        return pathlib.Path(override)
    return DEFAULT_RESULTS_JSON


def _load_payload(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def run_check() -> tuple[int, str]:
    """Mandatory auditor entry point.

    Returns a ``(exit_code, message)`` tuple using the auditor's
    verifier-style protocol: ``exit_code == 0`` iff the cached null
    screening produced ``NULL_FAMILY_SELECTED``; every other outcome
    (including absent / unreadable / malformed cache) returns ``2``.
    """

    path = _resolve_results_path()
    if not path.exists():
        return (
            2,
            f"null_family_gate: cache absent at {path} -- mandatory evidence missing",
        )

    payload = _load_payload(path)
    if payload is None:
        return (2, f"null_family_gate: cache {path} is unreadable or malformed JSON")

    verdict = payload.get("VERDICT") or payload.get("verdict")
    if not isinstance(verdict, str):
        return (2, f"null_family_gate: cache {path} has no VERDICT field")

    chosen = payload.get("chosen_family")
    if verdict == "NULL_FAMILY_SELECTED":
        return (0, f"null_family_gate: admissible null selected (family={chosen!r})")

    if verdict == "NO_ADMISSIBLE_NULL_FOUND":
        return (
            2,
            "null_family_gate: NO_ADMISSIBLE_NULL_FOUND -- blocking global success",
        )

    return (2, f"null_family_gate: blocking verdict={verdict!r}")
