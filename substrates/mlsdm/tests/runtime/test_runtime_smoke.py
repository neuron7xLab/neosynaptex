"""
Smoke tests for MLSDM runtime modes.

Tests basic functionality of each runtime mode:
- dev: Development mode
- cloud: Cloud production mode
- agent: Agent/API mode
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestRuntimeConfiguration:
    """Test runtime configuration module."""

    def test_import_config_runtime(self):
        """Test that config_runtime can be imported."""
        from mlsdm.config.runtime import (
            RuntimeMode,
            get_runtime_config,
            get_runtime_mode,
        )

        assert RuntimeMode.DEV.value == "dev"
        assert RuntimeMode.CLOUD_PROD.value == "cloud-prod"
        assert RuntimeMode.AGENT_API.value == "agent-api"
        assert callable(get_runtime_config)
        assert callable(get_runtime_mode)

    def test_get_runtime_mode_default(self):
        """Test default runtime mode is dev."""
        from mlsdm.config.runtime import RuntimeMode, get_runtime_mode

        with patch.dict(os.environ, {}, clear=True):
            # Clear MLSDM_RUNTIME_MODE
            os.environ.pop("MLSDM_RUNTIME_MODE", None)
            mode = get_runtime_mode()
            assert mode == RuntimeMode.DEV

    def test_get_runtime_mode_from_env(self):
        """Test runtime mode from environment."""
        from mlsdm.config.runtime import RuntimeMode, get_runtime_mode

        with patch.dict(os.environ, {"MLSDM_RUNTIME_MODE": "cloud-prod"}):
            mode = get_runtime_mode()
            assert mode == RuntimeMode.CLOUD_PROD

    def test_get_runtime_config_dev(self):
        """Test dev mode configuration."""
        from mlsdm.config.runtime import RuntimeMode, get_runtime_config

        config = get_runtime_config(RuntimeMode.DEV)
        assert config.mode == RuntimeMode.DEV
        assert config.server.reload is True
        assert config.debug is True
        assert config.security.rate_limit_enabled is False

    def test_get_runtime_config_cloud_prod(self):
        """Test cloud-prod mode configuration."""
        from mlsdm.config.runtime import RuntimeMode, get_runtime_config

        config = get_runtime_config(RuntimeMode.CLOUD_PROD)
        assert config.mode == RuntimeMode.CLOUD_PROD
        assert config.server.workers >= 1
        assert config.security.secure_mode is True
        assert config.observability.json_logging is True

    def test_get_runtime_config_agent_api(self):
        """Test agent-api mode configuration."""
        from mlsdm.config.runtime import RuntimeMode, get_runtime_config

        config = get_runtime_config(RuntimeMode.AGENT_API)
        assert config.mode == RuntimeMode.AGENT_API
        assert config.security.secure_mode is True
        assert config.engine.enable_fslgs is True

    def test_config_to_env_dict(self):
        """Test config to env dict conversion."""
        from mlsdm.config.runtime import RuntimeMode, get_runtime_config

        config = get_runtime_config(RuntimeMode.DEV)
        env_dict = config.to_env_dict()

        assert "HOST" in env_dict
        assert "PORT" in env_dict
        assert "LLM_BACKEND" in env_dict
        assert env_dict["PORT"] == str(config.server.port)


class TestHealthCheck:
    """Test entrypoint health check module."""

    def test_health_check_function(self):
        """Test health_check function returns expected structure."""
        from mlsdm.entrypoints.health import health_check

        result = health_check()
        assert "status" in result
        assert "timestamp" in result
        assert "checks" in result
        assert result["status"] in ("healthy", "degraded", "unhealthy")

    def test_is_healthy_function(self):
        """Test is_healthy returns boolean."""
        from mlsdm.entrypoints.health import is_healthy

        result = is_healthy()
        assert isinstance(result, bool)

    def test_get_health_status_function(self):
        """Test get_health_status returns string."""
        from mlsdm.entrypoints.health import get_health_status

        result = get_health_status()
        assert isinstance(result, str)
        assert result in ("healthy", "degraded", "unhealthy")

    def test_health_check_contains_expected_checks(self):
        """Test health_check contains expected check categories."""
        from mlsdm.entrypoints.health import health_check

        result = health_check()
        checks = result["checks"]

        assert "config" in checks
        assert "engine" in checks
        assert "memory_manager" in checks
        assert "system_resources" in checks

        # Each check should have healthy and details
        for check_name, check_result in checks.items():
            assert "healthy" in check_result
            assert "details" in check_result


class TestEntrypointsImport:
    """Test that entrypoints can be imported."""

    def test_import_dev_entry(self):
        """Test dev_entry can be imported."""
        from mlsdm.entrypoints.dev_entry import main

        assert callable(main)

    def test_import_cloud_entry(self):
        """Test cloud_entry can be imported."""
        from mlsdm.entrypoints.cloud_entry import main

        assert callable(main)

    def test_import_agent_entry(self):
        """Test agent_entry can be imported."""
        from mlsdm.entrypoints.agent_entry import main

        assert callable(main)

    def test_import_entrypoints_package(self):
        """Test entrypoints package can be imported."""
        from mlsdm.entrypoints import get_health_status, health_check, is_healthy

        assert callable(health_check)
        assert callable(is_healthy)
        assert callable(get_health_status)


class TestMakefileCommands:
    """Test Makefile commands exist."""

    MAKEFILE_PATH = "Makefile"

    @pytest.fixture
    def makefile_content(self) -> str:
        """Load Makefile content once for all tests."""
        with open(self.MAKEFILE_PATH) as f:
            return f.read()

    def test_makefile_has_run_dev(self, makefile_content: str):
        """Test Makefile has run-dev target."""
        assert "run-dev:" in makefile_content

    def test_makefile_has_run_cloud_local(self, makefile_content: str):
        """Test Makefile has run-cloud-local target."""
        assert "run-cloud-local:" in makefile_content

    def test_makefile_has_run_agent(self, makefile_content: str):
        """Test Makefile has run-agent target."""
        assert "run-agent:" in makefile_content

    def test_makefile_has_health_check(self, makefile_content: str):
        """Test Makefile has health-check target."""
        assert "health-check:" in makefile_content


class TestHealthCheckCLI:
    """Test health check can be run from command line."""

    def test_health_check_cli_runs(self):
        """Test health check CLI runs successfully."""
        repo_root = Path(__file__).resolve().parents[2]
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{repo_root / 'src'}:{env.get('PYTHONPATH', '')}".rstrip(":")
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.entrypoints.health"],
            capture_output=True,
            cwd=repo_root,
            env=env,
            text=True,
            timeout=30,
        )
        # Should output JSON and exit with 0 (success)
        assert result.returncode == 0
        assert "status" in result.stdout
        assert "checks" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
