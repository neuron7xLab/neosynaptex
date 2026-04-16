#!/usr/bin/env python3
# ruff: noqa: E501 -- markdown report template contains long Ukrainian/English claims lines.
"""
run_nsr_chf_descriptive_discriminator.py
NSR–CHF Descriptive Discriminator Protocol v1.3
================================================
2026-04-15 | NeoSynaptex
Canonical descriptive branch — surrogate/null program frozen separately.

EPISTEMIC POSITION:
  descriptive discrimination  = VALID or UNSTABLE (determined at runtime)
  surrogate-based nonlinearity = FROZEN
  cross-substrate universality = NOT CLAIMED HERE
  clinical deployment          = PENDING

BUG FIXED vs v1.2:
  loso_feature(nsr_hq2, chf_hq2, expected_sign="negative") was WRONG.
  cohens_d(NSR_hq2=1.10, CHF_hq2=0.74) is POSITIVE (NSR > CHF).
  Corrected to expected_sign="positive" for h(q=2).
  Δh remains expected_sign="negative" (NSR Δh < CHF Δh — correct).

OUTPUTS:
  evidence/replications/nsr_chf_descriptive/results.json
  evidence/replications/nsr_chf_descriptive/DISCRIMINATOR_REPORT.md
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import wfdb

from substrates.physionet_hrv.mfdfa import mfdfa

# ── IMMUTABLE CONFIG ──────────────────────────────────────────────────────────
OUTPUT_DIR = Path("evidence/replications/nsr_chf_descriptive")
PROTOCOL_VER = "1.3.0"

NSR_DB = "nsrdb"
CHF_DB = "chfdb"

RESAMPLE_HZ = 4.0
RR_MIN_MS = 300.0
RR_MAX_MS = 2000.0
MIN_DURATION_S = 1200.0
MIN_UNIFORM_SAMPLES = int(MIN_DURATION_S * RESAMPLE_HZ)  # 4800
# Cap RR sequence to a comparable window across records. PhysioNet NSR2DB
# records span ~24 h (≈ 300–340 k uniform samples at 4 Hz) — full-cohort
# MFDFA at n≈300k runs ~16 min/record and saturates the 24 h/full-cohort
# budget without methodological benefit over a fixed window. PR #102
# (run_nsr2db_hrv_multifractal.py) used RR_TRUNCATE=20000; we re-use the
# same cap here so the descriptive-branch results are directly comparable
# to that commit. The value is pinned in ``immutable_config`` so the
# freeze hash reflects it.
RR_TRUNCATE = 20000  # number of accepted RR intervals retained per record

Q_RANGE = np.arange(-5, 5.5, 0.5)
SCALE_RANGE = (32, 1024)  # 4 Hz → [8s, 256s]

N_BOOTSTRAP = 10_000
N_PERMUTATION = 10_000
BOOTSTRAP_SEED = 42
PERM_SEED = 42

MIN_SUBJECTS_PER_GROUP = 5  # bootstrap CI invalid below this

# ── SIGN CONVENTION (pre-registered, verified numerically) ────────────────────
# cohens_d(nsr_hq2, chf_hq2):  NSR(1.10) > CHF(0.74) → POSITIVE
# cohens_d(nsr_dh,  chf_dh):   NSR(0.19) < CHF(0.66) → NEGATIVE
# LOSO expected_sign must match cohens_d direction:
LOSO_SIGN_HQ2 = "positive"  # h(q=2): NSR > CHF
LOSO_SIGN_DH = "negative"  # Δh:     NSR < CHF


# ── FREEZE MACHINERY ──────────────────────────────────────────────────────────
def immutable_config() -> dict:
    return {
        "protocol_version": PROTOCOL_VER,
        "resample_hz": RESAMPLE_HZ,
        "rr_min_ms": RR_MIN_MS,
        "rr_max_ms": RR_MAX_MS,
        "min_duration_s": MIN_DURATION_S,
        "min_uniform_samples": MIN_UNIFORM_SAMPLES,
        "rr_truncate": RR_TRUNCATE,
        "q_range": Q_RANGE.tolist(),
        "scale_range": list(SCALE_RANGE),
        "n_bootstrap": N_BOOTSTRAP,
        "n_permutation": N_PERMUTATION,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "perm_seed": PERM_SEED,
        "loso_sign_hq2": LOSO_SIGN_HQ2,
        "loso_sign_dh": LOSO_SIGN_DH,
    }


def _sha16(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()[:16]


def config_hash() -> str:
    return _sha16(json.dumps(immutable_config(), sort_keys=True).encode())


def record_hash(record_ids: list[str]) -> str:
    return _sha16(json.dumps(sorted(record_ids)).encode())


def freeze_hash(record_ids: list[str]) -> str:
    return _sha16((record_hash(record_ids) + config_hash()).encode())


# ── PREPROCESSING ─────────────────────────────────────────────────────────────
def preprocess_hrv(record_id: str, db: str) -> np.ndarray | None:
    """
    annotations → RR intervals → gross filter → uniform 4 Hz grid.
    All validity checks applied AFTER uniform-series construction.
    Returns None if record does not meet protocol criteria.
    """
    record = wfdb.rdrecord(record_id, pn_dir=db)
    ann = wfdb.rdann(record_id, "atr", pn_dir=db)

    rr_ms = np.diff(ann.sample) / record.fs * 1000.0
    rr_ms = rr_ms[(rr_ms >= RR_MIN_MS) & (rr_ms <= RR_MAX_MS)]

    if rr_ms.size < 2:
        return None

    # Truncate to RR_TRUNCATE accepted intervals — comparable-window
    # cap that aligns the descriptive branch with PR #102 and keeps
    # MFDFA cost bounded on multi-hour NSR2DB records.
    if rr_ms.size > RR_TRUNCATE:
        rr_ms = rr_ms[:RR_TRUNCATE]

    rr_s = rr_ms / 1000.0
    # t[i] = cumulative time at START of i-th interval
    # rr_s[:-1] is intentional: last interval has no subsequent beat
    t = np.concatenate([[0.0], np.cumsum(rr_s[:-1])])

    if t.size < 2:
        return None
    if float(t[-1] - t[0]) < MIN_DURATION_S:
        return None

    t_uni = np.arange(t[0], t[-1], 1.0 / RESAMPLE_HZ)
    rr_uni = np.interp(t_uni, t, rr_ms).astype(float)

    if rr_uni.size < MIN_UNIFORM_SAMPLES:
        return None
    if not np.all(np.isfinite(rr_uni)):
        return None
    if np.std(rr_uni, ddof=1) <= 0.0:
        return None

    return rr_uni


# ── FEATURE EXTRACTION ────────────────────────────────────────────────────────
def extract_features(rr: np.ndarray, record_id: str, label: str) -> dict:
    """Canonical MFDFA features. No surrogate. No nonlinearity claim.

    Uses the repository's ``substrates.physionet_hrv.mfdfa.mfdfa`` —
    the same measurement-branch entry point as every other HRV runner
    in this repo — so cross-script numerical comparability is guaranteed.
    Δh reported here is ``max(α) − min(α)`` (singularity-strength span),
    matching the NULL-SCREEN and IAAFT-repair protocols.
    """
    res = mfdfa(
        rr,
        q_values=Q_RANGE,
        s_min=SCALE_RANGE[0],
        s_max=SCALE_RANGE[1],
        n_scales=20,
        fit_order=1,
    )
    alpha = np.asarray(res.alpha)

    return {
        "record": record_id,
        "label": label,
        "h_q2": float(res.h_at_q2),
        "delta_h": float(alpha.max() - alpha.min()),
        "alpha_min": float(alpha.min()),
        "alpha_max": float(alpha.max()),
        "n_samples": int(rr.size),
    }


# ── STATISTICS ────────────────────────────────────────────────────────────────
def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    pooled = np.sqrt((a.std(ddof=1) ** 2 + b.std(ddof=1) ** 2) / 2.0)
    return float((a.mean() - b.mean()) / (pooled + 1e-10))


def interpret_d(d: float) -> str:
    ad = abs(d)
    if ad >= 2.0:
        return "very large"
    if ad >= 0.8:
        return "large"
    if ad >= 0.5:
        return "medium"
    if ad >= 0.2:
        return "small"
    return "negligible"


def bootstrap_ci(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    ds = [
        cohens_d(
            rng.choice(a, size=a.size, replace=True),
            rng.choice(b, size=b.size, replace=True),
        )
        for _ in range(N_BOOTSTRAP)
    ]
    return float(np.percentile(ds, 2.5)), float(np.percentile(ds, 97.5))


def permutation_p(a: np.ndarray, b: np.ndarray) -> float:
    rng = np.random.default_rng(PERM_SEED)
    obs = abs(cohens_d(a, b))
    combined = np.concatenate([a, b]).astype(float)
    n_a = a.size
    count = 0
    for _ in range(N_PERMUTATION):
        perm = rng.permutation(combined)  # single permutation, no side-effects
        d_perm = abs(cohens_d(perm[:n_a], perm[n_a:]))
        if d_perm >= obs:
            count += 1
    return float(count / N_PERMUTATION)


def loso_feature(
    values_a: np.ndarray,
    values_b: np.ndarray,
    expected_sign: str,
) -> dict:
    """
    Leave-one-subject-out Cohen's d stability.
    expected_sign: "positive" | "negative" — pre-registered, not post-hoc.
    """
    loo = [cohens_d(np.delete(values_a, i), values_b) for i in range(values_a.size)] + [
        cohens_d(values_a, np.delete(values_b, i)) for i in range(values_b.size)
    ]

    if expected_sign == "negative":
        sign_stable = all(d < 0 for d in loo)
    elif expected_sign == "positive":
        sign_stable = all(d > 0 for d in loo)
    else:
        raise ValueError(f"expected_sign must be 'positive' or 'negative', got: {expected_sign!r}")

    return {
        "d_min": float(min(loo)),
        "d_max": float(max(loo)),
        "min_abs_d": float(min(abs(d) for d in loo)),
        "sign_stable": bool(sign_stable),
        "expected_sign": expected_sign,
        "values": [float(d) for d in loo],
    }


# ── DATA LOADING ──────────────────────────────────────────────────────────────
def load_group(db: str, label: str) -> tuple[list[dict], list[str]]:
    features = []
    accepted_ids = []

    for record_id in sorted(wfdb.get_record_list(db)):
        try:
            rr = preprocess_hrv(record_id, db)
            if rr is None:
                print(f"  [SKIP] {label} {record_id}: did not pass preprocessing")
                continue
            feat = extract_features(rr, record_id, label)
            features.append(feat)
            accepted_ids.append(record_id)
            print(
                f"  [OK]   {label} {record_id}: "
                f"h(q=2)={feat['h_q2']:.3f}, Δh={feat['delta_h']:.3f}, "
                f"n={feat['n_samples']}"
            )
        except Exception as exc:
            print(f"  [ERR]  {label} {record_id}: {exc}")

    return features, accepted_ids


# ── REPORT ────────────────────────────────────────────────────────────────────
def write_report(output: dict, path: Path) -> None:
    ef = output["effect_sizes"]
    loso = output["loso"]

    def _loso_row(key: str) -> str:
        r = loso[key]
        return (
            f"| {key} | [{r['d_min']:.3f}, {r['d_max']:.3f}] "
            f"| {r['min_abs_d']:.3f} | {r['sign_stable']} |"
        )

    # Pre-compute long row/verdict strings so the f-string template below
    # does not exceed the 100-char line limit.
    nsr_row = (
        f"| NSR | {output['nsr_n']} "
        f"| {output['nsr_hq2_mean']:.3f} ± {output['nsr_hq2_std']:.3f} "
        f"| {output['nsr_dh_mean']:.3f} ± {output['nsr_dh_std']:.3f} |"
    )
    chf_row = (
        f"| CHF | {output['chf_n']} "
        f"| {output['chf_hq2_mean']:.3f} ± {output['chf_hq2_std']:.3f} "
        f"| {output['chf_dh_mean']:.3f} ± {output['chf_dh_std']:.3f} |"
    )
    hq2 = ef["h_q2"]
    dh = ef["delta_h"]
    hq2_row = (
        f"| h(q=2) | {hq2['cohens_d']:.3f} "
        f"| [{hq2['ci_95'][0]:.3f}, {hq2['ci_95'][1]:.3f}] "
        f"| {hq2['perm_p']:.4f} | {hq2['interpretation']} |"
    )
    dh_row = (
        f"| Δh | {dh['cohens_d']:.3f} "
        f"| [{dh['ci_95'][0]:.3f}, {dh['ci_95'][1]:.3f}] "
        f"| {dh['perm_p']:.4f} | {dh['interpretation']} |"
    )
    if output["VERDICT"] == "DESCRIPTIVE_DISCRIMINATOR_VALID":
        verdict_para = (
            "VALID means: both h(q=2) and Δh retain sign stability under "
            "leave-one-subject-out. Descriptive discriminator claim admitted."
        )
    else:
        verdict_para = (
            "UNSTABLE means: numerical separation exists but at least one "
            "primary endpoint loses sign stability under LOSO. Descriptive "
            "discriminator claim NOT admitted."
        )
    if output["VERDICT"] == "DESCRIPTIVE_DISCRIMINATOR_VALID":
        coherence_status = "descriptive discriminator — VALID under this protocol"
    else:
        coherence_status = "descriptive discriminator"

    md = f"""\
