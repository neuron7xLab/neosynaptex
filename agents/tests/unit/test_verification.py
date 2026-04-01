"""Tests for Kriterion epistemic verification and anti-gaming."""

from __future__ import annotations

from neuron7x_agents.primitives.evidence import (
    EvidenceItem,
    EvidenceSource,
    EvidenceTier,
)
from neuron7x_agents.verification.anti_gaming import AntiGamingDetector
from neuron7x_agents.verification.gate import EpistemicGate, GateStatus

# ═══════════════════════════════════════════════════════════════════════
#  Epistemic Gate
# ═══════════════════════════════════════════════════════════════════════


class TestEpistemicGate:
    def _make_evidence(
        self,
        n: int = 3,
        tier: EvidenceTier = EvidenceTier.GIVEN,
        source: EvidenceSource = EvidenceSource.EXPERIMENT,
        provenance: str = "doi:10.1234",
    ) -> list[EvidenceItem]:
        return [EvidenceItem(f"claim_{i}", tier, source, provenance=provenance) for i in range(n)]

    def test_sufficient_evidence_passes(self) -> None:
        gate = EpistemicGate(min_evidence=2)
        evidence = self._make_evidence(3)
        verdict = gate.evaluate(evidence)
        assert verdict.status == GateStatus.PASSED
        assert verdict.is_admissible

    def test_insufficient_evidence_blocks(self) -> None:
        gate = EpistemicGate(min_evidence=5)
        evidence = self._make_evidence(2)
        verdict = gate.evaluate(evidence)
        assert verdict.status == GateStatus.BLOCKED
        assert not verdict.is_admissible

    def test_empty_evidence_is_invalid(self) -> None:
        gate = EpistemicGate()
        verdict = gate.evaluate([])
        assert verdict.status == GateStatus.INVALID
        assert verdict.score == 0.0

    def test_missing_provenance_caps_score(self) -> None:
        gate = EpistemicGate(require_provenance=True)
        evidence = self._make_evidence(3, provenance="")
        verdict = gate.evaluate(evidence, claimed_score=0.9)
        assert verdict.status in (GateStatus.CAPPED, GateStatus.BLOCKED)

    def test_low_given_ratio_caps(self) -> None:
        gate = EpistemicGate(min_given_ratio=0.5)
        evidence = [
            EvidenceItem("a", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="x"),
            EvidenceItem("b", EvidenceTier.SPECULATED, EvidenceSource.ANECDOTAL, provenance="x"),
            EvidenceItem("c", EvidenceTier.SPECULATED, EvidenceSource.ANECDOTAL, provenance="x"),
        ]
        verdict = gate.evaluate(evidence)
        assert verdict.status == GateStatus.CAPPED

    def test_score_never_exceeds_max(self) -> None:
        gate = EpistemicGate()
        evidence = self._make_evidence(3)
        verdict = gate.evaluate(evidence, claimed_score=5.0)
        assert verdict.score <= verdict.max_possible_score


# ═══════════════════════════════════════════════════════════════════════
#  Anti-Gaming
# ═══════════════════════════════════════════════════════════════════════


class TestAntiGaming:
    def test_clean_evidence(self) -> None:
        detector = AntiGamingDetector()
        evidence = [
            EvidenceItem("claim_1", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="x"),
            EvidenceItem(
                "claim_2", EvidenceTier.GIVEN, EvidenceSource.PEER_REVIEWED, provenance="y"
            ),
        ]
        report = detector.analyze(evidence)
        assert report.is_clean

    def test_detects_artifact_reuse(self) -> None:
        detector = AntiGamingDetector(max_reuse=1)
        evidence = [
            EvidenceItem(
                "same_claim", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="x"
            ),
            EvidenceItem(
                "same_claim", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="y"
            ),
            EvidenceItem(
                "same_claim", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="z"
            ),
        ]
        report = detector.analyze(evidence)
        assert not report.is_clean
        assert any(v.violation_type == "artifact_reuse" for v in report.violations)

    def test_detects_self_review(self) -> None:
        detector = AntiGamingDetector()
        evidence = [
            EvidenceItem("claim", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="x"),
        ]
        report = detector.analyze(
            evidence,
            authors={"alice"},
            reviewers={"alice", "bob"},
        )
        assert not report.is_clean
        assert any(v.violation_type == "self_review" for v in report.violations)

    def test_detects_provenance_gaps(self) -> None:
        detector = AntiGamingDetector()
        evidence = [
            EvidenceItem("a", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance=""),
            EvidenceItem("b", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance=""),
            EvidenceItem("c", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="x"),
        ]
        report = detector.analyze(evidence)
        assert any(v.violation_type == "provenance_gap" for v in report.violations)
