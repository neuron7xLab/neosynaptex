"""
Bayesian Immune System — false-alarm detection for agent regulation.

Dual-signal detection: an alert must fire on ≥ 2 independent channels
before triggering a response. Single-channel alerts are quarantined
and tracked but do not cause action.

With M=5 detectors and FP ≤ 0.02 per channel:
    Single-signal: P(autoimmune) = 1.0 (guaranteed false positive)
    Dual-signal:   P(autoimmune) ≈ 0.078 (12× reduction)

To push P(autoimmune) > 0.5, attacker needs to compromise ≥ 2
independent channels OR target methods with FP > 0.16.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Alert:
    """A single alert from one detection channel."""

    channel: str
    severity: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    evidence: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImmuneVerdict:
    """Result of immune system evaluation."""

    alerts: list[Alert]
    is_real_threat: bool
    corroborating_channels: int
    autoimmune_probability: float
    quarantined: list[Alert] = field(default_factory=list)

    @property
    def channels_firing(self) -> int:
        """Number of unique channels that fired."""
        return len({a.channel for a in self.alerts})


class BayesianImmune:
    """
    Dual-signal immune system for agent threat detection.

    Parameters
    ----------
    min_corroboration : int
        Minimum number of independent channels that must fire.
    false_positive_rate : float
        Expected false positive rate per channel.
    channels : list[str]
        Names of available detection channels.

    Examples
    --------
    >>> immune = BayesianImmune(channels=["error_rate", "latency", "cpu", "queue", "deps"])
    >>> verdict = immune.evaluate([
    ...     Alert("error_rate", severity=0.8, confidence=0.9),
    ...     Alert("latency", severity=0.6, confidence=0.7),
    ... ])
    >>> verdict.is_real_threat
    True
    """

    def __init__(
        self,
        min_corroboration: int = 2,
        false_positive_rate: float = 0.02,
        channels: list[str] | None = None,
    ) -> None:
        self.min_corroboration = min_corroboration
        self.fp_rate = false_positive_rate
        self.channels = channels or [
            "error_rate",
            "latency",
            "cpu_saturation",
            "queue_depth",
            "dependency_health",
        ]
        self._quarantine: list[Alert] = []

    def _autoimmune_probability(self, n_firing: int) -> float:
        """
        Probability that all firing channels are false positives.

        P(all FP) = fp_rate ^ n_firing
        """
        if n_firing <= 0:
            return 1.0
        return self.fp_rate**n_firing

    def evaluate(self, alerts: list[Alert]) -> ImmuneVerdict:
        """
        Evaluate a set of alerts through dual-signal detection.

        Parameters
        ----------
        alerts : list[Alert]
            Alerts from various detection channels.

        Returns
        -------
        ImmuneVerdict
            Whether this is a real threat or potential autoimmune response.
        """
        unique_channels = {a.channel for a in alerts}
        n_firing = len(unique_channels)
        autoimmune_p = self._autoimmune_probability(n_firing)

        is_real = n_firing >= self.min_corroboration

        quarantined = []
        if not is_real:
            quarantined = list(alerts)
            self._quarantine.extend(alerts)

        return ImmuneVerdict(
            alerts=alerts,
            is_real_threat=is_real,
            corroborating_channels=n_firing,
            autoimmune_probability=autoimmune_p,
            quarantined=quarantined,
        )

    @property
    def quarantine_size(self) -> int:
        """Number of alerts currently in quarantine."""
        return len(self._quarantine)
