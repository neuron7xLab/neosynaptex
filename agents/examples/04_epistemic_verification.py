#!/usr/bin/env python3
"""
Kriterion Epistemic Verification — fail-closed evidence gates.

Demonstrates how missing evidence, provenance gaps, and gaming
attempts are detected and blocked.

Usage:
    python examples/04_epistemic_verification.py
"""

from neuron7x_agents.primitives.evidence import (
    EvidenceItem,
    EvidenceSource,
    EvidenceTier,
    MarkovBlanket,
)
from neuron7x_agents.verification.gate import EpistemicGate
from neuron7x_agents.verification.anti_gaming import AntiGamingDetector


def main() -> None:
    print("=" * 60)
    print("KRITERION — FAIL-CLOSED EPISTEMIC VERIFICATION")
    print("=" * 60)

    gate = EpistemicGate()

    # Case 1: Strong evidence passes
    print("\n--- Case 1: Strong evidence with provenance ---")
    evidence = [
        EvidenceItem("Claim A", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="doi:10.1234/a"),
        EvidenceItem("Claim B", EvidenceTier.GIVEN, EvidenceSource.PEER_REVIEWED, provenance="doi:10.1234/b"),
        EvidenceItem("Claim C", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="doi:10.1234/c"),
    ]
    verdict = gate.evaluate(evidence, claimed_score=0.9)
    print(f"  Status:    {verdict.status.value}")
    print(f"  Score:     {verdict.score:.2f}")
    print(f"  Max score: {verdict.max_possible_score:.2f}")
    print(f"  Admissible: {verdict.is_admissible}")

    # Case 2: Missing provenance caps score
    print("\n--- Case 2: Evidence without provenance ---")
    weak = [
        EvidenceItem("Claim X", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance=""),
        EvidenceItem("Claim Y", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance=""),
    ]
    verdict = gate.evaluate(weak, claimed_score=0.9)
    print(f"  Status:    {verdict.status.value}")
    print(f"  Score:     {verdict.score:.2f}")
    print(f"  Violations: {verdict.violations}")

    # Case 3: Empty evidence is INVALID
    print("\n--- Case 3: No evidence at all ---")
    verdict = gate.evaluate([], claimed_score=0.95)
    print(f"  Status:    {verdict.status.value}")
    print(f"  Score:     {verdict.score}")
    print(f"  → Empty evidence = inadmissible. Not 'incomplete' — invalid.")

    # Case 4: Anti-gaming detection
    print("\n--- Case 4: Anti-gaming — artifact reuse + self-review ---")
    detector = AntiGamingDetector(max_reuse=1)
    gaming_evidence = [
        EvidenceItem("same claim", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="x"),
        EvidenceItem("same claim", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="y"),
        EvidenceItem("same claim", EvidenceTier.GIVEN, EvidenceSource.EXPERIMENT, provenance="z"),
    ]
    report = detector.analyze(
        gaming_evidence,
        authors={"alice"},
        reviewers={"alice", "bob"},
    )
    print(f"  Clean:      {report.is_clean}")
    print(f"  Violations: {report.violation_count}")
    for v in report.violations:
        print(f"    [{v.violation_type}] {v.description} (severity: {v.severity})")
    print(f"  Penalty:    {report.total_penalty:.1f}")

    # Case 5: Markov blanket — epistemic tiering
    print("\n--- Case 5: Markov blanket — never mix tiers ---")
    blanket = MarkovBlanket()
    blanket.add_given(EvidenceItem("fact", EvidenceTier.GIVEN, EvidenceSource.FORMAL_PROOF))
    blanket.add_inferred(EvidenceItem("derived", EvidenceTier.INFERRED, EvidenceSource.PEER_REVIEWED))
    blanket.add_speculated(EvidenceItem("hypothesis", EvidenceTier.SPECULATED, EvidenceSource.EXPERT_OPINION))
    print(f"  Tiers: {blanket.summary()}")
    print(f"  Aggregate precision: {blanket.aggregate_precision:.3f}")
    print(f"  → GIVEN=1.0, INFERRED=0.6, SPECULATED=0.2. Never mixed.")


if __name__ == "__main__":
    main()
