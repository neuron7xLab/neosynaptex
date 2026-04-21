"""neosynaptex-probe — dialogue substrate adapter for neosynaptex.

Exposes:
- ``DialogueAdapter`` (``domain = "dialogue"``) conforming to
  ``neosynaptex.DomainAdapter`` protocol.
- ``ProbeSession`` wrapping ``Neosynaptex.observe()`` for session-level
  gamma trajectories, never storing gamma internally.
- Anti-tautology battery (AT-1..AT-4) and falsification battery with
  an explicit null-result contract.
- JSONL ingestion with fail-closed validation (rejected sessions are
  logged, never silently dropped).

The probe is an experimental substrate in the neosynaptex family; it
extends the existing LM substrate null result (gamma = -0.094,
p = 0.626) with real human-AI dialogue data, and refuses to promote
any result into ``evidence/scientific/`` unless the anti-tautology
battery passes.
"""

from __future__ import annotations

from probe.anti_tautology import AntiTautologyResult, run_anti_tautology
from probe.dialogue_adapter import DialogueAdapter, Turn
from probe.falsification import FalsificationResult, run_falsification
from probe.ingestion import IngestionError, SessionRecord, ingest_jsonl
from probe.session import (
    MIN_TURNS,
    InsufficientDataError,
    ProbeSession,
    load_seed_ledger,
    log_seed,
)

__all__ = [
    "MIN_TURNS",
    "AntiTautologyResult",
    "DialogueAdapter",
    "FalsificationResult",
    "IngestionError",
    "InsufficientDataError",
    "ProbeSession",
    "SessionRecord",
    "Turn",
    "ingest_jsonl",
    "load_seed_ledger",
    "log_seed",
    "run_anti_tautology",
    "run_falsification",
]

__version__ = "0.1.0"
