#!/usr/bin/env python3
"""
GPT-4o-mini Logprob Substrate — γ Derivation
=============================================
200 prompts × sequential (increasing complexity)
Extract: mean_logprob, var_logprob per response → PSD → γ

PREDICTION (recorded before running): γ ∈ [0.9, 1.1] if metastable.

Author: Yaroslav Vasylenko (neuron7xLab)
"""

import json
import os
import sys
import time

import numpy as np
from scipy.stats import theilslopes

MODEL = "gpt-4o-mini"
N_PROMPTS = 200
MAX_TOKENS = 200
TEMPERATURE = 1.0
OUTPUT_RAW = "/home/neuro7/gpt4o_substrate_raw.json"
OUTPUT_FIG = "/home/neuro7/fig_gpt4o_gamma.png"


def generate_prompts(n):
    rng = np.random.default_rng(42)
    topics = [
        "sorting algorithms", "graph theory", "probability",
        "thermodynamics", "evolution", "game theory", "topology",
        "information theory", "complex systems", "emergence",
        "cellular automata", "neural networks", "optimization",
        "dynamical systems", "category theory", "measure theory",
        "ergodic theory", "renormalization", "phase transitions",
        "self-organization",
    ]
    domains = [
        "cooking", "music", "architecture", "biology",
        "economics", "linguistics", "physics", "philosophy",
    ]
    templates = [
        "Define {t} in exactly {c} words.",
        "Explain {t} using only analogies from {d}.",
        "List {c} non-obvious connections between {t} and {t2}.",
        "In {c} sentences, describe why {t} matters for {t2}.",
        "Construct a {c}-step argument connecting {t} to {d}.",
        "Find {c} hidden assumptions in the claim that {t} is simple.",
        "Write {c} increasingly abstract definitions of {t}.",
        "Compare {t} and {t2} across {c} dimensions.",
    ]
    prompts = []
    for i in range(n):
        c = 3 + (i * 7) // n
        t = topics[i % len(topics)]
        t2 = topics[(i + 7) % len(topics)]
        d = domains[i % len(domains)]
        tmpl = templates[i % len(templates)]
        prompts.append(tmpl.format(t=t, t2=t2, d=d, c=c))
    return prompts


def call_api(client, prompt, retries=3):
    for attempt in range(retries):
        try:
            t0 = time.monotonic()
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                logprobs=True,
                top_logprobs=1,
                messages=[{"role": "user", "content": prompt}],
            )
            lat = time.monotonic() - t0
            ch = resp.choices[0]
            lps = [t.logprob for t in ch.logprobs.content] if ch.logprobs else []
            return {
                "text": ch.message.content,
                "logprobs": lps,
                "n_tokens": len(lps),
                "mean_logprob": float(np.mean(lps)) if lps else 0,
                "var_logprob": float(np.var(lps)) if len(lps) > 1 else 0,
                "min_logprob": float(np.min(lps)) if lps else 0,
                "latency_ms": round(lat * 1000, 1),
            }
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
            else:
                return {"logprobs": [], "n_tokens": 0, "mean_logprob": 0,
                        "var_logprob": 0, "min_logprob": 0, "latency_ms": 0,
                        "text": "", "error": str(e)}


def compute_gamma(series, label="", seed=42):
    n = len(series)
    if n < 20:
        return {"gamma": float("nan"), "beta": float("nan"), "H": float("nan"),
                "r2": 0, "ci": [float("nan")] * 2, "p_perm": float("nan"), "n": n}

    x = series - np.mean(series)
    freqs = np.fft.rfftfreq(n, d=1.0)
    psd = np.abs(np.fft.rfft(x)) ** 2 / n
    mask = freqs > 0
    log_f, log_p = np.log(freqs[mask]), np.log(psd[mask] + 1e-20)

    slope, intc, lo, hi = theilslopes(log_p, log_f)
    beta = -slope
    H = (beta - 1) / 2.0
    gamma = 2 * H + 1  # = beta for fBm. NEVER 2H-1.

    yhat = slope * log_f + intc
    ss_r = np.sum((log_p - yhat) ** 2)
    ss_t = np.sum((log_p - log_p.mean()) ** 2)
    r2 = 1 - ss_r / ss_t if ss_t > 1e-10 else 0

    rng = np.random.default_rng(seed)
    boot = np.empty(2000)
    for i in range(2000):
        idx = rng.choice(len(log_f), len(log_f), replace=True)
        s, _, _, _ = theilslopes(log_p[idx], log_f[idx])
        boot[i] = -s
    ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]

    null = np.empty(10000)
    for i in range(10000):
        s, _, _, _ = theilslopes(rng.permutation(log_p), log_f)
        null[i] = -s
    p_perm = float(np.mean(np.abs(null) >= abs(beta)))

    return {"gamma": round(float(gamma), 4), "beta": round(float(beta), 4),
            "H": round(float(H), 4), "r2": round(float(r2), 4),
            "ci": [round(c, 4) for c in ci], "p_perm": round(p_perm, 4), "n": n}


