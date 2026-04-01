"""Tests for API configuration alignment across components."""

from __future__ import annotations

import os

from mycelium_fractal_net.integration.api_config import APIConfig, reset_config


def _clear_env_vars() -> None:
    for var in [
        "MFN_ENV",
        "MFN_METRICS_ENABLED",
        "MFN_METRICS_INCLUDE_IN_AUTH",
        "MFN_METRICS_ENDPOINT",
        "MFN_RATE_LIMIT_REQUESTS",
        "MFN_RATE_LIMIT_WINDOW",
    ]:
        os.environ.pop(var, None)


def test_metrics_public_by_default(monkeypatch) -> None:
    """Metrics endpoint should remain public when auth is not requested."""

    _clear_env_vars()
    reset_config()

    config = APIConfig.from_env()

    assert config.metrics.include_in_auth is False
    assert "/metrics" in config.auth.public_endpoints


def test_metrics_can_be_protected(monkeypatch) -> None:
    """Enabling metrics auth should remove the endpoint from public list."""

    _clear_env_vars()
    monkeypatch.setenv("MFN_METRICS_INCLUDE_IN_AUTH", "true")
    reset_config()

    config = APIConfig.from_env()

    assert config.metrics.include_in_auth is True
    assert "/metrics" not in config.auth.public_endpoints


def test_metrics_endpoint_can_be_customized(monkeypatch) -> None:
    """Custom metrics paths should propagate into public endpoints."""

    _clear_env_vars()
    monkeypatch.setenv("MFN_METRICS_ENDPOINT", "/custom-metrics")
    reset_config()

    config = APIConfig.from_env()

    assert config.metrics.endpoint == "/custom-metrics"
    assert "/custom-metrics" in config.auth.public_endpoints
    assert "/metrics" not in config.auth.public_endpoints


def test_auth_required_without_keys_raises(monkeypatch) -> None:
    """Requiring API keys should fail fast when no keys are configured."""

    _clear_env_vars()
    monkeypatch.setenv("MFN_API_KEY_REQUIRED", "true")
    # Ensure no default keys are injected
    monkeypatch.delenv("MFN_API_KEY", raising=False)
    monkeypatch.delenv("MFN_API_KEYS", raising=False)
    reset_config()

    try:
        APIConfig.from_env()
    except ValueError as exc:
        assert "no API keys were provided" in str(exc)
    else:
        raise AssertionError("Expected ValueError when auth is required but no keys set")


def test_rate_limit_invalid_requests_raises(monkeypatch) -> None:
    """Invalid rate limit request values should raise a clear error."""

    _clear_env_vars()
    monkeypatch.setenv("MFN_RATE_LIMIT_REQUESTS", "not-a-number")
    reset_config()

    try:
        APIConfig.from_env()
    except ValueError as exc:
        assert "MFN_RATE_LIMIT_REQUESTS must be an integer" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid rate limit request value")


def test_rate_limit_invalid_window_raises(monkeypatch) -> None:
    """Non-positive rate limit windows should raise a clear error."""

    _clear_env_vars()
    monkeypatch.setenv("MFN_RATE_LIMIT_WINDOW", "0")
    reset_config()

    try:
        APIConfig.from_env()
    except ValueError as exc:
        assert "MFN_RATE_LIMIT_WINDOW must be a positive integer" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid rate limit window value")