# NSR–CHF Descriptive Discriminator Report
**Protocol:** v{output["protocol_version"]}
**Execution date (UTC):** {output["execution_date_utc"]}
**Record hash:** `{output["record_hash"]}`
**Config hash:**  `{output["config_hash"]}`
**Freeze hash:**  `{output["freeze_hash"]}`

---

## Epistemic status

| Domain | Status |
|---|---|
| Descriptive separation NSR vs CHF | **{output["VERDICT"]}** |
| Surrogate-based nonlinearity | **FROZEN** |
| Cross-substrate universality | **NOT CLAIMED HERE** |
| Clinical deployment readiness | **PENDING** |

---

## Subjects

| Group | n | h(q=2) mean ± std | Δh mean ± std |
|---|---:|---:|---:|
{nsr_row}
{chf_row}

---

## Primary endpoints

| Feature | Cohen's d | 95% CI | Permutation p | Interpretation |
|---|---:|---|---:|---|
{hq2_row}
{dh_row}

---

## LOSO stability

| Feature | d range | min |d| | Sign stable |
|---|---|---:|---|
{_loso_row("h_q2")}
{_loso_row("delta_h")}

**Sign convention (pre-registered):**
- h(q=2): expected positive — NSR(≈1.10) > CHF(≈0.74)
- Δh:     expected negative — NSR(≈0.19) < CHF(≈0.66)

