"""Reference network simulator for BN-Syn.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements SPEC P2-11 reference network dynamics for deterministic tests.

References
----------
docs/SPEC.md#P2-11
docs/SSOT.md
"""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral, Real
from typing import Any, Literal, cast

import os
import numpy as np
from numpy.typing import NDArray

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams
from bnsyn.connectivity import SparseConnectivity
from bnsyn.criticality.branching import BranchingEstimator, SigmaController
from bnsyn.neuron.adex import AdExState, adex_step, adex_step_adaptive
from bnsyn.numerics.integrators import exp_decay_step
from bnsyn.synapse.conductance import nmda_mg_block
from bnsyn.validation import NetworkValidationConfig, validate_connectivity_matrix

torch: Any | None
try:
    import torch as torch_module
except Exception:  # pragma: no cover - optional GPU support
    torch = None
else:
    torch = torch_module

# Physics constants for synaptic transmission
AMPA_FRACTION = 0.7  # Fraction of excitatory current through AMPA receptors
NMDA_FRACTION = 0.3  # Fraction of excitatory current through NMDA receptors
GAIN_CURRENT_SCALE_PA = 50.0  # Current scaling factor for criticality gain (pA)
INITIAL_V_STD_MV = 5.0  # Standard deviation for initial voltage distribution (mV)

__all__ = ["Network", "NetworkParams", "run_simulation"]


@dataclass(frozen=True)
class NetworkParams:
    """Network configuration parameters.

    Parameters
    ----------
    N : int
        Number of neurons.
    frac_inhib : float
        Fraction of inhibitory neurons (0, 1).
    p_conn : float
        Connection probability for random connectivity.
    w_exc_nS : float
        Excitatory synaptic weight in nS.
    w_inh_nS : float
        Inhibitory synaptic weight in nS.
    ext_rate_hz : float
        External Poisson drive rate per neuron (Hz).
    ext_w_nS : float
        External synaptic weight in nS.
    V_min_mV : float
        Minimum membrane voltage bound (mV).
    V_max_mV : float
        Maximum membrane voltage bound (mV).

    Notes
    -----
    Configuration values are validated at network initialization.
    """

    N: int = 200
    frac_inhib: float = 0.2
    p_conn: float = 0.05
    w_exc_nS: float = 0.5
    w_inh_nS: float = 1.0
    ext_rate_hz: float = 2.0  # Poisson external drive per neuron
    ext_w_nS: float = 0.3

    # Simulation bounds
    V_min_mV: float = -100.0
    V_max_mV: float = 50.0


