"""Tests for cognitive primitives: column, confidence, evidence."""

from __future__ import annotations

import pytest

from neuron7x_agents.primitives.column import (
    Complexity,
    CorticalColumn,
    Role,
)
from neuron7x_agents.primitives.confidence import (
    ConfidenceLevel,
    ProofGate,
    calibrate,
    enforce_gate,
)
from neuron7x_agents.primitives.evidence import (
    EvidenceItem,
    EvidenceSource,
    EvidenceTier,
    MarkovBlanket,
)

# ═══════════════════════════════════════════════════════════════════════
#  Confidence
# ═══════════════════════════════════════════════════════════════════════


class TestConfidenceLevel:
    def test_from_score_unknown(self) -> None:
        assert ConfidenceLevel.from_score(0.2) == ConfidenceLevel.UNKNOWN

    def test_from_score_uncertain(self) -> None:
        assert ConfidenceLevel.from_score(0.5) == ConfidenceLevel.UNCERTAIN

    def test_from_score_reasonable(self) -> None:
        assert ConfidenceLevel.from_score(0.7) == ConfidenceLevel.REASONABLE

    def test_from_score_strong(self) -> None:
        assert ConfidenceLevel.from_score(0.9) == ConfidenceLevel.STRONG

    def test_from_score_proven(self) -> None:
        assert ConfidenceLevel.from_score(0.99) == ConfidenceLevel.PROVEN


class TestProofGate:
    def test_gate_requires_all_three(self) -> None:
        gate = ProofGate(
            has_formal_proof=True,
            reductio_completed=True,
            unrebutted_objections=0,
        )
        assert gate.passed is True

    def test_gate_fails_without_evidence(self) -> None:
        gate = ProofGate(reductio_completed=True, unrebutted_objections=0)
        assert gate.passed is False

    def test_gate_fails_without_reductio(self) -> None:
        gate = ProofGate(has_formal_proof=True, unrebutted_objections=0)
        assert gate.passed is False

    def test_gate_fails_with_objections(self) -> None:
        gate = ProofGate(
            has_formal_proof=True,
            reductio_completed=True,
            unrebutted_objections=1,
        )
        assert gate.passed is False


class TestEnforceGate:
    def test_high_confidence_without_gate_is_downgraded(self) -> None:
        result = enforce_gate(0.97)
        assert result.calibrated_score == 0.94
        assert result.was_downgraded is True

    def test_high_confidence_with_valid_gate_passes(self) -> None:
        gate = ProofGate(
            has_formal_proof=True,
            reductio_completed=True,
            unrebutted_objections=0,
        )
        result = enforce_gate(0.97, gate)
        assert result.calibrated_score == 0.97
        assert result.was_downgraded is False

    def test_low_confidence_passes_through(self) -> None:
        result = enforce_gate(0.6)
        assert result.calibrated_score == 0.6
        assert result.was_downgraded is False

    def test_score_clamped_to_bounds(self) -> None:
        assert enforce_gate(-0.5).calibrated_score == 0.0
        assert enforce_gate(1.5).calibrated_score == 0.94  # >0.95, no gate → downgrade


class TestCalibrate:
    def test_fragility_check_reduces_score(self) -> None:
        result = calibrate(0.8, fragility_check="New RCT could invalidate this")
        assert result.calibrated_score < 0.8

    def test_no_fragility_check_passes_through(self) -> None:
        result = calibrate(0.7)
        assert result.calibrated_score == 0.7


# ═══════════════════════════════════════════════════════════════════════
#  Evidence
# ═══════════════════════════════════════════════════════════════════════


class TestEvidenceTier:
    def test_weight_hierarchy(self) -> None:
        assert EvidenceTier.GIVEN.weight > EvidenceTier.INFERRED.weight
        assert EvidenceTier.INFERRED.weight > EvidenceTier.SPECULATED.weight

    def test_source_reliability_hierarchy(self) -> None:
        assert EvidenceSource.FORMAL_PROOF.reliability > EvidenceSource.ANECDOTAL.reliability


class TestMarkovBlanket:
    def test_add_given(self) -> None:
        blanket = MarkovBlanket()
        item = EvidenceItem("sky is blue", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT)
        blanket.add_given(item)
        assert blanket.total_evidence == 1
        assert blanket.summary()["given"] == 1

    def test_add_wrong_tier_raises(self) -> None:
        blanket = MarkovBlanket()
        item = EvidenceItem("hypothesis", EvidenceTier.SPECULATED, EvidenceSource.ANECDOTAL)
        with pytest.raises(ValueError, match="Expected GIVEN"):
            blanket.add_given(item)

    def test_aggregate_precision(self) -> None:
        blanket = MarkovBlanket()
        blanket.add_given(EvidenceItem("fact", EvidenceTier.GIVEN, EvidenceSource.FORMAL_PROOF))
        assert blanket.aggregate_precision == 1.0

    def test_empty_blanket_precision(self) -> None:
        blanket = MarkovBlanket()
        assert blanket.aggregate_precision == 0.0


# ═══════════════════════════════════════════════════════════════════════
#  Cortical Column
# ═══════════════════════════════════════════════════════════════════════


class TestCorticalColumn:
    def test_trivial_uses_creator_only(self) -> None:
        column = CorticalColumn()
        result = column.run({"query": "test"}, Complexity.TRIVIAL)
        assert len(result.role_results) == 1
        assert result.role_results[0].role == Role.CREATOR

    def test_complex_uses_three_roles(self) -> None:
        column = CorticalColumn()
        result = column.run({"query": "test"}, Complexity.COMPLEX)
        assert len(result.role_results) == 3

    def test_critical_uses_all_four(self) -> None:
        column = CorticalColumn()
        result = column.run({"query": "test"}, Complexity.CRITICAL)
        assert len(result.role_results) == 4

    def test_column_result_properties(self) -> None:
        result = CorticalColumn().run({"query": "test"})
        assert isinstance(result.has_consensus, bool)
        assert 0.0 <= result.min_confidence <= 1.0
