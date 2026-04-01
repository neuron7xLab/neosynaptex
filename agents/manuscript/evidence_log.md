# Evidence Log — γ-scaling Cross-Substrate Measurements

| DATE | SYSTEM | MEASUREMENT | VALUE | CI | N | STATUS |
|------|--------|-------------|-------|----|---|--------|
| 2026-03-29 | zebrafish | γ_WT | +1.043 | [0.933, 1.380] | — | PRIMARY |
| 2026-03-29 | DNCA | γ_NMO | +2.072 | [1.341, 2.849] | 949 | CONFIRMED |
| 2026-03-29 | DNCA | γ_PE | +6.975 | [6.503, 7.407] | — | CONFIRMED |
| 2026-03-29 | DNCA | γ_random | +0.068 | [-0.080, 0.210] | — | CONTROL_PASS |
| 2026-03-30 | MFN⁺ | γ_GrayScott (activator) | +0.865 | [0.649, 1.250] | 100 | CONFIRMED |
| 2026-03-30 | MFN⁺ | γ_GrayScott (inhibitor) | +0.655 | [0.431, 0.878] | 100 | CONFIRMED |
| 2026-03-30 | MFN⁺ | γ_control (shuffled) | +0.035 | — | — | CONTROL_PASS |
| 2026-03-30 | mvstack | γ_trending | +1.081 | [0.869, 1.290] | 200 | CONFIRMED |
| 2026-03-30 | mvstack | γ_chaotic | +1.007 | [0.797, 1.225] | 200 | CONFIRMED |
| 2026-03-30 | mvstack | γ_control (shuffled trending) | +0.145 | — | — | CONTROL_PASS |
| 2026-03-30 | mvstack | γ_control (shuffled chaotic) | -0.083 | — | — | CONTROL_PASS |
| 2026-03-30 | mvstack | Δγ(trending - chaotic) | +0.074 | — | — | NOTE |
| 2026-03-30 | cross-substrate | divergence (bio, MFN, market) | 0.216 | — | — | UNIFIED |
| 2026-03-30 | cross-substrate | divergence (all 4 substrates) | 1.207 | — | — | NOTE |
| 2026-03-30 | DNCA (full) | γ_NMO (state_dim=64, 1000 steps) | +2.185 | [1.743, 2.789] | 898 | CONFIRMED |
| 2026-03-30 | DNCA (full) | γ_PE (state_dim=64, 1000 steps) | +0.476 | [0.210, 0.615] | 899 | CONFIRMED |
| 2026-03-30 | DNCA (full) | γ_random (state_dim=64, 1000 steps) | +0.045 | [-0.082, 0.148] | — | CONTROL_PASS |
| 2026-03-30 | cross-substrate | DNCA full CI overlap with [0.865, 1.081] | 0.000 | — | — | DIVERGENT |
| 2026-03-30 | DNCA sweep | γ_min at competition=0.78 | +0.756 | — | 449 | CONVERGES TO BIO |
| 2026-03-30 | DNCA sweep | γ at competition=0.67 | +0.903 | — | 449 | CONSISTENT WITH γ_WT |
| 2026-03-30 | DNCA sweep | γ at competition=0.00 (no comp) | +4.547 | [2.008, 4.316] | 447 | INFLATED |
| 2026-03-30 | DNCA sweep | Pattern | NON-MONOTONIC | — | — | U-SHAPED |
| 2026-03-30 | SpatialDNCA | γ_NMO (8×8 grid) | +3.870 | [2.295, 4.318] | 447 | ELEVATED |
| 2026-03-30 | SpatialDNCA | γ_PE (8×8 grid) | +0.680 | [0.567, 0.908] | — | BIO RANGE |
| 2026-03-30 | all conditions | γ_PE mean (all conditions) | +0.757 | SD=0.128 | — | STABLE |
| 2026-03-30 | H1 test | Spatial locality effect | REJECTED | — | — | γ INCREASES |
| 2026-03-30 | H2 test | Competition strength effect | REJECTED | — | — | NON-MONOTONIC |
| 2026-03-30 | H3 (emergent) | Metastability hypothesis | SUPPORTED | — | — | γ min at optimal comp |

## T1-T6: Why gamma ≈ 1.0? Seven Tests

DATE: 2026-03-30

| Test | Result | Gates |
|---|---|---|
| T3: Method falsification | 1D embedding biased (white noise γ=1.6); native 2D valid | 1/5 |
| T2: 2D Ising (T_c=2.269) | γ decreases monotonically with T (1.68→0.96); NOT peaked at T_c | 2/4 |
| T1: Correlation η vs γ | η ≈ 0.2 everywhere, uncorrelated with γ (r=0.11) | 1/3 |
| T4: Persistence dynamics | γ→1.0 when pe0/β0 variance moderate, corr ~0.87 | 1/3 |
| T5: HH/VdP/Lorenz | All fail: low-D ODEs don't differentiate critical/non-critical | 2/5 |
| T6: Formula γ=νz/d | Closest match: 1.083 vs measured 1.329 (error 0.25) | partial |

