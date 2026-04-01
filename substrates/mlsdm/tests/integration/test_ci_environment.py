"""Integration tests for CI environment behavior.

These tests verify that the tracing configuration works correctly
in CI environments and handles environment variable isolation properly.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from mlsdm.observability.tracing import TracerManager, TracingConfig

if TYPE_CHECKING:
    import pytest


class TestCIEnvironmentBehavior:
    """Tests that verify correct behavior in CI environment."""

    def test_default_config_in_clean_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that default config works in clean CI environment."""
        # Simulate fresh CI environment
        for key in list(os.environ.keys()):
            if key.startswith("OTEL_") or key.startswith("MLSDM_OTEL"):
                monkeypatch.delenv(key, raising=False)

        config = TracingConfig()
        assert config.enabled is True
        assert config.service_name == "mlsdm"

    def test_config_after_disabled_test(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that config works correctly after a test that disables tracing."""
        # Simulate a previous test that disabled tracing
        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")

        config1 = TracingConfig()
        assert config1.enabled is False

        # Now simulate cleanup and next test
        monkeypatch.delenv("OTEL_SDK_DISABLED")

        config2 = TracingConfig()
        assert config2.enabled is True

    def test_tracer_manager_isolation(self) -> None:
        """Test that TracerManager properly resets between instances."""
        # First instance with disabled tracing
        TracerManager.reset_instance()
        config1 = TracingConfig(enabled=False, _env={})
        manager1 = TracerManager.get_instance(config1)
        assert manager1._config.enabled is False

        # Reset and create new instance with enabled tracing
        TracerManager.reset_instance()
        config2 = TracingConfig(enabled=True, exporter_type="console", _env={})
        manager2 = TracerManager.get_instance(config2)
        assert manager2._config.enabled is True

        # Verify they are different instances
        assert manager1 is not manager2

    def test_env_injection_prevents_pollution(self) -> None:
        """Test that _env parameter prevents environment pollution."""
        # Set environment variable that should NOT affect configs using _env
        os.environ["OTEL_SDK_DISABLED"] = "true"

        try:
            # Config with _env={} should ignore global environment
            config1 = TracingConfig(_env={})
            assert config1.enabled is True

            # Config without _env should read global environment
            config2 = TracingConfig()
            assert config2.enabled is False

            # Config with explicit _env should override everything
            config3 = TracingConfig(_env={"OTEL_SDK_DISABLED": "false"})
            assert config3.enabled is True
        finally:
            # Clean up
            del os.environ["OTEL_SDK_DISABLED"]

    def test_multiple_configs_no_cross_contamination(self) -> None:
        """Test that multiple TracingConfig instances don't affect each other."""
        configs = []

        # Create 10 configs with alternating settings
        for i in range(10):
            enabled = i % 2 == 0
            config = TracingConfig(
                enabled=enabled,
                service_name=f"service-{i}",
                _env={},
            )
            configs.append(config)

        # Verify all configs retained their settings
        for i, config in enumerate(configs):
            expected_enabled = i % 2 == 0
            assert config.enabled == expected_enabled
            assert config.service_name == f"service-{i}"