class Network:
    """Small reference network (dense enough for tests, not optimized).

    Parameters
    ----------
    nparams : NetworkParams
        Network configuration parameters.
    adex : AdExParams
        AdEx neuron parameters.
    syn : SynapseParams
        Synapse parameters.
    crit : CriticalityParams
        Criticality control parameters.
    dt_ms : float
        Timestep in milliseconds.
    rng : np.random.Generator
        NumPy RNG for deterministic sampling.

    Raises
    ------
    ValueError
        If parameters are invalid.

    Notes
    -----
    Implements SPEC P2-11 and integrates SPEC P0-1, P0-2, P0-4 components.

    References
    ----------
    docs/SPEC.md#P2-11
    docs/SSOT.md
    """

    def __init__(
        self,
        nparams: NetworkParams,
        adex: AdExParams,
        syn: SynapseParams,
        crit: CriticalityParams,
        dt_ms: float,
        rng: np.random.Generator,
        backend: Literal["reference", "accelerated"] = "reference",
    ):
        if nparams.N <= 0:
            raise ValueError("N must be positive")
        if not 0.0 < nparams.frac_inhib < 1.0:
            raise ValueError("frac_inhib must be in (0,1)")
        if dt_ms <= 0:
            raise ValueError("dt_ms must be positive")
        if backend not in ("reference", "accelerated"):
            raise ValueError("backend must be 'reference' or 'accelerated'")

        self.np = nparams
        self.adex = adex
        self.syn = syn
        self.dt_ms = dt_ms
        self.rng = rng
        self.backend = backend

        N = nparams.N
        nI = int(round(N * nparams.frac_inhib))
        nE = N - nI
        self.nE, self.nI = nE, nI
        self.is_inhib = np.zeros(N, dtype=bool)
        self.is_inhib[nE:] = True

        # adjacency masks
        mask = rng.random((N, N)) < nparams.p_conn
        np.fill_diagonal(mask, False)
        # excitatory weights (E->*)
        W_exc = np.asarray((mask[:nE, :].astype(np.float64) * nparams.w_exc_nS).T)
        # inhibitory weights (I->*)
        W_inh = np.asarray((mask[nE:, :].astype(np.float64) * nparams.w_inh_nS).T)

        validate_connectivity_matrix(W_exc, shape=(N, nE), name="W_exc")
        validate_connectivity_matrix(W_inh, shape=(N, nI), name="W_inh")

        # Backend-aware connectivity (reference = force dense, accelerated = force sparse)
        if backend == "reference":
            self.W_exc = SparseConnectivity(W_exc, force_format="dense")
            self.W_inh = SparseConnectivity(W_inh, force_format="dense")
        else:  # accelerated
            self.W_exc = SparseConnectivity(W_exc, force_format="sparse")
            self.W_inh = SparseConnectivity(W_inh, force_format="sparse")

        # neuron state
        V0 = np.asarray(
            rng.normal(loc=adex.EL_mV, scale=INITIAL_V_STD_MV, size=N), dtype=np.float64
        )
        w0 = np.zeros(N, dtype=np.float64)
        self.state = AdExState(V_mV=V0, w_pA=w0, spiked=np.zeros(N, dtype=bool))

        # conductances
        self.g_ampa = np.zeros(N, dtype=np.float64)
        self.g_nmda = np.zeros(N, dtype=np.float64)
        self.g_gabaa = np.zeros(N, dtype=np.float64)
        self._I_ext_buffer = np.zeros(N, dtype=np.float64)

        # criticality tracking
        self.branch = BranchingEstimator()
        self.sigma_ctl = SigmaController(params=crit, gain=1.0)
        self.gain = 1.0
        self._A_prev = 1.0
        self._use_torch = False
        self._torch_device = None
        self._W_exc_t = None
        self._W_inh_t = None

        if torch is not None and os.environ.get("BNSYN_USE_TORCH") == "1":
            device = os.environ.get("BNSYN_DEVICE", "cpu")
            self._torch_device = torch.device(device)
            self._W_exc_t = torch.as_tensor(self.W_exc.to_dense(), device=self._torch_device)
            self._W_inh_t = torch.as_tensor(self.W_inh.to_dense(), device=self._torch_device)
            self._use_torch = True

    def step(
        self,
        external_current_pA: NDArray[np.float64] | None = None,
    ) -> dict[str, float]:
        """Advance the network by one timestep.

        Parameters
        ----------
        external_current_pA : NDArray[np.float64] | None, optional
            External current injection per neuron in pA. Shape must be (N,).
            If None, no external current injection is applied (default behavior).

        Returns
        -------
        dict[str, float]
            Dictionary of metrics including sigma, gain, and spike rate.

        Raises
        ------
        ValueError
            If external_current_pA shape does not match number of neurons.
        RuntimeError
            If voltage bounds are violated (numerical instability).

        Notes
        -----
        Criticality gain is updated each step using sigma tracking.

        References
        ----------
        docs/SPEC.md#P2-11
        """
        N = self.np.N
        dt = self.dt_ms

        # validate external current if provided
        if external_current_pA is not None:
            if external_current_pA.shape != (N,):
                raise ValueError(
                    f"external_current_pA shape {external_current_pA.shape} "
                    f"does not match number of neurons ({N},)"
                )

        # external Poisson spikes (rate per neuron)
        lam = self.np.ext_rate_hz * (dt / 1000.0)
        ext_spikes = self.rng.random(N) < lam
        incoming_ext = ext_spikes.astype(float) * self.np.ext_w_nS

        # recurrent contributions from last step spikes
        spikes = self.state.spiked
        spikes_E = spikes[: self.nE].astype(float)
        spikes_I = spikes[self.nE :].astype(float)

        if self._use_torch:
            if torch is None:
                raise RuntimeError("PyTorch not available. Install with: pip install torch")
            torch_module = cast(Any, torch)
            spikes_E_t = torch_module.as_tensor(
                spikes_E,
                dtype=torch_module.float64,
                device=self._torch_device,
            )
            spikes_I_t = torch_module.as_tensor(
                spikes_I,
                dtype=torch_module.float64,
                device=self._torch_device,
            )
            incoming_exc = torch_module.matmul(self._W_exc_t, spikes_E_t).cpu().numpy()
            incoming_inh = torch_module.matmul(self._W_inh_t, spikes_I_t).cpu().numpy()
        else:
            incoming_exc = self.W_exc.apply(np.asarray(spikes_E, dtype=np.float64))
            incoming_inh = self.W_inh.apply(np.asarray(spikes_I, dtype=np.float64))

        # apply increments (split E into AMPA/NMDA)
        self.g_ampa += AMPA_FRACTION * incoming_exc + AMPA_FRACTION * incoming_ext
        self.g_nmda += NMDA_FRACTION * incoming_exc + NMDA_FRACTION * incoming_ext
        self.g_gabaa += incoming_inh

        # decay (exponential, dt-invariant)
        self.g_ampa = exp_decay_step(self.g_ampa, dt, self.syn.tau_AMPA_ms)
        self.g_nmda = exp_decay_step(self.g_nmda, dt, self.syn.tau_NMDA_ms)
        self.g_gabaa = exp_decay_step(self.g_gabaa, dt, self.syn.tau_GABAA_ms)

        # compute synaptic current (pA), then scale excitability by gain (criticality controller)
        V = self.state.V_mV
        B = nmda_mg_block(V, self.syn.mg_mM)
        I_syn = (
            self.g_ampa * (V - self.syn.E_AMPA_mV)
            + self.g_nmda * B * (V - self.syn.E_NMDA_mV)
            + self.g_gabaa * (V - self.syn.E_GABAA_mV)
        )

        # gain: multiplies external current (proxy for global excitability)
        I_ext = self._I_ext_buffer
        I_ext.fill(0.0)
        I_ext += GAIN_CURRENT_SCALE_PA * (self.gain - 1.0)  # pA offset

        # add optional external current injection
        if external_current_pA is not None:
            I_ext += external_current_pA

        self.state = adex_step(self.state, self.adex, dt, I_syn_pA=I_syn, I_ext_pA=I_ext)

        # safety bounds
        self._raise_if_voltage_out_of_bounds()

        # criticality estimation from population activity
        A_t = float(np.sum(spikes))
        A_t1 = float(np.sum(self.state.spiked))
        sigma = self.branch.update(A_t=max(A_t, 1.0), A_t1=max(A_t1, 1.0))
        self.gain = self.sigma_ctl.step(sigma)

        self._A_prev = A_t1

        return {
            "A_t": A_t,
            "A_t1": A_t1,
            "sigma": float(sigma),
            "gain": float(self.gain),
            "spike_rate_hz": float(A_t1 / N) / (dt / 1000.0),
        }

    def step_adaptive(
        self,
        *,
        atol: float = 1e-8,
        rtol: float = 1e-6,
        external_current_pA: NDArray[np.float64] | None = None,
    ) -> dict[str, float]:
        """Advance the network by one timestep using adaptive AdEx integration.

        Parameters
        ----------
        atol : float, optional
            Absolute tolerance for adaptive AdEx integration.
        rtol : float, optional
            Relative tolerance for adaptive AdEx integration.

        external_current_pA : NDArray[np.float64] | None, optional
            External current injection per neuron in pA. Shape must be (N,).
            If None, no external current injection is applied (default behavior).

        Returns
        -------
        dict[str, float]
            Dictionary of metrics including sigma, gain, and spike rate.

        Raises
        ------
        ValueError
            If external_current_pA shape does not match number of neurons.
        RuntimeError
            If voltage bounds are violated (numerical instability).

        Notes
        -----
        Uses adaptive AdEx integration while preserving criticality tracking.

        References
        ----------
        docs/SPEC.md#P2-11
        """
        N = self.np.N
        dt = self.dt_ms

        if external_current_pA is not None:
            if external_current_pA.shape != (N,):
                raise ValueError(
                    f"external_current_pA shape {external_current_pA.shape} "
                    f"does not match number of neurons ({N},)"
                )

        lam = self.np.ext_rate_hz * (dt / 1000.0)
        ext_spikes = self.rng.random(N) < lam
        incoming_ext = ext_spikes.astype(float) * self.np.ext_w_nS

        spikes = self.state.spiked
        spikes_E = spikes[: self.nE].astype(float)
        spikes_I = spikes[self.nE :].astype(float)

        if self._use_torch:
            if torch is None:
                raise RuntimeError("PyTorch not available. Install with: pip install torch")
            torch_module = cast(Any, torch)
            spikes_E_t = torch_module.as_tensor(
                spikes_E,
                dtype=torch_module.float64,
                device=self._torch_device,
            )
            spikes_I_t = torch_module.as_tensor(
                spikes_I,
                dtype=torch_module.float64,
                device=self._torch_device,
            )
            incoming_exc = torch_module.matmul(self._W_exc_t, spikes_E_t).cpu().numpy()
            incoming_inh = torch_module.matmul(self._W_inh_t, spikes_I_t).cpu().numpy()
        else:
            incoming_exc = self.W_exc.apply(np.asarray(spikes_E, dtype=np.float64))
            incoming_inh = self.W_inh.apply(np.asarray(spikes_I, dtype=np.float64))

        self.g_ampa += AMPA_FRACTION * incoming_exc + AMPA_FRACTION * incoming_ext
        self.g_nmda += NMDA_FRACTION * incoming_exc + NMDA_FRACTION * incoming_ext
        self.g_gabaa += incoming_inh

        self.g_ampa = exp_decay_step(self.g_ampa, dt, self.syn.tau_AMPA_ms)
        self.g_nmda = exp_decay_step(self.g_nmda, dt, self.syn.tau_NMDA_ms)
        self.g_gabaa = exp_decay_step(self.g_gabaa, dt, self.syn.tau_GABAA_ms)

        V = self.state.V_mV
        B = nmda_mg_block(V, self.syn.mg_mM)
        I_syn = (
            self.g_ampa * (V - self.syn.E_AMPA_mV)
            + self.g_nmda * B * (V - self.syn.E_NMDA_mV)
            + self.g_gabaa * (V - self.syn.E_GABAA_mV)
        )

        I_ext = self._I_ext_buffer
        I_ext.fill(0.0)
        I_ext += GAIN_CURRENT_SCALE_PA * (self.gain - 1.0)

        if external_current_pA is not None:
            I_ext += external_current_pA

        self.state = adex_step_adaptive(
            self.state,
            self.adex,
            dt,
            I_syn_pA=I_syn,
            I_ext_pA=I_ext,
            atol=atol,
            rtol=rtol,
        )

        self._raise_if_voltage_out_of_bounds()

        A_t = float(np.sum(spikes))
        A_t1 = float(np.sum(self.state.spiked))
        sigma = self.branch.update(A_t=max(A_t, 1.0), A_t1=max(A_t1, 1.0))
        self.gain = self.sigma_ctl.step(sigma)

        self._A_prev = A_t1

        return {
            "A_t": A_t,
            "A_t1": A_t1,
            "sigma": float(sigma),
            "gain": float(self.gain),
            "spike_rate_hz": float(A_t1 / N) / (dt / 1000.0),
        }

    def _raise_if_voltage_out_of_bounds(self) -> None:
        if (
            float(np.min(self.state.V_mV)) < self.np.V_min_mV
            or float(np.max(self.state.V_mV)) > self.np.V_max_mV
        ):
            raise RuntimeError("Voltage bounds violation (numerical instability)")


