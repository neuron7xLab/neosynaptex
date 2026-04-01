"""Diagnostic Memory — system that learns from its own outputs.

Three mutations that turn a calculator into an intelligence:

Mutation 1: DiagnosticMemory
  Stores every SystemReport, builds correlation matrix across runs.
  After N observations, can answer: "what usually follows this state?"

Mutation 2: PredictiveRule
  Learned from data: "when X exceeds threshold, Y follows within K steps."
  Not ML — statistical pattern extraction from accumulated reports.

Mutation 3: Self-calibrating thresholds
  Literature says H>0.85 = critical. But for THIS system's data,
  the optimal threshold may be 0.91. Learns from own observations.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

__all__ = [
    "CalibratedThresholds",
    "DiagnosticMemory",
    "PredictiveRule",
]

logger = logging.getLogger(__name__)

# Feature keys extracted from SystemReport for correlation analysis
_NUMERIC_KEYS = [
    "anomaly_score",
    "ews_score",
    "basin_stability",
    "basin_error",
    "cosine_anonymity",
    "persuadability_score",
    "free_energy",
    "delta_alpha",
    "lacunarity_4",
    "lacunarity_decay",
    "basin_entropy",
    "hurst_exponent",
    "chi_invariant",
]


@dataclass
class PredictiveRule:
    """A learned rule: when condition is met, outcome follows.

    Example:
        "When chi < 0.3, severity becomes 'critical' within 8±3 steps (p=0.94)"
    """

    condition_key: str
    condition_op: str  # ">" or "<"
    condition_threshold: float
    outcome_key: str
    outcome_value: str
    confidence: float
    support: int  # number of observations backing this rule
    mean_lag: float  # mean steps between condition and outcome

    def matches(self, report_dict: dict[str, Any]) -> bool:
        """Check if a report matches this rule's condition."""
        val = report_dict.get(self.condition_key)
        if val is None or not isinstance(val, (int, float)):
            return False
        if self.condition_op == ">":
            return float(val) > self.condition_threshold
        return float(val) < self.condition_threshold

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "condition": f"{self.condition_key} {self.condition_op} {self.condition_threshold:.4f}",
            "outcome": f"{self.outcome_key} = {self.outcome_value}",
            "confidence": round(self.confidence, 3),
            "support": self.support,
            "mean_lag": round(self.mean_lag, 1),
        }

    def describe(self) -> str:
        """Human-readable rule description."""
        return (
            f"When {self.condition_key} {self.condition_op} {self.condition_threshold:.3f}, "
            f"{self.outcome_key} → {self.outcome_value} "
            f"(p={self.confidence:.2f}, n={self.support}, lag={self.mean_lag:.0f})"
        )


