"""Cognitive extensions — high-level convenience API.

Seven functions that make MFN a joy to use:
  mfn.explain(seq)        → human-language interpretation
  mfn.compare_many(seqs)  → batch comparison table
  mfn.sweep(param, vals)  → parameter sweep with results
  mfn.plot_field(seq)     → ASCII heatmap in terminal
  mfn.benchmark_quick(seq)→ quick performance check
  mfn.to_markdown(seq)    → full report as markdown
  mfn.history(seq)        → temporal M(t), dH/dt profile
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from .types.field import FieldSequence, SimulationSpec

__all__ = [
    "benchmark_quick",
    "compare_many",
    "explain",
    "gamma_diagnostic",
    "history",
    "invariance_report",
    "plot_field",
    "sweep",
    "to_markdown",
]


# ═══════════════════════════════════════════════════════════════
# 1. EXPLAIN — human language
# ═══════════════════════════════════════════════════════════════


def explain(seq: FieldSequence) -> str:
    """One-paragraph human-language explanation of system state.

    >>> print(mfn.explain(seq))
    Your system is forming a spots pattern with 3 connected components...
    """
    from .analytics.tda_ews import compute_tda
    from .core.detect import detect_anomaly
    from .core.early_warning import early_warning

    det = detect_anomaly(seq)
    ews = early_warning(seq)
    tda = compute_tda(seq.field)

    lines = []

    # Pattern type
    lines.append(
        f"Your system shows a {tda.pattern_type} pattern "
        f"(β₀={tda.beta_0} components, β₁={tda.beta_1} loops)."
    )

    # Health
    if det.label == "nominal":
        lines.append("The system is healthy — operating in nominal regime.")
    elif det.label == "watch":
        lines.append(f"The system needs attention — anomaly score {det.score:.2f} is elevated.")
    else:
        lines.append(f"WARNING: anomaly detected (score={det.score:.2f}, label={det.label}).")

    # EWS
    if ews.ews_score > 0.5:
        lines.append(
            f"Early warning signals indicate {ews.transition_type} "
            f"(EWS={ews.ews_score:.2f}). Consider intervention."
        )
    elif ews.ews_score > 0.3:
        lines.append(f"Mild early warning: {ews.transition_type} (EWS={ews.ews_score:.2f}).")
    else:
        lines.append("No significant early warning signals detected.")

    # Recommendation
    if det.label in ("anomalous", "critical"):
        lines.append("Recommendation: run mfn.auto_heal(seq) to find optimal intervention.")
    elif ews.ews_score > 0.5:
        lines.append("Recommendation: monitor with mfn.watch() or reduce diffusion coefficient.")

    return " ".join(lines)


# ═══════════════════════════════════════════════════════════════
# 2. COMPARE_MANY — batch comparison
# ═══════════════════════════════════════════════════════════════


def compare_many(sequences: list[FieldSequence]) -> str:
    """Compare N systems side-by-side.

    >>> print(mfn.compare_many([seq1, seq2, seq3]))
    """
    from .analytics.unified_score import compute_hwi_components
    from .core.detect import detect_anomaly
    from .core.early_warning import early_warning

    rows = []
    for i, seq in enumerate(sequences):
        det = detect_anomaly(seq)
        ews = early_warning(seq)
        hwi = compute_hwi_components(seq.history[0], seq.field) if seq.history is not None else None

        rows.append(
            {
                "id": i + 1,
                "label": det.label,
                "score": det.score,
                "ews": ews.ews_score,
                "M": hwi.M if hwi else 0,
                "regime": det.regime.label if det.regime else "?",
            }
        )

    # Format table
    lines = [f"  {'#':>3} {'Label':>10} {'Score':>7} {'EWS':>6} {'M':>7} {'Regime':>12}"]
    lines.append(
        f"  {'---':>3} {'----------':>10} {'-------':>7} {'------':>6} {'-------':>7} {'------------':>12}"
    )
    for r in rows:
        lines.append(
            f"  {r['id']:>3} {r['label']:>10} {r['score']:>7.3f} "
            f"{r['ews']:>6.3f} {r['M']:>7.3f} {r['regime']:>12}"
        )

    # Summary
    best = min(rows, key=lambda r: r["score"])
    worst = max(rows, key=lambda r: r["score"])
    lines.append(f"\n  Healthiest: #{best['id']} ({best['label']}, score={best['score']:.3f})")
    lines.append(f"  Most stressed: #{worst['id']} ({worst['label']}, score={worst['score']:.3f})")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 3. SWEEP — parameter exploration
# ═══════════════════════════════════════════════════════════════


def sweep(
    param: str,
    values: list[float],
    base_spec: dict[str, Any] | None = None,
    seed: int = 42,
) -> str:
    """Sweep one parameter and show results.

    >>> print(mfn.sweep("alpha", [0.05, 0.10, 0.15, 0.20]))
    """
    from .analytics.unified_score import compute_hwi_components
    from .core.detect import detect_anomaly
    from .core.simulate import simulate_history

    base = base_spec or {"grid_size": 32, "steps": 60}
    base["seed"] = seed

    lines = [f"  {'Value':>8} {'Label':>10} {'Score':>7} {'M':>7} {'EWS':>6}"]
    lines.append(
        f"  {'--------':>8} {'----------':>10} {'-------':>7} {'-------':>7} {'------':>6}"
    )

    for val in values:
        spec_dict = {**base, param: val}
        try:
            spec = SimulationSpec(**spec_dict)
            seq = simulate_history(spec)
            det = detect_anomaly(seq)
            from .core.early_warning import early_warning

            ews = early_warning(seq)
            hwi = (
                compute_hwi_components(seq.history[0], seq.field)
                if seq.history is not None
                else None
            )
            M = hwi.M if hwi else 0
            lines.append(
                f"  {val:>8.4f} {det.label:>10} {det.score:>7.3f} {M:>7.3f} {ews.ews_score:>6.3f}"
            )
        except Exception as e:
            lines.append(f"  {val:>8.4f} {'ERROR':>10} — {str(e)[:30]}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 4. PLOT_FIELD — ASCII heatmap
# ═══════════════════════════════════════════════════════════════


def plot_field(seq: FieldSequence, width: int = 48, height: int = 24) -> str:
    """ASCII heatmap of the field. No dependencies needed.

    >>> print(mfn.plot_field(seq))
    """
    field = seq.field
    N, M = field.shape

    # Resample to terminal size
    row_idx = np.linspace(0, N - 1, height).astype(int)
    col_idx = np.linspace(0, M - 1, width).astype(int)
    sampled = field[np.ix_(row_idx, col_idx)]

    # Normalize to [0, 1]
    vmin, vmax = float(sampled.min()), float(sampled.max())
    if vmax - vmin < 1e-12:
        norm = np.zeros_like(sampled)
    else:
        norm = (sampled - vmin) / (vmax - vmin)

    # ASCII gradient (dark to bright)
    chars = " ░▒▓█"
    lines = []
    lines.append(f"  Field [{vmin:.4f}, {vmax:.4f}]  {N}×{M}")
    lines.append(f"  {'─' * width}")
    for row in norm:
        line = "".join(chars[min(int(v * (len(chars) - 1)), len(chars) - 1)] for v in row)
        lines.append(f"  {line}")
    lines.append(f"  {'─' * width}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 5. BENCHMARK_QUICK — performance snapshot
# ═══════════════════════════════════════════════════════════════


def benchmark_quick(seq: FieldSequence) -> str:
    """Quick performance check on a FieldSequence.

    >>> print(mfn.benchmark_quick(seq))
    """
    from .analytics.unified_score import compute_hwi_components
    from .core.detect import detect_anomaly
    from .core.early_warning import early_warning

    results = {}

    t0 = time.perf_counter()
    detect_anomaly(seq)
    results["detect"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    early_warning(seq)
    results["ews"] = (time.perf_counter() - t0) * 1000

    if seq.history is not None:
        t0 = time.perf_counter()
        compute_hwi_components(seq.history[0], seq.field)
        results["M"] = (time.perf_counter() - t0) * 1000

    from . import diagnose, extract

    t0 = time.perf_counter()
    extract(seq)
    results["extract"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    diagnose(seq)
    results["diagnose"] = (time.perf_counter() - t0) * 1000

    lines = [f"  {'Stage':>12} {'Time':>8}"]
    lines.append(f"  {'------------':>12} {'--------':>8}")
    total = 0
    for name, ms in results.items():
        lines.append(f"  {name:>12} {ms:>7.1f}ms")
        total += ms
    lines.append(f"  {'TOTAL':>12} {total:>7.1f}ms")
    lines.append(
        f"  Field: {seq.field.shape[0]}×{seq.field.shape[1]}, "
        f"History: {seq.history.shape[0] if seq.history is not None else 0} frames"
    )

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 6. TO_MARKDOWN — exportable report
# ═══════════════════════════════════════════════════════════════


def to_markdown(seq: FieldSequence) -> str:
    """Full diagnosis as markdown — paste into docs, PR, README.

    >>> print(mfn.to_markdown(seq))
    """
    from . import detect, diagnose, early_warning, extract

    diag = diagnose(seq)
    det = detect(seq)
    ews = early_warning(seq)
    desc = extract(seq)

    lines = [
        "## MFN Diagnosis Report",
        "",
        f"**Severity:** {diag.severity}",
        f"**Anomaly:** {det.label} (score={det.score:.3f})",
        f"**EWS:** {ews.transition_type} (score={ews.ews_score:.3f})",
        "",
        "### Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Anomaly score | {det.score:.4f} |",
        f"| EWS score | {ews.ews_score:.4f} |",
        f"| Regime | {det.regime.label if det.regime else 'N/A'} |",
        f"| Features | {len(desc.embedding)} |",
        f"| D_box | {desc.features.get('D_box', 0):.3f} |",
        "",
        "### Narrative",
        "",
        diag.narrative or "_No narrative available._",
        "",
        f"_Generated by MFN v{__import__('mycelium_fractal_net').__version__}_",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 8. GAMMA DIAGNOSTIC — scaling exponent from ensemble
# ═══════════════════════════════════════════════════════════════


def gamma_diagnostic(sequences: list[FieldSequence]) -> str:
    """Measure scaling exponent γ from an ensemble of FieldSequences.

    γ > 0: complexity gets cheaper with scale (healthy growth)
    γ < 0: complexity gets more expensive (pathological)

    Requires ≥4 sequences with different topological complexity.

    >>> seqs = [mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=i)) for i in range(10)]
    >>> print(mfn.gamma_diagnostic(seqs))
    """
    from scipy.ndimage import label
    from scipy.stats import linregress

    points = []
    ref = sequences[0].field

    for seq in sequences:
        field = seq.field
        # Entropy
        p = np.abs(field).ravel() + 1e-12
        p /= p.sum()
        q = np.abs(ref).ravel() + 1e-12
        q /= q.sum()
        dH = max(0, float(np.sum(p * np.log(p / (q + 1e-12)))))

        # Topology
        _, b0 = label(field > np.median(field))
        b = (field > np.median(field)).astype(int)
        V = b.sum()
        Eh = (b[:, :-1] * b[:, 1:]).sum()
        Ev = (b[:-1, :] * b[1:, :]).sum()
        F = (b[:-1, :-1] * b[:-1, 1:] * b[1:, :-1] * b[1:, 1:]).sum()
        b1 = max(0, b0 - (V - Eh - Ev + F))
        topo = b0 + b1

        if topo > 1 and dH > 0:
            points.append((topo, dH / topo))

    if len(points) < 4:
        return "  Insufficient data (need ≥4 sequences with different topology)."

    t = np.array([p[0] for p in points], dtype=float)
    c = np.array([p[1] for p in points], dtype=float)
    mask = c > 0
    if mask.sum() < 4:
        return "  Insufficient non-zero cost points."

    sl, _, r, p_val, se = linregress(np.log(t[mask]), np.log(c[mask]))
    gamma = -sl

    if gamma > 1.5:
        diag = "ACCELERATING — complexity cheapens fast"
    elif gamma > 0.7:
        diag = "HEALTHY GROWTH — sustainable scaling"
    elif gamma > 0.3:
        diag = "DEGRADING — approaching limits"
    elif gamma > 0:
        diag = "CRITICAL — near scaling collapse"
    else:
        diag = "PATHOLOGICAL — complexity unsustainable"

    lines = [
        f"  γ = {gamma:+.3f} ± {se:.3f}  (R²={r**2:.3f}, p={p_val:.4f})",
        f"  Topology range: [{int(t.min())}..{int(t.max())}]",
        f"  Diagnosis: {diag}",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 7. HISTORY — temporal profile
# ═══════════════════════════════════════════════════════════════


def history(seq: FieldSequence, stride: int = 5) -> str:
    """Show M(t), H(t), dH/dt across trajectory.

    >>> print(mfn.history(seq))
    """
    from .analytics.unified_score import hwi_trajectory

    if seq.history is None or seq.history.shape[0] < 3:
        return "  No history available (need ≥3 frames)."

    traj = hwi_trajectory(seq.history, stride=stride)
    M = traj["M"]
    H = traj["H"]
    dH = traj["dH_dt"]
    ts = traj["timesteps"]

    lines = [f"  {'Step':>6} {'M':>8} {'H':>8} {'dH/dt':>10}"]
    lines.append(f"  {'------':>6} {'--------':>8} {'--------':>8} {'----------':>10}")

    for i in range(len(M)):
        dh_str = f"{dH[i]:>+10.6f}" if i < len(dH) else f"{'—':>10}"
        lines.append(f"  {ts[i]:>6d} {M[i]:>8.4f} {H[i]:>8.4f} {dh_str}")

    # Summary
    lines.append(f"\n  M: {M[0]:.4f} → {M[-1]:.4f} (Δ={M[-1] - M[0]:+.4f})")
    lines.append(f"  dH/dt < 0: {traj['dH_dt_negative_frac']:.0%}")
    lines.append(f"  Descent: {'YES' if M[-1] < M[0] else 'NO'}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 9. INVARIANCE REPORT — compute Λ₂, Λ₅, Λ₆
# ═══════════════════════════════════════════════════════════════


def invariance_report(seq: FieldSequence) -> str:
    """Compute MFN integral invariants Λ₂, Λ₅, Λ₆ for a FieldSequence.

    Λ₂ = H/(W₂^0.59·I^0.86) ≈ 1.92  (per-step power law, CV~1%)
    Λ₅ = ΣH/(ΣW₂·√ΣI) ≈ 0.082      (integral ratio, CV~0.3%)
    Λ₆ = λ_H/(λ_W+λ_I/2) ≈ 1.323    (decay rate ratio, CV~0.9%)

    >>> print(mfn.invariance_report(seq))
    """
    from .analytics.invariant_operator import InvariantOperator

    if seq.history is None or seq.history.shape[0] < 5:
        return "  Need ≥5 history frames for invariance analysis."

    op = InvariantOperator()

    L2 = op.Lambda2(seq.history)
    L2_mean = float(np.mean(L2))
    L2_cv = float(np.std(L2) / (L2_mean + 1e-12))
    L5 = op.Lambda5(seq.history)
    L6 = op.Lambda6(seq.history)

    lines = [
        f"  Λ₂ = {L2_mean:.4f} ± {np.std(L2):.4f}  CV={L2_cv:.4f}  (ref: 1.92)",
        f"  Λ₅ = {L5:.6f}              (ref: 0.082 at N=32)",
        f"  Λ₆ = {L6:.4f}              (ref: 1.323)",
        "",
    ]

    l2_ok = L2_cv < 0.05
    l6_ok = abs(L6 - 1.323) / 1.323 < 0.10
    lines.append(f"  Λ₂ invariant (CV<5%): {'YES' if l2_ok else 'NO'}")
    lines.append(f"  Λ₆ within 10% of ref: {'YES' if l6_ok else 'NO'}")

    if l2_ok and l6_ok:
        lines.append("  System conforms to MFN integral invariance theorem.")
    else:
        lines.append("  System outside admissible class.")

    return "\n".join(lines)
