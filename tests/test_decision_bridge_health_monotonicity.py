"""Falsification battery for ``_compute_health`` — monotonicity audit.

A health classifier that is *not* monotone under dominance is a bug
generator: a system could get healthier along every measured axis
while the verdict silently drops. We falsify that possibility here.

Dominance partial order
-----------------------
We say signal set ``s'`` **dominates** ``s`` (write ``s' ≥ s``) if
every axis is at least as good:

    gradient_diagnosis:  dead_equilibrium < static_capacitor < transient < living_gradient
    operating_regime:    chaotic < frozen < critical
    hallucination_risk:  high < moderate < low
    stable:              False < True
    gamma distance:      |γ − 1| is ≤

Contract (I-DB-H1):
    s' ≥ s ⇒ rank(health(s')) ≥ rank(health(s))

where the health rank is:
    DEAD < CRITICAL < DEGRADED < OPTIMAL.

We enumerate the full Cartesian product of the enum-valued axes
(deterministic, not sampled) and sanity-check continuous axes with
Hypothesis.
"""

from __future__ import annotations

from itertools import product

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.decision_bridge import _compute_health

# Ranking tables (higher = better).
_DIAG_RANK = {
    "dead_equilibrium": 0,
    "static_capacitor": 1,
    "unknown": 2,
    "transient": 3,
    "living_gradient": 4,
}
_REGIME_RANK = {"chaotic": 0, "frozen": 1, "critical": 2}
_RISK_RANK = {"high": 0, "moderate": 1, "low": 2}
_STABLE_RANK = {False: 0, True: 1}
_HEALTH_RANK = {"DEAD": 0, "CRITICAL": 1, "DEGRADED": 2, "OPTIMAL": 3}


def _dominates(
    diag_a: str,
    regime_a: str,
    risk_a: str,
    stable_a: bool,
    gamma_a: float,
    diag_b: str,
    regime_b: str,
    risk_b: str,
    stable_b: bool,
    gamma_b: float,
) -> bool:
    """True iff (a) weakly dominates (b) on every axis."""
    return (
        _DIAG_RANK[diag_a] >= _DIAG_RANK[diag_b]
        and _REGIME_RANK[regime_a] >= _REGIME_RANK[regime_b]
        and _RISK_RANK[risk_a] >= _RISK_RANK[risk_b]
        and _STABLE_RANK[stable_a] >= _STABLE_RANK[stable_b]
        and abs(gamma_a - 1.0) <= abs(gamma_b - 1.0)
    )


# ─────────────────────────────────────────────────────────────────────────
# I-DB-H1 — exhaustive enumeration of the discrete axes.
# ─────────────────────────────────────────────────────────────────────────


class TestHealthMonotonicityExhaustive:
    def test_monotonicity_over_discrete_axes(self) -> None:
        """All pairs on the discrete axes with fixed γ satisfy I-DB-H1."""
        gamma_values = [1.0, 1.1, 1.2, 0.9, 0.5, 1.5]
        violations: list[str] = []
        for diag_a, diag_b in product(_DIAG_RANK, repeat=2):
            for reg_a, reg_b in product(_REGIME_RANK, repeat=2):
                for risk_a, risk_b in product(_RISK_RANK, repeat=2):
                    for stable_a, stable_b in product([False, True], repeat=2):
                        for g_a in gamma_values:
                            for g_b in gamma_values:
                                if _dominates(
                                    diag_a,
                                    reg_a,
                                    risk_a,
                                    stable_a,
                                    g_a,
                                    diag_b,
                                    reg_b,
                                    risk_b,
                                    stable_b,
                                    g_b,
                                ):
                                    ha = _compute_health(diag_a, reg_a, risk_a, stable_a, g_a)
                                    hb = _compute_health(diag_b, reg_b, risk_b, stable_b, g_b)
                                    if _HEALTH_RANK[ha] < _HEALTH_RANK[hb]:
                                        violations.append(
                                            f"({diag_a},{reg_a},{risk_a},"
                                            f"{stable_a},γ={g_a}) "
                                            f"dominates "
                                            f"({diag_b},{reg_b},{risk_b},"
                                            f"{stable_b},γ={g_b}) "
                                            f"but health {ha} < {hb}"
                                        )
        assert not violations, "\n".join(violations[:20])


# ─────────────────────────────────────────────────────────────────────────
# Absorbing states — DEAD and CRITICAL must not upgrade.
# ─────────────────────────────────────────────────────────────────────────


class TestHealthAbsorbingStates:
    @pytest.mark.parametrize(
        ("regime", "risk", "stable", "gamma"),
        [
            ("critical", "low", True, 1.0),
            ("frozen", "moderate", True, 1.05),
            ("chaotic", "high", False, 1.3),
        ],
    )
    def test_dead_equilibrium_is_absorbing(
        self, regime: str, risk: str, stable: bool, gamma: float
    ) -> None:
        """No upstream signal can lift the verdict off DEAD."""
        assert _compute_health("dead_equilibrium", regime, risk, stable, gamma) == "DEAD"

    @pytest.mark.parametrize(
        ("diag", "regime", "risk", "gamma"),
        [
            ("living_gradient", "critical", "low", 1.0),
            ("transient", "frozen", "moderate", 1.05),
        ],
    )
    def test_unstable_is_critical(self, diag: str, regime: str, risk: str, gamma: float) -> None:
        """State-space-unstable cannot be OPTIMAL."""
        assert _compute_health(diag, regime, risk, False, gamma) == "CRITICAL"


# ─────────────────────────────────────────────────────────────────────────
# OPTIMAL is rare on purpose — witness the narrow admissibility region.
# ─────────────────────────────────────────────────────────────────────────


class TestHealthOptimalGate:
    def test_optimal_requires_every_axis_aligned(self) -> None:
        good = _compute_health("living_gradient", "critical", "low", True, 1.0)
        assert good == "OPTIMAL"

    def test_single_axis_degradation_blocks_optimal(self) -> None:
        # Flip only hallucination risk: OPTIMAL → DEGRADED.
        assert _compute_health("living_gradient", "critical", "moderate", True, 1.0) != "OPTIMAL"
        # Flip only regime: OPTIMAL → DEGRADED.
        assert _compute_health("living_gradient", "frozen", "low", True, 1.0) != "OPTIMAL"
        # Flip only γ distance: OPTIMAL → DEGRADED.
        assert _compute_health("living_gradient", "critical", "low", True, 1.5) != "OPTIMAL"


# ─────────────────────────────────────────────────────────────────────────
# Continuous-axis sanity via Hypothesis.
# ─────────────────────────────────────────────────────────────────────────


class TestHealthContinuousAxis:
    @settings(max_examples=200, deadline=None)
    @given(
        gamma_a=st.floats(min_value=0.5, max_value=1.5, allow_nan=False),
        gamma_b=st.floats(min_value=0.5, max_value=1.5, allow_nan=False),
    )
    def test_gamma_closer_to_one_never_demotes(self, gamma_a: float, gamma_b: float) -> None:
        """Fix every discrete axis at the 'good' value; only γ varies.

        If ``|γ_a − 1| ≤ |γ_b − 1|``, health(a) must not be ranked
        strictly below health(b).
        """
        if abs(gamma_a - 1.0) > abs(gamma_b - 1.0):
            gamma_a, gamma_b = gamma_b, gamma_a
        ha = _compute_health("living_gradient", "critical", "low", True, gamma_a)
        hb = _compute_health("living_gradient", "critical", "low", True, gamma_b)
        assert _HEALTH_RANK[ha] >= _HEALTH_RANK[hb]
