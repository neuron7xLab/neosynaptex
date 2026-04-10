"""Verdict aggregation + reproducibility hash — spec §VIII & IX."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from formal.dcvp.protocol import (
    ALIGNMENT_SENSITIVITY_LIMIT,
    CASCADE_LAG_CV_LIMIT,
    GRANGER_P_LIMIT,
    JITTER_SURVIVAL_FLOOR,
    TE_Z_FLOOR,
    CausalityRow,
    DCVPConfig,
    DCVPVerdict,
    PerturbationSpec,
)

__all__ = [
    "score_row",
    "aggregate_verdict",
    "reproducibility_hash",
    "code_hash",
    "data_hash",
]


def score_row(
    seed: int,
    perturbation: PerturbationSpec,
    granger_p: float,
    granger_lag: int,
    te_obs: float,
    te_null_mean: float,
    te_null_std: float,
    cascade_mean_lag: int,
    cascade_cv: float,
    jitter_surv: float,
    alignment_sens: float,
    effect: float,
    drift: float,
) -> CausalityRow:
    """Score a single (seed, perturbation) row against spec §V."""
    te_z = (te_obs - te_null_mean) / (te_null_std + 1e-12)
    reasons: list[str] = []
    if not (granger_p < GRANGER_P_LIMIT):
        reasons.append(f"granger_p={granger_p:.4f}≥{GRANGER_P_LIMIT}")
    if not (te_z > TE_Z_FLOOR):
        reasons.append(f"te_z={te_z:.2f}≤{TE_Z_FLOOR}")
    if not (cascade_cv < CASCADE_LAG_CV_LIMIT):
        reasons.append(f"cascade_cv={cascade_cv:.2f}≥{CASCADE_LAG_CV_LIMIT}")
    if not (jitter_surv >= JITTER_SURVIVAL_FLOOR):
        reasons.append(f"jitter_surv={jitter_surv:.2f}<{JITTER_SURVIVAL_FLOOR}")
    if not (effect > drift):
        reasons.append(f"effect={effect:.3f}≤drift={drift:.3f}")
    if not (alignment_sens < ALIGNMENT_SENSITIVITY_LIMIT):
        reasons.append(f"align_sens={alignment_sens:.2f}≥{ALIGNMENT_SENSITIVITY_LIMIT}")
    return CausalityRow(
        seed=seed,
        perturbation=perturbation,
        granger_p=granger_p,
        granger_lag=granger_lag,
        te_z=float(te_z),
        te_value=float(te_obs),
        cascade_lag=cascade_mean_lag,
        cascade_lag_cv=cascade_cv,
        jitter_survival=jitter_surv,
        alignment_sensitivity=alignment_sens,
        effect_size=effect,
        baseline_drift=drift,
        passes=not reasons,
        fail_reasons=tuple(reasons),
    )


def aggregate_verdict(
    rows: tuple[CausalityRow, ...],
    controls_flagged: dict[str, bool],
) -> DCVPVerdict:
    """Collapse all rows + controls into final label."""
    if not rows:
        return DCVPVerdict(
            label="ARTIFACT",
            positive_frac=0.0,
            controls_all_failed=all(not v for v in controls_flagged.values()),
            reasons=("no_rows",),
        )
    n_pass = sum(1 for r in rows if r.passes)
    frac = n_pass / len(rows)
    controls_clean = all(not flagged for flagged in controls_flagged.values())
    reasons: list[str] = []
    if not controls_clean:
        bad = [k for k, v in controls_flagged.items() if v]
        reasons.append("contaminating_controls=" + ",".join(bad))
    if frac == 1.0 and controls_clean:
        return DCVPVerdict(
            label="CAUSAL_INVARIANT",
            positive_frac=1.0,
            controls_all_failed=True,
            reasons=(),
        )
    if frac >= 0.5 and controls_clean:
        reasons.append(f"partial_pass_frac={frac:.2f}")
        return DCVPVerdict(
            label="CONDITIONAL",
            positive_frac=frac,
            controls_all_failed=True,
            reasons=tuple(reasons),
        )
    return DCVPVerdict(
        label="ARTIFACT",
        positive_frac=frac,
        controls_all_failed=controls_clean,
        reasons=tuple(reasons) if reasons else (f"pass_frac={frac:.2f}<0.5",),
    )


def _canonical_config(cfg: DCVPConfig) -> dict[str, object]:
    d = asdict(cfg)
    d["perturbations"] = [asdict(p) for p in cfg.perturbations]
    d["pair"] = asdict(cfg.pair)
    d["seeds"] = list(cfg.seeds)
    return d


def reproducibility_hash(
    cfg: DCVPConfig,
    code_hex: str,
    data_hex: str,
) -> str:
    """sha256 over (config, code, data) — spec §IX."""
    payload = {
        "config": _canonical_config(cfg),
        "code": code_hex,
        "data": data_hex,
    }
    blob = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def code_hash(module_paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(module_paths):
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()


def data_hash(gamma_a: dict[int, tuple[float, ...]], gamma_b: dict[int, tuple[float, ...]]) -> str:
    h = hashlib.sha256()
    for seed in sorted(gamma_a):
        h.update(f"A|{seed}|".encode())
        h.update(np.asarray(gamma_a[seed], dtype=np.float64).tobytes())
    for seed in sorted(gamma_b):
        h.update(f"B|{seed}|".encode())
        h.update(np.asarray(gamma_b[seed], dtype=np.float64).tobytes())
    return h.hexdigest()
