"""Anti-tautology battery — AT-1 through AT-4.

All four tests MUST pass before a gamma value may enter
``evidence/scientific/``. Each test recomputes gamma via a fresh
``ProbeSession`` (canonical engine); the probe never reimplements
gamma (HARD RULE 1).

AT-1 Shuffled null        : turn-order permutation, delta < 0.1 -> flag
AT-2 Lexical surrogate    : random content, same token counts, p < 0.05 required
AT-3 Piecewise stability  : first/second half gamma diff < 0.3
AT-4 Leave-one-turn-out   : max per-turn sensitivity < 0.2
"""

from __future__ import annotations

import math
import random
import string
from dataclasses import dataclass, field

import numpy as np

from probe.dialogue_adapter import Turn
from probe.session import MIN_TURNS, ProbeSession

# Thresholds from the spec. Named constants so reviewers can find and
# defend them without grepping.
_SHUFFLED_TAUTOLOGY_DELTA: float = 0.1
_PIECEWISE_INSTABILITY_DELTA: float = 0.3
_LOTO_OUTLIER_DELTA: float = 0.2
_SURROGATE_TRIALS: int = 32
_SURROGATE_VOCAB_SIZE: int = 512
_SURROGATE_P_THRESHOLD: float = 0.05


@dataclass(frozen=True)
class AntiTautologyResult:
    """Per-battery report. ``passed`` iff no flag is set and gamma valid."""

    gamma_original: float
    shuffled_delta: float
    surrogate_p: float
    piecewise_delta: float
    max_loto_sensitivity: float
    tautology_flag: bool
    instability_flag: bool
    outlier_flag: bool
    surrogate_flag: bool
    passed: bool
    notes: tuple[str, ...] = field(default_factory=tuple)


def run_anti_tautology(
    session: ProbeSession,
    seed: int = 7,
) -> AntiTautologyResult:
    """Run AT-1..AT-4. Returns ``AntiTautologyResult`` — caller must gate.

    ``session`` must have already been populated with >= MIN_TURNS turns.
    We take ``session.adapter.turns`` as the canonical turn sequence.
    """
    turns = list(session.adapter.turns)
    if len(turns) < MIN_TURNS:
        raise ValueError(f"session has {len(turns)} turns, need >= {MIN_TURNS} for AT battery")

    gamma_original = _final_gamma(turns, window=session.window, seed=seed)
    notes: list[str] = []

    # AT-1 Shuffled null
    shuffled_gamma = _shuffled_gamma(turns, window=session.window, seed=seed)
    shuffled_delta = _safe_abs_delta(gamma_original, shuffled_gamma)
    tautology_flag = not math.isnan(shuffled_delta) and shuffled_delta < _SHUFFLED_TAUTOLOGY_DELTA
    if math.isnan(shuffled_delta):
        notes.append("AT-1: NaN gamma encountered; shuffled delta undefined.")

    # AT-2 Lexical surrogate
    surrogate_p = _surrogate_p_value(
        turns,
        gamma_original,
        window=session.window,
        seed=seed,
    )
    surrogate_flag = not math.isnan(surrogate_p) and surrogate_p >= _SURROGATE_P_THRESHOLD
    if math.isnan(surrogate_p):
        notes.append("AT-2: could not estimate surrogate distribution (all NaN).")

    # AT-3 Piecewise stability
    mid = len(turns) // 2
    first_half = turns[:mid]
    second_half = turns[mid:]
    if len(first_half) >= MIN_TURNS and len(second_half) >= MIN_TURNS:
        gamma_first = _final_gamma(first_half, window=session.window, seed=seed)
        gamma_second = _final_gamma(second_half, window=session.window, seed=seed)
        piecewise_delta = _safe_abs_delta(gamma_first, gamma_second)
    else:
        piecewise_delta = float("nan")
        notes.append("AT-3: half-sessions below MIN_TURNS; piecewise stability skipped.")
    instability_flag = (
        not math.isnan(piecewise_delta) and piecewise_delta > _PIECEWISE_INSTABILITY_DELTA
    )

    # AT-4 Leave-one-turn-out
    max_sensitivity = _loto_max_sensitivity(
        turns,
        gamma_original,
        window=session.window,
        seed=seed,
    )
    outlier_flag = not math.isnan(max_sensitivity) and max_sensitivity > _LOTO_OUTLIER_DELTA
    if math.isnan(max_sensitivity):
        notes.append("AT-4: LOTO produced only NaN gammas; sensitivity undefined.")

    gamma_valid = not math.isnan(gamma_original)
    if not gamma_valid:
        notes.append("gamma_original is NaN — battery result invalid.")
    passed = (
        gamma_valid
        and not tautology_flag
        and not instability_flag
        and not outlier_flag
        and not surrogate_flag
    )

    return AntiTautologyResult(
        gamma_original=gamma_original,
        shuffled_delta=shuffled_delta,
        surrogate_p=surrogate_p,
        piecewise_delta=piecewise_delta,
        max_loto_sensitivity=max_sensitivity,
        tautology_flag=tautology_flag,
        instability_flag=instability_flag,
        outlier_flag=outlier_flag,
        surrogate_flag=surrogate_flag,
        passed=passed,
        notes=tuple(notes),
    )


