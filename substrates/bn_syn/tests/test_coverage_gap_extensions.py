from __future__ import annotations

import builtins
import importlib.util
import runpy
import sys
import types
from collections import deque
from pathlib import Path

import numpy as np
import pytest

from bnsyn.calibration.accuracy_speed import calibrate_integrator_accuracy_speed
from bnsyn.config import (
    AdExParams,
    CriticalityParams,
    DualWeightParams,
    SynapseParams,
    TemperatureParams,
)
from bnsyn.consolidation.dual_weight import DualWeights
from bnsyn.criticality.phase_transition import PhaseTransitionDetector
from bnsyn.emergence.crystallizer import (
    Attractor,
    AttractorCrystallizer,
    Phase,
)
from bnsyn.memory.consolidator import MemoryConsolidator
from bnsyn.memory.ledger import ConsolidationLedger
from bnsyn.neuron.adex import AdExState, adex_step, adex_step_adaptive
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams
from bnsyn.sleep.cycle import MemorySnapshot, SleepCycle, SleepStage, SleepStageConfig
from bnsyn.temperature.schedule import TemperatureSchedule
from bnsyn.viz import interactive as viz_interactive


class _DummyTensor:
    def __init__(self, array: np.ndarray):
        self._array = np.asarray(array, dtype=float)

    def cpu(self) -> "_DummyTensor":
        return self

    def numpy(self) -> np.ndarray:
        return np.asarray(self._array, dtype=float)


class _DummyTorch(types.SimpleNamespace):
    float64 = np.float64

    @staticmethod
    def device(name: str) -> str:
        return f"device:{name}"

    @staticmethod
    def as_tensor(
        data: np.ndarray, dtype: object | None = None, device: object | None = None
    ) -> _DummyTensor:
        return _DummyTensor(np.asarray(data, dtype=float))

    @staticmethod
    def matmul(left: _DummyTensor, right: _DummyTensor) -> _DummyTensor:
        return _DummyTensor(left.numpy() @ right.numpy())


class _WeirdHistory:
    def __init__(self, items: list[tuple[int, float]]):
        self._items = items

    def __len__(self) -> int:
        return 2

    def __iter__(self):
        return iter(self._items)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"dt_ms": 0.0},
        {"steps": 0},
        {"tau_ms": 0.0},
        {"state_size": 0},
        {"integrators": ["unknown"]},
    ],
)
def test_calibration_accuracy_speed_validation_errors(kwargs: dict[str, object]) -> None:
    base = dict(dt_ms=0.1, steps=10, tau_ms=10.0, state_size=4)
    base.update(kwargs)
    with pytest.raises(ValueError):
        calibrate_integrator_accuracy_speed(**base)


def test_dual_weight_step_validation_errors() -> None:
    weights = DualWeights.init((2, 2))
    params = DualWeightParams()
    with pytest.raises(ValueError):
        weights.step(0.0, params, fast_update=np.zeros((2, 2)))
    with pytest.raises(ValueError):
        weights.step(0.1, params, fast_update=np.zeros((3, 2)))


def test_phase_transition_sigma_derivative_edges() -> None:
    detector = PhaseTransitionDetector()
    detector._sigma_history = _WeirdHistory([(1, 0.9)])  # type: ignore[assignment]
    assert detector.sigma_derivative() is None

    detector._sigma_history = deque([(5, 0.9), (5, 1.1)], maxlen=2)
    assert detector.sigma_derivative() == 0.0


def test_crystallizer_edges_and_callbacks() -> None:
    crystallizer = AttractorCrystallizer(
        state_dim=2,
        max_buffer_size=3,
        snapshot_dim=2,
        pca_update_interval=2,
        cluster_eps=0.01,
        cluster_min_samples=2,
    )
    crystallizer._buffer[:1] = np.array([[1.0, 1.0]])
    crystallizer._buffer_idx = 1
    crystallizer._buffer_filled = False
    crystallizer._update_pca()

    assert crystallizer._dbscan_lite(np.array([[0.0, 0.0]])) == []

    crystallizer._buffer_idx = 1
    crystallizer._buffer_filled = False
    assert crystallizer._detect_attractors() == []

    crystallizer._buffer[:2] = np.array([[0.0, 0.0], [10.0, 10.0]])
    crystallizer._buffer_idx = 2
    crystallizer._buffer_filled = False
    assert crystallizer._detect_attractors() == []

    phase_transitions: list[tuple[Phase, Phase]] = []
    crystallizer.on_phase_transition(lambda old, new: phase_transitions.append((old, new)))
    crystallizer._attractors = [
        Attractor(
            center=np.array([0.0, 0.0]),
            basin_radius=1.0,
            stability=0.2,
            formation_step=0,
            crystallization=0.2,
        ),
        Attractor(
            center=np.array([0.0, 0.0]),
            basin_radius=1.0,
            stability=0.5,
            formation_step=0,
            crystallization=0.5,
        ),
        Attractor(
            center=np.array([0.0, 0.0]),
            basin_radius=1.0,
            stability=0.7,
            formation_step=0,
            crystallization=0.7,
        ),
        Attractor(
            center=np.array([0.0, 0.0]),
            basin_radius=1.0,
            stability=0.9,
            formation_step=0,
            crystallization=0.9,
        ),
    ]
    crystallizer._current_phase = Phase.GROWTH
    crystallizer._update_phase()
    assert crystallizer._current_phase == Phase.CRYSTALLIZED
    assert phase_transitions

    with pytest.raises(ValueError):
        crystallizer.observe(np.array([0.0, 0.0]), temperature=-1.0)

    callback_hits: list[Attractor] = []
    crystallizer = AttractorCrystallizer(
        state_dim=2,
        max_buffer_size=4,
        snapshot_dim=2,
        pca_update_interval=1,
        cluster_eps=0.5,
        cluster_min_samples=2,
    )
    crystallizer.on_attractor_formed(callback_hits.append)
    crystallizer.observe(np.array([1.0, 1.0]), temperature=0.5)
    crystallizer.observe(np.array([1.0, 1.0]), temperature=0.5)
    assert len(callback_hits) == 1


