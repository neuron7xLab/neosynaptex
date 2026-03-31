#!/usr/bin/env python3
"""neosynaptex v0.2 demo -- full mirror diagnostic."""

from neosynaptex import (
    MockBnSynAdapter, MockMarketAdapter, MockMfnAdapter,
    MockPsycheCoreAdapter, Neosynaptex,
)
import numpy as np


def _f(v, w=6):
    return f"{v:.3f}".rjust(w) if np.isfinite(v) else "n/a".rjust(w)


def main():
    nx = Neosynaptex(window=16)
    nx.register(MockBnSynAdapter())
    nx.register(MockMfnAdapter())
    nx.register(MockPsycheCoreAdapter())
    nx.register(MockMarketAdapter())

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
            f"  {d:8s}  "
            f"g={_f(g,6)}  "
            f"CI={ci_str}  "
            f"sr={_f(sr,6)}  "
            f"cond={_f(cond,8)}  "
            f"anom={_f(anom,5)}  "
            f"mod={mod:+.4f}"
        )

    print()
    print("  Granger causality (F-stat):")
    for src, targets in sorted(s.granger_graph.items()):
        for tgt, f_val in sorted(targets.items()):
            if np.isfinite(f_val) and f_val > 1.0:
                print(f"    {src} -> {tgt}: F={f_val:.2f}")

    print()
    p = s.portrait
    print(f"  Phase portrait: area={_f(p.get('area', float('nan')))}"
          f"  recurrence={_f(p.get('recurrence', float('nan')))}"
          f"  dist_ideal={_f(p.get('distance_to_ideal', float('nan')))}")

    print()
    proof = nx.export_proof()
    print(f"  Verdict: {proof['verdict']}")
    print("=" * 72)


if __name__ == "__main__":
    main()
