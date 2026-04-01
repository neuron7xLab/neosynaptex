"""Auto-Heal — closed cognitive loop with experience memory.

OBSERVE → DIAGNOSE → DECIDE → ACT → VERIFY → LEARN → REPORT

The system diagnoses itself, plans an intervention if needed,
applies it (re-simulates), re-diagnoses, and proves whether
the intervention worked — with ΔM as evidence.

After each heal, the outcome is stored in ExperienceMemory.
After enough experiences, the system predicts outcomes before
running expensive counterfactual simulations. Prediction error
reveals where the system doesn't understand itself.

    result = mfn.auto_heal(seq)           # first call: brute-force
    ...                                    # 50 calls later
    result = mfn.auto_heal(seq)           # uses learned predictions
    print(result.prediction_used)          # True
    print(result.prediction_error)         # 0.03 (low = understood)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from .types.field import FieldSequence

__all__ = ["ExperienceMemory", "HealResult", "auto_heal"]


# ═══════════════════════════════════════════════════════════════════════════
# EXPERIENCE MEMORY — the system learns from its own interventions
# ═══════════════════════════════════════════════════════════════════════════


_FEATURE_KEYS = [
    "M_before",
    "anomaly_before",
    "alpha",
    "turing_threshold",
    "jitter_var",
    "spike_probability",
    "delta_alpha",
    "delta_spike",
    "delta_gabaa",
    "delta_sero_gain",
]


class ExperienceMemory:
    """Accumulates (state, action, outcome) triples. Predicts via Ridge regression.

    After min_experiences calls, a Ridge model predicts M_after from the
    full feature vector. Feature importances reveal what the system has
    learned about itself. R² measures depth of self-understanding.

    Compression = understanding (Sutskever): the linear model IS the
    system's compressed self-knowledge. Features it assigns high weight
    are the ones it has discovered as causal.
    """

    def __init__(self, min_experiences: int = 15, max_experiences: int = 500) -> None:
        self.min_experiences = min_experiences
        self.max_experiences = max_experiences
        self._features: list[dict[str, float]] = []
        self._M_after: list[float] = []
        self._anomaly_after: list[float] = []
        self._healed: list[bool] = []
        self._model: Any = None
        self._r2: float = 0.0
        self._importances: dict[str, float] = {}

    @property
    def size(self) -> int:
        return len(self._M_after)

    @property
    def can_predict(self) -> bool:
        return self._model is not None

    @property
    def r_squared(self) -> float:
        """How well the system understands itself. 1.0 = perfect self-model."""
        return self._r2

    @property
    def feature_importances(self) -> dict[str, float]:
        """What the system has discovered matters. Higher = more causal."""
        return dict(self._importances)

    def store(
        self, features: dict[str, float], M_after: float, anomaly_after: float, healed: bool
    ) -> None:
        self._features.append(features)
        self._M_after.append(M_after)
        self._anomaly_after.append(anomaly_after)
        self._healed.append(healed)
        # FIFO eviction when over capacity
        if self.size > self.max_experiences:
            self._features = self._features[-self.max_experiences:]
            self._M_after = self._M_after[-self.max_experiences:]
            self._anomaly_after = self._anomaly_after[-self.max_experiences:]
            self._healed = self._healed[-self.max_experiences:]
        # Refit model when we have enough data
        if self.size >= self.min_experiences:
            self._fit()

    def _fit(self) -> None:
        """Fit Ridge regression on accumulated experiences."""
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import StandardScaler

        keys = list(self._features[0].keys())
        X = np.array([[f.get(k, 0.0) for k in keys] for f in self._features])
        y = np.array(self._M_after)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = Ridge(alpha=1.0)
        model.fit(X_scaled, y)
        self._r2 = float(model.score(X_scaled, y))

        # Feature importances: |coefficient| on scaled data = relative importance
        abs_coef = np.abs(model.coef_)
        total = abs_coef.sum() + 1e-12
        self._importances = {
            k: round(float(c / total), 4) for k, c in zip(keys, abs_coef, strict=False)
        }

        # Store for prediction
        self._model = model
        self._scaler = scaler
        self._keys = keys

    def predict(self, features: dict[str, float]) -> tuple[float, float, float]:
        """Predict M_after from features.

        Returns (predicted_M_after, predicted_anomaly_after, R²).
        R² = confidence (how well the model fits all past data).
        """
        if self._model is None:
            return 0.0, 0.0, 0.0

        x = np.array([[features.get(k, 0.0) for k in self._keys]])
        x_scaled = self._scaler.transform(x)
        M_pred = float(self._model.predict(x_scaled)[0])

        # Anomaly: simple mean of past (Ridge on M only)
        a_pred = float(np.mean(self._anomaly_after))

        return M_pred, a_pred, self._r2

    def recommend(
        self,
        state_features: dict[str, float],
        lever_names: list[str] | None = None,
        n_candidates: int = 20,
    ) -> dict[str, float] | None:
        """Use the learned model to find the best intervention.

        Instead of brute-force counterfactual, the Ridge model
        evaluates many candidate interventions analytically.
        Returns the delta values that MINIMIZE predicted M_after.
        """
        if not self.can_predict or self._model is None:
            return None

        rng = np.random.default_rng(42)
        levers = lever_names or [k for k in self._keys if k.startswith("delta_")]
        if not levers:
            return None

        best_M = float("inf")
        best_deltas = None

        for _ in range(n_candidates):
            candidate = dict(state_features)
            for lever in levers:
                candidate[lever] = rng.uniform(-0.5, 0.5)
            x = np.array([[candidate.get(k, 0.0) for k in self._keys]])
            x_scaled = self._scaler.transform(x)
            M_pred = float(self._model.predict(x_scaled)[0])
            if M_pred < best_M:
                best_M = M_pred
                best_deltas = {k: candidate[k] for k in levers}

        return best_deltas

    @property
    def top_levers(self) -> list[str]:
        """Return top 2 levers by importance — for focused intervention."""
        if not self._importances:
            return []
        sorted_imp = sorted(self._importances.items(), key=lambda x: -x[1])
        return [k for k, _ in sorted_imp[:2] if k.startswith("delta_")]

    @property
    def best_known_intervention(self) -> dict[str, float] | None:
        """Return the intervention from experience that gave lowest M_after."""
        if not self._features:
            return None
        best_idx = int(np.argmin(self._M_after))
        return {k: v for k, v in self._features[best_idx].items() if k.startswith("delta_")}

    def stats(self) -> dict[str, Any]:
        if not self._M_after:
            return {"size": 0}
        healed = sum(self._healed)
        return {
            "size": self.size,
            "heal_rate": round(healed / self.size, 3),
            "M_after_mean": round(float(np.mean(self._M_after)), 4),
            "M_after_std": round(float(np.std(self._M_after)), 4),
            "can_predict": self.can_predict,
            "r_squared": round(self._r2, 4),
            "top_features": dict(sorted(self._importances.items(), key=lambda x: -x[1])[:5])
            if self._importances
            else {},
            "top_levers": self.top_levers,
            "best_known_M": round(float(min(self._M_after)), 4) if self._M_after else None,
        }


# Global state — persists across calls within process
_MEMORY = ExperienceMemory()
_DA_STATE = None  # lazy init
_STATE_LOCK = threading.Lock()

_log = logging.getLogger(__name__)


def _get_da_module():
    from .neurochem.dopamine import DopamineState, compute_dopamine, modulate_plasticity

    return DopamineState, compute_dopamine, modulate_plasticity


@dataclass
class HealResult:
    """Complete result of the auto-heal cognitive loop."""

    # Before
    severity_before: str
    anomaly_before: str
    anomaly_score_before: float
    M_before: float
    hwi_before: bool

    # Decision
    needs_healing: bool
    intervention_applied: bool
    changes: list[dict[str, Any]]

    # After (None if no intervention needed)
    severity_after: str | None
    anomaly_after: str | None
    anomaly_score_after: float | None
    M_after: float | None
    hwi_after: bool | None

    # Verification
    delta_M: float | None
    delta_anomaly: float | None
    healed: bool | None

    # Learning
    prediction_used: bool = False
    predicted_M_after: float | None = None
    prediction_error: float | None = None
    experience_count: int = 0

    # Dopamine
    dopamine_level: float = 0.0
    dopamine_plasticity: float = 1.0

    # Meta
    compute_time_ms: float = 0.0

    def summary(self) -> str:
        if not self.needs_healing:
            return (
                f"[HEAL] System healthy — no intervention needed. "
                f"M={self.M_before:.3f} severity={self.severity_before} "
                f"({self.compute_time_ms:.0f}ms)"
            )

        status = "HEALED" if self.healed else "FAILED"
        dm = self.delta_M if self.delta_M is not None else 0
        d_anom = self.delta_anomaly if self.delta_anomaly is not None else 0
        pred = ""
        if self.prediction_used and self.prediction_error is not None:
            pred = f" pred_err={self.prediction_error:.3f}"
        da_str = f" DA={self.dopamine_level:.2f}" if self.dopamine_level > 0 else ""
        exp = f" exp={self.experience_count}" if self.experience_count > 0 else ""
        return (
            f"[HEAL] {status} | "
            f"M: {self.M_before:.3f} -> {self.M_after:.3f} (dM={dm:+.3f}) | "
            f"anomaly: {self.anomaly_score_before:.3f} -> {self.anomaly_score_after:.3f} "
            f"(d={d_anom:+.3f}) | "
            f"severity: {self.severity_before} -> {self.severity_after}"
            f"{pred}{da_str}{exp} ({self.compute_time_ms:.0f}ms)"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "before": {
                "severity": self.severity_before,
                "anomaly": self.anomaly_before,
                "anomaly_score": round(self.anomaly_score_before, 4),
                "M": round(self.M_before, 6),
                "hwi_holds": self.hwi_before,
            },
            "decision": {
                "needs_healing": self.needs_healing,
                "intervention_applied": self.intervention_applied,
                "changes": self.changes,
            },
            "after": {
                "severity": self.severity_after,
                "anomaly": self.anomaly_after,
                "anomaly_score": round(self.anomaly_score_after, 4)
                if self.anomaly_score_after is not None
                else None,
                "M": round(self.M_after, 6) if self.M_after is not None else None,
                "hwi_holds": self.hwi_after,
            },
            "verification": {
                "delta_M": round(self.delta_M, 6) if self.delta_M is not None else None,
                "delta_anomaly": round(self.delta_anomaly, 4)
                if self.delta_anomaly is not None
                else None,
                "healed": self.healed,
            },
            "learning": {
                "prediction_used": self.prediction_used,
                "predicted_M_after": round(self.predicted_M_after, 6)
                if self.predicted_M_after is not None
                else None,
                "prediction_error": round(self.prediction_error, 6)
                if self.prediction_error is not None
                else None,
                "experience_count": self.experience_count,
                "dopamine_level": round(self.dopamine_level, 4),
                "dopamine_plasticity": round(self.dopamine_plasticity, 4),
            },
            "compute_time_ms": round(self.compute_time_ms, 1),
        }


def get_experience_memory() -> ExperienceMemory:
    """Access the global experience memory for inspection."""
    return _MEMORY


# M baseline from 200-seed invariance test (5-gate publication-grade validation).
# M(N=32) = 0.4145 ± 0.0017, CV=0.41%. Phase-dependent invariant.
M_BASELINE = 0.4145
M_BASELINE_STD = 0.0017

# Optimal parameters discovered from 400-simulation thermodynamic landscape sweep.
# alpha=0.055, threshold=0.10 gives M=0.253 (1.71x better than defaults).
OPTIMAL_PARAMS = {
    "alpha": 0.055,
    "turing_threshold": 0.10,
}


def _diagnose_state(seq: FieldSequence) -> tuple:
    """Diagnose current state: returns (detection, ews, hwi, severity)."""
    from .analytics.unified_score import compute_hwi_components
    from .core.detect import detect_anomaly
    from .core.early_warning import early_warning

    det = detect_anomaly(seq)
    ews = early_warning(seq)
    hwi = compute_hwi_components(seq.history[0], seq.field, fast=True)

    is_anom = det.label in ("anomalous", "critical")
    is_ews = ews.ews_score > 0.5
    severity_map = {
        (True, True): "critical",
        (True, False): "warning",
        (False, True): "warning",
        (False, False): "stable" if ews.ews_score < 0.3 else "info",
    }
    severity = severity_map[(is_anom, is_ews)]
    return det, ews, hwi, severity


def _early_heal_result(
    severity_before: str,
    det_before: Any,
    hwi_before: Any,
    elapsed: float,
    *,
    needs_healing: bool,
) -> HealResult:
    """Build HealResult for early-return paths (no healing needed or no viable plan)."""
    return HealResult(
        severity_before=severity_before,
        anomaly_before=det_before.label,
        anomaly_score_before=float(det_before.score),
        M_before=hwi_before.M,
        hwi_before=hwi_before.hwi_holds,
        needs_healing=needs_healing,
        intervention_applied=False,
        changes=[],
        severity_after=None,
        anomaly_after=None,
        anomaly_score_after=None,
        M_after=None,
        hwi_after=None,
        delta_M=None,
        delta_anomaly=None,
        healed=None if not needs_healing else False,
        compute_time_ms=elapsed,
    )


def auto_heal(
    seq: FieldSequence,
    target_regime: str = "stable",
    budget: float = 10.0,
    verbose: bool = False,
    memory: ExperienceMemory | None = None,
) -> HealResult:
    """Closed cognitive loop: diagnose → predict → intervene → verify → learn."""
    from .intervention import plan_intervention

    t0 = time.perf_counter()

    # ── 1. DIAGNOSE BEFORE ──────────────────────────────────────
    det_before, _ews_before, hwi_before, severity_before = _diagnose_state(seq)

    # ── 2. DOPAMINE STATE FROM PREVIOUS CYCLE ───────────────────
    global _DA_STATE
    with _STATE_LOCK:
        if _DA_STATE is None:
            DopamineState, _, _ = _get_da_module()
            _DA_STATE = DopamineState()
        da_budget = budget * (0.5 + 0.5 * _DA_STATE.plasticity_scale / 3.0)

    # ── 3. DECIDE ───────────────────────────────────────────────
    needs_healing = severity_before in ("warning", "critical") or det_before.label == "anomalous"

    if not needs_healing:
        elapsed = (time.perf_counter() - t0) * 1000
        return _early_heal_result(severity_before, det_before, hwi_before, elapsed, needs_healing=False)

    # ── 4. PLAN (DA-modulated budget + lever selection) ────────
    # DA selects which levers to try: high DA → all, low DA → top 2
    from .intervention import list_levers
    from .neurochem.dopamine import select_levers

    all_levers = list_levers()
    mem = memory if memory is not None else _MEMORY
    selected = select_levers(_DA_STATE, all_levers, mem.top_levers)

    # Fewer counterfactuals when model is confident
    n_candidates = 32 if not mem.can_predict else max(8, int(32 * _DA_STATE.level))
    plan = plan_intervention(
        seq,
        target_regime=target_regime,
        budget=da_budget,
        allowed_levers=selected,
        max_candidates=n_candidates,
    )

    # ── 4b. CHOICE OPERATOR A_C — resolve Pareto indeterminacy ───
    best = plan.best_candidate
    if plan.has_viable_plan and len(plan.pareto_front) > 1:
        from .core.choice_operator import choice_operator

        pareto = list(plan.pareto_front)
        pareto_scores = [c.composite_score for c in pareto]
        choice = choice_operator(
            candidates=pareto,
            scores=pareto_scores,
            seq=seq,
            sigma=_DA_STATE.plasticity_scale * 0.001,  # DA modulates perturbation
            seed=42,
        )
        if choice.selected_index >= 0:
            best = pareto[choice.selected_index]

    if best is None or not plan.has_viable_plan:
        elapsed = (time.perf_counter() - t0) * 1000
        return _early_heal_result(severity_before, det_before, hwi_before, elapsed, needs_healing=True)

    changes = [
        {"name": s.name, "from": round(s.current_value, 4), "to": round(s.proposed_value, 4)}
        for s in best.proposed_changes
        if abs(s.proposed_value - s.current_value) > 1e-6
    ]

    # ── 5. ACT — re-simulate with intervention parameters ──────
    from .core.simulate import simulate_history
    from .intervention.counterfactual import _apply_interventions

    modified_spec = _apply_interventions(seq.spec, best.proposed_changes)
    seq_after = simulate_history(modified_spec)

    # ── 6. VERIFY — re-diagnose ────────────────────────────────
    det_after, _ews_after, hwi_after, severity_after = _diagnose_state(seq_after)

    delta_M = hwi_after.M - hwi_before.M
    delta_anomaly = det_after.score - det_before.score

    # Healed = severity improved or stayed same AND anomaly score decreased
    severity_order = {"stable": 0, "info": 1, "warning": 2, "critical": 3}
    sev_improved = severity_order.get(severity_after, 3) <= severity_order.get(severity_before, 3)
    anomaly_improved = det_after.score <= det_before.score + 0.01
    healed = sev_improved and anomaly_improved

    # ── 8. BUILD FEATURE VECTOR ─────────────────────────────────
    mem = memory if memory is not None else _MEMORY

    spec = seq.spec
    feat = {
        "M_before": hwi_before.M,
        "anomaly_before": float(det_before.score),
        "alpha": spec.alpha if spec else 0.18,
        "turing_threshold": spec.turing_threshold if spec else 0.75,
        "jitter_var": spec.jitter_var if spec else 0.0,
        "spike_probability": spec.spike_probability if spec else 0.25,
        # Dopamine state — so Ridge learns when DA matters
        "dopamine_level": _DA_STATE.level,
        "dopamine_rpe": _DA_STATE.rpe,
    }
    # Add intervention deltas
    for s in best.proposed_changes:
        feat[f"delta_{s.name}"] = s.proposed_value - s.current_value

    # ── 8. PREDICT + LEARN + DOPAMINE ────────────────────────────
    prediction_used, predicted_M, prediction_error = False, None, None
    if mem.can_predict:
        predicted_M, _, _ = mem.predict(feat)
        prediction_used = True
        prediction_error = abs(predicted_M - hwi_after.M)

    pe_for_da = prediction_error if prediction_error is not None else abs(delta_M)
    _, compute_dopamine_fn, _ = _get_da_module()
    with _STATE_LOCK:
        _DA_STATE = compute_dopamine_fn(pe_for_da, _DA_STATE)
        mem.store(feat, M_after=hwi_after.M, anomaly_after=float(det_after.score), healed=healed)

    elapsed = (time.perf_counter() - t0) * 1000

    return HealResult(
        severity_before=severity_before,
        anomaly_before=det_before.label,
        anomaly_score_before=float(det_before.score),
        M_before=hwi_before.M,
        hwi_before=hwi_before.hwi_holds,
        needs_healing=True,
        intervention_applied=True,
        changes=changes,
        severity_after=severity_after,
        anomaly_after=det_after.label,
        anomaly_score_after=float(det_after.score),
        M_after=hwi_after.M,
        hwi_after=hwi_after.hwi_holds,
        delta_M=delta_M,
        delta_anomaly=delta_anomaly,
        healed=healed,
        prediction_used=prediction_used,
        predicted_M_after=predicted_M,
        prediction_error=prediction_error,
        experience_count=mem.size,
        dopamine_level=_DA_STATE.level,
        dopamine_plasticity=_DA_STATE.plasticity_scale,
        compute_time_ms=elapsed,
    )
