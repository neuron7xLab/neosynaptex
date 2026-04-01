"""Tests for entrypoint deprecation warnings."""

import os
import warnings
from unittest.mock import patch

import pytest


class TestEntrypointDeprecations:
    """Test that entrypoints emit deprecation warnings."""

    def test_dev_entrypoint_deprecation_warning(self):
        """Test dev_entry emits deprecation warning."""
        with patch("mlsdm.entrypoints.serve.serve") as mock_serve:
            mock_serve.return_value = 0

            with pytest.warns(DeprecationWarning, match="python -m mlsdm.entrypoints.dev"):
                from mlsdm.entrypoints.dev_entry import main

                # Mock health check to avoid side effects
                with patch("mlsdm.entrypoints.health.health_check") as mock_health:
                    mock_health.return_value = {
                        "status": "healthy",
                        "checks": {},
                    }

                    result = main()

            assert result == 0
            assert mock_serve.called

    def test_cloud_entrypoint_deprecation_warning(self):
        """Test cloud_entry emits deprecation warning."""
        with patch("mlsdm.entrypoints.serve.serve") as mock_serve:
            mock_serve.return_value = 0

            with pytest.warns(
                DeprecationWarning, match="python -m mlsdm.entrypoints.cloud"
            ):
                from mlsdm.entrypoints.cloud_entry import main

                # Mock health check to avoid side effects
                with patch("mlsdm.entrypoints.health.health_check") as mock_health:
                    mock_health.return_value = {
                        "status": "healthy",
                        "checks": {},
                    }

                    result = main()

            assert result == 0
            assert mock_serve.called

    def test_agent_entrypoint_deprecation_warning(self):
        """Test agent_entry emits deprecation warning."""
        with patch("mlsdm.entrypoints.serve.serve") as mock_serve:
            mock_serve.return_value = 0

            with pytest.warns(
                DeprecationWarning, match="python -m mlsdm.entrypoints.agent"
            ):
                from mlsdm.entrypoints.agent_entry import main

                # Mock health check to avoid side effects
                with patch("mlsdm.entrypoints.health.health_check") as mock_health:
                    mock_health.return_value = {
                        "status": "healthy",
                        "checks": {},
                    }

                    result = main()

            assert result == 0
            assert mock_serve.called

    def test_dev_entrypoint_applies_env_compat(self):
        """Test dev_entry applies environment compatibility layer."""
        with patch("mlsdm.entrypoints.serve.serve") as mock_serve:
            mock_serve.return_value = 0

            with patch("mlsdm.config.env_compat.apply_env_compat") as mock_compat:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)

                    from mlsdm.entrypoints.dev_entry import main

                    with patch("mlsdm.entrypoints.health.health_check") as mock_health:
                        mock_health.return_value = {
                            "status": "healthy",
                            "checks": {},
                        }

                        main()

                # Verify env_compat was called
                assert mock_compat.called

    def test_cloud_entrypoint_applies_env_compat(self):
        """Test cloud_entry applies environment compatibility layer."""
        with patch("mlsdm.entrypoints.serve.serve") as mock_serve:
            mock_serve.return_value = 0

            with patch("mlsdm.config.env_compat.apply_env_compat") as mock_compat:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)

                    from mlsdm.entrypoints.cloud_entry import main

                    with patch("mlsdm.entrypoints.health.health_check") as mock_health:
                        mock_health.return_value = {
                            "status": "healthy",
                            "checks": {},
                        }

                        main()

                # Verify env_compat was called
                assert mock_compat.called

    def test_agent_entrypoint_applies_env_compat(self):
        """Test agent_entry applies environment compatibility layer."""
        with patch("mlsdm.entrypoints.serve.serve") as mock_serve:
            mock_serve.return_value = 0

            with patch("mlsdm.config.env_compat.apply_env_compat") as mock_compat:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)

                    from mlsdm.entrypoints.agent_entry import main

                    with patch("mlsdm.entrypoints.health.health_check") as mock_health:
                        mock_health.return_value = {
                            "status": "healthy",
                            "checks": {},
                        }

                        main()

                # Verify env_compat was called
                assert mock_compat.called

    def test_entrypoints_set_correct_runtime_mode(self):
        """Test each entrypoint sets the correct MLSDM_RUNTIME_MODE."""
        with patch("mlsdm.entrypoints.serve.serve"), warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            from mlsdm.entrypoints.dev_entry import main as dev_main

            with patch("mlsdm.entrypoints.health.health_check") as mock_health:
                mock_health.return_value = {"status": "healthy", "checks": {}}
                dev_main()

            assert os.environ.get("MLSDM_RUNTIME_MODE") == "dev"

        with patch("mlsdm.entrypoints.serve.serve"), warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            from mlsdm.entrypoints.cloud_entry import main as cloud_main

            with patch("mlsdm.entrypoints.health.health_check") as mock_health:
                mock_health.return_value = {"status": "healthy", "checks": {}}
                cloud_main()

            assert os.environ.get("MLSDM_RUNTIME_MODE") == "cloud-prod"

        with patch("mlsdm.entrypoints.serve.serve"), warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            from mlsdm.entrypoints.agent_entry import main as agent_main

            with patch("mlsdm.entrypoints.health.health_check") as mock_health:
                mock_health.return_value = {"status": "healthy", "checks": {}}
                agent_main()

            assert os.environ.get("MLSDM_RUNTIME_MODE") == "agent-api"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

