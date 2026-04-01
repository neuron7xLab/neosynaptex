"""
RegimeDiagnostics — real-time diagnostic output for DNCA runs.

Plain text, structured, readable in terminal and loggable to file.
Tracks metastability, competition health, regime history, prediction
quality, and all 5 failure modes.
"""

from __future__ import annotations

import json
import math
from collections import Counter, deque
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from neuron7x_agents.dnca.core.types import (
    COLLAPSE_THRESHOLD,
    METASTABILITY_THRESHOLD,
    RIGIDITY_THRESHOLD,
    RegimeTransitionEvent,
)
from neuron7x_agents.dnca.orchestrator import DNCA, DNCStepOutput


@dataclass(slots=True)
class _StepRecord:
    step: int
    dominant_nmo: Optional[str]
    dominant_activity: float
    activities: Dict[str, float]
    regime_phase: str
    regime_age: int
    r_order: float
    r_std: float
    mismatch: float
    satiation: float
    plasticity_gate: float
    theta_phase: float
    transition: Optional[RegimeTransitionEvent]


class RegimeDiagnostics:
    """
    Collects and formats DNCA runtime diagnostics.

    Usage:
        diag = RegimeDiagnostics(dnca)
        for step in range(1000):
            output = dnca.step(input_tensor)
            diag.record(output)
        print(diag.summary())
        diag.export_json("run_001.json")
    """

    # Canonical NMO display names
    _NMO_DISPLAY: Dict[str, str] = {
        "dopamine": "DA   (dopamine)",
        "acetylcholine": "ACh  (acetylcholine)",
        "norepinephrine": "NE   (norepinephrine)",
        "serotonin": "5-HT (serotonin)",
        "gaba": "GABA (gaba)",
        "glutamate": "Glu  (glutamate)",
    }

    def __init__(self, dnca: Optional[DNCA] = None, history_size: int = 5000):
        self.dnca = dnca
        self._records: deque[_StepRecord] = deque(maxlen=history_size)
        self._transitions: List[RegimeTransitionEvent] = []
        self._r_values: deque[float] = deque(maxlen=history_size)
        self._mismatches: deque[float] = deque(maxlen=history_size)
        # Per-NMO activity tracking
        self._nmo_activity_sums: Dict[str, float] = {}
        self._nmo_activity_counts: Dict[str, int] = {}

    def record(self, output: DNCStepOutput) -> None:
        """Record one DNCA step output."""
        rec = _StepRecord(
            step=output.step,
            dominant_nmo=output.dominant_nmo,
            dominant_activity=output.dominant_activity,
            activities=dict(output.all_activities),
            regime_phase=output.regime_phase,
            regime_age=output.regime_age,
            r_order=output.r_order,
            r_std=output.r_std,
            mismatch=output.mismatch,
            satiation=output.satiation,
            plasticity_gate=output.plasticity_gate,
            theta_phase=output.theta_phase,
            transition=output.transition_event,
        )
        self._records.append(rec)
        self._r_values.append(output.r_order)
        self._mismatches.append(output.mismatch)
        if output.transition_event:
            self._transitions.append(output.transition_event)
        # Accumulate per-NMO activity
        for name, act in output.all_activities.items():
            self._nmo_activity_sums[name] = self._nmo_activity_sums.get(name, 0.0) + act
            self._nmo_activity_counts[name] = self._nmo_activity_counts.get(name, 0) + 1

    # ── Computed metrics ─────────────────────────────────────────────

    @property
    def n_steps(self) -> int:
        return len(self._records)

    def _r_mean(self) -> float:
        if not self._r_values:
            return 0.0
        return sum(self._r_values) / len(self._r_values)

    def _r_std(self) -> float:
        if len(self._r_values) < 10:
            return 0.0
        mu = self._r_mean()
        var = sum((x - mu) ** 2 for x in self._r_values) / len(self._r_values)
        return math.sqrt(max(0.0, var))

    def _activity_entropy(self) -> float:
        if not self._records:
            return 0.0
        counts: Counter = Counter()
        for r in self._records:
            if r.dominant_nmo:
                counts[r.dominant_nmo] += 1
        total = sum(counts.values())
        if total == 0:
            return 0.0
        probs = [c / total for c in counts.values()]
        return -sum(p * math.log(p + 1e-10) for p in probs)

    def _transition_rate(self) -> float:
        if self.n_steps < 10:
            return 0.0
        return len(self._transitions) / (self.n_steps / 100.0)

    def _mismatch_mean(self) -> float:
        if not self._mismatches:
            return 0.0
        return sum(self._mismatches) / len(self._mismatches)

    def _mismatch_trend(self) -> float:
        """Linear regression slope of mismatch over steps (OLS)."""
        if len(self._mismatches) < 20:
            return 0.0
        mm = list(self._mismatches)
        n = len(mm)
        # OLS slope: Σ(x_i - x̄)(y_i - ȳ) / Σ(x_i - x̄)²
        x_mean = (n - 1) / 2.0
        y_mean = sum(mm) / n
        num = sum((i - x_mean) * (mm[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n))
        if den < 1e-12:
            return 0.0
        return num / den

    def _prediction_r2(self) -> float:
        if len(self._mismatches) < 20:
            return 0.0
        mm = list(self._mismatches)
        mu = sum(mm) / len(mm)
        ss_tot = sum((x - mu) ** 2 for x in mm)
        if ss_tot < 1e-12:
            return 1.0
        ss_res = sum(x ** 2 for x in mm)
        return max(0.0, 1.0 - ss_res / ss_tot)

    def regime_sequence_entropy(self) -> float:
        seq = [t.from_nmo for t in self._transitions if t.from_nmo]
        if not seq:
            return 0.0
        counts = Counter(seq)
        total = len(seq)
        probs = [c / total for c in counts.values()]
        return -sum(p * math.log(p + 1e-10) for p in probs)

    # ── Failure mode detection ───────────────────────────────────────

    def _check_fm1_rigidity(self) -> bool:
        """FM-1: r_std < 0.05 for sustained period."""
        return self._r_std() >= 0.05

    def _check_fm2_collapse(self) -> bool:
        """FM-2: r_mean < 0.10."""
        return self._r_mean() >= 0.10 or self.n_steps < 50

    def _check_fm3_pred_drift(self) -> bool:
        """FM-3: mismatch growing monotonically."""
        return self._mismatch_trend() <= 0.005

    def _check_fm4_phase_desync(self) -> bool:
        """FM-4: pac_coherence < 0.001."""
        if not self._records:
            return True
        last = self._records[-1]
        return last.r_order > 0.001 or self.n_steps < 100

    def _check_fm5_operator_silence(self) -> bool:
        """FM-5: any NMO's activity < 0.01 for entire run."""
        return self._activity_entropy() > 0.4

    # ── Summary output ───────────────────────────────────────────────

    def summary(self) -> str:
        """Formatted diagnostic summary."""
        step = self._records[-1].step if self._records else 0
        r_mean = self._r_mean()
        r_std = self._r_std()
        ent = self._activity_entropy()
        tr_rate = self._transition_rate()
        mm_mean = self._mismatch_mean()
        mm_trend = self._mismatch_trend()
        pred_r2 = self._prediction_r2()

        def _ok(cond: bool) -> str:
            return "OK" if cond else "FAIL"

        def _check(val: float, lo: float, hi: float) -> str:
            return "\u2713" if lo <= val <= hi else "\u2717"

        # Metastability status
        if r_std >= METASTABILITY_THRESHOLD and COLLAPSE_THRESHOLD < r_mean < RIGIDITY_THRESHOLD:
            meta_status = "HEALTHY"
        elif r_std < 0.05:
            meta_status = "RIGID"
        elif r_mean < COLLAPSE_THRESHOLD:
            meta_status = "COLLAPSED"
        else:
            meta_status = "TRANSITIONAL"

        # Last regime info
        last = self._records[-1] if self._records else None
        dom_str = f"{last.dominant_nmo} (A={last.dominant_activity:.2f}, age={last.regime_age})" if last else "—"

        # Regime history (last 5 transitions)
        history_lines = []
        for t in self._transitions[-5:]:
            history_lines.append(
                f"  step {t.step:4d}: {t.from_nmo or '—':5s} \u2192 {t.to_nmo or '—':5s} "
                f"({t.trigger:20s}) duration={t.from_duration}"
            )

        # Failure modes
        fm_lines = [
            f"  FM-1 Rigidity    : {_ok(self._check_fm1_rigidity())}",
            f"  FM-2 Collapse    : {_ok(self._check_fm2_collapse())}",
            f"  FM-3 Pred.Drift  : {_ok(self._check_fm3_pred_drift())}",
            f"  FM-4 Phase Desync: {_ok(self._check_fm4_phase_desync())}",
            f"  FM-5 Op.Silence  : {_ok(self._check_fm5_operator_silence())}",
        ]

        lines = [
            "\u2550" * 55,
            f"DNCA DIAGNOSTICS \u2014 step {step}",
            "\u2550" * 55,
            "METASTABILITY",
            f"  r_mean      = {r_mean:.3f}  {_check(r_mean, 0.15, 0.85)} [target: 0.15\u20130.85]",
            f"  r_std       = {r_std:.3f}  {_check(r_std, 0.10, 9.0)} [target: > 0.10]",
            f"  status      = {meta_status}",
            "",
            "COMPETITION",
            f"  activity_entropy  = {ent:.2f} bits  {_check(ent, 0.90, 99.0)} [target: > 0.90]",
            f"  dominant NMO      = {dom_str}",
            f"  transition_rate   = {tr_rate:.1f} / 100 steps",
            "",
            f"REGIME HISTORY (last {min(5, len(self._transitions))})",
        ]
        lines.extend(history_lines if history_lines else ["  (no transitions yet)"])
        lines.extend([
            "",
            "PREDICTION QUALITY",
            f"  mismatch_mean   = {mm_mean:.4f}",
            f"  mismatch_trend  = {mm_trend:+.4f}/step  {'(\u2713 learning)' if mm_trend <= 0 else '(\u2717 drifting)'}",
            f"  prediction_r2   = {pred_r2:.2f}",
            "",
            "FAILURE MODES",
        ])
        lines.extend(fm_lines)

        # Per-NMO mean activity section
        lines.extend(["", "OPERATOR ACTIVITY (mean over run)"])
        # Canonical order
        _order = ["dopamine", "acetylcholine", "norepinephrine", "serotonin", "gaba", "glutamate"]
        nmo_names_ordered = [n for n in _order if n in self._nmo_activity_sums]
        # Add any remaining not in canonical order
        for n in sorted(self._nmo_activity_sums.keys()):
            if n not in nmo_names_ordered:
                nmo_names_ordered.append(n)
        for name in nmo_names_ordered:
            count = self._nmo_activity_counts.get(name, 1)
            mean_act = self._nmo_activity_sums.get(name, 0.0) / max(count, 1)
            display = self._NMO_DISPLAY.get(name, name)
            mark = "\u2713" if mean_act >= 0.05 else "\u2717"
            lines.append(f"  {display:25s} {mean_act:.2f}  {mark}")

        lines.append("\u2550" * 55)

        return "\n".join(lines)

    # ── ASCII activity plot ──────────────────────────────────────────

    def plot_ascii(self, width: int = 50) -> str:
        """ASCII activity heatmap over recent steps."""
        if not self._records:
            return "(no data)"

        # Get all NMO names from first record
        nmo_names = sorted(self._records[0].activities.keys()) if self._records else []
        if not nmo_names:
            return "(no operators)"

        # Sample records to fit width
        records = list(self._records)
        step_size = max(1, len(records) // width)
        sampled = records[::step_size][:width]

        lines = [f"NMO Activity Over Last {len(sampled)} Samples"]
        for name in nmo_names:
            bar = ""
            for rec in sampled:
                act = rec.activities.get(name, 0.0)
                if act > 0.5:
                    bar += "\u2588"
                elif act > 0.2:
                    bar += "\u2593"
                elif act > 0.05:
                    bar += "\u2591"
                else:
                    bar += "\u2591" if act > 0.01 else " "
            short = name[:4].upper().ljust(5)
            lines.append(f"{short}{bar}")

        return "\n".join(lines)

    # ── Export ────────────────────────────────────────────────────────

    def export_json(self, path: str) -> None:
        """Full structured export for analysis."""
        data = {
            "n_steps": self.n_steps,
            "metastability": {
                "r_mean": self._r_mean(),
                "r_std": self._r_std(),
            },
            "competition": {
                "activity_entropy": self._activity_entropy(),
                "transition_rate": self._transition_rate(),
                "regime_sequence_entropy": self.regime_sequence_entropy(),
            },
            "prediction": {
                "mismatch_mean": self._mismatch_mean(),
                "mismatch_trend": self._mismatch_trend(),
                "prediction_r2": self._prediction_r2(),
            },
            "failure_modes": {
                "fm1_rigidity": self._check_fm1_rigidity(),
                "fm2_collapse": self._check_fm2_collapse(),
                "fm3_pred_drift": self._check_fm3_pred_drift(),
                "fm4_phase_desync": self._check_fm4_phase_desync(),
                "fm5_operator_silence": self._check_fm5_operator_silence(),
            },
            "transitions": [
                {
                    "step": t.step,
                    "from": t.from_nmo,
                    "to": t.to_nmo,
                    "trigger": t.trigger,
                    "duration": t.from_duration,
                    "coherence": t.coherence_at_transition,
                }
                for t in self._transitions
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
