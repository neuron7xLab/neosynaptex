"""Smoke tests for viz module to ensure high coverage without requiring matplotlib display.

Notes
-----
These tests mock matplotlib to avoid display requirements while ensuring
all rendering code paths are executed and covered.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np


def test_dashboard_attach_and_update() -> None:
    """Test dashboard attach and update methods.

    Notes
    -----
    Tests the attach() and update() methods which store component references
    and accumulate metrics data.
    """
    from bnsyn.viz.dashboard import EmergenceDashboard

    dashboard = EmergenceDashboard(figsize=(10, 8))

    # Create mock components
    mock_network = MagicMock()
    mock_crystallizer = MagicMock()
    mock_sleep_cycle = MagicMock()
    mock_consolidator = MagicMock()

    # Test attach
    dashboard.attach(mock_network, mock_crystallizer, mock_sleep_cycle, mock_consolidator)
    assert dashboard._network is mock_network
    assert dashboard._crystallizer is mock_crystallizer
    assert dashboard._sleep_cycle is mock_sleep_cycle
    assert dashboard._consolidator is mock_consolidator

    # Test update with various metrics (deterministic)
    metrics = {
        "sigma": 1.05,
        "temperature": 1.2,
        "sleep_stage": "NREM2",
        "consolidation": 0.75,
        "avalanche_size": 15,
        "attractor_point": np.linspace(0.0, 1.0, num=10),
    }
    dashboard.update(metrics)

    assert len(dashboard._sigma_history) == 1
    assert len(dashboard._temp_history) == 1
    assert len(dashboard._stage_history) == 1
    assert len(dashboard._consol_history) == 1
    assert len(dashboard._avalanche_sizes) == 1
    assert len(dashboard._attractor_points) == 1


def test_dashboard_full_cycle_mocked() -> None:
    """Test full dashboard lifecycle with mocked matplotlib.

    Notes
    -----
    This test ensures all rendering methods are executed and covered
    without requiring actual matplotlib to be installed or a display.
    """
    from bnsyn.viz.dashboard import EmergenceDashboard

    # Mock matplotlib modules
    mock_plt = MagicMock()
    mock_animation = MagicMock()
    mock_fig = MagicMock()
    mock_ax = MagicMock()

    # Configure mock figure to return mock axes
    mock_fig.add_subplot.return_value = mock_ax

    # Configure mock plt to return mock figure
    mock_plt.figure.return_value = mock_fig

    def mock_import_module(name: str) -> MagicMock:
        if name == "matplotlib.pyplot":
            return mock_plt
        elif name == "matplotlib.animation":
            return mock_animation
        elif name == "mpl_toolkits.mplot3d":
            return MagicMock()
        return MagicMock()

    with patch("bnsyn.viz.dashboard.importlib.import_module", side_effect=mock_import_module):
        # Reset module cache
        import bnsyn.viz.dashboard

        bnsyn.viz.dashboard._plt = None
        bnsyn.viz.dashboard._animation = None

        # Create dashboard
        dashboard = EmergenceDashboard(figsize=(12, 8))

        # Create mock components with get_attractors method (deterministic attractors)
        mock_crystallizer = MagicMock()
        mock_attractor = MagicMock()
        mock_attractor.center = np.linspace(-1.0, 1.0, num=10)
        mock_crystallizer.get_attractors.return_value = [mock_attractor]

        dashboard.attach(MagicMock(), mock_crystallizer, MagicMock(), MagicMock())

        # Add sample data to trigger all rendering paths
        for i in range(50):
            metrics = {
                "sigma": 1.0 + 0.1 * np.sin(i * 0.5),
                "temperature": 1.0 + 0.2 * np.cos(i * 0.3),
                "sleep_stage": ["WAKE", "NREM1", "NREM2", "NREM3", "REM"][i % 5],
                "consolidation": 0.5 + 0.2 * (i / 50.0),
                "avalanche_size": (i % 10) + 1,
                "attractor_point": np.linspace(0.0, 1.0, num=10),
            }
            dashboard.update(metrics)

        # Test show() - should trigger all rendering
        dashboard.show()

        # Verify matplotlib was called
        mock_plt.figure.assert_called_once()
        assert mock_fig.add_subplot.call_count == 6  # 6 panels
        mock_plt.tight_layout.assert_called()
        mock_plt.show.assert_called_once()

        # Verify all axes were created
        assert "attractor" in dashboard._axes
        assert "sigma" in dashboard._axes
        assert "temperature" in dashboard._axes
        assert "sleep" in dashboard._axes
        assert "consolidation" in dashboard._axes
        assert "avalanche" in dashboard._axes


def test_dashboard_save_animation_mocked() -> None:
    """Test save_animation method with mocked matplotlib.

    Notes
    -----
    Tests the save_animation path which should also trigger rendering.
    """
    from bnsyn.viz.dashboard import EmergenceDashboard

    # Mock matplotlib
    mock_plt = MagicMock()
    mock_animation = MagicMock()
    mock_fig = MagicMock()
    mock_ax = MagicMock()

    mock_fig.add_subplot.return_value = mock_ax
    mock_plt.figure.return_value = mock_fig

    mock_figure_cls = MagicMock(return_value=mock_fig)
    mock_canvas_cls = MagicMock()

    mock_backends_agg = MagicMock()
    mock_backends_agg.FigureCanvasAgg = mock_canvas_cls

    mock_figure_mod = MagicMock()
    mock_figure_mod.Figure = mock_figure_cls

    def mock_import_module(name: str) -> MagicMock:
        if name == "matplotlib.pyplot":
            return mock_plt
        elif name == "matplotlib.animation":
            return mock_animation
        elif name == "mpl_toolkits.mplot3d":
            return MagicMock()
        elif name == "matplotlib.backends.backend_agg":
            return mock_backends_agg
        elif name == "matplotlib.figure":
            return mock_figure_mod
        return MagicMock()

    with patch("bnsyn.viz.dashboard.importlib.import_module", side_effect=mock_import_module):
        # Reset module cache
        import bnsyn.viz.dashboard

        bnsyn.viz.dashboard._plt = None
        bnsyn.viz.dashboard._animation = None

        dashboard = EmergenceDashboard()

        # Add some sample data
        for i in range(10):
            dashboard.update(
                {
                    "sigma": 1.0,
                    "temperature": 1.0,
                    "sleep_stage": "WAKE",
                    "consolidation": 0.5,
                }
            )

        # Test save_animation
        dashboard.save_animation("test.png")

        # Verify Figure was constructed and savefig was called
        mock_figure_cls.assert_called_once()
        mock_fig.tight_layout.assert_called()
        mock_fig.savefig.assert_called_once_with("test.png", dpi=150, bbox_inches="tight")


def test_dashboard_rendering_methods_with_data() -> None:
    """Test all individual rendering methods with populated data.

    Notes
    -----
    Exercises all _render_* methods to ensure complete coverage.
    """
    from bnsyn.viz.dashboard import EmergenceDashboard

    # Mock matplotlib
    mock_plt = MagicMock()
    mock_animation = MagicMock()
    mock_fig = MagicMock()
    mock_ax = MagicMock()

    mock_fig.add_subplot.return_value = mock_ax
    mock_plt.figure.return_value = mock_fig

    def mock_import_module(name: str) -> MagicMock:
        if name == "matplotlib.pyplot":
            return mock_plt
        elif name == "matplotlib.animation":
            return mock_animation
        elif name == "mpl_toolkits.mplot3d":
            return MagicMock()
        return MagicMock()

    with patch("bnsyn.viz.dashboard.importlib.import_module", side_effect=mock_import_module):
        # Reset module cache
        import bnsyn.viz.dashboard

        bnsyn.viz.dashboard._plt = None
        bnsyn.viz.dashboard._animation = None

        dashboard = EmergenceDashboard()

        # Mock crystallizer with attractors
        mock_crystallizer = MagicMock()
        mock_attractor1 = MagicMock()
        mock_attractor1.center = np.array([1.0, 2.0, 3.0])
        mock_attractor2 = MagicMock()
        mock_attractor2.center = np.array([4.0, 5.0, 6.0])
        mock_crystallizer.get_attractors.return_value = [
            mock_attractor1,
            mock_attractor2,
        ]

        dashboard.attach(MagicMock(), mock_crystallizer, MagicMock(), MagicMock())

        # Populate with rich data to exercise all rendering paths
        for i in range(100):
            metrics = {
                "sigma": 0.8 + 0.3 * np.sin(i * 0.1),
                "temperature": 0.9 + 0.2 * np.cos(i * 0.15),
                "sleep_stage": ["WAKE", "NREM1", "NREM2", "NREM3", "REM"][i % 5],
                "consolidation": 0.3 + 0.5 * (i / 100.0),
                "avalanche_size": max(1, int(50 * np.exp(-i / 50.0))),
                "attractor_point": np.array([i / 10.0, i / 20.0, i / 30.0]),
            }
            dashboard.update(metrics)

        # Ensure figure is initialized
        dashboard._ensure_figure()

        # Call all rendering methods explicitly
        dashboard._render_attractor()
        dashboard._render_sigma()
        dashboard._render_temperature()
        dashboard._render_sleep()
        dashboard._render_consolidation()
        dashboard._render_avalanche()

        # Verify axes methods were called
        # Each render method calls ax.clear() and various plotting methods
        assert mock_ax.clear.call_count >= 6  # At least once per panel


def test_dashboard_empty_data_rendering() -> None:
    """Test rendering methods with empty/minimal data.

    Notes
    -----
    Ensures rendering methods handle edge cases gracefully.
    """
    from bnsyn.viz.dashboard import EmergenceDashboard

    # Mock matplotlib
    mock_plt = MagicMock()
    mock_animation = MagicMock()
    mock_fig = MagicMock()
    mock_ax = MagicMock()

    mock_fig.add_subplot.return_value = mock_ax
    mock_plt.figure.return_value = mock_fig

    def mock_import_module(name: str) -> MagicMock:
        if name == "matplotlib.pyplot":
            return mock_plt
        elif name == "matplotlib.animation":
            return mock_animation
        elif name == "mpl_toolkits.mplot3d":
            return MagicMock()
        return MagicMock()

    with patch("bnsyn.viz.dashboard.importlib.import_module", side_effect=mock_import_module):
        # Reset module cache
        import bnsyn.viz.dashboard

        bnsyn.viz.dashboard._plt = None
        bnsyn.viz.dashboard._animation = None

        dashboard = EmergenceDashboard()

        # Mock crystallizer with no attractors
        mock_crystallizer = MagicMock()
        mock_crystallizer.get_attractors.return_value = []

        dashboard.attach(MagicMock(), mock_crystallizer, MagicMock(), MagicMock())

        # Don't add any data - test rendering with empty buffers
        dashboard._ensure_figure()

        # Call all rendering methods with empty data
        dashboard._render_attractor()
        dashboard._render_sigma()
        dashboard._render_temperature()
        dashboard._render_sleep()
        dashboard._render_consolidation()
        dashboard._render_avalanche()

        # Verify clear was called for each axis
        assert mock_ax.clear.call_count >= 6


def test_dashboard_ensure_figure_idempotent() -> None:
    """Test that _ensure_figure is idempotent.

    Notes
    -----
    Calling _ensure_figure multiple times should only create figure once.
    """
    from bnsyn.viz.dashboard import EmergenceDashboard

    # Mock matplotlib
    mock_plt = MagicMock()
    mock_animation = MagicMock()
    mock_fig = MagicMock()
    mock_ax = MagicMock()

    mock_fig.add_subplot.return_value = mock_ax
    mock_plt.figure.return_value = mock_fig

    def mock_import_module(name: str) -> MagicMock:
        if name == "matplotlib.pyplot":
            return mock_plt
        elif name == "matplotlib.animation":
            return mock_animation
        elif name == "mpl_toolkits.mplot3d":
            return MagicMock()
        return MagicMock()

    with patch("bnsyn.viz.dashboard.importlib.import_module", side_effect=mock_import_module):
        # Reset module cache
        import bnsyn.viz.dashboard

        bnsyn.viz.dashboard._plt = None
        bnsyn.viz.dashboard._animation = None

        dashboard = EmergenceDashboard()

        # Call _ensure_figure multiple times
        dashboard._ensure_figure()
        dashboard._ensure_figure()
        dashboard._ensure_figure()

        # Should only create figure once
        mock_plt.figure.assert_called_once()
