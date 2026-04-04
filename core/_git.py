"""Git utilities — shared across modules that need commit SHA.

Single source of truth for git operations used by:
  - core.coherence_bridge
  - core.evidence_pipeline

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

import subprocess  # nosec B404 — used only for hardcoded git command


def get_short_sha() -> str:
    """Return short git SHA of HEAD, or 'unknown' if unavailable."""
    try:
        result = subprocess.run(  # nosec B603 B607 — hardcoded git command, no user input
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


__all__ = ["get_short_sha"]
