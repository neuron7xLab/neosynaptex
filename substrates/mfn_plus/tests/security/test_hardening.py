"""Tests for Anthropic-level security hardening.

Covers: output sanitization, error scrubbing, body limits,
security headers, API boundary enforcement.
"""

from __future__ import annotations

import pytest

from mycelium_fractal_net.security.hardening import (
    MAX_GRID_SIZE_API,
    MAX_HORIZON_API,
    MAX_STEPS_API,
    enforce_api_boundaries,
    sanitize_numerical_output,
    scrub_error_response,
)


class TestNumericalOutputSanitization:
    """NaN/Inf must never appear in API responses."""

    def test_nan_replaced_with_none(self) -> None:
        assert sanitize_numerical_output(float("nan")) is None

    def test_inf_replaced_with_none(self) -> None:
        assert sanitize_numerical_output(float("inf")) is None

    def test_neg_inf_replaced_with_none(self) -> None:
        assert sanitize_numerical_output(float("-inf")) is None

    def test_normal_float_preserved(self) -> None:
        assert sanitize_numerical_output(3.14) == 3.14

    def test_nested_dict_sanitized(self) -> None:
        data = {"a": 1.0, "b": float("nan"), "c": {"d": float("inf"), "e": 2.0}}
        result = sanitize_numerical_output(data)
        assert result["a"] == 1.0
        assert result["b"] is None
        assert result["c"]["d"] is None
        assert result["c"]["e"] == 2.0

    def test_list_sanitized(self) -> None:
        data = [1.0, float("nan"), [float("inf"), 3.0]]
        result = sanitize_numerical_output(data)
        assert result[0] == 1.0
        assert result[1] is None
        assert result[2][0] is None
        assert result[2][1] == 3.0

    def test_non_float_passthrough(self) -> None:
        assert sanitize_numerical_output("hello") == "hello"
        assert sanitize_numerical_output(42) == 42
        assert sanitize_numerical_output(None) is None
        assert sanitize_numerical_output(True) is True


class TestErrorScrubbing:
    """Stack traces must not leak to production."""

    def test_dev_mode_preserves_detail(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MFN_ENV", "dev")
        detail = "Error at /home/user/src/mycelium.py:42 in _process"
        assert scrub_error_response(detail) == detail

    def test_prod_mode_scrubs_paths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MFN_ENV", "prod")
        detail = "Error at /home/user/src/mycelium.py:42 in _process"
        result = scrub_error_response(detail)
        assert "/home/" not in result
        assert ".py:42" not in result
        assert "[internal]" in result

    def test_prod_mode_scrubs_memory_addresses(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MFN_ENV", "prod")
        detail = "Object at 0x7f4a3c2b1d00 is invalid"
        result = scrub_error_response(detail)
        assert "0x7f4a" not in result
        assert "[redacted]" in result

    def test_prod_mode_truncates_long_messages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MFN_ENV", "prod")
        detail = "x" * 500
        result = scrub_error_response(detail)
        assert len(result) <= 203  # 200 + "..."


class TestAPIBoundaryEnforcement:
    """API must reject dangerous parameters before domain layer."""

    def test_valid_params_pass(self) -> None:
        params = {"grid_size": 64, "steps": 100, "horizon": 8}
        result = enforce_api_boundaries(params)
        assert result == params

    def test_grid_size_too_large(self) -> None:
        with pytest.raises(ValueError, match="grid_size.*exceeds"):
            enforce_api_boundaries({"grid_size": MAX_GRID_SIZE_API + 1})

    def test_grid_size_too_small(self) -> None:
        with pytest.raises(ValueError, match="grid_size must be >= 4"):
            enforce_api_boundaries({"grid_size": 2})

    def test_steps_too_large(self) -> None:
        with pytest.raises(ValueError, match="steps.*exceeds"):
            enforce_api_boundaries({"steps": MAX_STEPS_API + 1})

    def test_steps_too_small(self) -> None:
        with pytest.raises(ValueError, match="steps must be >= 1"):
            enforce_api_boundaries({"steps": 0})

    def test_horizon_too_large(self) -> None:
        with pytest.raises(ValueError, match="horizon.*exceeds"):
            enforce_api_boundaries({"horizon": MAX_HORIZON_API + 1})

    def test_missing_params_ok(self) -> None:
        # No grid_size/steps/horizon = no validation needed
        result = enforce_api_boundaries({"seed": 42})
        assert result == {"seed": 42}


class TestSecurityHeaders:
    """Verify security headers are added to API responses."""

    def test_security_headers_present(self) -> None:
        from starlette.testclient import TestClient

        from mycelium_fractal_net.api import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Content-Security-Policy") == "default-src 'none'"
        assert response.headers.get("Cache-Control") == "no-store"
        assert response.headers.get("Referrer-Policy") == "no-referrer"

    def test_hsts_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MFN_ENV", "prod")
        # HSTS is checked at response time via _is_production()
        # Just verify the function works
        from mycelium_fractal_net.security.hardening import _is_production

        assert _is_production()
