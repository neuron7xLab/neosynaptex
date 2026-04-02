"""
CFP/ДІЙ Metrics — Cognitive Field Protocol v2.0
================================================
Core measurement instruments for human+AI co-adaptation.

CRR  = Cognitive Recovery Ratio = S(T3) / S(T0)
S    = w₁·LD + w₂·TC + w₃·DT
CPR  = Compression Primitive Ratio
DI   = Dependency Index
TTR  = Time to Resolution

Author: Yaroslav Vasylenko (neuron7xLab)
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DEFAULT_WEIGHTS = (0.30, 0.35, 0.35)  # w_LD, w_TC, w_DT

# Linguistic primitives — single-token imperatives with full intent vector
# Ukrainian + English core set
_PRIMITIVES_UK = {"дій", "стоп", "ні", "так", "далі", "все", "ок", "зроби", "іди", "дай"}
_PRIMITIVES_EN = {"do", "stop", "no", "yes", "go", "next", "done", "ok", "run", "fix"}
_PRIMITIVES = _PRIMITIVES_UK | _PRIMITIVES_EN


# ---------------------------------------------------------------------------
# MTLD — Measure of Textual Lexical Diversity
# ---------------------------------------------------------------------------
def mtld(tokens: Sequence[str], threshold: float = 0.72) -> float:
    """Compute MTLD (McCarthy & Jarvis, 2010).

    Forward + backward pass, averaged. Returns lexical diversity score.
    Higher = more diverse vocabulary usage.
    """
    if len(tokens) < 10:
        return 0.0

    def _one_pass(toks: Sequence[str]) -> float:
        factors = 0.0
        types: set[str] = set()
        token_count = 0
        for t in toks:
            types.add(t.lower())
            token_count += 1
            ttr = len(types) / token_count
            if ttr <= threshold:
                factors += 1.0
                types = set()
                token_count = 0
        # Partial factor
        if token_count > 0:
            ttr = len(types) / token_count
            if ttr < 1.0:
                factors += (1.0 - ttr) / (1.0 - threshold)
        return len(toks) / factors if factors > 0 else float(len(toks))

    fwd = _one_pass(tokens)
    bwd = _one_pass(list(reversed(tokens)))
    return (fwd + bwd) / 2.0


# ---------------------------------------------------------------------------
# CPR — Compression Primitive Ratio
# ---------------------------------------------------------------------------
def cpr(tokens: Sequence[str]) -> float:
    """Compression Primitive Ratio.

    Fraction of tokens that are single-token imperatives with maximal intent.
    CPR preserved T0→T3 = compression skill internalized.
    CPR drops T3 = masked degradation.
    """
    if not tokens:
        return 0.0
    count = sum(1 for t in tokens if t.lower().strip() in _PRIMITIVES)
    return count / len(tokens)


# ---------------------------------------------------------------------------
# Tokenizer (lightweight, no external deps)
# ---------------------------------------------------------------------------
_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯіІїЇєЄґҐ'']+")


def tokenize(text: str) -> list[str]:
    """Simple word tokenizer for Ukrainian + English."""
    return _WORD_RE.findall(text)


# ---------------------------------------------------------------------------
# Cognitive Complexity Score S
# ---------------------------------------------------------------------------
@dataclass
class CognitiveScore:
    """Integrated cognitive complexity score."""

    ld: float       # Lexical Diversity (MTLD)
    tc: float       # Task Complexity (0-10 scale)
    dt: float       # Divergent Thinking (hypotheses count)
    s: float        # Weighted integral
    weights: tuple[float, float, float] = _DEFAULT_WEIGHTS

    @property
    def components(self) -> dict[str, float]:
        return {"LD": self.ld, "TC": self.tc, "DT": self.dt, "S": self.s}


def cognitive_score(
    ld: float,
    tc: float,
    dt: float,
    weights: tuple[float, float, float] = _DEFAULT_WEIGHTS,
) -> CognitiveScore:
    """Compute S = w₁·LD_norm + w₂·TC_norm + w₃·DT_norm.

    All components are min-max normalized to [0, 1] before integration.
    LD: MTLD typically 20-200 → norm by /200
    TC: 0-10 scale → norm by /10
    DT: hypotheses count typically 0-20 → norm by /20
    """
    w1, w2, w3 = weights
    ld_n = min(ld / 200.0, 1.0)
    tc_n = min(tc / 10.0, 1.0)
    dt_n = min(dt / 20.0, 1.0)
    s = w1 * ld_n + w2 * tc_n + w3 * dt_n
    return CognitiveScore(ld=ld, tc=tc, dt=dt, s=s, weights=weights)


# ---------------------------------------------------------------------------
# CRR — Cognitive Recovery Ratio
# ---------------------------------------------------------------------------
@dataclass
class CRRResult:
    """Cognitive Recovery Ratio measurement."""

    crr: float                # S(T3) / S(T0)
    s_t0: CognitiveScore
    s_t3: CognitiveScore
    state: str                # gain / neutral / compression / degradation
    cpr_t0: float = 0.0
    cpr_t2: float = 0.0
    cpr_t3: float = 0.0
    cpr_discriminator: str = ""  # "internalized" / "co-adaptive" / "simplification"

    def is_masked_degradation(self) -> bool:
        """CRR in compression zone but CPR drops → masked degradation."""
        return (0.85 <= self.crr < 0.95) and (self.cpr_t3 < self.cpr_t2 * 0.8)


def classify_crr(crr: float) -> str:
    """Classify CRR into cognitive state."""
    if crr > 1.05:
        return "gain"
    elif crr >= 0.95:
        return "neutral"
    elif crr >= 0.85:
        return "compression"
    else:
        return "degradation"


def classify_cpr(cpr_t0: float, cpr_t2: float, cpr_t3: float) -> str:
    """Classify CPR trajectory.

    - grows T0→T2, preserved T3 → internalized compression
    - grows T0→T2, drops T3 → co-adaptive only (not internalized)
    - drops T0→T2 → simplification (degradation signal)
    """
    grew = cpr_t2 > cpr_t0 * 1.1
    preserved = cpr_t3 >= cpr_t2 * 0.8
    dropped_early = cpr_t2 < cpr_t0 * 0.9

    if dropped_early:
        return "simplification"
    if grew and preserved:
        return "internalized"
    if grew and not preserved:
        return "co-adaptive"
    return "stable"


def compute_crr(
    s_t0: CognitiveScore,
    s_t3: CognitiveScore,
    cpr_t0: float = 0.0,
    cpr_t2: float = 0.0,
    cpr_t3: float = 0.0,
) -> CRRResult:
    """Compute CRR = S(T3) / S(T0) with full diagnostics."""
    crr = s_t3.s / s_t0.s if s_t0.s > 1e-10 else 0.0
    state = classify_crr(crr)
    cpr_disc = classify_cpr(cpr_t0, cpr_t2, cpr_t3)
    return CRRResult(
        crr=crr,
        s_t0=s_t0,
        s_t3=s_t3,
        state=state,
        cpr_t0=cpr_t0,
        cpr_t2=cpr_t2,
        cpr_t3=cpr_t3,
        cpr_discriminator=cpr_disc,
    )


# ---------------------------------------------------------------------------
# DI — Dependency Index
# ---------------------------------------------------------------------------
def dependency_index(ai_assisted: int, total_decisions: int) -> float:
    """DI = ai_assisted / total_decisions. Behavioural marker, not in S."""
    if total_decisions <= 0:
        return 0.0
    return ai_assisted / total_decisions


# ---------------------------------------------------------------------------
# γ-CRR — scaling exponent from CRR time series
# ---------------------------------------------------------------------------
def gamma_crr(
    crr_series: np.ndarray,
    method: str = "psd",
    seed: int = 42,
) -> dict:
    """Compute γ-CRR from a time series of CRR measurements.

    Methods:
      - 'psd': Power Spectral Density slope → γ = β (spectral exponent)
        For fBm: β = 2H + 1 (NEVER 2H - 1)
      - 'theilsen': Theil-Sen on log-log of ordered pairs

    Returns dict with gamma, ci, p_perm, method.
    """
    from scipy.stats import theilslopes

    n = len(crr_series)
    if n < 10:
        return {"gamma": float("nan"), "ci": [float("nan")] * 2,
                "p_perm": float("nan"), "method": method, "n": n}

    rng = np.random.default_rng(seed)

    if method == "psd":
        # Welch PSD → spectral slope
        freqs = np.fft.rfftfreq(n, d=1.0)
        psd = np.abs(np.fft.rfft(crr_series - crr_series.mean())) ** 2 / n
        mask = freqs > 0
        log_f = np.log(freqs[mask])
        log_p = np.log(psd[mask] + 1e-20)
        slope, intc, lo, hi = theilslopes(log_p, log_f)
        beta = -slope  # spectral exponent
        # For fBm: β = 2H + 1 → H = (β - 1) / 2
        H = (beta - 1) / 2.0
        gamma = 2 * H + 1  # γ_PSD = β itself for fBm

        # Permutation test
        n_perm = 10000
        null_betas = np.empty(n_perm)
        for i in range(n_perm):
            shuffled = rng.permutation(crr_series)
            psd_s = np.abs(np.fft.rfft(shuffled - shuffled.mean())) ** 2 / n
            s_slope, _, _, _ = theilslopes(np.log(psd_s[mask] + 1e-20), log_f)
            null_betas[i] = -s_slope
        p_perm = float(np.mean(null_betas >= beta))

        # Bootstrap CI
        n_boot = 2000
        boot_gammas = np.empty(n_boot)
        for i in range(n_boot):
            idx = rng.choice(n, n, replace=True)
            boot = crr_series[idx]
            psd_b = np.abs(np.fft.rfft(boot - boot.mean())) ** 2 / n
            b_slope, _, _, _ = theilslopes(np.log(psd_b[mask] + 1e-20), log_f)
            boot_gammas[i] = -b_slope
        ci = [float(np.percentile(boot_gammas, 2.5)),
              float(np.percentile(boot_gammas, 97.5))]

        return {"gamma": round(float(gamma), 4), "ci": [round(c, 4) for c in ci],
                "p_perm": round(p_perm, 4), "method": "psd", "n": n,
                "H": round(float(H), 4), "beta": round(float(beta), 4)}

    elif method == "theilsen":
        # Ordered index as topo proxy
        x = np.arange(1, n + 1, dtype=float)
        y = crr_series.copy()
        mask = y > 0
        if mask.sum() < 5:
            return {"gamma": float("nan"), "ci": [float("nan")] * 2,
                    "p_perm": float("nan"), "method": "theilsen", "n": n}
        log_x = np.log(x[mask])
        log_y = np.log(y[mask])
        slope, intc, lo, hi = theilslopes(log_y, log_x)
        gamma = -slope

        # Permutation
        n_perm = 10000
        null_slopes = np.empty(n_perm)
        for i in range(n_perm):
            perm_y = rng.permutation(log_y)
            s, _, _, _ = theilslopes(perm_y, log_x)
            null_slopes[i] = -s
        p_perm = float(np.mean(np.abs(null_slopes) >= abs(gamma)))

        return {"gamma": round(float(gamma), 4),
                "ci": [round(float(-hi), 4), round(float(-lo), 4)],
                "p_perm": round(p_perm, 4), "method": "theilsen", "n": n}

    raise ValueError(f"Unknown method: {method}")
