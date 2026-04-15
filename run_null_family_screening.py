#!/usr/bin/env python3
"""NULL-SCREEN-v1.1 — canonical null-family screening runner.

Generates the three canonical null families against a pre-registered
fixture battery (synthetic linear, synthetic nonlinear, real NSR2DB)
and produces one admissibility verdict:

    NULL_FAMILY_SELECTED
    NO_ADMISSIBLE_NULL_FOUND
    IMPLEMENTATION_BLOCKED

No threshold tuning is permitted inside this script. All gates come
from the 2026-04-15 protocol. Evidence is written to:

    evidence/replications/hrv_null_screening/null_screening_results.json
    evidence/replications/hrv_null_screening/NULL_SCREENING_REPORT.md

Fail-closed: if the binomial-cascade fixture does not reproduce the
expected Δh > 0.15, the final verdict is IMPLEMENTATION_BLOCKED and
screening is NOT executed.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import json
import logging
import pathlib
import sys
from collections.abc import Callable
from typing import Any

import numpy as np
from scipy.stats import t as _student_t

from core.nulls import FAMILIES, NullDiagnostics
from core.nulls.metrics import (
    compute_delta_h,
)
from substrates.physionet_hrv.hrv_gamma_fit import rr_to_uniform_4hz
from substrates.physionet_hrv.nsr2db_client import PN_DIR, fetch_rr_intervals

# ---------------------------------------------------------------------------
# Pre-registered gates (NULL-SCREEN-v1.1 §METRICS)
# ---------------------------------------------------------------------------
PSD_GATE = 0.15
ACF_GATE = 0.10
DIST_GATE_EXACT = 1e-10
STD_PSD_GATE = 0.03
STD_ACF_GATE = 0.03
STD_DH_GATE = 0.02
LINEAR_SEP_ABS_GATE = 0.03
NONLINEAR_SEP_GATE = 0.05
CASCADE_DH_PREFLIGHT = 0.15
SEEDS = tuple(range(10))
PER_FIXTURE_TIMEOUT_S = 120.0

OUTPUT_DIR = pathlib.Path("evidence/replications/hrv_null_screening")
RESULTS_JSON = OUTPUT_DIR / "null_screening_results.json"
REPORT_MD = OUTPUT_DIR / "NULL_SCREENING_REPORT.md"
LOG_PATH = OUTPUT_DIR / "run.log"

logger = logging.getLogger("null_screening")


# ---------------------------------------------------------------------------
# Fixtures (all synthetic ones deterministic under ``seed``)
# ---------------------------------------------------------------------------
def fix_white_noise(n: int = 4096, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n)


def fix_pink_fgn(n: int = 4096, hurst: float = 0.7, seed: int = 0) -> np.ndarray:
    """Spectral-synthesis fGn with Hurst index ``hurst``."""
    rng = np.random.default_rng(seed)
    freqs = np.fft.rfftfreq(n, d=1.0)
    freqs_nz = np.where(freqs == 0.0, 1.0, freqs)
    beta = 2.0 * hurst - 1.0
    amp = freqs_nz ** (-beta / 2.0)
    amp[0] = 0.0
    phases = rng.uniform(0.0, 2.0 * np.pi, len(freqs))
    phases[0] = 0.0
    x = np.fft.irfft(amp * np.exp(1j * phases), n=n)
    return np.asarray((x - x.mean()) / (x.std() + 1e-12))


def fix_phase_rand_1f(n: int = 4096, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    freqs = np.fft.rfftfreq(n, d=1.0)
    freqs_nz = np.where(freqs == 0.0, 1.0, freqs)
    amp = freqs_nz ** (-0.5)  # PSD ~ 1/f
    amp[0] = 0.0
    phases = rng.uniform(0.0, 2.0 * np.pi, len(freqs))
    phases[0] = 0.0
    x = np.fft.irfft(amp * np.exp(1j * phases), n=n)
    return np.asarray((x - x.mean()) / (x.std() + 1e-12))


def fix_binomial_cascade(n_levels: int = 12, p: float = 0.3, seed: int = 0) -> np.ndarray:
    """Binomial p-cascade (Meneveau & Sreenivasan 1987), integrated.

    With randomised half-assignment per level; output length 2**n_levels.
    """
    rng = np.random.default_rng(seed)
    size = 2**n_levels
    sig = np.ones(size)
    for lvl in range(n_levels):
        step = 2 ** (n_levels - lvl - 1)
        for i in range(0, size, 2 * step):
            if rng.uniform() < 0.5:
                sig[i : i + step] *= p
                sig[i + step : i + 2 * step] *= 1.0 - p
            else:
                sig[i : i + step] *= 1.0 - p
                sig[i + step : i + 2 * step] *= p
    return np.asarray(np.cumsum(sig - sig.mean()))


def fix_hrv_like_nonlinear(n: int = 4096, seed: int = 0) -> np.ndarray:
    """ARFIMA(0, d=0.4, 0)-like backbone + Student-t(df=5) innovations
    + multiplicative sign-feedback nonlinearity.

    Long-memory backbone implemented as a long moving-average with
    weights w_k = 1/k^(1-d), a practical approximation of ARFIMA(0,d,0);
    this is noted in ``diagnostics.notes``.
    """
    rng = np.random.default_rng(seed)
    d = 0.4
    df = 5
    eps = _student_t.rvs(df, size=n + 256, random_state=rng)
    # Long-memory linear backbone.
    window = 128
    k = np.arange(1, window + 1, dtype=np.float64)
    weights = k ** -(1.0 - d)
    weights /= weights.sum()
    backbone = np.convolve(eps, weights, mode="valid")[:n]
    # Nonlinear modulation: x[t] *= (1 + 0.3 * sign(x[t-1])).
    y = np.empty(n, dtype=np.float64)
    y[0] = backbone[0]
    for t in range(1, n):
        y[t] = backbone[t] * (1.0 + 0.3 * np.sign(y[t - 1]))
    return y


NSR_RECORDS_CACHE: list[tuple[str, np.ndarray]] = []
# Screening window — the N1 MCMC search is O(n·max_lag·n_proposals), so
# we screen real NSR records on the FIRST 4096 uniform-4Hz samples (≈17 min
# of RR data). This matches the synthetic-fixture length for apples-to-
# apples comparison. Full-record analysis is explicitly a separate step.
SCREENING_WINDOW_N = 4096


def _load_nsr_records() -> list[tuple[str, np.ndarray]]:
    """Same 5 NSR2DB records as SIGN-FLIP-DIAG-v1, cached, screening-windowed."""
    if NSR_RECORDS_CACHE:
        return NSR_RECORDS_CACHE
    import wfdb

    names = sorted(r for r in wfdb.get_record_list(PN_DIR) if r.startswith("nsr"))[:5]
    for name in names:
        rec = fetch_rr_intervals(name)
        rr = np.asarray(rec.rr_seconds, dtype=np.float64)[:20000]
        rr_u = rr_to_uniform_4hz(rr)
        NSR_RECORDS_CACHE.append((name, rr_u[:SCREENING_WINDOW_N]))
    return NSR_RECORDS_CACHE


# ---------------------------------------------------------------------------
# Screening data model
# ---------------------------------------------------------------------------
@dataclasses.dataclass
class FixtureOutcome:
    fixture: str
    kind: str  # "linear_synth" | "nonlinear_synth" | "real"
    delta_h_real: float
    seed_runs: list[dict[str, Any]]
    median_delta_h_surrogate: float
    median_psd_error: float
    median_acf_error: float
    max_dist_error: float
    sep: float
    std_psd_error: float
    std_acf_error: float
    std_dh_surrogate: float
    any_timeout: bool


@dataclasses.dataclass
class FamilyOutcome:
    family: str
    preserves_distribution_exactly: bool
    fixtures: list[FixtureOutcome]
    admit: bool
    fail_codes: list[str]
    summary_notes: list[str]


# ---------------------------------------------------------------------------
# Preflight validation (§FIXTURE VALIDATION)
# ---------------------------------------------------------------------------
def preflight() -> tuple[bool, str, dict[str, Any]]:
    # 1. binomial cascade Δh > 0.15
    cascade = fix_binomial_cascade(n_levels=12, p=0.3, seed=0)
    try:
        dh_cascade = compute_delta_h(cascade)
    except Exception as exc:  # noqa: BLE001
        return (
            False,
            f"cascade MFDFA failed: {exc}",
            {"cascade_delta_h": None, "error": str(exc)},
        )
    if dh_cascade <= CASCADE_DH_PREFLIGHT:
        return (
            False,
            (
                "Binomial cascade fixture invalid or measurement path not "
                f"reproducing expected nonlinear width: Δh={dh_cascade:.3f} "
                f"<= {CASCADE_DH_PREFLIGHT}."
            ),
            {"cascade_delta_h": dh_cascade},
        )

    # 2. HRV-like synthetic deterministic + length + finite + MFDFA OK
    y1 = fix_hrv_like_nonlinear(n=4096, seed=42)
    y2 = fix_hrv_like_nonlinear(n=4096, seed=42)
    if y1.shape != (4096,):
        return False, f"HRV-like length wrong: {y1.shape}", {"cascade_delta_h": dh_cascade}
    if not np.array_equal(y1, y2):
        return (
            False,
            "HRV-like synthetic NOT deterministic under seed=42",
            {"cascade_delta_h": dh_cascade},
        )
    if float(np.var(y1)) <= 0:
        return False, "HRV-like variance non-positive", {"cascade_delta_h": dh_cascade}
    if not np.all(np.isfinite(y1)):
        return False, "HRV-like contains NaN/inf", {"cascade_delta_h": dh_cascade}
    try:
        dh_hrv = compute_delta_h(y1)
    except Exception as exc:  # noqa: BLE001
        return (
            False,
            f"HRV-like MFDFA failed: {exc}",
            {"cascade_delta_h": dh_cascade, "hrv_like_error": str(exc)},
        )

    return (
        True,
        "preflight OK",
        {"cascade_delta_h": float(dh_cascade), "hrv_like_delta_h": float(dh_hrv)},
    )


# ---------------------------------------------------------------------------
# Run one family against one fixture across all seeds
# ---------------------------------------------------------------------------
def run_family_on_fixture(
    family_name: str,
    family_fn: Callable,
    fixture_name: str,
    fixture_kind: str,
    fixture: np.ndarray,
) -> FixtureOutcome:
    dh_real = compute_delta_h(fixture)
    seed_runs: list[dict[str, Any]] = []

    psd_errs: list[float] = []
    acf_errs: list[float] = []
    dh_surr: list[float] = []
    dist_errs: list[float] = []
    any_timeout = False

    for seed in SEEDS:
        try:
            _, diag = family_fn(fixture, seed=seed, timeout_s=PER_FIXTURE_TIMEOUT_S)
        except Exception as exc:  # noqa: BLE001
            seed_runs.append({"seed": seed, "error": str(exc)})
            any_timeout = any_timeout  # unchanged
            continue
        assert isinstance(diag, NullDiagnostics)
        if diag.terminated_by_timeout:
            any_timeout = True
        psd_errs.append(float(diag.psd_error or float("nan")))
        acf_errs.append(float(diag.acf_error or float("nan")))
        dh_surr.append(float(diag.delta_h_surrogate or float("nan")))
        dist_errs.append(
            float(diag.extras and dict(diag.extras).get("distribution_error", 0.0))
            if not diag.preserves_distribution_exactly
            else 0.0
        )
        seed_runs.append(
            {
                "seed": seed,
                "converged": diag.converged,
                "terminated_by_timeout": diag.terminated_by_timeout,
                "psd_error": diag.psd_error,
                "acf_error": diag.acf_error,
                "delta_h_surrogate": diag.delta_h_surrogate,
                "notes": list(diag.notes),
            }
        )

    if not dh_surr:
        return FixtureOutcome(
            fixture=fixture_name,
            kind=fixture_kind,
            delta_h_real=dh_real,
            seed_runs=seed_runs,
            median_delta_h_surrogate=float("nan"),
            median_psd_error=float("nan"),
            median_acf_error=float("nan"),
            max_dist_error=float("inf"),
            sep=float("nan"),
            std_psd_error=float("inf"),
            std_acf_error=float("inf"),
            std_dh_surrogate=float("inf"),
            any_timeout=any_timeout,
        )

    arr_psd = np.asarray(psd_errs)
    arr_acf = np.asarray(acf_errs)
    arr_dh = np.asarray(dh_surr)
    arr_dist = np.asarray(dist_errs)
    med_dh = float(np.median(arr_dh))
    sep = float(dh_real - med_dh)

    return FixtureOutcome(
        fixture=fixture_name,
        kind=fixture_kind,
        delta_h_real=dh_real,
        seed_runs=seed_runs,
        median_delta_h_surrogate=med_dh,
        median_psd_error=float(np.median(arr_psd)),
        median_acf_error=float(np.median(arr_acf)),
        max_dist_error=float(np.max(arr_dist)),
        sep=sep,
        std_psd_error=float(np.std(arr_psd)),
        std_acf_error=float(np.std(arr_acf)),
        std_dh_surrogate=float(np.std(arr_dh)),
        any_timeout=any_timeout,
    )


# ---------------------------------------------------------------------------
# Admissibility law
# ---------------------------------------------------------------------------
def evaluate_admissibility(
    family_name: str,
    preserves_distribution_exactly: bool,
    fixtures: list[FixtureOutcome],
) -> tuple[bool, list[str], list[str]]:
    fails: list[str] = []
    notes: list[str] = []

    for f in fixtures:
        # FAIL_NULL_TIMEOUT — any timeout masks the run.
        if f.any_timeout:
            fails.append(f"FAIL_NULL_TIMEOUT::{f.fixture}")

        # Distribution fidelity — only if the family claims exact preservation.
        if preserves_distribution_exactly and f.max_dist_error > DIST_GATE_EXACT:
            fails.append(f"FAIL_NULL_DIST::{f.fixture}")

        # PSD + ACF fidelity (per-family-specific; all families use same gates
        # for screening since we do NOT assume exact spectrum preservation).
        if f.median_psd_error > PSD_GATE:
            fails.append(f"FAIL_NULL_PSD::{f.fixture}")
        if f.median_acf_error > ACF_GATE:
            fails.append(f"FAIL_NULL_ACF::{f.fixture}")

        # Seed stability (within this fixture).
        if f.std_psd_error > STD_PSD_GATE:
            fails.append(f"FAIL_NULL_SEED::{f.fixture}::psd")
        if f.std_acf_error > STD_ACF_GATE:
            fails.append(f"FAIL_NULL_SEED::{f.fixture}::acf")
        if f.std_dh_surrogate > STD_DH_GATE:
            fails.append(f"FAIL_NULL_SEED::{f.fixture}::dh")

        # Discrimination.
        if f.kind == "linear_synth" and abs(f.sep) >= LINEAR_SEP_ABS_GATE:
            fails.append(f"FAIL_DISC_INJECTION::{f.fixture}")
        if f.kind == "nonlinear_synth" and f.sep <= NONLINEAR_SEP_GATE:
            # Use FAIL_DISC_NONLINEAR for failure on a specific nonlinear fixture.
            fails.append(f"FAIL_DISC_NONLINEAR::{f.fixture}")

    # FAIL_DISC_COLLAPSE — if ALL nonlinear fixtures have sep <= 0.02 the
    # family is over-preserving.
    nonlin = [f for f in fixtures if f.kind == "nonlinear_synth"]
    if nonlin and all(f.sep <= 0.02 for f in nonlin):
        fails.append("FAIL_DISC_COLLAPSE")

    # FAIL_DISC_LINEAR — systematically drifting linear fixtures in one direction.
    lin = [f for f in fixtures if f.kind == "linear_synth"]
    if lin and all(f.sep > LINEAR_SEP_ABS_GATE for f in lin):
        fails.append("FAIL_DISC_LINEAR")
    if lin and all(f.sep < -LINEAR_SEP_ABS_GATE for f in lin):
        fails.append("FAIL_DISC_LINEAR")

    admit = not fails
    if not admit:
        notes.append(f"{family_name}: rejected with {len(fails)} fail code(s)")
    return admit, fails, notes


# ---------------------------------------------------------------------------
# Selection law (§SELECTION LAW)
# ---------------------------------------------------------------------------
_FAMILY_SIMPLICITY_RANK = {
    "linear_matched": 1,  # simplest: fit + simulate
    "wavelet_phase": 2,  # medium: one shuffle per band
    "constrained_randomization": 3,  # most machinery: MCMC loop
}


def select_single(admissible: list[FamilyOutcome]) -> FamilyOutcome | None:
    if not admissible:
        return None
    admissible.sort(key=lambda fo: _FAMILY_SIMPLICITY_RANK.get(fo.family, 99))
    return admissible[0]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger.info("NULL-SCREEN-v1.1 runner — start")

    pre_ok, pre_msg, pre_info = preflight()
    logger.info("preflight: %s — %s", "OK" if pre_ok else "FAIL", pre_msg)
    if not pre_ok:
        out = {
            "protocol": "NULL-SCREEN-v1.1",
            "date": _dt.datetime.now(_dt.UTC).isoformat(),
            "preflight": {"ok": False, "message": pre_msg, "info": pre_info},
            "VERDICT": "IMPLEMENTATION_BLOCKED",
            "next_action": (
                "Isolate the blocker that prevents the measurement branch "
                "from reproducing the cascade Δh gate (>0.15) or the HRV-"
                "like fixture from being well-posed. Screening was not run."
            ),
        }
        RESULTS_JSON.write_text(json.dumps(out, indent=2))
        _emit_report(out, [])
        logger.info("[VERDICT] IMPLEMENTATION_BLOCKED")
        return 2

    # Build the fixture set.
    logger.info("building fixtures …")
    synth_linear: list[tuple[str, np.ndarray]] = [
        ("white_noise", fix_white_noise(n=4096, seed=0)),
        ("pink_fgn_H07", fix_pink_fgn(n=4096, hurst=0.7, seed=0)),
        ("phase_rand_1f", fix_phase_rand_1f(n=4096, seed=0)),
    ]
    synth_nonlinear: list[tuple[str, np.ndarray]] = [
        ("binomial_cascade_p03", fix_binomial_cascade(n_levels=12, p=0.3, seed=0)),
        ("hrv_like_nonlinear", fix_hrv_like_nonlinear(n=4096, seed=0)),
    ]
    logger.info("fetching 5 NSR2DB records …")
    real = [(name, rr_u) for name, rr_u in _load_nsr_records()]

    family_outcomes: list[FamilyOutcome] = []
    for family_name, family_fn in FAMILIES.items():
        logger.info("=== family: %s ===", family_name)
        fixtures_out: list[FixtureOutcome] = []

        for name, fx in synth_linear:
            logger.info("  linear_synth %s …", name)
            fo = run_family_on_fixture(family_name, family_fn, name, "linear_synth", fx)
            fixtures_out.append(fo)
            logger.info(
                "    sep=%+.3f  psd=%.3f  acf=%.3f  std_dh=%.3f  to=%s",
                fo.sep,
                fo.median_psd_error,
                fo.median_acf_error,
                fo.std_dh_surrogate,
                fo.any_timeout,
            )

        for name, fx in synth_nonlinear:
            logger.info("  nonlinear_synth %s …", name)
            fo = run_family_on_fixture(family_name, family_fn, name, "nonlinear_synth", fx)
            fixtures_out.append(fo)
            logger.info(
                "    sep=%+.3f  psd=%.3f  acf=%.3f  std_dh=%.3f  to=%s",
                fo.sep,
                fo.median_psd_error,
                fo.median_acf_error,
                fo.std_dh_surrogate,
                fo.any_timeout,
            )

        for name, fx in real:
            logger.info("  real %s (n=%d) …", name, len(fx))
            fo = run_family_on_fixture(family_name, family_fn, name, "real", fx)
            fixtures_out.append(fo)
            logger.info(
                "    sep=%+.3f  psd=%.3f  acf=%.3f  std_dh=%.3f  to=%s",
                fo.sep,
                fo.median_psd_error,
                fo.median_acf_error,
                fo.std_dh_surrogate,
                fo.any_timeout,
            )

        # Distribution-preservation claim is family-fixed — ask a one-sample probe.
        probe = synth_linear[0][1]
        _, probe_diag = family_fn(probe, seed=0, timeout_s=5.0)
        preserves = bool(probe_diag.preserves_distribution_exactly)

        admit, fail_codes, notes = evaluate_admissibility(family_name, preserves, fixtures_out)
        family_outcomes.append(
            FamilyOutcome(
                family=family_name,
                preserves_distribution_exactly=preserves,
                fixtures=fixtures_out,
                admit=admit,
                fail_codes=fail_codes,
                summary_notes=notes,
            )
        )
        logger.info(
            "  %s => %s  fails=%d",
            family_name,
            "ADMIT" if admit else "REJECT",
            len(fail_codes),
        )

    # Final verdict.
    admissible = [fo for fo in family_outcomes if fo.admit]
    chosen = select_single(admissible)

    if chosen is not None:
        verdict = "NULL_FAMILY_SELECTED"
        next_action = (
            f"Prepare a follow-up protocol for calibration rerun under the "
            f"{chosen.family!r} null family."
        )
    else:
        verdict = "NO_ADMISSIBLE_NULL_FOUND"
        next_action = (
            "Freeze the Δh + surrogate line and continue only on the "
            "non-null-dependent HRV pathology branch (PR #102)."
        )

    out: dict[str, Any] = {
        "protocol": "NULL-SCREEN-v1.1",
        "date": _dt.datetime.now(_dt.UTC).isoformat(),
        "preflight": {"ok": True, "message": pre_msg, "info": pre_info},
        "gates": {
            "psd": PSD_GATE,
            "acf": ACF_GATE,
            "dist_exact": DIST_GATE_EXACT,
            "std_psd": STD_PSD_GATE,
            "std_acf": STD_ACF_GATE,
            "std_dh": STD_DH_GATE,
            "linear_sep_abs": LINEAR_SEP_ABS_GATE,
            "nonlinear_sep": NONLINEAR_SEP_GATE,
            "cascade_preflight": CASCADE_DH_PREFLIGHT,
            "seeds": list(SEEDS),
        },
        "families": [
            {
                "family": fo.family,
                "preserves_distribution_exactly": fo.preserves_distribution_exactly,
                "admit": fo.admit,
                "fail_codes": fo.fail_codes,
                "notes": fo.summary_notes,
                "fixtures": [
                    {
                        "fixture": fix.fixture,
                        "kind": fix.kind,
                        "delta_h_real": fix.delta_h_real,
                        "median_delta_h_surrogate": fix.median_delta_h_surrogate,
                        "median_psd_error": fix.median_psd_error,
                        "median_acf_error": fix.median_acf_error,
                        "max_dist_error": fix.max_dist_error,
                        "sep": fix.sep,
                        "std_psd_error": fix.std_psd_error,
                        "std_acf_error": fix.std_acf_error,
                        "std_dh_surrogate": fix.std_dh_surrogate,
                        "any_timeout": fix.any_timeout,
                    }
                    for fix in fo.fixtures
                ],
            }
            for fo in family_outcomes
        ],
        "chosen_family": chosen.family if chosen else None,
        "VERDICT": verdict,
        "next_action": next_action,
    }
    RESULTS_JSON.write_text(json.dumps(out, indent=2, default=float))
    _emit_report(out, family_outcomes)
    logger.info("=" * 60)
    logger.info("[VERDICT] %s", verdict)
    logger.info("  chosen: %s", chosen.family if chosen else "—")
    logger.info("  Output: %s", RESULTS_JSON)
    return 0 if verdict == "NULL_FAMILY_SELECTED" else 1


# ---------------------------------------------------------------------------
# Report emission
# ---------------------------------------------------------------------------
def _emit_report(out: dict[str, Any], family_outcomes: list[FamilyOutcome]) -> None:
    lines: list[str] = []
    lines.append("# NULL-SCREEN-v1.1 Report")
    lines.append("")
    lines.append(f"> **Date.** {out['date']}")
    lines.append(f"> **VERDICT.** `{out['VERDICT']}`")
    lines.append(f"> **Chosen family.** `{out.get('chosen_family') or '—'}`")
    lines.append(f"> **Next action.** {out['next_action']}")
    lines.append("")
    lines.append("## Preflight")
    lines.append("")
    pf = out["preflight"]
    lines.append(f"- **ok:** {pf['ok']}")
    lines.append(f"- **message:** {pf['message']}")
    lines.append(f"- **info:** `{pf.get('info')}`")
    lines.append("")
    if not pf["ok"]:
        lines.append("Screening was NOT executed per protocol fail-closed gate.")
        REPORT_MD.write_text("\n".join(lines))
        return

    lines.append("## Gates (pre-registered)")
    lines.append("")
    for k, v in out["gates"].items():
        lines.append(f"- `{k}` = `{v}`")
    lines.append("")

    lines.append("## Per-family results")
    lines.append("")
    for fo in family_outcomes:
        lines.append(f"### {fo.family}")
        lines.append("")
        lines.append(f"- admit: **{fo.admit}**")
        lines.append(f"- preserves_distribution_exactly: {fo.preserves_distribution_exactly}")
        lines.append(f"- fail_codes: {fo.fail_codes or '—'}")
        lines.append("")
        lines.append("| fixture | kind | Δh_real | Δh_surr_med | psd | acf | std_dh | sep | TO |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for fx in fo.fixtures:
            lines.append(
                f"| `{fx.fixture}` | {fx.kind} | "
                f"{fx.delta_h_real:.3f} | {fx.median_delta_h_surrogate:.3f} | "
                f"{fx.median_psd_error:.3f} | {fx.median_acf_error:.3f} | "
                f"{fx.std_dh_surrogate:.3f} | {fx.sep:+.3f} | "
                f"{'yes' if fx.any_timeout else 'no'} |"
            )
        lines.append("")

    REPORT_MD.write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
