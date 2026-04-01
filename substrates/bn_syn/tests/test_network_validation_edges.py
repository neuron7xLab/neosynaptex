import numpy as np
import pytest

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams
from bnsyn.sim.network import Network, NetworkParams


def _make_network(**nparams_kwargs: float | int) -> Network:
    nparams = NetworkParams(**nparams_kwargs)
    rng = np.random.default_rng(0)
    return Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.1,
        rng=rng,
    )


def test_network_param_validation() -> None:
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="N must be positive"):
        Network(
            NetworkParams(N=0),
            AdExParams(),
            SynapseParams(),
            CriticalityParams(),
            dt_ms=0.1,
            rng=rng,
        )
    with pytest.raises(ValueError, match="frac_inhib must be in \\(0,1\\)"):
        Network(
            NetworkParams(N=10, frac_inhib=1.0),
            AdExParams(),
            SynapseParams(),
            CriticalityParams(),
            dt_ms=0.1,
            rng=rng,
        )
    with pytest.raises(ValueError, match="dt_ms must be positive"):
        Network(
            NetworkParams(N=10),
            AdExParams(),
            SynapseParams(),
            CriticalityParams(),
            dt_ms=0.0,
            rng=rng,
        )
    with pytest.raises(ValueError, match="backend must be 'reference' or 'accelerated'"):
        Network(
            NetworkParams(N=10),
            AdExParams(),
            SynapseParams(),
            CriticalityParams(),
            dt_ms=0.1,
            rng=rng,
            backend="invalid",
        )


def test_network_external_current_shape_validation() -> None:
    net = _make_network(N=6)
    with pytest.raises(ValueError, match="external_current_pA shape"):
        net.step(external_current_pA=np.zeros(5, dtype=np.float64))


def test_network_voltage_bounds_violation() -> None:
    net = _make_network(N=6, V_min_mV=-1.0, V_max_mV=1.0)
    with pytest.raises(RuntimeError, match="Voltage bounds violation"):
        net.step()


def test_network_voltage_bounds_violation_adaptive() -> None:
    net = _make_network(N=6, V_min_mV=-1.0, V_max_mV=1.0)
    with pytest.raises(RuntimeError, match="Voltage bounds violation"):
        net.step_adaptive()
