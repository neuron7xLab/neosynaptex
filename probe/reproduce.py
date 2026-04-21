"""Engineering reproducibility check for neosynaptex-probe.

*** THIS SCRIPT PRODUCES SYNTHETIC DATA — NOT SCIENTIFIC EVIDENCE. ***

The purpose is to verify:
  * DialogueAdapter invariants (topo non-decreasing, cost strictly increasing)
  * ProbeSession <-> nx.observe() integration yields deterministic output
  * Anti-tautology battery runs end-to-end on two qualitatively distinct
    synthetic sessions (vocabulary-growing vs flat-vocabulary)

Scientific evidence requires real session data via ``probe.ingestion``
and belongs in ``evidence/scientific/``, produced only when the
anti-tautology battery passes (HARD RULE 4).

Any machine running this script with the same interpreter + library
versions must produce identical numbers to 6 decimal places.
"""

from __future__ import annotations

import json
import platform
import random
import string
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy

from probe.anti_tautology import run_anti_tautology
from probe.dialogue_adapter import Turn
from probe.session import ProbeSession, log_seed

SEED = 7
WINDOW = 16
N_TURNS = 24

ROOT = Path(__file__).resolve().parent
EVIDENCE_DIR = ROOT / "evidence" / "engineering"
SEED_LEDGER = ROOT / "seed_ledger.json"


def _versions() -> dict[str, str]:
    import neosynaptex  # local import — optional at module load

    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "neosynaptex": getattr(neosynaptex, "__version__", "unknown"),
    }


def _growing_vocabulary_session(seed: int, n: int) -> list[Turn]:
    """Synthetic session where every turn introduces new tokens.

    Matches the spec's "human_ai_synthetic" scenario: vocabulary grows
    approximately linearly with turns, token_count rises with each turn.
    """
    rng = random.Random(seed)
    turns: list[Turn] = []
    base_cost = 40
    for i in range(n):
        words = [_random_word(rng, size=rng.randint(4, 8)) for _ in range(10 + i)]
        content = " ".join(words)
        tokens = base_cost + 3 * i + rng.randint(0, 5)
        role = "human" if i % 2 == 0 else "assistant"
        turns.append(Turn(role=role, content=content, token_count=tokens))
    return turns


def _flat_vocabulary_session(seed: int, n: int) -> list[Turn]:
    """Synthetic session where vocabulary saturates quickly (LLM-only surrogate).

    Uses a fixed 8-word vocabulary. Matches the spec's "llm_only_synthetic"
    scenario.
    """
    rng = random.Random(seed ^ 0xDEAD)
    vocab = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]
    turns: list[Turn] = []
    base_cost = 40
    for i in range(n):
        words = [rng.choice(vocab) for _ in range(10 + i)]
        content = " ".join(words)
        tokens = base_cost + 3 * i + rng.randint(0, 5)
        role = "human" if i % 2 == 0 else "assistant"
        turns.append(Turn(role=role, content=content, token_count=tokens))
    return turns


def _random_word(rng: random.Random, size: int) -> str:
    return "".join(rng.choice(string.ascii_lowercase) for _ in range(size))


def _run_scenario(name: str, turns: list[Turn]) -> dict[str, object]:
    session = ProbeSession(window=WINDOW, seed=SEED, seed_ledger_path=SEED_LEDGER)
    for t in turns:
        session.push_turn(t)
    evidence = session.export_evidence()
    at = run_anti_tautology(session, seed=SEED)
    result_dict = asdict(at)
    # dataclass `notes` is a tuple -> make JSON friendly
    result_dict["notes"] = list(at.notes)
    return {
        "scenario": name,
        "label": "SYNTHETIC — engineering verification only",
        "evidence": evidence,
        "anti_tautology": result_dict,
        "gamma_trajectory_rounded": [round(g, 6) for g in evidence["gamma_trajectory"]],
    }


def main() -> int:
    print("=== ENGINEERING CORRECTNESS CHECK ===")
    print("This script verifies implementation, not scientific claims.")
    print("Scientific evidence requires real session data via ingestion.py")
    print()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_seed(SEED_LEDGER, SEED, f"reproduce-{timestamp}")

    scenarios = {
        "human_ai_synthetic": _growing_vocabulary_session(SEED, N_TURNS),
        "llm_only_synthetic": _flat_vocabulary_session(SEED, N_TURNS),
    }

    report: dict[str, object] = {
        "label": "SYNTHETIC — engineering verification only",
        "seed": SEED,
        "window": WINDOW,
        "n_turns": N_TURNS,
        "versions": _versions(),
        "timestamp_utc": timestamp,
        "scenarios": {name: _run_scenario(name, turns) for name, turns in scenarios.items()},
    }

    out_path = EVIDENCE_DIR / f"reproduce_{timestamp}.json"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Report written: {out_path}")

    # Terse stdout summary so CI logs stay readable.
    for name, data in report["scenarios"].items():  # type: ignore[union-attr]
        at = data["anti_tautology"]  # type: ignore[index]
        print(
            f"  {name}: gamma={at['gamma_original']:.6f} "
            f"passed={at['passed']} "
            f"flags=(T={at['tautology_flag']}, I={at['instability_flag']}, "
            f"O={at['outlier_flag']}, S={at['surrogate_flag']})"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
