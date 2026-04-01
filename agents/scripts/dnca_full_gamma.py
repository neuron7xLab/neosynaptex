#!/usr/bin/env python3
"""DNCA Full Gamma Validation — state_dim=64, n_steps=1000, seed=42."""

import time
import torch
import numpy as np

from neuron7x_agents.dnca import DNCA
from neuron7x_agents.dnca.probes.gamma_probe import BNSynGammaProbe

torch.manual_seed(42)
np.random.seed(42)

# Full parameters
dnca = DNCA(state_dim=64, seed=42)
probe = BNSynGammaProbe(window_size=100, n_bootstrap=500, seed=42)

print("=" * 60)
print("DNCA FULL GAMMA VALIDATION")
print(f"  state_dim = 64, n_steps = 1000, seed = 42")
print(f"  window_size = 100, n_bootstrap = 500")
print("=" * 60)

t0 = time.time()
print("\nRunning DNCA 1000 steps, state_dim=64...")
nmo_report, pred_report, ctrl_report = probe.run(dnca, n_steps=1000)
elapsed = time.time() - t0

print(f"\nRuntime: {elapsed:.1f}s ({elapsed/60:.1f} min)")

# Primary measurement (NMO activity field)
print(f"\n=== NMO ACTIVITY FIELD ===")
print(f"γ_DNCA     = {nmo_report.gamma:.3f}")
print(f"CI 95%     = [{nmo_report.ci_low:.3f}, {nmo_report.ci_high:.3f}]")
print(f"R²         = {nmo_report.r2:.4f}")
print(f"n_pairs    = {nmo_report.n_pairs}")
print(f"verdict    = {nmo_report.verdict}")

# Prediction error field
print(f"\n=== PREDICTION ERROR FIELD ===")
print(f"γ_pred     = {pred_report.gamma:.3f}")
print(f"CI 95%     = [{pred_report.ci_low:.3f}, {pred_report.ci_high:.3f}]")
print(f"R²         = {pred_report.r2:.4f}")
print(f"n_pairs    = {pred_report.n_pairs}")
print(f"verdict    = {pred_report.verdict}")

# Control
print(f"\n=== CONTROL (SHUFFLED) ===")
print(f"γ_control  = {ctrl_report.gamma:.3f}")
print(f"CI control = [{ctrl_report.ci_low:.3f}, {ctrl_report.ci_high:.3f}]")
print(f"R²         = {ctrl_report.r2:.4f}")
print(f"verdict    = {ctrl_report.verdict}")

# Use the best measurement (NMO activity)
result = nmo_report

# Overlap check with bio range
bio_lower, bio_upper = 0.865, 1.081
dnca_lower = result.ci_low
dnca_upper = result.ci_high
overlap = max(0, min(dnca_upper, bio_upper) - max(dnca_lower, bio_lower))

print(f"\n=== OVERLAP CHECK ===")
print(f"DNCA CI:   [{dnca_lower:.3f}, {dnca_upper:.3f}]")
print(f"Bio range: [{bio_lower:.3f}, {bio_upper:.3f}]")
print(f"Overlap:   {overlap:.3f}")
print(f"Verdict:   {'UNIFIED' if overlap > 0 else 'DIVERGENT'}")

# Gate checks
g1 = result.gamma > 0 and result.r2 > 0.1
g2 = -0.1 <= ctrl_report.gamma <= 0.3
g3 = overlap > 0
g4 = result.n_pairs >= 50
gates = sum([g1, g2, g3, g4])

print(f"\n=== GATES ===")
print(f"G1 (γ>0, R²>0.1): {'PASS' if g1 else 'FAIL'} (γ={result.gamma:.3f}, R²={result.r2:.4f})")
print(f"G2 (ctrl∈[-0.1,0.3]): {'PASS' if g2 else 'FAIL'} (γ_ctrl={ctrl_report.gamma:.3f})")
print(f"G3 (CI overlap): {'PASS' if g3 else 'FAIL'} (overlap={overlap:.3f})")
print(f"G4 (n_pairs≥50): {'PASS' if g4 else 'FAIL'} (n={result.n_pairs})")
print(f"Gates passed: {gates}/4")

print(f"\n{'='*60}")
print(f"DNCA FULL GAMMA — FINAL REPORT")
print(f"  γ_DNCA_full  : {result.gamma:.3f}")
print(f"  CI 95%       : [{result.ci_low:.3f}, {result.ci_high:.3f}]")
print(f"  R²           : {result.r2:.4f}")
print(f"  n_pairs      : {result.n_pairs}")
print(f"  γ_control    : {ctrl_report.gamma:.3f}")
print(f"  Overlap      : {overlap:.3f}")
print(f"  Verdict      : {'UNIFIED' if overlap > 0 else 'DIVERGENT'}")
print(f"  Runtime      : {elapsed:.1f}s")
print(f"  Gates        : {gates}/4")
print(f"{'='*60}")
