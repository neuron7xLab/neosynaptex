"""DialogueAdapter — human-AI session substrate for neosynaptex.

Semantic contract:
    domain = "dialogue"
    topo        = cumulative unique token types across all turns so far
    thermo_cost = cumulative token count across all turns

``topo`` and ``thermo_cost`` are both strictly non-decreasing; the power-law
contract ``cost ~ topo^(-gamma)`` is evaluated by the canonical neosynaptex
gamma engine, never computed inside the adapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts.provenance import ClaimStatus, Provenance, ProvenanceClass


@dataclass(frozen=True)
class Turn:
    """Immutable dialogue turn.

    Attributes:
        role: ``"human"`` or ``"assistant"``.
        content: Raw turn text.
        token_count: Caller-provided token total (input + output). Must be
            strictly positive; zero is rejected by adapter push().
    """

    role: str
    content: str
    token_count: int

    def __post_init__(self) -> None:
        if self.role not in {"human", "assistant"}:
            raise ValueError(f"role must be 'human' or 'assistant', got {self.role!r}")
        if self.token_count <= 0:
            raise ValueError(f"token_count must be positive, got {self.token_count}")


class DialogueAdapter:
    """Dialogue substrate adapter conforming to ``DomainAdapter`` Protocol.

    Invariants enforced on every ``push``:
      * topo non-decreasing (strict equality permitted only if the turn
        introduces no new vocabulary).
      * thermo_cost strictly increasing (every turn contributes tokens).
      * Turn history is append-only; existing entries are never mutated.
    """

    _DOMAIN: str = "dialogue"
    _STATE_KEYS: tuple[str, ...] = ("topo", "thermo_cost", "turn_count")

    @property
    def domain(self) -> str:
        return self._DOMAIN

    @property
    def state_keys(self) -> list[str]:
        return list(self._STATE_KEYS)

    # Default SYNTHETIC+ADMISSIBLE provenance — safe for TEST engine mode.
    # Must be upgraded via ``with_real_provenance`` before binding to a real
    # corpus in REAL/CANONICAL/PROOF/REPLICATION modes.
    provenance: Provenance = Provenance(
        provenance_class=ProvenanceClass.SYNTHETIC,
        claim_status=ClaimStatus.ADMISSIBLE,
        corpus_ref="neosynaptex-probe dialogue substrate (STEP 2)",
        notes=(
            "Default SYNTHETIC provenance; upgrade to REAL with "
            "with_real_provenance(corpus_ref=...) before binding to "
            "real human-AI corpora under REAL/CANONICAL modes."
        ),
    )

    def __init__(self) -> None:
        self._turns: list[Turn] = []
        self._vocab: set[str] = set()
        self._cumulative_tokens: int = 0
        # Mirror of the last observed (topo, cost) pair; used solely to
        # enforce monotonicity invariants. Not exported as state.
        self._last_topo: float = 0.0
        self._last_cost: float = 0.0

    # ------------------------------------------------------------------
    # Protocol surface
    # ------------------------------------------------------------------
    def state(self) -> dict[str, float]:
        return {
            "topo": float(len(self._vocab)),
            "thermo_cost": float(self._cumulative_tokens),
            "turn_count": float(len(self._turns)),
        }

    def topo(self) -> float:
        return float(len(self._vocab))

    def thermo_cost(self) -> float:
        return float(self._cumulative_tokens)

    # ------------------------------------------------------------------
    # Mutation — append-only
    # ------------------------------------------------------------------
    def push(self, turn: Turn) -> None:
        """Append one turn. Enforces adapter invariants fail-closed."""
        if not isinstance(turn, Turn):
            raise TypeError(f"expected Turn, got {type(turn).__name__}")

        new_vocab = self._vocab | set(_tokenize(turn.content))
        new_cost = self._cumulative_tokens + turn.token_count
        new_topo = float(len(new_vocab))

        if new_topo < self._last_topo:
            raise AssertionError(f"topo invariant violated: {new_topo} < {self._last_topo}")
        if new_cost <= self._last_cost:
            raise AssertionError(
                f"thermo_cost strict-monotone invariant violated: {new_cost} <= {self._last_cost}"
            )

        # All checks passed — commit. A failure above leaves state untouched.
        self._turns.append(turn)
        self._vocab = new_vocab
        self._cumulative_tokens = new_cost
        self._last_topo = new_topo
        self._last_cost = float(new_cost)

    # ------------------------------------------------------------------
    # Read-only accessors (no mutation escape hatch)
    # ------------------------------------------------------------------
    @property
    def turns(self) -> tuple[Turn, ...]:
        """Immutable view of the turn history."""
        return tuple(self._turns)

    @property
    def vocab_size(self) -> int:
        return len(self._vocab)

    # ------------------------------------------------------------------
    # Provenance upgrade (opt-in)
    # ------------------------------------------------------------------
    def with_real_provenance(
        self,
        corpus_ref: str,
        notes: str = "",
    ) -> DialogueAdapter:
        """Stamp this adapter as REAL-provenance for canonical modes.

        Returns ``self`` so callers can chain at registration sites. The
        stamp is attached on the instance (shadowing the class default)
        so other instances remain SYNTHETIC unless explicitly upgraded.
        """
        self.provenance = Provenance(
            provenance_class=ProvenanceClass.REAL,
            claim_status=ClaimStatus.ADMISSIBLE,
            corpus_ref=corpus_ref,
            notes=notes or f"Upgraded to REAL for corpus: {corpus_ref}",
        )
        return self


def _tokenize(text: str) -> list[str]:
    """Case-insensitive whitespace tokenization.

    Kept deliberately minimal — matches the spec ``content.lower().split()``
    so results are deterministic across platforms. Callers that want
    morphological normalization (stemming, NFKC) must preprocess before
    constructing ``Turn``.
    """
    return text.lower().split()
