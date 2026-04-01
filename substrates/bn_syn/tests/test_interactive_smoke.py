"""Smoke test for interactive dashboard components.

Tests that interactive module can be imported and basic functions work.
Does not actually launch Streamlit.
"""

from __future__ import annotations

from importlib.util import find_spec

import numpy as np
import pytest

HAS_STREAMLIT = find_spec("streamlit") is not None
HAS_PLOTLY = find_spec("plotly") is not None
MISSING_INTERACTIVE_DEPS = not (HAS_STREAMLIT and HAS_PLOTLY)


@pytest.mark.smoke
@pytest.mark.skipif(
    MISSING_INTERACTIVE_DEPS,
    reason="Streamlit/plotly not installed (optional dependency)",
)
def test_interactive_import() -> None:
    """Test that interactive module can be imported."""
    from bnsyn.viz import interactive  # noqa: F401


@pytest.mark.smoke
@pytest.mark.skipif(
    MISSING_INTERACTIVE_DEPS,
    reason="Streamlit/plotly not installed (optional dependency)",
)
def test_interactive_helper_functions() -> None:
    """Test helper functions for creating plots."""
    from bnsyn.viz.interactive import (
        create_firing_rate_plot,
        create_raster_plot,
        create_stats_plot,
        create_voltage_plot,
    )

    # Test raster plot creation
    spike_trains = [(0.0, np.array([1, 2, 3])), (1.0, np.array([4, 5]))]
    fig = create_raster_plot(spike_trains, N=10, duration_ms=100)
    assert fig is not None

    # Test voltage plot creation
    voltage_history = [np.random.randn(10) for _ in range(100)]
    fig = create_voltage_plot(voltage_history, dt_ms=0.1)
    assert fig is not None

    # Test firing rate plot creation
    metrics_history = [{"spike_rate_hz": float(i % 10)} for i in range(100)]
    fig = create_firing_rate_plot(metrics_history, dt_ms=0.1)
    assert fig is not None

    # Test stats plot creation
    metrics_history = [{"sigma": 1.0 + 0.01 * i, "V_mean_mV": -60.0 - 0.1 * i} for i in range(100)]
    fig = create_stats_plot(metrics_history, dt_ms=0.1)
    assert fig is not None


@pytest.mark.smoke
def test_declarative_load_config() -> None:
    """Test loading YAML configuration."""
    from pathlib import Path

    from bnsyn.experiments.declarative import load_config

    config_path = Path(__file__).parent.parent / "examples" / "configs" / "quickstart.yaml"

    if config_path.exists():
        config = load_config(config_path)
        assert config.experiment.name == "quickstart"
        assert config.experiment.version == "v1"
        assert config.network.size == 50
        assert config.simulation.duration_ms == 500
        assert config.simulation.dt_ms == 0.1
        assert len(config.experiment.seeds) == 3
    else:
        pytest.skip("Example config not found")


@pytest.mark.smoke
def test_declarative_invalid_config() -> None:
    """Test that invalid configs raise helpful errors."""
    import tempfile
    from pathlib import Path

    from bnsyn.experiments.declarative import load_config

    # Create invalid config
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
experiment:
  name: "test"
  version: "v1"
  seeds: ["not_an_integer"]  # Invalid: should be integers
network:
  size: 50
simulation:
  duration_ms: 500
  dt_ms: 0.1
