"""Metacognition — the system's awareness of its own epistemic state.

Three capabilities that no protocol requested — pure Claude Opus 4.6 cognition:

1. Self-Consistency: do subsystems agree or contradict each other?
   A system that says "stable" while Hurst screams "critical" is lying to itself.
   Coherence score measures internal agreement.

2. Confidence Estimation: how sure is the system in its output?
   Not "anomaly_score=0.22" but "anomaly_score=0.22 ± 0.05 (confidence: high)".
   Based on signal agreement, not arbitrary thresholds.

3. Surprise Detection: is this observation novel relative to memory?
   Bayesian surprise = KL(posterior || prior). High surprise = increase uncertainty,
   gather more data before acting. Low surprise = act on learned patterns.

Together: a system that knows what it knows, knows what it doesn't know,
and knows when it's seeing something it's never seen before.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = ["MetaCognitiveLayer", "MetaCognitiveReport"]

logger = logging.getLogger(__name__)


@dataclass
class MetaCognitiveReport:
    """The system's assessment of its own epistemic state."""

    # Self-consistency
    coherence_score: float  # 0=total contradiction, 1=perfect agreement
    contradictions: list[str]  # human-readable contradiction descriptions
    n_signals_agree: int
    n_signals_total: int

    # Confidence
    confidence: float  # 0=no confidence, 1=maximum certainty
    confidence_drivers: list[str]  # what drives confidence up/down

    # Surprise
    surprise: float  # 0=expected, >2=highly novel
    novelty_dimensions: list[str]  # which features are novel

    def summary(self) -> str:
        """Single-line metacognitive summary."""
        coh = "COHERENT" if self.coherence_score > 0.7 else "CONFLICTED"
        conf = "HIGH" if self.confidence > 0.7 else ("MED" if self.confidence > 0.4 else "LOW")
        nov = "NOVEL" if self.surprise > 2.0 else ("familiar" if self.surprise < 0.5 else "mixed")
        return (
            f"[META] coherence={self.coherence_score:.2f}({coh}) "
            f"confidence={self.confidence:.2f}({conf}) "
            f"surprise={self.surprise:.2f}({nov})"
        )

    def interpretation(self) -> str:
        """Human-readable metacognitive interpretation."""
        lines: list[str] = []

        if self.coherence_score > 0.8:
            lines.append(
                f"All {self.n_signals_agree}/{self.n_signals_total} signals agree — "
                f"diagnosis is internally consistent."
            )
        elif self.coherence_score > 0.5:
            lines.append(
                f"Partial agreement ({self.n_signals_agree}/{self.n_signals_total}) — "
                f"some signals contradict."
            )
            for c in self.contradictions[:2]:
                lines.append(f"  Contradiction: {c}")
        else:
            lines.append(
                f"Low coherence ({self.n_signals_agree}/{self.n_signals_total}) — "
                f"subsystems disagree significantly. Treat results with caution."
            )
            for c in self.contradictions[:3]:
                lines.append(f"  Contradiction: {c}")

        if self.confidence > 0.7:
            lines.append("Confidence is high — safe to act on this diagnosis.")
        elif self.confidence > 0.4:
            lines.append("Moderate confidence — consider gathering more data.")
        else:
            lines.append(
                f"Low confidence — diagnosis unreliable. "
                f"Drivers: {', '.join(self.confidence_drivers[:2])}"
            )

        if self.surprise > 2.0:
            lines.append(
                f"HIGH SURPRISE ({self.surprise:.1f}) — this observation is novel. "
                f"Novel dimensions: {', '.join(self.novelty_dimensions[:3])}. "
                f"Learned rules may not apply."
            )
        elif self.surprise > 1.0:
            lines.append(
                f"Moderate novelty ({self.surprise:.1f}) — partially outside learned distribution."
            )

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize."""
        return {
            "coherence_score": round(self.coherence_score, 4),
            "contradictions": self.contradictions,
            "n_signals_agree": self.n_signals_agree,
            "n_signals_total": self.n_signals_total,
            "confidence": round(self.confidence, 4),
            "confidence_drivers": self.confidence_drivers,
            "surprise": round(self.surprise, 4),
            "novelty_dimensions": self.novelty_dimensions,
        }


class MetaCognitiveLayer:
    """Evaluates the system's own epistemic state from a SystemReport.

    Usage::

        meta = MetaCognitiveLayer()
        report = engine.analyze(seq)
        mc = meta.evaluate(report)
        print(mc.summary())
        print(mc.interpretation())
    """

    def __init__(self) -> None:
        self._seen_distributions: dict[str, list[float]] = {}

    def evaluate(self, report: Any) -> MetaCognitiveReport:
        """Assess coherence, confidence, and surprise of a SystemReport."""
        coherence, contradictions, n_agree, n_total = self._check_coherence(report)
        confidence, drivers = self._estimate_confidence(report, coherence)
        surprise, novel_dims = self._compute_surprise(report)

        return MetaCognitiveReport(
            coherence_score=coherence,
            contradictions=contradictions,
            n_signals_agree=n_agree,
            n_signals_total=n_total,
            confidence=confidence,
            confidence_drivers=drivers,
            surprise=surprise,
            novelty_dimensions=novel_dims,
        )

    def _check_coherence(self, report: Any) -> tuple[float, list[str], int, int]:
        """Check if subsystem signals are mutually consistent."""
        contradictions: list[str] = []
        checks: list[bool] = []

        severity = getattr(report, "severity", "info")
        is_critical = getattr(report, "is_critical_slowing", False)
        basin_stab = getattr(report, "basin_stability", 1.0)
        ews = getattr(report, "ews_score", 0.0)
        expanding = getattr(report, "spectral_expanding", True)
        anomaly = getattr(report, "anomaly_label", "nominal")

        # Check 1: severity vs Hurst critical
        if severity == "stable" and is_critical:
            contradictions.append("severity=stable but Hurst says CRITICAL slowing")
            checks.append(False)
        else:
            checks.append(True)

        # Check 2: basin stability vs severity
        if basin_stab > 0.8 and severity in ("warning", "critical"):
            contradictions.append(
                f"basin_stability={basin_stab:.2f} (high) but severity={severity}"
            )
            checks.append(False)
        elif basin_stab < 0.4 and severity == "stable":
            contradictions.append(f"basin_stability={basin_stab:.2f} (low) but severity=stable")
            checks.append(False)
        else:
            checks.append(True)

        # Check 3: EWS vs anomaly
        if ews > 0.7 and anomaly == "nominal":
            contradictions.append(f"ews_score={ews:.2f} (high transition risk) but anomaly=nominal")
            checks.append(False)
        else:
            checks.append(True)

        # Check 4: spectral expanding vs severity
        if not expanding and severity == "stable":
            contradictions.append("spectral COLLAPSING but severity=stable")
            checks.append(False)
        else:
            checks.append(True)

        # Check 5: anomaly vs ews direction
        if anomaly == "anomalous" and ews < 0.2:
            contradictions.append(
                "anomaly=anomalous but ews_score low — anomaly without transition signal"
            )
            checks.append(False)
        else:
            checks.append(True)

        n_agree = sum(checks)
        n_total = len(checks)
        coherence = n_agree / max(n_total, 1)
        return coherence, contradictions, n_agree, n_total

    def _estimate_confidence(self, report: Any, coherence: float) -> tuple[float, list[str]]:
        """Estimate confidence from signal strength and agreement."""
        drivers: list[str] = []
        scores: list[float] = []

        # Factor 1: coherence (most important)
        scores.append(coherence)
        if coherence < 0.6:
            drivers.append("low_coherence")

        # Factor 2: causal validation
        causal = getattr(report, "causal_decision", "pass")
        if causal == "pass":
            scores.append(1.0)
        elif causal == "degraded":
            scores.append(0.5)
            drivers.append("causal_degraded")
        else:
            scores.append(0.0)
            drivers.append("causal_failed")

        # Factor 3: anomaly score decisiveness (far from 0.5 = more decisive)
        anomaly_score = getattr(report, "anomaly_score", 0.5)
        decisiveness = abs(anomaly_score - 0.5) * 2  # 0 at 0.5, 1 at 0 or 1
        scores.append(decisiveness)
        if decisiveness < 0.3:
            drivers.append("ambiguous_anomaly_score")

        # Factor 4: basin stability (high = more confident)
        basin = getattr(report, "basin_stability", 0.5)
        scores.append(min(basin, 1.0))
        if basin < 0.5:
            drivers.append("unstable_basin")

        confidence = float(np.mean(scores))
        return confidence, drivers

    def _compute_surprise(self, report: Any) -> tuple[float, list[str]]:
        """Compute Bayesian surprise relative to seen distribution.

        Surprise = sum of z-scores for features outside 2σ of seen distribution.
        High surprise = novel observation, learned rules may not apply.
        """
        feature_keys = [
            "anomaly_score",
            "ews_score",
            "basin_stability",
            "delta_alpha",
            "hurst_exponent",
            "chi_invariant",
        ]

        novel_dims: list[str] = []
        z_scores: list[float] = []

        for key in feature_keys:
            val = getattr(report, key, None)
            if val is None or not isinstance(val, (int, float)):
                continue
            val = float(val)

            # Update running distribution
            if key not in self._seen_distributions:
                self._seen_distributions[key] = []
            self._seen_distributions[key].append(val)

            history = self._seen_distributions[key]
            if len(history) < 5:
                continue  # not enough data to judge surprise

            mean = float(np.mean(history[:-1]))
            std = float(np.std(history[:-1]))
            if std < 1e-12:
                continue

            z = abs(val - mean) / std
            z_scores.append(z)
            if z > 2.0:
                novel_dims.append(f"{key}(z={z:.1f})")

        surprise = float(np.mean(z_scores)) if z_scores else 0.0
        return surprise, novel_dims
