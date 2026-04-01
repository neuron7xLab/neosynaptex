#!/usr/bin/env python3
"""
Confidence Calibration Gates — the 0.95 enforcement in action.

Demonstrates that high confidence is EARNED, not claimed.
Without a valid proof gate, 0.95+ is forcibly downgraded.

Usage:
    python examples/02_confidence_gates.py
"""

from neuron7x_agents.primitives.confidence import (
    ConfidenceLevel,
    ProofGate,
    calibrate,
    enforce_gate,
)


def main() -> None:
    print("=" * 60)
    print("CONFIDENCE CALIBRATION GATES")
    print("=" * 60)

    # Case 1: Claim 0.97 without proof
    print("\n--- Case 1: Claim 0.97 WITHOUT proof gate ---")
    result = enforce_gate(0.97)
    print(f"  Raw:        {result.raw_score}")
    print(f"  Calibrated: {result.calibrated_score}")
    print(f"  Level:      {result.level.value}")
    print(f"  Downgraded: {result.was_downgraded}")
    print(f"  → 0.97 BLOCKED. Downgraded to 0.94.")

    # Case 2: Claim 0.97 WITH valid proof
    print("\n--- Case 2: Claim 0.97 WITH valid proof gate ---")
    gate = ProofGate(
        has_formal_proof=True,
        reductio_completed=True,
        unrebutted_objections=0,
    )
    result = enforce_gate(0.97, gate)
    print(f"  Raw:        {result.raw_score}")
    print(f"  Calibrated: {result.calibrated_score}")
    print(f"  Level:      {result.level.value}")
    print(f"  Downgraded: {result.was_downgraded}")
    print(f"  → 0.97 EARNED. All three gate conditions met.")

    # Case 3: Fragility check
    print("\n--- Case 3: Calibrate with fragility check ---")
    result = calibrate(
        0.85,
        fragility_check="A single new RCT could invalidate this finding",
    )
    print(f"  Raw:        0.85")
    print(f"  Calibrated: {result.calibrated_score}")
    print(f"  Level:      {result.level.value}")
    print(f"  → Score reduced by 0.05 (humility correction).")

    # Case 4: Confidence level tiers
    print("\n--- Confidence tier map ---")
    for score in [0.2, 0.45, 0.65, 0.85, 0.97]:
        level = ConfidenceLevel.from_score(score)
        print(f"  {score:.2f} → {level.value}")


if __name__ == "__main__":
    main()
