#!/usr/bin/env python3
"""MFN Quickstart — full diagnostic pipeline demonstration.

Run: python examples/quickstart.py
"""

import mycelium_fractal_net as mfn

# ── 1. Simulate a biophysical field ──────────────────────────
spec = mfn.SimulationSpec(grid_size=32, steps=60, seed=42)
seq = mfn.simulate(spec)
print(f"Simulated: {seq}")

# ── 2. Full diagnosis in one call ────────────────────────────
report = mfn.diagnose(seq)
print(f"\n{report.summary()}")
print(report.narrative)
print(f"  is_ok: {report.is_ok()}")
print(f"  needs_intervention: {report.needs_intervention()}")

# ── 3. Ensemble diagnosis (statistical confidence) ───────────
ensemble = mfn.ensemble_diagnose(spec, n_runs=5)
print(f"\n{ensemble.summary()}")
print(f"  robust: {ensemble.is_robust()}")

# ── 4. Temporal monitoring ───────────────────────────────────
print("\nWatch (3 ticks):")
reports = mfn.watch(spec, n_steps_per_tick=20, n_ticks=3)
for i, r in enumerate(reports):
    print(f"  tick {i}: {r.severity} ews={r.warning.ews_score:.3f}")

# ── 5. Temporal diff ─────────────────────────────────────────
if len(reports) >= 2:
    diff = reports[0].diff(reports[-1])
    print(f"\n{diff.summary()}")

# ── 6. Individual pipeline stages ────────────────────────────
print(f"\nDetection: {seq.detect()}")
print(f"Forecast:  {seq.forecast(4)}")
print(
    f"EWS:       ews={mfn.early_warning(seq).ews_score:.3f} type={mfn.early_warning(seq).transition_type}"
)
