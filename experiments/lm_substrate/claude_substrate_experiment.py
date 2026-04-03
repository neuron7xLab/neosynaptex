#!/usr/bin/env python3
"""
Claude Self-Consistency Substrate — γ Derivation
=================================================
200 prompts × 3 repeats × temperature=1.0
Measure: variance of response lengths per prompt → PSD → γ

PREDICTION (recorded before running): γ ∈ [0.9, 1.1] if metastable.

Usage:
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 claude_substrate_experiment.py

Author: Yaroslav Vasylenko (neuron7xLab)
Date: 2026-04-02
"""

from __future__ import annotations

import json
import time
import sys
import os
from pathlib import Path

import numpy as np
from scipy.stats import theilslopes

# ── Config ──
MODEL = "claude-sonnet-4-20250514"
N_PROMPTS = 200
N_REPEATS = 3
TEMPERATURE = 1.0
MAX_TOKENS = 300
SEED = 42
OUTPUT_RAW = Path("/home/neuro7/claude_substrate_raw.json")
OUTPUT_FIG = Path("/home/neuro7/fig_claude_gamma.png")

# ── Prompt generator: incrementally increasing complexity ──
def generate_prompts(n: int, seed: int = 42) -> list[str]:
    """Generate N prompts with progressive complexity.

    Complexity increases via:
    - More constraints per prompt
    - Deeper reasoning required
    - More abstract concepts
    """
    rng = np.random.default_rng(seed)

    topics = [
        "sorting algorithms", "graph theory", "probability",
        "thermodynamics", "evolution", "game theory", "topology",
        "information theory", "complex systems", "emergence",
        "cellular automata", "neural networks", "optimization",
        "dynamical systems", "category theory", "measure theory",
        "ergodic theory", "renormalization", "phase transitions",
        "self-organization",
    ]

    tasks = [
        "Define {topic} in exactly {n} words.",
        "Explain {topic} using only analogies from {domain}.",
        "List {n} non-obvious connections between {topic} and {topic2}.",
        "Write a {n}-step proof that {topic} relates to {topic2}.",
        "Describe {topic} from the perspective of {domain}, using exactly {n} sentences.",
        "Find {n} contradictions in the claim that {topic} is unrelated to {topic2}.",
        "Construct a {n}-level hierarchy showing how {topic} builds on {topic2}.",
        "In {n} words, explain why {topic} is essential for understanding {topic2}.",
    ]

    domains = [
        "cooking", "music", "architecture", "biology",
        "economics", "linguistics", "physics", "philosophy",
    ]

    prompts = []
    for i in range(n):
        # Complexity increases with i
        complexity = 2 + (i * 8) // n  # 2→10 constraints
        t_idx = i % len(tasks)
        topic = topics[i % len(topics)]
        topic2 = topics[(i + 7) % len(topics)]
        domain = domains[i % len(domains)]

        prompt = tasks[t_idx].format(
            topic=topic, topic2=topic2, domain=domain, n=complexity
        )
        prompts.append(prompt)

    return prompts


def call_api(client, prompt: str, attempt: int = 0) -> dict:
    """Single API call with retry."""
    max_retries = 3
    for retry in range(max_retries):
        try:
            t0 = time.monotonic()
            resp = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                messages=[{"role": "user", "content": prompt}],
            )
            latency = time.monotonic() - t0
            text = resp.content[0].text
            return {
                "text": text,
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
                "latency_ms": round(latency * 1000, 1),
                "stop_reason": resp.stop_reason,
            }
        except Exception as e:
            if retry < max_retries - 1:
                wait = 2 ** (retry + 1)
                print(f"    Retry {retry+1}/{max_retries} after {wait}s: {e}")
                time.sleep(wait)
            else:
                return {"text": "", "input_tokens": 0, "output_tokens": 0,
                        "latency_ms": 0, "stop_reason": "error", "error": str(e)}