def run_simulation(
    steps: int,
    dt_ms: float,
    seed: int,
    N: int = 200,
    backend: Literal["reference", "accelerated"] = "reference",
    external_current_pA: float = 0.0,
) -> dict[str, float]:
    """Run a deterministic simulation and return summary metrics.

    Parameters
    ----------
    steps : int
        Number of simulation steps.
    dt_ms : float
        Timestep in milliseconds.
    seed : int
        RNG seed.
    N : int, optional
        Number of neurons.
    backend : Literal["reference", "accelerated"], optional
        Backend mode: 'reference' (default) or 'accelerated'.
    external_current_pA : float, optional
        Constant external current injection per neuron in picoamps.
        Default is 0.0 (no injection). Use positive values to increase
        network excitability and ensure spiking activity.

    Returns
    -------
    dict[str, float]
        Summary metrics with mean and standard deviation for sigma and firing rate.

    Notes
    -----
    Uses explicit seeding and validation to satisfy the determinism contract.
    External current injection can be used to ensure network activity for testing.

    References
    ----------
    docs/SPEC.md#P2-11
    docs/REPRODUCIBILITY.md
    """
    from bnsyn.rng import seed_all

    if not isinstance(steps, Integral):
        raise TypeError("steps must be a positive integer")
    if steps <= 0:
        raise ValueError("steps must be greater than 0")
    if not isinstance(external_current_pA, Real):
        raise TypeError("external_current_pA must be a finite real number")
    external_current = float(external_current_pA)
    if not np.isfinite(external_current):
        raise ValueError("external_current_pA must be a finite real number")

    _ = NetworkValidationConfig(N=N, dt_ms=dt_ms)
    pack = seed_all(seed)
    rng = pack.np_rng
    nparams = NetworkParams(N=N)
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=dt_ms,
        rng=rng,
        backend=backend,
    )

    sigmas: list[float] = []
    rates: list[float] = []

    # Prepare external current array if needed
    injected_current: NDArray[np.float64] | None = None
    if abs(external_current) > 1e-9:  # Robust check for non-zero
        injected_current = np.full(N, external_current, dtype=np.float64)

    for _ in range(steps):
        m = net.step(external_current_pA=injected_current)
        sigmas.append(m["sigma"])
        rates.append(m["spike_rate_hz"])

    return {
        "sigma_mean": float(np.mean(sigmas)),
        "rate_mean_hz": float(np.mean(rates)),
        "sigma_std": float(np.std(sigmas)),
        "rate_std": float(np.std(rates)),
    }