def test_consolidation_ledger_validation_and_state() -> None:
    ledger = ConsolidationLedger()
    with pytest.raises(ValueError):
        ledger.record_event(step=0, timestamp=0.0, gate=-0.1, temperature=0.0)
    with pytest.raises(ValueError):
        ledger.record_event(step=0, timestamp=0.0, gate=0.5, temperature=-1.0)
    with pytest.raises(ValueError):
        ledger.record_event(step=-1, timestamp=0.0, gate=0.5, temperature=0.0)
    with pytest.raises(ValueError):
        ledger.record_event(step=0, timestamp=0.0, gate=0.5, temperature=0.0, dw_protein=1.5)

    ledger.record_event(step=1, timestamp=0.1, gate=0.5, temperature=0.0)
    state = ledger.get_state()
    assert state["event_count"] == 1
    assert state["hash"] == ledger.compute_hash()


def test_memory_consolidator_eviction_and_validation() -> None:
    consolidator = MemoryConsolidator(capacity=1)
    consolidator.tag(np.array([1.0, 0.0]), importance=0.5)
    consolidator._consolidated_flags[0] = True
    assert consolidator._find_eviction_candidate() == 0

    with pytest.raises(ValueError):
        consolidator.consolidate(protein_level=1.5, temperature=0.0)
    with pytest.raises(ValueError):
        consolidator.consolidate(protein_level=0.5, temperature=-1.0)


def test_adex_validation_and_spike_reset() -> None:
    params = AdExParams()
    state = AdExState(
        V_mV=np.array([params.EL_mV], dtype=float),
        w_pA=np.array([0.0], dtype=float),
        spiked=np.array([False]),
    )
    with pytest.raises(ValueError):
        adex_step(state, params, dt_ms=0.1, I_syn_pA=np.array([np.nan]), I_ext_pA=np.array([0.0]))

    with pytest.raises(ValueError):
        adex_step_adaptive(
            state, params, dt_ms=0.0, I_syn_pA=np.array([0.0]), I_ext_pA=np.array([0.0])
        )

    spike_state = AdExState(
        V_mV=np.array([params.Vpeak_mV + 5.0], dtype=float),
        w_pA=np.array([0.0], dtype=float),
        spiked=np.array([False]),
    )
    updated = adex_step_adaptive(
        spike_state,
        params,
        dt_ms=0.1,
        I_syn_pA=np.array([0.0]),
        I_ext_pA=np.array([0.0]),
    )
    assert updated.spiked[0]
    assert updated.V_mV[0] == params.Vreset_mV


def test_manifest_fallback_import_path(monkeypatch: pytest.MonkeyPatch) -> None:
    import bnsyn.provenance.manifest as manifest

    dummy_importlib_metadata = types.ModuleType("importlib_metadata")
    dummy_importlib_metadata.distributions = lambda: []
    monkeypatch.setitem(sys.modules, "importlib_metadata", dummy_importlib_metadata)

    real_import = builtins.__import__

    def fake_import(name: str, globals=None, locals=None, fromlist=(), level=0):
        if name == "importlib.metadata":
            raise ImportError("forced")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    module_name = "bnsyn.provenance.manifest_fallback"
    spec = importlib.util.spec_from_file_location(module_name, Path(manifest.__file__))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    assert module.distributions() == []


def test_network_module_import_with_torch_available(monkeypatch: pytest.MonkeyPatch) -> None:
    import bnsyn.sim.network as network

    dummy_torch = _DummyTorch()
    monkeypatch.setitem(sys.modules, "torch", dummy_torch)
    module_name = "bnsyn.sim.network_torch"
    spec = importlib.util.spec_from_file_location(module_name, Path(network.__file__))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    assert module.torch is dummy_torch


