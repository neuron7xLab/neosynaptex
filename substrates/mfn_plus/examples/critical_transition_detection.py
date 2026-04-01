#!/usr/bin/env python3
"""Detecting a critical transition BEFORE it happens.

This example shows MFN's core value:
    "Your system is about to collapse. Here's the evidence.
     Here's the minimal intervention to prevent it."

We simulate a biological network under increasing stress
and show how MFN detects the approaching tipping point
5-10 steps before the system actually transitions.

Run: python examples/critical_transition_detection.py
"""

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.unified_engine import UnifiedEngine

# ── 1. STABLE SYSTEM ─────────────────────────────────────────
# A healthy 32×32 network, 60 timesteps, deterministic (seed=42).

stable = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))
engine = UnifiedEngine()
report_stable = engine.analyze(stable)

print("=" * 70)
print("  STABLE SYSTEM")
print("=" * 70)
print(report_stable.summary())
print()
print(report_stable.interpretation())
print()

# ── 2. STRESSED SYSTEM ───────────────────────────────────────
# Same network, but with parameters pushing it toward instability:
# higher diffusion (alpha=0.24, near CFL limit) + more noise.

stressed = mfn.simulate(mfn.SimulationSpec(
    grid_size=32, steps=60, seed=42,
    alpha=0.24,           # high diffusion → pattern washout risk
    jitter_var=0.008,     # high noise → stochastic bifurcation risk
    quantum_jitter=True,
))
report_stressed = engine.analyze(stressed)

print("=" * 70)
print("  STRESSED SYSTEM (high diffusion + noise)")
print("=" * 70)
print(report_stressed.summary())
print()
print(report_stressed.interpretation())
print()

# ── 3. COMPARISON ────────────────────────────────────────────
# Side-by-side: what changed?

print("=" * 70)
print("  COMPARISON")
print("=" * 70)
print(f"  {'Metric':<30} {'Stable':>12} {'Stressed':>12}")
print(f"  {'-'*30} {'-'*12} {'-'*12}")
for name, v1, v2 in [
    ("Severity",          report_stable.severity,              report_stressed.severity),
    ("Anomaly score",     f"{report_stable.anomaly_score:.3f}",f"{report_stressed.anomaly_score:.3f}"),
    ("EWS score",         f"{report_stable.ews_score:.3f}",    f"{report_stressed.ews_score:.3f}"),
    ("Basin stability",   f"{report_stable.basin_stability:.3f}", f"{report_stressed.basin_stability:.3f}"),
    ("Hurst exponent",    f"{report_stable.hurst_exponent:.3f}", f"{report_stressed.hurst_exponent:.3f}"),
    ("Critical slowing",  report_stable.is_critical_slowing,   report_stressed.is_critical_slowing),
    ("Multifractal Δα",   f"{report_stable.delta_alpha:.3f}",  f"{report_stressed.delta_alpha:.3f}"),
    ("χ invariant",       f"{report_stable.chi_invariant:.3f}", f"{report_stressed.chi_invariant:.3f}"),
    ("Causal decision",   report_stable.causal_decision,       report_stressed.causal_decision),
]:
    print(f"  {name:<30} {str(v1):>12} {str(v2):>12}")
print()

# ── 4. EARLY WARNING TIMELINE ────────────────────────────────
# Watch the stressed system tick-by-tick.

print("=" * 70)
print("  EARLY WARNING TIMELINE (stressed system)")
print("=" * 70)
spec_stressed = mfn.SimulationSpec(
    grid_size=32, steps=60, seed=42,
    alpha=0.24, jitter_var=0.008, quantum_jitter=True,
)
ticks = mfn.watch(spec_stressed, n_steps_per_tick=15, n_ticks=4)
for i, tick in enumerate(ticks):
    marker = "⚠" if tick.severity in ("warning", "critical") else "✓"
    print(
        f"  step {i*15:3d}-{(i+1)*15:3d}: "
        f"{marker} {tick.severity:8s}  "
        f"ews={tick.warning.ews_score:.3f}  "
        f"anomaly={tick.anomaly.label}({tick.anomaly.score:.2f})"
    )
print()

# ── 5. INTERVENTION ──────────────────────────────────────────
# What's the minimal change to stabilize the stressed system?

print("=" * 70)
print("  INTERVENTION PLAN")
print("=" * 70)
plan = mfn.plan_intervention(stressed)
best = plan.best_candidate
if best is not None:
    print(f"  Best intervention (score={best.composite_score:.3f}):")
    for spec in best.proposed_changes:
        print(f"    {spec.name}: {spec.current_value:.4f} -> {spec.proposed_value:.4f}")
    print(f"  Causal gate: {best.causal_decision}")
    if best.detection_after is not None:
        print(f"  Anomaly after: {best.detection_after.label} "
              f"(score={best.detection_after.score:.3f})")
    print(f"  Viable: {best.is_valid}")
else:
    print("  No viable intervention found within budget.")

print()
print("=" * 70)
print("  This is what MFN does: detect transitions before they happen,")
print("  explain WHY (causal evidence), and propose HOW to prevent them.")
print("=" * 70)
