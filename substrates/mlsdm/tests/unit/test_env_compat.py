"""Tests for environment variable compatibility layer."""

import os
from unittest.mock import patch

import pytest

from mlsdm.config.env_compat import (
    apply_env_compat,
    get_env_compat_info,
    warn_if_legacy_vars_used,
)


class TestEnvCompat:
    """Test environment variable compatibility layer."""

    def test_apply_env_compat_is_noop(self):
        """Test apply_env_compat is a no-op (compatibility preserved)."""
        with patch.dict(os.environ, {"DISABLE_RATE_LIMIT": "1"}, clear=False):
            # Should not modify environment
            before = dict(os.environ)
            apply_env_compat()
            after = dict(os.environ)

            assert before == after

    def test_warn_if_legacy_vars_returns_empty(self):
        """Test no legacy variables are reported (all are stable API)."""
        with patch.dict(
            os.environ,
            {
                "DISABLE_RATE_LIMIT": "1",
                "CONFIG_PATH": "config/test.yaml",
                "LLM_BACKEND": "openai",
            },
            clear=False,
        ):
            legacy = warn_if_legacy_vars_used()
            assert len(legacy) == 0

    def test_get_env_compat_info_structure(self):
        """Test get_env_compat_info returns expected structure."""
        info = get_env_compat_info()

        assert "DISABLE_RATE_LIMIT" in info
        assert "CONFIG_PATH" in info
        assert "LLM_BACKEND" in info

        # Check each entry has expected keys
        for var_info in info.values():
            assert "status" in var_info
            assert "current_value" in var_info
            assert "note" in var_info

    def test_get_env_compat_info_with_values(self):
        """Test get_env_compat_info returns correct values."""
        with patch.dict(
            os.environ,
            {
                "DISABLE_RATE_LIMIT": "1",
                "CONFIG_PATH": "config/test.yaml",
                "LLM_BACKEND": "openai",
            },
            clear=False,
        ):
            info = get_env_compat_info()

            assert info["DISABLE_RATE_LIMIT"]["current_value"] == "1"
            assert info["CONFIG_PATH"]["current_value"] == "config/test.yaml"
            assert info["LLM_BACKEND"]["current_value"] == "openai"

            # All should have stable status
            assert info["DISABLE_RATE_LIMIT"]["status"] == "stable"
            assert info["CONFIG_PATH"]["status"] == "stable"
            assert info["LLM_BACKEND"]["status"] == "stable"

    def test_apply_env_compat_is_idempotent(self):
        """Test that apply_env_compat can be called multiple times safely."""
        with patch.dict(os.environ, {"DISABLE_RATE_LIMIT": "1"}, clear=False):
            before = dict(os.environ)

            # First call
            apply_env_compat()
            after_first = dict(os.environ)

            # Second call
            apply_env_compat()
            after_second = dict(os.environ)

            # Should remain unchanged
            assert before == after_first == after_second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
