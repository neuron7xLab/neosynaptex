"""Tests for auto_heal — closed cognitive loop."""

from __future__ import annotations

import json

import pytest

import mycelium_fractal_net as mfn


@pytest.fixture(scope="module")
def healthy() -> mfn.FieldSequence:
    return mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=30, seed=42))


@pytest.fixture(scope="module")
def stressed() -> mfn.FieldSequence:
    return mfn.simulate(
        mfn.SimulationSpec(
            grid_size=16,
            steps=30,
            seed=42,
            alpha=0.24,
            jitter_var=0.008,
            quantum_jitter=True,
        )
    )


def test_healthy_no_intervention(healthy: mfn.FieldSequence) -> None:
    """Healthy system should not trigger healing."""
    r = mfn.auto_heal(healthy)
    assert isinstance(r, mfn.HealResult)
    assert not r.needs_healing or not r.intervention_applied
    assert r.M_before > 0
    assert r.compute_time_ms > 0


def test_stressed_triggers_healing(stressed: mfn.FieldSequence) -> None:
    """Stressed system should trigger intervention."""
    r = mfn.auto_heal(stressed)
    assert r.needs_healing
    assert r.intervention_applied
    assert len(r.changes) > 0


def test_heal_has_delta_M(stressed: mfn.FieldSequence) -> None:
    """After healing, delta_M should exist."""
    r = mfn.auto_heal(stressed)
    if r.intervention_applied:
        assert r.delta_M is not None
        assert r.M_after is not None
        assert r.delta_anomaly is not None


def test_heal_anomaly_decreases(stressed: mfn.FieldSequence) -> None:
    """Anomaly score should decrease after successful healing."""
    r = mfn.auto_heal(stressed)
    if r.healed:
        assert r.anomaly_score_after <= r.anomaly_score_before + 0.02


def test_heal_json_serializable(stressed: mfn.FieldSequence) -> None:
    """HealResult must be JSON-serializable."""
    r = mfn.auto_heal(stressed)
    d = r.to_dict()
    json.dumps(d)
    assert "before" in d
    assert "after" in d
    assert "verification" in d


def test_heal_summary(stressed: mfn.FieldSequence) -> None:
    """Summary string must contain key info."""
    r = mfn.auto_heal(stressed)
    s = r.summary()
    assert "[HEAL]" in s
    assert "M:" in s or "healthy" in s.lower()


# ── EXPERIENCE MEMORY ─────────────────────────────────────────────────────


def test_experience_memory_accumulates() -> None:
    """Memory should grow with each heal call."""
    mem = mfn.ExperienceMemory(min_experiences=3)
    for seed in range(5):
        seq = mfn.simulate(
            mfn.SimulationSpec(
                grid_size=16,
                steps=20,
                seed=seed,
                alpha=0.22,
                jitter_var=0.005,
                quantum_jitter=True,
            )
        )
        mfn.auto_heal(seq, memory=mem)
    assert mem.size >= 3


def test_experience_prediction_after_min() -> None:
    """After min_experiences, prediction should kick in."""
    mem = mfn.ExperienceMemory(min_experiences=3)
    results = []
    for seed in range(6):
        seq = mfn.simulate(
            mfn.SimulationSpec(
                grid_size=16,
                steps=20,
                seed=seed,
                alpha=0.22,
                jitter_var=0.005,
                quantum_jitter=True,
            )
        )
        r = mfn.auto_heal(seq, memory=mem)
        results.append(r)
    # Later results should have prediction
    has_prediction = any(r.prediction_used for r in results)
    assert has_prediction, "Prediction should activate after min_experiences"


def test_experience_stats() -> None:
    """Stats should be well-formed."""
    mem = mfn.ExperienceMemory(min_experiences=2)
    s = mem.stats()
    assert s["size"] == 0
    assert not mem.can_predict