def main():
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    print("=" * 70)
    print("  PREDICTION: γ ∈ [0.9, 1.1] if GPT-4o-mini is metastable")
    print("=" * 70)

    prompts = generate_prompts(N_PROMPTS)

    # ── Phase 1: Sequential ──
    print(f"\n  PHASE 1: Sequential — {N_PROMPTS} prompts")
    raw = []
    for i, p in enumerate(prompts):
        r = call_api(client, p)
        raw.append({"idx": i, "prompt": p, **r})
        if (i + 1) % 25 == 0:
            print(f"    [{i+1:3d}/{N_PROMPTS}] mean_lp={r['mean_logprob']:.3f}  "
                  f"var_lp={r['var_logprob']:.4f}  n_tok={r['n_tokens']}")
        time.sleep(0.05)

    mean_lp = np.array([r["mean_logprob"] for r in raw])
    var_lp = np.array([r["var_logprob"] for r in raw])

    # ── Phase 2: Control (shuffled) ──
    print(f"\n  PHASE 2: Control (shuffled) — {N_PROMPTS} prompts")
    rng = np.random.default_rng(1042)
    shuf_idx = rng.permutation(N_PROMPTS)
    control_raw = []
    for count, idx in enumerate(shuf_idx):
        r = call_api(client, prompts[idx])
        control_raw.append({"original_idx": int(idx), **r})
        if (count + 1) % 25 == 0:
            print(f"    [{count+1:3d}/{N_PROMPTS}]")
        time.sleep(0.05)

    control_var_lp = np.array([r["var_logprob"] for r in control_raw])

    # ── Compute γ ──
    print(f"\n  COMPUTING γ...")

    # Primary: var_logprob series
    g_var = compute_gamma(var_lp, "var_logprob", seed=42)
    g_ctrl = compute_gamma(control_var_lp, "control", seed=142)

    # Secondary: mean_logprob series
    g_mean = compute_gamma(mean_lp, "mean_logprob", seed=242)

    # ── Save ──
    output = {
        "prediction": "γ ∈ [0.9, 1.1]",
        "model": MODEL,
        "n_prompts": N_PROMPTS,
        "results": {
            "var_logprob": g_var,
            "mean_logprob": g_mean,
            "control_var_logprob": g_ctrl,
        },
        "series": {
            "mean_logprob": mean_lp.tolist(),
            "var_logprob": var_lp.tolist(),
            "control_var_logprob": control_var_lp.tolist(),
        },
        "raw_sequential": raw,
        "raw_control": control_raw,
    }
    with open(OUTPUT_RAW, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  Saved: {OUTPUT_RAW}")

    # ── Figure ──
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # A: time series
    axes[0].plot(var_lp, "-", color="#1f77b4", lw=0.8, alpha=0.7, label="Sequential")
    axes[0].plot(control_var_lp, "-", color="#aaaaaa", lw=0.5, alpha=0.5, label="Control")
    axes[0].set_xlabel("Prompt index")
    axes[0].set_ylabel("σ²(logprob)")
    axes[0].set_title("A. Logprob Variance Series", fontweight="bold")
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)

    # B: PSD
    n = len(var_lp)
    freqs = np.fft.rfftfreq(n, d=1.0)
    psd = np.abs(np.fft.rfft(var_lp - var_lp.mean())) ** 2 / n
    m = freqs > 0
    axes[1].loglog(freqs[m], psd[m], "o", color="#1f77b4", ms=3, alpha=0.5)
    sl, ic, _, _ = theilslopes(np.log(psd[m] + 1e-20), np.log(freqs[m]))
    ff = np.logspace(np.log10(freqs[m].min()), np.log10(freqs[m].max()), 50)
    axes[1].loglog(ff, np.exp(ic) * ff ** sl, "-", color="#d62728", lw=2,
                   label=f"β={-sl:.3f}")
    axes[1].set_xlabel("Frequency")
    axes[1].set_ylabel("PSD")
    axes[1].set_title("B. Power Spectral Density", fontweight="bold")
    axes[1].legend(fontsize=10)
    axes[1].grid(True, alpha=0.3, which="both")

    # C: summary
    dist = abs(g_var["gamma"] - 1.0)
    regime = ("METASTABLE" if dist < 0.15 else "WARNING" if dist < 0.30
              else "CRITICAL" if dist < 0.50 else "COLLAPSE")
    sep = abs(g_var["gamma"] - g_ctrl["gamma"])

    txt = (f"SEQUENTIAL (var_logprob)\n"
           f"  γ = {g_var['gamma']:.4f}\n"
           f"  CI₉₅ = [{g_var['ci'][0]:.3f}, {g_var['ci'][1]:.3f}]\n"
           f"  p = {g_var['p_perm']:.4f}  R² = {g_var['r2']:.4f}\n\n"
           f"CONTROL (shuffled)\n"
           f"  γ = {g_ctrl['gamma']:.4f}\n"
           f"  p = {g_ctrl['p_perm']:.4f}\n\n"
           f"SECONDARY (mean_logprob)\n"
           f"  γ = {g_mean['gamma']:.4f}\n\n"
           f"REGIME: {regime}\n"
           f"Separation: Δγ = {sep:.4f}")

    axes[2].text(0.05, 0.95, txt, transform=axes[2].transAxes, fontsize=10,
                 va="top", fontfamily="monospace",
                 bbox=dict(boxstyle="round", fc="#f8f8f8", ec="gray"))
    axes[2].axis("off")
    axes[2].set_title("C. Results", fontweight="bold")

    fig.suptitle(f"GPT-4o-mini Substrate: γ = {g_var['gamma']:.4f} "
                 f"[{g_var['ci'][0]:.3f}, {g_var['ci'][1]:.3f}]",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_FIG, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"  Saved: {OUTPUT_FIG}")

    # ── Result ──
    print(f"\n{'='*70}")
    hit = 0.9 <= g_var["gamma"] <= 1.1
    print(f"  GPT-4o-mini substrate γ = {g_var['gamma']:.4f} "
          f"[CI: {g_var['ci'][0]:.3f}, {g_var['ci'][1]:.3f}], "
          f"p={g_var['p_perm']:.4f}")
    print(f"  Control γ = {g_ctrl['gamma']:.4f}")
    print(f"  Regime: {regime}")
    print(f"  Prediction (γ ∈ [0.9, 1.1]): {'CONFIRMED' if hit else 'FALSIFIED'}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
