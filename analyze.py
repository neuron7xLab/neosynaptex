"""
NFI v2.1 — Channel B Analyzer
==============================
Derives gamma-proxy from decision latency time series.
No interpretation — only computation and quality gates.

Usage:
    python analyze.py evidence/sessions/session_YYYYMMDD_HHMM/
"""

import json, sys, numpy as np
from pathlib import Path

def check_quality(decisions):
    gates = {
        "sufficient_data": len(decisions) >= 20,
        "has_correct_field": all("correct" in d for d in decisions),
        "has_timestamps": all("t_ns" in d for d in decisions),
        "no_smoothing": True,
    }
    if len(decisions) >= 2:
        t_range_s = (decisions[-1]["t_ns"] - decisions[0]["t_ns"]) / 1e9
        gates["min_duration_ok"] = t_range_s >= 15 * 60
    else:
        gates["min_duration_ok"] = False
    gates["all_pass"] = all(gates.values())
    return gates

def compute_psd_slope(series, fs=1.0):
    if len(series) < 16:
        return {"status": "INSUFFICIENT_DATA", "n": len(series)}
    from scipy import signal
    from scipy.stats import theilslopes
    series = np.asarray(series, dtype=np.float64)
    nperseg = min(len(series), max(16, len(series) // 4))
    freqs, psd = signal.welch(series, fs=fs, nperseg=nperseg, detrend='linear')
    mask = freqs > 0
    freqs, psd = freqs[mask], psd[mask]
    if len(freqs) < 4:
        return {"status": "INSUFFICIENT_FREQ_BINS"}
    log_f = np.log10(freqs)
    log_p = np.log10(psd + 1e-30)
    slope, intercept, lo, hi = theilslopes(log_p, log_f)
    return {
        "status": "OK",
        "beta": round(-slope, 4),
        "slope_raw": round(slope, 4),
        "ci95_lo": round(-hi, 4),
        "ci95_hi": round(-lo, 4),
        "n_freqs": len(freqs),
        "n_samples": len(series),
    }

def compute_stats(decisions):
    lat = np.array([d["latency_ms"] for d in decisions])
    cor = np.array([d["correct"] for d in decisions])
    jitter = np.diff(lat)
    stats = {
        "n_tasks": len(decisions),
        "n_correct": int(cor.sum()),
        "accuracy_pct": round(100 * cor.mean(), 2),
        "latency_mean_ms": round(lat.mean(), 1),
        "latency_median_ms": round(float(np.median(lat)), 1),
        "latency_std_ms": round(float(lat.std()), 1),
        "latency_cv": round(float(lat.std() / lat.mean()), 4) if lat.mean() > 0 else None,
        "jitter_mean_ms": round(float(np.abs(jitter).mean()), 1) if len(jitter) > 0 else None,
        "jitter_std_ms": round(float(jitter.std()), 1) if len(jitter) > 0 else None,
    }
    phases = set(d.get("phase", "baseline") for d in decisions)
    for phase in sorted(phases):
        ph = [d for d in decisions if d.get("phase", "baseline") == phase]
        pl = np.array([d["latency_ms"] for d in ph])
        pc = np.array([d["correct"] for d in ph])
        key = phase.replace(":", "_")
        stats[f"phase_{key}_n"] = len(ph)
        stats[f"phase_{key}_accuracy"] = round(100 * pc.mean(), 2) if len(pc) > 0 else None
        stats[f"phase_{key}_latency_mean"] = round(float(pl.mean()), 1) if len(pl) > 0 else None
    return stats

def compute_phase_contrast(decisions):
    phases = {"baseline": [], "perturbation": [], "recovery": []}
    for d in decisions:
        p = d.get("phase", "baseline")
        if "perturbation" in p: phases["perturbation"].append(d)
        elif "recovery" in p: phases["recovery"].append(d)
        else: phases["baseline"].append(d)
    result = {}
    for name, data in phases.items():
        if len(data) < 3:
            result[name] = {"status": "INSUFFICIENT", "n": len(data)}
            continue
        lat = np.array([d["latency_ms"] for d in data])
        cor = np.array([d["correct"] for d in data])
        result[name] = {
            "n": len(data),
            "accuracy": round(100 * cor.mean(), 2),
            "latency_mean": round(float(lat.mean()), 1),
            "latency_cv": round(float(lat.std() / lat.mean()), 4) if lat.mean() > 0 else None,
        }
    return result

def analyze(session_dir):
    sp = Path(session_dir)
    df = sp / "decisions.jsonl"
    if not df.exists():
        print(f"ERROR: {df} not found."); sys.exit(1)
    with open(df) as f:
        decisions = [json.loads(l) for l in f if l.strip()]
    print(f"\n{'='*60}")
    print(f"  NFI v2.1 — Channel B Analysis: {sp.name}")
    print(f"  Records: {len(decisions)}")
    print(f"{'='*60}\n")
    gates = check_quality(decisions)
    print("  QUALITY GATES:")
    for g, p in gates.items():
        print(f"    {'V' if p else 'X'} {g}")
    print()
    if not gates["has_correct_field"] or not gates["has_timestamps"]:
        print("  FATAL: Missing required fields."); sys.exit(1)
    stats = compute_stats(decisions)
    print("  STATISTICS:")
    for k, v in stats.items():
        if not k.startswith("phase_"): print(f"    {k}: {v}")
    print()
    pk = [k for k in stats if k.startswith("phase_")]
    if pk:
        print("  PHASE BREAKDOWN:")
        for k in pk: print(f"    {k}: {stats[k]}")
        print()
    contrast = compute_phase_contrast(decisions)
    if any(v.get("n", 0) >= 3 for v in contrast.values()):
        print("  PHASE CONTRAST:")
        for ph, d in contrast.items(): print(f"    {ph}: {d}")
        print()
    lat = np.array([d["latency_ms"] for d in decisions])
    if len(decisions) >= 2:
        dt_s = np.diff([d["t_ns"] for d in decisions]) / 1e9
        fs = 1.0 / np.mean(dt_s) if np.mean(dt_s) > 0 else 1.0
    else:
        fs = 1.0
    psd = compute_psd_slope(lat, fs)
    print("  PSD ANALYSIS (latency):")
    for k, v in psd.items(): print(f"    {k}: {v}")
    if psd.get("status") == "OK":
        b = psd["beta"]
        print(f"\n    beta = {b}")
        if b < 0.3: print("      ~white noise (uncorrelated)")
        elif b < 0.7: print("      ~pink-ish (emerging structure)")
        elif b < 1.3: print("      ~1/f (metastable regime)")
        elif b < 1.7: print("      ~Brownian (inertia)")
        else: print("      >1.7 strong persistence (rigidity)")
    print()
    output = {"session": sp.name, "quality_gates": gates, "statistics": stats,
              "phase_contrast": contrast, "psd_latency": psd, "fs_hz": round(fs, 4)}
    of = sp / "analysis.json"
    with open(of, "w") as f: json.dump(output, f, indent=2, default=str)
    print(f"  Saved: {of}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        ss = sorted(Path("evidence/sessions").glob("session_*"))
        if not ss: print("No sessions."); sys.exit(1)
        sd = str(ss[-1]); print(f"  Auto: {sd}")
    else:
        sd = sys.argv[1]
    analyze(sd)
