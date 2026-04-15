# NULL-SCREEN-v1.1 Report

> **Date.** 2026-04-15T16:44:50.030914+00:00
> **VERDICT.** `NO_ADMISSIBLE_NULL_FOUND`
> **Chosen family.** `—`
> **Next action.** Freeze the Δh + surrogate line and continue only on the non-null-dependent HRV pathology branch (PR #102).

## Preflight

- **ok:** True
- **message:** preflight OK
- **info:** `{'cascade_delta_h': 0.3555, 'hrv_like_delta_h': 0.1781}`

## Gates (pre-registered)

- `psd` = `0.15`
- `acf` = `0.1`
- `dist_exact` = `1e-10`
- `std_psd` = `0.03`
- `std_acf` = `0.03`
- `std_dh` = `0.02`
- `linear_sep_abs` = `0.03`
- `nonlinear_sep` = `0.05`
- `cascade_preflight` = `0.15`
- `seeds` = `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]`

## Per-family results

### constrained_randomization

- admit: **False**
- preserves_distribution_exactly: True
- fail_codes: ['FAIL_NULL_SEED::white_noise::dh', 'FAIL_NULL_SEED::pink_fgn_H07::dh', 'FAIL_NULL_SEED::phase_rand_1f::dh', 'FAIL_DISC_INJECTION::phase_rand_1f', 'FAIL_NULL_PSD::binomial_cascade_p03', 'FAIL_NULL_ACF::binomial_cascade_p03', 'FAIL_NULL_SEED::binomial_cascade_p03::dh', 'FAIL_NULL_PSD::hrv_like_nonlinear', 'FAIL_NULL_SEED::hrv_like_nonlinear::dh', 'FAIL_DISC_NONLINEAR::hrv_like_nonlinear', 'FAIL_NULL_PSD::nsr001', 'FAIL_NULL_ACF::nsr001', 'FAIL_NULL_SEED::nsr001::dh', 'FAIL_NULL_PSD::nsr002', 'FAIL_NULL_ACF::nsr002', 'FAIL_NULL_SEED::nsr002::dh', 'FAIL_NULL_PSD::nsr003', 'FAIL_NULL_ACF::nsr003', 'FAIL_NULL_SEED::nsr003::psd', 'FAIL_NULL_SEED::nsr003::dh', 'FAIL_NULL_PSD::nsr004', 'FAIL_NULL_SEED::nsr004::dh', 'FAIL_NULL_PSD::nsr005', 'FAIL_NULL_SEED::nsr005::dh']

| fixture | kind | Δh_real | Δh_surr_med | psd | acf | std_dh | sep | TO |
|---|---|---|---|---|---|---|---|---|
| `white_noise` | linear_synth | 0.021 | 0.031 | 0.061 | 0.001 | 0.023 | -0.009 | no |
| `pink_fgn_H07` | linear_synth | 0.041 | 0.058 | 0.054 | 0.001 | 0.024 | -0.017 | no |
| `phase_rand_1f` | linear_synth | 0.066 | 0.126 | 0.131 | 0.007 | 0.034 | -0.060 | no |
| `binomial_cascade_p03` | nonlinear_synth | 0.355 | 0.070 | 4.167 | 0.297 | 0.040 | +0.285 | no |
| `hrv_like_nonlinear` | nonlinear_synth | 0.268 | 0.243 | 0.178 | 0.010 | 0.025 | +0.024 | no |
| `nsr001` | real | 0.486 | 0.069 | 3.382 | 0.109 | 0.020 | +0.417 | no |
| `nsr002` | real | 0.379 | 0.097 | 4.032 | 0.125 | 0.045 | +0.282 | no |
| `nsr003` | real | 0.986 | 0.877 | 4.011 | 0.222 | 0.064 | +0.110 | no |
| `nsr004` | real | 0.448 | 0.173 | 3.964 | 0.079 | 0.049 | +0.275 | no |
| `nsr005` | real | 0.700 | 0.253 | 3.041 | 0.041 | 0.050 | +0.447 | no |

### wavelet_phase

- admit: **False**
- preserves_distribution_exactly: False
- fail_codes: ['FAIL_NULL_PSD::white_noise', 'FAIL_DISC_INJECTION::white_noise', 'FAIL_NULL_PSD::pink_fgn_H07', 'FAIL_NULL_ACF::pink_fgn_H07', 'FAIL_DISC_INJECTION::pink_fgn_H07', 'FAIL_NULL_PSD::phase_rand_1f', 'FAIL_NULL_ACF::phase_rand_1f', 'FAIL_DISC_INJECTION::phase_rand_1f', 'FAIL_NULL_PSD::binomial_cascade_p03', 'FAIL_NULL_SEED::binomial_cascade_p03::dh', 'FAIL_DISC_NONLINEAR::binomial_cascade_p03', 'FAIL_NULL_PSD::hrv_like_nonlinear', 'FAIL_NULL_ACF::hrv_like_nonlinear', 'FAIL_NULL_PSD::nsr001', 'FAIL_NULL_ACF::nsr001', 'FAIL_NULL_PSD::nsr002', 'FAIL_NULL_ACF::nsr002', 'FAIL_NULL_PSD::nsr003', 'FAIL_NULL_ACF::nsr003', 'FAIL_NULL_PSD::nsr004', 'FAIL_NULL_ACF::nsr004', 'FAIL_NULL_PSD::nsr005', 'FAIL_NULL_ACF::nsr005', 'FAIL_DISC_LINEAR']

| fixture | kind | Δh_real | Δh_surr_med | psd | acf | std_dh | sep | TO |
|---|---|---|---|---|---|---|---|---|
| `white_noise` | linear_synth | 0.021 | 0.151 | 0.640 | 0.050 | 0.004 | -0.130 | no |
| `pink_fgn_H07` | linear_synth | 0.041 | 0.188 | 0.650 | 0.122 | 0.007 | -0.147 | no |
| `phase_rand_1f` | linear_synth | 0.066 | 0.147 | 0.650 | 0.333 | 0.012 | -0.081 | no |
| `binomial_cascade_p03` | nonlinear_synth | 0.355 | 0.461 | 0.555 | 0.001 | 0.053 | -0.106 | no |
| `hrv_like_nonlinear` | nonlinear_synth | 0.268 | 0.056 | 0.652 | 0.393 | 0.014 | +0.212 | no |
| `nsr001` | real | 0.486 | 0.212 | 1.796 | 0.174 | 0.011 | +0.274 | no |
| `nsr002` | real | 0.379 | 0.097 | 2.112 | 0.220 | 0.011 | +0.282 | no |
| `nsr003` | real | 0.986 | 0.400 | 1.603 | 0.518 | 0.012 | +0.586 | no |
| `nsr004` | real | 0.448 | 0.073 | 2.003 | 0.304 | 0.016 | +0.375 | no |
| `nsr005` | real | 0.700 | 0.111 | 1.799 | 0.379 | 0.013 | +0.588 | no |

### linear_matched

- admit: **False**
- preserves_distribution_exactly: False
- fail_codes: ['FAIL_NULL_SEED::white_noise::dh', 'FAIL_NULL_PSD::pink_fgn_H07', 'FAIL_NULL_SEED::pink_fgn_H07::dh', 'FAIL_NULL_PSD::phase_rand_1f', 'FAIL_NULL_ACF::phase_rand_1f', 'FAIL_NULL_SEED::phase_rand_1f::dh', 'FAIL_NULL_PSD::binomial_cascade_p03', 'FAIL_NULL_SEED::binomial_cascade_p03::acf', 'FAIL_NULL_SEED::binomial_cascade_p03::dh', 'FAIL_NULL_PSD::hrv_like_nonlinear', 'FAIL_NULL_ACF::hrv_like_nonlinear', 'FAIL_NULL_SEED::hrv_like_nonlinear::dh', 'FAIL_NULL_PSD::nsr001', 'FAIL_NULL_ACF::nsr001', 'FAIL_NULL_SEED::nsr001::dh', 'FAIL_NULL_PSD::nsr002', 'FAIL_NULL_ACF::nsr002', 'FAIL_NULL_SEED::nsr002::dh', 'FAIL_NULL_PSD::nsr003', 'FAIL_NULL_ACF::nsr003', 'FAIL_NULL_SEED::nsr003::psd', 'FAIL_NULL_SEED::nsr003::dh', 'FAIL_NULL_PSD::nsr004', 'FAIL_NULL_ACF::nsr004', 'FAIL_NULL_SEED::nsr004::psd', 'FAIL_NULL_SEED::nsr004::dh', 'FAIL_NULL_PSD::nsr005', 'FAIL_NULL_ACF::nsr005', 'FAIL_NULL_SEED::nsr005::psd', 'FAIL_NULL_SEED::nsr005::dh']

| fixture | kind | Δh_real | Δh_surr_med | psd | acf | std_dh | sep | TO |
|---|---|---|---|---|---|---|---|---|
| `white_noise` | linear_synth | 0.021 | 0.049 | 0.111 | 0.021 | 0.020 | -0.027 | no |
| `pink_fgn_H07` | linear_synth | 0.041 | 0.049 | 0.194 | 0.060 | 0.020 | -0.007 | no |
| `phase_rand_1f` | linear_synth | 0.066 | 0.049 | 0.646 | 0.413 | 0.020 | +0.017 | no |
| `binomial_cascade_p03` | nonlinear_synth | 0.355 | 0.130 | 1.640 | 0.040 | 0.064 | +0.226 | no |
| `hrv_like_nonlinear` | nonlinear_synth | 0.268 | 0.049 | 0.704 | 0.290 | 0.020 | +0.219 | no |
| `nsr001` | real | 0.486 | 0.049 | 3.829 | 0.766 | 0.020 | +0.437 | no |
| `nsr002` | real | 0.379 | 0.049 | 4.389 | 0.696 | 0.020 | +0.330 | no |
| `nsr003` | real | 0.986 | 1.256 | 163.898 | 0.389 | 0.180 | -0.269 | no |
| `nsr004` | real | 0.448 | 1.289 | 22.618 | 0.829 | 0.099 | -0.841 | no |
| `nsr005` | real | 0.700 | 1.269 | 226.797 | 0.518 | 0.251 | -0.569 | no |
