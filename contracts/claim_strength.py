"""Canonical claim-strength taxonomy for the semantic drift gate."""

from __future__ import annotations

from typing import Final

PROTOCOL_VERSION: Final[str] = "1.0.0"

CLAIM_TIER_NAMES: Final[tuple[str, ...]] = (
    "descriptive",
    "speculative",
    "consistent_with",
    "suggestive",
    "measured",
    "bounded_positive",
    "validated",
    "causal",
    "generalized",
)

CLAIM_TIER_MARKERS: Final[dict[int, tuple[str, ...]]] = {
    0: (),
    1: (
        "may",
        "could",
        "possible",
        "possibly",
        "candidate",
        "exploratory",
        "hypothesized",
        "hypothesis",
        "pending replication",
        "pending controls",
    ),
    2: (
        "consistent with",
        "compatible with",
        "in line with",
        "matches qualitatively",
    ),
    3: (
        "suggests",
        "indicates",
        "points to",
        "supports provisional interpretation",
    ),
    4: (
        "measured",
        "observed",
        "estimated",
        "detected",
        "fit",
        "bounded result",
        "substrate-specific",
    ),
    5: (
        "bounded positive",
        "separates under controls",
        "survives null hierarchy",
        "positive but bounded",
    ),
    6: (
        "validated",
        "replicated",
        "externally confirmed",
        "gate-closed",
        "demonstrates",
        "establishes",
        "confirms",
        "proven",
        "proof",
    ),
    7: (
        "causes",
        "drives",
        "produces",
        "determines",
        "mechanism",
        "mechanistic",
    ),
    8: (
        "general",
        "universal",
        "law",
        "across systems",
        "proof of intelligence",
        "proof of consciousness",
        "generalized",
    ),
}

BOUNDARY_MARKERS: Final[tuple[str, ...]] = (
    "bounded",
    "substrate-specific",
    "candidate",
    "exploratory",
    "hypothesized",
    "pending replication",
    "pending controls",
    "measured_but_bounded",
    "not proof",
    "interpretation boundary",
)

HARD_FAIL_MARKERS: Final[tuple[str, ...]] = (
    "validated",
    "demonstrates",
    "proof",
    "proven",
    "causal",
    "causes",
    "universal",
    "law",
)

STATUS_CEILINGS: Final[dict[str, int]] = {
    # Canonical labels from tools.audit.claim_status_applied.CANONICAL_LABELS
    # (docs/SYSTEM_PROTOCOL.md §Barrier rule):
    "measured": 4,
    "derived": 3,
    "hypothesized": 1,
    "unverified analogy": 1,
    "falsified": 0,
    # Extended taxonomy used internally by the drift gate:
    "draft": 1,
    "active": 2,
    "measured_but_bounded": 5,
    "bounded_positive": 5,
    "validated": 6,
    # Analytical theorem layer (Claim C-001 of docs/CLAIM_BOUNDARY.md).
    # Reserved for claims with a fully specified analytical proof;
    # strictly scoped to the model/graph family covered by the proof.
    "proved": 8,
    "enforced": 4,
    "honest_negative": 0,
    "honest_null": 2,
    "blocked": 0,
    "stop_pending_owner": 0,
    "superseded": 0,
    "archived": 0,
}

DEFAULT_PROTECTED_FILES: Final[tuple[str, ...]] = (
    "README.md",
    "CANONICAL_POSITION.md",
    "PROTOCOL.md",
    "CONTRACT.md",
    "docs/SYSTEM_PROTOCOL.md",
    "docs/ADVERSARIAL_CONTROLS.md",
    "docs/REPLICATION_PROTOCOL.md",
)

DEFAULT_EXCLUDED_PREFIXES: Final[tuple[str, ...]] = (
    "archive/",
    "archived/",
)

SCOPE_LEVEL_NAMES: Final[tuple[str, ...]] = (
    "local",
    "substrate_specific",
    "cross_substrate_bounded",
    "general",
    "universal",
)

SCOPE_MARKERS: Final[dict[int, tuple[str, ...]]] = {
    0: (),
    1: (
        "in this substrate",
        "substrate-specific",
        "local result",
        "this dataset",
    ),
    2: (
        "across substrates",
        "cross-substrate",
        "multi-substrate",
        "bounded across substrates",
    ),
    3: (
        "general",
        "broadly",
        "generalizable",
    ),
    4: (
        "universal",
        "law",
        "across systems",
        "proof of intelligence",
        "proof of consciousness",
    ),
}

CAUSALITY_LEVEL_NAMES: Final[tuple[str, ...]] = (
    "none",
    "associative",
    "predictive",
    "mechanistic",
    "causal",
)

CAUSALITY_MARKERS: Final[dict[int, tuple[str, ...]]] = {
    0: (),
    1: (
        "associated with",
        "correlates with",
        "tracks",
        "linked to",
    ),
    2: (
        "predicts",
        "forecasts",
    ),
    3: (
        "mechanism",
        "mechanistic",
    ),
    4: (
        "causes",
        "drives",
        "produces",
        "determines",
        "causal",
    ),
}

PROOF_OR_VALIDATION_MARKERS: Final[tuple[str, ...]] = (
    "validated",
    "proof",
    "proven",
    "demonstrates",
    "establishes",
    "confirms",
)

POSITIVE_CLAIM_MIN_TIER: Final[int] = 3

SPECIAL_SURFACES: Final[tuple[str, ...]] = (
    "PR_TITLE",
    "PR_BODY",
)
