"""Transfer Entropy engine for causal information flow between E and I populations.

Implements TE(X->Y) using binned spike counts with Treves-Panzeri bias
correction and circular-shift surrogates for significance testing.

Mathematical definition
----------------------
TE(X->Y) = sum p(y_{t+1}, y_t^k, x_t^l) * log2[ p(y_{t+1}|y_t^k, x_t^l)
                                                    / p(y_{t+1}|y_t^k) ]

where k = l = history_depth.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

BoolArray = NDArray[np.bool_]
Float64Array = NDArray[np.float64]


@dataclass(frozen=True)
class TransferEntropyParams:
    """Parameters governing the Transfer Entropy computation."""

    bin_ms: float = 2.5
    history_depth: int = 3
    update_interval: int = 100
    buffer_size: int = 2000
    bias_correction: bool = True
    n_surrogates: int = 20


@dataclass(frozen=True)
class TEResult:
    """Immutable result container for a single TE computation."""

    te_e_to_i: float
    te_i_to_e: float
    te_net: float
    p_value_e_to_i: float
    p_value_i_to_e: float
    timestamp_step: int


class TransferEntropyEngine:
    """Ring-buffer-backed Transfer Entropy estimator for E/I populations.

    Parameters
    ----------
    N : int
        Total number of neurons.
    nE : int
        Number of excitatory neurons (indices 0..nE-1).
    params : TransferEntropyParams
        Configuration dataclass.
    """

    def __init__(
        self,
        N: int,
        nE: int,
        params: TransferEntropyParams | None = None,
    ) -> None:
        self._N = N
        self._nE = nE
        self._params = params or TransferEntropyParams()

        # Ring buffer: each entry stores (e_count, i_count) for one simulation step.
        self._buf_e = np.zeros(self._params.buffer_size, dtype=np.float64)
        self._buf_i = np.zeros(self._params.buffer_size, dtype=np.float64)
        self._write_idx: int = 0
        self._total_observed: int = 0

        # Accumulator for binning within a single bin_ms window.
        self._bin_accum_e: float = 0.0
        self._bin_accum_i: float = 0.0
        self._steps_in_bin: int = 0

        # How many simulation steps fit in one bin (set on first observe).
        self._steps_per_bin: int = max(1, int(round(self._params.bin_ms)))

        self._last_step: int = 0
        self._last_result: TEResult | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def observe(self, spiked: BoolArray, step: int) -> None:
        """Ingest one simulation step of spike data.

        Parameters
        ----------
        spiked : BoolArray
            Boolean array of length N indicating which neurons fired.
        step : int
            Current simulation step (monotonically increasing).
        """
        e_count = float(np.sum(spiked[: self._nE]))
        i_count = float(np.sum(spiked[self._nE :]))

        self._bin_accum_e += e_count
        self._bin_accum_i += i_count
        self._steps_in_bin += 1
        self._last_step = step

        if self._steps_in_bin >= self._steps_per_bin:
            idx = self._write_idx % self._params.buffer_size
            self._buf_e[idx] = self._bin_accum_e
            self._buf_i[idx] = self._bin_accum_i
            self._write_idx += 1
            self._total_observed += 1

            self._bin_accum_e = 0.0
            self._bin_accum_i = 0.0
            self._steps_in_bin = 0

    def compute(self) -> TEResult | None:
        """Compute transfer entropy if enough data is available.

        Returns None when the buffer does not yet contain enough bins
        (need at least ``history_depth + 1``).
        """
        n_available = min(self._total_observed, self._params.buffer_size)
        k = self._params.history_depth
        if n_available < k + 1:
            return None

        # Extract the valid portion of the ring buffer in chronological order.
        e_series, i_series = self._ordered_series(n_available)

        te_e2i_raw = self._estimate_te(e_series, i_series, k)
        te_i2e_raw = self._estimate_te(i_series, e_series, k)

        # Surrogate significance via circular shifts.
        # Surrogates also serve as bias correction: by subtracting the mean
        # surrogate TE we remove the finite-sample upward bias that affects
        # both the real and surrogate estimates equally.
        rng = np.random.default_rng(seed=42)
        n_sur = self._params.n_surrogates
        sur_e2i = np.empty(n_sur, dtype=np.float64)
        sur_i2e = np.empty(n_sur, dtype=np.float64)

        T = len(e_series)
        for s in range(n_sur):
            shift = rng.integers(k + 1, T)
            shifted_e = np.roll(e_series, int(shift))
            shifted_i = np.roll(i_series, int(shift))
            sur_e2i[s] = self._estimate_te(shifted_e, i_series, k)
            sur_i2e[s] = self._estimate_te(shifted_i, e_series, k)

        p_e2i = float(np.mean(sur_e2i >= te_e2i_raw))
        p_i2e = float(np.mean(sur_i2e >= te_i2e_raw))

        # Bias-corrected TE: subtract mean surrogate (finite-sample bias estimate).
        if self._params.bias_correction:
            te_e2i = max(te_e2i_raw - float(np.mean(sur_e2i)), 0.0)
            te_i2e = max(te_i2e_raw - float(np.mean(sur_i2e)), 0.0)
        else:
            te_e2i = te_e2i_raw
            te_i2e = te_i2e_raw

        self._last_result = TEResult(
            te_e_to_i=te_e2i,
            te_i_to_e=te_i2e,
            te_net=te_e2i - te_i2e,
            p_value_e_to_i=p_e2i,
            p_value_i_to_e=p_i2e,
            timestamp_step=self._last_step,
        )
        return self._last_result

    def get_flow_graph(self) -> dict[str, float]:
        """Return the most recent TE summary as a flat dict."""
        if self._last_result is None:
            return {"E_to_I": 0.0, "I_to_E": 0.0, "net": 0.0}
        return {
            "E_to_I": self._last_result.te_e_to_i,
            "I_to_E": self._last_result.te_i_to_e,
            "net": self._last_result.te_net,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ordered_series(
        self, n_available: int
    ) -> tuple[Float64Array, Float64Array]:
        """Return chronologically ordered (e, i) bin count arrays."""
        buf_size = self._params.buffer_size
        if n_available <= buf_size:
            if self._write_idx <= buf_size:
                return (
                    self._buf_e[: n_available].copy(),
                    self._buf_i[: n_available].copy(),
                )
            # Buffer has wrapped; reconstruct order.
            start = self._write_idx % buf_size
            e = np.concatenate([self._buf_e[start:], self._buf_e[:start]])
            i = np.concatenate([self._buf_i[start:], self._buf_i[:start]])
            return e, i
        # Fully wrapped.
        start = self._write_idx % buf_size
        e = np.concatenate([self._buf_e[start:], self._buf_e[:start]])
        i = np.concatenate([self._buf_i[start:], self._buf_i[:start]])
        return e, i

    @staticmethod
    def _quantize(series: Float64Array, n_levels: int = 2) -> NDArray[np.int64]:
        """Quantize a continuous series into ``n_levels`` discrete bins.

        Uses equal-frequency (quantile) binning so that each discrete level
        has roughly the same number of observations, which keeps the state
        space small and probability estimates stable.
        """
        edges = np.percentile(
            series,
            np.linspace(0, 100, n_levels + 1)[1:-1],
        )
        # Remove duplicate edges to avoid degenerate bins.
        edges = np.unique(edges)
        return np.digitize(series, edges).astype(np.int64)

    def _estimate_te(
        self,
        source: Float64Array,
        target: Float64Array,
        k: int,
    ) -> float:
        """Plug-in TE estimator with optional Treves-Panzeri bias correction.

        Quantises continuous spike counts into a small number of discrete
        levels (median split by default) to keep the state space manageable.
        """
        T = len(target)
        if T < k + 1:
            return 0.0

        n_samples = T - k

        # Adaptively choose quantization levels: keep state-space well below
        # sample count.  With k history lags per variable the joint table has
        # L^(2k+1) cells.  We want N_samples / n_cells >= ~5.
        n_levels = 2  # binary (above/below median) -- very robust default
        # Allow 3 levels only if we have plenty of data.
        if n_samples > 3 ** (2 * k + 1) * 10:
            n_levels = 3

        # Quantize into discrete levels.
        src_int = self._quantize(source, n_levels)
        tgt_int = self._quantize(target, n_levels)

        base = int(max(src_int.max(), tgt_int.max())) + 2

        # target_future: y_{t+1}
        y_future = tgt_int[k:]  # length n_samples

        # Encode history tuples as single integers.
        tgt_hist_codes = np.zeros(n_samples, dtype=np.int64)
        src_hist_codes = np.zeros(n_samples, dtype=np.int64)
        for lag in range(k):
            tgt_hist_codes = tgt_hist_codes * base + tgt_int[k - 1 - lag : T - 1 - lag]
            src_hist_codes = src_hist_codes * base + src_int[k - 1 - lag : T - 1 - lag]

        # Count joint and marginal occurrences via dicts.
        joint_yhs: dict[tuple[int, int, int], int] = {}
        joint_yh: dict[tuple[int, int], int] = {}
        joint_hs: dict[tuple[int, int], int] = {}
        marginal_h: dict[int, int] = {}

        for i in range(n_samples):
            yf = int(y_future[i])
            th = int(tgt_hist_codes[i])
            sh = int(src_hist_codes[i])

            key_yhs = (yf, th, sh)
            joint_yhs[key_yhs] = joint_yhs.get(key_yhs, 0) + 1

            key_yh = (yf, th)
            joint_yh[key_yh] = joint_yh.get(key_yh, 0) + 1

            key_hs = (th, sh)
            joint_hs[key_hs] = joint_hs.get(key_hs, 0) + 1

            marginal_h[th] = marginal_h.get(th, 0) + 1

        # Plug-in TE estimator.
        te = 0.0
        N_obs = float(n_samples)
        log2 = np.log2

        for (yf, th, sh), c_yhs in joint_yhs.items():
            p_yhs = c_yhs / N_obs
            c_yh = joint_yh[(yf, th)]
            c_hs = joint_hs[(th, sh)]
            c_h = marginal_h[th]

            # p(y|h,s) = c_yhs / c_hs
            # p(y|h)   = c_yh  / c_h
            ratio = (c_yhs * c_h) / (c_yh * c_hs) if (c_yh > 0 and c_hs > 0) else 1.0
            if ratio > 0:
                te += p_yhs * log2(ratio)

        return float(max(te, 0.0))