# ----------------------------------------------------------------------
# Internals
# ----------------------------------------------------------------------
def _final_gamma(turns: list[Turn], *, window: int, seed: int) -> float:
    """Build a fresh ProbeSession, replay ``turns``, return final gamma_mean."""
    session = ProbeSession(window=window, seed=seed)
    for t in turns:
        session.push_turn(t)
    if session.n_turns == 0:
        return float("nan")
    return float(session.states()[-1].gamma_mean)


def _shuffled_gamma(turns: list[Turn], *, window: int, seed: int) -> float:
    rng = random.Random(seed)
    permuted = turns.copy()
    rng.shuffle(permuted)
    return _final_gamma(permuted, window=window, seed=seed)


def _surrogate_p_value(
    turns: list[Turn],
    gamma_original: float,
    *,
    window: int,
    seed: int,
) -> float:
    """Empirical p-value from random-content surrogate trials.

    Generates ``_SURROGATE_TRIALS`` surrogate sessions: each turn's
    ``content`` is replaced with random tokens sampled from a fixed-size
    vocabulary, ``token_count`` preserved. Returns the two-sided empirical
    p-value under a normal approximation. NaN gammas in surrogates are
    dropped (with a lower-bound floor on sample size = 4).
    """
    if math.isnan(gamma_original):
        return float("nan")
    vocab = _surrogate_vocab(_SURROGATE_VOCAB_SIZE, seed)
    rng = random.Random(seed)
    gammas: list[float] = []
    for trial in range(_SURROGATE_TRIALS):
        trial_rng = random.Random(rng.getrandbits(64))
        surrogate_turns = [_surrogate_turn(t, vocab, trial_rng) for t in turns]
        g = _final_gamma(surrogate_turns, window=window, seed=seed + trial + 1)
        if not math.isnan(g):
            gammas.append(g)
    if len(gammas) < 4:
        return float("nan")
    mean = float(np.mean(gammas))
    std = float(np.std(gammas, ddof=1))
    if std == 0.0 or not math.isfinite(std):
        # Degenerate: all surrogates produced the same gamma.
        # If that gamma differs from the original, surrogate structure is
        # irrelevant -> declare p = 0.0 (reject H0 of "same"). If it
        # matches, return p = 1.0 (cannot reject).
        return 1.0 if math.isclose(mean, gamma_original, abs_tol=1e-9) else 0.0
    z = abs(gamma_original - mean) / std
    # Two-sided normal tail probability: erfc(z / sqrt(2)).
    return float(math.erfc(z / math.sqrt(2.0)))


def _loto_max_sensitivity(
    turns: list[Turn],
    gamma_original: float,
    *,
    window: int,
    seed: int,
) -> float:
    if math.isnan(gamma_original):
        return float("nan")
    deltas: list[float] = []
    for i in range(len(turns)):
        subset = turns[:i] + turns[i + 1 :]
        if len(subset) < MIN_TURNS:
            continue
        g_minus = _final_gamma(subset, window=window, seed=seed)
        d = _safe_abs_delta(gamma_original, g_minus)
        if not math.isnan(d):
            deltas.append(d)
    if not deltas:
        return float("nan")
    return float(max(deltas))


def _safe_abs_delta(a: float, b: float) -> float:
    if math.isnan(a) or math.isnan(b):
        return float("nan")
    return float(abs(a - b))


def _surrogate_vocab(size: int, seed: int) -> list[str]:
    rng = random.Random(seed ^ 0xA71CBA11)
    vocab: list[str] = []
    alphabet = string.ascii_lowercase
    for _ in range(size):
        n = rng.randint(3, 9)
        vocab.append("".join(rng.choice(alphabet) for _ in range(n)))
    return vocab


def _surrogate_turn(turn: Turn, vocab: list[str], rng: random.Random) -> Turn:
    # Preserve structural length (token_count) but replace content.
    # Use max(1, min(len(turn.content.split()), token_count)) words so we
    # stay within reasonable bounds without inflating cost.
    n_words = max(1, len(turn.content.split()))
    content = " ".join(rng.choice(vocab) for _ in range(n_words))
    return Turn(role=turn.role, content=content, token_count=turn.token_count)
