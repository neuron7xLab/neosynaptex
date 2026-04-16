"""Every exported bundle must carry provenance_class + claim_status per domain.

REPLICATION_GATE_v1.0 Phase 4 requires the serialized bundle to expose,
for every registered adapter, both ``provenance_class`` (real / synthetic
/ mock / downgraded / unknown) and ``claim_status`` (admissible /
downgraded / forbidden / unknown). Silent absence is a contract violation;
an adapter without a ``provenance`` attribute emits the explicit
``"unknown"`` sentinel.
"""

from __future__ import annotations

import json

import pytest

from contracts.provenance import ClaimStatus, Provenance, ProvenanceClass
from core.coherence_bridge import CoherenceBridge, RuntimeContext
from neosynaptex import Neosynaptex
from substrates.cns_ai_loop.adapter import SyntheticCnsAiLoopAdapter

_ALLOWED_PROV_CLASS = {"real", "synthetic", "mock", "downgraded", "unknown"}
_ALLOWED_CLAIM_STATUS = {"admissible", "downgraded", "forbidden", "unknown"}


class _NakedAdapter:
    """Adapter with no ``provenance`` attribute -- must emit 'unknown'."""

    @property
    def domain(self) -> str:
        return "naked"

    @property
    def state_keys(self) -> list[str]:
        return ["x"]

    def state(self) -> dict[str, float]:
        return {"x": 0.0}

    def topo(self) -> float:
        return 1.0

    def thermo_cost(self) -> float:
        return 1.0


class _RealAdapter:
    """Synthetic-equivalent helper but declared REAL / ADMISSIBLE."""

    provenance: Provenance = Provenance(
        provenance_class=ProvenanceClass.REAL,
        claim_status=ClaimStatus.ADMISSIBLE,
        corpus_ref="test://real",
    )

    @property
    def domain(self) -> str:
        return "real_domain"

    @property
    def state_keys(self) -> list[str]:
        return ["x"]

    def state(self) -> dict[str, float]:
        return {"x": 1.0}

    def topo(self) -> float:
        return 2.0

    def thermo_cost(self) -> float:
        return 3.0


def _payload_with(*adapters: object) -> dict[str, object]:
    engine = Neosynaptex(window=8, mode="test")
    for ad in adapters:
        engine.register(ad)  # type: ignore[arg-type]
    for _ in range(6):
        engine.observe()
    rt = RuntimeContext.fixed(git_sha="test_bundle", timestamp=0.0)
    blob = CoherenceBridge(engine=engine, runtime=rt).export_bundle()
    parsed = json.loads(blob)
    assert isinstance(parsed, dict)
    return parsed


def _per_domain_block(payload: dict[str, object]) -> dict[str, dict[str, str]]:
    pd = payload.get("per_domain")
    assert isinstance(pd, dict), f"expected top-level 'per_domain' dict, got {type(pd).__name__}"
    return pd


# --------------------------------------------------------------------------
# Positive path: synthetic + real adapter both emit valid metadata
# --------------------------------------------------------------------------


def test_synthetic_adapter_emits_downgraded_metadata() -> None:
    payload = _payload_with(SyntheticCnsAiLoopAdapter(seed=0))
    block = _per_domain_block(payload)["cns_ai"]
    assert block["provenance_class"] == "synthetic"
    assert block["claim_status"] == "downgraded"


def test_real_adapter_emits_admissible_metadata() -> None:
    payload = _payload_with(_RealAdapter())
    block = _per_domain_block(payload)["real_domain"]
    assert block["provenance_class"] == "real"
    assert block["claim_status"] == "admissible"


# --------------------------------------------------------------------------
# Fail-closed path: adapter without provenance -> explicit 'unknown'
# --------------------------------------------------------------------------


def test_naked_adapter_emits_unknown_sentinel() -> None:
    payload = _payload_with(_NakedAdapter())
    block = _per_domain_block(payload)["naked"]
    assert block["provenance_class"] == "unknown"
    assert block["claim_status"] == "unknown"


# --------------------------------------------------------------------------
# Invariants: every exported domain is inside the canonical enums.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "adapter_factory",
    [
        lambda: SyntheticCnsAiLoopAdapter(seed=0),
        lambda: _RealAdapter(),
        lambda: _NakedAdapter(),
    ],
)
def test_exported_values_inside_canonical_enums(
    adapter_factory: object,
) -> None:
    payload = _payload_with(adapter_factory())  # type: ignore[operator]
    for name, block in _per_domain_block(payload).items():
        assert block["provenance_class"] in _ALLOWED_PROV_CLASS, (
            f"{name}: provenance_class={block['provenance_class']!r} outside canonical set"
        )
        assert block["claim_status"] in _ALLOWED_CLAIM_STATUS, (
            f"{name}: claim_status={block['claim_status']!r} outside canonical set"
        )


def test_every_registered_domain_present_in_bundle() -> None:
    payload = _payload_with(SyntheticCnsAiLoopAdapter(seed=0), _RealAdapter(), _NakedAdapter())
    block = _per_domain_block(payload)
    assert set(block) == {"cns_ai", "real_domain", "naked"}
    # No silent skip: every adapter contributes an entry.
    for name, entry in block.items():
        assert "provenance_class" in entry, f"{name}: missing provenance_class"
        assert "claim_status" in entry, f"{name}: missing claim_status"


# --------------------------------------------------------------------------
# export_bundle must merge proof.per_domain into the final JSON
# unchanged (no mutation / no drop).
# --------------------------------------------------------------------------


def test_export_bundle_preserves_provenance_from_proof() -> None:
    engine = Neosynaptex(window=8, mode="test")
    engine.register(SyntheticCnsAiLoopAdapter(seed=0))
    for _ in range(6):
        engine.observe()
    rt = RuntimeContext.fixed(git_sha="test_merge", timestamp=0.0)
    bridge = CoherenceBridge(engine=engine, runtime=rt)
    # Read the proof directly + through the bundle; per_domain must match.
    proof_direct = engine.export_proof()
    bundle = json.loads(bridge.export_bundle())
    assert bundle["per_domain"] == proof_direct["per_domain"]
