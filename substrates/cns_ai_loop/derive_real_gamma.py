#!/usr/bin/env python3
"""CNS-AI Loop — DATA SOURCE NON-EXISTENT (downgraded 2026-04-14).

================================================================
SUBSTRATE DOWNGRADE NOTICE
================================================================

This module previously derived a γ estimate from "CNS-AI session
data" on the path below. The substrate claim was downgraded to
``falsified_downgraded`` on 2026-04-14 per
``docs/CLAIM_BOUNDARY_CNS_AI.md``. Reasons:

1. The archive that produced the headline ``n=8271`` does not
   exist as a reproducible corpus. It was a scan of the owner's
   local workspace at a specific point in time; that workspace
   state is not preserved.
2. The unit of analysis in the surviving report is file-system
   entries classified by extension (``.py``, ``.odt``, ``.md``,
   ``.txt``, ``.json``) — a category error relative to the
   substrate's nominal claim about human-AI cognitive loops.

Path mismatch is canonised in
``docs/protocols/CNS_AI_PATH_CONTRACT.md``. The loader below no
longer attempts a silent fallback; it raises
``CorpusNotFoundError`` with a pointer at the canonical boundary
document.

The historical shape of the loader — latency-CV × n as topo,
1/accuracy as cost — is retained in the body of this file for
archival reference only. It does NOT execute against any
extant corpus.

================================================================
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CANON_BOUNDARY = _REPO_ROOT / "docs" / "CLAIM_BOUNDARY_CNS_AI.md"
_PATH_CONTRACT = _REPO_ROOT / "docs" / "protocols" / "CNS_AI_PATH_CONTRACT.md"


class CorpusNotFoundError(FileNotFoundError):
    """Raised when the CNS-AI corpus is requested — it does not exist.

    The substrate was downgraded on 2026-04-14 because the corpus
    that produced ``γ=1.059, n=8271`` is non-reproducible (see
    ``docs/CLAIM_BOUNDARY_CNS_AI.md``). No silent fallback is
    permitted; every caller MUST handle this exception explicitly,
    typically by downgrading its own claim or refusing to proceed.
    """


def load_sessions() -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Deprecated: raises ``CorpusNotFoundError`` by contract.

    Historically this walked ``substrates/cns_ai_loop/evidence/sessions/``
    expecting ``session_*/analysis.json`` with statistics from a
    session collector. That directory never contained the 8271
    files counted in ``xform_full_archive_gamma_report.json``, and
    the actual workspace scan that produced them is not preserved.
    See ``docs/protocols/CNS_AI_PATH_CONTRACT.md`` §2–§3.
    """

    raise CorpusNotFoundError(
        "CNS-AI corpus is non-reproducible. The substrate has been "
        f"downgraded to 'falsified_downgraded'. See {_CANON_BOUNDARY} "
        f"for the boundary contract and {_PATH_CONTRACT} for the "
        "frozen record of the path mismatch. Callers MUST NOT attempt "
        "to fall back to any other path; doing so reintroduces the "
        "category error that triggered the downgrade."
    )


def compute_gamma(
    points: list[tuple[float, float]], label: str
) -> dict | None:  # pragma: no cover - no corpus to exercise
    """Deprecated: the CNS-AI γ derivation pipeline is no longer executed.

    Retained as a function signature for archival reference only.
    Any invocation with non-empty points is meaningless because the
    corpus they were supposed to come from does not exist. Invoking
    this function directly is not prohibited, but the returned γ
    has no evidential standing under
    ``docs/CLAIM_BOUNDARY_CNS_AI.md``.
    """

    _ = points, label
    raise CorpusNotFoundError(
        "compute_gamma() is disabled. CNS-AI substrate is downgraded. "
        f"See {_CANON_BOUNDARY}."
    )


def main() -> int:
    """CLI entry — always fails loud with the downgrade notice."""

    print(
        "CNS-AI substrate is DOWNGRADED (falsified_downgraded).",
        file=sys.stderr,
    )
    print(
        f"See {_CANON_BOUNDARY.relative_to(_REPO_ROOT)} for the "
        "boundary contract.",
        file=sys.stderr,
    )
    print(
        f"See {_PATH_CONTRACT.relative_to(_REPO_ROOT)} for the "
        "frozen path-mismatch record.",
        file=sys.stderr,
    )
    print(
        "This script no longer derives γ. No silent fallback.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
