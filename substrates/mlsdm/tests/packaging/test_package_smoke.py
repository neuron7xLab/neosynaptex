"""
Smoke tests for MLSDM package verification.

These tests verify that the package is correctly installed and
core functionality works.

Run with:
    pytest tests/packaging/test_package_smoke.py -v
"""

from pathlib import Path

import pytest


class TestPackageSmoke:
    """Smoke tests for package installation verification."""

    def test_package_import(self) -> None:
        """Test that mlsdm package can be imported.

        Verifies the package has the expected __version__ attribute.
        """
        import mlsdm

        assert mlsdm is not None
        assert hasattr(mlsdm, "__version__")

    def test_version_format(self) -> None:
        """Test that version follows semver format.

        Validates the version string matches semantic versioning pattern.
        """
        import re

        from mlsdm import __version__

        # Semver pattern: major.minor.patch with optional pre-release
        # Matches: 1.0.0, 1.2.3, 1.0.0-rc1, 1.0.0-alpha.1, etc.
        semver_pattern = r"^\d+\.\d+(\.\d+)?(-[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?$"
        assert re.match(
            semver_pattern, __version__
        ), f"Version should follow semver format: {__version__}"

    def test_core_imports(self) -> None:
        """Test that core classes can be imported.

        Verifies LLMWrapper, LLMPipeline, NeuroCognitiveEngine,
        and NeuroCognitiveClient are importable.
        """
        from mlsdm import (
            LLMPipeline,
            LLMWrapper,
            NeuroCognitiveClient,
            NeuroCognitiveEngine,
        )

        assert LLMWrapper is not None
        assert LLMPipeline is not None
        assert NeuroCognitiveEngine is not None
        assert NeuroCognitiveClient is not None

    def test_factory_functions(self) -> None:
        """Test that factory functions can be imported.

        Verifies all factory functions are callable.
        """
        from mlsdm import (
            build_neuro_engine_from_env,
            create_llm_pipeline,
            create_llm_wrapper,
            create_neuro_engine,
        )

        assert callable(create_llm_wrapper)
        assert callable(create_neuro_engine)
        assert callable(create_llm_pipeline)
        assert callable(build_neuro_engine_from_env)

    def test_create_llm_wrapper_smoke(self) -> None:
        """Test that LLMWrapper can be created with defaults.

        Verifies factory function returns a non-None instance.
        """
        from mlsdm import create_llm_wrapper

        wrapper = create_llm_wrapper()
        assert wrapper is not None

    def test_llm_wrapper_generate(self) -> None:
        """Test that LLMWrapper can generate a response.

        Verifies generate returns expected response structure.
        """
        from mlsdm import create_llm_wrapper

        wrapper = create_llm_wrapper()
        result = wrapper.generate(prompt="Hello", moral_value=0.8)

        assert isinstance(result, dict)
        assert "response" in result
        assert "accepted" in result
        assert "phase" in result
        assert result["accepted"] is True  # 0.8 > 0.5 default threshold

    def test_llm_wrapper_state(self) -> None:
        """Test that LLMWrapper state can be retrieved.

        Verifies get_state returns expected fields.
        """
        from mlsdm import create_llm_wrapper

        wrapper = create_llm_wrapper()
        state = wrapper.get_state()

        assert isinstance(state, dict)
        assert "phase" in state
        assert "step" in state
        assert "moral_threshold" in state

    def test_create_neuro_engine_smoke(self) -> None:
        """Test that NeuroCognitiveEngine can be created.

        Verifies factory function returns a non-None instance.
        """
        from mlsdm import create_neuro_engine

        engine = create_neuro_engine()
        assert engine is not None

    def test_neuro_engine_generate(self) -> None:
        """Test that NeuroCognitiveEngine can generate a response.

        Verifies generate returns expected response structure.
        """
        from mlsdm import create_neuro_engine

        engine = create_neuro_engine()
        result = engine.generate(prompt="Test", moral_value=0.8)

        assert isinstance(result, dict)
        assert "response" in result

    def test_create_llm_pipeline_smoke(self) -> None:
        """Test that LLMPipeline can be created.

        Verifies factory function returns a non-None instance.
        """
        from mlsdm import create_llm_pipeline

        pipeline = create_llm_pipeline()
        assert pipeline is not None

    def test_neuro_cognitive_client_smoke(self) -> None:
        """Test that NeuroCognitiveClient can be created.

        Verifies client can be instantiated with local_stub backend.
        """
        from mlsdm import NeuroCognitiveClient

        client = NeuroCognitiveClient(backend="local_stub")
        assert client is not None

    def test_client_generate(self) -> None:
        """Test that NeuroCognitiveClient can generate a response.

        Verifies generate returns expected response structure.
        """
        from mlsdm import NeuroCognitiveClient

        client = NeuroCognitiveClient(backend="local_stub")
        result = client.generate(prompt="Hello", moral_value=0.8)

        assert isinstance(result, dict)
        assert "response" in result


class TestCLISmoke:
    """Smoke tests for CLI."""

    def test_cli_import(self) -> None:
        """Test that CLI can be imported.

        Verifies main function is callable.
        """
        from mlsdm.cli import main

        assert callable(main)

    def test_cli_info_command(self) -> None:
        """Test that info command works.

        Verifies cmd_info returns success exit code.
        """
        import argparse

        from mlsdm.cli import cmd_info

        args = argparse.Namespace()
        result = cmd_info(args)
        assert result == 0

    def test_cli_check_command(self) -> None:
        """Test that check command works.

        Verifies cmd_check returns success exit code.
        """
        import argparse

        from mlsdm.cli import cmd_check

        args = argparse.Namespace(verbose=False)
        result = cmd_check(args)
        assert result == 0


class TestAPISmoke:
    """Smoke tests for API components."""

    def test_api_app_import(self) -> None:
        """Test that API app can be imported.

        Verifies FastAPI app instance is available.
        """
        from mlsdm.api.app import app

        assert app is not None

    def test_api_health_router_import(self) -> None:
        """Test that health router can be imported.

        Verifies health router is available.
        """
        from mlsdm.api.health import router

        assert router is not None

    def test_fastapi_app_has_routes(self) -> None:
        """Test that FastAPI app has expected routes.

        Verifies /health, /generate, and /infer routes exist.
        """
        from mlsdm.api.app import app

        routes = [r.path for r in app.routes]
        assert "/health" in routes or any("/health" in r for r in routes)
        assert "/generate" in routes
        assert "/infer" in routes


class TestObservabilitySmoke:
    """Smoke tests for observability components."""

    def test_metrics_exporter_import(self) -> None:
        """Test that metrics exporter can be imported.

        Verifies get_metrics_exporter returns a non-None instance.
        """
        from mlsdm.observability.metrics import get_metrics_exporter

        exporter = get_metrics_exporter()
        assert exporter is not None

    def test_metrics_text_output(self) -> None:
        """Test that metrics can be exported as text.

        Verifies get_metrics_text returns a string.
        """
        from mlsdm.observability.metrics import get_metrics_exporter

        exporter = get_metrics_exporter()
        text = exporter.get_metrics_text()
        assert isinstance(text, str)


def test_packaged_default_config_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure packaged default_config.yaml loads when cwd lacks config/."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CONFIG_PATH", raising=False)

    from mlsdm.utils.config_loader import ConfigLoader

    config = ConfigLoader.load_config("config/default_config.yaml")

    assert isinstance(config, dict)
    assert config.get("dimension") == 10
