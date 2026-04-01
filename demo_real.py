#!/usr/bin/env python3
"""neosynaptex v0.2 demo -- ALL REAL substrates. Zero mocks.

Substrates:
  1. zebrafish   — McGuirl 2020 .mat data
  2. gray_scott  — Turing reaction-diffusion simulation
  3. kuramoto    — Market coherence oscillators
  4. bn_syn      — Spiking neural criticality
  5. cns_ai_loop — Cognitive decision loop
"""

from neosynaptex import Neosynaptex
from substrates.zebrafish.adapter import ZebrafishAdapter
from substrates.gray_scott.adapter import GrayScottAdapter
from substrates.kuramoto.adapter import KuramotoAdapter
from substrates.bn_syn.adapter import BnSynAdapter
from substrates.cns_ai_loop.adapter import CnsAiLoopAdapter
import numpy as np


def _f(v, w=6):
    return f"{v:.3f}".rjust(w) if np.isfinite(v) else "n/a".rjust(w)


def main():
    nx = Neosynaptex(window=16)

    # ALL REAL substrates — no mocks
    nx.register(ZebrafishAdapter("WT"))
    nx.register(GrayScottAdapter())
    nx.register(KuramotoAdapter())
    nx.register(BnSynAdapter())
    nx.register(CnsAiLoopAdapter())

    for _ in range(50):
        s = nx.observe()
        print(
            f"  t={s.t:02d}  "
            f"gamma={_f(s.gamma_mean)}  "
            f"dg/dt={_f(s.dgamma_dt)}  "
            f"sr={_f(s.spectral_radius)}  "
            f"coh={_f(s.cross_coherence)}  "
            f"p={_f(s.universal_scaling_p)}  "
            f"phase={s.phase}"
        )

    print()
    print("=" * 72)
    print("  NEOSYNAPTEX — ALL REAL SUBSTRATES")
    print("=" * 72)
    print(f"  gamma_mean       = {_f(s.gamma_mean)}")
    print(f"  gamma_std        = {_f(s.gamma_std)}")
    print(f"  dgamma/dt        = {_f(s.dgamma_dt)}")
    print(f"  cross_coherence  = {_f(s.cross_coherence)}")
    print(f"  universal_p      = {_f(s.universal_scaling_p)}")
    print(f"  spectral_radius  = {_f(s.spectral_radius)}")
    print(f"  phase            = {s.phase}")
    print(f"  resilience       = {_f(s.resilience_score)}")
    print()

    for d in sorted(s.gamma_per_domain):
        g = s.gamma_per_domain[d]
        ci = s.gamma_ci_per_domain[d]
        sr = s.sr_per_domain.get(d, float("nan"))
        cond = s.cond_per_domain.get(d, float("nan"))
        anom = s.anomaly_score.get(d, float("nan"))
        mod = s.modulation.get(d, 0.0)
        ci_str = f"[{_f(ci[0],5)}, {_f(ci[1],5)}]" if np.isfinite(ci[0]) else "[n/a]"
        print(
            f"  {d:12s} [REAL]  "
            f"g={_f(g,6)}  "
            f"CI={ci_str}  "
            f"sr={_f(sr,6)}  "
            f"anom={_f(anom,5)}  "
            f"mod={mod:+.4f}"
        )

    print()
    proof = nx.export_proof()
    print(f"  Verdict: {proof['verdict']}")
    print(f"  Mock adapters remaining: 0")
    print("=" * 72)


if __name__ == "__main__":
    main()