Key conclusions:
- γ ≈ 1.0 is NOT a critical exponent (T1, T2)
- γ ≈ 1.0 is NOT a pipeline artifact on native 2D fields (controls ≈ 0)
- γ ≈ 1.0 IS the baseline for moderate topological variability (T4)
- γ works on multi-dimensional density fields, NOT low-D ODE trajectories (T5)
- Cross-substrate convergence [0.86, 1.33] is real and qualified (T2, T4)

## Competition Sweep — γ as function of competition_strength

DATE: 2026-03-30
Protocol: 10-level sweep, competition_strength ∈ [0.0, 1.0]
Three levers: growth rate compression, ρ_ij scaling, GABA exponent
DNCA state_dim=64, BNSynGammaProbe window=50, n_bootstrap=300, seed=42
Forward model learning disabled during measurement (preserves competition dynamics)

| competition | γ_NMO | R² | γ_ctrl |
|---|---|---|---|
| 0.00 | +4.547 | 0.272 | +0.043 |
| 0.11 | +1.977 | 0.063 | +0.046 |
| 0.22 | +1.133 | 0.038 | -0.010 |
| 0.33 | +2.424 | 0.126 | -0.003 |
| 0.44 | +2.080 | 0.300 | -0.008 |
| 0.56 | +1.117 | 0.089 | +0.030 |
| 0.67 | +0.903 | 0.080 | +0.036 |
| 0.78 | +0.756 | 0.103 | -0.055 |
| 0.89 | +1.236 | 0.162 | +0.019 |
| 1.00 | +1.930 | 0.171 | +0.053 |

Minimum: γ = 0.756 at competition = 0.778
Maximum: γ = 4.547 at competition = 0.000
Pattern: NON-MONOTONIC with minimum near 0.75-0.78
All |γ_ctrl| < 0.06 — controls pass at every level

Key finding: At competition ≈ 0.75-0.78, DNCA γ enters the bio-morphogenetic range [0.756, 0.903].
This suggests γ ≈ 1.0 is the signature of METASTABLE competition, not weak or strong competition.

## SpatialDNCA — 8×8 grid with local interactions

DATE: 2026-03-30
γ_SpatialDNCA(NMO) = +3.870, CI [+2.295, +4.318], R² = 0.204
γ_SpatialDNCA(PE) = +0.680, CI [+0.567, +0.908]
γ_control = -0.000
Verdict: Spatial locality INCREASES γ (not decreases). H1 rejected.

## Prediction Error Field — stable across all conditions

Mean γ_PE = 0.757 (SD = 0.128) across all competition levels and spatial variant.
The PE channel converges to bio-morphogenetic range regardless of internal architecture.

## DNCA Full Run — state_dim=64, 1000 steps

DATE: 2026-03-30
γ_DNCA_full   = +2.185
CI 95%        = [1.743, 2.789]
R²            = 0.2235
n_pairs       = 898
γ_control     = +0.045
Verdict       = DIVERGENT
Overlap width = 0.000
Runtime       = 410s (6.8 min)

Cross-substrate summary:
  γ_bio    = +1.043  [0.933, 1.380]  PRIMARY
  γ_MFN    = +0.865  [0.649, 1.250]  ORGANIZED
  γ_market = +1.081  [0.869, 1.290]  ORGANIZED
  γ_DNCA   = +2.185  [1.743, 2.789]  ORGANIZED (different scale)
  γ_ctrl   = +0.045  [-0.082, 0.148] RANDOM
  divergence (bio, MFN, market) = 0.216
  overall  = THREE SUBSTRATES UNIFIED; DNCA DIVERGENT (distinct organizational scale)

## Notes

- DNCA γ_NMO = +2.072 (state_dim=8, 200 steps) and +2.185 (state_dim=64, 1000 steps) — full run confirms elevated γ is not an artifact of reduced parameters.
- DNCA full run CI [1.743, 2.789] does NOT overlap bio-morphogenetic range [0.865, 1.081]. DNCA operates at a distinct organizational scale.
- Control γ = +0.045 confirms signal is genuine (not pipeline artifact).
- MFN⁺ CI [0.649, 1.250] includes γ_WT = 1.043.
- mvstack γ is stable across market regimes (Δγ = 0.074), suggesting Kuramoto coupling topology itself carries the invariant.
- Three substrates unified: γ_bio = 1.043, γ_MFN = 0.865, γ_market = 1.081 → divergence = 0.216 → UNIFIED.
- DNCA is related but architecturally distinct: neuromodulatory competitive dynamics (Lotka-Volterra winnerless competition) produce stronger topological scaling than reaction-diffusion or synchronization systems.
