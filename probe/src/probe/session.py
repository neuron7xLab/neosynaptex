"""ProbeSession — thin wrapper around neosynaptex.observe() for dialogue."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from probe.dialogue_adapter import DialogueAdapter, Turn

if TYPE_CHECKING:  # pragma: no cover
    from neosynaptex import Neosynaptex, NeosynaptexState

# Minimum turns before gamma is meaningful. Derived from the neosynaptex
# window parameter: the engine requires >= 5 finite (topo, cost) pairs and
# non-trivial log-range before emitting a gamma value. We use 8 as a
# practical floor (matches engine default window=16 with ample margin).
MIN_TURNS: int = 8


class InsufficientDataError(RuntimeError):
    """Raised by ``ProbeSession.export_evidence`` below ``MIN_TURNS``."""


@dataclass(frozen=True)
class _SeedEntry:
    seed: int
    session_hash: str
    timestamp: str


class ProbeSession:
    """Wraps a ``Neosynaptex`` engine with a single ``DialogueAdapter``.

    Gamma is never stored on the session — each ``push_turn`` calls
    ``nx.observe()`` and returns the frozen ``NeosynaptexState`` snapshot.

    The session logs its seed to ``seed_ledger_path`` before any
    stochastic downstream operation can run (HARD RULE 8).
    """

    def __init__(
        self,
        window: int = 16,
        seed: int = 7,
        *,
        mode: str = "test",
        seed_ledger_path: Path | None = None,
    ) -> None:
        # Import at call time so unit tests that stub neosynaptex can work
        # without the full dependency being present at module import.
        from neosynaptex import Neosynaptex

        if window < 8:
            raise ValueError(f"window must be >= 8, got {window}")
        self._adapter = DialogueAdapter()
        self._nx: Neosynaptex = Neosynaptex(window=window, mode=mode)
        self._nx.register(self._adapter)
        self._seed: int = int(seed)
        self._window: int = int(window)
        self._states: list[NeosynaptexState] = []
        self._seed_ledger_path = seed_ledger_path
        if seed_ledger_path is not None:
            log_seed(seed_ledger_path, self._seed, self._session_fingerprint())

    # ------------------------------------------------------------------
    # Primary loop
    # ------------------------------------------------------------------
    def push_turn(self, turn: Turn) -> NeosynaptexState:
        self._adapter.push(turn)
        state = self._nx.observe()
        self._states.append(state)
        return state

    # ------------------------------------------------------------------
    # Read-only access
    # ------------------------------------------------------------------
    @property
    def seed(self) -> int:
        return self._seed

    @property
    def window(self) -> int:
        return self._window

    @property
    def adapter(self) -> DialogueAdapter:
        return self._adapter

    @property
    def n_turns(self) -> int:
        return len(self._states)

    def states(self) -> tuple[NeosynaptexState, ...]:
        return tuple(self._states)

    def gamma_trajectory(self) -> list[float]:
        """Ordered sequence of ``gamma_mean`` values, one per pushed turn."""
        return [float(s.gamma_mean) for s in self._states]

    def phase_trajectory(self) -> list[str]:
        return [str(s.phase) for s in self._states]

    # ------------------------------------------------------------------
    # Export (gated by MIN_TURNS)
    # ------------------------------------------------------------------
    def export_evidence(self) -> dict[str, Any]:
        if self.n_turns < MIN_TURNS:
            raise InsufficientDataError(f"need >= {MIN_TURNS} turns, have {self.n_turns}")
        final = self._states[-1]
        gamma_traj = self.gamma_trajectory()
        return {
            "seed": self._seed,
            "window": self._window,
            "n_turns": self.n_turns,
            "gamma_trajectory": gamma_traj,
            "phase_trajectory": self.phase_trajectory(),
            "final_state": {
                "gamma_mean": float(final.gamma_mean),
                "gamma_std": float(final.gamma_std),
                "phase": str(final.phase),
                "cross_coherence": float(final.cross_coherence),
                "dgamma_dt": float(final.dgamma_dt),
            },
            "adapter": {
                "domain": self._adapter.domain,
                "state_keys": list(self._adapter.state_keys),
                "vocab_size": int(self._adapter.vocab_size),
                "cumulative_tokens": int(self._adapter.thermo_cost()),
            },
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _session_fingerprint(self) -> str:
        """Deterministic-ish identifier for this session instance.

        Uses ``id(self)`` so two sessions constructed back-to-back with the
        same seed still get distinct ledger entries, but does not leak any
        cross-run identity (restarting the process reshuffles ids).
        """
        return f"{self._seed}-{id(self):x}"


# ----------------------------------------------------------------------
# Seed ledger (module-level so reproduce.py and batch ingestion can call
# without constructing a session first).
# ----------------------------------------------------------------------
def log_seed(path: Path, seed: int, session_hash: str) -> None:
    """Append one seed record to the JSONL ledger at ``path``.

    The ledger is monotonic append-only. Failures to write (e.g. readonly
    filesystem) raise ``OSError`` loudly rather than silently dropping.
    """
    import datetime

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "seed": int(seed),
        "session_hash": str(session_hash),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def load_seed_ledger(path: Path) -> list[_SeedEntry]:
    """Read the JSONL ledger back; used by reproduce.py for determinism checks."""
    path = Path(path)
    if not path.exists():
        return []
    out: list[_SeedEntry] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            out.append(
                _SeedEntry(
                    seed=int(data["seed"]),
                    session_hash=str(data["session_hash"]),
                    timestamp=str(data["timestamp"]),
                )
            )
    return out
