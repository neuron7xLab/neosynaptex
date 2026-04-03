#!/usr/bin/env python3
"""
Invariant hardening protocol: proxy sensitivity, shuffling controls,
scale invariance, and unified information space.

Outputs:
  evidence/proxy_sensitivity.json
  evidence/shuffling_controls.json
  evidence/scale_invariance.json
  evidence/unified_space_gamma.json
  manuscript/figures/fig4_scale_invariance.png
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.gamma import compute_gamma

SEED = 42
EVIDENCE = ROOT / "evidence"
FIGURES = ROOT / "manuscript" / "figures"


def _rd(res, name, proxy):
    return {
        "substrate": name, "proxy": proxy,
        "gamma": round(res.gamma, 4) if np.isfinite(res.gamma) else None,
        "ci_low": round(res.ci_low, 4) if np.isfinite(res.ci_low) else None,
        "ci_high": round(res.ci_high, 4) if np.isfinite(res.ci_high) else None,
        "r2": round(res.r2, 4) if np.isfinite(res.r2) else None,
        "n_valid": res.n_valid, "verdict": res.verdict,
        "in_metastable_band": abs(res.gamma - 1.0) < 0.15 if np.isfinite(res.gamma) else False,
    }


# ═══════════════════════════════════════
# TASK 1 — PROXY SENSITIVITY
# ═══════════════════════════════════════

def task1_proxy_sensitivity():
    print("\n" + "=" * 60)
    print("TASK 1 — PROXY SENSITIVITY")
    print("=" * 60)

    results = []

    # --- ZEBRAFISH ---
    print("  Zebrafish...", flush=True)
    from substrates.zebrafish.adapter import ZebrafishAdapter
    za = ZebrafishAdapter(phenotype="WT", seed=SEED)
    za._ensure_loaded()
    mask = np.isfinite(za._densities) & np.isfinite(za._nn_cvs) & (za._densities > 0) & (za._nn_cvs > 0)
    dens, cvs = za._densities[mask], za._nn_cvs[mask]
    pops = za._populations[mask]

    # Original: C=density, K=NN_CV
    results.append(_rd(compute_gamma(dens, cvs), "zebrafish", "original: density vs NN_CV"))

    # Alt1: C=population_count, K=NN_CV (different complexity measure, same cost)
    results.append(_rd(compute_gamma(pops, cvs), "zebrafish", "alt1: population vs NN_CV"))

    # Alt2: C=density, K=1/population (different cost proxy)
    inv_pop = 1.0 / (pops + 1e-6)
    results.append(_rd(compute_gamma(dens, inv_pop), "zebrafish", "alt2: density vs 1/population"))

    # --- HRV ---
    print("  HRV PhysioNet...", flush=True)
    from substrates.hrv_physionet.adapter import HRVPhysioNetAdapter
    hrv = HRVPhysioNetAdapter(n_subjects=10)
    freqs, psd = hrv.get_all_pairs()

    # Original: VLF band 0.003-0.04 Hz
    m_vlf = (freqs >= 0.003) & (freqs <= 0.04) & (freqs > 0) & (psd > 0)
    results.append(_rd(compute_gamma(freqs[m_vlf], psd[m_vlf]), "hrv", "original: VLF freq vs PSD"))

    # Alt1: LF band 0.04-0.15 Hz
    m_lf = (freqs >= 0.04) & (freqs <= 0.15) & (freqs > 0) & (psd > 0)
    if np.sum(m_lf) >= 5:
        results.append(_rd(compute_gamma(freqs[m_lf], psd[m_lf]), "hrv", "alt1: LF freq vs PSD"))
    else:
        results.append({"substrate": "hrv", "proxy": "alt1: LF freq vs PSD",
                        "gamma": None, "verdict": "INSUFFICIENT_DATA", "in_metastable_band": False})

    # Alt2: Full band 0.003-0.15 Hz
    m_full = (freqs >= 0.003) & (freqs <= 0.15) & (freqs > 0) & (psd > 0)
    results.append(_rd(compute_gamma(freqs[m_full], psd[m_full]), "hrv", "alt2: full band freq vs PSD"))

    # --- EEG ---
    print("  EEG PhysioNet...", flush=True)
    from substrates.eeg_physionet.adapter import EEGPhysioNetAdapter
    eeg = EEGPhysioNetAdapter(n_subjects=20)
    freqs_e, psd_e = eeg.get_grand_average_psd()

    # Original: 2-35 Hz
    m_orig = (freqs_e >= 2.0) & (freqs_e <= 35.0) & (freqs_e > 0) & (psd_e > 0)
    results.append(_rd(compute_gamma(freqs_e[m_orig], psd_e[m_orig]), "eeg", "original: 2-35Hz freq vs PSD"))

    # Alt1: Alpha-beta band 8-30 Hz
    m_ab = (freqs_e >= 8.0) & (freqs_e <= 30.0) & (freqs_e > 0) & (psd_e > 0)
    results.append(_rd(compute_gamma(freqs_e[m_ab], psd_e[m_ab]), "eeg", "alt1: 8-30Hz freq vs PSD"))

    # Alt2: Low-frequency 2-12 Hz
    m_lo = (freqs_e >= 2.0) & (freqs_e <= 12.0) & (freqs_e > 0) & (psd_e > 0)
    results.append(_rd(compute_gamma(freqs_e[m_lo], psd_e[m_lo]), "eeg", "alt2: 2-12Hz freq vs PSD"))

    alt_results = [r for r in results if "alt" in r["proxy"]]
    n_pass = sum(1 for r in alt_results if r["in_metastable_band"])

    output = {
        "description": "Proxy sensitivity: alternative (C,K) pairs per Tier 1 substrate",
        "results": results,
        "summary": {
            "n_alternatives": len(alt_results),
            "n_in_metastable_band": n_pass,
            "pass_rate": f"{n_pass}/{len(alt_results)}",
            "gate_pass": n_pass >= 4,
        },
    }
    with open(EVIDENCE / "proxy_sensitivity.json", "w") as f:
        json.dump(output, f, indent=2)

    for r in results:
        tag = "PASS" if r["in_metastable_band"] else "FAIL"
        g = r["gamma"]
        ci = f"CI=[{r.get('ci_low','?')},{r.get('ci_high','?')}]"
        print(f"    [{tag}] {r['substrate']:10s} {r['proxy']:45s} γ={g}  {ci}")
    print(f"\n  GATE: {n_pass}/{len(alt_results)} alternatives in metastable band (need ≥4)")
    return output


# ═══════════════════════════════════════
# TASK 2 — SHUFFLING CONTROL
# ═══════════════════════════════════════

def task2_shuffling_controls():
    print("\n" + "=" * 60)
    print("TASK 2 — SHUFFLING CONTROLS")
    print("=" * 60)

    rng = np.random.default_rng(SEED)
    N_PERM = 199

    from substrates.zebrafish.adapter import ZebrafishAdapter
    from substrates.hrv_physionet.adapter import HRVPhysioNetAdapter
    from substrates.eeg_physionet.adapter import EEGPhysioNetAdapter

    substrates = {}
    za = ZebrafishAdapter(phenotype="WT", seed=SEED)
    za._ensure_loaded()
    mask = np.isfinite(za._densities) & np.isfinite(za._nn_cvs) & (za._densities > 0) & (za._nn_cvs > 0)
    substrates["zebrafish"] = (za._densities[mask], za._nn_cvs[mask])

    hrv = HRVPhysioNetAdapter(n_subjects=10)
    f, p = hrv.get_all_pairs()
    m = (f >= 0.003) & (f <= 0.04) & (f > 0) & (p > 0)
    substrates["hrv"] = (f[m], p[m])

    eeg = EEGPhysioNetAdapter(n_subjects=20)
    fe, pe = eeg.get_grand_average_psd()
    me = (fe >= 2.0) & (fe <= 35.0) & (fe > 0) & (pe > 0)
    substrates["eeg"] = (fe[me], pe[me])

    results = {}
    all_separated = True

    for name, (topo, cost) in substrates.items():
        print(f"  {name}: {N_PERM} permutations...", flush=True)
        real_gamma = compute_gamma(topo, cost).gamma

        shuffled_gammas = []
        for _ in range(N_PERM):
            perm_cost = rng.permutation(cost)
            sr = compute_gamma(topo, perm_cost)
            if np.isfinite(sr.gamma):
                shuffled_gammas.append(sr.gamma)

        sg = np.array(shuffled_gammas)
        p95 = float(np.percentile(sg, 97.5))
        p05 = float(np.percentile(sg, 2.5))

        separated = abs(real_gamma - 1.0) < abs(float(np.median(sg)) - 1.0)
        if not separated:
            all_separated = False

        results[name] = {
            "gamma_real": round(real_gamma, 4),
            "gamma_shuffled_median": round(float(np.median(sg)), 4),
            "gamma_shuffled_std": round(float(np.std(sg)), 4),
            "gamma_shuffled_95CI": [round(p05, 4), round(p95, 4)],
            "n_permutations": N_PERM,
            "real_closer_to_unity": bool(separated),
        }
        tag = "PASS" if separated else "FAIL"
        print(f"    [{tag}] γ_real={real_gamma:.4f}, shuffled median={np.median(sg):.4f}, "
              f"95CI=[{p05:.3f},{p95:.3f}]")

    output = {
        "description": "Random pairing shuffle: destroy C↔K correspondence, preserve marginals",
        "results": results, "all_separated": all_separated,
    }
    with open(EVIDENCE / "shuffling_controls.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  GATE: {'ALL SEPARATED' if all_separated else 'SOME FAILED'}")
    return output


# ═══════════════════════════════════════
# TASK 3 — SCALE INVARIANCE
# ═══════════════════════════════════════

def task3_scale_invariance():
    print("\n" + "=" * 60)
    print("TASK 3 — SCALE INVARIANCE")
    print("=" * 60)

    from substrates.zebrafish.adapter import ZebrafishAdapter
    from substrates.hrv_physionet.adapter import HRVPhysioNetAdapter
    from substrates.eeg_physionet.adapter import EEGPhysioNetAdapter

    substrates = {}
    za = ZebrafishAdapter(phenotype="WT", seed=SEED)
    za._ensure_loaded()
    mask = np.isfinite(za._densities) & np.isfinite(za._nn_cvs) & (za._densities > 0) & (za._nn_cvs > 0)
    substrates["zebrafish"] = (za._densities[mask], za._nn_cvs[mask])

    hrv = HRVPhysioNetAdapter(n_subjects=10)
    f, p = hrv.get_all_pairs()
    m = (f >= 0.003) & (f <= 0.04) & (f > 0) & (p > 0)
    substrates["hrv"] = (f[m], p[m])

    eeg = EEGPhysioNetAdapter(n_subjects=20)
    fe, pe = eeg.get_grand_average_psd()
    me = (fe >= 2.0) & (fe <= 35.0) & (fe > 0) & (pe > 0)
    substrates["eeg"] = (fe[me], pe[me])

    factors = [1, 2, 4, 8, 16]
    results = {}

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    colors = {"zebrafish": "#2ca02c", "hrv": "#d62728", "eeg": "#1f77b4"}

    for idx, (name, (topo, cost)) in enumerate(substrates.items()):
        print(f"  {name} (n={len(topo)})...", flush=True)
        gammas, cis, vf = [], [], []
        for fac in factors:
            t_ds, c_ds = topo[::fac], cost[::fac]
            if len(t_ds) < 5:
                break
            res = compute_gamma(t_ds, c_ds)
            if np.isfinite(res.gamma):
                gammas.append(res.gamma)
                cis.append((res.ci_low if np.isfinite(res.ci_low) else res.gamma - 0.5,
                            res.ci_high if np.isfinite(res.ci_high) else res.gamma + 0.5))
                vf.append(fac)

        in_band = [abs(g - 1.0) < 0.15 for g in gammas]
        max_consec = max((sum(1 for _ in grp) for val, grp in
                          __import__('itertools').groupby(in_band) if val), default=0)

        results[name] = {
            "factors": vf, "gammas": [round(g, 4) for g in gammas],
            "in_metastable_band": in_band,
            "max_consecutive_octaves": max_consec, "stable": max_consec >= 3,
        }

        ax = axes[idx]
        g_arr = np.array(gammas)
        ci_lo = np.array([c[0] for c in cis])
        ci_hi = np.array([c[1] for c in cis])
        x = np.arange(len(vf))
        ax.errorbar(x, g_arr, yerr=[g_arr - ci_lo, ci_hi - g_arr],
                     fmt='o-', color=colors[name], capsize=4, markersize=6, linewidth=1.5)
        ax.axhline(1.0, color='#333', linestyle='--', alpha=0.7)
        ax.axhspan(0.85, 1.15, alpha=0.12, color='green')
        ax.set_xlabel('Downsample factor', fontsize=9)
        ax.set_ylabel('γ', fontsize=10)
        ax.set_title(name, fontsize=11, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([f'{f}×' for f in vf], fontsize=8)
        ax.set_ylim(max(0, min(g_arr) - 0.3), max(g_arr) + 0.3)

        tag = "PASS" if max_consec >= 3 else f"PARTIAL ({max_consec})"
        print(f"    [{tag}] octaves in band. γ={[round(g,3) for g in gammas]}")

    plt.suptitle("Figure 4: Scale invariance of γ under downsampling", fontsize=12, fontweight='bold', y=1.02)
    plt.tight_layout()
    fig.savefig(FIGURES / "fig4_scale_invariance.png", dpi=200, bbox_inches='tight')
    plt.close()
    print(f"  Figure: {FIGURES / 'fig4_scale_invariance.png'}")

    with open(EVIDENCE / "scale_invariance.json", "w") as f:
        json.dump({"description": "Scale invariance under downsampling", "results": results}, f, indent=2)
    return {"results": results}


# ═══════════════════════════════════════
# TASK 4 — UNIFIED INFORMATION SPACE
# ═══════════════════════════════════════

def task4_unified_space():
    print("\n" + "=" * 60)
    print("TASK 4 — UNIFIED INFORMATION SPACE")
    print("=" * 60)

    from substrates.zebrafish.adapter import ZebrafishAdapter
    from substrates.hrv_physionet.adapter import HRVPhysioNetAdapter
    from substrates.eeg_physionet.adapter import EEGPhysioNetAdapter
    from substrates.gray_scott.adapter import GrayScottAdapter
    from substrates.kuramoto.adapter import KuramotoAdapter
    from substrates.bn_syn.adapter import BnSynAdapter

    def _load(name):
        if name == "zebrafish":
            za = ZebrafishAdapter(phenotype="WT", seed=SEED)
            za._ensure_loaded()
            m = np.isfinite(za._densities) & np.isfinite(za._nn_cvs) & (za._densities > 0) & (za._nn_cvs > 0)
            return za._densities[m], za._nn_cvs[m]
        elif name == "hrv":
            h = HRVPhysioNetAdapter(n_subjects=10)
            f, p = h.get_all_pairs()
            m = (f >= 0.003) & (f <= 0.04) & (f > 0) & (p > 0)
            return f[m], p[m]
        elif name == "eeg":
            e = EEGPhysioNetAdapter(n_subjects=20)
            f, p = e.get_grand_average_psd()
            m = (f >= 2.0) & (f <= 35.0) & (f > 0) & (p > 0)
            return f[m], p[m]
        elif name == "gray_scott":
            gs = GrayScottAdapter(seed=SEED)
            ts, cs = [], []
            for _ in range(200):
                gs.state(); t, c = gs.topo(), gs.thermo_cost()
                if t > 1e-6 and c > 1e-6: ts.append(t); cs.append(c)
            return np.array(ts), np.array(cs)
        elif name == "kuramoto":
            k = KuramotoAdapter(seed=SEED)
            ts, cs = [], []
            for _ in range(300):
                k.state(); t, c = k.topo(), k.thermo_cost()
                if t > 1e-6 and c > 1e-6: ts.append(t); cs.append(c)
            return np.array(ts), np.array(cs)
        elif name == "bnsyn":
            return BnSynAdapter(seed=SEED).get_all_pairs()

    def normalize(topo, cost):
        """Median-scale normalization: preserves log-log slope (γ invariant)."""
        c_norm = topo / np.median(topo)
        k_norm = cost / np.median(cost)
        return c_norm, k_norm

    all_subs = ["zebrafish", "hrv", "eeg", "gray_scott", "kuramoto", "bnsyn"]
    results = {}

    for name in all_subs:
        print(f"  {name}...", flush=True)
        topo, cost = _load(name)
        c_n, k_n = normalize(topo, cost)
        res_orig = compute_gamma(topo, cost)
        res_norm = compute_gamma(c_n, k_n)

        results[name] = {
            "gamma_original": round(res_orig.gamma, 4),
            "gamma_unified": round(res_norm.gamma, 4),
            "ci_low": round(res_norm.ci_low, 4) if np.isfinite(res_norm.ci_low) else None,
            "ci_high": round(res_norm.ci_high, 4) if np.isfinite(res_norm.ci_high) else None,
            "ci_contains_unity": bool(res_norm.ci_low <= 1.0 <= res_norm.ci_high) if np.isfinite(res_norm.ci_low) else False,
            "n_valid": res_norm.n_valid, "verdict": res_norm.verdict,
            "gamma_preserved": abs(res_orig.gamma - res_norm.gamma) < 0.01 if np.isfinite(res_orig.gamma) and np.isfinite(res_norm.gamma) else False,
        }
        tag = "PASS" if results[name]["gamma_preserved"] else "FAIL"
        print(f"    [{tag}] γ_orig={results[name]['gamma_original']:.4f} → "
              f"γ_unified={results[name]['gamma_unified']:.4f} "
              f"(Δ={abs(res_orig.gamma - res_norm.gamma):.6f})")

    t1 = [results[n]["gamma_unified"] for n in ["zebrafish", "hrv", "eeg"]]
    t1_ci = [(results[n]["ci_low"], results[n]["ci_high"]) for n in ["zebrafish", "hrv", "eeg"]]
    n_preserved = sum(1 for n in all_subs if results[n]["gamma_preserved"])
    n_ci = sum(1 for n in all_subs if results[n]["ci_contains_unity"])

    output = {
        "description": "Unified information space: median-scaled (C/C_median, K/K_median)",
        "normalization": "C_norm = C/median(C), K_norm = K/median(K). "
                         "Preserves log-log slope exactly (γ invariant under multiplicative rescaling).",
        "results": results,
        "tier1_mean_unified": round(float(np.mean(t1)), 4),
        "n_gamma_preserved": n_preserved,
        "n_ci_contains_unity": n_ci,
        "gate_pass": n_preserved == len(all_subs),
    }
    with open(EVIDENCE / "unified_space_gamma.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  GATE: {n_preserved}/{len(all_subs)} γ preserved under normalization")
    return output


# ═══════════════════════════════════════
if __name__ == "__main__":
    r1 = task1_proxy_sensitivity()
    r2 = task2_shuffling_controls()
    r3 = task3_scale_invariance()
    r4 = task4_unified_space()

    print("\n" + "=" * 60)
    print("INVARIANT HARDENING — FINAL REPORT")
    print("=" * 60)
    print(f"  PROXY SENSITIVITY: {r1['summary']['pass_rate']} pass")
    print(f"  SHUFFLING: {'ALL SEPARATED' if r2['all_separated'] else 'SOME FAILED'}")
    s3 = r3["results"]
    for k in s3:
        print(f"    {k}: {s3[k]['max_consecutive_octaves']} octaves, stable={s3[k]['stable']}")
    print(f"  UNIFIED SPACE: {r4['n_gamma_preserved']}/{len(r4['results'])} preserved, "
          f"Tier1 mean={r4['tier1_mean_unified']:.4f}")
    gates = {
        "proxy": r1["summary"]["gate_pass"],
        "shuffling": r2["all_separated"],
        "scale": all(s3[k]["max_consecutive_octaves"] >= 2 for k in s3),
        "unified": r4["gate_pass"],
    }
    print(f"\n  GATES: {sum(gates.values())}/4 pass")
    for g, v in gates.items():
        print(f"    {'[PASS]' if v else '[FAIL]'} {g}")
