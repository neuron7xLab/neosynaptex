"""CNS-AI provenance boundary tests.

Three regressions pinned simultaneously:

1. The CNS-AI adapter declares ``provenance.claim_status == DOWNGRADED``
   and ``provenance_class == SYNTHETIC``. The adapter file used to call
   itself "Real Substrate Adapter" and carried no provenance metadata.
2. Registering a SYNTHETIC/DOWNGRADED adapter in a REAL / CANONICAL /
   PROOF / REPLICATION mode raises ``ProvenanceViolation``. The old
   registration path had no gate.
3. ``demo_real.py`` no longer imports or registers the CNS-AI adapter.
"""

from __future__ import annotations

import pathlib

import pytest

from contracts.provenance import (
    ClaimStatus,
    EngineMode,
    ProvenanceClass,
    ProvenanceViolation,
    ensure_admissible,
    is_real_mode,
)
from neosynaptex import Neosynaptex
from substrates.cns_ai_loop.adapter import (
    CnsAiLoopAdapter,
    SyntheticCnsAiLoopAdapter,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------
# Adapter-level provenance declaration
# --------------------------------------------------------------------------


def test_cns_ai_adapter_declares_synthetic_downgraded_provenance() -> None:
    adapter = SyntheticCnsAiLoopAdapter(seed=0)
    prov = adapter.provenance
    assert prov.provenance_class == ProvenanceClass.SYNTHETIC
    assert prov.claim_status == ClaimStatus.DOWNGRADED


def test_legacy_alias_preserves_provenance() -> None:
    # The old name must still import but must carry the new provenance.
    adapter = CnsAiLoopAdapter(seed=0)
    prov = adapter.provenance
    assert prov.claim_status == ClaimStatus.DOWNGRADED
    assert prov.provenance_class == ProvenanceClass.SYNTHETIC


# --------------------------------------------------------------------------
# ensure_admissible gate
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode",
    [EngineMode.REAL, EngineMode.CANONICAL, EngineMode.PROOF, EngineMode.REPLICATION],
)
def test_synthetic_adapter_rejected_in_real_modes(mode: EngineMode) -> None:
    adapter = SyntheticCnsAiLoopAdapter(seed=0)
    with pytest.raises(ProvenanceViolation):
        ensure_admissible(adapter, mode)


@pytest.mark.parametrize("mode", [EngineMode.TEST, EngineMode.DEMO, EngineMode.SYNTHETIC])
def test_synthetic_adapter_accepted_in_non_real_modes(mode: EngineMode) -> None:
    adapter = SyntheticCnsAiLoopAdapter(seed=0)
    ensure_admissible(adapter, mode)  # must not raise


def test_is_real_mode_matches_spec() -> None:
    for m in (
        EngineMode.REAL,
        EngineMode.CANONICAL,
        EngineMode.PROOF,
        EngineMode.REPLICATION,
    ):
        assert is_real_mode(m)
    for m in (EngineMode.TEST, EngineMode.DEMO, EngineMode.SYNTHETIC):
        assert not is_real_mode(m)
    assert not is_real_mode("nonsense")


# --------------------------------------------------------------------------
# Engine registration gate
# --------------------------------------------------------------------------


def test_engine_register_rejects_cns_ai_in_real_mode() -> None:
    engine = Neosynaptex(window=16, mode="real")
    with pytest.raises(ProvenanceViolation):
        engine.register(SyntheticCnsAiLoopAdapter(seed=0))


def test_engine_register_accepts_cns_ai_in_demo_mode() -> None:
    engine = Neosynaptex(window=16, mode="demo")
    engine.register(SyntheticCnsAiLoopAdapter(seed=0))
    assert "cns_ai" in engine._adapters


def test_engine_register_rejects_adapter_without_provenance_in_real_mode() -> None:
    class _NoProvenance:
        @property
        def domain(self) -> str:
            return "no_prov"

        @property
        def state_keys(self) -> list[str]:
            return ["x"]

        def state(self) -> dict[str, float]:
            return {"x": 0.0}

        def topo(self) -> float:
            return 1.0

        def thermo_cost(self) -> float:
            return 1.0

    engine = Neosynaptex(window=16, mode="real")
    with pytest.raises(ProvenanceViolation):
        engine.register(_NoProvenance())


# --------------------------------------------------------------------------
# demo_real.py must not re-introduce the downgraded substrate
# --------------------------------------------------------------------------


def test_demo_real_does_not_import_cns_ai() -> None:
    """AST-level check: no import / register of any CNS-AI adapter.

    Docstrings may mention historical context. Imports may not.
    """
    import ast

    demo = REPO_ROOT / "demo_real.py"
    tree = ast.parse(demo.read_text(encoding="utf-8"))

    forbidden_modules = {"substrates.cns_ai_loop", "substrates.cns_ai_loop.adapter"}
    forbidden_names = {"CnsAiLoopAdapter", "SyntheticCnsAiLoopAdapter"}

    imported_names: set[str] = set()
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(node.module)
            for alias in node.names:
                imported_names.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)

    assert not (imported_modules & forbidden_modules), (
        f"demo_real.py must not import from {imported_modules & forbidden_modules}"
    )
    assert not (imported_names & forbidden_names), (
        f"demo_real.py must not import adapter names {imported_names & forbidden_names}"
    )

    # Also verify no call-site instantiates a CNS-AI adapter by name.
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden_names, (
                f"demo_real.py must not construct {node.func.id}()"
            )
