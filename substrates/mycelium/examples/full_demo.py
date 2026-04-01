#!/usr/bin/env python3
"""MFN Full Demo — every major feature in action.

Demonstrates: simulation, diagnosis, ensemble, intervention,
inverse synthesis, temporal monitoring, and causal verification.

Run: python examples/full_demo.py
"""

import json

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.causal_validation import validate_causal_consistency

print("=" * 60)
print("  MyceliumFractalNet v4.1.0 — Full Capability Demo")
print("=" * 60)

# ── 1. Baseline simulation ───────────────────────────────────
print("\n1. SIMULATION")
spec = mfn.SimulationSpec(grid_size=32, steps=60, seed=42)
seq = mfn.simulate(spec)
print(f"   {seq}")

# ── 2. Full pipeline ─────────────────────────────────────────
print("\n2. FULL PIPELINE")
desc = mfn.extract(seq)
det = mfn.detect(seq)
fc = mfn.forecast(seq, horizon=8)
print(
    f"   Extract:  {desc.version} | {len(desc.features)} features | {len(desc.embedding)}-dim embedding"
)
print(f"   Detect:   {det.label} | score={det.score:.3f} | regime={det.regime.label}")
print(f"   Forecast: horizon={fc.horizon} | method={fc.method}")

# ── 3. Causal validation ─────────────────────────────────────
print("\n3. CAUSAL VALIDATION")
cv = validate_causal_consistency(seq, descriptor=desc, detection=det, forecast=fc, mode="strict")
print(f"   Decision: {cv.decision.value}")
print(f"   Rules evaluated: {len(cv.rule_results)}")
print(f"   Passed: {sum(1 for r in cv.rule_results if r.passed)}/{len(cv.rule_results)}")

# ── 4. Unified diagnosis ─────────────────────────────────────
print("\n4. DIAGNOSIS")
report = mfn.diagnose(seq)
print(f"   {report.summary()}")
print(f"   {report.narrative}")

# ── 5. Ensemble diagnosis ────────────────────────────────────
print("\n5. ENSEMBLE (5 seeds)")
er = mfn.ensemble_diagnose(spec, n_runs=5)
print(f"   {er.summary()}")
print(f"   Robust: {er.is_robust()} | Causal pass rate: {er.causal_pass_rate:.0%}")

# ── 6. Temporal monitoring ───────────────────────────────────
print("\n6. WATCH (5 ticks)")
reports = mfn.watch(spec, n_steps_per_tick=20, n_ticks=5)
for i, r in enumerate(reports):
    marker = "→" if r.warning.ews_score > 0.5 else " "
    print(
        f"   {marker} tick {i}: {r.severity:8s} ews={r.warning.ews_score:.3f} {r.warning.transition_type}"
    )

if len(reports) >= 2:
    diff = reports[0].diff(reports[-1])
    print(f"   Trend: {diff.overall_trend} (ews Δ={diff.ews_score_delta:+.3f})")

# ── 7. Intervention planning ─────────────────────────────────
print("\n7. INTERVENTION PLANNING")
plan = mfn.plan_intervention(seq, target_regime="stable", budget=5.0, max_candidates=8)
print(f"   Viable: {plan.has_viable_plan}")
if plan.best_candidate:
    bc = plan.best_candidate
    print(f"   Score: {bc.composite_score:.4f} | Causal: {bc.causal_decision}")
    for ch in bc.proposed_changes:
        if abs(ch.proposed_value - ch.current_value) > 1e-9:
            print(f"     {ch.name}: {ch.current_value:.3f} → {ch.proposed_value:.3f}")

# ── 8. Inverse synthesis ─────────────────────────────────────
print("\n8. INVERSE SYNTHESIS")
inv = mfn.inverse_synthesis("approaching_transition", 0.5, grid_size=32, steps=60, max_iterations=5)
print(f"   {inv.summary()}")

# ── 9. JSON serialization ────────────────────────────────────
print("\n9. SERIALIZATION")
d = report.to_dict()
json_str = json.dumps(d, indent=2, default=str)
print(f"   DiagnosisReport → JSON: {len(json_str)} bytes")
print(f"   Keys: {sorted(d.keys())}")

print("\n" + "=" * 60)
print("  Demo complete. All features operational.")
print("=" * 60)
