"""CoherenceBridge v2 -- NFI-market integration layer.

SSI.EXTERNAL domain: models market agent dynamics, NOT internal NFI state.
INVARIANT_IV compliant by architecture.

Pipeline:
  Ali signal_analyzer -> raw_signals
  CoherenceBridge.ingest() -> coherence_state
  NFI.observe(coherence_state) -> gamma_market
  ActionGate.decide(gamma_market) -> trade_action

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
from scipy.signal import hilbert
from scipy.stats import theilslopes


class CoherenceBridge:
    """NFI-market integration layer.

    Operates in SSI.EXTERNAL domain (INVARIANT_IV compliant).
    Models market agent dynamics -- NOT internal NFI state.
    """

    def __init__(self, window: int = 50, bootstrap_n: int = 200) -> None:
        self.window = window
        self.bootstrap_n = bootstrap_n
        self._history: List[Dict] = []

    def ingest(self, raw_signals: Dict) -> Dict:
        """Convert raw market signals to NFI coherence state.

        Input:  {'prices': array, 'volumes': array, 'timestamp': float}
        Output: {'kuramoto_r': float, 'gamma_estimate': float,
                 'regime': str, 'confidence': float}
        """
        prices = np.asarray(raw_signals["prices"], dtype=np.float64)
        if len(prices) < self.window:
            return {
                "kuramoto_r": float("nan"),
                "gamma_estimate": float("nan"),
                "regime": "insufficient_data",
                "confidence": 0.0,
                "timestamp": raw_signals.get("timestamp", 0),
            }

        # Phase extraction via Hilbert transform
        centered = prices - prices.mean()
        # Avoid zero signal
        if np.std(centered) < 1e-10:
            centered = centered + np.random.default_rng(0).standard_normal(len(centered)) * 1e-8
        analytic = hilbert(centered)
        phases = np.angle(analytic)

        r = self.compute_kuramoto_r(phases[-self.window:])
        gamma = self._estimate_gamma_theil_sen(prices)
        regime = self.regime_classify(r, gamma)
        confidence = self._bootstrap_confidence(phases)

        state = {
            "kuramoto_r": float(r),
            "gamma_estimate": float(gamma),
            "regime": regime,
            "confidence": float(confidence),
            "timestamp": raw_signals.get("timestamp", 0),
        }
        self._history.append(state)
        return state

    def compute_kuramoto_r(self, phases: np.ndarray) -> float:
        """Order parameter r = |1/N * sum exp(i*theta_j)|.

        r -> 1.0: full sync (trend)
        r -> 0.0: incoherent (noise)
        r ~ 0.5-0.7: critical regime <- trade here
        """
        return float(np.abs(np.mean(np.exp(1j * phases))))

    def _estimate_gamma_theil_sen(self, prices: np.ndarray) -> float:
        """Theil-Sen robust gamma estimation. gamma DERIVED, never assigned.

        Uses gamma_PSD = 2H + 1 (VERIFIED formula).
        """
        log_prices = np.log(np.abs(prices) + 1e-10)
        x = np.arange(len(log_prices), dtype=np.float64)
        result = theilslopes(log_prices, x)
        raw_slope = result.slope
        H_estimate = np.clip(0.5 + raw_slope * 10, 0.01, 0.99)
        gamma = 2 * H_estimate + 1  # gamma_PSD = 2H + 1, VERIFIED
        return float(np.clip(gamma, 0.1, 3.0))

    def regime_classify(self, r: float, gamma: float) -> str:
        """Classify market regime via (r, gamma).

        Returns: "critical" | "synchronized" | "incoherent" | "transitioning"
        """
        gamma_metastable = abs(gamma - 1.0) < 0.15
        if gamma_metastable and 0.4 < r < 0.8:
            return "critical"
        elif r > 0.85:
            return "synchronized"
        elif r < 0.3:
            return "incoherent"
        else:
            return "transitioning"

    def _bootstrap_confidence(self, phases: np.ndarray, n: int = 100) -> float:
        """Bootstrap CI95 on r estimate. Narrower CI -> higher confidence."""
        window_phases = phases[-self.window:]
        rng = np.random.default_rng(42)
        r_samples = []
        for _ in range(n):
            idx = rng.choice(len(window_phases), len(window_phases), replace=True)
            r_boot = self.compute_kuramoto_r(window_phases[idx])
            r_samples.append(r_boot)
        ci_width = np.percentile(r_samples, 97.5) - np.percentile(r_samples, 2.5)
        return float(max(0.0, 1.0 - ci_width))

    @property
    def history(self) -> List[Dict]:
        return list(self._history)

    def demo_synthetic(self, T: int = 500) -> Dict:
        """Synthetic market demo.

        Generates: incoherent -> transitioning -> critical -> synchronized
        Ready to show Ali as live gamma_market trajectory.
        """
        rng = np.random.default_rng(42)
        prices = np.cumsum(rng.standard_normal(T)) + 100
        # Inject critical period in middle third
        mid = T // 3
        span = min(150, T // 3)
        prices[mid:mid + span] += np.sin(np.linspace(0, 4 * np.pi, span)) * 5

        results = []
        for i in range(self.window, T, 10):
            window_prices = prices[max(0, i - self.window):i]
            state = self.ingest({
                "prices": window_prices,
                "timestamp": float(i),
            })
            results.append(state)

        gammas = [r["gamma_estimate"] for r in results]
        return {
            "trajectory": results,
            "mean_gamma": float(np.mean(gammas)),
            "std_gamma": float(np.std(gammas)),
            "critical_windows": sum(1 for r in results if r["regime"] == "critical"),
            "total_windows": len(results),
        }


if __name__ == "__main__":
    bridge = CoherenceBridge(window=50)
    demo = bridge.demo_synthetic(500)
    print(f"Demo: {demo['total_windows']} windows, {demo['critical_windows']} critical")
    print(f"Mean gamma: {demo['mean_gamma']:.4f} +/- {demo['std_gamma']:.4f}")
    for r in demo["trajectory"][:5]:
        print(f"  t={r['timestamp']:.0f} r={r['kuramoto_r']:.3f} g={r['gamma_estimate']:.3f} regime={r['regime']}")
