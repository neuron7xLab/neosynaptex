"""
CFP/ДІЙ Protocol Engine — T0→T3 Experiment Controller
=====================================================
Manages the four-phase cognitive field experiment:
  T0 (baseline) → T1 (onset) → T2 (deep co-adapt) → T3 (recovery)

Tracks subjects, sessions, metrics evolution, and phase transitions.

Author: Yaroslav Vasylenko (neuron7xLab)
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import numpy as np

from .metrics import (
    CRRResult,
    CognitiveScore,
    classify_crr,
    cognitive_score,
    compute_crr,
    cpr,
    dependency_index,
    mtld,
    tokenize,
)


class Phase(str, Enum):
    T0 = "T0_baseline"
    T1 = "T1_onset"
    T2 = "T2_deep"
    T3 = "T3_recovery"


@dataclass
class TaskResult:
    """Single task execution record within a phase."""

    task_id: str
    phase: str
    text_response: str  # Subject's written response
    complexity_rating: float  # TC: 0-10 rated by evaluator
    hypotheses_count: int  # DT: independent hypotheses generated
    time_seconds: float  # TTR
    ai_assisted: bool  # Whether AI was used
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class PhaseSnapshot:
    """Aggregated metrics for one phase of one subject."""

    phase: str
    ld: float  # MTLD across all texts in phase
    tc_mean: float  # Mean task complexity
    dt_mean: float  # Mean divergent thinking
    cpr_value: float  # CPR across all texts
    di: float  # Dependency index (0 for T0/T3)
    n_tasks: int
    ttr_mean: float  # Mean time to resolution
    score: CognitiveScore = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.score is None:
            self.score = cognitive_score(self.ld, self.tc_mean, self.dt_mean)


@dataclass
class Subject:
    """A participant in the CFP experiment."""

    subject_id: str
    domain: str = "science"  # science / engineering / business / creative
    tasks: list[TaskResult] = field(default_factory=list)
    phase_snapshots: dict[str, PhaseSnapshot] = field(default_factory=dict)
    crr_result: Optional[CRRResult] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_task(self, result: TaskResult) -> None:
        self.tasks.append(result)

    def compute_phase_snapshot(self, phase: Phase) -> PhaseSnapshot:
        """Aggregate all tasks in a given phase."""
        phase_tasks = [t for t in self.tasks if t.phase == phase.value]
        if not phase_tasks:
            return PhaseSnapshot(
                phase=phase.value,
                ld=0,
                tc_mean=0,
                dt_mean=0,
                cpr_value=0,
                di=0,
                n_tasks=0,
                ttr_mean=0,
            )

        # Concatenate all text responses for LD and CPR
        all_text = " ".join(t.text_response for t in phase_tasks)
        tokens = tokenize(all_text)

        ld_val = mtld(tokens)
        cpr_val = cpr(tokens)
        tc_mean = float(np.mean([t.complexity_rating for t in phase_tasks]))
        dt_mean = float(np.mean([t.hypotheses_count for t in phase_tasks]))
        ttr_mean = float(np.mean([t.time_seconds for t in phase_tasks]))

        # DI: only meaningful in T1/T2
        ai_count = sum(1 for t in phase_tasks if t.ai_assisted)
        di_val = dependency_index(ai_count, len(phase_tasks))

        snap = PhaseSnapshot(
            phase=phase.value,
            ld=ld_val,
            tc_mean=tc_mean,
            dt_mean=dt_mean,
            cpr_value=cpr_val,
            di=di_val,
            n_tasks=len(phase_tasks),
            ttr_mean=ttr_mean,
        )
        self.phase_snapshots[phase.value] = snap
        return snap

    def compute_crr(self) -> CRRResult:
        """Compute CRR after T0 and T3 phases are complete."""
        if Phase.T0.value not in self.phase_snapshots:
            self.compute_phase_snapshot(Phase.T0)
        if Phase.T3.value not in self.phase_snapshots:
            self.compute_phase_snapshot(Phase.T3)

        snap_t0 = self.phase_snapshots[Phase.T0.value]
        snap_t3 = self.phase_snapshots[Phase.T3.value]

        # CPR from T2 if available
        cpr_t2 = 0.0
        if Phase.T2.value in self.phase_snapshots:
            cpr_t2 = self.phase_snapshots[Phase.T2.value].cpr_value

        self.crr_result = compute_crr(
            s_t0=snap_t0.score,
            s_t3=snap_t3.score,
            cpr_t0=snap_t0.cpr_value,
            cpr_t2=cpr_t2,
            cpr_t3=snap_t3.cpr_value,
        )
        return self.crr_result


class CFPExperiment:
    """Controller for a full CFP/ДІЙ experiment run."""

    def __init__(self, experiment_id: str = "cfp_v2_pilot") -> None:
        self.experiment_id = experiment_id
        self.subjects: dict[str, Subject] = {}
        self.created_at = time.time()

    def add_subject(self, subject_id: str, domain: str = "science") -> Subject:
        subj = Subject(subject_id=subject_id, domain=domain)
        self.subjects[subject_id] = subj
        return subj

    def record_task(
        self,
        subject_id: str,
        task_id: str,
        phase: Phase,
        text_response: str,
        complexity_rating: float,
        hypotheses_count: int,
        time_seconds: float,
        ai_assisted: bool = False,
    ) -> TaskResult:
        """Record a single task result for a subject."""
        if subject_id not in self.subjects:
            self.add_subject(subject_id)

        result = TaskResult(
            task_id=task_id,
            phase=phase.value,
            text_response=text_response,
            complexity_rating=complexity_rating,
            hypotheses_count=hypotheses_count,
            time_seconds=time_seconds,
            ai_assisted=ai_assisted,
        )
        self.subjects[subject_id].add_task(result)
        return result

    def compute_all_crr(self) -> dict[str, CRRResult]:
        """Compute CRR for all subjects with T0 and T3 data."""
        results = {}
        for sid, subj in self.subjects.items():
            t0_tasks = [t for t in subj.tasks if t.phase == Phase.T0.value]
            t3_tasks = [t for t in subj.tasks if t.phase == Phase.T3.value]
            if t0_tasks and t3_tasks:
                for phase in Phase:
                    subj.compute_phase_snapshot(phase)
                results[sid] = subj.compute_crr()
        return results

    def crr_distribution(self) -> np.ndarray:
        """Get CRR values for all completed subjects."""
        crrs = self.compute_all_crr()
        return np.array([r.crr for r in crrs.values()])

    def summary(self) -> dict[str, Any]:
        """Experiment summary with state distribution."""
        crrs = self.compute_all_crr()
        if not crrs:
            return {"n": 0, "status": "NO_DATA"}

        values = np.array([r.crr for r in crrs.values()])
        states = [r.state for r in crrs.values()]
        state_counts = {s: states.count(s) for s in set(states)}

        return {
            "experiment_id": self.experiment_id,
            "n_subjects": len(crrs),
            "crr_mean": round(float(np.mean(values)), 4),
            "crr_std": round(float(np.std(values)), 4),
            "crr_median": round(float(np.median(values)), 4),
            "state_distribution": state_counts,
            "masked_degradation_count": sum(1 for r in crrs.values() if r.is_masked_degradation()),
        }

    def export_json(self, path: Path) -> None:
        """Export full experiment data."""
        data = {
            "experiment_id": self.experiment_id,
            "created_at": self.created_at,
            "n_subjects": len(self.subjects),
            "summary": self.summary(),
            "subjects": {},
        }
        for sid, subj in self.subjects.items():
            data["subjects"][sid] = {
                "domain": subj.domain,
                "n_tasks": len(subj.tasks),
                "phases": {
                    k: {
                        "ld": v.ld,
                        "tc": v.tc_mean,
                        "dt": v.dt_mean,
                        "cpr": v.cpr_value,
                        "di": v.di,
                        "s": v.score.s,
                    }
                    for k, v in subj.phase_snapshots.items()
                },
                "crr": subj.crr_result.crr if subj.crr_result else None,
                "state": subj.crr_result.state if subj.crr_result else None,
                "cpr_discriminator": (
                    subj.crr_result.cpr_discriminator if subj.crr_result else None
                ),
            }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