def compute_gamma(variance_series: np.ndarray, seed: int = 42) -> dict:
    """Compute γ from PSD of variance time series.

    γ_PSD = 2H + 1 for fBm (NEVER 2H - 1).
    """
    n = len(variance_series)
    if n < 20:
        return {"gamma": float("nan"), "r2": 0, "ci": [float("nan")]*2,
                "p_perm": float("nan"), "n": n}

    # Detrend
    series = variance_series - np.mean(variance_series)

    # PSD via FFT
    freqs = np.fft.rfftfreq(n, d=1.0)
    psd = np.abs(np.fft.rfft(series)) ** 2 / n

    mask = freqs > 0
    log_f = np.log(freqs[mask])
    log_p = np.log(psd[mask] + 1e-20)

    # Theil-Sen fit
    slope, intc, lo, hi = theilslopes(log_p, log_f)
    beta = -slope  # spectral exponent
    H = (beta - 1) / 2.0
    gamma = 2 * H + 1  # = beta itself for fBm

    # R²
    yhat = slope * log_f + intc
    ss_res = np.sum((log_p - yhat) ** 2)
    ss_tot = np.sum((log_p - log_p.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 1e-10 else 0

    # Bootstrap CI
    rng = np.random.default_rng(seed)
    n_boot = 2000
    boot_gammas = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.choice(len(log_f), len(log_f), replace=True)
        s, _, _, _ = theilslopes(log_p[idx], log_f[idx])
        boot_gammas[i] = -s
    ci = [float(np.percentile(boot_gammas, 2.5)),
          float(np.percentile(boot_gammas, 97.5))]

    # Permutation test
    n_perm = 10000
    null_betas = np.empty(n_perm)
    for i in range(n_perm):
        perm_p = rng.permutation(log_p)
        s, _, _, _ = theilslopes(perm_p, log_f)
        null_betas[i] = -s
    p_perm = float(np.mean(np.abs(null_betas) >= abs(beta)))

    return {
        "gamma": round(float(gamma), 4),
        "beta": round(float(beta), 4),
        "H": round(float(H), 4),
        "r2": round(float(r2), 4),
        "ci": [round(c, 4) for c in ci],
        "p_perm": round(p_perm, 4),
        "n": n,
    }


def make_figure(variance_series, gamma_result, control_result, output_path):
    """Generate publication figure."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    n = len(variance_series)
    fig = plt.figure(figsize=(14, 5), facecolor="white")
    gs = GridSpec(1, 3, wspace=0.35)

    # Panel A: variance time series
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(range(n), variance_series, "-", color="#1f77b4", linewidth=0.8, alpha=0.7)
    ax1.set_xlabel("Prompt index (increasing complexity)", fontsize=10)
    ax1.set_ylabel("σ²(response) across 3 repeats", fontsize=10)
    ax1.set_title("A. Response Variance Time Series", fontsize=11, fontweight="bold")
    ax1.grid(True, alpha=0.3)

    # Panel B: PSD
    ax2 = fig.add_subplot(gs[0, 1])
    freqs = np.fft.rfftfreq(n, d=1.0)
    psd = np.abs(np.fft.rfft(variance_series - variance_series.mean())) ** 2 / n
    mask = freqs > 0
    ax2.loglog(freqs[mask], psd[mask], "o", color="#1f77b4", markersize=3, alpha=0.5)
    # Fit line
    log_f = np.log(freqs[mask])
    slope, intc, _, _ = theilslopes(np.log(psd[mask] + 1e-20), log_f)
    f_fit = np.logspace(np.log10(freqs[mask].min()), np.log10(freqs[mask].max()), 50)
    ax2.loglog(f_fit, np.exp(intc) * f_fit ** slope, "-", color="#d62728", linewidth=2,
               label=f"β = {-slope:.3f}")
    ax2.set_xlabel("Frequency", fontsize=10)
    ax2.set_ylabel("PSD", fontsize=10)
    ax2.set_title("B. Power Spectral Density", fontsize=11, fontweight="bold")
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3, which="both")

    # Panel C: result summary
    ax3 = fig.add_subplot(gs[0, 2])
    g = gamma_result
    c = control_result
    text = (
        f"SEQUENTIAL (ordered prompts)\n"
        f"  γ = {g['gamma']:.4f}\n"
        f"  CI₉₅ = [{g['ci'][0]:.3f}, {g['ci'][1]:.3f}]\n"
        f"  p_perm = {g['p_perm']:.4f}\n"
        f"  R² = {g['r2']:.4f}\n"
        f"  β = {g['beta']:.4f}, H = {g['H']:.4f}\n\n"
        f"CONTROL (shuffled prompts)\n"
        f"  γ = {c['gamma']:.4f}\n"
        f"  CI₉₅ = [{c['ci'][0]:.3f}, {c['ci'][1]:.3f}]\n"
        f"  p_perm = {c['p_perm']:.4f}\n\n"
    )

    # Regime classification
    dist = abs(g["gamma"] - 1.0)
    regime = ("METASTABLE" if dist < 0.15 else "WARNING" if dist < 0.30
              else "CRITICAL" if dist < 0.50 else "COLLAPSE")
    text += f"REGIME: {regime}\n"
    text += f"Separation: Δγ = {abs(g['gamma'] - c['gamma']):.4f}"

    ax3.text(0.05, 0.95, text, transform=ax3.transAxes, fontsize=10,
             verticalalignment="top", fontfamily="monospace",
             bbox=dict(boxstyle="round", facecolor="#f8f8f8", edgecolor="gray"))
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis("off")
    ax3.set_title("C. γ Derivation", fontsize=11, fontweight="bold")

    fig.suptitle(f"Claude Substrate: γ = {g['gamma']:.4f} [{g['ci'][0]:.3f}, {g['ci'][1]:.3f}]",
                 fontsize=13, fontweight="bold")

    plt.savefig(str(output_path), dpi=200, bbox_inches="tight", facecolor="white")
    print(f"Figure saved: {output_path}")


def main():
    import anthropic

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    client = anthropic.Anthropic()

    # ── Record prediction ──
    print("=" * 70)
    print("  PREDICTION (recorded before data collection)")
    print("  γ ∈ [0.9, 1.1] if Claude operates in metastable regime")
    print("=" * 70)

    # ── Generate prompts ──
    prompts = generate_prompts(N_PROMPTS, seed=SEED)
    print(f"\nGenerated {len(prompts)} prompts")
    print(f"  First: {prompts[0][:80]}...")
    print(f"  Last:  {prompts[-1][:80]}...")

    # ── Collect data: sequential ──
    print(f"\n{'='*70}")
    print(f"  PHASE 1: Sequential (ordered) — {N_PROMPTS} × {N_REPEATS} calls")
    print(f"{'='*70}\n")

    raw_data = []
    for i, prompt in enumerate(prompts):
        repeats = []
        for r in range(N_REPEATS):
            result = call_api(client, prompt)
            repeats.append(result)
            time.sleep(0.1)  # Rate limit courtesy

        raw_data.append({
            "prompt_idx": i,
            "prompt": prompt,
            "repeats": repeats,
        })

        if (i + 1) % 20 == 0:
            lengths = [rep["output_tokens"] for rep in repeats]
            var = float(np.var(lengths)) if len(lengths) > 1 else 0
            print(f"  [{i+1:3d}/{N_PROMPTS}] σ²(tokens)={var:.1f}  "
                  f"lengths={[rep['output_tokens'] for rep in repeats]}")

    # ── Compute variance series ──
    variance_series = []
    for entry in raw_data:
        lengths = [r["output_tokens"] for r in entry["repeats"] if r["output_tokens"] > 0]
        if len(lengths) >= 2:
            variance_series.append(float(np.var(lengths)))
        else:
            variance_series.append(0.0)

    variance_series = np.array(variance_series)

    # ── Collect control: shuffled ──
    print(f"\n{'='*70}")
    print(f"  PHASE 2: Control (shuffled) — {N_PROMPTS} × {N_REPEATS} calls")
    print(f"{'='*70}\n")

    rng = np.random.default_rng(SEED + 1000)
    shuffled_indices = rng.permutation(N_PROMPTS)

    control_data = []
    for count, idx in enumerate(shuffled_indices):
        prompt = prompts[idx]
        repeats = []
        for r in range(N_REPEATS):
            result = call_api(client, prompt)
            repeats.append(result)
            time.sleep(0.1)

        control_data.append({
            "original_idx": int(idx),
            "repeats": repeats,
        })

        if (count + 1) % 20 == 0:
            print(f"  [{count+1:3d}/{N_PROMPTS}]")

    control_variance = []
    for entry in control_data:
        lengths = [r["output_tokens"] for r in entry["repeats"] if r["output_tokens"] > 0]
        if len(lengths) >= 2:
            control_variance.append(float(np.var(lengths)))
        else:
            control_variance.append(0.0)

    control_variance = np.array(control_variance)

    # ── Compute γ ──
    print(f"\n{'='*70}")
    print(f"  COMPUTING γ")
    print(f"{'='*70}\n")

    gamma_result = compute_gamma(variance_series, seed=SEED)
    control_result = compute_gamma(control_variance, seed=SEED + 500)

    # ── Save raw data ──
    output = {
        "prediction": "γ ∈ [0.9, 1.1] if metastable",
        "model": MODEL,
        "n_prompts": N_PROMPTS,
        "n_repeats": N_REPEATS,
        "temperature": TEMPERATURE,
        "sequential": {
            "gamma": gamma_result,
            "variance_series": variance_series.tolist(),
        },
        "control": {
            "gamma": control_result,
            "variance_series": control_variance.tolist(),
        },
        "raw_sequential": raw_data,
        "raw_control": control_data,
    }

    OUTPUT_RAW.write_text(json.dumps(output, indent=2, default=str, ensure_ascii=False))
    print(f"Raw data saved: {OUTPUT_RAW}")

    # ── Figure ──
    make_figure(variance_series, gamma_result, control_result, OUTPUT_FIG)

    # ── Final result ──
    dist = abs(gamma_result["gamma"] - 1.0)
    regime = ("METASTABLE" if dist < 0.15 else "WARNING" if dist < 0.30
              else "CRITICAL" if dist < 0.50 else "COLLAPSE")

    separation = abs(gamma_result["gamma"] - control_result["gamma"])

    print(f"\n{'='*70}")
    print(f"  RESULT")
    print(f"{'='*70}")
    print(f"\n  Claude substrate γ = {gamma_result['gamma']:.4f} "
          f"[CI: {gamma_result['ci'][0]:.3f}, {gamma_result['ci'][1]:.3f}], "
          f"p={gamma_result['p_perm']:.4f}")
    print(f"  Control γ = {control_result['gamma']:.4f}")
    print(f"  Separation: Δγ = {separation:.4f}")
    print(f"  Regime: {regime}")
    print(f"\n  Prediction was: γ ∈ [0.9, 1.1]")
    hit = 0.9 <= gamma_result["gamma"] <= 1.1
    print(f"  Prediction {'CONFIRMED' if hit else 'FALSIFIED'}: γ = {gamma_result['gamma']:.4f}")


if __name__ == "__main__":
    main()
