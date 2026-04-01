#!/usr/bin/env python3
"""Verify A_C axioms A1-A5 across all selection strategies.

Usage:
    python scripts/verify_axioms.py
"""

from __future__ import annotations

from mycelium_fractal_net.neurochem.axiomatic_choice import (
    AxiomaticChoiceOperator,
    SelectionStrategy,
    check_activation_conditions,
)
from mycelium_fractal_net.neurochem.gnc import MODULATORS, compute_gnc_state, gnc_diagnose

print("=" * 65)
print("A_C Axiom Verification — Vasylenko (2026)")
print("Reality_t = phi( S_Theta_t( h_t( R(A_t) ) ) )")
print("=" * 65)

# Generate test candidates U_t
candidates = [
    compute_gnc_state({
        "Glutamate": 0.7, "GABA": 0.3, "Noradrenaline": 0.6,
        "Serotonin": 0.4, "Dopamine": 0.65, "Acetylcholine": 0.55, "Opioid": 0.5,
    }),
    compute_gnc_state(dict.fromkeys(MODULATORS, 0.5)),
    compute_gnc_state({
        "Glutamate": 0.6, "GABA": 0.4, "Noradrenaline": 0.55,
        "Serotonin": 0.45, "Dopamine": 0.6, "Acetylcholine": 0.5, "Opioid": 0.55,
    }),
]

prev_state = compute_gnc_state(dict.fromkeys(MODULATORS, 0.5))

print("\n--- Strategy Sweep ---\n")

all_pass = True
for strategy in SelectionStrategy:
    op = AxiomaticChoiceOperator(strategy=strategy, seed=42)
    selected = op.select(candidates, prev_state=prev_state, force=True)
    axioms = op.validate_axioms(selected, candidates, prev_state)
    ok = axioms["all_satisfied"]
    if not ok:
        all_pass = False
    status = "\u2713" if ok else "\u2717"
    diag = gnc_diagnose(selected)
    print(
        f"{status} {strategy.value:25s} "
        f"A1={axioms['A1_admissibility']} "
        f"A2={axioms['A2_ccp_closure']} "
        f"A4={axioms['A4_phase_induction']} "
        f"A5={axioms['A5_stabilization']} "
        f"coh={diag.coherence:.3f} regime={diag.regime}"
    )

print("\n--- Activation Scenarios ---\n")

# Nominal — should NOT activate
act_nom = check_activation_conditions(candidates[0], ccp_D_f=1.71, ccp_R=0.80)
print(f"  Nominal:    {act_nom.summary()}")

# CCP violation — SHOULD activate
act_ccp = check_activation_conditions(candidates[0], ccp_D_f=1.2, ccp_R=0.3)
print(f"  CCP fail:   {act_ccp.summary()}")

# Multi-condition
act_multi = check_activation_conditions(
    candidates[0], ccp_D_f=1.2, ccp_R=0.2, gradient_norm=0.001,
    j_values=[0.50, 0.51],
)
print(f"  Multi-cond: {act_multi.summary()}")

print("\n--- Integration Test ---\n")

op = AxiomaticChoiceOperator(strategy=SelectionStrategy.ENSEMBLE)
selected = op.select(candidates, prev_state=prev_state, ccp_D_f=1.2, ccp_R=0.3)

if selected:
    diag = gnc_diagnose(selected)
    print(f"A_C activated: regime={diag.regime} coherence={diag.coherence:.3f}")
    print(op.summary())
else:
    print("A_C: not activated (system nominal)")

print("\n" + "=" * 65)
if all_pass:
    print("RESULT: ALL AXIOMS SATISFIED across all strategies")
else:
    print("RESULT: AXIOM VIOLATION detected — check output above")
print("=" * 65)
