"""Tests for stable API surface re-exports."""

from __future__ import annotations


def test_control_reexports() -> None:
    import bnsyn.control as control
    from bnsyn.criticality.branching import BranchingEstimator, SigmaController
    from bnsyn.energy.regularization import energy_cost, total_reward
    from bnsyn.temperature.schedule import TemperatureSchedule, gate_sigmoid

    assert control.BranchingEstimator is BranchingEstimator
    assert control.SigmaController is SigmaController
    assert control.TemperatureSchedule is TemperatureSchedule
    assert control.gate_sigmoid is gate_sigmoid
    assert control.energy_cost is energy_cost
    assert control.total_reward is total_reward

    exported = set(control.__all__)
    assert exported == {
        "BranchingEstimator",
        "SigmaController",
        "TemperatureSchedule",
        "gate_sigmoid",
        "energy_cost",
        "total_reward",
    }


def test_neurons_reexports() -> None:
    import bnsyn.neurons as neurons
    from bnsyn.neuron.adex import (
        AdExState,
        IntegrationMetrics,
        adex_step,
        adex_step_adaptive,
        adex_step_with_error_tracking,
    )

    assert neurons.AdExState is AdExState
    assert neurons.IntegrationMetrics is IntegrationMetrics
    assert neurons.adex_step is adex_step
    assert neurons.adex_step_adaptive is adex_step_adaptive
    assert neurons.adex_step_with_error_tracking is adex_step_with_error_tracking

    exported = set(neurons.__all__)
    assert exported == {
        "AdExState",
        "IntegrationMetrics",
        "adex_step",
        "adex_step_adaptive",
        "adex_step_with_error_tracking",
    }


def test_simulation_reexports() -> None:
    import bnsyn.simulation as simulation
    from bnsyn.sim.network import Network, NetworkParams, run_simulation

    assert simulation.Network is Network
    assert simulation.NetworkParams is NetworkParams
    assert simulation.run_simulation is run_simulation

    exported = set(simulation.__all__)
    assert exported == {"Network", "NetworkParams", "run_simulation"}


def test_synapses_reexports() -> None:
    import bnsyn.synapses as synapses
    from bnsyn.synapse.conductance import ConductanceState, ConductanceSynapses, nmda_mg_block

    assert synapses.ConductanceState is ConductanceState
    assert synapses.ConductanceSynapses is ConductanceSynapses
    assert synapses.nmda_mg_block is nmda_mg_block

    exported = set(synapses.__all__)
    assert exported == {"ConductanceState", "ConductanceSynapses", "nmda_mg_block"}