def test_network_torch_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    import bnsyn.sim.network as network

    dummy_torch = _DummyTorch()
    monkeypatch.setattr(network, "torch", dummy_torch)
    monkeypatch.setenv("BNSYN_USE_TORCH", "1")

    rng = np.random.default_rng(0)
    net = Network(
        NetworkParams(N=4), AdExParams(), SynapseParams(), CriticalityParams(), dt_ms=0.1, rng=rng
    )
    assert net._use_torch

    net.step()
    net.step_adaptive()

    monkeypatch.setattr(network, "torch", None)
    net._use_torch = True
    with pytest.raises(RuntimeError):
        net.step()
    with pytest.raises(RuntimeError):
        net.step_adaptive()


def _make_sleep_cycle(seed: int = 1, n: int = 4) -> SleepCycle:
    pack = seed_all(seed)
    net = Network(
        NetworkParams(N=n),
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.1,
        rng=pack.np_rng,
    )
    schedule = TemperatureSchedule(TemperatureParams())
    return SleepCycle(net, schedule, max_memories=5)


def test_sleep_cycle_validation_and_callbacks() -> None:
    with pytest.raises(ValueError):
        _ = SleepCycle(
            Network(
                NetworkParams(N=4),
                AdExParams(),
                SynapseParams(),
                CriticalityParams(),
                dt_ms=0.1,
                rng=np.random.default_rng(0),
            ),
            TemperatureSchedule(TemperatureParams()),
            max_memories=0,
        )

    cycle = _make_sleep_cycle()
    big_voltage = np.arange(600, dtype=float)
    subsampled = cycle._subsample_voltage(big_voltage)
    assert subsampled.shape[0] == 500

    with pytest.raises(ValueError):
        cycle.record_memory(importance=1.5)

    with pytest.raises(ValueError):
        cycle.wake(duration_steps=0)
    with pytest.raises(ValueError, match=r"record_interval.*0"):
        cycle.wake(duration_steps=1, record_interval=0)
    with pytest.raises(ValueError, match=r"record_interval.*-1"):
        cycle.wake(duration_steps=1, record_interval=-1)

    stage_calls: list[tuple[SleepStage, SleepStage]] = []

    def record_stage(old: SleepStage, new: SleepStage) -> None:
        stage_calls.append((old, new))

    cycle.on_stage_change(record_stage)
    cycle.current_stage = SleepStage.DEEP_SLEEP

    task_called = {"count": 0}

    def task() -> dict[str, float]:
        task_called["count"] += 1
        return {"sigma": 1.0, "spike_rate_hz": 0.0}

    cycle.wake(duration_steps=1, task=task, record_memories=False)
    assert task_called["count"] == 1
    assert stage_calls


def test_sleep_cycle_sleep_and_dream_paths() -> None:
    cycle = _make_sleep_cycle()

    with pytest.raises(ValueError):
        cycle.sleep([])

    cycle_calls: list[bool] = []
    cycle.on_cycle_complete(lambda: cycle_calls.append(True))

    stage = SleepStageConfig(
        stage=SleepStage.LIGHT_SLEEP,
        duration_steps=1,
        temperature_range=(0.8, 1.0),
        replay_active=False,
        replay_noise=0.0,
    )
    cycle.sleep([stage])
    assert cycle_calls

    with pytest.raises(ValueError):
        cycle.dream(memories=[], noise_level=-0.1, duration_steps=1)
    with pytest.raises(ValueError):
        cycle.dream(memories=[], noise_level=0.5, duration_steps=0)

    assert cycle.dream(memories=[], noise_level=0.0, duration_steps=1) == []

    memory = MemorySnapshot(voltage_mV=np.array([cycle.network.adex.EL_mV]), importance=1.0, step=0)
    cycle.dream(memories=[memory], noise_level=0.0, duration_steps=1)

    cycle.memories.append(memory)
    cycle.clear_memories()
    assert cycle.get_memory_count() == 0


def test_viz_interactive_optional_dependency_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(viz_interactive, "HAVE_STREAMLIT", False)
    monkeypatch.setattr(viz_interactive, "_IMPORT_ERROR", ImportError("missing"))

    with pytest.raises(RuntimeError):
        viz_interactive.main()

    with pytest.raises(RuntimeError):
        viz_interactive.create_voltage_plot([np.zeros((2,))], dt_ms=0.1)

    with pytest.raises(RuntimeError):
        viz_interactive.create_firing_rate_plot([{"spike_rate_hz": 1.0}], dt_ms=0.1)

    with pytest.raises(RuntimeError):
        viz_interactive.create_stats_plot([{"sigma": 1.0, "V_mean_mV": -60.0}], dt_ms=0.1)

    real_import = builtins.__import__

    def fake_import(name: str, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("streamlit") or name.startswith("plotly"):
            raise ImportError("forced")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError):
        runpy.run_module("bnsyn.viz.interactive", run_name="__main__")
