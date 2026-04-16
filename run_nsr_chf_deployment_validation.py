#!/usr/bin/env python3
# ruff: noqa: E501 -- markdown report template carries long claim lines.
"""NSR-CHF Deployment Validation (Point 5)
==========================================
2026-04-16 | NeoSynaptex

Consumes the v1.3 descriptive-branch output and produces the three
deployment-readiness metrics pre-registered by the user:

    1. AUROC / AUPRC         — does the signal separate the classes?
    2. Calibration            — can we trust the probability, not just
                                the ranking? (Brier + reliability curve)
    3. Threshold stability    — does the operating point survive
                                leave-one-subject-out cross-validation?

CONTRACT — verdict table
------------------------
    DESCRIPTIVE_DISCRIMINATOR_VALID   → this script may run.
    DESCRIPTIVE_DISCRIMINATOR_UNSTABLE → this script exits with
        DEPLOYMENT_BLOCKED_BY_DESCRIPTIVE_UNSTABLE and writes an
        explanatory report. No deployment metrics are reported.
    (absent results.json)             → IMPLEMENTATION_BLOCKED.

No threshold tuning is performed at runtime. Thresholds are pinned in
``DEPLOYMENT_GATES`` and frozen in the result hash.

Epistemic position — what this script CAN claim
  * A classifier trained on (h(q=2), Δh) separates NSR from CHF on
    PhysioNet NSR2DB + CHFDB under the fixed v1.3 preprocessing.
  * If AUROC and Brier both pass gate AND threshold sign is stable
    under LOSO, the discriminator is deployment-ready on THIS cohort.
Epistemic position — what this script CANNOT claim
  * External cohort replication (Point 6).
  * Nonlinear dynamics, criticality, substrate-invariant claim.

Outputs
  evidence/replications/nsr_chf_deployment_validation/results.json
  evidence/replications/nsr_chf_deployment_validation/DEPLOYMENT_REPORT.md
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

# ---------------------------------------------------------------------------
# Pre-registered gates (deployment-readiness bar, NOT tunable)
# ---------------------------------------------------------------------------
DEPLOYMENT_GATES: dict[str, float] = {
    "auroc_min": 0.80,  # decision-quality floor
    "auprc_min": 0.75,  # precision-aware companion to AUROC
    "brier_max": 0.20,  # calibration: lower is better
    "threshold_loso_sign_stable": 1.0,  # all LOSO folds must agree on class order
    "threshold_loso_range_max": 0.20,  # decision-threshold spread across LOSO folds
}

PROTOCOL_VER = "1.0.0"
SEED = 42

INPUT_JSON = Path("evidence/replications/nsr_chf_descriptive/results.json")
OUTPUT_DIR = Path("evidence/replications/nsr_chf_deployment_validation")
RESULTS_JSON = OUTPUT_DIR / "results.json"
REPORT_MD = OUTPUT_DIR / "DEPLOYMENT_REPORT.md"


# ---------------------------------------------------------------------------
# Immutable config + hashing
# ---------------------------------------------------------------------------
def immutable_config() -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VER,
        "seed": SEED,
        "gates": DEPLOYMENT_GATES,
        "classifier": "LogisticRegression(solver='lbfgs', max_iter=1000)",
        "cv": "LeaveOneSubjectOut (LOSO)",
        "feature_set": ["h_q2", "delta_h"],
        "positive_class": "CHF",  # we label the PATHOLOGY as positive
    }


def _sha16(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()[:16]


def config_hash() -> str:
    return _sha16(json.dumps(immutable_config(), sort_keys=True).encode())


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------
def auprc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Average precision = area under precision-recall curve."""
    # Local import so sklearn is the only external dependency this file adds.
    from sklearn.metrics import average_precision_score

    return float(average_precision_score(y_true, y_score))


def reliability_curve(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10
) -> dict[str, list[float]]:
    """Manual reliability curve without sklearn's calibration_curve — keeps
    the call stable across sklearn versions and returns all three columns
    (bin_centre, observed_freq, bin_count) so the report can show sparse bins.
    """
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    centres: list[float] = []
    observed: list[float] = []
    counts: list[int] = []
    for i in range(n_bins):
        mask = (y_prob >= edges[i]) & (
            y_prob < edges[i + 1] if i < n_bins - 1 else y_prob <= edges[i + 1]
        )
        k = int(mask.sum())
        counts.append(k)
        if k == 0:
            centres.append(float(0.5 * (edges[i] + edges[i + 1])))
            observed.append(float("nan"))
            continue
        centres.append(float(y_prob[mask].mean()))
        observed.append(float(y_true[mask].mean()))
    return {
        "bin_centre": centres,
        "observed_freq": observed,
        "bin_count": [float(c) for c in counts],
    }