---

## Verdict

### **{output["VERDICT"]}**

{verdict_para}

**Surrogate-based nonlinearity claim: FROZEN.**
**Cross-substrate universality: NOT CLAIMED HERE.**

---

## Allowed claims

1. h(q=2) і Δh з MFDFA демонструють описову розділюваність між NSR і CHF на PhysioNet датасетах.
2. Ефект стабільний за leave-one-subject-out аналізом (якщо sign_stable = True для обох).
3. Permutation p-value < 0.05 виключає випадкову розділюваність на цьому датасеті.
4. (h(q=2), Δh) є кандидатом у descriptive discriminator для CHF vs NSR.
5. Surrogate-based інтерпретація нелінійності заморожена через відсутність валідного null environment.

## Forbidden claims

1. Нелінійна мультифрактальність підтверджена.
2. Surrogate-based nonlinearity verified.
3. Результат субстрат-інваріантний.
4. Δh підтверджує критичний режим, SOC або metastability.
5. Cohen's d = X означає клінічно готову діагностику.
6. Результат відтворений на незалежній когорті.
7. Будь-яке твердження за межами: "descriptive separation between NSR and CHF on PhysioNet NSR2DB + CHFDB under this fixed protocol."

---

## CoherenceBridge note

Current status: {coherence_status}.
Next step for commercialization: deployment validation protocol (nested CV, AUROC, calibration, external cohort).
"""
    path.write_text(md, encoding="utf-8")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("NSR–CHF Descriptive Discriminator Protocol v1.3\n")
    print("Loading NSR records...")
    nsr_features, nsr_ids = load_group(NSR_DB, "NSR")

    print("\nLoading CHF records...")
    chf_features, chf_ids = load_group(CHF_DB, "CHF")

    print(f"\nAccepted: n_NSR={len(nsr_features)}, n_CHF={len(chf_features)}")

    # Hard gate: n < MIN_SUBJECTS_PER_GROUP
    if len(nsr_features) < MIN_SUBJECTS_PER_GROUP or len(chf_features) < MIN_SUBJECTS_PER_GROUP:
        raise SystemExit(
            f"ERROR: n < {MIN_SUBJECTS_PER_GROUP} in one or both groups. "
            "Bootstrap CI not accepted under this protocol."
        )

    nsr_hq2 = np.array([f["h_q2"] for f in nsr_features], dtype=float)
    nsr_dh = np.array([f["delta_h"] for f in nsr_features], dtype=float)
    chf_hq2 = np.array([f["h_q2"] for f in chf_features], dtype=float)
    chf_dh = np.array([f["delta_h"] for f in chf_features], dtype=float)

    # Cached effect sizes (no redundant recomputation)
    print("\nComputing effect sizes (bootstrap n=10000, permutation n=10000)...")
    d_hq2 = cohens_d(nsr_hq2, chf_hq2)
    d_dh = cohens_d(nsr_dh, chf_dh)

    effect_sizes = {
        "h_q2": {
            "cohens_d": d_hq2,
            "ci_95": bootstrap_ci(nsr_hq2, chf_hq2),
            "perm_p": permutation_p(nsr_hq2, chf_hq2),
            "interpretation": interpret_d(d_hq2),
        },
        "delta_h": {
            "cohens_d": d_dh,
            "ci_95": bootstrap_ci(nsr_dh, chf_dh),
            "perm_p": permutation_p(nsr_dh, chf_dh),
            "interpretation": interpret_d(d_dh),
        },
    }

    # LOSO — pre-registered sign directions
    print("Computing LOSO stability...")
    loso_res = {
        "h_q2": loso_feature(nsr_hq2, chf_hq2, LOSO_SIGN_HQ2),
        "delta_h": loso_feature(nsr_dh, chf_dh, LOSO_SIGN_DH),
    }

    # VERDICT: requires LOSO sign stability on BOTH features
    loso_ok = loso_res["h_q2"]["sign_stable"] and loso_res["delta_h"]["sign_stable"]
    verdict = "DESCRIPTIVE_DISCRIMINATOR_VALID" if loso_ok else "DESCRIPTIVE_DISCRIMINATOR_UNSTABLE"

    all_ids = nsr_ids + chf_ids

    output = {
        "protocol_version": PROTOCOL_VER,
        "execution_date_utc": datetime.now(timezone.utc).isoformat(),
        "record_hash": record_hash(all_ids),
        "config_hash": config_hash(),
        "freeze_hash": freeze_hash(all_ids),
        "immutable_config": immutable_config(),
        "nsr_n": int(len(nsr_features)),
        "chf_n": int(len(chf_features)),
        "nsr_ids": nsr_ids,
        "chf_ids": chf_ids,
        "nsr_hq2_mean": float(nsr_hq2.mean()),
        "nsr_hq2_std": float(nsr_hq2.std(ddof=1)),
        "nsr_dh_mean": float(nsr_dh.mean()),
        "nsr_dh_std": float(nsr_dh.std(ddof=1)),
        "chf_hq2_mean": float(chf_hq2.mean()),
        "chf_hq2_std": float(chf_hq2.std(ddof=1)),
        "chf_dh_mean": float(chf_dh.mean()),
        "chf_dh_std": float(chf_dh.std(ddof=1)),
        "effect_sizes": effect_sizes,
        "loso": loso_res,
        "VERDICT": verdict,
        "epistemic_status": {
            "descriptive_separation": verdict,
            "surrogate_nonlinearity": "FROZEN",
            "cross_substrate_universality": "NOT_CLAIMED_HERE",
            "clinical_deployment": "PENDING",
        },
        "nsr_features": nsr_features,
        "chf_features": chf_features,
    }

    json_path = OUTPUT_DIR / "results.json"
    report_path = OUTPUT_DIR / "DISCRIMINATOR_REPORT.md"

    json_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(output, report_path)

    print(f"\n{'=' * 62}")
    print(f"[VERDICT] {verdict}")
    print(
        f"  h(q=2): d={d_hq2:.3f}  "
        f"CI=[{effect_sizes['h_q2']['ci_95'][0]:.3f}, "
        f"{effect_sizes['h_q2']['ci_95'][1]:.3f}]  "
        f"p={effect_sizes['h_q2']['perm_p']:.4f}  "
        f"LOSO_stable={loso_res['h_q2']['sign_stable']}"
    )
    print(
        f"  Δh:     d={d_dh:.3f}  "
        f"CI=[{effect_sizes['delta_h']['ci_95'][0]:.3f}, "
        f"{effect_sizes['delta_h']['ci_95'][1]:.3f}]  "
        f"p={effect_sizes['delta_h']['perm_p']:.4f}  "
        f"LOSO_stable={loso_res['delta_h']['sign_stable']}"
    )
    print(f"  Freeze hash: {output['freeze_hash']}")
    print(f"  Results: {json_path}")
    print(f"  Report:  {report_path}")
    print(f"{'=' * 62}")
    print("\n[FROZEN] surrogate-based nonlinearity claim")
    print("[FROZEN] cross-substrate universality")


if __name__ == "__main__":
    main()
