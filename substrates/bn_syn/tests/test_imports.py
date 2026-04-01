from __future__ import annotations

import importlib


def test_public_imports() -> None:
    modules = [
        "bnsyn",
        "bnsyn.cli",
        "bnsyn.config",
        "bnsyn.rng",
        "bnsyn.sim.network",
        "bnsyn.neuron.adex",
        "bnsyn.synapse.conductance",
        "bnsyn.plasticity.three_factor",
        "bnsyn.criticality.branching",
        "bnsyn.temperature.schedule",
        "bnsyn.connectivity.sparse",
    ]

    for module in modules:
        importlib.import_module(module)


def test_network_module_exports() -> None:
    """Test that network module has proper __all__ and constants defined."""
    from bnsyn.sim import network

    # Test __all__ exists and contains expected exports
    assert hasattr(network, "__all__")
    assert "Network" in network.__all__
    assert "NetworkParams" in network.__all__
    assert "run_simulation" in network.__all__

    # Test physics constants are defined and have correct values
    assert hasattr(network, "AMPA_FRACTION")
    assert network.AMPA_FRACTION == 0.7

    assert hasattr(network, "NMDA_FRACTION")
    assert network.NMDA_FRACTION == 0.3

    assert hasattr(network, "GAIN_CURRENT_SCALE_PA")
    assert network.GAIN_CURRENT_SCALE_PA == 50.0

    assert hasattr(network, "INITIAL_V_STD_MV")
    assert network.INITIAL_V_STD_MV == 5.0

    # Verify fractions sum to 1.0 (AMPA + NMDA = 100% of excitatory current)
    assert network.AMPA_FRACTION + network.NMDA_FRACTION == 1.0
