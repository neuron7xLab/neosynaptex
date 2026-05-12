from __future__ import annotations

import pytest

from pfc_coherent_induction import MemoryTrace, PFCInductionEngine, RawIdea, default_goal_memory


def test_release_gate_requires_full_closure() -> None:
    engine = PFCInductionEngine()
    result = engine.run(
        raw_idea=RawIdea("Use PFC-inspired architecture."),
        goal_memory=default_goal_memory(),
        traces=(MemoryTrace("pfc", "PFC maintains goal context.", 0.9),),
        candidate_output="role context artifact_tests evidence_ledger value_score",
    )
    assert result.ledger.utc_timestamp.endswith("Z")
    assert len(result.ledger.artifact_hash) == 64


def test_clean_run_passes() -> None:
    engine = PFCInductionEngine()
    result = engine.run(
        raw_idea=RawIdea("Build a testable PFC-inspired model."),
        goal_memory=default_goal_memory(),
        traces=(MemoryTrace("pfc", "PFC maintains goals.", 0.95),),
        candidate_output="role context artifact tests evidence ledger",
    )
    assert result.ledger.final_verdict == "PASS"


def test_forbidden_neuroclaim_fails() -> None:
    engine = PFCInductionEngine()
    result = engine.run(
        raw_idea=RawIdea("x"),
        goal_memory=default_goal_memory(),
        traces=(MemoryTrace("pfc", "x", 0.95),),
        candidate_output="literal human-ai fusion proved",
    )
    assert result.ledger.final_verdict == "FAIL"


def test_empty_raw_idea_fails() -> None:
    with pytest.raises(ValueError):
        PFCInductionEngine().run(RawIdea("   "), default_goal_memory(), (), "x")