def youden_threshold(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Youden's-J optimal decision threshold on the ROC curve."""
    from sklearn.metrics import roc_curve

    fpr, tpr, thresholds = roc_curve(y_true, y_score)
    j = tpr - fpr
    # sklearn can return +inf as the first threshold; skip it.
    valid = np.isfinite(thresholds)
    if not np.any(valid):
        return 0.5
    j_valid = j[valid]
    thresh_valid = thresholds[valid]
    return float(thresh_valid[int(np.argmax(j_valid))])


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------
def run_validation(features: np.ndarray, y_true: np.ndarray) -> dict[str, Any]:
    """Full-cohort + LOSO metrics with pre-registered gates."""
    n = len(y_true)

    # --- Full-cohort (training + scoring on the same data is fine for
    # a calibration diagnostic; per-fold metrics come from LOSO below) ---
    clf = LogisticRegression(solver="lbfgs", max_iter=1000, random_state=SEED)
    clf.fit(features, y_true)
    y_prob_in = clf.predict_proba(features)[:, 1]
    full_auroc = float(roc_auc_score(y_true, y_prob_in))
    full_auprc = auprc(y_true, y_prob_in)
    full_brier = float(brier_score_loss(y_true, y_prob_in))

    # --- Leave-one-subject-out ---
    y_prob_loso = np.empty(n, dtype=np.float64)
    loso_thresholds: list[float] = []
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        clf_i = LogisticRegression(solver="lbfgs", max_iter=1000, random_state=SEED)
        clf_i.fit(features[mask], y_true[mask])
        # Score the held-out subject
        y_prob_loso[i] = float(clf_i.predict_proba(features[i : i + 1])[0, 1])
        # Fold-level operating point computed on the training set only
        in_fold_prob = clf_i.predict_proba(features[mask])[:, 1]
        loso_thresholds.append(youden_threshold(y_true[mask], in_fold_prob))

    loso_auroc = float(roc_auc_score(y_true, y_prob_loso))
    loso_auprc = auprc(y_true, y_prob_loso)
    loso_brier = float(brier_score_loss(y_true, y_prob_loso))

    thr_arr = np.asarray(loso_thresholds, dtype=np.float64)
    thr_sign_stable = bool(
        np.all(thr_arr > 0.0)
        and np.all(thr_arr < 1.0)
        and (thr_arr.max() - thr_arr.min()) <= DEPLOYMENT_GATES["threshold_loso_range_max"]
    )

    # --- Reliability curve on the LOSO out-of-fold predictions ---
    reliability = reliability_curve(y_true, y_prob_loso, n_bins=10)

    # --- Gate evaluation (LOSO is the primary evidence) ---
    fail_codes: list[str] = []
    if loso_auroc < DEPLOYMENT_GATES["auroc_min"]:
        fail_codes.append(f"FAIL_AUROC::loso={loso_auroc:.3f}<{DEPLOYMENT_GATES['auroc_min']}")
    if loso_auprc < DEPLOYMENT_GATES["auprc_min"]:
        fail_codes.append(f"FAIL_AUPRC::loso={loso_auprc:.3f}<{DEPLOYMENT_GATES['auprc_min']}")
    if loso_brier > DEPLOYMENT_GATES["brier_max"]:
        fail_codes.append(f"FAIL_BRIER::loso={loso_brier:.3f}>{DEPLOYMENT_GATES['brier_max']}")
    if not thr_sign_stable:
        fail_codes.append(
            f"FAIL_THRESHOLD_STABILITY::range={float(thr_arr.max() - thr_arr.min()):.3f}"
        )

    verdict = "DEPLOYMENT_READY" if not fail_codes else "DEPLOYMENT_BLOCKED"

    return {
        "full_cohort": {
            "auroc": full_auroc,
            "auprc": full_auprc,
            "brier": full_brier,
            "n": int(n),
        },
        "loso": {
            "auroc": loso_auroc,
            "auprc": loso_auprc,
            "brier": loso_brier,
            "thresholds": [float(t) for t in thr_arr],
            "threshold_mean": float(thr_arr.mean()),
            "threshold_std": float(thr_arr.std(ddof=1)) if n > 1 else 0.0,
            "threshold_range": [float(thr_arr.min()), float(thr_arr.max())],
            "threshold_sign_stable": thr_sign_stable,
        },
        "reliability": reliability,
        "fail_codes": fail_codes,
        "VERDICT": verdict,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def write_report(output: dict[str, Any], path: Path) -> None:
    v = output["validation"]
    full = v["full_cohort"]
    loso = v["loso"]
    fails_md = "\n".join(f"- `{f}`" for f in v["fail_codes"]) if v["fail_codes"] else "— (none)"

    thr_row_lines = "\n".join(
        f"| subj {i + 1:02d} | {t:.3f} |" for i, t in enumerate(loso["thresholds"])
    )
    rel = output["validation"]["reliability"]
    rel_rows = "\n".join(
        f"| {c:.3f} | {o if np.isnan(o) else f'{o:.3f}'} | {int(n)} |"
        for c, o, n in zip(rel["bin_centre"], rel["observed_freq"], rel["bin_count"], strict=True)
    )
    if v["VERDICT"] == "DEPLOYMENT_READY":
        allowed_claims_md = (
            "1. (h(q=2), Δh) is deployment-ready as a descriptive CHF-vs-NSR "
            "classifier on PhysioNet under the fixed v1.3 preprocessing.\n"
            "2. Operating point is stable under leave-one-subject-out "
            "cross-validation.\n"
            "3. Calibration (Brier) is within the pre-registered gate."
        )
    else:
        allowed_claims_md = (
            "No deployment claim is admissible under this verdict. See fail codes."
        )
    next_action_md = (
        "Proceed to Point 6: external cohort replication (MIT-BIH Long-Term "
        "or equivalent holdout)."
        if v["VERDICT"] == "DEPLOYMENT_READY"
        else "Do NOT proceed to Point 6. Diagnose the failing gate(s) above; "
        "consider whether the descriptive branch itself needs re-examination "
        "before any deployment claim."
    )

    md = f"""\
# NSR-CHF Deployment Validation Report
**Protocol:** v{output["protocol_version"]}
**Execution date (UTC):** {output["execution_date_utc"]}
**Config hash:** `{output["config_hash"]}`
**Upstream v1.3 freeze hash:** `{output["upstream_freeze_hash"]}`
**Upstream VERDICT:** `{output["upstream_verdict"]}`

---

## VERDICT: **{v["VERDICT"]}**

### Fail codes
{fails_md}

---

## Pre-registered gates

| Gate | Value | Required | LOSO result | Pass |
|---|---|---|---|---|
| AUROC | decision quality | ≥ {DEPLOYMENT_GATES["auroc_min"]} | {loso["auroc"]:.3f} | {
        "✓" if loso["auroc"] >= DEPLOYMENT_GATES["auroc_min"] else "✗"
    } |
| AUPRC | precision-aware quality | ≥ {DEPLOYMENT_GATES["auprc_min"]} | {loso["auprc"]:.3f} | {
        "✓" if loso["auprc"] >= DEPLOYMENT_GATES["auprc_min"] else "✗"
    } |
| Brier | calibration | ≤ {DEPLOYMENT_GATES["brier_max"]} | {loso["brier"]:.3f} | {
        "✓" if loso["brier"] <= DEPLOYMENT_GATES["brier_max"] else "✗"
    } |
| Thr range | decision stability | ≤ {DEPLOYMENT_GATES["threshold_loso_range_max"]} | {
        loso["threshold_range"][1] - loso["threshold_range"][0]:.3f} | {
        "✓" if loso["threshold_sign_stable"] else "✗"
    } |

---

## Full-cohort reference

| Metric | Value |
|---|---:|
| n | {full["n"]} |
| AUROC | {full["auroc"]:.3f} |
| AUPRC | {full["auprc"]:.3f} |
| Brier | {full["brier"]:.3f} |

Full-cohort numbers are for context only — **LOSO is the primary evidence**.

---

## LOSO decision thresholds (Youden J per fold)

| Fold | Threshold |
|---|---:|
{thr_row_lines}

Mean ± std: {loso["threshold_mean"]:.3f} ± {loso["threshold_std"]:.3f}
Range: [{loso["threshold_range"][0]:.3f}, {loso["threshold_range"][1]:.3f}]
Sign stable across folds: **{loso["threshold_sign_stable"]}**

---

## Reliability curve (LOSO out-of-fold)

| Bin centre | Observed CHF freq | Count |
|---|---|---:|
{rel_rows}

---

## Allowed claims (under this verdict)

{allowed_claims_md}

## Forbidden claims (regardless of verdict)

1. External-cohort readiness (see Point 6).
2. Nonlinear dynamics / criticality confirmation (surrogate line remains FROZEN).
3. Clinical diagnostic endorsement — that requires regulatory evidence outside this scope.

---

## Next action

{next_action_md}
"""
    path.write_text(md, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _blocked(msg: str, extra: dict[str, Any] | None = None) -> int:
    """Write a block report and exit non-zero without running validation."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "protocol_version": PROTOCOL_VER,
        "execution_date_utc": datetime.now(timezone.utc).isoformat(),
        "config_hash": config_hash(),
        "VERDICT": "DEPLOYMENT_BLOCKED_BY_DESCRIPTIVE_UNSTABLE"
        if "UNSTABLE" in msg
        else "IMPLEMENTATION_BLOCKED",
        "reason": msg,
    }
    if extra:
        payload.update(extra)
    RESULTS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    REPORT_MD.write_text(
        f"# Deployment validation BLOCKED\n\n"
        f"**Verdict:** `{payload['VERDICT']}`\n\n"
        f"**Reason:** {msg}\n\n"
        f"No deployment metrics were computed.\n",
        encoding="utf-8",
    )
    print(f"[VERDICT] {payload['VERDICT']}  — {msg}")
    return 2


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_JSON.exists():
        return _blocked(
            f"upstream v1.3 results not found at {INPUT_JSON}; run the "
            "descriptive discriminator first."
        )
    upstream = json.loads(INPUT_JSON.read_text())
    upstream_verdict = upstream.get("VERDICT")
    if upstream_verdict != "DESCRIPTIVE_DISCRIMINATOR_VALID":
        return _blocked(
            f"upstream descriptive verdict is {upstream_verdict!r}; "
            "deployment validation only runs on DESCRIPTIVE_DISCRIMINATOR_VALID.",
            extra={"upstream_verdict": upstream_verdict},
        )

    nsr = upstream["nsr_features"]
    chf = upstream["chf_features"]
    if not nsr or not chf:
        return _blocked("upstream feature arrays empty.")

    # Matrix [n_samples × 2], labels: NSR=0, CHF=1 (pathology positive).
    features = np.vstack(
        [
            np.array([[f["h_q2"], f["delta_h"]] for f in nsr]),
            np.array([[f["h_q2"], f["delta_h"]] for f in chf]),
        ]
    )
    y_true = np.concatenate([np.zeros(len(nsr), dtype=np.int8), np.ones(len(chf), dtype=np.int8)])

    print(
        f"Running deployment validation on n_NSR={len(nsr)}, n_CHF={len(chf)} "
        f"(LOSO, {len(features)} folds)"
    )
    validation = run_validation(features, y_true)

    output = {
        "protocol_version": PROTOCOL_VER,
        "execution_date_utc": datetime.now(timezone.utc).isoformat(),
        "config_hash": config_hash(),
        "upstream_freeze_hash": upstream.get("freeze_hash"),
        "upstream_verdict": upstream_verdict,
        "immutable_config": immutable_config(),
        "n_nsr": int(len(nsr)),
        "n_chf": int(len(chf)),
        "validation": validation,
    }

    RESULTS_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(output, REPORT_MD)

    v = validation
    loso = v["loso"]
    print(f"\n{'=' * 62}")
    print(f"[VERDICT] {v['VERDICT']}")
    print(
        f"  LOSO AUROC={loso['auroc']:.3f}  AUPRC={loso['auprc']:.3f}  "
        f"Brier={loso['brier']:.3f}  thr={loso['threshold_mean']:.3f} ±{loso['threshold_std']:.3f}"
    )
    if v["fail_codes"]:
        print(f"  fails: {v['fail_codes']}")
    print(f"{'=' * 62}")
    return 0 if v["VERDICT"] == "DEPLOYMENT_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
