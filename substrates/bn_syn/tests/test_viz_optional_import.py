"""Test that visualization module is optional and handles missing matplotlib gracefully."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_viz_module_imports_without_matplotlib() -> None:
    """Test that bnsyn.viz can be imported even if matplotlib is not installed.

    Notes
    -----
    This test ensures that importing the viz module does not require matplotlib
    to be installed. The module should only attempt to load matplotlib when
    visualization methods are actually called.
    """
    # This test verifies that the module itself can be imported
    # The actual matplotlib import is deferred until visualization methods are called
    import bnsyn.viz

    assert hasattr(bnsyn.viz, "EmergenceDashboard")


def test_interactive_module_imports_without_streamlit() -> None:
    """Test that bnsyn.viz.interactive can be imported even if streamlit/plotly not installed.

    Notes
    -----
    This test ensures that importing the interactive module does not crash
    when optional dependencies are missing. The module should only raise
    an error when main() is actually called.
    """
    import bnsyn.viz.interactive

    # Import should succeed
    assert hasattr(bnsyn.viz.interactive, "main")
    assert hasattr(bnsyn.viz.interactive, "HAVE_STREAMLIT")

    # If streamlit is not installed, calling main should raise RuntimeError
    if not bnsyn.viz.interactive.HAVE_STREAMLIT:
        with pytest.raises(RuntimeError, match=r"optional dependency"):
            bnsyn.viz.interactive.main()


def test_viz_runtime_error_when_matplotlib_missing() -> None:
    """Test that calling viz methods raises informative error when matplotlib is missing.

    Notes
    -----
    When matplotlib is not installed, attempting to use visualization methods
    should raise a RuntimeError with a clear message about how to install the
    optional dependencies.
    """
    from bnsyn.viz.dashboard import EmergenceDashboard

    # Create a mock that raises ModuleNotFoundError when matplotlib.pyplot is imported
    def mock_import_module(name: str) -> MagicMock:
        if name in ["matplotlib.pyplot", "matplotlib.animation", "mpl_toolkits.mplot3d"]:
            raise ModuleNotFoundError(f"No module named '{name}'")
        # For any other module, return a mock
        return MagicMock()

    # Patch importlib.import_module to simulate missing matplotlib
    with patch("bnsyn.viz.dashboard.importlib.import_module", side_effect=mock_import_module):
        # Reset the module cache to force reload attempt
        import bnsyn.viz.dashboard

        bnsyn.viz.dashboard._plt = None
        bnsyn.viz.dashboard._animation = None

        dashboard = EmergenceDashboard()

        # Attempting to show the dashboard should raise RuntimeError with install hint
        with pytest.raises(RuntimeError, match=r".*pip install.*viz.*"):
            dashboard.show()


def test_viz_load_matplotlib_caching() -> None:
    """Test that matplotlib modules are cached after first load.

    Notes
    -----
    The _load_matplotlib function should cache the loaded modules to avoid
    repeated imports. This test verifies the caching behavior.
    """
    from bnsyn.viz.dashboard import _load_matplotlib

    # Reset cache
    import bnsyn.viz.dashboard

    bnsyn.viz.dashboard._plt = None
    bnsyn.viz.dashboard._animation = None

    # Mock successful import
    mock_plt = MagicMock()
    mock_animation = MagicMock()
    mock_mplot3d = MagicMock()

    def mock_import_module(name: str) -> MagicMock:
        if name == "matplotlib.pyplot":
            return mock_plt
        elif name == "matplotlib.animation":
            return mock_animation
        elif name == "mpl_toolkits.mplot3d":
            return mock_mplot3d
        return MagicMock()

    with patch(
        "bnsyn.viz.dashboard.importlib.import_module", side_effect=mock_import_module
    ) as mock_import:
        # First call should import
        plt1, anim1 = _load_matplotlib()
        assert plt1 is mock_plt
        assert anim1 is mock_animation
        first_call_count = mock_import.call_count

        # Second call should use cache
        plt2, anim2 = _load_matplotlib()
        assert plt2 is mock_plt
        assert anim2 is mock_animation
        # Should not have called import_module again
        assert mock_import.call_count == first_call_count


def test_dashboard_creation_without_matplotlib() -> None:
    """Test that EmergenceDashboard can be instantiated without matplotlib.

    Notes
    -----
    Creating a dashboard object should not require matplotlib. Only when
    calling methods that render visualizations should matplotlib be loaded.
    """
    from bnsyn.viz.dashboard import EmergenceDashboard

    # This should succeed without importing matplotlib
    dashboard = EmergenceDashboard(figsize=(10, 8))
    assert dashboard._figsize == (10, 8)
    assert dashboard._fig is None  # Should not be initialized yet


def test_save_animation_requires_matplotlib() -> None:
    """Test that save_animation also raises error when matplotlib is missing.

    Notes
    -----
    The save_animation method should also require matplotlib and raise
    an informative error if it's not available.
    """
    from bnsyn.viz.dashboard import EmergenceDashboard

    # Create a mock that raises ModuleNotFoundError
    def mock_import_module(name: str) -> MagicMock:
        if name in ["matplotlib.pyplot", "matplotlib.animation", "mpl_toolkits.mplot3d"]:
            raise ModuleNotFoundError(f"No module named '{name}'")
        return MagicMock()

    with patch("bnsyn.viz.dashboard.importlib.import_module", side_effect=mock_import_module):
        # Reset the module cache
        import bnsyn.viz.dashboard

        bnsyn.viz.dashboard._plt = None
        bnsyn.viz.dashboard._animation = None

        dashboard = EmergenceDashboard()

        # Attempting to save should raise RuntimeError
        with pytest.raises(RuntimeError, match=r".*pip install.*viz.*"):
            dashboard.save_animation("test.png")
