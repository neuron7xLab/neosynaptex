from __future__ import annotations

import time
from typing import Any

import numpy as np

from .math_constants import EPSILON_LOG


class MetricsCollector:
    def __init__(self) -> None:
        self.metrics: dict[str, Any] = {
            "time": [],
            "phase": [],
            "L1_norm": [],
            "L2_norm": [],
            "L3_norm": [],
            "entropy_L1": [],
            "entropy_L2": [],
            "entropy_L3": [],
            "current_moral_threshold": [],
            "total_events_processed": 0,
            "accepted_events_count": 0,
            "latent_events_count": 0,
            "latencies": [],
        }
        self._event_start: float | None = None

    def start_event_timer(self) -> None:
        self._event_start = time.monotonic()

    def stop_event_timer_and_record_latency(self) -> None:
        if self._event_start is None:
            return
        latency = time.monotonic() - self._event_start
        self._event_start = None
        self.metrics["latencies"].append(latency)
        self.metrics["total_events_processed"] += 1

    def add_latent_event(self) -> None:
        self.metrics["latent_events_count"] += 1

    def add_accepted_event(self) -> None:
        self.metrics["accepted_events_count"] += 1

    @staticmethod
    def _entropy(vec: np.ndarray) -> float:
        """Compute Shannon entropy with improved numerical stability.

        Uses softmax transformation and log-sum-exp trick to avoid
        overflow/underflow issues.
        """
        if vec.size == 0:
            return 0.0
        v = np.abs(vec)
        # Log-sum-exp trick: subtract max for numerical stability
        v = v - v.max()
        exp_v = np.exp(v)
        s = exp_v.sum()
        if s < EPSILON_LOG:
            return 0.0
        p = exp_v / s
        return float(-np.sum(p * np.log2(p + EPSILON_LOG)))

    def record_memory_state(
        self, step: int, L1: np.ndarray, L2: np.ndarray, L3: np.ndarray, phase: str
    ) -> None:
        self.metrics["time"].append(step)
        self.metrics["phase"].append(phase)
        self.metrics["L1_norm"].append(float(np.linalg.norm(L1)))
        self.metrics["L2_norm"].append(float(np.linalg.norm(L2)))
        self.metrics["L3_norm"].append(float(np.linalg.norm(L3)))
        self.metrics["entropy_L1"].append(self._entropy(L1))
        self.metrics["entropy_L2"].append(self._entropy(L2))
        self.metrics["entropy_L3"].append(self._entropy(L3))

    def record_moral_threshold(self, threshold: float) -> None:
        self.metrics["current_moral_threshold"].append(float(threshold))

    def reset_metrics(self) -> None:
        # Reset all metrics to initial state
        self.metrics = {
            "time": [],
            "phase": [],
            "L1_norm": [],
            "L2_norm": [],
            "L3_norm": [],
            "entropy_L1": [],
            "entropy_L2": [],
            "entropy_L3": [],
            "current_moral_threshold": [],
            "total_events_processed": 0,
            "accepted_events_count": 0,
            "latent_events_count": 0,
            "latencies": [],
        }
        self._event_start = None

    def get_metrics(self) -> dict[str, Any]:
        return self.metrics
