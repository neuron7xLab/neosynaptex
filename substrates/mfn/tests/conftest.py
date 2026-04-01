"""
Global pytest configuration and fixtures for MFN tests.

Sets up the test environment to ensure consistent behavior across all tests.
"""

from __future__ import annotations

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest: env vars + Hypothesis profiles."""
    if "MFN_ENV" not in os.environ:
        os.environ["MFN_ENV"] = "dev"
    if "MFN_API_KEY_REQUIRED" not in os.environ:
        os.environ["MFN_API_KEY_REQUIRED"] = "false"
    if "MFN_RATE_LIMIT_ENABLED" not in os.environ:
        os.environ["MFN_RATE_LIMIT_ENABLED"] = "false"

    # Hypothesis profiles: fast (PR), ci (default), full (nightly)
    try:
        from hypothesis import HealthCheck
        from hypothesis import settings as h_settings

        h_settings.register_profile(
            "fast",
            max_examples=20,
            deadline=2000,
            suppress_health_check=[HealthCheck.too_slow],
        )
        h_settings.register_profile(
            "ci",
            max_examples=50,
            deadline=5000,
            suppress_health_check=[HealthCheck.too_slow],
        )
        h_settings.register_profile(
            "full",
            max_examples=500,
            deadline=None,
            suppress_health_check=[HealthCheck.too_slow],
        )
        profile = os.environ.get("BIO_HYPOTHESIS_PROFILE", "fast")
        h_settings.load_profile(profile)
    except ImportError:
        pass


@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """
    Session-scoped fixture to ensure test environment is properly configured.

    This runs once at the start of the test session.
    """
    # Store original values
    original_env = os.environ.get("MFN_ENV")
    original_auth = os.environ.get("MFN_API_KEY_REQUIRED")
    original_rate = os.environ.get("MFN_RATE_LIMIT_ENABLED")

    # Set test environment
    os.environ["MFN_ENV"] = "dev"
    os.environ["MFN_API_KEY_REQUIRED"] = "false"
    os.environ["MFN_RATE_LIMIT_ENABLED"] = "false"

    yield

    # Restore original values
    if original_env is not None:
        os.environ["MFN_ENV"] = original_env
    elif "MFN_ENV" in os.environ:
        del os.environ["MFN_ENV"]

    if original_auth is not None:
        os.environ["MFN_API_KEY_REQUIRED"] = original_auth
    elif "MFN_API_KEY_REQUIRED" in os.environ:
        del os.environ["MFN_API_KEY_REQUIRED"]

    if original_rate is not None:
        os.environ["MFN_RATE_LIMIT_ENABLED"] = original_rate
    elif "MFN_RATE_LIMIT_ENABLED" in os.environ:
        del os.environ["MFN_RATE_LIMIT_ENABLED"]


# === Shared fixtures for common test patterns ===


@pytest.fixture(scope="session")
def baseline_spec():
    """Canonical baseline SimulationSpec (seed=42, 16x16, 16 steps)."""
    from mycelium_fractal_net.types.field import SimulationSpec

    return SimulationSpec(grid_size=16, steps=16, seed=42)


@pytest.fixture(scope="session")
def baseline_sequence(baseline_spec):
    """Pre-computed FieldSequence from baseline spec. Session-scoped for speed."""
    from mycelium_fractal_net.core.simulate import simulate_history

    return simulate_history(baseline_spec)


@pytest.fixture(scope="session")
def baseline_descriptor(baseline_sequence):
    """Pre-computed MorphologyDescriptor from baseline sequence."""
    from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor

    return compute_morphology_descriptor(baseline_sequence)


@pytest.fixture(autouse=True)
def clear_descriptor_cache():
    """Clear descriptor cache between tests to prevent cross-test contamination."""
    from mycelium_fractal_net.analytics.morphology import _descriptor_cache

    _descriptor_cache.clear()
    yield
    _descriptor_cache.clear()


# ── Benchmark baseline loader ─────────────────────────────────────────────────


@pytest.fixture(scope="session")
def bio_baseline():
    """Load calibrated benchmark baselines from JSON."""
    import json
    from pathlib import Path

    p = Path(__file__).parent.parent / "benchmarks" / "bio_baseline.json"
    if p.exists():
        return json.loads(p.read_text())
    return {
        "physarum_step_32": {"median_ms": 100.0, "p95_ms": 150.0},
        "memory_query_200": {"median_ms": 5.0, "p95_ms": 10.0},
        "hdv_encode": {"median_ms": 2.0, "p95_ms": 3.0},
        "bio_step_16": {"median_ms": 50.0, "p95_ms": 80.0},
        "meta_single_eval": {"median_ms": 500.0, "p95_ms": 800.0},
    }
