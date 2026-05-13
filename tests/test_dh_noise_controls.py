"""
Noise-control battery for the Δh invariant (TASK-3 per V3 protocol).

Purpose
-------
The pre-registered "healthy-critical" band is Δh ∈ [0.11, 0.59] (see
evidence/priors/eeg_resting_literature_prior.yaml). This test battery
verifies that simple stochastic processes — which do not carry critical
dynamics — produce Δh BELOW the lower edge of that band when measured
with the exact same pipeline used for EEG (scale window (16, 512),
q ∈ [-5, 5] step 0.5, fit order 1, n_scales=20).

If any noise control consistently produces Δh ≥ 0.11, the lower edge of
the healthy band is not discriminative and the hypothesis must be
reformulated before further substrates are added.

Pre-registered expectations (from the same generators used in TASK-0):

    white noise        (H = 0.50): Δh ≲ 0.10
    fGn H = 0.30       (rough)    : Δh ≲ 0.10
    fGn H = 0.70       (persist.) : Δh ≲ 0.10
    fGn H = 0.90       (smooth)   : Δh ≲ 0.12

Gate
----
For each generator we draw N=5 independent seeds; the 95th-percentile Δh
across those 5 samples must remain < 0.11 (the EEG healthy-band lower
edge). Using the 95th percentile (not max) tolerates a single outlier
from finite-sample noise without voiding the gate.
"""

from __future__ import annotations

import numpy as np
import pytest

from substrates.physionet_hrv.mfdfa import mfdfa
from tests.test_mfdfa_scale_invariance import fgn_spectral

Q_VALUES = np.arange(-5.0, 5.5, 0.5)
SCALE_RANGE = (16, 512)
N_SEEDS = 5

# Lower edge of the EEG healthy-critical Δh band.
HEALTHY_LOWER_EDGE = 0.11


NOISE_CONTROLS = [
    ("white_noise", 0.50, 0.12),
    ("fgn_rough_H03", 0.30, 0.12),
    ("fgn_persistent_H07", 0.70, 0.12),
    ("fgn_smooth_H09", 0.90, 0.14),
]


@pytest.mark.parametrize(
    "label,H_true,dh_p95_ceiling",
    NOISE_CONTROLS,
    ids=[c[0] for c in NOISE_CONTROLS],
)
def test_noise_control_dh_below_healthy_band(
    label: str, H_true: float, dh_p95_ceiling: float
) -> None:
    """Δh on monofractal noise must sit below the EEG healthy band."""

    dh_values: list[float] = []
    for seed in range(N_SEEDS):
        signal = fgn_spectral(n=4096, H=H_true, seed=seed + 1)
        res = mfdfa(
            signal,
            q_values=Q_VALUES,
            s_min=SCALE_RANGE[0],
            s_max=SCALE_RANGE[1],
            n_scales=20,
            fit_order=1,
        )
        dh_values.append(float(res.delta_h))

    dh_arr = np.asarray(dh_values)
    dh_p95 = float(np.percentile(dh_arr, 95))
    dh_mean = float(dh_arr.mean())
    dh_max = float(dh_arr.max())

    # Visible in CI log whether the test passes or fails.
    print(
        f"\n{label} (H={H_true}): Δh samples = {dh_values}, "
        f"mean={dh_mean:.4f}, p95={dh_p95:.4f}, max={dh_max:.4f}"
    )

    # Primary gate: generator-specific ceiling (documents what we expect).
    assert dh_p95 < dh_p95_ceiling, (
        f"{label}: Δh p95={dh_p95:.4f} exceeded generator ceiling "
        f"{dh_p95_ceiling} — MFDFA pipeline may have a regression."
    )
    # Secondary gate: must stay below the EEG healthy-band lower edge,
    # otherwise the band is not discriminative.
    assert dh_p95 < HEALTHY_LOWER_EDGE, (
        f"{label}: Δh p95={dh_p95:.4f} >= healthy lower edge "
        f"{HEALTHY_LOWER_EDGE}. Band is not discriminative against this noise "
        f"process; protocol V3 must be revised before any cross-substrate run."
    )


def test_noise_controls_all_below_hrv_nsr_mean() -> None:
    """Group gate: aggregate noise Δh must sit below HRV-NSR mean (0.19).

    This is a softer, cross-generator sanity check: the average Δh across
    all noise controls must be meaningfully lower than the empirical
    healthy-cardiac anchor (NSR-HRV Δh ≈ 0.19). Rationale: if noise can
    match the HRV-healthy anchor, then HRV-healthy is not distinguishable
    from noise and the entire multifractal-invariant programme is void.
    """

    all_dh: list[float] = []
    for label, H_true, _ in NOISE_CONTROLS:
        for seed in range(N_SEEDS):
            signal = fgn_spectral(n=4096, H=H_true, seed=seed + 1)
            res = mfdfa(
                signal,
                q_values=Q_VALUES,
                s_min=SCALE_RANGE[0],
                s_max=SCALE_RANGE[1],
                n_scales=20,
                fit_order=1,
            )
            all_dh.append(float(res.delta_h))

    pooled_mean = float(np.mean(all_dh))
    print(f"\nPooled noise Δh mean across {len(all_dh)} runs = {pooled_mean:.4f}")

    assert pooled_mean < 0.19 - 0.02, (
        f"Pooled noise Δh {pooled_mean:.4f} not separated from HRV-NSR anchor 0.19 "
        "by at least 0.02 — multifractal Δh lacks discriminative power vs noise."
    )