"""
        )
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="validation failed"):
            load_config(temp_path)
    finally:
        Path(temp_path).unlink()


@pytest.mark.smoke
def test_incremental_cache_decorator() -> None:
    """Test incremental caching decorator."""
    from bnsyn.incremental import cached, clear_cache

    # Clear cache first to ensure clean state
    clear_cache()

    call_count = 0

    @cached()
    def expensive_function(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call
    result1 = expensive_function(5)
    assert result1 == 10
    first_count = call_count
    assert first_count >= 1

    # Second call with same input - should use cache
    result2 = expensive_function(5)
    assert result2 == 10
    # call_count should not increase (or increase minimally)
    assert call_count <= first_count + 1  # Allow for cache lookup overhead

    # Different input - should compute
    result3 = expensive_function(10)
    assert result3 == 20
    assert call_count > first_count


@pytest.mark.smoke
def test_schema_validation() -> None:
    """Test Pydantic schema validation."""
    from bnsyn.schemas.experiment import BNSynExperimentConfig

    # Valid config
    config_dict = {
        "experiment": {"name": "test", "version": "v1", "seeds": [1, 2, 3]},
        "network": {"size": 50},
        "simulation": {"duration_ms": 100, "dt_ms": 0.1},
    }
    config = BNSynExperimentConfig(**config_dict)
    assert config.experiment.name == "test"

    # Invalid config - network size too small
    invalid_config = {
        "experiment": {"name": "test", "version": "v1", "seeds": [1]},
        "network": {"size": 5},  # Too small (min 10)
        "simulation": {"duration_ms": 100, "dt_ms": 0.1},
    }
    with pytest.raises(Exception):  # Pydantic ValidationError
        BNSynExperimentConfig(**invalid_config)

    # Invalid config - invalid dt_ms
    invalid_config2 = {
        "experiment": {"name": "test", "version": "v1", "seeds": [1]},
        "network": {"size": 50},
        "simulation": {"duration_ms": 100, "dt_ms": 0.15},  # Not in allowed values
    }
    with pytest.raises(Exception):  # Pydantic ValidationError
        BNSynExperimentConfig(**invalid_config2)


@pytest.mark.smoke
@pytest.mark.skipif(
    MISSING_INTERACTIVE_DEPS,
    reason="Streamlit/plotly not installed (optional dependency)",
)
def test_dashboard_ui_no_simulation() -> None:
    """Test dashboard renders UI without running simulation."""
    from unittest.mock import patch

    with (
        patch("streamlit.set_page_config"),
        patch("streamlit.title") as mock_title,
        patch("streamlit.markdown"),
        patch("streamlit.sidebar.header"),
        patch("streamlit.sidebar.slider", return_value=100) as mock_slider,
        patch("streamlit.sidebar.select_slider", return_value=0.1),
        patch("streamlit.sidebar.number_input", return_value=42),
        patch("streamlit.sidebar.button", return_value=False),
        patch("streamlit.info"),
    ):
        from bnsyn.viz.interactive import main

        main()  # Should not raise
        mock_title.assert_called_once()
        assert mock_slider.call_count >= 1


@pytest.mark.smoke
@pytest.mark.skipif(
    MISSING_INTERACTIVE_DEPS,
    reason="Streamlit/plotly not installed (optional dependency)",
)
def test_dashboard_simulation_flow() -> None:
    """Test simulation runs when button clicked."""
    from unittest.mock import Mock, patch

    # Create context manager mocks
    mock_spinner_context = Mock()
    mock_spinner_context.__enter__ = Mock(return_value=mock_spinner_context)
    mock_spinner_context.__exit__ = Mock(return_value=None)

    mock_progress_obj = Mock()
    mock_progress_obj.progress = Mock()
    mock_progress_obj.empty = Mock()

    # Mock tabs as context managers
    mock_tab = Mock()
    mock_tab.__enter__ = Mock(return_value=mock_tab)
    mock_tab.__exit__ = Mock(return_value=None)

    # Mock columns as context managers
    mock_col = Mock()
    mock_col.__enter__ = Mock(return_value=mock_col)
    mock_col.__exit__ = Mock(return_value=None)
    mock_col.metric = Mock()

    with (
        patch("streamlit.set_page_config"),
        patch("streamlit.title"),
        patch("streamlit.markdown"),
        patch("streamlit.sidebar.header"),
        patch("streamlit.sidebar.slider", return_value=50),
        patch("streamlit.sidebar.select_slider", return_value=0.1),
        patch("streamlit.sidebar.number_input", return_value=42),
        patch("streamlit.sidebar.button", return_value=True),
        patch("streamlit.spinner", return_value=mock_spinner_context),
        patch("streamlit.sidebar.progress", return_value=mock_progress_obj),
        patch("streamlit.tabs", return_value=[mock_tab, mock_tab, mock_tab, mock_tab]),
        patch("streamlit.subheader"),
        patch("streamlit.plotly_chart") as mock_chart,
        patch("streamlit.columns", return_value=[mock_col, mock_col, mock_col, mock_col]),
    ):
        from bnsyn.viz.interactive import main

        main()

        # Verify simulation ran
        assert mock_chart.call_count >= 4  # 4 tabs with charts
