"""Validation tests for visualization dashboard.

Notes
-----
Tests marked with @pytest.mark.validation to ensure optional viz
functionality works correctly without requiring display.

References
----------
docs/features/viz_dashboard.md
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams
from bnsyn.consolidation import DualWeights
from bnsyn.emergence import AttractorCrystallizer
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams
from bnsyn.sleep import SleepCycle
from bnsyn.viz import EmergenceDashboard


@pytest.mark.validation
def test_dashboard_creation() -> None:
    """Test basic dashboard creation and initialization."""
    dashboard = EmergenceDashboard(figsize=(12, 8))

    # Should not import matplotlib yet
    assert dashboard._fig is None
    assert len(dashboard._axes) == 0
    assert dashboard._step_count == 0


@pytest.mark.validation
def test_dashboard_attach_and_update() -> None:
    """Test attaching components and updating with metrics."""
    seed = 42
    pack = seed_all(seed)

    # Create minimal components
    nparams = NetworkParams(N=50)
    network = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.5,
        rng=pack.np_rng,
    )

    crystallizer = AttractorCrystallizer(
        state_dim=50,
        max_buffer_size=100,
        snapshot_dim=20,
        pca_update_interval=20,
    )

    # Create temperature schedule and sleep cycle
    from bnsyn.config import TemperatureParams
    from bnsyn.temperature.schedule import TemperatureSchedule

    temp_params = TemperatureParams(T0=1.0, Tmin=0.5, decay_rate=0.99)
    temp_schedule = TemperatureSchedule(params=temp_params)

    sleep_cycle = SleepCycle(
        network=network,
        temperature_schedule=temp_schedule,
        max_memories=100,
        rng=pack.np_rng,
    )

    consolidator = DualWeights.init(shape=(50, 50), w0=0.0)

    # Create dashboard and attach
    dashboard = EmergenceDashboard()
    dashboard.attach(network, crystallizer, sleep_cycle, consolidator)

    assert dashboard._network is network
    assert dashboard._crystallizer is crystallizer
    assert dashboard._sleep_cycle is sleep_cycle
    assert dashboard._consolidator is consolidator

    # Update with sample metrics
    for i in range(10):
        metrics = {
            "sigma": 0.95 + 0.05 * np.random.rand(),
            "temperature": 1.0 + 0.1 * np.random.rand(),
            "sleep_stage": "WAKE",
            "consolidation": 0.5 + 0.1 * np.random.rand(),
            "avalanche_size": np.random.randint(1, 20),
            "attractor_point": np.random.randn(20),
        }
        dashboard.update(metrics)

    assert dashboard._step_count == 10
    assert len(dashboard._sigma_history) == 10
    assert len(dashboard._temp_history) == 10
    assert len(dashboard._stage_history) == 10
    assert len(dashboard._consol_history) == 10
    assert len(dashboard._avalanche_sizes) > 0
    assert len(dashboard._attractor_points) == 10


@pytest.mark.validation
def test_dashboard_save_png() -> None:
    """Test saving dashboard as PNG image."""
    pytest.importorskip("matplotlib")

    dashboard = EmergenceDashboard()

    # Add some sample data
    for i in range(20):
        metrics = {
            "sigma": 1.0 + 0.1 * np.sin(i * 0.5),
            "temperature": 1.0 + 0.2 * np.cos(i * 0.3),
            "sleep_stage": "WAKE" if i < 10 else "NREM2",
            "consolidation": 0.5 + 0.2 * (i / 20.0),
            "avalanche_size": max(1, int(10 * np.random.rand())),
            "attractor_point": np.random.randn(20),
        }
        dashboard.update(metrics)

    # Save to temporary file
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "dashboard_test.png"
        dashboard.save_animation(str(output_file))

        assert output_file.exists()
        assert output_file.stat().st_size > 0


@pytest.mark.validation
def test_dashboard_empty_data() -> None:
    """Test dashboard handles empty data gracefully."""
    pytest.importorskip("matplotlib")

    dashboard = EmergenceDashboard()

    # Try to save with no data
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "empty_dashboard.png"
        dashboard.save_animation(str(output_file))

        # Should create file even with empty data
        assert output_file.exists()


@pytest.mark.validation
def test_dashboard_partial_metrics() -> None:
    """Test dashboard with partial metrics (not all keys present)."""
    dashboard = EmergenceDashboard()

    # Update with only some metrics
    dashboard.update({"sigma": 1.0})
    assert len(dashboard._sigma_history) == 1
    assert len(dashboard._temp_history) == 0

    dashboard.update({"temperature": 1.5, "sleep_stage": "NREM3"})
    assert len(dashboard._sigma_history) == 1
    assert len(dashboard._temp_history) == 1
    assert len(dashboard._stage_history) == 1

    assert dashboard._step_count == 2