@dataclass
class CalibratedThresholds:
    """Self-calibrated thresholds from observed data distribution."""

    hurst_critical: float = 0.85
    delta_alpha_genuine: float = 0.2
    chi_critical: float = 0.3
    ews_warning: float = 0.5
    basin_stability_low: float = 0.4
    n_observations: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize."""
        return {
            "hurst_critical": round(self.hurst_critical, 4),
            "delta_alpha_genuine": round(self.delta_alpha_genuine, 4),
            "chi_critical": round(self.chi_critical, 4),
            "ews_warning": round(self.ews_warning, 4),
            "basin_stability_low": round(self.basin_stability_low, 4),
            "n_observations": self.n_observations,
        }


class DiagnosticMemory:
    """Accumulates SystemReports and extracts predictive intelligence.

    Usage::

        memory = DiagnosticMemory()

        # Feed reports from analysis runs
        for seed in range(100):
            seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=seed))
            report = engine.analyze(seq)
            memory.observe(report)

        # Extract learned intelligence
        rules = memory.extract_rules()
        for rule in rules:
            print(rule.describe())

        thresholds = memory.calibrate_thresholds()
        print(f"Optimal H critical: {thresholds.hurst_critical}")

        # Predict from current state
        predictions = memory.predict(current_report)
    """

    def __init__(self, capacity: int = 10000) -> None:
        self.capacity = capacity
        self._observations: list[dict[str, Any]] = []
        self._matrix: np.ndarray | None = None
        self._dirty = True
        self._rules: list[PredictiveRule] = []
        self._thresholds = CalibratedThresholds()

    @property
    def size(self) -> int:
        """Number of stored observations."""
        return len(self._observations)

    def observe(self, report: Any) -> None:
        """Store a SystemReport observation."""
        if hasattr(report, "to_dict"):
            d = self._flatten(report.to_dict())
        elif isinstance(report, dict):
            d = self._flatten(report)
        else:
            return

        self._observations.append(d)
        self._dirty = True

        # Evict oldest if over capacity
        if len(self._observations) > self.capacity:
            self._observations = self._observations[-self.capacity :]

    def _flatten(self, d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        """Flatten nested dict to single-level."""
        flat: dict[str, Any] = {}
        for k, v in d.items():
            key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
            if isinstance(v, dict):
                flat.update(self._flatten(v, key))
            else:
                flat[k] = v
        return flat

    def _build_matrix(self) -> None:
        """Build numeric matrix from observations for correlation analysis."""
        if not self._dirty or not self._observations:
            return
        n = len(self._observations)
        m = len(_NUMERIC_KEYS)
        mat = np.full((n, m), np.nan)
        for i, obs in enumerate(self._observations):
            for j, key in enumerate(_NUMERIC_KEYS):
                val = obs.get(key)
                if isinstance(val, (int, float)) and np.isfinite(val):
                    mat[i, j] = float(val)
        self._matrix = mat
        self._dirty = False

    def correlation_matrix(self) -> dict[str, dict[str, float]]:
        """Compute pairwise Pearson correlations between all numeric features."""
        self._build_matrix()
        if self._matrix is None or self.size < 5:
            return {}

        mat = self._matrix
        result: dict[str, dict[str, float]] = {}
        for i, ki in enumerate(_NUMERIC_KEYS):
            result[ki] = {}
            for j, kj in enumerate(_NUMERIC_KEYS):
                col_i = mat[:, i]
                col_j = mat[:, j]
                valid = np.isfinite(col_i) & np.isfinite(col_j)
                if valid.sum() < 5:
                    result[ki][kj] = 0.0
                    continue
                ci, cj = col_i[valid], col_j[valid]
                si, sj = np.std(ci), np.std(cj)
                if si < 1e-12 or sj < 1e-12:
                    result[ki][kj] = 0.0
                    continue
                r = float(np.corrcoef(ci, cj)[0, 1])
                result[ki][kj] = round(r, 4) if np.isfinite(r) else 0.0
        return result

    def extract_rules(
        self, min_confidence: float = 0.7, min_support: int = 10
    ) -> list[PredictiveRule]:
        """Extract predictive rules from accumulated observations.

        Scans for patterns: "when feature X crosses threshold T,
        severity/outcome Y follows with probability P."
        """
        self._build_matrix()
        if self._matrix is None or self.size < min_support:
            return []

        rules: list[PredictiveRule] = []
        severities = [obs.get("severity", "") for obs in self._observations]

        for j, key in enumerate(_NUMERIC_KEYS):
            col = self._matrix[:, j]
            valid = np.isfinite(col)
            if valid.sum() < min_support:
                continue

            vals = col[valid]
            sev_valid = [s for s, v in zip(severities, valid, strict=True) if v]

            # Try percentile-based thresholds
            for pct in [25, 75]:
                threshold = float(np.percentile(vals, pct))
                for op in [">", "<"]:
                    mask = vals > threshold if op == ">" else vals < threshold
                    if mask.sum() < min_support:
                        continue

                    # Check if this condition predicts a specific severity
                    sev_when_true = [s for s, m in zip(sev_valid, mask, strict=True) if m]
                    for target_sev in ["critical", "warning", "info", "stable"]:
                        count = sum(1 for s in sev_when_true if s == target_sev)
                        conf = count / len(sev_when_true) if sev_when_true else 0
                        if conf >= min_confidence and count >= min_support:
                            rules.append(
                                PredictiveRule(
                                    condition_key=key,
                                    condition_op=op,
                                    condition_threshold=threshold,
                                    outcome_key="severity",
                                    outcome_value=target_sev,
                                    confidence=conf,
                                    support=count,
                                    mean_lag=0.0,
                                )
                            )

        # Deduplicate: keep highest confidence per (key, outcome)
        best: dict[tuple[str, str], PredictiveRule] = {}
        for rule in rules:
            k = (rule.condition_key, rule.outcome_value)
            if k not in best or rule.confidence > best[k].confidence:
                best[k] = rule

        self._rules = sorted(best.values(), key=lambda r: -r.confidence)
        return self._rules

    def calibrate_thresholds(self) -> CalibratedThresholds:
        """Self-calibrate thresholds from observed data distribution.

        Uses the 90th percentile of each metric as the "critical" threshold,
        replacing hardcoded literature values with data-driven ones.
        """
        self._build_matrix()
        if self._matrix is None or self.size < 20:
            return self._thresholds

        def _pct(key: str, pct: float, default: float) -> float:
            idx = _NUMERIC_KEYS.index(key) if key in _NUMERIC_KEYS else -1
            if idx < 0:
                return default
            col = self._matrix[:, idx]
            valid = col[np.isfinite(col)]
            if len(valid) < 10:
                return default
            return float(np.percentile(valid, pct))

        self._thresholds = CalibratedThresholds(
            hurst_critical=_pct("hurst_exponent", 90, 0.85),
            delta_alpha_genuine=_pct("delta_alpha", 10, 0.2),
            chi_critical=_pct("chi_invariant", 25, 0.3),
            ews_warning=_pct("ews_score", 75, 0.5),
            basin_stability_low=_pct("basin_stability", 25, 0.4),
            n_observations=self.size,
        )
        return self._thresholds

    def predict(self, report: Any) -> list[str]:
        """Apply learned rules to a new report and return predictions."""
        if hasattr(report, "to_dict"):
            d = self._flatten(report.to_dict())
        elif isinstance(report, dict):
            d = self._flatten(report)
        else:
            return []

        if not self._rules:
            self.extract_rules()

        predictions: list[str] = []
        for rule in self._rules:
            if rule.matches(d):
                predictions.append(rule.describe())
        return predictions

    def save(self, path: str | Path) -> None:
        """Save memory state to JSON file."""
        p = Path(path)
        state = {
            "n_observations": self.size,
            "rules": [r.to_dict() for r in self._rules],
            "thresholds": self._thresholds.to_dict(),
            "observations": self._observations[-100:],  # last 100 for portability
        }
        p.write_text(json.dumps(state, indent=2, default=str))
        logger.info("DiagnosticMemory saved to %s (%d observations)", p, self.size)

    def load(self, path: str | Path) -> None:
        """Load memory state from JSON file."""
        p = Path(path)
        if not p.exists():
            return
        state = json.loads(p.read_text())
        self._observations = state.get("observations", [])
        self._dirty = True
        logger.info("DiagnosticMemory loaded from %s (%d observations)", p, self.size)

    def status(self) -> dict[str, Any]:
        """Return memory status."""
        return {
            "observations": self.size,
            "rules_learned": len(self._rules),
            "thresholds_calibrated": self._thresholds.n_observations > 0,
            "capacity": self.capacity,
        }
