"""Unit tests for sleep replay utilities."""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.sleep.replay import (
    add_replay_noise,
    validate_noise_level,
    weighted_pattern_selection,
)


def _patterns() -> list[np.ndarray]:
    return [
        np.array([1.0, 0.0], dtype=np.float64),
        np.array([0.0, 1.0], dtype=np.float64),
    ]


def test_weighted_pattern_selection_rejects_non_1d_importance() -> None:
    rng = np.random.default_rng(0)
    importance = np.array([[1.0, 2.0]], dtype=np.float64)

    with pytest.raises(ValueError, match="importance must be a 1D array"):
        weighted_pattern_selection(_patterns(), importance, rng)


def test_weighted_pattern_selection_rejects_non_finite_importance() -> None:
    rng = np.random.default_rng(0)
    importance = np.array([1.0, np.inf], dtype=np.float64)

    with pytest.raises(ValueError, match="importance must be finite"):
        weighted_pattern_selection(_patterns(), importance, rng)


def test_weighted_pattern_selection_rejects_negative_importance() -> None:
    rng = np.random.default_rng(0)
    importance = np.array([1.0, -0.5], dtype=np.float64)

    with pytest.raises(ValueError, match="importance must be non-negative"):
        weighted_pattern_selection(_patterns(), importance, rng)


def test_weighted_pattern_selection_rejects_empty_patterns() -> None:
    rng = np.random.default_rng(0)
    importance = np.array([1.0], dtype=np.float64)

    with pytest.raises(ValueError, match="patterns list is empty"):
        weighted_pattern_selection([], importance, rng)


def test_weighted_pattern_selection_rejects_length_mismatch() -> None:
    rng = np.random.default_rng(0)
    importance = np.array([1.0, 2.0, 3.0], dtype=np.float64)

    with pytest.raises(ValueError, match="importance length must match patterns length"):
        weighted_pattern_selection(_patterns(), importance, rng)


def test_weighted_pattern_selection_uniform_weights_is_deterministic() -> None:
    patterns = _patterns()
    importance = np.zeros(len(patterns), dtype=np.float64)
    expected_rng = np.random.default_rng(123)
    rng = np.random.default_rng(123)
    expected_idx = expected_rng.choice(len(patterns), p=np.array([0.5, 0.5]))

    selected = weighted_pattern_selection(patterns, importance, rng)

    assert np.array_equal(selected, patterns[expected_idx])


def test_weighted_pattern_selection_returns_copy() -> None:
    patterns = _patterns()
    rng = np.random.default_rng(0)

    selected = weighted_pattern_selection(patterns, np.array([1.0, 0.0], dtype=np.float64), rng)
    selected[0] = 99.0

    assert patterns[0][0] == 1.0


def test_validate_noise_level_rejects_out_of_range() -> None:
    with pytest.raises(ValueError, match="noise_level must be in \\[0, 1\\]"):
        validate_noise_level(-0.1)

    with pytest.raises(ValueError, match="noise_level must be in \\[0, 1\\]"):
        validate_noise_level(1.1)


def test_add_replay_noise_zero_level_returns_copy() -> None:
    rng = np.random.default_rng(0)
    pattern = np.array([1.0, -1.0], dtype=np.float64)

    noisy = add_replay_noise(pattern, noise_level=0.0, noise_scale=1.0, rng=rng)

    assert np.array_equal(noisy, pattern)
    assert noisy is not pattern


def test_add_replay_noise_rejects_out_of_range_level() -> None:
    rng = np.random.default_rng(0)
    pattern = np.array([1.0, -1.0], dtype=np.float64)

    with pytest.raises(ValueError, match="noise_level must be in \\[0, 1\\]"):
        add_replay_noise(pattern, noise_level=1.1, noise_scale=1.0, rng=rng)


def test_add_replay_noise_applies_noise() -> None:
    rng = np.random.default_rng(0)
    pattern = np.array([1.0, -1.0], dtype=np.float64)

    noisy = add_replay_noise(pattern, noise_level=0.5, noise_scale=1.0, rng=rng)

    assert noisy.shape == pattern.shape
    assert np.all(np.isfinite(noisy))
    assert not np.array_equal(noisy, pattern)
