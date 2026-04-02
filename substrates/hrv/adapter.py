"""Heart Rate Variability substrate adapter.

Cardiac HRV is a classic 1/f system. Topo = DFA α exponent complexity,
cost = inverse regularity (1/approximate_entropy). At physiological
criticality, γ ≈ 1.0 reflects balanced sympatho-vagal dynamics.

Data source: synthetic RR intervals with 1/f^α spectrum.
For real data: PhysioNet MIT-BIH, Fantasia, or NSR databases.
"""

from __future__ import annotations

import math

import numpy as np


class HrvAdapter:
    """DomainAdapter for cardiac HRV — 1/f criticality substrate."""

    def __init__(self, alpha: float = 1.0, n_beats: int = 512, seed: int = 77) -> None:
        self._alpha = alpha  # 1/f^alpha spectral slope
        self._n = n_beats
        self._rng = np.random.default_rng(seed)
        self._t = 0
        self._rr: np.ndarray = self._generate_rr()

    @property
    def domain(self) -> str:
        return "hrv"

    @property
    def state_keys(self) -> list[str]:
        return ["dfa_alpha", "sample_entropy", "rmssd"]

    def state(self) -> dict[str, float]:
        self._t += 1
        self._rr = self._generate_rr()

        dfa = self._dfa_alpha(self._rr)
        se = self._sample_entropy(self._rr, m=2, r=0.2)
        rmssd = self._rmssd(self._rr)

        return {
            "dfa_alpha": dfa,
            "sample_entropy": se,
            "rmssd": rmssd,
        }

    def topo(self) -> float:
        """Topological complexity = DFA scaling × log(n_beats).

        Higher DFA α × more beats = more complex organization.
        """
        dfa = self._dfa_alpha(self._rr)
        return max(0.01, dfa * math.log(self._n))

    def thermo_cost(self) -> float:
        """Thermodynamic cost = 1 / sample_entropy.

        Low entropy (high regularity) = high cost to maintain order.
        """
        se = self._sample_entropy(self._rr, m=2, r=0.2)
        return max(0.01, 1.0 / max(se, 0.01))

    def _generate_rr(self) -> np.ndarray:
        """Generate RR intervals with 1/f^alpha spectrum."""
        n = self._n
        freqs = np.fft.rfftfreq(n, d=1.0)
        freqs[0] = 1.0  # avoid division by zero
        # Modulate alpha slightly per tick for non-stationarity
        alpha_t = self._alpha + 0.1 * math.sin(0.05 * self._t) + self._rng.normal(0, 0.02)
        amplitudes = freqs ** (-alpha_t / 2.0)
        phases = self._rng.uniform(0, 2 * math.pi, len(freqs))
        phases[0] = 0
        spectrum = amplitudes * np.exp(1j * phases)
        rr = np.fft.irfft(spectrum, n=n)
        # Normalize to physiological range (800 ± 100 ms)
        rr = 800 + 100 * (rr - np.mean(rr)) / (np.std(rr) + 1e-10)
        return np.clip(rr, 400, 1500)

    @staticmethod
    def _dfa_alpha(rr: np.ndarray) -> float:
        """Detrended Fluctuation Analysis scaling exponent."""
        y = np.cumsum(rr - np.mean(rr))
        n = len(y)
        scales = [2**i for i in range(2, int(math.log2(n / 4)) + 1)]
        if len(scales) < 3:
            return float("nan")

        flucts = []
        for s in scales:
            n_seg = n // s
            if n_seg < 1:
                continue
            f_sum = 0.0
            for seg in range(n_seg):
                segment = y[seg * s : (seg + 1) * s]
                x_fit = np.arange(s, dtype=float)
                # Linear detrend
                coeffs = np.polyfit(x_fit, segment, 1)
                trend = np.polyval(coeffs, x_fit)
                f_sum += np.mean((segment - trend) ** 2)
            flucts.append(math.sqrt(f_sum / n_seg))

        if len(flucts) < 3:
            return float("nan")

        log_s = np.log(scales[: len(flucts)])
        log_f = np.log(np.array(flucts) + 1e-10)
        coeffs = np.polyfit(log_s, log_f, 1)
        return float(coeffs[0])

    @staticmethod
    def _sample_entropy(rr: np.ndarray, m: int = 2, r: float = 0.2) -> float:
        """Sample entropy (Richman & Moorman 2000)."""
        n = len(rr)
        tolerance = r * np.std(rr)
        if tolerance < 1e-10 or n < m + 2:
            return float("nan")

        def _count_matches(template_len: int) -> int:
            count = 0
            for i in range(n - template_len):
                for j in range(i + 1, n - template_len):
                    diff = np.abs(rr[i : i + template_len] - rr[j : j + template_len])
                    if np.max(diff) < tolerance:
                        count += 1
            return count

        a = _count_matches(m + 1)
        b = _count_matches(m)
        if b == 0:
            return float("nan")
        return float(-math.log(a / b)) if a > 0 else float("nan")

    @staticmethod
    def _rmssd(rr: np.ndarray) -> float:
        """Root mean square of successive differences."""
        diff = np.diff(rr)
        return float(math.sqrt(np.mean(diff**2)))
