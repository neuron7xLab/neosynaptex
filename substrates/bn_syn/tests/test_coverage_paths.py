import argparse
import importlib

import numpy as np
import pytest

from bnsyn.cli import _cmd_demo, _cmd_dtcheck, main
from bnsyn.config import AdExParams, PlasticityParams
from bnsyn.criticality.analysis import fit_power_law_mle, mr_branching_ratio
from bnsyn.neuron.adex import AdExState, adex_step_adaptive, adex_step_with_error_tracking
from bnsyn.numerics.integrators import clamp_exp_arg, euler_step, exp_decay_step, rk2_step
from bnsyn.production.adex import AdExNeuron
from bnsyn.production.connectivity import ConnectivityConfig, build_connectivity
from bnsyn.rng import seed_all, split


def test_cli_commands_direct() -> None:
    demo_args = argparse.Namespace(steps=5, dt_ms=0.1, seed=1, N=10)
    assert _cmd_demo(demo_args) == 0

    dt_args = argparse.Namespace(steps=5, dt_ms=0.1, dt2_ms=0.05, seed=2, N=10)
    assert _cmd_dtcheck(dt_args) == 0

    argv = ["bnsyn", "demo", "--steps", "3", "--dt-ms", "0.1", "--seed", "1", "--N", "5"]
    with pytest.raises(SystemExit) as exc:
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr("sys.argv", argv)
            main()
    assert exc.value.code == 0


def test_criticality_analysis_paths() -> None:
    activity = np.array([1, 2, 4, 8, 16, 32], dtype=float)
    sigma = mr_branching_ratio(activity, max_lag=2)
    assert sigma > 0

    with pytest.raises(ValueError):
        mr_branching_ratio(np.array([[1.0, 2.0]]))
    with pytest.raises(ValueError):
        mr_branching_ratio(np.array([1.0, -1.0, 2.0]))
    with pytest.raises(ValueError):
        mr_branching_ratio(np.array([1.0, 2.0]), max_lag=3)

    data = np.array([1.0, 2.0, 4.0, 8.0])
    fit = fit_power_law_mle(data, xmin=1.0)
    assert fit.alpha > 1.0
    with pytest.raises(ValueError):
        fit_power_law_mle(np.array([0.5, 1.0]), xmin=1.0)
    with pytest.raises(ValueError):
        fit_power_law_mle(np.array([1.0, 1.0]), xmin=1.0)


def test_integrators_and_stdp() -> None:
    assert clamp_exp_arg(5.0, max_arg=4.0) == 4.0
    x = np.array([1.0, 2.0])

    def f(arr: np.ndarray) -> np.ndarray:
        return arr * 2.0

    assert np.allclose(euler_step(x, 0.1, f), x + 0.1 * f(x))
    assert np.allclose(rk2_step(x, 0.1, f), x + 0.1 * f(x + 0.05 * f(x)))
    assert np.allclose(exp_decay_step(np.array([1.0]), 0.1, 1.0), np.exp(-0.1))
    with pytest.raises(ValueError):
        exp_decay_step(np.array([1.0]), 0.1, 0.0)

    p = PlasticityParams()
    from bnsyn.plasticity.stdp import stdp_kernel

    assert stdp_kernel(10.0, p) > 0
    assert stdp_kernel(-10.0, p) < 0
    assert stdp_kernel(0.0, p) == 0.0


def test_rng_seed_and_split() -> None:
    pack = seed_all(123)
    assert pack.seed == 123
    with pytest.raises(TypeError):
        seed_all(1.5)
    with pytest.raises(ValueError):
        seed_all(-1)

    children = split(pack.np_rng, 3)
    assert len(children) == 3
    pack_again = seed_all(123)
    children_again = split(pack_again.np_rng, 3)
    assert children[0].normal() == children_again[0].normal()
    with pytest.raises(ValueError):
        split(pack.np_rng, 0)


def test_production_adex_step_paths() -> None:
    neuron = AdExNeuron.init(2)
    spikes, v = neuron.step(np.zeros(2), dt=1e-3, t=0.0)
    assert spikes.shape == (2,)
    assert v.shape == (2,)

    neuron.t_last_spike = np.array([0.0, 0.0])
    spikes, v = neuron.step(np.zeros(2), dt=1e-3, t=1e-4)
    assert np.all(v == neuron.params.V_reset)
    assert spikes.shape == (2,)

    with pytest.raises(ValueError):
        neuron.step(np.zeros(3), dt=1e-3, t=0.0)


def test_production_connectivity_paths() -> None:
    rng = np.random.default_rng(0)
    cfg = ConnectivityConfig(n_pre=3, n_post=3, p_connect=1.0, allow_self=False)
    adj = build_connectivity(cfg, rng=rng)
    assert adj.shape == (3, 3)
    assert not np.any(np.diag(adj))

    cfg_self = ConnectivityConfig(n_pre=3, n_post=3, p_connect=1.0, allow_self=True)
    adj_self = build_connectivity(cfg_self, rng=rng)
    assert np.all(np.diag(adj_self))

    with pytest.raises(ValueError):
        build_connectivity(ConnectivityConfig(n_pre=0, n_post=1, p_connect=0.5), rng=rng)
    with pytest.raises(ValueError):
        build_connectivity(ConnectivityConfig(n_pre=1, n_post=1, p_connect=1.5), rng=rng)


def test_jax_backend_import_error() -> None:
    """Test JAX backend import behavior based on JAX availability.

    Contract:
    - Importing the module never raises if JAX is missing.
    - When JAX is missing, calling JAX-backed functions raises RuntimeError.
    """
    try:
        import jax  # noqa: F401

        jax_available = True
    except ImportError:
        jax_available = False

    module = importlib.import_module("bnsyn.production.jax_backend")
    assert module.JAX_AVAILABLE is jax_available

    if not jax_available:
        with pytest.raises(RuntimeError, match="JAX is required"):
            module.adex_step_jax(
                np.array([-55.0], dtype=float),
                np.array([0.0], dtype=float),
                np.array([0.0], dtype=float),
                C=200.0,
                gL=10.0,
                EL=-65.0,
                VT=-50.0,
                DeltaT=2.0,
                tau_w=100.0,
                a=2.0,
                b=50.0,
                V_reset=-65.0,
                V_spike=-40.0,
                dt=0.1,
            )


def test_adex_error_tracking_and_adaptive() -> None:
    state = AdExState(V_mV=np.array([-65.0]), w_pA=np.array([0.0]), spiked=np.array([False]))
    full, metrics = adex_step_with_error_tracking(
        state,
        params=AdExParams(),
        dt_ms=0.1,
        I_syn_pA=np.array([0.0]),
        I_ext_pA=np.array([0.0]),
    )
    assert full.V_mV.shape == (1,)
    assert metrics.recommended_dt_ms > 0
    with pytest.raises(ValueError):
        adex_step_with_error_tracking(
            state,
            params=AdExParams(),
            dt_ms=-0.1,
            I_syn_pA=np.array([0.0]),
            I_ext_pA=np.array([0.0]),
        )
    with pytest.raises(ValueError):
        adex_step_with_error_tracking(
            state,
            params=AdExParams(),
            dt_ms=0.1,
            I_syn_pA=np.array([0.0]),
            I_ext_pA=np.array([0.0]),
            atol=0.0,
        )

    adaptive = adex_step_adaptive(
        state,
        params=AdExParams(),
        dt_ms=0.1,
        I_syn_pA=np.array([0.0]),
        I_ext_pA=np.array([0.0]),
    )
    assert adaptive.V_mV.shape == (1,)
