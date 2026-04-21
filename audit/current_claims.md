# Phase 0B · Current claims per SURFACE

Extracted verbatim lines mentioning γ/Kuramoto/universality/cost-complexity
from every SURFACE-class file identified in surfaces.yaml.

Total SURFACE files: 231

## .github/BRANCH_PROTECTION.md

_matches: 3_

```
.github/BRANCH_PROTECTION.md:24:| 7 | `check` | `.github/workflows/gamma_ledger_integrity.yml` | `evidence/gamma_ledger.json` entries satisfy structural invariants (CI envelope, positive γ, canonical status, T1–T5 tier). |
.github/BRANCH_PROTECTION.md:25:| 8 | (ci.yml jobs) | `.github/workflows/ci.yml` | Lint (Ruff), types (mypy), tests (matrix), γ formula verify, axiom verification, import-linter. Multiple job names. |
.github/BRANCH_PROTECTION.md:66:      "gamma_ledger_integrity / check"
```

## .github/dependabot.yml

_matches: 7_

```
.github/dependabot.yml:11:#   npm (x2)        — the two JS/TS subprojects under substrates/kuramoto:
.github/dependabot.yml:79:  # ── npm: substrates/kuramoto/apps/web (Next.js) ─────────────────────
.github/dependabot.yml:81:    directory: "/substrates/kuramoto/apps/web"
.github/dependabot.yml:114:  # ── cargo: substrates/kuramoto/rust/tradepulse-accel ────────────────
.github/dependabot.yml:116:    directory: "/substrates/kuramoto/rust/tradepulse-accel"
.github/dependabot.yml:132:  # ── npm: substrates/kuramoto/ui/dashboard (Playwright + ESLint) ─────
.github/dependabot.yml:134:    directory: "/substrates/kuramoto/ui/dashboard"
```

## .github/workflows/benchmarks.yml

_matches: 6_

```
.github/workflows/benchmarks.yml:34:      - name: Substrate γ benchmarks
.github/workflows/benchmarks.yml:43:          for name, (gamma, note) in SUBSTRATE_GAMMA.items():
.github/workflows/benchmarks.yml:45:              regime = classify_regime(gamma)
.github/workflows/benchmarks.yml:47:              status = 'PASS' if abs(gamma - 1.0) < 0.15 else 'WARN'
.github/workflows/benchmarks.yml:48:              print(f'{status} {name:20s} γ={gamma:.4f} regime={regime} ({dt*1000:.1f}ms)')
.github/workflows/benchmarks.yml:64:        run: python3 -c "from core.axioms import SUBSTRATE_GAMMA, gamma_psd, verify_axiom_consistency; print('axioms OK:', len(SUBSTRATE_GAMMA), 'substrates')"
```

## .github/workflows/ci.yml

_matches: 9_

```
.github/workflows/ci.yml:79:      - name: Verify gamma_PSD = 2H+1 formula
.github/workflows/ci.yml:85:          print('gamma_PSD = 2H+1: VERIFIED')
.github/workflows/ci.yml:90:        run: python3 -c "from core.axioms import SUBSTRATE_GAMMA, gamma_psd, verify_axiom_consistency; print('axioms OK:', len(SUBSTRATE_GAMMA), 'substrates')"
.github/workflows/ci.yml:114:      - name: INV-1 — gamma never stored
.github/workflows/ci.yml:123:                      if isinstance(item, ast.Attribute) and item.attr == 'gamma':
.github/workflows/ci.yml:125:                              raise AssertionError(f'INV-1 VIOLATED: gamma stored at line {item.lineno}')
.github/workflows/ci.yml:126:          print('INV-1 OK: gamma never stored as attribute')
.github/workflows/ci.yml:199:      - name: Verify gamma formula
.github/workflows/ci.yml:205:          print('gamma_PSD = 2H+1: VERIFIED')
```

## .github/workflows/docker-reproduce.yml

_matches: 6_

```
.github/workflows/docker-reproduce.yml:21:      - "evidence/gamma_ledger.json"
.github/workflows/docker-reproduce.yml:73:          from core.gamma import compute_gamma
.github/workflows/docker-reproduce.yml:76:          from substrates.kuramoto.adapter import KuramotoAdapter
.github/workflows/docker-reproduce.yml:77:          from substrates.serotonergic_kuramoto.adapter import SerotonergicKuramotoAdapter
.github/workflows/docker-reproduce.yml:85:          with open('evidence/gamma_ledger.json') as f:
.github/workflows/docker-reproduce.yml:98:            tests/test_gamma_invariant.py \
```

## .github/workflows/gamma_ledger_integrity.yml

_matches: 6_

```
.github/workflows/gamma_ledger_integrity.yml:1:name: gamma_ledger_integrity
.github/workflows/gamma_ledger_integrity.yml:3:# Every entry in ``evidence/gamma_ledger.json`` MUST satisfy the
.github/workflows/gamma_ledger_integrity.yml:4:# γ-ledger structural invariants (required keys, CI envelope,
.github/workflows/gamma_ledger_integrity.yml:5:# positive γ, canonical status, T1–T5 method tier, boolean locked,
.github/workflows/gamma_ledger_integrity.yml:33:      - name: Run γ-ledger integrity check
.github/workflows/gamma_ledger_integrity.yml:34:        run: python -m tools.audit.gamma_ledger_integrity
```

## .pre-commit-config.yaml

_matches: 4_

```
.pre-commit-config.yaml:29:  # under substrates/kuramoto/deploy/ and substrates/mlsdm/deploy/
.pre-commit-config.yaml:36:        files: ^(neosynaptex\.py|core/|contracts/|evl/|tests/|substrates/(serotonergic_kuramoto|hrv|lotka_volterra|gray_scott|bn_syn|eeg_physionet|hrv_physionet|hrv_fantasia|eeg_resting|zebrafish|cfp_diy|cns_ai_loop|hippocampal_ca1|mfn)/).*\.py$
.pre-commit-config.yaml:38:        files: ^(neosynaptex\.py|core/|contracts/|evl/|tests/|substrates/(serotonergic_kuramoto|hrv|lotka_volterra|gray_scott|bn_syn|eeg_physionet|hrv_physionet|hrv_fantasia|eeg_resting|zebrafish|cfp_diy|cns_ai_loop|hippocampal_ca1|mfn)/).*\.py$
.pre-commit-config.yaml:59:          - tests/test_gamma_invariant.py
```

## AUDIT_REPORT_2026-04-01.md

_matches: 25_

```
AUDIT_REPORT_2026-04-01.md:2:This repository is not ready to be the single canonical repo. It is a meta-monorepo that aggregates multiple independently-canonical systems (Neosynaptex core, BN-Syn, TradePulse/Kuramoto, MLSDM, Mycelium/MFN+, neuron7x-agents) with conflicting package identities, duplicated codebases, mixed licenses, and non-hermetic test/dependency surfaces. Canonical R&D value is high, but authority is split across parallel truth layers; archive operations on predecessor repos are unsafe until authority ownership, migration map, and reproducibility contracts are normalized.
AUDIT_REPORT_2026-04-01.md:9:- Strategic center: root `neosynaptex.py` + `contracts/` + `core/` + root tests for gamma/coherence contract.
AUDIT_REPORT_2026-04-01.md:12:  - Imported substrate stacks: `substrates/bn_syn`, `substrates/kuramoto`, `substrates/mlsdm`, `substrates/mfn_plus`, `substrates/mycelium`.
AUDIT_REPORT_2026-04-01.md:17:- `neosynaptex.py` -> integration runtime for gamma/coherence -> canonical.
AUDIT_REPORT_2026-04-01.md:22:- `substrates/kuramoto/` -> standalone TradePulse platform -> drifted (independent canonical).
AUDIT_REPORT_2026-04-01.md:77:- source: `substrates/kuramoto/docs/requirements/traceability_matrix.md`
AUDIT_REPORT_2026-04-01.md:78:  target: `docs/traceability/kuramoto_traceability_matrix.md`
AUDIT_REPORT_2026-04-01.md:83:- source: `substrates/kuramoto/data/golden/**`
AUDIT_REPORT_2026-04-01.md:84:  target: `data/golden/kuramoto/**`
AUDIT_REPORT_2026-04-01.md:92:- `substrates/kuramoto/docs/adr/**` -> `docs/adr/kuramoto/**` -> OPTIONAL_HIGH_VALUE -> cross-subsystem design rationale.
AUDIT_REPORT_2026-04-01.md:121:  competing licenses: root AGPL, `agents` MIT, `kuramoto` proprietary label
AUDIT_REPORT_2026-04-01.md:165:Repository contains significant intellectual capital but is architecturally multi-canonical, not singular. Root Neosynaptex runtime and contracts form one coherent core, while BN-Syn, TradePulse/Kuramoto, MLSDM, neuron7x-agents, and Mycelium/MFN+ remain semi-independent systems with their own manifests, CI, and governance surfaces. Highest-risk issue is split authority: duplicate package ownership (`mfn_plus` vs `mycelium`) and dual BN-Syn surfaces (`bn_syn/` vs `substrates/bn_syn/`) create non-deterministic maintenance and archival risk. Proof, benchmark, and bibliography assets are rich but fragmented; no unified root evidence spine exists. Mixed license regimes across subtree packages further block canonical archival decisions. Immediate value is preserved by locking ownership, migrating duplicated surfaces into single authorities, centralizing evidence/claim ledgers, and partitioning CI/test/dependency boundaries per subsystem. Until these migrations and governance artifacts are completed, old-repo archival is unsafe and canonical-repo status is not achieved.
AUDIT_REPORT_2026-04-01.md:183:    own gamma outside the protocol (via `get_gamma_result` /
AUDIT_REPORT_2026-04-01.md:184:    `compute_gamma`) are recorded as protocol-compatibility-shim
AUDIT_REPORT_2026-04-01.md:187:    (all derive gamma directly from per-subject DFA / aperiodic
AUDIT_REPORT_2026-04-01.md:189:    never touches the reported gamma).
AUDIT_REPORT_2026-04-01.md:191:    perturbation in between; the reported gamma must differ and the
AUDIT_REPORT_2026-04-01.md:192:    adapter must carry no `gamma` or `_gamma_cached` attribute.
AUDIT_REPORT_2026-04-01.md:193:  - C — Window gaming: synthetic stream with known `gamma_true = 1.0`
AUDIT_REPORT_2026-04-01.md:194:    is run through `core.gamma.compute_gamma` at window in
AUDIT_REPORT_2026-04-01.md:195:    {8, 16, 32, 64}; every recovered gamma must lie in [0.80, 1.20]
AUDIT_REPORT_2026-04-01.md:197:  - D — Adversarial injection: an adapter providing `gamma = 1.0`,
AUDIT_REPORT_2026-04-01.md:198:    `_gamma_cached = 1.0`, `_compute_gamma()` returning 1.0, and a
AUDIT_REPORT_2026-04-01.md:199:    `"gamma"` key in its state dict is registered with `gamma_true`
AUDIT_REPORT_2026-04-01.md:202:    `observe()` body contains no `adapter.gamma` attribute access.
```

## CANONICAL_OWNERSHIP.yaml

_matches: 8_

```
CANONICAL_OWNERSHIP.yaml:18:      - tests/test_gamma_invariant.py
CANONICAL_OWNERSHIP.yaml:20:      - tests/test_kuramoto_real.py
CANONICAL_OWNERSHIP.yaml:38:    scope: "Mycelium Fractal Net — morphogenetic integrity + γ-scaling"
CANONICAL_OWNERSHIP.yaml:48:  kuramoto:
CANONICAL_OWNERSHIP.yaml:50:    scope: "TradePulse/Kuramoto + curvature + OFI microstructure"
CANONICAL_OWNERSHIP.yaml:52:      - substrates/kuramoto/
CANONICAL_OWNERSHIP.yaml:159:    - tests/test_gamma_invariant.py
CANONICAL_OWNERSHIP.yaml:161:    - tests/test_kuramoto_real.py
```

## CANONICAL_POSITION.md

_matches: 7_

```
CANONICAL_POSITION.md:3:> γ ≈ 1.0 is a **candidate cross-substrate regime marker** of metastable critical regimes in coupled, productive dynamical systems. The protocol treats it as a **falsifiable hypothesis under active test** — not a confirmed correlate, not a universal law, not a definition of intelligence. Current evidence is **substrate-dependent**: `evidence/replications/registry.yaml` records both supportive and falsifying verdicts.
CANONICAL_POSITION.md:5:> The Neosynaptex protocol requires **independent replication**, **falsification tests**, **adversarial controls**, and **active counter-example search**. Levin provides the biological precedent for distributed agency; the operational bridge between **H** (integration horizon), **C** (coordination), **γ** (metastability), and **P** (productivity) is under audit **directly at every level of systemic description**.
CANONICAL_POSITION.md:15:**Canonical.** This file is the single reference every manuscript, README, release note, and agent-generated artefact must align with when describing the scope of the γ claim.
CANONICAL_POSITION.md:19:- "γ ≈ 1 defines intelligence / cognition / agency."
CANONICAL_POSITION.md:20:- "γ ≈ 1 proves [anything about a specific substrate without the four falsification requirements being met on that substrate]."
CANONICAL_POSITION.md:26:1. **Independent replication** — at least one party who did not build the estimator reproduces the γ value from raw substrate output.
CANONICAL_POSITION.md:42:- `experiments/lm_substrate/README.md` — existing falsification record for stateless LLM-API inference (γ ≈ 0).
```

## CFP_PROTOCOL.md

_matches: 21_

```
CFP_PROTOCOL.md:157:gamma-CRR ~ 1.0 -> metastable regime
CFP_PROTOCOL.md:165:* For fBm: gamma_PSD = 2H + 1 (NEVER 2H - 1)
CFP_PROTOCOL.md:190:| F2: CRR collapse       | universal degradation |
CFP_PROTOCOL.md:192:| F4: gamma mismatch     | no universality       |
CFP_PROTOCOL.md:211:5. gamma-CRR estimation
CFP_PROTOCOL.md:229:+-- Biological:    Zebrafish (McGuirl 2020)     gamma = +1.055
CFP_PROTOCOL.md:230:+-- Morphogenetic: MFN+ (Gray-Scott)            gamma = +0.979
CFP_PROTOCOL.md:231:+-- Oscillatory:   mvstack (Kuramoto)            gamma = +0.963
CFP_PROTOCOL.md:232:+-- Neural:        BN-Syn / DNCA                 gamma = +0.946
CFP_PROTOCOL.md:233:+-- Cognitive:     CNS-AI Loop                   gamma = +1.059
CFP_PROTOCOL.md:234:+-- Co-adaptive:   CFP/DIY (human+AI)            gamma = +1.832 (CONSTRUCTED, ABM)
CFP_PROTOCOL.md:239:* gamma derived only, never assigned
CFP_PROTOCOL.md:250:| 1     | N=1 self-experiment | CRR, CPR, preliminary gamma-CRR |
CFP_PROTOCOL.md:276:* After cross-substrate gamma alignment -> Universal principle
CFP_PROTOCOL.md:286:| `adapter.py` | ABM simulation: 50 agents, 25 AI-quality regimes, emergent gamma |
CFP_PROTOCOL.md:287:| `metrics.py` | CRR, CPR, MTLD, S-score, gamma-CRR (PSD + Theil-Sen) |
CFP_PROTOCOL.md:296:gamma  = 1.832  (COLLAPSE zone, NOT metastable)
CFP_PROTOCOL.md:303:as AI quality increases. The system is NOT in metastable equilibrium.
CFP_PROTOCOL.md:305:real human data may produce different gamma.
CFP_PROTOCOL.md:309:1. AST scan: no `gamma = <float>` assignments in adapter source
CFP_PROTOCOL.md:313:5. gamma is whatever the simulation produces
```

## CONTRACT.md

_matches: 30_

```
CONTRACT.md:27:| I-1 | Gamma is derived, never stored | `observe()` recomputes every call; no `gamma` attribute on `Neosynaptex` |
CONTRACT.md:43:   topo,            │  3. Per-domain gamma + bootstrap CI   │
CONTRACT.md:45:                    │  5. Permutation test (universal H0)   │
CONTRACT.md:81:thermo_cost ~ A * topo^(-gamma)
CONTRACT.md:84:when the subsystem operates near its critical point. The scaling exponent `gamma` is what
CONTRACT.md:86:gamma estimate will be gated out (R^2 < 0.5 or range < 0.5).
CONTRACT.md:94:| psyche | PsycheCore | free_energy, kuramoto_r | oscillator count | variational free energy |
CONTRACT.md:110:   gamma = -slope
CONTRACT.md:118:dg/dt = theilslopes(gamma_mean_trace[-W:], arange(W))
CONTRACT.md:121:Negative dg/dt with gamma > 1.0 = converging toward criticality.
CONTRACT.md:126:H0: all domains share the same gamma distribution
CONTRACT.md:149:  Restricted model: gamma_target(t) ~ gamma_target(t-1)
CONTRACT.md:150:  Full model:       gamma_target(t) ~ gamma_target(t-1) + gamma_source(t-1)
CONTRACT.md:158:  coherence_without_d = 1 - CV(gammas excluding d)
CONTRACT.md:159:  coherence_with_all  = 1 - CV(all gammas)
CONTRACT.md:166:Points: (gamma_mean(t), sr(t)) for t in trace
CONTRACT.md:200:mod(domain) = clip(-0.05 * (gamma_domain - 1.0) * sign(dg/dt), -0.05, +0.05)
CONTRACT.md:203:Positive mod = strengthen domain (gamma too low and falling).
CONTRACT.md:204:Negative mod = dampen domain (gamma too high and rising).
CONTRACT.md:217:    gamma_per_domain: Dict[str, float]              # gamma or NaN
CONTRACT.md:218:    gamma_ci_per_domain: Dict[str, Tuple[float, float]]  # (ci_low, ci_high) or NaN
CONTRACT.md:219:    gamma_mean: float                               # mean of valid gammas
CONTRACT.md:220:    gamma_std: float                                # std of valid gammas
CONTRACT.md:221:    cross_coherence: float                          # 1 - CV(gamma_valid)
CONTRACT.md:223:    dgamma_dt: float                                # convergence rate
CONTRACT.md:224:    gamma_ema_per_domain: Dict[str, float]          # exponential moving average
CONTRACT.md:226:    universal_scaling_p: float                      # permutation test p-value
CONTRACT.md:252:| Min pairs gate | `>= 5` valid (topo, cost) pairs for gamma |
CONTRACT.md:266:  gamma: {per_domain: {name: {value, ci, r2, ema}}, mean, std, dgamma_dt, universal_scaling_p},
CONTRACT.md:290:- Adaptive window sizing based on gamma CI width
```

## CONTRIBUTING.md

_matches: 16_

```
CONTRIBUTING.md:29:# Should print: AXIOM_0: CONSISTENT | N substrates | gamma=0.xxxx
CONTRIBUTING.md:85:gamma_mean = compute_gamma(topo, cost)
CONTRIBUTING.md:89:# gamma_сред = ...       # Cyrillic
CONTRIBUTING.md:141:Expected gamma: <value> (CI: [<low>, <high>])
CONTRIBUTING.md:206:from core.gamma import compute_gamma
CONTRIBUTING.md:209:def test_my_substrate_gamma_in_range():
CONTRIBUTING.md:210:    """gamma CI must contain 1.0 (or be documented as out-of-regime)."""
CONTRIBUTING.md:219:    gamma, r2, ci_lo, ci_hi, _ = compute_gamma(
CONTRIBUTING.md:222:    assert np.isfinite(gamma), "gamma must be finite"
CONTRIBUTING.md:246:After validating your substrate, add an entry to `evidence/gamma_ledger.json`:
CONTRIBUTING.md:253:    "gamma": <measured value>,
CONTRIBUTING.md:284:fix/gamma-bootstrap-edge-case
CONTRIBUTING.md:286:refactor/core-gamma-cleanup
CONTRIBUTING.md:297:- [ ] If adding a substrate: entry in `evidence/gamma_ledger.json`
CONTRIBUTING.md:298:- [ ] If changing gamma computation: update `docs/adr/` if a new decision is made
CONTRIBUTING.md:321:core/                   # reusable math: gamma, bootstrap, axioms, ...
```

## LICENSE_BOUNDARIES.md

_matches: 3_

```
LICENSE_BOUNDARIES.md:10:| Root Neosynaptex | `/` (excluding `agents/`, `substrates/kuramoto/`) | AGPL-3.0-or-later | AGPL-compatible code only in root runtime package |
LICENSE_BOUNDARIES.md:12:| TradePulse/Kuramoto | `substrates/kuramoto/` | AGPL-3.0-or-later | Isolated subsystem boundary |
LICENSE_BOUNDARIES.md:24:- ~~Kuramoto final license posture~~: **RESOLVED** — AGPL-3.0-or-later (2026-04-01).
```

## PROTOCOL.md

_matches: 8_

```
PROTOCOL.md:16:| 7. Temporal gamma viz | DONE | -- | e609cc2 |
PROTOCOL.md:27:gamma = 0.994 | 6 substrates | slope = -0.0016 | CONFIRMED
PROTOCOL.md:34:| I | GAMMA DERIVED ONLY | `enforce_gamma_derived()` raises `InvariantViolation` |
PROTOCOL.md:42:gamma_PSD = 2H + 1    (VERIFIED, NEVER 2H-1)
PROTOCOL.md:43:H=0.5 -> gamma=2.0    (Brownian, known result)
PROTOCOL.md:44:H->0  -> gamma=1.0    (anti-persistent)
PROTOCOL.md:45:H->1  -> gamma=3.0    (persistent)
PROTOCOL.md:58:gamma_trajectory.pdf          3-panel publication figure
```

## README.md

_matches: 38_

```
README.md:13:  <i>NFI Integrating Mirror Layer &mdash; gamma-scaling diagnostics across biological, physical, and cognitive systems.</i>
README.md:17:  <a href="#the-number"><img src="https://img.shields.io/badge/%CE%B3%20%E2%89%88%201.0-universal-gold?style=for-the-badge" alt="gamma"></a>
README.md:44:         gamma-scaling across substrates
README.md:64:### K ~ C<sup>-gamma</sup>
README.md:68:gamma = 1.0 is not a tuned parameter. It is a **measured invariant** across:
README.md:78:gamma = 0.991 +/- 0.052
README.md:101:<code>gamma = 1.043</code><br>
README.md:117:<code>gamma = 0.865</code><br>
README.md:133:<code>gamma = 0.950</code><br>
README.md:149:<code>gamma = 1.081</code><br>
README.md:164:<code>gamma = 1.030</code><br>
README.md:183:<sub>Historical figures γ≈1.059, n≈8271 are <b>not evidence</b>.</sub><br>
README.md:189:<sub>Five validated substrates have 95% CI containing gamma = 1.0. The CNS-AI Loop cell is retained for historical continuity only (downgraded 2026-04-14).</sub>
README.md:203:<code>gamma = 1.832</code><br>
README.md:218:<code>gamma = -0.094</code><br>
README.md:238:   PsycheCore -----+  ||   Layer 1: Collect       ||  |          +-- gamma_per_domain + CI
README.md:266:   gamma = 1.138              gamma = -0.557
README.md:284:Non-productive sessions show **anti-scaling** (gamma < 0): complexity and cost move in the same direction. No computation. Just noise.
README.md:286:Productive sessions converge toward gamma = 1.0: **the system computes.**
README.md:302:                         |   |gamma - 1| < 0.15             |
README.md:334:nx.register(MockBnSynAdapter())   # gamma ~ 0.95
README.md:335:nx.register(MockMfnAdapter())     # gamma ~ 1.00
README.md:340:print(f"gamma = {s.gamma_mean:.3f}")          # 1.030
README.md:352:| 1 | **Gamma scaling** | K ~ C^(-gamma) via Theil-Sen | per-domain gamma + 95% bootstrap CI |
README.md:353:| 2 | **Gamma dynamics** | dg/dt = slope of gamma trace | convergence rate toward gamma = 1.0 |
README.md:354:| 3 | **Universal scaling** | Permutation test, H0: all gamma equal | p-value |
README.md:356:| 5 | **Granger causality** | F-test: gamma_i(t-1) --> gamma_j(t) | directed influence graph |
README.md:358:| 7 | **Phase portrait** | Convex hull + recurrence in (gamma, rho) | trajectory topology |
README.md:359:| 8 | **Resilience** | Return rate after METASTABLE departures | metastability proof |
README.md:360:| 9 | **Modulation** | m = -alpha(gamma - 1)sgn(dg/dt) | bounded reflexive signal |
README.md:399:| I | **gamma derived only** | recomputed every `observe()`, never stored |
README.md:414:+-- neosynaptex.py                    engine: γ-scaling, Jacobian, phase dynamics
README.md:421:|   +-- lm_substrate/                 GPT-4o-mini γ derivation (null result)
README.md:424:+-- evidence/                         gamma_ledger.json + proof chains
README.md:463:Contract: `C ~ topo^(-gamma)`. The adapter provides `topo` and `thermo_cost` such that this power-law holds near criticality.
README.md:487:GPT-4o-mini via API: **gamma = -0.094 (null result)**. Stateless inference has no temporal structure. Confirms that gamma != 0 requires closed-loop dynamics, not isolated sampling.
README.md:498:Its scaling signature is gamma = 1.0.
README.md:517:   *       .    gamma = 1.0    .       *
```

## REPO_TOPOLOGY.md

_matches: 26_

```
REPO_TOPOLOGY.md:15:├── neosynaptex.py          ← Single-file engine (1384 LOC, all γ computation)
REPO_TOPOLOGY.md:19:│   ├── coherence_state_space.py  ← 4-D state-space model (S, γ, E_obj, σ²)
REPO_TOPOLOGY.md:20:│   ├── gamma_fdt_estimator.py    ← FDT γ-estimator (auto, not manual tuning)
REPO_TOPOLOGY.md:25:│   └── ... (21 legacy modules: gamma, falsification, iaaft, rqa, etc.)
REPO_TOPOLOGY.md:28:│   ├── proofs.py           ← 3 machine-verifiable theorems (γ=2H+1, susceptibility, INV-YV1)
REPO_TOPOLOGY.md:36:├── evidence/               ← gamma_ledger.json (16 entries) + proof chains
REPO_TOPOLOGY.md:43:## Substrate Map (from gamma_ledger.json)
REPO_TOPOLOGY.md:47:| Substrate | γ | CI | Domain | Source |
REPO_TOPOLOGY.md:51:| Kuramoto | 0.963 | [0.93, 1.00] | Network dynamics | 128-oscillator phase sync |
REPO_TOPOLOGY.md:56:| Serotonergic Kuramoto | 1.068 | — | Network dynamics | 5-HT modulated oscillators |
REPO_TOPOLOGY.md:60:| Substrate | γ | Status | Note |
REPO_TOPOLOGY.md:65:| CFP/ДІЙ | 1.832 | CONSTRUCTED | Outlier — ABM, not γ ≈ 1 |
REPO_TOPOLOGY.md:73:| **`axioms.py`** | **INV-YV1 + AXIOM_0 + γ_PSD = 2H+1 + check_inv_yv1()** |
REPO_TOPOLOGY.md:74:| **`coherence_state_space.py`** | **4-D state-space model (S, γ, E_obj, σ²)** |
REPO_TOPOLOGY.md:75:| **`gamma_fdt_estimator.py`** | **FDT γ-estimator (auto-calibration, not manual)** |
REPO_TOPOLOGY.md:83:| `gamma.py` | Canonical compute_gamma() with bootstrap CI |
REPO_TOPOLOGY.md:84:| `gamma_registry.py` | Read-only gateway to gamma_ledger.json |
REPO_TOPOLOGY.md:92:| `coherence.py` | Transfer entropy γ estimation |
REPO_TOPOLOGY.md:107:| `proofs.py` | 3 machine-verifiable theorems (γ=2H+1, susceptibility, INV-YV1) |
REPO_TOPOLOGY.md:117:| LM Substrate | `experiments/lm_substrate/` | Stateless γ≈0 (null result) |
REPO_TOPOLOGY.md:126:| Benchmarks | `benchmarks.yml` | γ substrate benchmarks, core test performance | GREEN |
REPO_TOPOLOGY.md:135:| I | γ derived only, never assigned | `gamma_registry.py` + AST tests |
REPO_TOPOLOGY.md:144:gamma_ledger.json → gamma_registry.py → neosynaptex.py (read-only)
REPO_TOPOLOGY.md:153:3. Kuramoto license — AGPL-3.0-or-later
REPO_TOPOLOGY.md:166:Single source of truth: `core/gamma.py:compute_gamma()`.
REPO_TOPOLOGY.md:167:All other gamma implementations (`neosynaptex.py:_per_domain_gamma`, `xform_session_probe.py:gamma_probe`)
```

## XFORM_MANUSCRIPT_DRAFT.md

_matches: 17_

```
XFORM_MANUSCRIPT_DRAFT.md:13:We report empirical evidence for a universal scaling exponent gamma ≈ 1.0
XFORM_MANUSCRIPT_DRAFT.md:16:exponent is defined through the power-law relation K ~ C^(-gamma) between
XFORM_MANUSCRIPT_DRAFT.md:17:thermodynamic cost K and topological complexity C. A value of gamma = 1.0
XFORM_MANUSCRIPT_DRAFT.md:18:corresponds to the metastable regime where cost and complexity scale inversely
XFORM_MANUSCRIPT_DRAFT.md:21:**Key result:** Mean gamma across six validated Tier-1/Tier-2 substrates is
XFORM_MANUSCRIPT_DRAFT.md:24:human EEG) reproduce gamma ≈ 1.0 from real external data. Four simulation
XFORM_MANUSCRIPT_DRAFT.md:25:substrates (Gray-Scott, Kuramoto, BN-Syn, serotonergic Kuramoto) validate
XFORM_MANUSCRIPT_DRAFT.md:26:the theoretical prediction. One out-of-regime control (cfp_diy, gamma = 1.83)
XFORM_MANUSCRIPT_DRAFT.md:35:> For all substrates S_i at metastability: gamma(S_i) in [0.85, 1.15] with
XFORM_MANUSCRIPT_DRAFT.md:38:H1 is supported if gamma in [0.85, 1.15] across N >= 3 independent substrates
XFORM_MANUSCRIPT_DRAFT.md:43:> The regime gamma ≈ 1 maximises computational capacity at minimal cost of
XFORM_MANUSCRIPT_DRAFT.md:52:| Substrate | Tier | gamma | 95% CI | R2 | Status |
XFORM_MANUSCRIPT_DRAFT.md:60:| kuramoto | T3 | 0.963 | [0.93, 1.00] | 0.90 | VALIDATED |
XFORM_MANUSCRIPT_DRAFT.md:62:| serotonergic_kuramoto | T5 | 1.068 | [0.145, 1.506] | — | VALIDATED |
XFORM_MANUSCRIPT_DRAFT.md:73:`core/gamma.py::compute_gamma`. Negative controls (white noise, random walk,
XFORM_MANUSCRIPT_DRAFT.md:74:supercritical) show gamma clearly separated from 1.0, confirming the
XFORM_MANUSCRIPT_DRAFT.md:87:For the evidence ledger see [`evidence/gamma_ledger.json`](evidence/gamma_ledger.json).
```

## XFORM_NEURO_DIGITAL_SYMBIOSIS.md

_matches: 1_

```
XFORM_NEURO_DIGITAL_SYMBIOSIS.md:28:**7. Гармонія γ ≈ 1.0**
```

## agents/CHANGELOG.md

_matches: 3_

```
agents/CHANGELOG.md:11:  - Kuramoto phase coupling with MetastabilityEngine.
agents/CHANGELOG.md:15:  - BNSynGammaProbe — TDA-based gamma-scaling measurement (Theil-Sen + bootstrap CI).
agents/CHANGELOG.md:26:- NFI bridge gamma probe window_size corrected from 30 to 50 for stable estimates.
```

## agents/README.md

_matches: 9_

```
agents/README.md:3:Cognition is the regulated succession of metastable dominant regimes over a shared
agents/README.md:5:through Lotka-Volterra dynamics, couple via Kuramoto phase oscillators, and maintain
agents/README.md:6:metastability through active regulation. Each operator runs its own Dominant-Acceptor
agents/README.md:17:**Gamma probe**: TDA-based gamma-scaling measurement. gamma_DNCA ~ +1.0 (consistent with gamma_WT = +1.043, McGuirl 2020 zebrafish).
agents/README.md:115:| **Eq.7** | Damping | `Ŝ(t) ← Ŝ(t-1) + γ · (Ŝ_raw - Ŝ(t-1))` |
agents/README.md:151:    "What drives gamma oscillations in cortical circuits?",
agents/README.md:158:            "PV+ interneurons generate gamma via PING mechanism",
agents/README.md:259:   │ gamma-scaling    │  │ sleep-wake       │  │ HippoRAG for LLM  │
agents/README.md:309:*gamma = coherence. not a metric — a consequence.*
```

## agents/docs/BIBLIOGRAPHY.md

_matches: 15_

```
agents/docs/BIBLIOGRAPHY.md:34:| **Kuramoto coupling** | `dnca/coupling/` | Kuramoto 1984; Acebrón+ 2005 | F, A |
agents/docs/BIBLIOGRAPHY.md:35:| **Gamma probe (TDA)** | `dnca/gamma_probe/` | Edelsbrunner+ 2002; Carlsson 2009; McGuirl+ 2020 | F, A |
agents/docs/BIBLIOGRAPHY.md:49:**[F1]** Kuramoto Y. (1984). *Chemical Oscillations, Waves, and Turbulence*. Springer. DOI: [10.1007/978-3-642-69689-3](https://doi.org/10.1007/978-3-642-69689-3)
agents/docs/BIBLIOGRAPHY.md:68:Persistent homology — TDA-based gamma probe.
agents/docs/BIBLIOGRAPHY.md:92:**[A7]** Rabinovich M.I., Huerta R., Varona P., Afraimovich V.S. (2008). Transient cognitive dynamics, metastability, and decision making. *PLoS Comput. Biol.*, 4(5), e1000072. DOI: [10.1371/journal.pcbi.1000072](https://doi.org/10.1371/journal.pcbi.1000072)
agents/docs/BIBLIOGRAPHY.md:95:**[A8]** Acebrón J.A., Bonilla L.L., Pérez Vicente C.J., Ritort F., Spigler R. (2005). The Kuramoto model: A simple paradigm for synchronization phenomena. *Rev. Mod. Phys.*, 77(1), 137--185. DOI: [10.1103/RevModPhys.77.137](https://doi.org/10.1103/RevModPhys.77.137)
agents/docs/BIBLIOGRAPHY.md:96:Kuramoto review — order parameter r(t) in DNCA coherence.
agents/docs/BIBLIOGRAPHY.md:111:TDA survey — gamma probe methodology.
agents/docs/BIBLIOGRAPHY.md:122:**[A17]** Cardin J.A. et al. (2009). Driving fast-spiking cells induces gamma rhythm and controls sensory responses. *Nature*, 459(7247), 663--667. DOI: [10.1038/nature08002](https://doi.org/10.1038/nature08002)
agents/docs/BIBLIOGRAPHY.md:123:PV+ interneurons generate gamma via PING — cited in examples.
agents/docs/BIBLIOGRAPHY.md:125:**[A18]** Buzsáki G., Wang X.-J. (2012). Mechanisms of gamma oscillations. *Annu. Rev. Neurosci.*, 35, 203--225. DOI: [10.1146/annurev-neuro-062111-150444](https://doi.org/10.1146/annurev-neuro-062111-150444)
agents/docs/BIBLIOGRAPHY.md:128:**[A19]** Tognoli E., Kelso J.A.S. (2014). The metastable brain. *Neuron*, 81(1), 35--48. DOI: [10.1016/j.neuron.2013.12.022](https://doi.org/10.1016/j.neuron.2013.12.022)
agents/docs/BIBLIOGRAPHY.md:132:Criticality validation — gamma probe.
agents/docs/BIBLIOGRAPHY.md:135:γ_WT = +1.043 — external validation for γ_DNCA ~ 1.0.
agents/docs/BIBLIOGRAPHY.md:168:| Kuramoto 1984 | **x** | **x** | | **x** | | |
```

## agents/manuscript/evidence_log.md

_matches: 58_

```
agents/manuscript/evidence_log.md:1:# Evidence Log — γ-scaling Cross-Substrate Measurements
agents/manuscript/evidence_log.md:5:| 2026-03-29 | zebrafish | γ_WT | +1.043 | [0.933, 1.380] | — | PRIMARY |
agents/manuscript/evidence_log.md:6:| 2026-03-29 | DNCA | γ_NMO | +2.072 | [1.341, 2.849] | 949 | CONFIRMED |
agents/manuscript/evidence_log.md:7:| 2026-03-29 | DNCA | γ_PE | +6.975 | [6.503, 7.407] | — | CONFIRMED |
agents/manuscript/evidence_log.md:8:| 2026-03-29 | DNCA | γ_random | +0.068 | [-0.080, 0.210] | — | CONTROL_PASS |
agents/manuscript/evidence_log.md:9:| 2026-03-30 | MFN⁺ | γ_GrayScott (activator) | +0.865 | [0.649, 1.250] | 100 | CONFIRMED |
agents/manuscript/evidence_log.md:10:| 2026-03-30 | MFN⁺ | γ_GrayScott (inhibitor) | +0.655 | [0.431, 0.878] | 100 | CONFIRMED |
agents/manuscript/evidence_log.md:11:| 2026-03-30 | MFN⁺ | γ_control (shuffled) | +0.035 | — | — | CONTROL_PASS |
agents/manuscript/evidence_log.md:12:| 2026-03-30 | mvstack | γ_trending | +1.081 | [0.869, 1.290] | 200 | CONFIRMED |
agents/manuscript/evidence_log.md:13:| 2026-03-30 | mvstack | γ_chaotic | +1.007 | [0.797, 1.225] | 200 | CONFIRMED |
agents/manuscript/evidence_log.md:14:| 2026-03-30 | mvstack | γ_control (shuffled trending) | +0.145 | — | — | CONTROL_PASS |
agents/manuscript/evidence_log.md:15:| 2026-03-30 | mvstack | γ_control (shuffled chaotic) | -0.083 | — | — | CONTROL_PASS |
agents/manuscript/evidence_log.md:16:| 2026-03-30 | mvstack | Δγ(trending - chaotic) | +0.074 | — | — | NOTE |
agents/manuscript/evidence_log.md:19:| 2026-03-30 | DNCA (full) | γ_NMO (state_dim=64, 1000 steps) | +2.185 | [1.743, 2.789] | 898 | CONFIRMED |
agents/manuscript/evidence_log.md:20:| 2026-03-30 | DNCA (full) | γ_PE (state_dim=64, 1000 steps) | +0.476 | [0.210, 0.615] | 899 | CONFIRMED |
agents/manuscript/evidence_log.md:21:| 2026-03-30 | DNCA (full) | γ_random (state_dim=64, 1000 steps) | +0.045 | [-0.082, 0.148] | — | CONTROL_PASS |
agents/manuscript/evidence_log.md:23:| 2026-03-30 | DNCA sweep | γ_min at competition=0.78 | +0.756 | — | 449 | CONVERGES TO BIO |
agents/manuscript/evidence_log.md:24:| 2026-03-30 | DNCA sweep | γ at competition=0.67 | +0.903 | — | 449 | CONSISTENT WITH γ_WT |
agents/manuscript/evidence_log.md:25:| 2026-03-30 | DNCA sweep | γ at competition=0.00 (no comp) | +4.547 | [2.008, 4.316] | 447 | INFLATED |
agents/manuscript/evidence_log.md:27:| 2026-03-30 | SpatialDNCA | γ_NMO (8×8 grid) | +3.870 | [2.295, 4.318] | 447 | ELEVATED |
agents/manuscript/evidence_log.md:28:| 2026-03-30 | SpatialDNCA | γ_PE (8×8 grid) | +0.680 | [0.567, 0.908] | — | BIO RANGE |
agents/manuscript/evidence_log.md:29:| 2026-03-30 | all conditions | γ_PE mean (all conditions) | +0.757 | SD=0.128 | — | STABLE |
agents/manuscript/evidence_log.md:30:| 2026-03-30 | H1 test | Spatial locality effect | REJECTED | — | — | γ INCREASES |
agents/manuscript/evidence_log.md:32:| 2026-03-30 | H3 (emergent) | Metastability hypothesis | SUPPORTED | — | — | γ min at optimal comp |
agents/manuscript/evidence_log.md:34:## T1-T6: Why gamma ≈ 1.0? Seven Tests
agents/manuscript/evidence_log.md:40:| T3: Method falsification | 1D embedding biased (white noise γ=1.6); native 2D valid | 1/5 |
agents/manuscript/evidence_log.md:41:| T2: 2D Ising (T_c=2.269) | γ decreases monotonically with T (1.68→0.96); NOT peaked at T_c | 2/4 |
agents/manuscript/evidence_log.md:42:| T1: Correlation η vs γ | η ≈ 0.2 everywhere, uncorrelated with γ (r=0.11) | 1/3 |
agents/manuscript/evidence_log.md:43:| T4: Persistence dynamics | γ→1.0 when pe0/β0 variance moderate, corr ~0.87 | 1/3 |
agents/manuscript/evidence_log.md:45:| T6: Formula γ=νz/d | Closest match: 1.083 vs measured 1.329 (error 0.25) | partial |
agents/manuscript/evidence_log.md:48:- γ ≈ 1.0 is NOT a critical exponent (T1, T2)
agents/manuscript/evidence_log.md:49:- γ ≈ 1.0 is NOT a pipeline artifact on native 2D fields (controls ≈ 0)
agents/manuscript/evidence_log.md:50:- γ ≈ 1.0 IS the baseline for moderate topological variability (T4)
agents/manuscript/evidence_log.md:51:- γ works on multi-dimensional density fields, NOT low-D ODE trajectories (T5)
agents/manuscript/evidence_log.md:54:## Competition Sweep — γ as function of competition_strength
agents/manuscript/evidence_log.md:62:| competition | γ_NMO | R² | γ_ctrl |
agents/manuscript/evidence_log.md:75:Minimum: γ = 0.756 at competition = 0.778
agents/manuscript/evidence_log.md:76:Maximum: γ = 4.547 at competition = 0.000
agents/manuscript/evidence_log.md:78:All |γ_ctrl| < 0.06 — controls pass at every level
agents/manuscript/evidence_log.md:80:Key finding: At competition ≈ 0.75-0.78, DNCA γ enters the bio-morphogenetic range [0.756, 0.903].
agents/manuscript/evidence_log.md:81:This suggests γ ≈ 1.0 is the signature of METASTABLE competition, not weak or strong competition.
agents/manuscript/evidence_log.md:86:γ_SpatialDNCA(NMO) = +3.870, CI [+2.295, +4.318], R² = 0.204
agents/manuscript/evidence_log.md:87:γ_SpatialDNCA(PE) = +0.680, CI [+0.567, +0.908]
agents/manuscript/evidence_log.md:88:γ_control = -0.000
agents/manuscript/evidence_log.md:89:Verdict: Spatial locality INCREASES γ (not decreases). H1 rejected.
agents/manuscript/evidence_log.md:93:Mean γ_PE = 0.757 (SD = 0.128) across all competition levels and spatial variant.
agents/manuscript/evidence_log.md:99:γ_DNCA_full   = +2.185
agents/manuscript/evidence_log.md:103:γ_control     = +0.045
agents/manuscript/evidence_log.md:109:  γ_bio    = +1.043  [0.933, 1.380]  PRIMARY
agents/manuscript/evidence_log.md:110:  γ_MFN    = +0.865  [0.649, 1.250]  ORGANIZED
agents/manuscript/evidence_log.md:111:  γ_market = +1.081  [0.869, 1.290]  ORGANIZED
agents/manuscript/evidence_log.md:112:  γ_DNCA   = +2.185  [1.743, 2.789]  ORGANIZED (different scale)
agents/manuscript/evidence_log.md:113:  γ_ctrl   = +0.045  [-0.082, 0.148] RANDOM
agents/manuscript/evidence_log.md:119:- DNCA γ_NMO = +2.072 (state_dim=8, 200 steps) and +2.185 (state_dim=64, 1000 steps) — full run confirms elevated γ is not an artifact of reduced parameters.
agents/manuscript/evidence_log.md:121:- Control γ = +0.045 confirms signal is genuine (not pipeline artifact).
agents/manuscript/evidence_log.md:122:- MFN⁺ CI [0.649, 1.250] includes γ_WT = 1.043.
agents/manuscript/evidence_log.md:123:- mvstack γ is stable across market regimes (Δγ = 0.074), suggesting Kuramoto coupling topology itself carries the invariant.
agents/manuscript/evidence_log.md:124:- Three substrates unified: γ_bio = 1.043, γ_MFN = 0.865, γ_market = 1.081 → divergence = 0.216 → UNIFIED.
```

## agents/manuscript/gamma_scaling_manuscript.md

_matches: 56_

```
agents/manuscript/gamma_scaling_manuscript.md:1:# γ-Scaling Across Substrates: Topological Coherence in Organized Systems
agents/manuscript/gamma_scaling_manuscript.md:11:We measure the topological scaling exponent γ — the log-log slope between changes in H0 persistent entropy and H0 Betti number — across five independent substrates: zebrafish pigmentation (biological), Gray-Scott reaction-diffusion (morphogenetic), Kuramoto market synchronization (economic), 2D Ising lattice (physical), and a distributed neuromodulatory cognitive architecture (computational). Three diffusive-oscillatory substrates converge on γ ∈ [0.865, 1.081] with divergence 0.216. The competitive cognitive architecture yields γ ≈ 2.0 at default parameters but converges to the same range (γ = 0.86) when competition is tuned to its metastable operating point. Shuffled controls yield γ ≈ 0 across all substrates (mean 0.041, SD 0.094).
agents/manuscript/gamma_scaling_manuscript.md:13:Seven falsification tests establish that: (i) γ is not a standard critical exponent, (ii) γ is not an artifact of the measurement pipeline on native multi-dimensional fields, (iii) γ ≈ 1.0 occurs in systems with moderate topological variability regardless of substrate, and (iv) the measurement is restricted to multi-dimensional density fields (not low-dimensional ODE trajectories). The theoretical mechanism underlying the specific value γ ≈ 1.0 remains an open question. We report the empirical pattern without overclaiming its interpretation, following the precedent of Kuramoto (1975), whose synchronization model preceded its theoretical explanation by two decades.
agents/manuscript/gamma_scaling_manuscript.md:15:**Keywords:** topological data analysis, persistent homology, substrate-specific candidate marker, γ-scaling, metastability, self-organization
agents/manuscript/gamma_scaling_manuscript.md:21:The question of whether organized systems share measurable invariants across substrates has been posed since Bertalanffy's General System Theory (1968) but resisted quantification. A candidate invariant emerged from the topological analysis of biological pattern formation: McGuirl et al. (2020) measured γ = +1.043 on zebrafish pigmentation patterns using cubical persistent homology, demonstrating that γ distinguishes wild-type from mutant developmental programs.
agents/manuscript/gamma_scaling_manuscript.md:23:This work extends the γ measurement to four additional substrates that share no code, no parameters, and no architectural similarity with zebrafish pigmentation. We ask: does the same topological scaling exponent appear in systems organized by different mechanisms?
agents/manuscript/gamma_scaling_manuscript.md:25:The affirmative answer, qualified by seven falsification tests, suggests that γ-scaling captures a property of how organized systems evolve their topological structure over time — independent of the specific organizing mechanism.
agents/manuscript/gamma_scaling_manuscript.md:31:All γ measurements follow the same pipeline:
agents/manuscript/gamma_scaling_manuscript.md:38:6. Fit log(Δpe₀) vs log(Δβ₀) via Theil-Sen robust regression → slope = γ
agents/manuscript/gamma_scaling_manuscript.md:40:8. Control: independently shuffle pe₀ and β₀ series, recompute γ → should yield ≈ 0
agents/manuscript/gamma_scaling_manuscript.md:49:| mvstack market sync | This work | Kuramoto r(t) coherence | 1D → 2D embedded |
agents/manuscript/gamma_scaling_manuscript.md:54:All experiments: seed=42, deterministic. Code: `github.com/neuron7xLab/neuron7x-agents/scripts/`. Reproduction: `python scripts/gamma_phase_investigation.py`.
agents/manuscript/gamma_scaling_manuscript.md:60:### 3.1 Cross-substrate γ measurements
agents/manuscript/gamma_scaling_manuscript.md:62:| Substrate | System | γ | 95% CI | R² | γ_control |
agents/manuscript/gamma_scaling_manuscript.md:66:| Economic | mvstack Kuramoto (trending) | +1.081 | [+0.869, +1.290] | — | +0.145 |
agents/manuscript/gamma_scaling_manuscript.md:67:| Economic | mvstack Kuramoto (chaotic) | +1.007 | [+0.797, +1.225] | — | −0.083 |
agents/manuscript/gamma_scaling_manuscript.md:73:Three diffusive-oscillatory substrates (zebrafish, MFN⁺, market) converge on γ ∈ [0.865, 1.081], divergence = 0.216. The 2D Ising model at T_c yields γ = 1.329, slightly above this band. DNCA at default parameters yields γ = 2.185 but converges to γ = 0.861 when competition is tuned to its metastable operating point (competition = 0.75).
agents/manuscript/gamma_scaling_manuscript.md:75:All controls satisfy |γ_ctrl| < 0.15. Mean γ_control = +0.041.
agents/manuscript/gamma_scaling_manuscript.md:81:| Competition | γ | R² |
agents/manuscript/gamma_scaling_manuscript.md:94:Minimum: γ = 0.756 at competition = 0.778. All |γ_ctrl| < 0.06.
agents/manuscript/gamma_scaling_manuscript.md:98:The 2D Ising model (L=32) shows monotonically decreasing γ with temperature:
agents/manuscript/gamma_scaling_manuscript.md:100:| T | Phase | γ | Magnetization |
agents/manuscript/gamma_scaling_manuscript.md:109:γ is not peaked at T_c. It tracks the degree of spatial order.
agents/manuscript/gamma_scaling_manuscript.md:113:In DNCA, γ measured on the prediction error field (sensory − predicted) is remarkably stable across all competition levels: mean γ_PE = 0.757, SD = 0.128. This channel converges to the bio-morphogenetic range regardless of internal architecture.
agents/manuscript/gamma_scaling_manuscript.md:117:Destroying temporal structure (shuffling) reduces γ by 0.8–2.0 in every substrate tested, confirming γ measures temporal organization, not static signal properties.
agents/manuscript/gamma_scaling_manuscript.md:123:### 4.1 Is γ = 1.0 a pipeline artifact? (T3)
agents/manuscript/gamma_scaling_manuscript.md:125:Seven synthetic signal classes were tested via 1D→2D time-delay embedding. White noise yielded γ = 1.6, indicating the embedding approach is systematically biased. However, native multi-dimensional measurements (DNCA 6D activities, Ising 32×32 grids, MFN⁺ 128×128 fields) produce γ_ctrl ≈ 0, confirming the pipeline is valid on native fields.
agents/manuscript/gamma_scaling_manuscript.md:127:**Conclusion:** γ measurement is valid on native multi-dimensional density fields. The 1D→2D embedding approach requires methodological revision.
agents/manuscript/gamma_scaling_manuscript.md:129:### 4.2 Is γ a critical exponent? (T1, T2, T6)
agents/manuscript/gamma_scaling_manuscript.md:131:The temporal autocorrelation exponent η ≈ 0.2 across all DNCA competition levels, uncorrelated with γ (Pearson r = 0.11). The Ising model shows γ monotonically decreasing with T, not peaked at T_c. No formula from standard critical exponents (ν, z, d, η) reproduces the measured γ values (best candidate νz/d = 1.08 vs measured 1.33 for 2D Ising).
agents/manuscript/gamma_scaling_manuscript.md:133:**Conclusion:** γ is not a standard critical exponent in the renormalization group sense.
agents/manuscript/gamma_scaling_manuscript.md:135:### 4.3 Does γ work on arbitrary dynamical systems? (T5)
agents/manuscript/gamma_scaling_manuscript.md:137:Hodgkin-Huxley (γ ≈ 6.5), Van der Pol (γ ≈ 8.5), and Lorenz (γ ≈ 2.9) systems show no differentiation between critical and non-critical operating points. Low-dimensional ODE trajectories (2–4D) are outside the domain of the γ pipeline.
agents/manuscript/gamma_scaling_manuscript.md:139:**Conclusion:** γ is restricted to multi-dimensional density fields with sufficient topological complexity.
agents/manuscript/gamma_scaling_manuscript.md:141:### 4.4 What determines γ ≈ 1.0? (T4)
agents/manuscript/gamma_scaling_manuscript.md:143:Analysis of persistent homology dynamics reveals: γ approaches 1.0 when pe₀ and β₀ have moderate variance with moderate mutual correlation (~0.87). Extreme variance (competition=0.0: pe₀_std = 0.80, β₀_std = 18.1, corr = 0.997) produces γ >> 1. Low variance (competition=1.0: β₀_std = 5.6, corr = 0.74) produces γ ≈ 2.
agents/manuscript/gamma_scaling_manuscript.md:145:**Conclusion:** γ = 1.0 is the scaling regime where topological entropy and Betti number changes are proportional — each topological feature contributes a proportional amount of entropy.
agents/manuscript/gamma_scaling_manuscript.md:151:### 5.1 What γ is
agents/manuscript/gamma_scaling_manuscript.md:153:γ is a topological scaling exponent that quantifies how persistent entropy changes relative to persistent Betti number changes in time-evolving multi-dimensional density fields. It satisfies three conditions for a useful diagnostic:
agents/manuscript/gamma_scaling_manuscript.md:155:1. **Discrimination:** γ > 0 for all organized systems; γ ≈ 0 for shuffled controls
agents/manuscript/gamma_scaling_manuscript.md:156:2. **Convergence:** γ ∈ [0.86, 1.33] across five independent substrates operating in moderate-variability regimes
agents/manuscript/gamma_scaling_manuscript.md:157:3. **Sensitivity:** γ responds to parameter changes (competition sweep, temperature sweep) in a systematic, reproducible way
agents/manuscript/gamma_scaling_manuscript.md:159:### 5.2 What γ is not
agents/manuscript/gamma_scaling_manuscript.md:161:γ is not a universal constant. It is not a critical exponent. It is not applicable to low-dimensional trajectories. It does not distinguish criticality from near-criticality in the Ising model. Its specific value (~1.0) has no known analytical derivation from first principles.
agents/manuscript/gamma_scaling_manuscript.md:163:### 5.3 The Kuramoto precedent
agents/manuscript/gamma_scaling_manuscript.md:165:Kuramoto (1975) introduced his coupled oscillator model to describe the Belousov-Zhabotinsky chemical reaction. That the same equation would describe firefly synchronization, cardiac rhythms, and neural oscillations was not predicted — it was discovered empirically over the following two decades (Strogatz 2000).
agents/manuscript/gamma_scaling_manuscript.md:167:γ-scaling may follow a similar trajectory. The empirical pattern — convergence across substrates, clean controls, reproducible sensitivity to parameters — is established. The theoretical explanation for why five substrates converge on γ ≈ 1.0 remains open. We report the observation without overclaiming its interpretation.
agents/manuscript/gamma_scaling_manuscript.md:175:5. DNCA measurements use fast mode (forward model learning disabled); full learning may produce different γ dynamics.
agents/manuscript/gamma_scaling_manuscript.md:180:2. The prediction error field shows γ_PE ≈ 0.76 across all DNCA conditions. Why is the system-environment interface invariant to internal architecture?
agents/manuscript/gamma_scaling_manuscript.md:181:3. Can γ differentiate pathological from healthy organization in real neural data (e.g., epilepsy, Parkinson's)?
agents/manuscript/gamma_scaling_manuscript.md:182:4. What is the relationship between γ and other complexity measures (integrated information Φ, transfer entropy, Lempel-Ziv complexity)?
agents/manuscript/gamma_scaling_manuscript.md:188:We report an empirical observation: the topological scaling exponent γ, measured via cubical persistent homology on time-evolving density fields, converges on γ ∈ [0.86, 1.33] across five independent substrates — biological tissue, reaction-diffusion fields, market synchronization, spin lattices, and cognitive competitive dynamics. Shuffled controls yield γ ≈ 0 in every case. The convergence is not a measurement artifact, not a critical exponent, and not universal to all dynamical systems. It is a reproducible, falsifiable, substrate-spanning pattern whose theoretical explanation is an open problem.
agents/manuscript/gamma_scaling_manuscript.md:192:> *Five independent substrates — zebrafish morphogenesis, Gray-Scott reaction-diffusion, Kuramoto market synchronization, 2D Ising lattice, and neuromodulatory cognitive competition — converge on γ ∈ [0.86, 1.33] when operating in moderate-variability regimes. All organized systems show γ > 0; all shuffled controls show γ ≈ 0. The mechanism underlying the convergence on γ ≈ 1.0 is unknown. We report the pattern.*
agents/manuscript/gamma_scaling_manuscript.md:208:Kuramoto Y. (1975) Self-entrainment of a population of coupled non-linear oscillators. *Lecture Notes in Physics* 39:420–422.
agents/manuscript/gamma_scaling_manuscript.md:220:Strogatz S.H. (2000) From Kuramoto to Crawford: exploring the onset of synchronization in populations of coupled oscillators. *Physica D* 143:1–20.
agents/manuscript/gamma_scaling_manuscript.md:222:Tognoli E., Kelso J.A.S. (2014) The metastable brain. *Neuron* 81(1):35–48.
```

## agents/manuscript/results_gamma.md

_matches: 50_

```
agents/manuscript/results_gamma.md:1:# 3. Results: γ-scaling as a Substrate-Specific Candidate Marker of Organized Systems
agents/manuscript/results_gamma.md:3:## 3.1 γ-scaling in zebrafish pigmentation (McGuirl et al. 2020)
agents/manuscript/results_gamma.md:5:The γ-scaling exponent was first measured on density fields of zebrafish skin pigmentation patterns by McGuirl et al. (2020, PNAS 117(21):11350–11361). Using cubical persistent homology on time-lapse images of wild-type zebrafish pigmentation, with H0 persistent entropy (pe₀) and H0 Betti number (β₀) extracted at each developmental timepoint, the authors computed the scaling relationship between topological change rates: log(Δpe₀) versus log(Δβ₀). The wild-type zebrafish exhibited γ_WT = +1.043 with R² = 0.492 (p = 0.001, 95% CI = [0.933, 1.380]). The corresponding H1 maximum homology lifetime (H1_MHL_WT) was 0.464, indicating topologically organized pattern formation. Mutant fish with disrupted cell–cell communication showed significantly different γ values and reduced H1_MHL, confirming that γ captures the organizing principle of the biological system rather than mere geometric regularity. This established γ as a candidate invariant of biological self-organization measurable through persistent homology.
agents/manuscript/results_gamma.md:7:## 3.2 γ-scaling in DNCA internal trajectories
agents/manuscript/results_gamma.md:9:We measured γ on the internal state trajectories of the Distributed Neuromodulatory Cognitive Architecture (DNCA), a computational system with no geometric substrate, no pigmentation, and no biological cells. DNCA implements six neuromodulatory operators (dopamine, acetylcholine, norepinephrine, serotonin, GABA, glutamate) competing through Lotka-Volterra winnerless dynamics over a shared predictive state. Each operator runs a Dominant-Acceptor cycle (Ukhtomsky 1923; Anokhin 1968) as its base computational unit.
agents/manuscript/results_gamma.md:11:From the NMO activity field — the six-dimensional vector of operator activities recorded over 1000 timesteps — we constructed sliding-window density snapshots (window = 50 steps) and applied the identical TDA pipeline: cubical persistent homology, H0 persistent entropy, H0 Betti number, log-delta Theil-Sen regression. The result: γ_DNCA = +1.285 with 95% bootstrap CI = [+0.987, +1.812], R² = 0.138, n = 949 valid measurement pairs. The confidence interval includes γ_WT = +1.043.
agents/manuscript/results_gamma.md:13:A randomized control was performed by independently permuting the pe₀ and β₀ series to destroy their temporal coupling. The random baseline yielded γ_random = −0.009 (CI = [−0.069, +0.145], R² = 0.001), confirming that the observed γ_DNCA is not an artifact of the measurement pipeline or windowing procedure.
agents/manuscript/results_gamma.md:15:### γ grows with learning
agents/manuscript/results_gamma.md:17:When γ was computed in sliding windows of 200 steps across a 2000-step trajectory, the mean γ over the first five windows was +1.260 and over the last five windows was +1.481, demonstrating a monotonic increase with training. This suggests that γ is not a static parameter but a developmental metric: as the system learns to predict its environment more accurately (mismatch decreasing from 0.61 to 0.37), its topological coherence increases. If confirmed across architectures, this would establish γ as the first topological measure of cognitive development.
agents/manuscript/results_gamma.md:19:### Inverted-U γ versus noise level
agents/manuscript/results_gamma.md:21:Five separate 1000-step trajectories were collected at noise levels σ ∈ {0.0, 0.05, 0.1, 0.2, 0.5}. The γ values were: +1.389, +1.276, +1.445, +1.475, +1.198, respectively. The peak occurred at σ = 0.2, with lower values at both extremes. This inverted-U pattern directly validates the metastability hypothesis: the system achieves maximum topological coherence at intermediate noise levels where the Kuramoto order parameter fluctuates most (r_std = 0.147), not at zero noise (rigid regime, r_std → 0) or high noise (collapsed regime, r_std → 0). This provides an independent topological confirmation of the metastability operating point, complementing the standard oscillatory measure r(t).
agents/manuscript/results_gamma.md:25:The same TDA pipeline applied to the prediction error field (state_dim-dimensional vectors over time) yielded γ_PE = +0.482 (CI = [+0.315, +0.789], R² = 0.075). While lower than the NMO activity measurement and with weaker R², this value is significantly positive, indicating that the prediction error dynamics also exhibit organized scaling — though at a different scale than the competitive dynamics of operator activities.
agents/manuscript/results_gamma.md:27:## 3.3 γ-scaling in MFN⁺ morphogenetic fields
agents/manuscript/results_gamma.md:29:To extend the measurement beyond neural/cognitive substrates, we computed γ on the 2D reaction-diffusion fields of Mycelium Fractal Network Plus (MFN⁺), a morphogenetic simulation implementing Gray-Scott dynamics on a 128×128 spatial grid. The activator and inhibitor concentration fields at each timestep were treated as 2D density images — identical to the zebrafish pigmentation density fields of McGuirl et al. — and processed through the same cubical persistent homology pipeline: H0 persistent entropy, H0 Betti number, log-delta Theil-Sen regression with 200-iteration bootstrap CI.
agents/manuscript/results_gamma.md:31:The activator field yielded γ_MFN(activator) = +0.865 with 95% CI = [+0.649, +1.250]. The confidence interval includes γ_WT = +1.043, establishing direct overlap with the biological measurement. The inhibitor field yielded γ_MFN(inhibitor) = +0.655 (CI = [+0.431, +0.878]), lower but still positive, reflecting the inhibitor's role as a smoother, less topologically complex field.
agents/manuscript/results_gamma.md:33:A shuffled control — temporal permutation of the field sequence destroying developmental trajectory while preserving per-frame statistics — yielded γ_control = +0.035, confirming that the observed γ reflects temporal organization of the morphogenetic process, not static spatial properties of individual frames.
agents/manuscript/results_gamma.md:35:This result is significant because MFN⁺ Gray-Scott dynamics share no parameters, no code, and no architectural similarity with either zebrafish pigmentation or DNCA cognitive competition. Yet the γ values overlap. The organizing principle measured by γ is not specific to any substrate — it is a property of how organized systems evolve their topological structure over time.
agents/manuscript/results_gamma.md:37:## 3.4 γ-scaling in market synchronization regimes
agents/manuscript/results_gamma.md:39:We measured γ on the Kuramoto coherence trajectories of mvstack, an economic synchronization model where coupled oscillators represent market agents. The coherence order parameter r(t) — the magnitude of the mean phase vector — was recorded over 500 timesteps and embedded into 2D sliding-window images for the same TDA pipeline.
agents/manuscript/results_gamma.md:42:- **Trending market** (trend = 0.01): γ_trending = +1.081 (CI = [+0.869, +1.290])
agents/manuscript/results_gamma.md:43:- **Chaotic market** (trend = 0.0): γ_chaotic = +1.007 (CI = [+0.797, +1.225])
agents/manuscript/results_gamma.md:45:Both conditions produce γ > 0 with CIs overlapping γ_WT = +1.043. The difference between conditions is small: Δγ = +0.074, indicating that γ in market synchronization reflects the topological structure of the Kuramoto coupling mechanism itself, not the market's directional regime. This is consistent with the thesis: the organizing principle is in the synchronization dynamics, and γ measures its invariant topology regardless of whether the market is trending or chaotic.
agents/manuscript/results_gamma.md:47:Shuffled controls yielded γ_control(trending) = +0.145 and γ_control(chaotic) = −0.083, both near zero, confirming that the measurement captures genuine temporal organization.
agents/manuscript/results_gamma.md:51:Previous measurements in Section 3.2 used state_dim=8 as a computational proxy, yielding γ_DNCA = +2.072 (CI [1.341, 2.849]). To determine whether this elevated γ was an artifact of reduced dimensionality, we performed a full validation with state_dim=64 (the architecture's native dimensionality) and 1000 integration steps, using window_size=100 and 500 bootstrap iterations for CI estimation.
agents/manuscript/results_gamma.md:53:Full validation yields: γ_DNCA_full = +2.185, 95% CI [1.743, 2.789], R² = 0.2235, n = 898 valid measurement pairs. The prediction error field measurement yields γ_PE = +0.476 (CI [0.210, 0.615], R² = 0.050). Control (trajectory-shuffled): γ_control = +0.045 (CI [-0.082, 0.148], R² = 0.002), confirming the signal is genuine and not a pipeline artifact.
agents/manuscript/results_gamma.md:55:The full-parameter DNCA measurement (γ = +2.185) is consistent with the reduced-parameter proxy (γ = +2.072), confirming that the elevated γ is not an artifact of dimensionality reduction. However, the confidence interval [1.743, 2.789] does not overlap with the biological-morphogenetic range [0.865, 1.081] (overlap = 0.000).
agents/manuscript/results_gamma.md:57:**Interpretation.** DNCA's neuromodulatory competitive dynamics (six operators in Lotka-Volterra winnerless competition) produce topological scaling at approximately twice the rate of reaction-diffusion or synchronization substrates. This likely reflects the architectural difference between competitive winner-take-all dynamics (where topological transitions are sharp and frequent) and diffusive/oscillatory dynamics (where topological change is gradual). Three substrates — biological (zebrafish), morphogenetic (MFN⁺), and economic (mvstack) — remain unified with divergence = 0.216. DNCA is reported as a related but architecturally distinct organizational scale: γ > 0, control ≈ 0, but γ_DNCA ≈ 2× the bio-morphogenetic invariant.
agents/manuscript/results_gamma.md:59:## 3.6 Δγ as structural diagnostic (perturbation analysis)
agents/manuscript/results_gamma.md:61:Across all substrates, perturbation or destruction of organizational structure drives γ toward zero:
agents/manuscript/results_gamma.md:63:| Perturbation | Substrate | γ_organized | γ_perturbed | Δγ |
agents/manuscript/results_gamma.md:71:In every case, destroying temporal coherence while preserving marginal statistics reduces γ by 0.8–2.0, confirming that γ measures the time-extended organizational process, not static signal properties. The DNCA shows the largest Δγ (−2.004), consistent with its higher absolute γ from the reduced-parameter measurement.
agents/manuscript/results_gamma.md:73:Additionally, DNCA γ exhibits an inverted-U relationship with noise: γ peaks at intermediate noise levels (σ = 0.2, γ = +1.475) and decreases at both zero noise (rigid regime, γ = +1.389) and high noise (collapsed regime, γ = +1.198). This links γ directly to the metastable operating point where Kuramoto order parameter fluctuations are maximal (r_std = 0.147), providing independent topological confirmation of the metastability hypothesis.
agents/manuscript/results_gamma.md:75:## 3.7 Control: γ_random ≈ 0 across all substrates
agents/manuscript/results_gamma.md:77:Every γ measurement was accompanied by a shuffled baseline. Summary of control values:
agents/manuscript/results_gamma.md:79:| Substrate | γ_control | Method |
agents/manuscript/results_gamma.md:86:Mean γ_control = +0.041 (SD = 0.094). No control exceeds |0.15|. The measurement pipeline does not produce spurious positive γ from unstructured data.
agents/manuscript/results_gamma.md:90:The central finding of this work is that γ-scaling — the log-log slope between changes in H0 persistent entropy and H0 Betti number — reproduces across four substrates that share no common implementation:
agents/manuscript/results_gamma.md:92:| Substrate | System | γ | 95% CI | Verdict |
agents/manuscript/results_gamma.md:97:| Economic | mvstack Kuramoto market synchronization | +1.081 | [+0.869, +1.290] | ORGANIZED |
agents/manuscript/results_gamma.md:100:The full DNCA validation (Section 3.5) confirmed γ_DNCA = +2.185 (CI [1.743, 2.789]) at native parameters (state_dim=64, 1000 steps), ruling out reduced-parameter artifacts. The DNCA CI does not overlap the bio-morphogenetic range [0.865, 1.081]. The remaining three substrates — biological, morphogenetic, and economic — yield γ values within a narrow band: 0.865–1.081, with divergence = 0.216. The NFI Unified γ Diagnostic classifies this triad as **UNIFIED** (divergence < 0.3, all γ ∈ [0.649, 1.290]). DNCA is classified as a related but architecturally distinct organizational regime.
agents/manuscript/results_gamma.md:104:1. **Cross-substrate consistency.** γ > 0 in all organized systems, γ ≈ 0 in all shuffled controls. This is the minimal condition for an invariant.
agents/manuscript/results_gamma.md:106:2. **CI overlap with biological ground truth.** MFN⁺ CI [0.649, 1.250] and mvstack CI [0.869, 1.290] both include γ_WT = 1.043. The measurement does not merely detect organization — it detects the *same degree* of organization as the biological reference.
agents/manuscript/results_gamma.md:108:3. **γ grows with learning.** In DNCA, γ increases monotonically as prediction error decreases over training, suggesting it tracks the development of an internal model — consistent with Levin's (2019) definition of self-organizing systems as those containing a model of their own future state.
agents/manuscript/results_gamma.md:110:4. **γ peaks at metastability.** The inverted-U relationship between γ and noise in DNCA links topological coherence to the edge-of-chaos operating regime, providing an independent confirmation via persistent homology of what Kuramoto r(t) measures via oscillatory dynamics.
agents/manuscript/results_gamma.md:112:5. **Regime-independence in markets.** mvstack γ is stable across trending and chaotic market conditions (Δγ = 0.074), indicating that the invariant captures the coupling topology, not the behavioral state — consistent with γ being a structural rather than dynamical quantity.
agents/manuscript/results_gamma.md:116:The DNCA γ = +2.185 (full validation: state_dim=64, 1000 steps, CI [1.743, 2.789]) does not overlap with the biological-morphogenetic range [0.865, 1.081]. The reduced-parameter proxy (state_dim=8, γ = +2.072) and full validation are consistent, confirming this is a genuine architectural difference rather than a computational artifact. Neuromodulatory competitive dynamics (Lotka-Volterra winnerless competition among six operators) produce sharper topological transitions than reaction-diffusion or synchronization substrates, yielding γ ≈ 2× the bio-morphogenetic invariant. Three substrates remain unified (divergence = 0.216); DNCA represents a related but distinct organizational scale.
agents/manuscript/results_gamma.md:122:### Toward a universal statement
agents/manuscript/results_gamma.md:124:Despite these caveats, the pattern is clear: **organized systems exhibit γ > 0, random systems exhibit γ ≈ 0, and the specific value γ ≈ 1.0 appears in biological, morphogenetic, and economic substrates with overlapping confidence intervals.** If confirmed with empirical data across additional substrates, this would establish γ as the first quantitative, substrate-specific candidate marker of organized systems — measurable through persistent homology alone, requiring no knowledge of the system's internal mechanism. (Substrate-independence is empirically contradicted by the 2026-04-14 HRV n=5 pilot: γ mean 0.50 ± 0.44. See `docs/CLAIM_BOUNDARY.md` §2.)
agents/manuscript/results_gamma.md:128:> *Three independent substrates converge on γ ∈ [0.865, 1.081] (divergence = 0.216, verdict: UNIFIED): zebrafish morphogenesis (γ = +1.043), MFN⁺ reaction-diffusion (γ = +0.865), and market synchronization (γ = +1.081). Neuromodulatory cognitive dynamics exhibit a related but architecturally distinct scaling regime (γ = +2.185), consistent with the stronger topological transitions of competitive winner-take-all dynamics. All organized substrates show γ > 0; all shuffled controls show γ ≈ 0. γ-scaling is a substrate-specific candidate signature of organization, with the specific value γ ≈ 1.0 characterizing diffusive-oscillatory self-organization.*
agents/manuscript/results_gamma.md:148:Vasylenko Y. (2026) Distributed Neuromodulatory Cognitive Architecture: γ-scaling as substrate-specific candidate marker. neuron7xLab Technical Report.
```

## agents/manuscript/section4_mechanistic_interpretation.md

_matches: 43_

```
agents/manuscript/section4_mechanistic_interpretation.md:1:## 4. Mechanistic Interpretation of γ-Regimes
agents/manuscript/section4_mechanistic_interpretation.md:5:The divergence between γ ≈ 1.0 (zebrafish, MFN⁺, market) and γ ≈ 2.185 (DNCA full validation) raised a mechanistic question: what determines the γ-regime of an organized system? Two hypotheses were tested:
agents/manuscript/section4_mechanistic_interpretation.md:7:**H1 (Spatial Geometry):** γ is determined by whether organization operates through spatial propagation (diffusion → γ ≈ 1.0) or global competition (no space → γ ≈ 2.0).
agents/manuscript/section4_mechanistic_interpretation.md:9:**H2 (Competition Strength):** γ is determined by the strength of winner-take-all dynamics. Weak competition → γ ≈ 1.0. Strong competition → γ ≈ 2.0.
agents/manuscript/section4_mechanistic_interpretation.md:11:Both hypotheses predict that reducing competition or introducing spatial locality in DNCA should shift γ toward 1.0.
agents/manuscript/section4_mechanistic_interpretation.md:21:γ was measured via BNSynGammaProbe (NMO activity field, window=50, 500 steps, 300 bootstrap iterations, seed=42) at five competition levels:
agents/manuscript/section4_mechanistic_interpretation.md:23:| Competition | γ_NMO | 95% CI | R² | γ_control | Verdict |
agents/manuscript/section4_mechanistic_interpretation.md:28:| 0.75 | +0.861 | [+0.590, +1.258] | 0.114 | +0.068 | CONSISTENT WITH γ_WT |
agents/manuscript/section4_mechanistic_interpretation.md:31:All controls satisfy |γ_ctrl| < 0.1 at every level, confirming the signal is genuine.
agents/manuscript/section4_mechanistic_interpretation.md:33:**Result: H2 is rejected.** The relationship between competition strength and γ is non-monotonic. γ does not decrease with weaker competition — it increases dramatically (γ = 4.55 at competition=0.0).
agents/manuscript/section4_mechanistic_interpretation.md:35:### 4.3 The U-shaped γ response
agents/manuscript/section4_mechanistic_interpretation.md:40:γ_NMO vs competition_strength:
agents/manuscript/section4_mechanistic_interpretation.md:48:  1.0 |              *-------- γ_WT = 1.043
agents/manuscript/section4_mechanistic_interpretation.md:55:The minimum occurs at competition ≈ 0.75, where γ_DNCA = +0.861 — which falls within the CI of γ_WT = +1.043 and overlaps with the bio-morphogenetic range [0.865, 1.081].
agents/manuscript/section4_mechanistic_interpretation.md:57:**This is the central finding:** the DNCA system converges to the biological γ-invariant at a specific operating point of its competition dynamics, not at the extremes.
agents/manuscript/section4_mechanistic_interpretation.md:59:**Interpretation.** At competition=0.0 (minimal competition), all NMO operators have nearly equal growth rates and weak mutual inhibition. This produces undifferentiated dynamics where topological transitions are frequent but unconstrained — each small perturbation creates a new topological feature. The result is inflated γ (more entropy change per Betti change).
agents/manuscript/section4_mechanistic_interpretation.md:61:At competition=1.0 (full WTA), the dynamics are dominated by sharp, discrete regime transitions. Each transition involves a sudden reorganization of the NMO activity landscape, producing large, correlated changes in both pe₀ and β₀. The ratio of these changes yields γ ≈ 2.0.
agents/manuscript/section4_mechanistic_interpretation.md:63:At competition≈0.75, the system operates in a regime where competition is strong enough to create well-defined regimes but not so strong that transitions are all-or-nothing. This "metastable competition" produces gradual, wave-like transitions — topologically similar to reaction-diffusion dynamics — yielding γ ≈ 1.0.
agents/manuscript/section4_mechanistic_interpretation.md:76:- γ_SpatialDNCA(NMO) = +3.870, CI [+2.295, +4.318]
agents/manuscript/section4_mechanistic_interpretation.md:77:- γ_SpatialDNCA(PE) = +0.680, CI [+0.567, +0.908]
agents/manuscript/section4_mechanistic_interpretation.md:78:- γ_control = −0.000
agents/manuscript/section4_mechanistic_interpretation.md:80:**H1 is rejected.** Introducing spatial locality increases γ rather than reducing it. The spatial diffusion creates spatially correlated NMO activities that produce large-scale topological transitions — each wave-like reorganization affects many spatial locations simultaneously, amplifying the topological entropy change.
agents/manuscript/section4_mechanistic_interpretation.md:82:However, the prediction error field γ_PE = +0.680 remains in the bio-morphogenetic range, suggesting that the PE measurement channel is more robust to architectural variations than the NMO activity channel.
agents/manuscript/section4_mechanistic_interpretation.md:84:### 4.5 Prediction error field: a robust γ channel
agents/manuscript/section4_mechanistic_interpretation.md:86:Across all experimental conditions, the prediction error field γ_PE shows remarkable stability:
agents/manuscript/section4_mechanistic_interpretation.md:88:| Condition | γ_PE | 95% CI |
agents/manuscript/section4_mechanistic_interpretation.md:97:Mean γ_PE = 0.757 (SD = 0.128). The PE field γ always falls within or near the bio-morphogenetic range [0.865, 1.081], regardless of competition strength or spatial structure. This suggests:
agents/manuscript/section4_mechanistic_interpretation.md:105:The original binary classification (Regime I: diffusive γ ≈ 1.0, Regime II: competitive γ ≈ 2.0) requires revision based on the experimental evidence:
agents/manuscript/section4_mechanistic_interpretation.md:107:**γ is not determined by the presence or absence of competition, nor by spatial geometry.** Instead, γ reflects the *dynamical regime* of the system's internal organization:
agents/manuscript/section4_mechanistic_interpretation.md:109:1. **Undifferentiated regime** (γ >> 1): competition too weak → unconstrained topological fluctuations → inflated γ
agents/manuscript/section4_mechanistic_interpretation.md:110:2. **Metastable regime** (γ ≈ 1.0): competition balanced → gradual regime transitions → γ converges to bio-morphogenetic invariant
agents/manuscript/section4_mechanistic_interpretation.md:111:3. **Winner-take-all regime** (γ ≈ 2.0): competition too strong → sharp discrete transitions → elevated γ
agents/manuscript/section4_mechanistic_interpretation.md:113:The bio-morphogenetic invariant γ ≈ 1.0 corresponds to Regime 2: metastable dynamics at the optimal balance of competition. This is consistent with the inverted-U relationship between γ and noise (Section 3.2) — both noise and competition have optimal operating points where topological coherence matches the biological reference.
agents/manuscript/section4_mechanistic_interpretation.md:115:**Falsifiable prediction:** Any system whose internal competition can be tuned should exhibit a U-shaped γ response, with a minimum near γ ≈ 1.0 at the metastability operating point. This prediction can be tested on:
agents/manuscript/section4_mechanistic_interpretation.md:118:- Economic models (by varying the coupling strength K in Kuramoto)
agents/manuscript/section4_mechanistic_interpretation.md:120:### 4.7 γ as a metastability diagnostic
agents/manuscript/section4_mechanistic_interpretation.md:122:The convergence of three independent observations strengthens the metastability interpretation:
agents/manuscript/section4_mechanistic_interpretation.md:124:1. **γ peaks at intermediate noise** (Section 3.2, inverted-U): maximum topological coherence at σ = 0.2 where r_std is maximal
agents/manuscript/section4_mechanistic_interpretation.md:125:2. **γ minimizes to bio-invariant at optimal competition** (this section): minimum at competition ≈ 0.75 where dynamics are metastable
agents/manuscript/section4_mechanistic_interpretation.md:126:3. **γ_PE is stable across all conditions** (this section): the prediction error channel filters out internal dynamics, preserving only the environment-system interface
agents/manuscript/section4_mechanistic_interpretation.md:128:Together, these suggest that γ ≈ 1.0 is not merely a coincidence across substrates — it is the **topological signature of metastability itself**. Systems at the edge of order and disorder, whether biological tissues, computational architectures, or economic networks, produce the same rate of topological change per unit structural reorganization.
agents/manuscript/section4_mechanistic_interpretation.md:130:If confirmed, this would establish γ not as a passive measurement of organization, but as a **diagnostic of dynamical regime**: given any time series from an unknown system, measuring γ tells you whether the system operates in the metastable band (γ ≈ 1.0), the rigid regime (γ > 1.5), or the chaotic regime (γ < 0.5).
agents/manuscript/section4_mechanistic_interpretation.md:136:Controls: independently shuffled pe₀ and β₀ series at every measurement point. All |γ_ctrl| < 0.1.
```

## agents/manuscript/section5_why_gamma_one.md

_matches: 46_

```
agents/manuscript/section5_why_gamma_one.md:1:## 5. Why γ ≈ 1.0? Seven Tests and an Honest Answer
agents/manuscript/section5_why_gamma_one.md:5:Section 4 established that γ minimizes to the bio-morphogenetic range [0.76, 0.90] at optimal competition in DNCA (competition ≈ 0.75). Three biological/synthetic substrates converge on γ ∈ [0.865, 1.081]. But *why* 1.0? Three possibilities were tested:
agents/manuscript/section5_why_gamma_one.md:7:- (A) γ = 1.0 is a mathematical consequence of criticality
agents/manuscript/section5_why_gamma_one.md:8:- (B) γ = 1.0 is an artifact of the TDA measurement pipeline
agents/manuscript/section5_why_gamma_one.md:9:- (C) γ = 1.0 is a fundamental constant of organized systems
agents/manuscript/section5_why_gamma_one.md:13:### 5.2 T3: Method falsification — is γ = 1.0 a pipeline artifact?
agents/manuscript/section5_why_gamma_one.md:17:| Signal | γ | R² | γ_ctrl | Bio range? |
agents/manuscript/section5_why_gamma_one.md:27:**Verdict: PARTIALLY ARTIFACT.** The 1D→2D embedding approach produces γ ≈ 1.0–1.6 for many signal types, including white noise (γ = 1.6). This is because time-delay embedding of correlated windows introduces systematic structure that inflates γ away from zero.
agents/manuscript/section5_why_gamma_one.md:29:**Critical distinction:** The DNCA, MFN⁺, and Ising measurements use *native multi-dimensional fields* (6-NMO activities, 2D grids), not 1D→2D embedding. In those native measurements, shuffled controls consistently yield γ ≈ 0, confirming the signal is genuine. The 1D embedding approach is methodologically different and should not be used to validate or invalidate native 2D measurements.
agents/manuscript/section5_why_gamma_one.md:31:**Methodological recommendation:** γ measurement via the TDA pipeline is valid on native multi-dimensional density fields. Extension to 1D signals requires alternative embedding methods.
agents/manuscript/section5_why_gamma_one.md:37:| T | Phase | γ | R² | Magnetization | γ_ctrl |
agents/manuscript/section5_why_gamma_one.md:46:**Key finding: γ decreases monotonically with temperature.** It is NOT peaked at T_c. The Ising model shows γ_Tc = 1.329 — within the range we observe for organized systems, but not special relative to neighboring temperatures.
agents/manuscript/section5_why_gamma_one.md:48:**Interpretation:** In the Ising model, γ tracks the *degree of spatial order*, not criticality per se. Ordered phases (low T) have persistent topological features that change coherently → high γ. Disordered phases (high T) have rapidly decorrelating features → γ approaches ~1.0 from above.
agents/manuscript/section5_why_gamma_one.md:50:The value γ ≈ 1.0 for the disordered phase is significant: it suggests that γ = 1.0 is the **natural baseline for systems with moderate topological variability** — when topological features change at uncorrelated, moderate rates, the log-log scaling between Δpe₀ and Δβ₀ naturally approaches unity.
agents/manuscript/section5_why_gamma_one.md:56:| Competition | η (power-law exponent) | η R² | γ | η/γ |
agents/manuscript/section5_why_gamma_one.md:64:**Verdict: γ ≠ η.** The power-law correlation exponent η ≈ 0.2 is nearly constant across all competition levels (Pearson r(η,γ) = 0.11). γ is not a standard critical exponent. It captures a different aspect of the system's topology than temporal correlations.
agents/manuscript/section5_why_gamma_one.md:70:| Competition | pe₀ std | β₀ std | corr(pe₀, β₀) | γ |
agents/manuscript/section5_why_gamma_one.md:78:**Mechanism identified:** γ is determined by the *ratio of variability* between persistent entropy (pe₀) and Betti number (β₀):
agents/manuscript/section5_why_gamma_one.md:80:- At competition=0.0: both pe₀ and β₀ have HIGH variance, near-perfect correlation → the log-log slope is dominated by extreme events where pe₀ changes superlinearly with β₀ → γ >> 1
agents/manuscript/section5_why_gamma_one.md:81:- At competition=0.75: MODERATE variance in both, still good correlation (0.87) → scaling is approximately linear → γ ≈ 1.0
agents/manuscript/section5_why_gamma_one.md:82:- At competition=1.0: LOW β₀ variance (5.6), lower correlation (0.74) → sharp discrete transitions create outlier points in the log-log space → γ ≈ 2.0
agents/manuscript/section5_why_gamma_one.md:84:**γ = 1.0 occurs when the topological features vary at moderate rates with moderate mutual coupling.** This is the regime where changes in persistent entropy scale linearly with changes in Betti number — each connected component that appears or disappears contributes a proportional amount of entropy.
agents/manuscript/section5_why_gamma_one.md:88:Hodgkin-Huxley, Van der Pol, and Lorenz systems were tested at critical/metastable and non-critical operating points:
agents/manuscript/section5_why_gamma_one.md:90:| System | γ | R² | γ_ctrl |
agents/manuscript/section5_why_gamma_one.md:101:**Verdict: NEGATIVE.** Low-dimensional ODE trajectories (2–4D) do not show γ ≈ 1.0 at critical points, nor do they differentiate critical from non-critical operating regimes. The TDA pipeline measures topological complexity of *density fields* — low-dimensional trajectories do not generate sufficiently rich topological structure for meaningful γ measurement.
agents/manuscript/section5_why_gamma_one.md:103:This narrows the domain of γ: it is applicable to **high-dimensional activity fields** (multi-NMO dynamics, spatial grids, reaction-diffusion fields), not to arbitrary dynamical systems.
agents/manuscript/section5_why_gamma_one.md:107:Five candidate formulas from critical exponent theory were tested against the 2D Ising measurement (γ_measured = 1.329):
agents/manuscript/section5_why_gamma_one.md:109:| Formula | Predicted γ (2D Ising) | Error |
agents/manuscript/section5_why_gamma_one.md:117:**Verdict: NO EXACT MATCH.** The closest formula ν·z/d = 1.083 is within 0.25 of the measured 1.329, but this is not precise enough to claim derivation from known critical exponents. The relationship between γ and standard universality class exponents, if any, is not a simple ratio.
agents/manuscript/section5_why_gamma_one.md:119:### 5.8 Synthesis: what γ actually is
agents/manuscript/section5_why_gamma_one.md:121:The seven experiments converge on a picture that is less dramatic than "universal law" but more honest and still significant:
agents/manuscript/section5_why_gamma_one.md:123:**1. γ is a topological scaling exponent of multi-dimensional density fields.**
agents/manuscript/section5_why_gamma_one.md:126:**2. γ ≈ 1.0 is the baseline for systems with moderate topological variability.**
agents/manuscript/section5_why_gamma_one.md:127:It occurs when topological features (connected components) are born and die at moderate, approximately proportional rates. Too much order (strong spatial correlations, rigid regimes) → γ > 1. Too much chaos (unconstrained fluctuations) → γ > 1 via extreme events. The balance → γ ≈ 1.
agents/manuscript/section5_why_gamma_one.md:129:**3. γ is NOT a critical exponent in the Ising/RG sense.**
agents/manuscript/section5_why_gamma_one.md:132:**4. γ IS a diagnostic of organizational regime in multi-component systems.**
agents/manuscript/section5_why_gamma_one.md:133:Across DNCA (6 NMO operators), Ising (32×32 grid), MFN⁺ (128×128 R-D field), zebrafish (pigmentation density field), and market (Kuramoto coherence): γ ∈ [0.86, 1.33] consistently appears when the system has *moderate topological variability* — the regime we identified as metastable in Section 4.
agents/manuscript/section5_why_gamma_one.md:136:Three substrates (zebrafish, MFN⁺, market) converge on γ ∈ [0.865, 1.081]. This convergence persists because:
agents/manuscript/section5_why_gamma_one.md:140:- Controls (γ_ctrl ≈ 0) confirm the signal
agents/manuscript/section5_why_gamma_one.md:142:However, the specific value ~1.0 may reflect a mathematical property of the Theil-Sen regression on log-deltas of persistent homology when the underlying density field has moderate variance — not a universal constant of organized systems.
agents/manuscript/section5_why_gamma_one.md:146:The original claim ("γ ≈ 1.0 is a substrate-independent invariant") is replaced by a more precise and defensible statement:
agents/manuscript/section5_why_gamma_one.md:148:> **γ-scaling measured via cubical persistent homology on multi-dimensional density fields consistently yields γ ∈ [0.86, 1.33] for systems operating in the metastable regime, across biological (zebrafish), morphogenetic (Gray-Scott), computational (DNCA at optimal competition), economic (Kuramoto), and physical (Ising near T_c) substrates. This convergence is not a measurement artifact (controls yield γ ≈ 0), not a critical exponent (not peaked at phase transitions), and not universal to all dynamical systems (low-dimensional ODEs are out of scope). It is a topological signature of multi-component systems operating with moderate topological variability.**
agents/manuscript/section5_why_gamma_one.md:152:1. Why does the log-log scaling of Δpe₀ vs Δβ₀ approach unity specifically for moderate-variance density fields? An analytical derivation connecting γ to the variance of the persistence diagram would strengthen the theoretical foundation.
agents/manuscript/section5_why_gamma_one.md:154:2. The prediction error field in DNCA shows γ_PE ≈ 0.76 across ALL competition levels (Section 4.5). If PE represents the system-environment interface, why is it always in the metastable range regardless of internal dynamics?
agents/manuscript/section5_why_gamma_one.md:156:3. The Ising result (γ monotonically decreasing with T) suggests γ captures spatial ORDER, not criticality. Can this be reconciled with the DNCA result (γ minimized at optimal competition ≈ 0.75)?
agents/manuscript/section5_why_gamma_one.md:172:Tognoli E., Kelso J.A.S. (2014) The metastable brain. *Neuron* 81(1):35–48.
```

## config/analysis_split.yaml

_matches: 1_

```
config/analysis_split.yaml:1:# Immutable analysis split — PhysioNet cardiac γ-program
```

## contracts/semantic_drift_config.yaml

_matches: 2_

```
contracts/semantic_drift_config.yaml:24:  - universal
contracts/semantic_drift_config.yaml:53:# the full HRV / γ-program corpus, treat PR surfaces as out-of-scope
```

## core/rust/geosync-accel/README.md

_matches: 4_

```
core/rust/geosync-accel/README.md:19:| `gamma_kernel.rs` | SIMD-accelerated Theil-Sen regression + parallel bootstrap |
core/rust/geosync-accel/README.md:90:from core.accel import compute_gamma_accel, hilbert_sort, simd_info
core/rust/geosync-accel/README.md:93:result = compute_gamma_accel(topo_data, cost_data)
core/rust/geosync-accel/README.md:94:print(f"gamma = {result['gamma']:.4f} (backend: {ACCEL_BACKEND})")
```

## docs/ADVERSARIAL_CONTROLS.md

_matches: 66_

```
docs/ADVERSARIAL_CONTROLS.md:1:# Adversarial Controls — Protocol Constraints for γ Claims
docs/ADVERSARIAL_CONTROLS.md:4:> Governs the generation, validation, and reporting of every γ-related
docs/ADVERSARIAL_CONTROLS.md:11:adversarial-control and falsification specification. Every γ-related
docs/ADVERSARIAL_CONTROLS.md:19:of γ, a 1/f-like spectral exponent, a DFA exponent, an avalanche
docs/ADVERSARIAL_CONTROLS.md:21:substrate: neural, neurorobotic, reaction-diffusion, Kuramoto, or any
docs/ADVERSARIAL_CONTROLS.md:30:  γ ≈ 1 is a meaningful candidate regime marker *in healthy neural
docs/ADVERSARIAL_CONTROLS.md:31:  systems under suitable conditions*, not as proof of universality.
docs/ADVERSARIAL_CONTROLS.md:43:  evidence of a universal criticality law.
docs/ADVERSARIAL_CONTROLS.md:47:any repository-level γ claim. Unverified citations of any form are
docs/ADVERSARIAL_CONTROLS.md:53:γ ≈ 1 is a **candidate regime marker**. It is never, on its own,
docs/ADVERSARIAL_CONTROLS.md:55:universal law. Every γ-related claim in this repository MUST pass the
docs/ADVERSARIAL_CONTROLS.md:59:A γ value with no adversarial control is a number, not evidence.
docs/ADVERSARIAL_CONTROLS.md:69:- **Definition.** Re-estimate γ on versions of the data in which
docs/ADVERSARIAL_CONTROLS.md:75:- **Why it matters.** Any γ value produced by a structure-destroying
docs/ADVERSARIAL_CONTROLS.md:76:  surrogate that matches the observed γ indicates that the effect is
docs/ADVERSARIAL_CONTROLS.md:79:- **Pass criterion.** Observed γ lies outside the two-sided 95 %
docs/ADVERSARIAL_CONTROLS.md:82:- **Fail criterion.** Observed γ falls within the surrogate
docs/ADVERSARIAL_CONTROLS.md:88:- **Definition.** Re-estimate γ after mechanism-targeted perturbations
docs/ADVERSARIAL_CONTROLS.md:89:  of the system whose γ is claimed: weaken or remove coupling, remove
docs/ADVERSARIAL_CONTROLS.md:95:- **Why it matters.** A γ value that does not depend on the proposed
docs/ADVERSARIAL_CONTROLS.md:96:  mechanism cannot support a mechanistic interpretation of that γ.
docs/ADVERSARIAL_CONTROLS.md:98:  degrades γ (confidence intervals separated from the unperturbed
docs/ADVERSARIAL_CONTROLS.md:100:- **Fail criterion.** γ is preserved under removal of the claimed
docs/ADVERSARIAL_CONTROLS.md:101:  mechanism. The mechanism claim is retracted; the γ value may still
docs/ADVERSARIAL_CONTROLS.md:110:- **Why it matters.** γ claims must disclose whether the effect is
docs/ADVERSARIAL_CONTROLS.md:114:  E/I balance regimes, not universally across topology and coupling.
docs/ADVERSARIAL_CONTROLS.md:115:- **Pass criterion.** γ claim is classified and reported as robust,
docs/ADVERSARIAL_CONTROLS.md:120:- **Fail criterion.** γ ≈ 1 appears only under accidental tuning and
docs/ADVERSARIAL_CONTROLS.md:133:  yields the same γ under the same pipeline, the γ measures the
docs/ADVERSARIAL_CONTROLS.md:135:- **Pass criterion.** Every counter-model tested produces a γ that is
docs/ADVERSARIAL_CONTROLS.md:138:- **Fail criterion.** Any counter-model reproduces the observed γ
docs/ADVERSARIAL_CONTROLS.md:144:- **Definition.** Re-estimate γ under representational changes that
docs/ADVERSARIAL_CONTROLS.md:156:- **Pass criterion.** γ remains within the reported confidence
docs/ADVERSARIAL_CONTROLS.md:160:- **Fail criterion.** γ collapses, reverses sign, or fails the higher-
docs/ADVERSARIAL_CONTROLS.md:167:Each γ claim MUST explicitly address each of the following items.
docs/ADVERSARIAL_CONTROLS.md:176:- **Why it can fake γ ≈ 1.** No criticality is required; any broad
docs/ADVERSARIAL_CONTROLS.md:180:  broad-τ mixture. If γ matches the primary result, the criticality
docs/ADVERSARIAL_CONTROLS.md:189:- **Why it can fake γ ≈ 1.** Many standard pipelines (Welch with
docs/ADVERSARIAL_CONTROLS.md:193:- **Concrete test.** Re-estimate γ under at least two alternate
docs/ADVERSARIAL_CONTROLS.md:195:  stability of the fit; KPSS or ADF on the residuals). Report every γ
docs/ADVERSARIAL_CONTROLS.md:196:  produced, not only the pipeline that yields γ ≈ 1.
docs/ADVERSARIAL_CONTROLS.md:203:- **Why it can fake γ ≈ 1.** Plasticity-driven drift of unit gains or
docs/ADVERSARIAL_CONTROLS.md:207:  input statistics; re-estimate γ. If γ ≈ 1 persists, plasticity is not
docs/ADVERSARIAL_CONTROLS.md:208:  the operating cause. If γ ≈ 1 disappears, plasticity *is* necessary
docs/ADVERSARIAL_CONTROLS.md:220:- **Why it can fake γ ≈ 1.** A Brownian process analysed over a
docs/ADVERSARIAL_CONTROLS.md:224:- **Concrete test.** Fit γ over at least two non-overlapping decades
docs/ADVERSARIAL_CONTROLS.md:233:- **What it is.** The reported γ is the outcome of an implicit search
docs/ADVERSARIAL_CONTROLS.md:235:  run that produced γ ≈ 1 reaches the report.
docs/ADVERSARIAL_CONTROLS.md:236:- **Why it can fake γ ≈ 1.** Selection bias on the reporting side.
docs/ADVERSARIAL_CONTROLS.md:245:Every γ-related result in this repository MUST disclose **all twelve**
docs/ADVERSARIAL_CONTROLS.md:264:   γ distributions and permutation p-values.
docs/ADVERSARIAL_CONTROLS.md:266:   the γ change under each.
docs/ADVERSARIAL_CONTROLS.md:268:    γ under the same pipeline.
docs/ADVERSARIAL_CONTROLS.md:286:1. **Structure-destroying shuffle persistence.** γ ≈ 1 persists after
docs/ADVERSARIAL_CONTROLS.md:288:2. **Null-control equivalence.** γ ≈ 1 appears equally in a null or
docs/ADVERSARIAL_CONTROLS.md:293:4. **No uncertainty estimate.** A γ value is reported without bootstrap
docs/ADVERSARIAL_CONTROLS.md:294:   CI, permutation distribution, or analytic SE. Unquantified γ is not
docs/ADVERSARIAL_CONTROLS.md:300:   mechanistic finding on one substrate to a universal law, without
docs/ADVERSARIAL_CONTROLS.md:313:- "γ ≈ 1 proves criticality / cognition / intelligence / agency."
docs/ADVERSARIAL_CONTROLS.md:314:- "γ ≈ 1 is a universal regime marker across substrates."
docs/ADVERSARIAL_CONTROLS.md:317:- "Because the biological literature shows γ ≈ 1 in some healthy
docs/ADVERSARIAL_CONTROLS.md:318:  neural systems, γ ≈ 1 in a software / LLM / non-biological substrate
docs/ADVERSARIAL_CONTROLS.md:320:- Any statement that cites γ ≈ 1 as primary evidence for a
docs/ADVERSARIAL_CONTROLS.md:325:  (2019) into universal claims beyond the conditions those papers
docs/ADVERSARIAL_CONTROLS.md:328:Counterexamples (γ ≉ 1 in structurally similar systems; γ ≈ 1 in
docs/ADVERSARIAL_CONTROLS.md:341:  correct γ value interpreted outside these bounds is a violation of
```

## docs/API.md

_matches: 26_

```
docs/API.md:44:| `window` | `int` | `16` | Sliding window size for circular buffers. Must be >= 8. Larger window = more stable gamma but slower response to changes. |
docs/API.md:105:- Computes per-domain Jacobian, gamma, and bootstrap CI.
docs/API.md:107:  phase portrait, resilience, modulation, and universal scaling test.
docs/API.md:120:print(state.gamma_mean)     # ~1.0
docs/API.md:146:| `gamma` | `dict` | Per-domain and mean gamma values with CIs |
docs/API.md:214:| `gamma_per_domain` | `dict[str, float]` | Theil-Sen gamma per domain. `NaN` during warm-up. |
docs/API.md:215:| `gamma_ci_per_domain` | `dict[str, tuple[float, float]]` | Bootstrap 95% CI `(low, high)` per domain |
docs/API.md:216:| `gamma_mean` | `float` | Mean gamma across all domains with finite values |
docs/API.md:217:| `gamma_std` | `float` | Std of gamma across domains |
docs/API.md:218:| `cross_coherence` | `float` | `1 - std/mean` of gammas, clamped to `[0, 1]`. Measures cross-domain agreement. |
docs/API.md:224:| `dgamma_dt` | `float` | Rate of change of `gamma_mean` over the recent window (Theil-Sen slope) |
docs/API.md:225:| `gamma_ema_per_domain` | `dict[str, float]` | Exponential moving average of gamma per domain (alpha=0.3) |
docs/API.md:231:| `universal_scaling_p` | `float` | Permutation p-value for the hypothesis that all domains share the same gamma. Low p = substrates diverging. |
docs/API.md:262:| `cross_jacobian` | `dict[str, dict[str, float]] \| None` | `None` | Cross-domain Jacobian `J[i][j] = d(gamma_i)/d(state_mean_j)` |
docs/API.md:265:| `ci_width_mean` | `float` | `NaN` | Mean width of gamma CI across domains |
docs/API.md:348:synthetic time series that converge toward the metastable gamma ≈ 1.0 regime.
docs/API.md:352:Simulates a BN-Syn spiking network oscillating near criticality (gamma ≈ 0.95).
docs/API.md:389:Simulates market Kuramoto dynamics.
docs/API.md:405:METASTABLE   = "METASTABLE"     # gamma in [0.85, 1.15], rho in [0.80, 1.25]
docs/API.md:407:DIVERGING    = "DIVERGING"      # gamma > 1.15
docs/API.md:408:COLLAPSING   = "COLLAPSING"     # gamma < 0.85
docs/API.md:438:print(f"Gamma mean   : {state.gamma_mean:.4f}")
docs/API.md:440:print(f"Univ. scaling: p = {state.universal_scaling_p:.4f}")
docs/API.md:442:for domain, gamma in state.gamma_per_domain.items():
docs/API.md:443:    ci = state.gamma_ci_per_domain[domain]
docs/API.md:444:    print(f"  {domain:20s}: gamma={gamma:.3f}  CI=[{ci[0]:.3f}, {ci[1]:.3f}]")
```

## docs/BIBLIOGRAPHY.md

_matches: 23_

```
docs/BIBLIOGRAPHY.md:5:> **Role in NFI platform:** Integrating mirror layer — cross-substrate gamma-scaling diagnostics
docs/BIBLIOGRAPHY.md:26:| **Layer 1: Collect** | `observe()` adapters | Kuramoto 1984; Acebrón+ 2005; Pikovsky+ 2001 | F, A, B |
docs/BIBLIOGRAPHY.md:28:| **Layer 3: Gamma** | K ~ C^{−γ} regression | Clauset+ 2009; Efron & Tibshirani 1993; DiCiccio & Efron 1996 | A, B |
docs/BIBLIOGRAPHY.md:33:| **Cross-domain scaling** | γ ≈ 1.0 invariant | West+ 1997; Mora & Bialek 2011; Fries 2005, 2015; Buzsáki & Wang 2012 | A, F |
docs/BIBLIOGRAPHY.md:34:| **Zebrafish substrate** | d = 47, γ_WT = 1.043 | McGuirl+ 2020; Turing 1952 | A, F |
docs/BIBLIOGRAPHY.md:58:SOC theory — universal power-law scaling at edge of chaos.
docs/BIBLIOGRAPHY.md:63:**[F7]** Kuramoto Y. (1984). *Chemical Oscillations, Waves, and Turbulence*. Springer. DOI: [10.1007/978-3-642-69689-3](https://doi.org/10.1007/978-3-642-69689-3)
docs/BIBLIOGRAPHY.md:67:Communication-through-coherence — functional rationale for gamma scaling.
docs/BIBLIOGRAPHY.md:73:**[A1]** Acebrón J.A., Bonilla L.L., Pérez Vicente C.J., Ritort F., Spigler R. (2005). The Kuramoto model: A simple paradigm for synchronization phenomena. *Rev. Mod. Phys.*, 77(1), 137--185. DOI: [10.1103/RevModPhys.77.137](https://doi.org/10.1103/RevModPhys.77.137)
docs/BIBLIOGRAPHY.md:76:**[A2]** Strogatz S.H. (2000). From Kuramoto to Crawford: Exploring the onset of synchronization. *Physica D*, 143(1--4), 1--20. DOI: [10.1016/S0167-2789(00)00094-4](https://doi.org/10.1016/S0167-2789(00)00094-4)
docs/BIBLIOGRAPHY.md:79:**[A3]** Buzsáki G., Wang X.-J. (2012). Mechanisms of gamma oscillations. *Annu. Rev. Neurosci.*, 35, 203--225. DOI: [10.1146/annurev-neuro-062111-150444](https://doi.org/10.1146/annurev-neuro-062111-150444)
docs/BIBLIOGRAPHY.md:80:Gamma-band oscillation mechanisms — motivates the γ invariant.
docs/BIBLIOGRAPHY.md:83:Updated CTC hypothesis — gamma scaling ↔ computational efficiency.
docs/BIBLIOGRAPHY.md:89:Gold-standard power-law fitting — gamma exponent validation.
docs/BIBLIOGRAPHY.md:92:Scaling exponents ↔ biological function — framework for γ ~ 1.0.
docs/BIBLIOGRAPHY.md:94:**[A8]** Tognoli E., Kelso J.A.S. (2014). The metastable brain. *Neuron*, 81(1), 35--48. DOI: [10.1016/j.neuron.2013.12.022](https://doi.org/10.1016/j.neuron.2013.12.022)
docs/BIBLIOGRAPHY.md:107:TDA on zebrafish patterning — primary reference (d = 47, γ_WT = 1.043).
docs/BIBLIOGRAPHY.md:119:BCa bootstrap with bias correction — CI construction on γ estimates.
docs/BIBLIOGRAPHY.md:125:Universal allometric scaling from fractal geometry — γ ~ 1.0 invariant theory.
docs/BIBLIOGRAPHY.md:128:Biological systems at critical points — universal γ hypothesis support.
docs/BIBLIOGRAPHY.md:147:Coordination dynamics and metastability — conceptual foundation.
docs/BIBLIOGRAPHY.md:150:Bootstrap CI methodology — all γ CI computations.
docs/BIBLIOGRAPHY.md:185:| Kuramoto 1984 | **x** | | **x** | **x** | | |
```

## docs/CLAIM_BOUNDARY.md

_matches: 29_

```
docs/CLAIM_BOUNDARY.md:1:# γ-Claim Boundary — v1.0
docs/CLAIM_BOUNDARY.md:3:> **Authority.** NeoSynaptex γ-program, `CNS-AI Validation Protocol v1` §Step 1
docs/CLAIM_BOUNDARY.md:14:> **γ ≈ 1.0 is a candidate cross-substrate regime marker for a
docs/CLAIM_BOUNDARY.md:15:> metastable critical state, tested through an open, falsifiable
docs/CLAIM_BOUNDARY.md:28:- "γ ≈ 1.0 is a law."
docs/CLAIM_BOUNDARY.md:29:- "γ ≈ 1.0 proves criticality."
docs/CLAIM_BOUNDARY.md:30:- "γ ≈ 1.0 proves cognition, intelligence, consciousness, or selfhood."
docs/CLAIM_BOUNDARY.md:31:- "Substrate-independent law of metastable computation."
docs/CLAIM_BOUNDARY.md:34:- "γ ≈ 1.0 is universal across all substrates."
docs/CLAIM_BOUNDARY.md:37:  Bouchaud 2024, Aguilera 2015, etc.) as evidence **for** γ in
docs/CLAIM_BOUNDARY.md:46:> γ = {value} ± {CI}, consistent with a metastable critical regime
docs/CLAIM_BOUNDARY.md:51:from `NULL_MODEL_HIERARCHY.md` did not reproduce the observed γ.
docs/CLAIM_BOUNDARY.md:56:> `CROSS_SUBSTRATE_EVIDENCE_MATRIX.md`, γ falls within the [a, b]
docs/CLAIM_BOUNDARY.md:65:> "Within {substrate}, γ {does / does not} survive {null family}
docs/CLAIM_BOUNDARY.md:74:Any γ-statement in a canonical artefact MUST name all of:
docs/CLAIM_BOUNDARY.md:93:### 5.1 Evidential core — admissible for γ-claims
docs/CLAIM_BOUNDARY.md:103:- γ has been reproduced from raw data under the frozen pipeline.
docs/CLAIM_BOUNDARY.md:105:  NOT reproduce the observed γ distribution.
docs/CLAIM_BOUNDARY.md:111:`evidence/gamma_ledger.json` are internal derivations; they are
docs/CLAIM_BOUNDARY.md:118:experiments but MUST NOT support a γ-claim in any outward-facing
docs/CLAIM_BOUNDARY.md:132:  falsified γ, surrogate family matched γ).
docs/CLAIM_BOUNDARY.md:139:Every γ-statement is tagged with exactly one of the following,
docs/CLAIM_BOUNDARY.md:160:avalanches, etc.) motivate the γ search and provide method hierarchy
docs/CLAIM_BOUNDARY.md:163:- Count as evidence for NeoSynaptex γ.
docs/CLAIM_BOUNDARY.md:174:*eLife* 12:RP89337) shows γ = 1.1–1.3 can emerge from coupling to
docs/CLAIM_BOUNDARY.md:177:γ-claim must be tested against it, not just shuffled / IAAFT / OU.
docs/CLAIM_BOUNDARY.md:179:If γ cannot be separated from the latent-variable null on any
docs/CLAIM_BOUNDARY.md:199:| v1.0 | 2026-04-14 | Initial canonical claim boundary. | NeoSynaptex γ-program Phase I §Step 1. |
docs/CLAIM_BOUNDARY.md:203:**claim_status:** measured (about the boundary itself; the γ-claims it constrains are still `hypothesized` pending Phase IV–VI replications)
```

## docs/CLAIM_BOUNDARY_CNS_AI.md

_matches: 12_

```
docs/CLAIM_BOUNDARY_CNS_AI.md:6:> **Applies to:** the CNS-AI Loop substrate claim `γ=1.059, p=0.005, n=8271, CI=[0.985,1.131]` previously displayed in `README.md` and stamped in `substrates/cns_ai_loop/__init__.py`.
docs/CLAIM_BOUNDARY_CNS_AI.md:16:**R2 — Category error in unit of analysis.** `xform_full_archive_gamma_report.json` records `n=8271` with a `by_ext` breakdown (`.py=5979, .odt=986, .md=938, .txt=188, .json=147`). The unit of analysis is therefore **file-system entries classified by extension**. The substrate is described as a human-AI cognitive loop whose unit should be a session, decision, or interaction episode. Files are not cognitions. Counting files produces a number; it does not measure the substrate the claim names.
docs/CLAIM_BOUNDARY_CNS_AI.md:28:- any language that treats `γ=1.059 / n=8271` as evidence for metastability, criticality, cognition, a universal law, or a cross-substrate invariant.
docs/CLAIM_BOUNDARY_CNS_AI.md:45:- The headline figures `γ=1.059, p=0.005, n=8271, CI=[0.985,1.131]`.
docs/CLAIM_BOUNDARY_CNS_AI.md:46:- The status of `xform_full_archive_gamma_report.json` as evidence (re-classified: report of a historical scan, not a validation artefact).
docs/CLAIM_BOUNDARY_CNS_AI.md:50:- The five substrates already present in `evidence/gamma_ledger.json` with `status: VALIDATED`:
docs/CLAIM_BOUNDARY_CNS_AI.md:51:  `zebrafish_wt`, `gray_scott`, `kuramoto`, `bnsyn`, `eeg_physionet`
docs/CLAIM_BOUNDARY_CNS_AI.md:52:  (plus `hrv_physionet`, `eeg_resting`, `serotonergic_kuramoto`, `hrv_fantasia` under their existing entry-level `status` and `verdict` fields).
docs/CLAIM_BOUNDARY_CNS_AI.md:66:| §4 path repair | `derive_real_gamma.py` reads from `substrates/cns_ai_loop/evidence/sessions/` which never contained the 8271 files. Repair has no valid target. |
docs/CLAIM_BOUNDARY_CNS_AI.md:68:| §6 reproduce | Re-deriving γ from the claimed pipeline on the claimed corpus is impossible; the corpus does not exist. |
docs/CLAIM_BOUNDARY_CNS_AI.md:81:4. Ships a reproducible pipeline that re-derives γ from the bundle with `substrate_code_hash` and `data_sha256` stamped on every row.
docs/CLAIM_BOUNDARY_CNS_AI.md:92:- **Code annotation:** `substrates/cns_ai_loop/derive_real_gamma.py` now raises `CorpusNotFoundError` at the loader boundary; no silent fallback.
```

## docs/DATA_ACQUISITION_AND_REPLICATION_PLAN.md

_matches: 11_

```
docs/DATA_ACQUISITION_AND_REPLICATION_PLAN.md:3:> **Authority.** γ-program Phase III §Step 12.
docs/DATA_ACQUISITION_AND_REPLICATION_PLAN.md:5:> expected γ-method, controls, compute estimate.
docs/DATA_ACQUISITION_AND_REPLICATION_PLAN.md:16:| Rank | Dataset | Substrate class | Format | Size | γ-method primary | Expected runtime | URL |
docs/DATA_ACQUISITION_AND_REPLICATION_PLAN.md:29:| Rank | Dataset | Substrate class | Format | Size | γ-method primary | Expected runtime | URL |
docs/DATA_ACQUISITION_AND_REPLICATION_PLAN.md:44:| Rank | Dataset | Substrate class | Format | Size | γ-method primary | DUA path | URL |
docs/DATA_ACQUISITION_AND_REPLICATION_PLAN.md:86:  - γ: Theil-Sen slope on log(K), log(C).
docs/DATA_ACQUISITION_AND_REPLICATION_PLAN.md:102:  - Substrate-wise γ: median across parcels per subject.
docs/DATA_ACQUISITION_AND_REPLICATION_PLAN.md:134:## 3. Per-Tier prior γ ranges
docs/DATA_ACQUISITION_AND_REPLICATION_PLAN.md:140:stating γ expectations as if they were results. **These priors are
docs/DATA_ACQUISITION_AND_REPLICATION_PLAN.md:146:| Substrate class | Prior range for γ (literature-sourced) | Primary null family most likely to threaten |
docs/DATA_ACQUISITION_AND_REPLICATION_PLAN.md:212:**claim_status:** measured (about the plan itself; individual dataset γ-claims are hypothesized until Phase IV–VI reports land).
```

## docs/EVIDENCE_LEDGER_GUIDE.md

_matches: 17_

```
docs/EVIDENCE_LEDGER_GUIDE.md:6:> The evidence system consists of `evidence/gamma_ledger.json`, the
docs/EVIDENCE_LEDGER_GUIDE.md:8:> they form a tamper-evident, append-only record of all validated gamma
docs/EVIDENCE_LEDGER_GUIDE.md:17:  gamma_ledger.json          # authoritative gamma values per substrate
docs/EVIDENCE_LEDGER_GUIDE.md:18:  gamma_provenance.md        # tier classification and falsification conditions
docs/EVIDENCE_LEDGER_GUIDE.md:30:## `gamma_ledger.json` — Schema
docs/EVIDENCE_LEDGER_GUIDE.md:37:  "invariant": "gamma derived only, never assigned",
docs/EVIDENCE_LEDGER_GUIDE.md:50:| `gamma` | `number` | yes | Theil-Sen gamma exponent (point estimate) |
docs/EVIDENCE_LEDGER_GUIDE.md:61:| `derivation_method` | `string` | yes | Human-readable description of how gamma was derived |
docs/EVIDENCE_LEDGER_GUIDE.md:70:  "gamma": 1.055,
docs/EVIDENCE_LEDGER_GUIDE.md:100:- `locked: true` is set — the gamma value is frozen.
docs/EVIDENCE_LEDGER_GUIDE.md:122:The gamma value was not measured directly from the substrate but derived
docs/EVIDENCE_LEDGER_GUIDE.md:125:Example: a theoretical prediction from a mean-field model, or a gamma value
docs/EVIDENCE_LEDGER_GUIDE.md:136:Example: a mathematical signal constructed to have exactly gamma = 1.0 by
docs/EVIDENCE_LEDGER_GUIDE.md:140:**Meaning:** Never counts as evidence for the gamma = 1.0 claim. Used only
docs/EVIDENCE_LEDGER_GUIDE.md:171:    print(entry["t"], entry["phase"], entry["gamma"]["mean"])
docs/EVIDENCE_LEDGER_GUIDE.md:233:its `gamma`, `ci_low`, `ci_high`, and `status` fields must not be modified.
docs/EVIDENCE_LEDGER_GUIDE.md:253:3. Add the entry to `evidence/gamma_ledger.json` with `status: "PENDING"` and
```

## docs/EXTERNAL_PRECEDENTS.md

_matches: 4_

```
docs/EXTERNAL_PRECEDENTS.md:4:> for γ; it records external conceptual precedents only.**
docs/EXTERNAL_PRECEDENTS.md:8:This document records **external conceptual precedents** that are useful for `Neosynaptex`, but are **not part of canonical evidentiary claims**. They do not strengthen the γ-hypothesis directly. They justify architectural, operational, and safety choices around agent loops, human supervision, and observability.
docs/EXTERNAL_PRECEDENTS.md:12:John Boyd's OODA loop — **Observe → Orient → Decide → Act** — is an independently established decision-cycle model in military and strategic cognition. Air University summaries describe Boyd's concept as a loop in which success depends on observing, orienting, deciding, and acting more effectively than the opponent. In `Neosynaptex`, this is relevant as an **external structural precedent** for a cyclic agent contract, independent of any γ-based claim. It should be cited as **architectural convergence**, not as evidence for metastability.
docs/EXTERNAL_PRECEDENTS.md:41:These precedents are **conceptual and operational supports**, not canonical proof objects. They belong in `EXTERNAL_PRECEDENTS.md`, not in the γ canon. Their role is to strengthen loop design, observability, and supervision discipline without overstating empirical implications.
```

## docs/EXTERNAL_REPLICATION_INVITATION.md

_matches: 12_

```
docs/EXTERNAL_REPLICATION_INVITATION.md:1:# External Replication Invitation — PhysioNet Cardiac HRV γ Pilot
docs/EXTERNAL_REPLICATION_INVITATION.md:23:- γ, Δh, and h(q=2) per-subject within the tolerance window in §7.
docs/EXTERNAL_REPLICATION_INVITATION.md:32:A replication that produces different γ or rejects the pattern is a
docs/EXTERNAL_REPLICATION_INVITATION.md:40:- n=1 NSR2DB pilot → γ ≈ 1.0855, IAAFT not separable → revealed a
docs/EXTERNAL_REPLICATION_INVITATION.md:42:- n=5 NSR2DB multifractal pilot → γ mean **0.50 ± 0.44**, Δh = 0.19,
docs/EXTERNAL_REPLICATION_INVITATION.md:43:  beat-null separates on 4/5. Cross-subject γ **not** near 1.0;
docs/EXTERNAL_REPLICATION_INVITATION.md:110:- `substrates/physionet_hrv/hrv_gamma_fit.py` — RR → uniform-4Hz,
docs/EXTERNAL_REPLICATION_INVITATION.md:120:# γ-fit (Welch-PSD + Theil-Sen)
docs/EXTERNAL_REPLICATION_INVITATION.md:176:| γ (`value`) | ± 0.01 vs this repo's result.json             |
docs/EXTERNAL_REPLICATION_INVITATION.md:177:| γ CI        | ± 0.02 on both bounds                         |
docs/EXTERNAL_REPLICATION_INVITATION.md:248:- Cross-substrate universal-γ framing. Both HRV substrates contradict
docs/EXTERNAL_REPLICATION_INVITATION.md:249:  substrate-independence at the n=5 pilot level (γ mean 0.50 ± 0.44
```

## docs/KNOWN_LIMITATIONS.md

_matches: 38_

```
docs/KNOWN_LIMITATIONS.md:31:visibly wide (±0.1–0.25 on the γ point estimate). The replication
docs/KNOWN_LIMITATIONS.md:38:- Scale hrv_fantasia to all 20 (10 young + 10 elderly); expect γ to
docs/KNOWN_LIMITATIONS.md:41:### L2. eeg_resting lands slightly above the metastable window
docs/KNOWN_LIMITATIONS.md:43:The Welch+Theil-Sen resting-state estimate reports γ = 1.255,
docs/KNOWN_LIMITATIONS.md:44:CI95 [1.032, 1.452]. The NFI metastable window is [0.7, 1.3].
docs/KNOWN_LIMITATIONS.md:49:   runs from the same dataset reports γ = 1.068 — well inside the
docs/KNOWN_LIMITATIONS.md:54:   γ = 1.26 is consistent with that band.
docs/KNOWN_LIMITATIONS.md:56:**Impact.** The `test_gamma_finite_and_in_physical_band` assertion
docs/KNOWN_LIMITATIONS.md:58:the stricter metastable [0.7, 1.3]. This is flagged in the test
docs/KNOWN_LIMITATIONS.md:59:docstring and recorded in `evidence/gamma_provenance.md`.
docs/KNOWN_LIMITATIONS.md:64:frequency range to force γ < 1.3 would be exactly the kind of
docs/KNOWN_LIMITATIONS.md:67:### L3. serotonergic_kuramoto is a calibrated T5 substrate with a 1.17× basin
docs/KNOWN_LIMITATIONS.md:69:The serotonergic_kuramoto substrate requires a calibration of the
docs/KNOWN_LIMITATIONS.md:70:operational frequency bandwidth σ_op for the γ ≈ 1 claim to hold.
docs/KNOWN_LIMITATIONS.md:73:- Basin of γ ∈ [0.7, 1.3]: σ_op ∈ [0.058, 0.068] Hz
docs/KNOWN_LIMITATIONS.md:75:- Bootstrap CI on γ at reference σ_op: [0.145, 1.506] — very wide
docs/KNOWN_LIMITATIONS.md:78:that the serotonergic substrate is *consistent with* γ ≈ 1 in a narrow
docs/KNOWN_LIMITATIONS.md:80:the T5 classification in `evidence/gamma_provenance.md`. The
docs/KNOWN_LIMITATIONS.md:86:Documented in `substrates/serotonergic_kuramoto/CALIBRATION.md`.
docs/KNOWN_LIMITATIONS.md:90:The critical-branching substrate `bn_syn` reports γ = 0.946 with
docs/KNOWN_LIMITATIONS.md:93:**Impact.** The γ point estimate is near 1, but the log-log fit is
docs/KNOWN_LIMITATIONS.md:95:R² = 0.28 directly, and `evidence/gamma_provenance.md` lists it under
docs/KNOWN_LIMITATIONS.md:100:γ point estimate is independently consistent with the other T3
docs/KNOWN_LIMITATIONS.md:111:its parameters — the γ comes out of an unrelated paper’s model — but
docs/KNOWN_LIMITATIONS.md:116:Two ledger entries (`nfi_unified`, `cns_ai_loop`) have γ values
docs/KNOWN_LIMITATIONS.md:123:This is visible in every count row of `evidence/gamma_provenance.md`.
docs/KNOWN_LIMITATIONS.md:125:### L7. `cfp_diy` reports γ = 1.83 (out-of-regime)
docs/KNOWN_LIMITATIONS.md:127:The Cognitive Field Protocol ABM substrate gives γ = 1.832, CI95
docs/KNOWN_LIMITATIONS.md:128:[1.638, 1.978] — well outside the metastable window.
docs/KNOWN_LIMITATIONS.md:131:the ledger as an *out-of-regime witness*: a scenario where the γ
docs/KNOWN_LIMITATIONS.md:133:is not critical. It demonstrates that γ ≈ 1 is a property substrates
docs/KNOWN_LIMITATIONS.md:136:**How this is surfaced:** `evidence/gamma_provenance.md` lists it as
docs/KNOWN_LIMITATIONS.md:137:T3† out-of-regime. The headline "γ ≈ 1 across N substrates" explicitly
docs/KNOWN_LIMITATIONS.md:157:For per-unit γ populations (EEG subjects, HRV subjects, serotonergic
docs/KNOWN_LIMITATIONS.md:159:`1 − SS_resid/SS_total` around the null γ = 1, not a regression R².
docs/KNOWN_LIMITATIONS.md:161:field name `r2` is ambiguous with `core/gamma.py::compute_gamma.r2`
docs/KNOWN_LIMITATIONS.md:193:entries (eeg_resting, hrv_fantasia, serotonergic_kuramoto) should be
docs/KNOWN_LIMITATIONS.md:225:γ value.
```

## docs/LOBSTER_ACQUISITION_PLAN.md

_matches: 16_

```
docs/LOBSTER_ACQUISITION_PLAN.md:3:> **Authority.** γ-program Phase VI §Step 24.
docs/LOBSTER_ACQUISITION_PLAN.md:17:Key properties for γ-measurement:
docs/LOBSTER_ACQUISITION_PLAN.md:31:γ-claims. Published avalanche-analysis papers in finance almost
docs/LOBSTER_ACQUISITION_PLAN.md:32:universally use either LOBSTER or similar proprietary feeds.
docs/LOBSTER_ACQUISITION_PLAN.md:58:parser development, sanity γ-fit — but **not** sufficient for an
docs/LOBSTER_ACQUISITION_PLAN.md:74:- **Three independent γ-estimable signals** per dataset:
docs/LOBSTER_ACQUISITION_PLAN.md:82:### 3.2 Relation to γ-program
docs/LOBSTER_ACQUISITION_PLAN.md:92:  not directly supportive of cross-substrate γ convergence.
docs/LOBSTER_ACQUISITION_PLAN.md:99:   sample. Build the parser and γ-pipeline against it. Verify all
docs/LOBSTER_ACQUISITION_PLAN.md:105:   market_lobster/`) that ships the parser + γ-fit + null
docs/LOBSTER_ACQUISITION_PLAN.md:137:  γ-replication report derived from LOBSTER data may publish the
docs/LOBSTER_ACQUISITION_PLAN.md:138:  DERIVED NUMBERS (γ, CI, null z-scores) and the EXACT CODE PATH,
docs/LOBSTER_ACQUISITION_PLAN.md:160:multi-year studies beyond the current γ-program scope.
docs/LOBSTER_ACQUISITION_PLAN.md:183:- `substrates/market_lobster/` (new package) — parser, γ-fit,
docs/LOBSTER_ACQUISITION_PLAN.md:213:  — unsuitable for microstructure γ).
docs/LOBSTER_ACQUISITION_PLAN.md:221:- No `market_microstructure` γ-claim may be made in any canonical
```

## docs/MEASUREMENT_METHOD_HIERARCHY.md

_matches: 11_

```
docs/MEASUREMENT_METHOD_HIERARCHY.md:1:# γ-Measurement Method Hierarchy — v1.0
docs/MEASUREMENT_METHOD_HIERARCHY.md:3:> **Authority.** γ-program Phase III §Step 14.
docs/MEASUREMENT_METHOD_HIERARCHY.md:4:> **Status.** Canonical. Frozen method stack for every γ-estimation
docs/MEASUREMENT_METHOD_HIERARCHY.md:62:basis for a γ-claim.
docs/MEASUREMENT_METHOD_HIERARCHY.md:94:## 3. γ-specific procedure
docs/MEASUREMENT_METHOD_HIERARCHY.md:96:Every γ-estimation in NeoSynaptex runs this exact pipeline:
docs/MEASUREMENT_METHOD_HIERARCHY.md:118:8. **Null comparison** per `NULL_MODEL_HIERARCHY.md`. γ_real vs
docs/MEASUREMENT_METHOD_HIERARCHY.md:121:   γ, CI, p, x_min, KS-p, IRASA-specparam delta, null z-scores,
docs/MEASUREMENT_METHOD_HIERARCHY.md:160:Every γ-report MUST include, in this order:
docs/MEASUREMENT_METHOD_HIERARCHY.md:174:Missing any of 1–8 → report is incomplete → γ stays at
docs/MEASUREMENT_METHOD_HIERARCHY.md:185:**claim_status:** measured (about the method hierarchy; this document constrains the γ claims that flow through it)
```

## docs/NULL_MODEL_HIERARCHY.md

_matches: 29_

```
docs/NULL_MODEL_HIERARCHY.md:1:# γ-Null Model Hierarchy — v1.0
docs/NULL_MODEL_HIERARCHY.md:3:> **Authority.** γ-program Phase III §Step 15.
docs/NULL_MODEL_HIERARCHY.md:4:> **Status.** Canonical. Frozen null-model suite for every γ-claim.
docs/NULL_MODEL_HIERARCHY.md:11:> **A γ-value is admissible only if it is statistically separable
docs/NULL_MODEL_HIERARCHY.md:13:> significance threshold. If any null family reproduces γ, the
docs/NULL_MODEL_HIERARCHY.md:14:> γ-claim collapses under `CLAIM_BOUNDARY.md §5.3`.**
docs/NULL_MODEL_HIERARCHY.md:18:bootstrap n ≥ 500 surrogates, bootstrap CI95 of γ_real must fall
docs/NULL_MODEL_HIERARCHY.md:31:- **What it tests.** Whether γ depends on *organisation* rather
docs/NULL_MODEL_HIERARCHY.md:43:- **What it tests.** Whether γ requires *nonlinear* phase structure
docs/NULL_MODEL_HIERARCHY.md:59:- **What it tests.** Whether γ can emerge from a non-critical,
docs/NULL_MODEL_HIERARCHY.md:74:- **What it tests.** Whether γ can emerge from event timing alone
docs/NULL_MODEL_HIERARCHY.md:90:- **What it tests.** Whether γ can emerge from a non-critical
docs/NULL_MODEL_HIERARCHY.md:92:  the **strongest known critique** of cross-substrate γ claims —
docs/NULL_MODEL_HIERARCHY.md:93:  the paper reports γ = 1.1–1.3 from latent-variable coupling
docs/NULL_MODEL_HIERARCHY.md:101:  γ-measurement pipeline on the surrogate, compare γ_real to
docs/NULL_MODEL_HIERARCHY.md:102:  surrogate γ distribution.
docs/NULL_MODEL_HIERARCHY.md:103:- **Failure criterion.** If γ_real falls within the surrogate
docs/NULL_MODEL_HIERARCHY.md:128:For every γ-claim:
docs/NULL_MODEL_HIERARCHY.md:134:   each surrogate. Record γ_surrogate distribution per family.
docs/NULL_MODEL_HIERARCHY.md:136:   `z = (γ_real − μ_surrogate) / σ_surrogate`.
docs/NULL_MODEL_HIERARCHY.md:138:5. Bootstrap 95 % CI from resampled data; γ_real must fall
docs/NULL_MODEL_HIERARCHY.md:141:   γ-claim to survive into the evidential lane.
docs/NULL_MODEL_HIERARCHY.md:158:Every γ-report MUST include a null table of this exact shape:
docs/NULL_MODEL_HIERARCHY.md:170:Verdict is `pass` iff |z| ≥ 3 AND γ_real outside null CI95.
docs/NULL_MODEL_HIERARCHY.md:172:(per §2.3 Applicable section). Any `fail` row means the γ-claim
docs/NULL_MODEL_HIERARCHY.md:178:substrate, that substrate's γ-claim:
docs/NULL_MODEL_HIERARCHY.md:188:a **theory revision gate** per γ-program Phase IX §Step 34:
docs/NULL_MODEL_HIERARCHY.md:189:the γ≈1.0 framing must be narrowed to a bounded-regime law.
docs/NULL_MODEL_HIERARCHY.md:199:**claim_status:** measured (about the null hierarchy; it constrains every γ claim)
```

## docs/PREREG_TEMPLATE_GAMMA.md

_matches: 16_

```
docs/PREREG_TEMPLATE_GAMMA.md:1:# γ-Measurement Preregistration Template — v1.0
docs/PREREG_TEMPLATE_GAMMA.md:3:> **Authority.** γ-program Phase III §Step 13.
docs/PREREG_TEMPLATE_GAMMA.md:6:> with NeoSynaptex γ-specific fields.
docs/PREREG_TEMPLATE_GAMMA.md:7:> **Status.** Canonical. Every γ-measurement on every substrate in
docs/PREREG_TEMPLATE_GAMMA.md:26:# Prereg — NeoSynaptex γ-measurement — {substrate_id}
docs/PREREG_TEMPLATE_GAMMA.md:40:    One sentence. What γ value (or range) is predicted, in what
docs/PREREG_TEMPLATE_GAMMA.md:172:  primary_test: <name, e.g. "z-score of γ_real vs null-family means">
docs/PREREG_TEMPLATE_GAMMA.md:184:    What γ value / range is expected under the substrate's
docs/PREREG_TEMPLATE_GAMMA.md:187:    Under the null, γ distribution is <shape>.
docs/PREREG_TEMPLATE_GAMMA.md:189:    If the latent-variable or topology-controlled null reproduces γ,
docs/PREREG_TEMPLATE_GAMMA.md:259:    Under what data pattern do we narrow the γ≈1.0 claim to a
docs/PREREG_TEMPLATE_GAMMA.md:260:    bounded-regime law? (Per γ-program Phase IX §Step 34.)
docs/PREREG_TEMPLATE_GAMMA.md:291:    - γ_real survives all five null families at |z|≥3.
docs/PREREG_TEMPLATE_GAMMA.md:292:    - Bootstrap CI95 of γ_real is outside every surrogate CI95.
docs/PREREG_TEMPLATE_GAMMA.md:295:    - External rerun reproduces γ within preregistered ε.
docs/PREREG_TEMPLATE_GAMMA.md:303:      narrow to bounded-regime law (γ-program §Step 34).
```

## docs/REPLICATION_PROTOCOL.md

_matches: 35_

```
docs/REPLICATION_PROTOCOL.md:1:# Replication Protocol — Independent Validation of γ Claims
docs/REPLICATION_PROTOCOL.md:5:> γ-related claim in this repository MUST meet before it is admitted
docs/REPLICATION_PROTOCOL.md:20:γ-related claims, separated by substrate class. Replication under this
docs/REPLICATION_PROTOCOL.md:27:Applies to every γ-related observation, mechanism claim, or regime-marker
docs/REPLICATION_PROTOCOL.md:43:Other substrate classes (reaction-diffusion, Kuramoto, LLM multi-agent)
docs/REPLICATION_PROTOCOL.md:66:  that returns γ ≉ 1 under the same protocol is a first-class result.
docs/REPLICATION_PROTOCOL.md:80:cross-dataset replication of γ claims in intact neural systems.
docs/REPLICATION_PROTOCOL.md:112:### 4.4 γ estimation requirements
docs/REPLICATION_PROTOCOL.md:140:- Between-dataset consistency: the γ values across replications are
docs/REPLICATION_PROTOCOL.md:145:  γ-CIs whose lower bounds remain consistent with the claimed regime
docs/REPLICATION_PROTOCOL.md:154:- γ does not survive structure-destroying surrogates in any dataset
docs/REPLICATION_PROTOCOL.md:156:- γ collapses or reverses under the mandatory alternate preprocessing.
docs/REPLICATION_PROTOCOL.md:157:- A counter-model reproduces the γ value under the same pipeline.
docs/REPLICATION_PROTOCOL.md:239:- Store enough run length to satisfy the §6.4 γ estimation scaling-range
docs/REPLICATION_PROTOCOL.md:243:### 6.3 γ estimation requirements
docs/REPLICATION_PROTOCOL.md:251:- Remove or freeze homeostatic plasticity; re-estimate γ.
docs/REPLICATION_PROTOCOL.md:252:- Decouple the network or disable sensorimotor feedback; re-estimate γ.
docs/REPLICATION_PROTOCOL.md:254:  spectral energy; re-estimate γ.
docs/REPLICATION_PROTOCOL.md:256:Each perturbation is reported with its γ and CI. The primary
docs/REPLICATION_PROTOCOL.md:258:materially degrades γ (see `docs/ADVERSARIAL_CONTROLS.md §4.2`).
docs/REPLICATION_PROTOCOL.md:269:γ is reported across the full sweep. Claims that γ ≈ 1 only inside a
docs/REPLICATION_PROTOCOL.md:275:- γ survives the mandatory mechanism perturbations without material
docs/REPLICATION_PROTOCOL.md:277:- γ ≈ 1 appears only in a narrow accidental-tuning window of the
docs/REPLICATION_PROTOCOL.md:280:  γ under the same pipeline.
docs/REPLICATION_PROTOCOL.md:281:- Cross-seed variance across replications is so large that the γ
docs/REPLICATION_PROTOCOL.md:288:Every γ-related replication PR MUST file the following block in a
docs/REPLICATION_PROTOCOL.md:296:    One sentence. What is the γ claim, in its minimum admissible form?
docs/REPLICATION_PROTOCOL.md:318:    name: gamma
docs/REPLICATION_PROTOCOL.md:356:- γ-CIs across replications are consistent with the preregistered claim
docs/REPLICATION_PROTOCOL.md:371:- A counter-model reproduces the observed γ under the same pipeline.
docs/REPLICATION_PROTOCOL.md:372:- A mandatory perturbation (§4.2) does not materially change γ when
docs/REPLICATION_PROTOCOL.md:374:- γ collapses or reverses under an alternate preprocessing pipeline.
docs/REPLICATION_PROTOCOL.md:402:- **Replication does not prove universality.** A claim replicated on
docs/REPLICATION_PROTOCOL.md:407:- **γ ≈ 1 is not sufficient by itself.** The scaling exponent alone
docs/REPLICATION_PROTOCOL.md:412:  (H / C / γ) without a numeric P, but it MUST NOT feed any productivity
```

## docs/REPRODUCIBILITY.md

_matches: 28_

```
docs/REPRODUCIBILITY.md:4:> independently verify the gamma-scaling results reported in the manuscript.
docs/REPRODUCIBILITY.md:17:Expected: exits 0 and prints a gamma table matching the values below.
docs/REPRODUCIBILITY.md:45:1. Computes gamma for each substrate from scratch.
docs/REPRODUCIBILITY.md:46:2. Compares each computed gamma against `evidence/gamma_ledger.json`.
docs/REPRODUCIBILITY.md:52:Substrate            gamma  CI_low  CI_high  R2     status
docs/REPRODUCIBILITY.md:58:kuramoto             0.963  0.930   1.000    0.900  OK
docs/REPRODUCIBILITY.md:60:serotonergic_kuramoto 1.068 0.145   1.506    -      OK
docs/REPRODUCIBILITY.md:142:### `xform_gamma_report.json`
docs/REPRODUCIBILITY.md:144:Human-AI cognitive substrate gamma analysis. Fields:
docs/REPRODUCIBILITY.md:150:| `gamma_all.gamma` | float | Theil-Sen gamma across all sessions |
docs/REPRODUCIBILITY.md:151:| `gamma_all.r2` | float | R² of log-log fit |
docs/REPRODUCIBILITY.md:152:| `gamma_all.ci_low/ci_high` | float | Bootstrap 95% CI |
docs/REPRODUCIBILITY.md:153:| `gamma_all.verdict` | str | `METASTABLE` / `LOW_R2` / `INSUFFICIENT_DATA` |
docs/REPRODUCIBILITY.md:154:| `gamma_productive.gamma` | float | Gamma for productive sessions only |
docs/REPRODUCIBILITY.md:156:**Note:** `verdict = LOW_R2` means the log-log fit R² < 0.3. The gamma value
docs/REPRODUCIBILITY.md:168:| `gamma.per_domain` | dict | Per-domain gamma with CI and R² |
docs/REPRODUCIBILITY.md:169:| `gamma.mean` | float | Cross-domain mean gamma |
docs/REPRODUCIBILITY.md:195:cross-coherence scores, and the universal scaling p-value from a multi-domain
docs/REPRODUCIBILITY.md:199:### `xform_proof_bundle.json` vs `xform_combined_gamma_report.json`
docs/REPRODUCIBILITY.md:202:- `xform_combined_gamma_report.json` — combined gamma analysis across multiple
docs/REPRODUCIBILITY.md:212:| Substrate | Expected gamma | Tolerance | Tier | Notes |
docs/REPRODUCIBILITY.md:216:| eeg_resting | 1.255 | ±0.10 | T1 | Welch PSD slope — gamma above tight window; CI=[1.032,1.452] (see note) |
docs/REPRODUCIBILITY.md:220:| kuramoto | 0.963 | ±0.02 | T3 | 128-oscillator Kc |
docs/REPRODUCIBILITY.md:222:| serotonergic_kuramoto | 1.068 | ±0.20 | T5 | Wide CI expected |
docs/REPRODUCIBILITY.md:231:**Note on `eeg_resting` (gamma = 1.255):** This substrate's point estimate is
docs/REPRODUCIBILITY.md:232:above the [0.85, 1.15] tight metastable window. The bootstrap CI [1.032, 1.452]
docs/REPRODUCIBILITY.md:235:empirical data with a valid permutation p-value (p = 0.048). The elevated gamma
docs/REPRODUCIBILITY.md:237:`evidence/gamma_ledger.json::eeg_resting` for full bootstrap metadata. The
```

## docs/REVIEWER_GUIDE.md

_matches: 67_

```
docs/REVIEWER_GUIDE.md:1:# Reviewer Guide — NeoSynaptex γ-Criticality Claim
docs/REVIEWER_GUIDE.md:20:# 1. Reproduce the γ table for all substrates
docs/REVIEWER_GUIDE.md:44:> **γ ≈ 1 across 10 independent substrates, 4 of which are wild
docs/REVIEWER_GUIDE.md:45:> empirical witnesses. One substrate (cfp_diy) reports γ ≈ 1.83,
docs/REVIEWER_GUIDE.md:50:[`evidence/gamma_provenance.md`](../evidence/gamma_provenance.md).
docs/REVIEWER_GUIDE.md:56:### Per-substrate γ values
docs/REVIEWER_GUIDE.md:61:| Substrate | γ | 95 % CI | Adapter | Tests | Ledger key |
docs/REVIEWER_GUIDE.md:69:| kuramoto_market (T3) | 0.963 | [0.930, 1.000] | [`substrates/kuramoto/adapter.py`](../substrates/kuramoto/adapter.py) | [`tests/test_kuramoto_real.py`](../tests/test_kuramoto_real.py) | `kuramoto` |
docs/REVIEWER_GUIDE.md:71:| serotonergic_kuramoto (T5) | 1.068 | [0.145, 1.506] | [`substrates/serotonergic_kuramoto/adapter.py`](../substrates/serotonergic_kuramoto/adapter.py) | [`tests/test_serotonergic_kuramoto.py`](../tests/test_serotonergic_kuramoto.py), [`tests/test_calibration_robustness.py`](../tests/test_calibration_robustness.py) | `serotonergic_kuramoto` |
docs/REVIEWER_GUIDE.md:74:The authoritative γ numbers live in
docs/REVIEWER_GUIDE.md:75:[`evidence/gamma_ledger.json`](../evidence/gamma_ledger.json). Every
docs/REVIEWER_GUIDE.md:80:### γ core computation
docs/REVIEWER_GUIDE.md:82:All γ values flow through a single function:
docs/REVIEWER_GUIDE.md:84:- [`core/gamma.py::compute_gamma`](../core/gamma.py) — Theil-Sen
docs/REVIEWER_GUIDE.md:87:  per-unit γ population summary with permutation p-value.
docs/REVIEWER_GUIDE.md:94:  `SUBSTRATE_GAMMA` registry pulled from the ledger (no hard-coded γ).
docs/REVIEWER_GUIDE.md:95:- [`core/gamma_registry.py`](../core/gamma_registry.py) — single
docs/REVIEWER_GUIDE.md:97:  *γ DERIVED ONLY — never assigned, never input parameter*.
docs/REVIEWER_GUIDE.md:100:- [`evidence/gamma_ledger.json`](../evidence/gamma_ledger.json)
docs/REVIEWER_GUIDE.md:101:- [`evidence/gamma_provenance.md`](../evidence/gamma_provenance.md) —
docs/REVIEWER_GUIDE.md:108:  expected γ) was committed before the measurement was written into
docs/REVIEWER_GUIDE.md:122:  — 6 gates: gamma_provenance, evidence_hash, split_brain,
docs/REVIEWER_GUIDE.md:123:  math_core_tested, invariant_gamma, testpath_hermetic.
docs/REVIEWER_GUIDE.md:137:Eight tests prove that γ *breaks* when it should:
docs/REVIEWER_GUIDE.md:139:1. `test_gamma_breaks_under_shuffled_topo` — clean signal, shuffle the
docs/REVIEWER_GUIDE.md:140:   topo array → γ leaves [0.7, 1.3] or verdict becomes LOW_R2.
docs/REVIEWER_GUIDE.md:141:2. `test_gamma_breaks_under_random_cost` — uniform-log cost noise.
docs/REVIEWER_GUIDE.md:142:3. `test_brownian_1_over_f_squared_reports_gamma_near_2` — Brownian
docs/REVIEWER_GUIDE.md:143:   PSD returns γ ≈ 2.3 (observed), not 1.
docs/REVIEWER_GUIDE.md:146:   kuramoto. All three see their γ collapse when the topo array is
docs/REVIEWER_GUIDE.md:148:8. `test_exponential_decay_not_metastable` — exponential decay → γ
docs/REVIEWER_GUIDE.md:153:- **Bit-exact:** every γ value is reproducible from seed=42 on the
docs/REVIEWER_GUIDE.md:155:  - `tests/test_calibration_robustness.py` — serotonergic_kuramoto
docs/REVIEWER_GUIDE.md:172:| γ ≈ 1 across all substrates | `python reproduce.py` |
docs/REVIEWER_GUIDE.md:173:| γ is bit-exact reproducible | `pytest tests/test_bootstrap_helpers.py tests/test_calibration_robustness.py tests/test_eeg_resting_substrate.py tests/test_hrv_fantasia_substrate.py` |
docs/REVIEWER_GUIDE.md:175:| T1 EEG Welch γ = 1.26 on real PhysioNet data | `python -c "from substrates.eeg_resting.adapter import run_gamma_analysis; run_gamma_analysis()"` |
docs/REVIEWER_GUIDE.md:176:| T1 HRV DFA γ = 1.00 on real Fantasia data | `python -c "from substrates.hrv_fantasia.adapter import run_gamma_analysis; run_gamma_analysis()"` |
docs/REVIEWER_GUIDE.md:187:  serotonergic_kuramoto substrate literally tests. The Kuramoto
docs/REVIEWER_GUIDE.md:192:  count. See `evidence/gamma_provenance.md` for why.
docs/REVIEWER_GUIDE.md:207:| 1 | **Gamma scaling** | `log K = -gamma * log C + log A` (Theil-Sen) | Bootstrap n=500, R2 >= 0.3 | `gamma_per_domain`, `gamma_mean` |
docs/REVIEWER_GUIDE.md:208:| 2 | **Bootstrap CI** | Percentile interval [2.5, 97.5] of 500 Theil-Sen fits on resampled pairs | Confidence level 95% | `gamma_ci_per_domain` |
docs/REVIEWER_GUIDE.md:209:| 3 | **Permutation p** | `p = count(|slope_perm| >= |slope_obs|) / 500` | 500 permutations of cost array | `universal_scaling_p` |
docs/REVIEWER_GUIDE.md:212:| 6 | **Cross-coherence** | `coherence = 1 - std(gamma) / mean(gamma)` clamped to [0,1] | Coherent if > 0.85 | `cross_coherence` |
docs/REVIEWER_GUIDE.md:214:| 8 | **Anomaly isolation** | `score[d] = |gamma[d] - mean(gamma \ {d})|` (leave-one-out) | Outlier if > 0.3 | `anomaly_score` |
docs/REVIEWER_GUIDE.md:215:| 9 | **Phase portrait** | `area = ConvexHull((gamma, rho) trajectory).volume; recurrence = frac(|point - centroid| < 0.05)` | Requires >= 3 points | `portrait` |
docs/REVIEWER_GUIDE.md:217:| 11 | **Modulation signal** | `mod[d] = clip(1.0 - gamma[d], -0.05, +0.05)` | Bounded diagnostic, not control | `modulation` |
docs/REVIEWER_GUIDE.md:218:| 12 | **Cross-domain Jacobian** | `J[i][j] = d(gamma_i)/d(state_mean_j)` (least squares after 64 ticks) | Condition gate < 1e6 | `cross_jacobian` |
docs/REVIEWER_GUIDE.md:219:| 13 | **Gamma EMA** | `ema[t] = 0.3 * gamma[t] + 0.7 * ema[t-1]` | alpha=0.3 | `gamma_ema_per_domain` |
docs/REVIEWER_GUIDE.md:220:| 14 | **dGamma/dt** | Theil-Sen slope on `gamma_trace[-window:]` | Convergence diagnostic | `dgamma_dt` |
docs/REVIEWER_GUIDE.md:226:### "Why is gamma = 1.0 and not a tuned parameter?"
docs/REVIEWER_GUIDE.md:230:gamma = 1.0; it is that we measured it and found it close to 1.0 across
docs/REVIEWER_GUIDE.md:231:independent substrates. The invariant `"gamma derived only, never assigned"`
docs/REVIEWER_GUIDE.md:232:is enforced in `core/gamma_registry.py` and verified by `tests/test_gamma_registry.py`.
docs/REVIEWER_GUIDE.md:234:If gamma were a tuned parameter, you would find it hard-coded somewhere in
docs/REVIEWER_GUIDE.md:235:`neosynaptex.py` or the adapter files. Search for `gamma = 1` in the source —
docs/REVIEWER_GUIDE.md:262:from core.gamma import compute_gamma
docs/REVIEWER_GUIDE.md:266:gamma, r2, ci_lo, ci_hi, _ = compute_gamma(topos, costs, seed=42, n_bootstrap=500)
docs/REVIEWER_GUIDE.md:267:print(f"gamma={gamma:.4f}  CI=[{ci_lo:.4f}, {ci_hi:.4f}]  R2={r2:.4f}")
docs/REVIEWER_GUIDE.md:273:1. `gamma_mean` in [0.85, 1.15] (gamma within 15% of unity)
docs/REVIEWER_GUIDE.md:276:The name reflects the dynamical systems concept of metastability: the system
docs/REVIEWER_GUIDE.md:282:### "What is cfp_diy and why is gamma = 1.83?"
docs/REVIEWER_GUIDE.md:290:for the gamma = 1.0 claim. It is documented in `evidence/gamma_ledger.json`
docs/REVIEWER_GUIDE.md:296:Pre-registration means that the adapter code (and hence the expected gamma)
docs/REVIEWER_GUIDE.md:297:was committed to the repository *before* the gamma value was written into the
docs/REVIEWER_GUIDE.md:305:git log --oneline evidence/gamma_ledger.json  # shows when ledger entry was added
docs/REVIEWER_GUIDE.md:323:- No hard-coded gamma values found in source code.
docs/REVIEWER_GUIDE.md:335:interpreting all output files (`xform_gamma_report.json`,
```

## docs/SEMANTIC_DRIFT_GATE.md

_matches: 4_

```
docs/SEMANTIC_DRIFT_GATE.md:35:   - **Tier** 0–8 (descriptive → universal law) from lexical markers.
docs/SEMANTIC_DRIFT_GATE.md:36:   - **Scope** 0–4 (local → universal).
docs/SEMANTIC_DRIFT_GATE.md:74:- `universal` / `law` language from local or exploratory evidence.
docs/SEMANTIC_DRIFT_GATE.md:84:which would be every PR until the HRV / γ-program corpus is
```

## docs/SUBSTRATE_MEASUREMENT_TABLE.yaml

_matches: 33_

```
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:1:# Substrate measurement table — canonical K/C/γ definitions per substrate.
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:2:# Canonical authority: CNS-AI Validation Protocol v1 §Step 2+4, γ-program Phase I §Step 2.
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:4:#   - docs/CLAIM_BOUNDARY.md §4 (scope qualifiers that every γ-claim must cite)
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:7:#   - evidence/gamma_ledger.json
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:40:    public_bundle: "evidence/gamma_ledger.json entry zebrafish_wt; raw data cite Out_WT_default_1.mat"
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:41:    current_gamma: 1.055
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:59:    public_bundle: "evidence/gamma_ledger.json entry gray_scott; config cite data/gray_scott/params.json"
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:60:    current_gamma: 0.979
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:68:  - id: kuramoto_market
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:72:    signal: "128-oscillator Kuramoto simulation with volatility driver; vol-to-1/|ret| mapping"
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:78:    public_bundle: "evidence/gamma_ledger.json entry kuramoto"
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:79:    current_gamma: 0.963
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:85:    notes: "This is Kuramoto-as-market-proxy (NOT classical oscillator network). Proxy caveat MUST appear in every manuscript. See evidence/levin_bridge/horizon_knobs.md §2."
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:97:    public_bundle: "evidence/gamma_ledger.json entry bnsyn"
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:98:    current_gamma: 0.946
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:104:    notes: "Low r² (0.28) indicates high unexplained variance. Method_tier T3 but r² gate is borderline. Exception framework per γ-program Phase V §Step 22 applies."
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:116:    public_bundle: "PhysioNet EEGBCI — publicly downloadable; evidence/gamma_ledger.json entry eeg_physionet"
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:117:    current_gamma: 1.068
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:137:    current_gamma: 1.255
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:145:    notes: "γ>1.0 with r²=0.34; verdict WARNING flags high unexplained variance. Independent cross-validation of eeg_physionet; not a separate datum for cross-substrate count."
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:147:  - id: serotonergic_kuramoto
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:149:    K_definition: "topological coherence — Kuramoto r in cross-concentration sweep"
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:151:    signal: "5-HT2A modulated Kuramoto, N=64, mean-field, 4 phase ICs"
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:157:    public_bundle: "substrates/serotonergic_kuramoto/adapter.py (deterministic)"
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:158:    current_gamma: 1.0677
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:167:    notes: "Wide CI reflects finite-N folding near Kuramoto critical point. p=1.0 means NO separability from null — this is an honest METASTABLE call, not evidential support. Treat as orientation only."
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:180:    current_gamma: 0.885
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:200:    current_gamma: 1.0032
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:228:    notes: "Not yet measured in evidence/gamma_ledger.json. Acquisition trivial via https://fred.stlouisfed.org/graph/fredgraph.csv?id=INDPRO (no API key). Pre-registered in PREREG_TEMPLATE_GAMMA.md workflow."
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:288:    measurement_method: "historical: xform_full_archive_gamma_report.json; NOW INVALID"
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:294:    historical_gamma: 1.059
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:308:# The following are named in repo context but are NOT current γ-claim
docs/SUBSTRATE_MEASUREMENT_TABLE.yaml:312:#   - mlsdm: machine-learning substrate divergence module, not γ substrate
```

## docs/SYSTEM_PROTOCOL.md

_matches: 6_

```
docs/SYSTEM_PROTOCOL.md:100:> - `CANONICAL_POSITION.md` locks the claim level for γ.
docs/SYSTEM_PROTOCOL.md:101:> - `docs/ADVERSARIAL_CONTROLS.md` defines what makes a γ claim
docs/SYSTEM_PROTOCOL.md:277:Terms like *fractal*, *recursive*, *scale-rich*, *self-reflective*, *critical*, *metastable*, or *integrative* must not be used decoratively.
docs/SYSTEM_PROTOCOL.md:307:- `gamma`
docs/SYSTEM_PROTOCOL.md:318:No gamma-related or regime-related claim is admissible without control logic.
docs/SYSTEM_PROTOCOL.md:343:- "establishes universal law"
```

## docs/adr/ADR-001-single-file-engine.md

_matches: 2_

```
docs/adr/ADR-001-single-file-engine.md:14:The codebase already has a `core/` package for reusable math (gamma
docs/adr/ADR-001-single-file-engine.md:28:Jacobian, gamma, Granger) are private functions or classes within the same
```

## docs/adr/ADR-002-agpl-license.md

_matches: 1_

```
docs/adr/ADR-002-agpl-license.md:34:- Protects the scientific record: if someone modifies the gamma computation
```

## docs/adr/ADR-003-theil-sen-estimator.md

_matches: 9_

```
docs/adr/ADR-003-theil-sen-estimator.md:1:# ADR-003 — Theil-Sen estimator for gamma regression
docs/adr/ADR-003-theil-sen-estimator.md:9:The gamma-scaling exponent is estimated from (log topo, log cost) point pairs
docs/adr/ADR-003-theil-sen-estimator.md:13:log(K) = -gamma * log(C) + log(A)
docs/adr/ADR-003-theil-sen-estimator.md:20:3. Consistent with the canonical `core/gamma.py` computation used in the
docs/adr/ADR-003-theil-sen-estimator.md:27:Use **Theil-Sen slope estimator** (`scipy.stats.theilslopes`) for the gamma
docs/adr/ADR-003-theil-sen-estimator.md:28:regression, implemented in `core/gamma.py::compute_gamma` and mirrored in
docs/adr/ADR-003-theil-sen-estimator.md:69:| OLS (scipy.stats.linregress) | Breakdown point = 0; single spike in topo or cost can produce |gamma| >> 1 |
docs/adr/ADR-003-theil-sen-estimator.md:79:- `core/gamma.py::compute_gamma` — canonical implementation
docs/adr/ADR-003-theil-sen-estimator.md:81:- `evidence/gamma_ledger.json` — derived values
```

## docs/adr/README.md

_matches: 1_

```
docs/adr/README.md:18:| [ADR-003](ADR-003-theil-sen-estimator.md) | Theil-Sen estimator for gamma | Accepted |
```

## docs/adr/kuramoto/0001-fractal-indicator-composition-architecture.md

_matches: 2_

```
docs/adr/kuramoto/0001-fractal-indicator-composition-architecture.md:107:   - Identify candidate indicators (Kuramoto, Ricci, entropy measures)
docs/adr/kuramoto/0001-fractal-indicator-composition-architecture.md:145:- Migrate Kuramoto and Ricci indicators
```

## docs/bibliography/AGENTS_BIBLIOGRAPHY.md

_matches: 15_

```
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:34:| **Kuramoto coupling** | `dnca/coupling/` | Kuramoto 1984; Acebrón+ 2005 | F, A |
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:35:| **Gamma probe (TDA)** | `dnca/gamma_probe/` | Edelsbrunner+ 2002; Carlsson 2009; McGuirl+ 2020 | F, A |
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:49:**[F1]** Kuramoto Y. (1984). *Chemical Oscillations, Waves, and Turbulence*. Springer. DOI: [10.1007/978-3-642-69689-3](https://doi.org/10.1007/978-3-642-69689-3)
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:68:Persistent homology — TDA-based gamma probe.
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:92:**[A7]** Rabinovich M.I., Huerta R., Varona P., Afraimovich V.S. (2008). Transient cognitive dynamics, metastability, and decision making. *PLoS Comput. Biol.*, 4(5), e1000072. DOI: [10.1371/journal.pcbi.1000072](https://doi.org/10.1371/journal.pcbi.1000072)
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:95:**[A8]** Acebrón J.A., Bonilla L.L., Pérez Vicente C.J., Ritort F., Spigler R. (2005). The Kuramoto model: A simple paradigm for synchronization phenomena. *Rev. Mod. Phys.*, 77(1), 137--185. DOI: [10.1103/RevModPhys.77.137](https://doi.org/10.1103/RevModPhys.77.137)
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:96:Kuramoto review — order parameter r(t) in DNCA coherence.
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:111:TDA survey — gamma probe methodology.
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:122:**[A17]** Cardin J.A. et al. (2009). Driving fast-spiking cells induces gamma rhythm and controls sensory responses. *Nature*, 459(7247), 663--667. DOI: [10.1038/nature08002](https://doi.org/10.1038/nature08002)
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:123:PV+ interneurons generate gamma via PING — cited in examples.
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:125:**[A18]** Buzsáki G., Wang X.-J. (2012). Mechanisms of gamma oscillations. *Annu. Rev. Neurosci.*, 35, 203--225. DOI: [10.1146/annurev-neuro-062111-150444](https://doi.org/10.1146/annurev-neuro-062111-150444)
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:128:**[A19]** Tognoli E., Kelso J.A.S. (2014). The metastable brain. *Neuron*, 81(1), 35--48. DOI: [10.1016/j.neuron.2013.12.022](https://doi.org/10.1016/j.neuron.2013.12.022)
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:132:Criticality validation — gamma probe.
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:135:γ_WT = +1.043 — external validation for γ_DNCA ~ 1.0.
docs/bibliography/AGENTS_BIBLIOGRAPHY.md:168:| Kuramoto 1984 | **x** | **x** | | **x** | | |
```

## docs/contracts/decision_bridge.md

_matches: 2_

```
docs/contracts/decision_bridge.md:12:(state-space, resonance map, FDT γ-estimator, online predictor, PI
docs/contracts/decision_bridge.md:55:* **I-DB-H1** — Health classifier is monotone under dominance. For any two signal sets `s'` and `s`, if `s'` is at least as good as `s` on every axis (diagnosis, regime, hallucination risk, stability, `|γ − 1|`), then `rank(health(s')) ≥ rank(health(s))`. Exhaustively enumerated over the discrete axes (≈ 262 144 pairs).
```

## docs/contracts/decision_bridge.yaml

_matches: 4_

```
docs/contracts/decision_bridge.yaml:109:      If gamma_fdt_available, gamma_fdt_estimate and
docs/contracts/decision_bridge.yaml:110:      gamma_fdt_uncertainty are both finite.
docs/contracts/decision_bridge.yaml:120:      - tests/test_decision_bridge_properties.py::TestSensorGateSanitizeIdempotenceProperty::test_gamma_sanitize_is_idempotent
docs/contracts/decision_bridge.yaml:129:      - tests/test_decision_bridge_health_monotonicity.py::TestHealthContinuousAxis::test_gamma_closer_to_one_never_demotes
```

## docs/cosmo-neural-hud.md

_matches: 2_

```
docs/cosmo-neural-hud.md:9:- **Layer detection** — knows which subsystem you're working in (bn_syn, hca1, mlsdm, mfn+, kuramoto, etc.)
docs/cosmo-neural-hud.md:52:| `kuramoto`          | `kuramoto` | light blue    |
```

## docs/operator/OPERATOR_GUIDE.md

_matches: 11_

```
docs/operator/OPERATOR_GUIDE.md:22:# 4. Reproduce the gamma table
docs/operator/OPERATOR_GUIDE.md:46:print(f"gamma_mean   : {state.gamma_mean:.4f}")
docs/operator/OPERATOR_GUIDE.md:55:gamma_mean   : 0.9xxx
docs/operator/OPERATOR_GUIDE.md:90:| `make demo` | Print gamma table for all substrates |
docs/operator/OPERATOR_GUIDE.md:103:| `gamma_mean` | [0.85, 1.15] | Check adapter topo/cost functions |
docs/operator/OPERATOR_GUIDE.md:107:| `universal_scaling_p` | > 0.05 | p < 0.05 = substrates diverging |
docs/operator/OPERATOR_GUIDE.md:120:Log entries include: tick number, per-domain gamma, spectral radius, phase
docs/operator/OPERATOR_GUIDE.md:157:### `gamma_mean = NaN` after many ticks
docs/operator/OPERATOR_GUIDE.md:181:- `gamma_provenance`: ledger entry missing or hash mismatch
docs/operator/OPERATOR_GUIDE.md:223:`reproduce.py` and exits 0 if all gamma values match the ledger.
docs/operator/OPERATOR_GUIDE.md:232:| `docker-reproduce.yml` | push (relevant files) | Docker image builds and gamma reproduces |
```

## docs/operator/cosmo_neural_hud.md

_matches: 1_

```
docs/operator/cosmo_neural_hud.md:17:- cwd subsystem layer (`root_integration`, `agents`, `bn_syn`, `hippocampal_ca1`, `mlsdm`, `mfn_plus`, `kuramoto`, `docs`, `manuscript`, `tools_scripts`)
```

## docs/protocols/ANALYSIS_SPLIT.md

_matches: 2_

```
docs/protocols/ANALYSIS_SPLIT.md:1:# Analysis split contract — cardiac γ-program
docs/protocols/ANALYSIS_SPLIT.md:65:| Move a subject between splits | no | forbidden without superseding the entire γ-run; see CLAIM_BOUNDARY §E-02 |
```

## docs/protocols/CNS_AI_PATH_CONTRACT.md

_matches: 5_

```
docs/protocols/CNS_AI_PATH_CONTRACT.md:10:## 1. What `derive_real_gamma.py` declared as canonical
docs/protocols/CNS_AI_PATH_CONTRACT.md:12:`substrates/cns_ai_loop/derive_real_gamma.py:16–17`:
docs/protocols/CNS_AI_PATH_CONTRACT.md:38:- Regenerating `xform_full_archive_gamma_report.json` — the original workspace is not preserved; the scan cannot be repeated.
docs/protocols/CNS_AI_PATH_CONTRACT.md:57:`substrates/cns_ai_loop/derive_real_gamma.py` is patched in the same PR that ships this document:
docs/protocols/CNS_AI_PATH_CONTRACT.md:80:**supersedes:** `derive_real_gamma.py` silent-skip behaviour
```

## docs/protocols/levin_bridge_protocol.md

_matches: 25_

```
docs/protocols/levin_bridge_protocol.md:9:Systems with a **wider effective integration horizon** and **stronger distributed coordination** will, when still productive and non-collapsed, exhibit **γ closer to 1.0** more often than matched systems with narrower coordination horizons.
docs/protocols/levin_bridge_protocol.md:15:Do **not** claim that γ ≈ 1 defines intelligence, proves cognition, or validates universal agency. At this stage γ is only a **candidate cross-substrate regime marker**. Any manuscript, README, or release note that overstates this MUST be rejected at review.
docs/protocols/levin_bridge_protocol.md:27:| **γ** | Metastability signature | Existing Neosynaptex estimator from organisational cost vs topological/functional complexity (`core/gamma.py`, Theil–Sen; see `docs/science/MECHANISMS.md §1`). |
docs/protocols/levin_bridge_protocol.md:35:- **Kuramoto** / market-synchronisation substrate — in scope, operationalised as the **TradePulse Δr proxy** (not a classical oscillator; see `evidence/levin_bridge/horizon_knobs.md §2` — this caveat MUST be restated in every manuscript citing Kuramoto-substrate results).
docs/protocols/levin_bridge_protocol.md:61:- **Kuramoto** — same event-detection or regime-classification target.
docs/protocols/levin_bridge_protocol.md:63:Without this, γ may track task change instead of integration scale.
docs/protocols/levin_bridge_protocol.md:69:| **H1** | Higher H and stronger C predict γ moving toward 1.0 while P remains viable. |
docs/protocols/levin_bridge_protocol.md:71:| **H2** | Expanded H increases complexity but degrades function, producing drift or collapse rather than γ ≈ 1 stabilisation. |
docs/protocols/levin_bridge_protocol.md:72:| **Kill** | If γ approaches 1.0 equally often in shuffled, scrambled, or non-productive controls, the bridge fails. |
docs/protocols/levin_bridge_protocol.md:93:- **Kuramoto** — synchronisation influence span, lagged coordination radius.
docs/protocols/levin_bridge_protocol.md:104:- **Required, cross-substrate comparable:** `H_raw`, `H_rank`, `C`, `gamma`,
docs/protocols/levin_bridge_protocol.md:105:  `gamma_ci_lo`, `gamma_ci_hi`.
docs/protocols/levin_bridge_protocol.md:113:- Monotonic relation between H and |γ − 1|.
docs/protocols/levin_bridge_protocol.md:114:- Partial relation between H and γ controlling for P **where `P_status == "defined"`**.
docs/protocols/levin_bridge_protocol.md:115:- Relation between C and γ.
docs/protocols/levin_bridge_protocol.md:116:- Interaction term: `H × C → γ`.
docs/protocols/levin_bridge_protocol.md:134:- Productive regimes cluster nearer γ ≈ 1 than both fragmented **and** collapsed controls.
docs/protocols/levin_bridge_protocol.md:141:- γ ≈ 1 tracks scale inflation but not productivity.
docs/protocols/levin_bridge_protocol.md:142:- γ ≈ 1 occurs equally in pathological overcoupling and successful coordination.
docs/protocols/levin_bridge_protocol.md:144:The "γ ≈ 1 tracks scale inflation but not productivity" criterion can only
docs/protocols/levin_bridge_protocol.md:153:> Broader integration horizons and stronger distributed coordination are associated with γ values closer to 1.0 across multiple productive substrates, making γ a stronger candidate marker of metastable regime organisation.
docs/protocols/levin_bridge_protocol.md:157:> Levin-inspired scale and coordination concepts remain biologically meaningful, but they do not currently support γ ≈ 1 as a robust cross-substrate marker in Neosynaptex.
docs/protocols/levin_bridge_protocol.md:169:5. `notebooks/levin_bridge/gamma_vs_horizon_analysis.ipynb` — generated at run time; not required at scaffold commit.
docs/protocols/levin_bridge_protocol.md:176:> Levin's work provides a biologically grounded framework for distributed agency and scale-dependent goal-directedness; in Neosynaptex, we operationalise this not as a conclusion about machine intelligence, but as a falsifiable cross-substrate hypothesis linking integration horizon and coordinated dynamics to metastable regime signatures.
docs/protocols/levin_bridge_protocol.md:182:Translate cognitive light cone → integration horizon, manipulate it, measure γ, attack the bridge with controls, and keep only what survives.
```

## docs/protocols/mfn_plus_productivity_prereg.md

_matches: 3_

```
docs/protocols/mfn_plus_productivity_prereg.md:68:### Option γ — cross-seed reproducibility as 1 / Var(summary)
docs/protocols/mfn_plus_productivity_prereg.md:84:- No H / C / γ derivation.
docs/protocols/mfn_plus_productivity_prereg.md:90:A future substrate-owner PR must pick exactly one of Options α / β (Option γ is rejected as conceptually miscategorised) and commit:
```

## docs/protocols/telemetry_spine_spec.md

_matches: 6_

```
docs/protocols/telemetry_spine_spec.md:18:      abstraction in substrates/kuramoto/core/telemetry.py and the
docs/protocols/telemetry_spine_spec.md:19:      optional-OTel tracing layer in substrates/kuramoto/core/tracing/
docs/protocols/telemetry_spine_spec.md:72:- `substrates/kuramoto/core/telemetry.py` — vendor-agnostic
docs/protocols/telemetry_spine_spec.md:75:- `substrates/kuramoto/core/tracing/distributed.py` — optional-OTel
docs/protocols/telemetry_spine_spec.md:157:  `substrates/kuramoto/core/tracing/distributed.py`.
docs/protocols/telemetry_spine_spec.md:252:- Per-substrate scientific metrics (e.g. γ, H, C) — owned by the
```

## docs/science/MECHANISMS.md

_matches: 31_

```
docs/science/MECHANISMS.md:18:| 1 | Gamma scaling | `gamma_per_domain`, `gamma_mean` | [1](#1-gamma-scaling) |
docs/science/MECHANISMS.md:27:| 10 | Universal scaling | `universal_scaling_p` | [10](#10-universal-scaling-test) |
docs/science/MECHANISMS.md:36:log(K_t) = -gamma * log(C_t) + log(A)
docs/science/MECHANISMS.md:45:is K ~ C^(-gamma).
docs/science/MECHANISMS.md:54:**EMA:** Exponential moving average of gamma with alpha = 0.3, stored in
docs/science/MECHANISMS.md:55:`gamma_ema_per_domain`. Used for drift detection.
docs/science/MECHANISMS.md:57:**Minimum pairs:** 5 valid (log C, log K) pairs required before gamma is
docs/science/MECHANISMS.md:60:**Code:** `neosynaptex.py::_per_domain_gamma`, `core/gamma.py::compute_gamma`
docs/science/MECHANISMS.md:97:`J[i][j] = d(gamma_i)/d(state_mean_j)` is estimated via least-squares on
docs/science/MECHANISMS.md:98:the trace of (state means, gammas). Returned in `cross_jacobian`.
docs/science/MECHANISMS.md:107:gamma distribution. Phase changes require `_HYSTERESIS_COUNT = 3` consecutive
docs/science/MECHANISMS.md:115:elif |gamma_mean - 1.0| < 0.15 and 0.80 <= rho <= 1.25:
docs/science/MECHANISMS.md:118:elif gamma_mean > 1.15:         phase = DIVERGING
docs/science/MECHANISMS.md:119:elif gamma_mean < 0.85:         phase = COLLAPSING
docs/science/MECHANISMS.md:166:cross-domain mean gamma.
docs/science/MECHANISMS.md:171:anomaly_score[d] = |gamma[d] - gamma_mean_excluding_d|
docs/science/MECHANISMS.md:174:where `gamma_mean_excluding_d` is the mean gamma of all other domains.
docs/science/MECHANISMS.md:186:(gamma, spectral_radius) space over the observation window.
docs/science/MECHANISMS.md:192:| `area` | `ConvexHull(trajectory).volume` | Size of explored region in (gamma, rho) space |
docs/science/MECHANISMS.md:194:| `distance_to_ideal` | `sqrt((gamma_mean - 1)^2 + (rho_median - 1)^2)` | Euclidean distance from (1, 1) ideal |
docs/science/MECHANISMS.md:196:Requires at least 3 finite (gamma, rho) pairs. Returns NaN fields if
docs/science/MECHANISMS.md:228:nudge each domain adapter back toward the metastable regime.
docs/science/MECHANISMS.md:233:modulation[d] = clip(1.0 - gamma[d], -0.05, +0.05)
docs/science/MECHANISMS.md:265:The universal scaling test checks whether all registered domains share the
docs/science/MECHANISMS.md:266:same gamma exponent (universal scaling hypothesis).
docs/science/MECHANISMS.md:270:Each domain's bootstrap gamma distribution (n = 500 samples) is compared to
docs/science/MECHANISMS.md:273:1. Concatenate all bootstrap gamma samples from all domains.
docs/science/MECHANISMS.md:279:gamma values — the universal scaling hypothesis is rejected.
docs/science/MECHANISMS.md:280:A high p-value (p > 0.05) is consistent with universal scaling (all domains
docs/science/MECHANISMS.md:283:**Output:** `universal_scaling_p` in `NeosynaptexState`. Returned as NaN if
docs/science/MECHANISMS.md:286:**Code:** `neosynaptex.py::_universal_scaling_test`
```

## docs/science/agents/evidence_log.md

_matches: 58_

```
docs/science/agents/evidence_log.md:1:# Evidence Log — γ-scaling Cross-Substrate Measurements
docs/science/agents/evidence_log.md:5:| 2026-03-29 | zebrafish | γ_WT | +1.043 | [0.933, 1.380] | — | PRIMARY |
docs/science/agents/evidence_log.md:6:| 2026-03-29 | DNCA | γ_NMO | +2.072 | [1.341, 2.849] | 949 | CONFIRMED |
docs/science/agents/evidence_log.md:7:| 2026-03-29 | DNCA | γ_PE | +6.975 | [6.503, 7.407] | — | CONFIRMED |
docs/science/agents/evidence_log.md:8:| 2026-03-29 | DNCA | γ_random | +0.068 | [-0.080, 0.210] | — | CONTROL_PASS |
docs/science/agents/evidence_log.md:9:| 2026-03-30 | MFN⁺ | γ_GrayScott (activator) | +0.865 | [0.649, 1.250] | 100 | CONFIRMED |
docs/science/agents/evidence_log.md:10:| 2026-03-30 | MFN⁺ | γ_GrayScott (inhibitor) | +0.655 | [0.431, 0.878] | 100 | CONFIRMED |
docs/science/agents/evidence_log.md:11:| 2026-03-30 | MFN⁺ | γ_control (shuffled) | +0.035 | — | — | CONTROL_PASS |
docs/science/agents/evidence_log.md:12:| 2026-03-30 | mvstack | γ_trending | +1.081 | [0.869, 1.290] | 200 | CONFIRMED |
docs/science/agents/evidence_log.md:13:| 2026-03-30 | mvstack | γ_chaotic | +1.007 | [0.797, 1.225] | 200 | CONFIRMED |
docs/science/agents/evidence_log.md:14:| 2026-03-30 | mvstack | γ_control (shuffled trending) | +0.145 | — | — | CONTROL_PASS |
docs/science/agents/evidence_log.md:15:| 2026-03-30 | mvstack | γ_control (shuffled chaotic) | -0.083 | — | — | CONTROL_PASS |
docs/science/agents/evidence_log.md:16:| 2026-03-30 | mvstack | Δγ(trending - chaotic) | +0.074 | — | — | NOTE |
docs/science/agents/evidence_log.md:19:| 2026-03-30 | DNCA (full) | γ_NMO (state_dim=64, 1000 steps) | +2.185 | [1.743, 2.789] | 898 | CONFIRMED |
docs/science/agents/evidence_log.md:20:| 2026-03-30 | DNCA (full) | γ_PE (state_dim=64, 1000 steps) | +0.476 | [0.210, 0.615] | 899 | CONFIRMED |
docs/science/agents/evidence_log.md:21:| 2026-03-30 | DNCA (full) | γ_random (state_dim=64, 1000 steps) | +0.045 | [-0.082, 0.148] | — | CONTROL_PASS |
docs/science/agents/evidence_log.md:23:| 2026-03-30 | DNCA sweep | γ_min at competition=0.78 | +0.756 | — | 449 | CONVERGES TO BIO |
docs/science/agents/evidence_log.md:24:| 2026-03-30 | DNCA sweep | γ at competition=0.67 | +0.903 | — | 449 | CONSISTENT WITH γ_WT |
docs/science/agents/evidence_log.md:25:| 2026-03-30 | DNCA sweep | γ at competition=0.00 (no comp) | +4.547 | [2.008, 4.316] | 447 | INFLATED |
docs/science/agents/evidence_log.md:27:| 2026-03-30 | SpatialDNCA | γ_NMO (8×8 grid) | +3.870 | [2.295, 4.318] | 447 | ELEVATED |
docs/science/agents/evidence_log.md:28:| 2026-03-30 | SpatialDNCA | γ_PE (8×8 grid) | +0.680 | [0.567, 0.908] | — | BIO RANGE |
docs/science/agents/evidence_log.md:29:| 2026-03-30 | all conditions | γ_PE mean (all conditions) | +0.757 | SD=0.128 | — | STABLE |
docs/science/agents/evidence_log.md:30:| 2026-03-30 | H1 test | Spatial locality effect | REJECTED | — | — | γ INCREASES |
docs/science/agents/evidence_log.md:32:| 2026-03-30 | H3 (emergent) | Metastability hypothesis | SUPPORTED | — | — | γ min at optimal comp |
docs/science/agents/evidence_log.md:34:## T1-T6: Why gamma ≈ 1.0? Seven Tests
docs/science/agents/evidence_log.md:40:| T3: Method falsification | 1D embedding biased (white noise γ=1.6); native 2D valid | 1/5 |
docs/science/agents/evidence_log.md:41:| T2: 2D Ising (T_c=2.269) | γ decreases monotonically with T (1.68→0.96); NOT peaked at T_c | 2/4 |
docs/science/agents/evidence_log.md:42:| T1: Correlation η vs γ | η ≈ 0.2 everywhere, uncorrelated with γ (r=0.11) | 1/3 |
docs/science/agents/evidence_log.md:43:| T4: Persistence dynamics | γ→1.0 when pe0/β0 variance moderate, corr ~0.87 | 1/3 |
docs/science/agents/evidence_log.md:45:| T6: Formula γ=νz/d | Closest match: 1.083 vs measured 1.329 (error 0.25) | partial |
docs/science/agents/evidence_log.md:48:- γ ≈ 1.0 is NOT a critical exponent (T1, T2)
docs/science/agents/evidence_log.md:49:- γ ≈ 1.0 is NOT a pipeline artifact on native 2D fields (controls ≈ 0)
docs/science/agents/evidence_log.md:50:- γ ≈ 1.0 IS the baseline for moderate topological variability (T4)
docs/science/agents/evidence_log.md:51:- γ works on multi-dimensional density fields, NOT low-D ODE trajectories (T5)
docs/science/agents/evidence_log.md:54:## Competition Sweep — γ as function of competition_strength
docs/science/agents/evidence_log.md:62:| competition | γ_NMO | R² | γ_ctrl |
docs/science/agents/evidence_log.md:75:Minimum: γ = 0.756 at competition = 0.778
docs/science/agents/evidence_log.md:76:Maximum: γ = 4.547 at competition = 0.000
docs/science/agents/evidence_log.md:78:All |γ_ctrl| < 0.06 — controls pass at every level
docs/science/agents/evidence_log.md:80:Key finding: At competition ≈ 0.75-0.78, DNCA γ enters the bio-morphogenetic range [0.756, 0.903].
docs/science/agents/evidence_log.md:81:This suggests γ ≈ 1.0 is the signature of METASTABLE competition, not weak or strong competition.
docs/science/agents/evidence_log.md:86:γ_SpatialDNCA(NMO) = +3.870, CI [+2.295, +4.318], R² = 0.204
docs/science/agents/evidence_log.md:87:γ_SpatialDNCA(PE) = +0.680, CI [+0.567, +0.908]
docs/science/agents/evidence_log.md:88:γ_control = -0.000
docs/science/agents/evidence_log.md:89:Verdict: Spatial locality INCREASES γ (not decreases). H1 rejected.
docs/science/agents/evidence_log.md:93:Mean γ_PE = 0.757 (SD = 0.128) across all competition levels and spatial variant.
docs/science/agents/evidence_log.md:99:γ_DNCA_full   = +2.185
docs/science/agents/evidence_log.md:103:γ_control     = +0.045
docs/science/agents/evidence_log.md:109:  γ_bio    = +1.043  [0.933, 1.380]  PRIMARY
docs/science/agents/evidence_log.md:110:  γ_MFN    = +0.865  [0.649, 1.250]  ORGANIZED
docs/science/agents/evidence_log.md:111:  γ_market = +1.081  [0.869, 1.290]  ORGANIZED
docs/science/agents/evidence_log.md:112:  γ_DNCA   = +2.185  [1.743, 2.789]  ORGANIZED (different scale)
docs/science/agents/evidence_log.md:113:  γ_ctrl   = +0.045  [-0.082, 0.148] RANDOM
docs/science/agents/evidence_log.md:119:- DNCA γ_NMO = +2.072 (state_dim=8, 200 steps) and +2.185 (state_dim=64, 1000 steps) — full run confirms elevated γ is not an artifact of reduced parameters.
docs/science/agents/evidence_log.md:121:- Control γ = +0.045 confirms signal is genuine (not pipeline artifact).
docs/science/agents/evidence_log.md:122:- MFN⁺ CI [0.649, 1.250] includes γ_WT = 1.043.
docs/science/agents/evidence_log.md:123:- mvstack γ is stable across market regimes (Δγ = 0.074), suggesting Kuramoto coupling topology itself carries the invariant.
docs/science/agents/evidence_log.md:124:- Three substrates unified: γ_bio = 1.043, γ_MFN = 0.865, γ_market = 1.081 → divergence = 0.216 → UNIFIED.
```

## docs/science/agents/gamma_scaling_manuscript.md

_matches: 56_

```
docs/science/agents/gamma_scaling_manuscript.md:1:# γ-Scaling Across Substrates: Topological Coherence in Organized Systems
docs/science/agents/gamma_scaling_manuscript.md:11:We measure the topological scaling exponent γ — the log-log slope between changes in H0 persistent entropy and H0 Betti number — across five independent substrates: zebrafish pigmentation (biological), Gray-Scott reaction-diffusion (morphogenetic), Kuramoto market synchronization (economic), 2D Ising lattice (physical), and a distributed neuromodulatory cognitive architecture (computational). Three diffusive-oscillatory substrates converge on γ ∈ [0.865, 1.081] with divergence 0.216. The competitive cognitive architecture yields γ ≈ 2.0 at default parameters but converges to the same range (γ = 0.86) when competition is tuned to its metastable operating point. Shuffled controls yield γ ≈ 0 across all substrates (mean 0.041, SD 0.094).
docs/science/agents/gamma_scaling_manuscript.md:13:Seven falsification tests establish that: (i) γ is not a standard critical exponent, (ii) γ is not an artifact of the measurement pipeline on native multi-dimensional fields, (iii) γ ≈ 1.0 occurs in systems with moderate topological variability regardless of substrate, and (iv) the measurement is restricted to multi-dimensional density fields (not low-dimensional ODE trajectories). The theoretical mechanism underlying the specific value γ ≈ 1.0 remains an open question. We report the empirical pattern without overclaiming its interpretation, following the precedent of Kuramoto (1975), whose synchronization model preceded its theoretical explanation by two decades.
docs/science/agents/gamma_scaling_manuscript.md:15:**Keywords:** topological data analysis, persistent homology, substrate-specific candidate marker, γ-scaling, metastability, self-organization
docs/science/agents/gamma_scaling_manuscript.md:21:The question of whether organized systems share measurable invariants across substrates has been posed since Bertalanffy's General System Theory (1968) but resisted quantification. A candidate invariant emerged from the topological analysis of biological pattern formation: McGuirl et al. (2020) measured γ = +1.043 on zebrafish pigmentation patterns using cubical persistent homology, demonstrating that γ distinguishes wild-type from mutant developmental programs.
docs/science/agents/gamma_scaling_manuscript.md:23:This work extends the γ measurement to four additional substrates that share no code, no parameters, and no architectural similarity with zebrafish pigmentation. We ask: does the same topological scaling exponent appear in systems organized by different mechanisms?
docs/science/agents/gamma_scaling_manuscript.md:25:The affirmative answer, qualified by seven falsification tests, suggests that γ-scaling captures a property of how organized systems evolve their topological structure over time — independent of the specific organizing mechanism.
docs/science/agents/gamma_scaling_manuscript.md:31:All γ measurements follow the same pipeline:
docs/science/agents/gamma_scaling_manuscript.md:38:6. Fit log(Δpe₀) vs log(Δβ₀) via Theil-Sen robust regression → slope = γ
docs/science/agents/gamma_scaling_manuscript.md:40:8. Control: independently shuffle pe₀ and β₀ series, recompute γ → should yield ≈ 0
docs/science/agents/gamma_scaling_manuscript.md:49:| mvstack market sync | This work | Kuramoto r(t) coherence | 1D → 2D embedded |
docs/science/agents/gamma_scaling_manuscript.md:54:All experiments: seed=42, deterministic. Code: `github.com/neuron7xLab/neuron7x-agents/scripts/`. Reproduction: `python scripts/gamma_phase_investigation.py`.
docs/science/agents/gamma_scaling_manuscript.md:60:### 3.1 Cross-substrate γ measurements
docs/science/agents/gamma_scaling_manuscript.md:62:| Substrate | System | γ | 95% CI | R² | γ_control |
docs/science/agents/gamma_scaling_manuscript.md:66:| Economic | mvstack Kuramoto (trending) | +1.081 | [+0.869, +1.290] | — | +0.145 |
docs/science/agents/gamma_scaling_manuscript.md:67:| Economic | mvstack Kuramoto (chaotic) | +1.007 | [+0.797, +1.225] | — | −0.083 |
docs/science/agents/gamma_scaling_manuscript.md:73:Three diffusive-oscillatory substrates (zebrafish, MFN⁺, market) converge on γ ∈ [0.865, 1.081], divergence = 0.216. The 2D Ising model at T_c yields γ = 1.329, slightly above this band. DNCA at default parameters yields γ = 2.185 but converges to γ = 0.861 when competition is tuned to its metastable operating point (competition = 0.75).
docs/science/agents/gamma_scaling_manuscript.md:75:All controls satisfy |γ_ctrl| < 0.15. Mean γ_control = +0.041.
docs/science/agents/gamma_scaling_manuscript.md:81:| Competition | γ | R² |
docs/science/agents/gamma_scaling_manuscript.md:94:Minimum: γ = 0.756 at competition = 0.778. All |γ_ctrl| < 0.06.
docs/science/agents/gamma_scaling_manuscript.md:98:The 2D Ising model (L=32) shows monotonically decreasing γ with temperature:
docs/science/agents/gamma_scaling_manuscript.md:100:| T | Phase | γ | Magnetization |
docs/science/agents/gamma_scaling_manuscript.md:109:γ is not peaked at T_c. It tracks the degree of spatial order.
docs/science/agents/gamma_scaling_manuscript.md:113:In DNCA, γ measured on the prediction error field (sensory − predicted) is remarkably stable across all competition levels: mean γ_PE = 0.757, SD = 0.128. This channel converges to the bio-morphogenetic range regardless of internal architecture.
docs/science/agents/gamma_scaling_manuscript.md:117:Destroying temporal structure (shuffling) reduces γ by 0.8–2.0 in every substrate tested, confirming γ measures temporal organization, not static signal properties.
docs/science/agents/gamma_scaling_manuscript.md:123:### 4.1 Is γ = 1.0 a pipeline artifact? (T3)
docs/science/agents/gamma_scaling_manuscript.md:125:Seven synthetic signal classes were tested via 1D→2D time-delay embedding. White noise yielded γ = 1.6, indicating the embedding approach is systematically biased. However, native multi-dimensional measurements (DNCA 6D activities, Ising 32×32 grids, MFN⁺ 128×128 fields) produce γ_ctrl ≈ 0, confirming the pipeline is valid on native fields.
docs/science/agents/gamma_scaling_manuscript.md:127:**Conclusion:** γ measurement is valid on native multi-dimensional density fields. The 1D→2D embedding approach requires methodological revision.
docs/science/agents/gamma_scaling_manuscript.md:129:### 4.2 Is γ a critical exponent? (T1, T2, T6)
docs/science/agents/gamma_scaling_manuscript.md:131:The temporal autocorrelation exponent η ≈ 0.2 across all DNCA competition levels, uncorrelated with γ (Pearson r = 0.11). The Ising model shows γ monotonically decreasing with T, not peaked at T_c. No formula from standard critical exponents (ν, z, d, η) reproduces the measured γ values (best candidate νz/d = 1.08 vs measured 1.33 for 2D Ising).
docs/science/agents/gamma_scaling_manuscript.md:133:**Conclusion:** γ is not a standard critical exponent in the renormalization group sense.
docs/science/agents/gamma_scaling_manuscript.md:135:### 4.3 Does γ work on arbitrary dynamical systems? (T5)
docs/science/agents/gamma_scaling_manuscript.md:137:Hodgkin-Huxley (γ ≈ 6.5), Van der Pol (γ ≈ 8.5), and Lorenz (γ ≈ 2.9) systems show no differentiation between critical and non-critical operating points. Low-dimensional ODE trajectories (2–4D) are outside the domain of the γ pipeline.
docs/science/agents/gamma_scaling_manuscript.md:139:**Conclusion:** γ is restricted to multi-dimensional density fields with sufficient topological complexity.
docs/science/agents/gamma_scaling_manuscript.md:141:### 4.4 What determines γ ≈ 1.0? (T4)
docs/science/agents/gamma_scaling_manuscript.md:143:Analysis of persistent homology dynamics reveals: γ approaches 1.0 when pe₀ and β₀ have moderate variance with moderate mutual correlation (~0.87). Extreme variance (competition=0.0: pe₀_std = 0.80, β₀_std = 18.1, corr = 0.997) produces γ >> 1. Low variance (competition=1.0: β₀_std = 5.6, corr = 0.74) produces γ ≈ 2.
docs/science/agents/gamma_scaling_manuscript.md:145:**Conclusion:** γ = 1.0 is the scaling regime where topological entropy and Betti number changes are proportional — each topological feature contributes a proportional amount of entropy.
docs/science/agents/gamma_scaling_manuscript.md:151:### 5.1 What γ is
docs/science/agents/gamma_scaling_manuscript.md:153:γ is a topological scaling exponent that quantifies how persistent entropy changes relative to persistent Betti number changes in time-evolving multi-dimensional density fields. It satisfies three conditions for a useful diagnostic:
docs/science/agents/gamma_scaling_manuscript.md:155:1. **Discrimination:** γ > 0 for all organized systems; γ ≈ 0 for shuffled controls
docs/science/agents/gamma_scaling_manuscript.md:156:2. **Convergence:** γ ∈ [0.86, 1.33] across five independent substrates operating in moderate-variability regimes
docs/science/agents/gamma_scaling_manuscript.md:157:3. **Sensitivity:** γ responds to parameter changes (competition sweep, temperature sweep) in a systematic, reproducible way
docs/science/agents/gamma_scaling_manuscript.md:159:### 5.2 What γ is not
docs/science/agents/gamma_scaling_manuscript.md:161:γ is not a universal constant. It is not a critical exponent. It is not applicable to low-dimensional trajectories. It does not distinguish criticality from near-criticality in the Ising model. Its specific value (~1.0) has no known analytical derivation from first principles.
docs/science/agents/gamma_scaling_manuscript.md:163:### 5.3 The Kuramoto precedent
docs/science/agents/gamma_scaling_manuscript.md:165:Kuramoto (1975) introduced his coupled oscillator model to describe the Belousov-Zhabotinsky chemical reaction. That the same equation would describe firefly synchronization, cardiac rhythms, and neural oscillations was not predicted — it was discovered empirically over the following two decades (Strogatz 2000).
docs/science/agents/gamma_scaling_manuscript.md:167:γ-scaling may follow a similar trajectory. The empirical pattern — convergence across substrates, clean controls, reproducible sensitivity to parameters — is established. The theoretical explanation for why five substrates converge on γ ≈ 1.0 remains open. We report the observation without overclaiming its interpretation.
docs/science/agents/gamma_scaling_manuscript.md:175:5. DNCA measurements use fast mode (forward model learning disabled); full learning may produce different γ dynamics.
docs/science/agents/gamma_scaling_manuscript.md:180:2. The prediction error field shows γ_PE ≈ 0.76 across all DNCA conditions. Why is the system-environment interface invariant to internal architecture?
docs/science/agents/gamma_scaling_manuscript.md:181:3. Can γ differentiate pathological from healthy organization in real neural data (e.g., epilepsy, Parkinson's)?
docs/science/agents/gamma_scaling_manuscript.md:182:4. What is the relationship between γ and other complexity measures (integrated information Φ, transfer entropy, Lempel-Ziv complexity)?
docs/science/agents/gamma_scaling_manuscript.md:188:We report an empirical observation: the topological scaling exponent γ, measured via cubical persistent homology on time-evolving density fields, converges on γ ∈ [0.86, 1.33] across five independent substrates — biological tissue, reaction-diffusion fields, market synchronization, spin lattices, and cognitive competitive dynamics. Shuffled controls yield γ ≈ 0 in every case. The convergence is not a measurement artifact, not a critical exponent, and not universal to all dynamical systems. It is a reproducible, falsifiable, substrate-spanning pattern whose theoretical explanation is an open problem.
docs/science/agents/gamma_scaling_manuscript.md:192:> *Five independent substrates — zebrafish morphogenesis, Gray-Scott reaction-diffusion, Kuramoto market synchronization, 2D Ising lattice, and neuromodulatory cognitive competition — converge on γ ∈ [0.86, 1.33] when operating in moderate-variability regimes. All organized systems show γ > 0; all shuffled controls show γ ≈ 0. The mechanism underlying the convergence on γ ≈ 1.0 is unknown. We report the pattern.*
docs/science/agents/gamma_scaling_manuscript.md:208:Kuramoto Y. (1975) Self-entrainment of a population of coupled non-linear oscillators. *Lecture Notes in Physics* 39:420–422.
docs/science/agents/gamma_scaling_manuscript.md:220:Strogatz S.H. (2000) From Kuramoto to Crawford: exploring the onset of synchronization in populations of coupled oscillators. *Physica D* 143:1–20.
docs/science/agents/gamma_scaling_manuscript.md:222:Tognoli E., Kelso J.A.S. (2014) The metastable brain. *Neuron* 81(1):35–48.
```

## docs/science/agents/results_gamma.md

_matches: 50_

```
docs/science/agents/results_gamma.md:1:# 3. Results: γ-scaling as a Substrate-Specific Candidate Marker of Organized Systems
docs/science/agents/results_gamma.md:3:## 3.1 γ-scaling in zebrafish pigmentation (McGuirl et al. 2020)
docs/science/agents/results_gamma.md:5:The γ-scaling exponent was first measured on density fields of zebrafish skin pigmentation patterns by McGuirl et al. (2020, PNAS 117(21):11350–11361). Using cubical persistent homology on time-lapse images of wild-type zebrafish pigmentation, with H0 persistent entropy (pe₀) and H0 Betti number (β₀) extracted at each developmental timepoint, the authors computed the scaling relationship between topological change rates: log(Δpe₀) versus log(Δβ₀). The wild-type zebrafish exhibited γ_WT = +1.043 with R² = 0.492 (p = 0.001, 95% CI = [0.933, 1.380]). The corresponding H1 maximum homology lifetime (H1_MHL_WT) was 0.464, indicating topologically organized pattern formation. Mutant fish with disrupted cell–cell communication showed significantly different γ values and reduced H1_MHL, confirming that γ captures the organizing principle of the biological system rather than mere geometric regularity. This established γ as a candidate invariant of biological self-organization measurable through persistent homology.
docs/science/agents/results_gamma.md:7:## 3.2 γ-scaling in DNCA internal trajectories
docs/science/agents/results_gamma.md:9:We measured γ on the internal state trajectories of the Distributed Neuromodulatory Cognitive Architecture (DNCA), a computational system with no geometric substrate, no pigmentation, and no biological cells. DNCA implements six neuromodulatory operators (dopamine, acetylcholine, norepinephrine, serotonin, GABA, glutamate) competing through Lotka-Volterra winnerless dynamics over a shared predictive state. Each operator runs a Dominant-Acceptor cycle (Ukhtomsky 1923; Anokhin 1968) as its base computational unit.
docs/science/agents/results_gamma.md:11:From the NMO activity field — the six-dimensional vector of operator activities recorded over 1000 timesteps — we constructed sliding-window density snapshots (window = 50 steps) and applied the identical TDA pipeline: cubical persistent homology, H0 persistent entropy, H0 Betti number, log-delta Theil-Sen regression. The result: γ_DNCA = +1.285 with 95% bootstrap CI = [+0.987, +1.812], R² = 0.138, n = 949 valid measurement pairs. The confidence interval includes γ_WT = +1.043.
docs/science/agents/results_gamma.md:13:A randomized control was performed by independently permuting the pe₀ and β₀ series to destroy their temporal coupling. The random baseline yielded γ_random = −0.009 (CI = [−0.069, +0.145], R² = 0.001), confirming that the observed γ_DNCA is not an artifact of the measurement pipeline or windowing procedure.
docs/science/agents/results_gamma.md:15:### γ grows with learning
docs/science/agents/results_gamma.md:17:When γ was computed in sliding windows of 200 steps across a 2000-step trajectory, the mean γ over the first five windows was +1.260 and over the last five windows was +1.481, demonstrating a monotonic increase with training. This suggests that γ is not a static parameter but a developmental metric: as the system learns to predict its environment more accurately (mismatch decreasing from 0.61 to 0.37), its topological coherence increases. If confirmed across architectures, this would establish γ as the first topological measure of cognitive development.
docs/science/agents/results_gamma.md:19:### Inverted-U γ versus noise level
docs/science/agents/results_gamma.md:21:Five separate 1000-step trajectories were collected at noise levels σ ∈ {0.0, 0.05, 0.1, 0.2, 0.5}. The γ values were: +1.389, +1.276, +1.445, +1.475, +1.198, respectively. The peak occurred at σ = 0.2, with lower values at both extremes. This inverted-U pattern directly validates the metastability hypothesis: the system achieves maximum topological coherence at intermediate noise levels where the Kuramoto order parameter fluctuates most (r_std = 0.147), not at zero noise (rigid regime, r_std → 0) or high noise (collapsed regime, r_std → 0). This provides an independent topological confirmation of the metastability operating point, complementing the standard oscillatory measure r(t).
docs/science/agents/results_gamma.md:25:The same TDA pipeline applied to the prediction error field (state_dim-dimensional vectors over time) yielded γ_PE = +0.482 (CI = [+0.315, +0.789], R² = 0.075). While lower than the NMO activity measurement and with weaker R², this value is significantly positive, indicating that the prediction error dynamics also exhibit organized scaling — though at a different scale than the competitive dynamics of operator activities.
docs/science/agents/results_gamma.md:27:## 3.3 γ-scaling in MFN⁺ morphogenetic fields
docs/science/agents/results_gamma.md:29:To extend the measurement beyond neural/cognitive substrates, we computed γ on the 2D reaction-diffusion fields of Mycelium Fractal Network Plus (MFN⁺), a morphogenetic simulation implementing Gray-Scott dynamics on a 128×128 spatial grid. The activator and inhibitor concentration fields at each timestep were treated as 2D density images — identical to the zebrafish pigmentation density fields of McGuirl et al. — and processed through the same cubical persistent homology pipeline: H0 persistent entropy, H0 Betti number, log-delta Theil-Sen regression with 200-iteration bootstrap CI.
docs/science/agents/results_gamma.md:31:The activator field yielded γ_MFN(activator) = +0.865 with 95% CI = [+0.649, +1.250]. The confidence interval includes γ_WT = +1.043, establishing direct overlap with the biological measurement. The inhibitor field yielded γ_MFN(inhibitor) = +0.655 (CI = [+0.431, +0.878]), lower but still positive, reflecting the inhibitor's role as a smoother, less topologically complex field.
docs/science/agents/results_gamma.md:33:A shuffled control — temporal permutation of the field sequence destroying developmental trajectory while preserving per-frame statistics — yielded γ_control = +0.035, confirming that the observed γ reflects temporal organization of the morphogenetic process, not static spatial properties of individual frames.
docs/science/agents/results_gamma.md:35:This result is significant because MFN⁺ Gray-Scott dynamics share no parameters, no code, and no architectural similarity with either zebrafish pigmentation or DNCA cognitive competition. Yet the γ values overlap. The organizing principle measured by γ is not specific to any substrate — it is a property of how organized systems evolve their topological structure over time.
docs/science/agents/results_gamma.md:37:## 3.4 γ-scaling in market synchronization regimes
docs/science/agents/results_gamma.md:39:We measured γ on the Kuramoto coherence trajectories of mvstack, an economic synchronization model where coupled oscillators represent market agents. The coherence order parameter r(t) — the magnitude of the mean phase vector — was recorded over 500 timesteps and embedded into 2D sliding-window images for the same TDA pipeline.
docs/science/agents/results_gamma.md:42:- **Trending market** (trend = 0.01): γ_trending = +1.081 (CI = [+0.869, +1.290])
docs/science/agents/results_gamma.md:43:- **Chaotic market** (trend = 0.0): γ_chaotic = +1.007 (CI = [+0.797, +1.225])
docs/science/agents/results_gamma.md:45:Both conditions produce γ > 0 with CIs overlapping γ_WT = +1.043. The difference between conditions is small: Δγ = +0.074, indicating that γ in market synchronization reflects the topological structure of the Kuramoto coupling mechanism itself, not the market's directional regime. This is consistent with the thesis: the organizing principle is in the synchronization dynamics, and γ measures its invariant topology regardless of whether the market is trending or chaotic.
docs/science/agents/results_gamma.md:47:Shuffled controls yielded γ_control(trending) = +0.145 and γ_control(chaotic) = −0.083, both near zero, confirming that the measurement captures genuine temporal organization.
docs/science/agents/results_gamma.md:51:Previous measurements in Section 3.2 used state_dim=8 as a computational proxy, yielding γ_DNCA = +2.072 (CI [1.341, 2.849]). To determine whether this elevated γ was an artifact of reduced dimensionality, we performed a full validation with state_dim=64 (the architecture's native dimensionality) and 1000 integration steps, using window_size=100 and 500 bootstrap iterations for CI estimation.
docs/science/agents/results_gamma.md:53:Full validation yields: γ_DNCA_full = +2.185, 95% CI [1.743, 2.789], R² = 0.2235, n = 898 valid measurement pairs. The prediction error field measurement yields γ_PE = +0.476 (CI [0.210, 0.615], R² = 0.050). Control (trajectory-shuffled): γ_control = +0.045 (CI [-0.082, 0.148], R² = 0.002), confirming the signal is genuine and not a pipeline artifact.
docs/science/agents/results_gamma.md:55:The full-parameter DNCA measurement (γ = +2.185) is consistent with the reduced-parameter proxy (γ = +2.072), confirming that the elevated γ is not an artifact of dimensionality reduction. However, the confidence interval [1.743, 2.789] does not overlap with the biological-morphogenetic range [0.865, 1.081] (overlap = 0.000).
docs/science/agents/results_gamma.md:57:**Interpretation.** DNCA's neuromodulatory competitive dynamics (six operators in Lotka-Volterra winnerless competition) produce topological scaling at approximately twice the rate of reaction-diffusion or synchronization substrates. This likely reflects the architectural difference between competitive winner-take-all dynamics (where topological transitions are sharp and frequent) and diffusive/oscillatory dynamics (where topological change is gradual). Three substrates — biological (zebrafish), morphogenetic (MFN⁺), and economic (mvstack) — remain unified with divergence = 0.216. DNCA is reported as a related but architecturally distinct organizational scale: γ > 0, control ≈ 0, but γ_DNCA ≈ 2× the bio-morphogenetic invariant.
docs/science/agents/results_gamma.md:59:## 3.6 Δγ as structural diagnostic (perturbation analysis)
docs/science/agents/results_gamma.md:61:Across all substrates, perturbation or destruction of organizational structure drives γ toward zero:
docs/science/agents/results_gamma.md:63:| Perturbation | Substrate | γ_organized | γ_perturbed | Δγ |
docs/science/agents/results_gamma.md:71:In every case, destroying temporal coherence while preserving marginal statistics reduces γ by 0.8–2.0, confirming that γ measures the time-extended organizational process, not static signal properties. The DNCA shows the largest Δγ (−2.004), consistent with its higher absolute γ from the reduced-parameter measurement.
docs/science/agents/results_gamma.md:73:Additionally, DNCA γ exhibits an inverted-U relationship with noise: γ peaks at intermediate noise levels (σ = 0.2, γ = +1.475) and decreases at both zero noise (rigid regime, γ = +1.389) and high noise (collapsed regime, γ = +1.198). This links γ directly to the metastable operating point where Kuramoto order parameter fluctuations are maximal (r_std = 0.147), providing independent topological confirmation of the metastability hypothesis.
docs/science/agents/results_gamma.md:75:## 3.7 Control: γ_random ≈ 0 across all substrates
docs/science/agents/results_gamma.md:77:Every γ measurement was accompanied by a shuffled baseline. Summary of control values:
docs/science/agents/results_gamma.md:79:| Substrate | γ_control | Method |
docs/science/agents/results_gamma.md:86:Mean γ_control = +0.041 (SD = 0.094). No control exceeds |0.15|. The measurement pipeline does not produce spurious positive γ from unstructured data.
docs/science/agents/results_gamma.md:90:The central finding of this work is that γ-scaling — the log-log slope between changes in H0 persistent entropy and H0 Betti number — reproduces across four substrates that share no common implementation:
docs/science/agents/results_gamma.md:92:| Substrate | System | γ | 95% CI | Verdict |
docs/science/agents/results_gamma.md:97:| Economic | mvstack Kuramoto market synchronization | +1.081 | [+0.869, +1.290] | ORGANIZED |
docs/science/agents/results_gamma.md:100:The full DNCA validation (Section 3.5) confirmed γ_DNCA = +2.185 (CI [1.743, 2.789]) at native parameters (state_dim=64, 1000 steps), ruling out reduced-parameter artifacts. The DNCA CI does not overlap the bio-morphogenetic range [0.865, 1.081]. The remaining three substrates — biological, morphogenetic, and economic — yield γ values within a narrow band: 0.865–1.081, with divergence = 0.216. The NFI Unified γ Diagnostic classifies this triad as **UNIFIED** (divergence < 0.3, all γ ∈ [0.649, 1.290]). DNCA is classified as a related but architecturally distinct organizational regime.
docs/science/agents/results_gamma.md:104:1. **Cross-substrate consistency.** γ > 0 in all organized systems, γ ≈ 0 in all shuffled controls. This is the minimal condition for an invariant.
docs/science/agents/results_gamma.md:106:2. **CI overlap with biological ground truth.** MFN⁺ CI [0.649, 1.250] and mvstack CI [0.869, 1.290] both include γ_WT = 1.043. The measurement does not merely detect organization — it detects the *same degree* of organization as the biological reference.
docs/science/agents/results_gamma.md:108:3. **γ grows with learning.** In DNCA, γ increases monotonically as prediction error decreases over training, suggesting it tracks the development of an internal model — consistent with Levin's (2019) definition of self-organizing systems as those containing a model of their own future state.
docs/science/agents/results_gamma.md:110:4. **γ peaks at metastability.** The inverted-U relationship between γ and noise in DNCA links topological coherence to the edge-of-chaos operating regime, providing an independent confirmation via persistent homology of what Kuramoto r(t) measures via oscillatory dynamics.
docs/science/agents/results_gamma.md:112:5. **Regime-independence in markets.** mvstack γ is stable across trending and chaotic market conditions (Δγ = 0.074), indicating that the invariant captures the coupling topology, not the behavioral state — consistent with γ being a structural rather than dynamical quantity.
docs/science/agents/results_gamma.md:116:The DNCA γ = +2.185 (full validation: state_dim=64, 1000 steps, CI [1.743, 2.789]) does not overlap with the biological-morphogenetic range [0.865, 1.081]. The reduced-parameter proxy (state_dim=8, γ = +2.072) and full validation are consistent, confirming this is a genuine architectural difference rather than a computational artifact. Neuromodulatory competitive dynamics (Lotka-Volterra winnerless competition among six operators) produce sharper topological transitions than reaction-diffusion or synchronization substrates, yielding γ ≈ 2× the bio-morphogenetic invariant. Three substrates remain unified (divergence = 0.216); DNCA represents a related but distinct organizational scale.
docs/science/agents/results_gamma.md:122:### Toward a universal statement
docs/science/agents/results_gamma.md:124:Despite these caveats, the pattern is clear: **organized systems exhibit γ > 0, random systems exhibit γ ≈ 0, and the specific value γ ≈ 1.0 appears in biological, morphogenetic, and economic substrates with overlapping confidence intervals.** If confirmed with empirical data across additional substrates, this would establish γ as the first quantitative, substrate-specific candidate marker of organized systems — measurable through persistent homology alone, requiring no knowledge of the system's internal mechanism. (Substrate-independence is empirically contradicted by the 2026-04-14 HRV n=5 pilot: γ mean 0.50 ± 0.44. See `docs/CLAIM_BOUNDARY.md` §2.)
docs/science/agents/results_gamma.md:128:> *Three independent substrates converge on γ ∈ [0.865, 1.081] (divergence = 0.216, verdict: UNIFIED): zebrafish morphogenesis (γ = +1.043), MFN⁺ reaction-diffusion (γ = +0.865), and market synchronization (γ = +1.081). Neuromodulatory cognitive dynamics exhibit a related but architecturally distinct scaling regime (γ = +2.185), consistent with the stronger topological transitions of competitive winner-take-all dynamics. All organized substrates show γ > 0; all shuffled controls show γ ≈ 0. γ-scaling is a substrate-specific candidate signature of organization, with the specific value γ ≈ 1.0 characterizing diffusive-oscillatory self-organization.*
docs/science/agents/results_gamma.md:148:Vasylenko Y. (2026) Distributed Neuromodulatory Cognitive Architecture: γ-scaling as substrate-specific candidate marker. neuron7xLab Technical Report.
```

## docs/science/agents/section4_mechanistic_interpretation.md

_matches: 43_

```
docs/science/agents/section4_mechanistic_interpretation.md:1:## 4. Mechanistic Interpretation of γ-Regimes
docs/science/agents/section4_mechanistic_interpretation.md:5:The divergence between γ ≈ 1.0 (zebrafish, MFN⁺, market) and γ ≈ 2.185 (DNCA full validation) raised a mechanistic question: what determines the γ-regime of an organized system? Two hypotheses were tested:
docs/science/agents/section4_mechanistic_interpretation.md:7:**H1 (Spatial Geometry):** γ is determined by whether organization operates through spatial propagation (diffusion → γ ≈ 1.0) or global competition (no space → γ ≈ 2.0).
docs/science/agents/section4_mechanistic_interpretation.md:9:**H2 (Competition Strength):** γ is determined by the strength of winner-take-all dynamics. Weak competition → γ ≈ 1.0. Strong competition → γ ≈ 2.0.
docs/science/agents/section4_mechanistic_interpretation.md:11:Both hypotheses predict that reducing competition or introducing spatial locality in DNCA should shift γ toward 1.0.
docs/science/agents/section4_mechanistic_interpretation.md:21:γ was measured via BNSynGammaProbe (NMO activity field, window=50, 500 steps, 300 bootstrap iterations, seed=42) at five competition levels:
docs/science/agents/section4_mechanistic_interpretation.md:23:| Competition | γ_NMO | 95% CI | R² | γ_control | Verdict |
docs/science/agents/section4_mechanistic_interpretation.md:28:| 0.75 | +0.861 | [+0.590, +1.258] | 0.114 | +0.068 | CONSISTENT WITH γ_WT |
docs/science/agents/section4_mechanistic_interpretation.md:31:All controls satisfy |γ_ctrl| < 0.1 at every level, confirming the signal is genuine.
docs/science/agents/section4_mechanistic_interpretation.md:33:**Result: H2 is rejected.** The relationship between competition strength and γ is non-monotonic. γ does not decrease with weaker competition — it increases dramatically (γ = 4.55 at competition=0.0).
docs/science/agents/section4_mechanistic_interpretation.md:35:### 4.3 The U-shaped γ response
docs/science/agents/section4_mechanistic_interpretation.md:40:γ_NMO vs competition_strength:
docs/science/agents/section4_mechanistic_interpretation.md:48:  1.0 |              *-------- γ_WT = 1.043
docs/science/agents/section4_mechanistic_interpretation.md:55:The minimum occurs at competition ≈ 0.75, where γ_DNCA = +0.861 — which falls within the CI of γ_WT = +1.043 and overlaps with the bio-morphogenetic range [0.865, 1.081].
docs/science/agents/section4_mechanistic_interpretation.md:57:**This is the central finding:** the DNCA system converges to the biological γ-invariant at a specific operating point of its competition dynamics, not at the extremes.
docs/science/agents/section4_mechanistic_interpretation.md:59:**Interpretation.** At competition=0.0 (minimal competition), all NMO operators have nearly equal growth rates and weak mutual inhibition. This produces undifferentiated dynamics where topological transitions are frequent but unconstrained — each small perturbation creates a new topological feature. The result is inflated γ (more entropy change per Betti change).
docs/science/agents/section4_mechanistic_interpretation.md:61:At competition=1.0 (full WTA), the dynamics are dominated by sharp, discrete regime transitions. Each transition involves a sudden reorganization of the NMO activity landscape, producing large, correlated changes in both pe₀ and β₀. The ratio of these changes yields γ ≈ 2.0.
docs/science/agents/section4_mechanistic_interpretation.md:63:At competition≈0.75, the system operates in a regime where competition is strong enough to create well-defined regimes but not so strong that transitions are all-or-nothing. This "metastable competition" produces gradual, wave-like transitions — topologically similar to reaction-diffusion dynamics — yielding γ ≈ 1.0.
docs/science/agents/section4_mechanistic_interpretation.md:76:- γ_SpatialDNCA(NMO) = +3.870, CI [+2.295, +4.318]
docs/science/agents/section4_mechanistic_interpretation.md:77:- γ_SpatialDNCA(PE) = +0.680, CI [+0.567, +0.908]
docs/science/agents/section4_mechanistic_interpretation.md:78:- γ_control = −0.000
docs/science/agents/section4_mechanistic_interpretation.md:80:**H1 is rejected.** Introducing spatial locality increases γ rather than reducing it. The spatial diffusion creates spatially correlated NMO activities that produce large-scale topological transitions — each wave-like reorganization affects many spatial locations simultaneously, amplifying the topological entropy change.
docs/science/agents/section4_mechanistic_interpretation.md:82:However, the prediction error field γ_PE = +0.680 remains in the bio-morphogenetic range, suggesting that the PE measurement channel is more robust to architectural variations than the NMO activity channel.
docs/science/agents/section4_mechanistic_interpretation.md:84:### 4.5 Prediction error field: a robust γ channel
docs/science/agents/section4_mechanistic_interpretation.md:86:Across all experimental conditions, the prediction error field γ_PE shows remarkable stability:
docs/science/agents/section4_mechanistic_interpretation.md:88:| Condition | γ_PE | 95% CI |
docs/science/agents/section4_mechanistic_interpretation.md:97:Mean γ_PE = 0.757 (SD = 0.128). The PE field γ always falls within or near the bio-morphogenetic range [0.865, 1.081], regardless of competition strength or spatial structure. This suggests:
docs/science/agents/section4_mechanistic_interpretation.md:105:The original binary classification (Regime I: diffusive γ ≈ 1.0, Regime II: competitive γ ≈ 2.0) requires revision based on the experimental evidence:
docs/science/agents/section4_mechanistic_interpretation.md:107:**γ is not determined by the presence or absence of competition, nor by spatial geometry.** Instead, γ reflects the *dynamical regime* of the system's internal organization:
docs/science/agents/section4_mechanistic_interpretation.md:109:1. **Undifferentiated regime** (γ >> 1): competition too weak → unconstrained topological fluctuations → inflated γ
docs/science/agents/section4_mechanistic_interpretation.md:110:2. **Metastable regime** (γ ≈ 1.0): competition balanced → gradual regime transitions → γ converges to bio-morphogenetic invariant
docs/science/agents/section4_mechanistic_interpretation.md:111:3. **Winner-take-all regime** (γ ≈ 2.0): competition too strong → sharp discrete transitions → elevated γ
docs/science/agents/section4_mechanistic_interpretation.md:113:The bio-morphogenetic invariant γ ≈ 1.0 corresponds to Regime 2: metastable dynamics at the optimal balance of competition. This is consistent with the inverted-U relationship between γ and noise (Section 3.2) — both noise and competition have optimal operating points where topological coherence matches the biological reference.
docs/science/agents/section4_mechanistic_interpretation.md:115:**Falsifiable prediction:** Any system whose internal competition can be tuned should exhibit a U-shaped γ response, with a minimum near γ ≈ 1.0 at the metastability operating point. This prediction can be tested on:
docs/science/agents/section4_mechanistic_interpretation.md:118:- Economic models (by varying the coupling strength K in Kuramoto)
docs/science/agents/section4_mechanistic_interpretation.md:120:### 4.7 γ as a metastability diagnostic
docs/science/agents/section4_mechanistic_interpretation.md:122:The convergence of three independent observations strengthens the metastability interpretation:
docs/science/agents/section4_mechanistic_interpretation.md:124:1. **γ peaks at intermediate noise** (Section 3.2, inverted-U): maximum topological coherence at σ = 0.2 where r_std is maximal
docs/science/agents/section4_mechanistic_interpretation.md:125:2. **γ minimizes to bio-invariant at optimal competition** (this section): minimum at competition ≈ 0.75 where dynamics are metastable
docs/science/agents/section4_mechanistic_interpretation.md:126:3. **γ_PE is stable across all conditions** (this section): the prediction error channel filters out internal dynamics, preserving only the environment-system interface
docs/science/agents/section4_mechanistic_interpretation.md:128:Together, these suggest that γ ≈ 1.0 is not merely a coincidence across substrates — it is the **topological signature of metastability itself**. Systems at the edge of order and disorder, whether biological tissues, computational architectures, or economic networks, produce the same rate of topological change per unit structural reorganization.
docs/science/agents/section4_mechanistic_interpretation.md:130:If confirmed, this would establish γ not as a passive measurement of organization, but as a **diagnostic of dynamical regime**: given any time series from an unknown system, measuring γ tells you whether the system operates in the metastable band (γ ≈ 1.0), the rigid regime (γ > 1.5), or the chaotic regime (γ < 0.5).
docs/science/agents/section4_mechanistic_interpretation.md:136:Controls: independently shuffled pe₀ and β₀ series at every measurement point. All |γ_ctrl| < 0.1.
```

## docs/science/agents/section5_why_gamma_one.md

_matches: 46_

```
docs/science/agents/section5_why_gamma_one.md:1:## 5. Why γ ≈ 1.0? Seven Tests and an Honest Answer
docs/science/agents/section5_why_gamma_one.md:5:Section 4 established that γ minimizes to the bio-morphogenetic range [0.76, 0.90] at optimal competition in DNCA (competition ≈ 0.75). Three biological/synthetic substrates converge on γ ∈ [0.865, 1.081]. But *why* 1.0? Three possibilities were tested:
docs/science/agents/section5_why_gamma_one.md:7:- (A) γ = 1.0 is a mathematical consequence of criticality
docs/science/agents/section5_why_gamma_one.md:8:- (B) γ = 1.0 is an artifact of the TDA measurement pipeline
docs/science/agents/section5_why_gamma_one.md:9:- (C) γ = 1.0 is a fundamental constant of organized systems
docs/science/agents/section5_why_gamma_one.md:13:### 5.2 T3: Method falsification — is γ = 1.0 a pipeline artifact?
docs/science/agents/section5_why_gamma_one.md:17:| Signal | γ | R² | γ_ctrl | Bio range? |
docs/science/agents/section5_why_gamma_one.md:27:**Verdict: PARTIALLY ARTIFACT.** The 1D→2D embedding approach produces γ ≈ 1.0–1.6 for many signal types, including white noise (γ = 1.6). This is because time-delay embedding of correlated windows introduces systematic structure that inflates γ away from zero.
docs/science/agents/section5_why_gamma_one.md:29:**Critical distinction:** The DNCA, MFN⁺, and Ising measurements use *native multi-dimensional fields* (6-NMO activities, 2D grids), not 1D→2D embedding. In those native measurements, shuffled controls consistently yield γ ≈ 0, confirming the signal is genuine. The 1D embedding approach is methodologically different and should not be used to validate or invalidate native 2D measurements.
docs/science/agents/section5_why_gamma_one.md:31:**Methodological recommendation:** γ measurement via the TDA pipeline is valid on native multi-dimensional density fields. Extension to 1D signals requires alternative embedding methods.
docs/science/agents/section5_why_gamma_one.md:37:| T | Phase | γ | R² | Magnetization | γ_ctrl |
docs/science/agents/section5_why_gamma_one.md:46:**Key finding: γ decreases monotonically with temperature.** It is NOT peaked at T_c. The Ising model shows γ_Tc = 1.329 — within the range we observe for organized systems, but not special relative to neighboring temperatures.
docs/science/agents/section5_why_gamma_one.md:48:**Interpretation:** In the Ising model, γ tracks the *degree of spatial order*, not criticality per se. Ordered phases (low T) have persistent topological features that change coherently → high γ. Disordered phases (high T) have rapidly decorrelating features → γ approaches ~1.0 from above.
docs/science/agents/section5_why_gamma_one.md:50:The value γ ≈ 1.0 for the disordered phase is significant: it suggests that γ = 1.0 is the **natural baseline for systems with moderate topological variability** — when topological features change at uncorrelated, moderate rates, the log-log scaling between Δpe₀ and Δβ₀ naturally approaches unity.
docs/science/agents/section5_why_gamma_one.md:56:| Competition | η (power-law exponent) | η R² | γ | η/γ |
docs/science/agents/section5_why_gamma_one.md:64:**Verdict: γ ≠ η.** The power-law correlation exponent η ≈ 0.2 is nearly constant across all competition levels (Pearson r(η,γ) = 0.11). γ is not a standard critical exponent. It captures a different aspect of the system's topology than temporal correlations.
docs/science/agents/section5_why_gamma_one.md:70:| Competition | pe₀ std | β₀ std | corr(pe₀, β₀) | γ |
docs/science/agents/section5_why_gamma_one.md:78:**Mechanism identified:** γ is determined by the *ratio of variability* between persistent entropy (pe₀) and Betti number (β₀):
docs/science/agents/section5_why_gamma_one.md:80:- At competition=0.0: both pe₀ and β₀ have HIGH variance, near-perfect correlation → the log-log slope is dominated by extreme events where pe₀ changes superlinearly with β₀ → γ >> 1
docs/science/agents/section5_why_gamma_one.md:81:- At competition=0.75: MODERATE variance in both, still good correlation (0.87) → scaling is approximately linear → γ ≈ 1.0
docs/science/agents/section5_why_gamma_one.md:82:- At competition=1.0: LOW β₀ variance (5.6), lower correlation (0.74) → sharp discrete transitions create outlier points in the log-log space → γ ≈ 2.0
docs/science/agents/section5_why_gamma_one.md:84:**γ = 1.0 occurs when the topological features vary at moderate rates with moderate mutual coupling.** This is the regime where changes in persistent entropy scale linearly with changes in Betti number — each connected component that appears or disappears contributes a proportional amount of entropy.
docs/science/agents/section5_why_gamma_one.md:88:Hodgkin-Huxley, Van der Pol, and Lorenz systems were tested at critical/metastable and non-critical operating points:
docs/science/agents/section5_why_gamma_one.md:90:| System | γ | R² | γ_ctrl |
docs/science/agents/section5_why_gamma_one.md:101:**Verdict: NEGATIVE.** Low-dimensional ODE trajectories (2–4D) do not show γ ≈ 1.0 at critical points, nor do they differentiate critical from non-critical operating regimes. The TDA pipeline measures topological complexity of *density fields* — low-dimensional trajectories do not generate sufficiently rich topological structure for meaningful γ measurement.
docs/science/agents/section5_why_gamma_one.md:103:This narrows the domain of γ: it is applicable to **high-dimensional activity fields** (multi-NMO dynamics, spatial grids, reaction-diffusion fields), not to arbitrary dynamical systems.
docs/science/agents/section5_why_gamma_one.md:107:Five candidate formulas from critical exponent theory were tested against the 2D Ising measurement (γ_measured = 1.329):
docs/science/agents/section5_why_gamma_one.md:109:| Formula | Predicted γ (2D Ising) | Error |
docs/science/agents/section5_why_gamma_one.md:117:**Verdict: NO EXACT MATCH.** The closest formula ν·z/d = 1.083 is within 0.25 of the measured 1.329, but this is not precise enough to claim derivation from known critical exponents. The relationship between γ and standard universality class exponents, if any, is not a simple ratio.
docs/science/agents/section5_why_gamma_one.md:119:### 5.8 Synthesis: what γ actually is
docs/science/agents/section5_why_gamma_one.md:121:The seven experiments converge on a picture that is less dramatic than "universal law" but more honest and still significant:
docs/science/agents/section5_why_gamma_one.md:123:**1. γ is a topological scaling exponent of multi-dimensional density fields.**
docs/science/agents/section5_why_gamma_one.md:126:**2. γ ≈ 1.0 is the baseline for systems with moderate topological variability.**
docs/science/agents/section5_why_gamma_one.md:127:It occurs when topological features (connected components) are born and die at moderate, approximately proportional rates. Too much order (strong spatial correlations, rigid regimes) → γ > 1. Too much chaos (unconstrained fluctuations) → γ > 1 via extreme events. The balance → γ ≈ 1.
docs/science/agents/section5_why_gamma_one.md:129:**3. γ is NOT a critical exponent in the Ising/RG sense.**
docs/science/agents/section5_why_gamma_one.md:132:**4. γ IS a diagnostic of organizational regime in multi-component systems.**
docs/science/agents/section5_why_gamma_one.md:133:Across DNCA (6 NMO operators), Ising (32×32 grid), MFN⁺ (128×128 R-D field), zebrafish (pigmentation density field), and market (Kuramoto coherence): γ ∈ [0.86, 1.33] consistently appears when the system has *moderate topological variability* — the regime we identified as metastable in Section 4.
docs/science/agents/section5_why_gamma_one.md:136:Three substrates (zebrafish, MFN⁺, market) converge on γ ∈ [0.865, 1.081]. This convergence persists because:
docs/science/agents/section5_why_gamma_one.md:140:- Controls (γ_ctrl ≈ 0) confirm the signal
docs/science/agents/section5_why_gamma_one.md:142:However, the specific value ~1.0 may reflect a mathematical property of the Theil-Sen regression on log-deltas of persistent homology when the underlying density field has moderate variance — not a universal constant of organized systems.
docs/science/agents/section5_why_gamma_one.md:146:The original claim ("γ ≈ 1.0 is a substrate-independent invariant") is replaced by a more precise and defensible statement:
docs/science/agents/section5_why_gamma_one.md:148:> **γ-scaling measured via cubical persistent homology on multi-dimensional density fields consistently yields γ ∈ [0.86, 1.33] for systems operating in the metastable regime, across biological (zebrafish), morphogenetic (Gray-Scott), computational (DNCA at optimal competition), economic (Kuramoto), and physical (Ising near T_c) substrates. This convergence is not a measurement artifact (controls yield γ ≈ 0), not a critical exponent (not peaked at phase transitions), and not universal to all dynamical systems (low-dimensional ODEs are out of scope). It is a topological signature of multi-component systems operating with moderate topological variability.**
docs/science/agents/section5_why_gamma_one.md:152:1. Why does the log-log scaling of Δpe₀ vs Δβ₀ approach unity specifically for moderate-variance density fields? An analytical derivation connecting γ to the variance of the persistence diagram would strengthen the theoretical foundation.
docs/science/agents/section5_why_gamma_one.md:154:2. The prediction error field in DNCA shows γ_PE ≈ 0.76 across ALL competition levels (Section 4.5). If PE represents the system-environment interface, why is it always in the metastable range regardless of internal dynamics?
docs/science/agents/section5_why_gamma_one.md:156:3. The Ising result (γ monotonically decreasing with T) suggests γ captures spatial ORDER, not criticality. Can this be reconciled with the DNCA result (γ minimized at optimal competition ≈ 0.75)?
docs/science/agents/section5_why_gamma_one.md:172:Tognoli E., Kelso J.A.S. (2014) The metastable brain. *Neuron* 81(1):35–48.
```

## docs/science/manuscript/main.md

_matches: 6_

```
docs/science/manuscript/main.md:11:The central invariant: the scaling exponent gamma is **derived only, never assigned**.
docs/science/manuscript/main.md:17:universal scaling tests.
docs/science/manuscript/main.md:39:All four mock substrates recover gamma within 0.02 of the constructed
docs/science/manuscript/main.md:45:1. gamma NEVER hardcoded -- always from GammaRegistry.get()
docs/science/manuscript/main.md:46:2. gamma_ledger.json is the ONLY source of truth for gamma values
docs/science/manuscript/main.md:53:*"gamma derived only. Intelligence as regime property."*
```

## docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md

_matches: 110_

```
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:1:# Universal gamma-scaling at the edge of metastability: evidence from three independent biological substrates with simulation validation
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:12:We report empirical evidence for a universal scaling exponent $\gamma \approx 1.0$ observed across three independent biological substrates with additional simulation validation. **Tier 1 — Evidential (real external data):** zebrafish morphogenesis ($\gamma = 1.055$, $n = 47$, CI: $[0.89, 1.20]$, McGuirl 2020), human heart rate variability ($\gamma \approx 0.95$, CI $\approx [0.83, 1.08]$, PhysioNet NSR2DB), and human EEG during motor imagery ($\gamma \approx 1.07$, $n = 20$ subjects, CI: $[0.88, 1.25]$, PhysioNet EEGBCI). **Tier 2 — Simulation-validated:** Gray-Scott reaction-diffusion ($\gamma = 0.938$), Kuramoto oscillators at $K_c$ ($\gamma = 0.980$), and BN-Syn spiking criticality ($\gamma \approx 0.49$, honest finite-size deviation from mean-field prediction). Cross-substrate mean from evidential substrates only: $\bar{\gamma}$ with 95% CI containing unity. All Tier 1 substrates pass surrogate testing ($p < 0.05$), and three negative controls (white noise, random walk, supercritical) show $\gamma$ clearly separated from unity. The BN-Syn finite-size result ($\gamma \approx 0.49$ for $N=200$, $k=10$) is consistent with theoretical predictions of finite-size corrections below the upper critical dimension, validating that $\gamma \approx 1.0$ in biological substrates is a genuine property rather than a methodological artifact. We propose that $\gamma \approx 1.0$ constitutes a topological signature of metastability -- the dynamical regime where complex systems maintain coherent computation at the boundary between order and disorder.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:18:Complex systems across vastly different substrates -- from biological tissues to neural networks to financial markets -- share a common dynamical feature: they operate most effectively near critical points, at the boundary between ordered and disordered phases [1,2]. This regime, termed *metastability*, is characterized by long-range correlations, power-law scaling, and the capacity for flexible reconfiguration [3].
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:22:We introduce a complementary diagnostic: the *gamma-scaling exponent* $\gamma$, defined through the power-law relation between topological complexity $C$ and thermodynamic cost $K$:
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:24:$$K \sim C^{-\gamma}$$
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:26:where $C$ is a measure of the system's structural or information complexity and $K$ is the energetic or computational cost per unit of complexity. We present evidence that $\gamma \approx 1.0$ across five independent substrates, suggesting it may represent a universal signature of metastable computation.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:28:The extended mind thesis [4] proposes that cognitive processes extend beyond the brain into the environment. We test this framework empirically by treating the human-AI interaction loop as a measurable physical system and showing that productive cognitive coupling exhibits the same $\gamma$-scaling as biological and physical substrates.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:36:For a system with topological complexity $C$ (measuring information richness, structural diversity, or phase-space dimensionality) and thermodynamic cost $K$ (measuring energy expenditure, computational effort, or dissipation per unit complexity), we define the gamma-scaling relation:
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:38:$$K = A \cdot C^{-\gamma}$$
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:42:$$\log K = -\gamma \log C + \log A$$
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:44:The exponent $\gamma$ characterizes the system's efficiency-complexity tradeoff:
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:45:- $\gamma > 1$: *over-determined* -- cost decreases faster than complexity increases (convergent regime)
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:46:- $\gamma < 1$: *under-determined* -- cost decreases slower than complexity increases (divergent regime)  
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:47:- $\gamma = 1$: *critical balance* -- cost and complexity scale inversely at unit rate (metastable regime)
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:51:The gamma-scaling exponent relates to established criticality measures:
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:53:- **Branching ratio** $\sigma$: In spiking networks, $\sigma \approx 1.0$ indicates criticality [2]. Our BN-Syn substrate measures $\gamma = 0.950$ when $\sigma$ is tuned to the critical regime.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:55:- **Kuramoto order parameter** $r$: In coupled oscillator systems, coherence $r \in [0,1]$ measures synchronization. Our market substrate computes $\gamma$ from Kuramoto coherence trajectories, yielding $\gamma = 1.081$.¹
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:57:¹ $\gamma = 1.081$ refers to the market Kuramoto substrate (financial coherence trajectories, illustrative, not in Table 1). $\gamma = 0.980$ in Table 2 refers to the simulated Kuramoto oscillators at critical coupling $K_c$. These are distinct substrates measuring the same dynamical quantity in different contexts.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:59:- **Spectral radius** $\rho$: The largest eigenvalue of the system's Jacobian. In the neosynaptex cross-domain integrator, $\rho \approx 1.0$ and $\gamma \approx 1.0$ co-occur in the METASTABLE phase.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:79:**Statement:** Truth is not inevitable — it is the result of independent verification between autonomous witnesses. Within the framework of H1, intelligence is defined as a dynamical regime verified through synchronous phase shifts ($\gamma$) across independent channels of a single substrate, with coherent recovery. The absence of such cross-scale and independent reproducibility means the observed effect is an artifact of measurement or modeling.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:84:$$\forall\, S_i \in \{\text{substrates at metastability}\}:\quad \gamma_{S_i} \in [0.85, 1.15] \quad (\text{95\% CI contains } 1.0)$$
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:86:**Verification criterion:** H1 is supported if $\gamma \in [0.85, 1.15]$ with 95% CI containing 1.0 across $N \geq 3$ independent substrates from distinct physical domains, each passing surrogate testing ($p < 0.05$).
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:89:1. Measure $\gamma$ across $\geq 3$ independent substrates from distinct physical domains using Theil-Sen regression with bootstrap CI
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:91:3. If $\bar{\gamma}$ across substrates deviates from 1.0 by more than 2 SE $\to$ H1 rejected
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:92:4. If negative controls also produce $\gamma \approx 1.0$ $\to$ methodology is not discriminative, H1 cannot be tested
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:94:**Status:** SUPPORTED — three independent biological substrates (zebrafish, HRV PhysioNet, EEG PhysioNet), cross-substrate CI from Tier 1 contains unity. All Tier 1 IAAFT p-values $< 0.05$. Three additional simulation substrates provide theoretical validation; BN-Syn finite-size deviation ($\gamma \approx 0.49$) confirms methodology is not trivially producing $\gamma \approx 1.0$.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:100:**Statement:** The regime $\gamma \approx 1$ corresponds to a state that maximizes computational capacity at minimal cost of plasticity maintenance. This is an open claim requiring separate experimental and theoretical verification.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:103:$$\mathcal{C}_E:\quad \gamma \approx 1 \Longleftrightarrow \text{local minimum of energy dissipation while preserving plasticity}$$
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:114:4. If transformer achieves $\gamma \approx 1.0$ endogenously $\to$ H2 weakened
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:115:5. If BN-Syn holds $\gamma \approx 1.0$ at lower $C$ for equivalent $E$ $\to$ H2 supported
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:118:$$\gamma_{\text{dendritic}} \approx 1 \;\land\; \gamma_{\text{network}} \approx 1 \;\land\; \Delta\beta_{\text{dendritic}}(t) \sim \Delta\beta_{\text{network}}(t)$$
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:120:If dendritic-level $\gamma$ is indistinguishable from noise $\to$ compartmental model adds no explanatory power.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:131:- $\gamma_{\text{dendritic}}$ (compartment level)
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:132:- $\gamma_{\text{network}}$ (population level)
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:136:1. $\gamma_{\text{dendritic}}$ is stably measurable
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:138:3. Is not trivially identical to $\gamma_{\text{network}}$
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:141:**Fail-closed STOP:** If $\gamma_{\text{dendritic}} \approx \text{noise}$ $\to$ dendritic compartments are rejected. Scaling to main is FORBIDDEN until proof.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:145:### 2.5 Theoretical basis: $\gamma = 1.0$ in mean-field criticality
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:147:The result $\gamma = 1.0$ is not merely empirical but follows from mean-field theory of critical phenomena in multiple universality classes.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:149:**Branching process at $\sigma = 1$.** In a critical branching process, each event generates on average $\sigma = 1$ successor. The cost of propagating one unit of topological information is exactly one unit of energy [Harris, 1963]. This gives $K = C^{-1}$ directly, yielding $\gamma = 1$.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:151:**Self-organized criticality.** In the mean-field BTW sandpile [Bak, Tang & Wiesenfeld, 1987], avalanche size $S$ and duration $T$ satisfy $\langle S \rangle \sim T^{d_f/d}$. In mean-field ($d \geq d_c$), $d_f = d$, giving $\langle S \rangle \sim T^1$. The cost-complexity ratio $K/C \sim S/T = \text{const}$, yielding $\gamma = 1$.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:153:**Directed percolation universality.** Neural criticality belongs to the directed percolation universality class [Munoz et al., 1999; Beggs & Plenz, 2003]. In mean-field DP, the branching ratio $\sigma = 1$ at the critical point, and $\tau = 3/2$ (avalanche size exponent). The scaling relation $\gamma = (\tau_T - 1)/(\tau_S - 1)$ evaluates to exactly 1.0 in mean field.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:155:**Finite-size corrections.** Below the upper critical dimension $d_c$, corrections of order $\varepsilon = d_c - d$ appear, pushing $\gamma$ away from 1.0. Our BN-Syn simulation ($N=200$ neurons, $k=10$ sparse connectivity) yields $\gamma \approx 0.49$, consistent with finite-size deviations from the mean-field prediction. The observed $\gamma < 1$ in sparse networks confirms that the $\gamma \approx 1.0$ signature in biological substrates is a genuine property of those systems, not an artifact of the methodology.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:157:**Spectral connection.** At SOC, the power spectral density follows $S(f) \sim f^{-\beta}$ with $\beta = 1$ (1/f noise) [Bak et al., 1987]. The spectral exponent $\beta$ is related to the Hurst exponent $H$ via $\beta = 2H + 1$ (for fractional Brownian motion), giving $H = 0$ at criticality. In the HRV VLF range and EEG aperiodic component, $\beta \approx 1.0$ during healthy/active states corresponds to $\gamma_{\text{PSD}} \approx 1.0$, consistent with the topo-cost framework.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:167:**Note on fitting method.** We fit a deterministic scaling relation $K = A \cdot C^{-\gamma}$ in log-log space, not a power-law probability distribution. For scaling relations between two measured quantities, Theil-Sen regression on $(\log C, \log K)$ pairs is the appropriate estimator (robust to outliers, no distributional assumption on $K$). The maximum-likelihood framework of Clauset, Shalizi & Newman [14] applies to probability distributions $P(x) \sim x^{-\alpha}$; it is not applicable to scaling relations between paired observables.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:171:Bootstrap confidence intervals are computed by resampling with replacement ($B = 500$ iterations) and taking the 2.5th and 97.5th percentiles of the bootstrap distribution of $\gamma$.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:175:We apply three gates before accepting a $\gamma$ estimate:
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:182:A critical methodological point: the power spectral density $S(f) \sim f^{-\gamma}$ IS a topo-cost relationship. In this temporal formulation:
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:187:The scaling relation $S(f) = A \cdot f^{-\gamma}$ has exactly the form $K = A \cdot C^{-\gamma}$ from §2.1, where $C = f$ and $K = S(f)$. The $\gamma$ exponent extracted from the PSD via `compute_gamma(freqs, PSD)` is therefore the same quantity as the $\gamma$ extracted from spatial topo-cost pairs in the zebrafish substrate.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:189:This unification follows from the fluctuation-dissipation theorem: at thermodynamic equilibrium (and at critical points where generalized FDT holds), the spectral density of fluctuations is proportional to the system's dissipative response. At criticality, both spatial and temporal complexity-cost relationships converge to $\gamma \approx 1.0$.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:194:- **Dynamical topo-cost:** Kuramoto (volatility → 1/|returns|), BN-Syn (rate → rate CV)
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:196:All pass through the same `compute_gamma()` function: Theil-Sen regression on $(\log C, \log K)$ with bootstrap CI.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:200:To verify that observed $\gamma$ values are not artifacts of sample structure (e.g., autocorrelation or finite-size effects), we employ IAAFT (Iterative Amplitude Adjusted Fourier Transform) surrogates [Schreiber & Schmitz, 1996]. For each substrate, we generate $M = 199$ surrogates of the topological complexity time series. Each surrogate preserves the amplitude distribution and power spectrum of the original series but destroys the specific temporal ordering. We recompute $\gamma$ on each surrogate and calculate a two-tailed p-value: $p = (1 + \#\{|\gamma_{\text{null}}| \geq |\gamma_{\text{obs}}|\}) / (M + 1)$.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:204:To demonstrate that $\gamma \approx 1.0$ is not a trivial outcome of the methodology, we compute $\gamma$ for four classes of systems that should NOT exhibit metastable scaling:
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:210:If the methodology correctly detects $\gamma \approx 1.0$ only at criticality, these controls should all yield $\gamma$ far from unity or fail quality gates.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:218:| Substrate | $\gamma$ | 95% CI | $n$ | $R^2$ | IAAFT $p$ | $\log C$ range | Cutoff method | Verdict |
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:224:**Table 1.** Tier 1 evidential substrates. Cross-substrate mean: $\bar{\gamma} = 1.003 \pm 0.083$. $\log C$ range = natural log of topological complexity variable (see §3.4 for variable definitions). Cutoff method = how the lower bound of the fitting range was determined. *EEG $R^2$ is not applicable: $\gamma$ is computed as the per-subject mean aperiodic spectral exponent via specparam (Donoghue et al., 2020), not from log-log regression of topo-cost pairs. HRV uses VLF-range PSD of RR intervals (Peng et al., 1995). All substrates pass the quality gate $\text{range}(\log C) \geq 0.5$. Lower bound per data point: $C > 10^{-6}$ (numerical floor).
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:226:**DFA cross-validation (HRV).** As independent verification, we compute Detrended Fluctuation Analysis on the same RR interval series. DFA exponent $\alpha = 1.107 \pm 0.047$ ($n = 10$ subjects, range $[1.04, 1.18]$), confirming 1/f scaling. For stationary processes, $\alpha = (1 + \beta)/2$ where $\beta$ is the PSD spectral exponent; $\alpha \approx 1.1$ corresponds to $\beta \approx 1.2$, consistent with our PSD-based $\gamma = 0.885$ (the discrepancy reflects the different spectral windows used in Welch vs. DFA).
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:228:**Alternative model comparison.** For each Tier 1 substrate, we compare the power-law scaling model ($K = A \cdot C^{-\gamma}$, linear in log-log space) against lognormal (quadratic in log-log) and exponential ($K = A \cdot e^{-\lambda C}$) alternatives using AIC. Zebrafish: power-law preferred over lognormal ($\Delta\text{AIC} = +1.2$) and exponential ($\Delta\text{AIC} = +60.9$). HRV: power-law preferred over lognormal ($\Delta\text{AIC} = +1.5$) and exponential ($\Delta\text{AIC} = +29.7$). EEG: lognormal preferred ($\Delta\text{AIC} = -76.4$) on the full 2–35 Hz PSD, consistent with the spectral knee. Note: this AIC comparison applies to the full broad-band PSD; $\gamma$ for EEG is extracted from the aperiodic component only via specparam, which fits the $1/f$ region after removing the spectral knee — a non-overlapping analysis. Full results in `evidence/alternative_model_tests.json`.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:232:| Substrate | $\gamma$ | 95% CI | $n$ | $R^2$ | Note |
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:235:| Kuramoto oscillators ($K = K_c$) | 0.980 | [0.93, 1.01] | 300 | 0.42 | At critical coupling |
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:238:**Table 2.** Tier 2 simulation substrates. Gray-Scott and Kuramoto yield $\gamma$ near 1.0, consistent with mean-field predictions. BN-Syn ($N=200$ neurons, $k=10$) yields $\gamma \approx 0.49$, a finite-size deviation from the mean-field $\gamma = 1.0$ prediction, consistent with theoretical expectations below $d_c$ (§2.5). These substrates validate the methodology but are NOT counted toward the universality claim.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:242:| Substrate | $\gamma$ | SE | $|\gamma - 1|$ | MDE (80%) | Cohen's $d$ (vs $\gamma=0$) |
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:248:**Table 3.** Statistical power analysis. All substrates have Cohen's $d > 11$ (vs null $\gamma = 0$), indicating overwhelming evidence for non-zero scaling. Minimum detectable effect (MDE) at 80% power ranges from 0.18 to 0.26, meaning each substrate can reliably distinguish $\gamma = 1.0$ from $\gamma > 1.2$. Cross-substrate: $\bar{\gamma} = 1.003$, $t(2) = 0.06$ (two-sided $p > 0.9$ for $H_0: \gamma = 1.0$), confirming the mean is statistically indistinguishable from unity.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:252:| Substrate | $\gamma$ | 95% CI | $n$ | $R^2$ | CI contains 1.0 | Reason for exclusion |
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:258:**Table 2.** Illustrative substrates excluded from the core universality claim. Neosynaptex cross-domain is an aggregate of other substrates and therefore not independent. CNS-AI productivity classification was performed by the measured subject (single operator), introducing self-report bias; R2 values are catastrophically low, indicating the power-law model is a poor fit at the session level.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:264:$$\gamma_{\text{all}} = 1.059, \quad \text{CI} = [0.985, 1.131], \quad n = 8{,}271$$
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:266:The 95% confidence interval contains $\gamma = 1.0$.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:272:- $\gamma_{\text{productive}} = 1.138$, $|\gamma - 1| = 0.138$
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:273:- $\gamma_{\text{non-productive}} = -0.557$, $|\gamma - 1| = 1.557$
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:274:- $\Delta\gamma = 1.695$
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:280:| Type | $\gamma$ | 95% CI | $n$ |
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:291:| Control | $\gamma$ | $R^2$ | Verdict | Separated from $\gamma=1.0$ |
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:297:**Table 3.** Negative controls confirm that $\gamma \approx 1.0$ does not arise trivially from the methodology. Systems without critical dynamics show $\gamma$ clearly separated from unity, demonstrating falsifiability.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:301:To confirm that $\gamma \approx 1.0$ reflects causal dynamical structure rather than marginal distributional properties, we performed random pairing shuffles: for each Tier 1 substrate, we permuted the cost vector independently ($M = 199$ permutations), destroying the $C \leftrightarrow K$ correspondence while preserving both marginal distributions. In all three substrates, the shuffled $\gamma$ distribution collapsed to near-zero (median $|\gamma_{\text{shuffled}}| < 0.08$), while $\gamma_{\text{real}}$ remained closer to unity than any shuffled realization. This confirms that the scaling relationship is a property of the paired dynamical structure, not an artifact of the individual distributions of $C$ or $K$.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:303:| Substrate | $\gamma_{\text{real}}$ | $\gamma_{\text{shuffled}}$ (median) | Shuffled 95% CI | Separated |
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:311:To address variable selection bias, we tested 2 alternative $(C, K)$ proxy pairs per substrate. For zebrafish: population count vs NN_CV ($\gamma = 0.46$) and density vs 1/population ($\gamma = 2.29$). For HRV: LF band PSD (insufficient data) and full-band PSD ($\gamma = 0.89$, in band). For EEG: 8-30 Hz PSD ($\gamma = 0.57$) and 2-12 Hz PSD ($\gamma = 0.98$, in band). Result: 2/6 alternatives produced $\gamma$ in the metastable band. This confirms that $\gamma \approx 1.0$ is **not** a generic property of any complexity-cost pairing — it is specific to the theoretically motivated variable definitions (§3.4). The combination of proxy specificity (most alternatives fail) and shuffle sensitivity (destroying pairing kills the scaling) constitutes strong evidence against variable selection bias.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:315:**Figure 1** (manuscript/figures/fig1_substrates.pdf): Six-panel log-log scatter plots (2 rows x 3 columns) showing the topo-cost scaling relationship for each substrate. Row 1 (green, Tier 1 Evidential): zebrafish morphogenesis, HRV PhysioNet, EEG PhysioNet. Row 2 (blue, Tier 2 Simulation): Gray-Scott reaction-diffusion, Kuramoto oscillators, BN-Syn spiking criticality. Red lines: Theil-Sen robust regression fits. Each panel displays $\gamma$ and 95% CI.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:317:**Figure 2** (manuscript/figures/fig2_convergence.pdf): Cross-substrate $\gamma$ convergence by tier. Bar chart with 95% CI error bars. Green bars: Tier 1 evidential substrates. Blue bars: Tier 2 simulation substrates. Dashed line: $\gamma = 1.0$ reference.
docs/science/root_manuscript/XFORM_MANUSCRIPT_DRAFT.md:319:**Figure 3** (manuscript/figures/fig3_controls.pdf): Negative control $\gamma$ values. Shaded band: metastable zone $[0.85, 1.15]$. All controls fall outside the metastable band, confirming falsifiability of the $\gamma \approx 1.0$ claim.
... [30 more lines omitted; see audit/pre_closure_scan.txt]
```

## docs/submission/SUBMISSION_CHECKLIST.md

_matches: 10_

```
docs/submission/SUBMISSION_CHECKLIST.md:16:- [ ] **[GATE]** `python reproduce.py` produces gamma values matching `evidence/gamma_ledger.json`
docs/submission/SUBMISSION_CHECKLIST.md:28:- [ ] **[GATE]** Every substrate in Table 1 has a `VALIDATED` entry in `evidence/gamma_ledger.json`
docs/submission/SUBMISSION_CHECKLIST.md:39:- [ ] Cross-substrate mean gamma CI reported in manuscript matches ledger computation
docs/submission/SUBMISSION_CHECKLIST.md:40:- [ ] Bootstrap n >= 500 for all gamma CI computations (check `_BOOTSTRAP_N` constant)
docs/submission/SUBMISSION_CHECKLIST.md:42:- [ ] Negative controls (white noise, random walk, supercritical) produce gamma outside [0.7, 1.3]
docs/submission/SUBMISSION_CHECKLIST.md:44:- [ ] BN-Syn finite-size deviation (gamma ≈ 0.49) documented and explained in manuscript
docs/submission/SUBMISSION_CHECKLIST.md:52:- [ ] All gamma values in text match `evidence/gamma_ledger.json` (no manual edits)
docs/submission/SUBMISSION_CHECKLIST.md:57:- [ ] Methods section references `core/gamma.py` and `core/bootstrap.py` for computation details
docs/submission/SUBMISSION_CHECKLIST.md:68:- [ ] Gamma trajectory figure (`gamma_trajectory.pdf`) present and matches `reproduce.py` output
docs/submission/SUBMISSION_CHECKLIST.md:104:- [ ] Confirm no prior publication of these specific gamma results
```

## docs/traceability/TRACEABILITY_MATRIX.md

_matches: 25_

```
docs/traceability/TRACEABILITY_MATRIX.md:25:| gamma derived only, never assigned | `tests/test_gamma_registry.py` | `core/gamma_registry.py` | `evidence/gamma_ledger.json` (invariant field) |
docs/traceability/TRACEABILITY_MATRIX.md:26:| gamma CI requires bootstrap n >= 500 | `tests/test_bootstrap_helpers.py::test_bootstrap_n` | `neosynaptex.py::_BOOTSTRAP_N`, `core/gamma.py` | `evidence/gamma_ledger.json` (bootstrap_metadata) |
docs/traceability/TRACEABILITY_MATRIX.md:27:| gamma estimator is Theil-Sen (not OLS) | `tests/test_integrity_v2.py::test_theil_sen_used` | `core/gamma.py::compute_gamma` | [ADR-003](../adr/ADR-003-theil-sen-estimator.md) |
docs/traceability/TRACEABILITY_MATRIX.md:37:| zebrafish gamma in [0.85, 1.15] | `tests/test_integrity_v2.py::TestZebrafish` | `substrates/zebrafish/adapter.py` | `evidence/gamma_ledger.json::zebrafish_wt` |
docs/traceability/TRACEABILITY_MATRIX.md:38:| eeg_physionet gamma in [0.85, 1.15] | `tests/test_integrity_v2.py::TestEEG` | `substrates/eeg_physionet/adapter.py` | `evidence/gamma_ledger.json::eeg_physionet` |
docs/traceability/TRACEABILITY_MATRIX.md:39:| eeg_resting gamma CI contains 1.0 | `tests/test_eeg_resting_substrate.py` | `substrates/eeg_resting/adapter.py` | `evidence/gamma_ledger.json::eeg_resting` |
docs/traceability/TRACEABILITY_MATRIX.md:40:| hrv_physionet gamma in [0.75, 1.15] | `tests/test_integrity_v2.py::TestHRV` | `substrates/hrv_physionet/adapter.py` | `evidence/gamma_ledger.json::hrv_physionet` |
docs/traceability/TRACEABILITY_MATRIX.md:41:| hrv_fantasia gamma CI contains 1.0 | `tests/test_hrv_fantasia_substrate.py` | `substrates/hrv_fantasia/adapter.py` | `evidence/gamma_ledger.json::hrv_fantasia` |
docs/traceability/TRACEABILITY_MATRIX.md:42:| gray_scott gamma in [0.85, 1.15] | `tests/test_gray_scott_real.py` | `substrates/gray_scott/adapter.py` | `evidence/gamma_ledger.json::gray_scott` |
docs/traceability/TRACEABILITY_MATRIX.md:43:| kuramoto gamma in [0.85, 1.15] | `tests/test_kuramoto_real.py` | `substrates/kuramoto/adapter.py` | `evidence/gamma_ledger.json::kuramoto` |
docs/traceability/TRACEABILITY_MATRIX.md:44:| bn_syn gamma in [0.85, 1.15] | `tests/test_bnsyn_real.py` | `substrates/bn_syn/adapter.py` | `evidence/gamma_ledger.json::bnsyn` |
docs/traceability/TRACEABILITY_MATRIX.md:45:| serotonergic_kuramoto gamma CI contains 1.0 | `tests/test_serotonergic_kuramoto.py` | `substrates/serotonergic_kuramoto/adapter.py` | `evidence/gamma_ledger.json::serotonergic_kuramoto` |
docs/traceability/TRACEABILITY_MATRIX.md:46:| cfp_diy documented as out-of-regime | `tests/test_cfp_diy.py::test_out_of_regime_documented` | `substrates/cfp_diy/adapter.py` | `evidence/gamma_ledger.json::cfp_diy` |
docs/traceability/TRACEABILITY_MATRIX.md:54:| Shuffled topo breaks gamma | `tests/test_falsification_negative.py::test_gamma_breaks_under_shuffled_topo` | `core/gamma.py` | `tests/test_falsification_negative.py` |
docs/traceability/TRACEABILITY_MATRIX.md:55:| Random cost breaks gamma | `tests/test_falsification_negative.py::test_gamma_breaks_under_random_cost` | `core/gamma.py` | `tests/test_falsification_negative.py` |
docs/traceability/TRACEABILITY_MATRIX.md:56:| Brownian 1/f^2 returns gamma near 2 | `tests/test_falsification_negative.py::test_brownian_1_over_f_squared` | `core/gamma.py` | `tests/test_falsification_negative.py` |
docs/traceability/TRACEABILITY_MATRIX.md:58:| Exponential decay not METASTABLE | `tests/test_falsification_negative.py::test_exponential_decay_not_metastable` | `neosynaptex.py` | `tests/test_falsification_negative.py` |
docs/traceability/TRACEABILITY_MATRIX.md:66:| gamma is bit-exact reproducible (seed=42) | `tests/test_calibration_robustness.py` | `neosynaptex.py`, `core/gamma.py` | `reproduce.py` |
docs/traceability/TRACEABILITY_MATRIX.md:78:| AXIOM_0: mean gamma across substrates | `tests/test_axioms.py` | `core/axioms.py::verify_axiom_consistency` | `evidence/gamma_ledger.json` |
docs/traceability/TRACEABILITY_MATRIX.md:89:| gamma_provenance | `scripts/ci_canonical_gate.py::gate_gamma_provenance` | `evidence/gamma_provenance.md` | CI log |
docs/traceability/TRACEABILITY_MATRIX.md:91:| split_brain | `scripts/ci_canonical_gate.py::gate_split_brain` | `core/gamma_registry.py` | CI log |
docs/traceability/TRACEABILITY_MATRIX.md:93:| invariant_gamma | `scripts/ci_canonical_gate.py::gate_invariant_gamma` | `evidence/gamma_ledger.json` | CI log |
docs/traceability/TRACEABILITY_MATRIX.md:98:## Kuramoto-specific Traceability
docs/traceability/TRACEABILITY_MATRIX.md:100:For the Kuramoto substrate, a more detailed traceability matrix is available
docs/traceability/TRACEABILITY_MATRIX.md:101:at [`docs/traceability/kuramoto_traceability_matrix.md`](kuramoto_traceability_matrix.md).
```

## docs/traceability/kuramoto_traceability_matrix.md

_matches: 1_

```
docs/traceability/kuramoto_traceability_matrix.md:7:| REQ-001 | Fractal Indicator Composition | [`core/indicators/fractal_gcl.py`](../../core/indicators/fractal_gcl.py), [`core/indicators/multiscale_kuramoto.py`](../../core/indicators/multiscale_kuramoto.py) | N/A | N/A | [Dataset Catalog](../dataset_catalog.md) | [MLOps Orchestration](../devops/mlops-orchestration.md) | [Operational Readiness](../operational_readiness_runbooks.md), [Model Rollback](../runbook_model_rollback.md) | [`tests/test_fractal_gcl.py`](../../tests/test_fractal_gcl.py), [`tests/unit/test_indicators_kuramoto_multiscale.py`](../../tests/unit/test_indicators_kuramoto_multiscale.py) |
```

## evidence/IMMACULATE_REPORT.md

_matches: 26_

```
evidence/IMMACULATE_REPORT.md:5:> for peer review", "γ ≈ 1 across 4 independent wild empirical
evidence/IMMACULATE_REPORT.md:8:> and 2026-04-14 the γ-program falsification discipline tightened
evidence/IMMACULATE_REPORT.md:12:> level produced γ mean 0.50 ± 0.44 (NOT γ ≈ 1 across subjects),
evidence/IMMACULATE_REPORT.md:13:> and BTCUSDT hourly produced γ ≈ 0. **Current canonical state lives
evidence/IMMACULATE_REPORT.md:35:> metadata in the ledger, falsification battery that proves γ breaks
evidence/IMMACULATE_REPORT.md:68:### Headline count — γ ≈ 1 witnesses by tier
evidence/IMMACULATE_REPORT.md:74:| **T3 (first-principles simulation)** | 3 | `gray_scott`, `kuramoto_market`, `bn_syn` |
evidence/IMMACULATE_REPORT.md:75:| **T3† (out-of-regime witness)** | 1 | `cfp_diy` γ=1.832 (falsifying control, not counted in success rows) |
evidence/IMMACULATE_REPORT.md:77:| **T5 (calibrated model)** | 1 | `serotonergic_kuramoto` (1.17× basin) |
evidence/IMMACULATE_REPORT.md:79:### γ values and bootstrap CIs
evidence/IMMACULATE_REPORT.md:81:| # | Substrate | Tier | γ | 95 % CI | R² | n | Verdict |
evidence/IMMACULATE_REPORT.md:89:| 7 | kuramoto_market | T3 | 0.963 | [0.930, 1.000] | 0.9 | — | METASTABLE |
evidence/IMMACULATE_REPORT.md:91:| 9 | serotonergic_kuramoto | T5 | 1.068 | [0.145, 1.506] | 0.58 | 20 | METASTABLE |
evidence/IMMACULATE_REPORT.md:103:| γ ≈ 1 across independent wild empirical domains | T1 | **4** |
evidence/IMMACULATE_REPORT.md:104:| γ ≈ 1 empirical + reanalysed | T1 ∪ T2 | 5 |
evidence/IMMACULATE_REPORT.md:105:| γ ≈ 1 empirical + first-principles | T1 ∪ T2 ∪ T3 | 8 |
evidence/IMMACULATE_REPORT.md:106:| γ ≈ 1 all tiers (incl. calibrated + live) | T1–T5 | 10 |
evidence/IMMACULATE_REPORT.md:137:evidence/gamma_provenance.md                    # T1…T5 taxonomy
evidence/IMMACULATE_REPORT.md:143:substrates/serotonergic_kuramoto/CALIBRATION.md # basin analysis docs
evidence/IMMACULATE_REPORT.md:155:evidence/gamma_ledger.json                      # +3 entries, bootstrap_metadata, method_tier
evidence/IMMACULATE_REPORT.md:157:substrates/serotonergic_kuramoto/adapter.py     # sigma_hz_op parameter
evidence/IMMACULATE_REPORT.md:207:wrote the measured γ into the ledger. These SHAs are a cryptographic
evidence/IMMACULATE_REPORT.md:210:- `813d1c7` / `b6b74e6` — serotonergic_kuramoto, γ = 1.0677
evidence/IMMACULATE_REPORT.md:211:- `92db821` — eeg_resting, γ = 1.2550 (adapter + ledger same commit)
evidence/IMMACULATE_REPORT.md:212:- `56b1c49` — hrv_fantasia, γ = 1.0032 (adapter + ledger same commit)
evidence/IMMACULATE_REPORT.md:241:falsification battery proves γ breaks under structure destruction,
```

## evidence/PREREG.md

_matches: 32_

```
evidence/PREREG.md:1:# Pre-Registration — NeoSynaptex γ Measurements
evidence/PREREG.md:6:> γ value was first committed to the ledger**. The pair is a
evidence/PREREG.md:8:> its current form *before* the reported γ value — i.e. the γ was
evidence/PREREG.md:28:- **Tier** — T1…T5 classification from `evidence/gamma_provenance.md`.
evidence/PREREG.md:32:  the γ value into `evidence/gamma_ledger.json`.
evidence/PREREG.md:33:- **Measured γ** — the value committed to the ledger.
evidence/PREREG.md:36:  adapter at commit X with seed 42 fails to reproduce γ within
evidence/PREREG.md:47:### serotonergic_kuramoto (T5)
evidence/PREREG.md:50:  ("feat(substrates): serotonergic 5-HT2A Kuramoto — γ=1.07 metastable")
evidence/PREREG.md:52:  ("test: calibration robustness sweep for serotonergic_kuramoto")
evidence/PREREG.md:55:  serotonergic_kuramoto entry")
evidence/PREREG.md:56:- **Measured γ (seed = 42):** 1.0677
evidence/PREREG.md:60:  `python -c "from substrates.serotonergic_kuramoto.adapter import SerotonergicKuramotoAdapter, _sweep_gamma; print(_sweep_gamma(SerotonergicKuramotoAdapter(concentration=0.5, seed=42)))"`
evidence/PREREG.md:61:  at commit `b6b74e6` must return γ = 1.0677 ± 1e-4. Any drift > 1e-4
evidence/PREREG.md:75:- **Measured γ:** 1.2550, CI95 [1.0323, 1.4515]
evidence/PREREG.md:76:- **Verdict:** WARNING (|γ − 1| = 0.255 > 0.15)
evidence/PREREG.md:79:  seed = 42 must return γ = 1.2550 ± 1e-4. Any drift > 1e-4
evidence/PREREG.md:94:- **Measured γ (DFA α₂):** 1.0032, CI95 [0.9352, 1.0593]
evidence/PREREG.md:97:  with seed = 42 must return γ = 1.0032 ± 1e-4.
evidence/PREREG.md:104:  `serotonergic_kuramoto` carried the block. Subsequent entries
evidence/PREREG.md:114:  ("test: falsification negative controls — proving γ breaks under
evidence/PREREG.md:118:  tests that the γ machinery is obliged to fail on (shuffled topo,
evidence/PREREG.md:122:  *structure-preserved* data (i.e. reports γ ∈ [0.7, 1.3] on
evidence/PREREG.md:124:  all γ claims it protects are suspect.
evidence/PREREG.md:126:### Calibration robustness (serotonergic_kuramoto)
evidence/PREREG.md:129:  ("test: calibration robustness sweep for serotonergic_kuramoto")
evidence/PREREG.md:132:  numbers reported in `substrates/serotonergic_kuramoto/CALIBRATION.md`.
evidence/PREREG.md:144:  (`zebrafish_wt`, `gray_scott`, `kuramoto_market`, `bn_syn`,
evidence/PREREG.md:151:  `evidence/gamma_provenance.md`.
evidence/PREREG.md:169:# Re-compute γ for each substrate at its pre-registered commit
evidence/PREREG.md:172:python -c "from substrates.eeg_resting.adapter import run_gamma_analysis; run_gamma_analysis(n_subjects=10)"
evidence/PREREG.md:173:# Expected: γ = 1.2550 ± 1e-4
```

## evidence/gamma_provenance.md

_matches: 81_

```
evidence/gamma_provenance.md:4:> γ-criticality claim. Every substrate that contributes a γ value to
evidence/gamma_provenance.md:5:> `evidence/gamma_ledger.json` is classified here into one of five
evidence/gamma_provenance.md:7:> reported γ with confidence interval, residual R², sample size, and
evidence/gamma_provenance.md:14:> `substrates/serotonergic_kuramoto/CALIBRATION.md`).
evidence/gamma_provenance.md:24:| **T1** | *wild empirical* | γ derived from raw measurement data acquired in an external experiment, fed through our pipeline with no tunable parameters beyond standard signal processing defaults. | Strongest. |
evidence/gamma_provenance.md:25:| **T2** | *published reanalysis* | γ derived from a published, peer-reviewed dataset (or its deposited derivative) via our pipeline. | Strong when the underlying dataset itself is raw experimental data; weaker when the dataset is already a simulation output from the cited paper. |
evidence/gamma_provenance.md:26:| **T3** | *first-principles simulation* | γ emerges from a deterministic physical or dynamical model whose parameters are fixed by theory (critical coupling, universality class) rather than tuned toward γ ≈ 1. | Moderate. Strong when the model is canonical and the operating point is forced by theory (e.g. K = K_c in Kuramoto); weaker when γ depends on a free parameter. |
evidence/gamma_provenance.md:27:| **T4** | *live orchestrator / self-observation* | γ computed by the NFI engine while observing its own runtime behaviour. | Illustrative only. Subject to selection bias and metric circularity. |
evidence/gamma_provenance.md:28:| **T5** | *calibrated model* | γ emerges from a parameterised model whose parameters were explicitly tuned to place the system at metastability. Robustness must be demonstrated by a basin-width analysis. | Weakest. Defensible only when the calibration basin is wide and documented. |
evidence/gamma_provenance.md:39:| # | Substrate | Tier | γ | 95 % CI | R² | n | Ledger key |
evidence/gamma_provenance.md:47:| 7 | kuramoto_market | T3 | 0.963 | [0.930, 1.000] | 0.9 | — | `kuramoto` |
evidence/gamma_provenance.md:49:| 9 | serotonergic_kuramoto | T5 | 1.068 | [0.145, 1.506] | 0.58 | 20 | `serotonergic_kuramoto` |
evidence/gamma_provenance.md:54:† `cfp_diy` ships a γ value outside the [0.7, 1.3] metastable window.
evidence/gamma_provenance.md:60:They are explicitly constructed with a target γ and are **not**
evidence/gamma_provenance.md:80:  5. γ per subject = aperiodic exponent χ
evidence/gamma_provenance.md:81:  6. Aggregate: γ_mean ± 95 % CI across 20 subjects, permutation p
evidence/gamma_provenance.md:82:- **Reported.** γ = 1.068, CI [0.877, 1.246], n = 20, p_perm = 0.02.
evidence/gamma_provenance.md:87:    gives γ > 1.3 (shift away from critical).
evidence/gamma_provenance.md:88:  - Re-running with the newest `specparam` release changes γ_mean by
evidence/gamma_provenance.md:117:     χ. Per-subject = mean over epochs; aggregate γ = mean over
evidence/gamma_provenance.md:119:- **Reported.** γ = 1.255, CI [1.032, 1.452], n = 10, 299 epochs.
evidence/gamma_provenance.md:121:  (|γ − 1| = 0.255 > 0.15 METASTABLE threshold).
evidence/gamma_provenance.md:127:    `eeg_physionet`) reports γ = 1.068 on the same dataset. The two
evidence/gamma_provenance.md:131:  - No parameter in the pipeline was tuned toward γ = 1: alpha
evidence/gamma_provenance.md:139:  and is not grounds for demotion — γ = 1.26 is still within one
evidence/gamma_provenance.md:140:  population CI of the γ ≈ 1.07 measured by the alternate method on
evidence/gamma_provenance.md:143:  - Shuffling the frequency axis per epoch → γ should collapse to
evidence/gamma_provenance.md:145:  - γ from EEG with the PSD bins randomly permuted differs from γ
evidence/gamma_provenance.md:168:- **Reported.** γ = 0.885, CI [0.834, 1.080], R² = 0.93, n = 10.
evidence/gamma_provenance.md:172:  - Shuffling RR values destroys both γ and DFA α simultaneously
evidence/gamma_provenance.md:174:  - γ and DFA α disagree by more than 0.3.
evidence/gamma_provenance.md:204:  5. γ = α₂ = log-log slope over **long-scale** segment sizes
evidence/gamma_provenance.md:209:  γ (α₂) = 1.003, CI95 [0.935, 1.059], n = 10.
evidence/gamma_provenance.md:211:  Verdict: **METASTABLE** (|γ − 1| = 0.003 ≪ 0.15).
evidence/gamma_provenance.md:216:  γ = 0.885) is independent on both the dataset and the method.
evidence/gamma_provenance.md:242:  ourselves and none of its parameters were fit to produce γ ≈ 1.
evidence/gamma_provenance.md:248:- **Reported.** γ = 1.055, CI [0.890, 1.210], R² = 0.76, n = 45.
evidence/gamma_provenance.md:249:  Mutant controls: *pfef* γ ≈ 0.64 (sub-critical), *shady* γ ≈ 1.75
evidence/gamma_provenance.md:250:  (super-critical). Only WT lands in the metastable window.
evidence/gamma_provenance.md:252:  - γ computed on random subsets of 20 frames falls outside
evidence/gamma_provenance.md:255:    cell positions produces γ ≈ 1 (would indicate metric artefact).
evidence/gamma_provenance.md:266:- **Reported.** γ = 0.979, CI [0.880, 1.010], R² = 0.995, n = 20.
evidence/gamma_provenance.md:268:  - γ > 1.3 or < 0.7 on any F-sweep that includes ≥ 15 active-pattern
evidence/gamma_provenance.md:273:### T3 · kuramoto_market — first-principles oscillator network
evidence/gamma_provenance.md:275:- **Data source.** Self-contained 128-oscillator Kuramoto with
evidence/gamma_provenance.md:276:  Lorentzian frequencies (scale γ_freq = 0.5, so K_c = 1.0 exactly).
evidence/gamma_provenance.md:278:  not tuned toward γ ≈ 1. The mapping to market-like observables
evidence/gamma_provenance.md:281:- **Reported.** γ = 0.963, CI [0.930, 1.000], R² = 0.9.
evidence/gamma_provenance.md:283:  - γ > 1.3 or < 0.7 at K = K_c for any N ≥ 64 realisation.
evidence/gamma_provenance.md:284:  - γ invariant under K ∈ [0.5, 2.0] (would mean it is not critical).
evidence/gamma_provenance.md:291:  lower than the other T3 entries. The γ point estimate is close to 1
evidence/gamma_provenance.md:294:- **Reported.** γ = 0.946, CI [0.810, 1.080], R² = 0.28.
evidence/gamma_provenance.md:297:  - γ moves outside [0.7, 1.3] when k is varied between 3 and 6.
evidence/gamma_provenance.md:298:  - Destroying the branching structure (setting p ≠ 1/k) leaves γ
evidence/gamma_provenance.md:307:- **Reported.** γ = 1.832, CI [1.638, 1.978], R² = 0.853, n = 125.
evidence/gamma_provenance.md:308:  **This value is outside the [0.7, 1.3] metastable window.**
evidence/gamma_provenance.md:310:  methodology) but the resulting γ is *not* metastable. It is retained
evidence/gamma_provenance.md:313:  a γ that is explicitly out of regime. This demonstrates that
evidence/gamma_provenance.md:314:  γ ≈ 1 is not a bug of the fit, it is a property the substrate
evidence/gamma_provenance.md:323:- **Tier rationale.** T4 because γ is computed by the same system
evidence/gamma_provenance.md:325:  bias is possible (e.g. windows where γ drifts out of range may be
evidence/gamma_provenance.md:328:  - `nfi_unified`: γ = 0.8993, no CI, no R², `status: PENDING_REAL_DATA`.
evidence/gamma_provenance.md:329:  - `cns_ai_loop`: γ = 1.059, CI [0.985, 1.131], p_perm = 0.005,
evidence/gamma_provenance.md:335:  "N substrates with γ ≈ 1" claim unless T4 is explicitly called out.
evidence/gamma_provenance.md:337:### T5 · serotonergic_kuramoto — calibrated model
evidence/gamma_provenance.md:339:- **Data source.** Self-contained mean-field Kuramoto network
evidence/gamma_provenance.md:342:  `substrates/serotonergic_kuramoto/adapter.py` module docstring.
evidence/gamma_provenance.md:347:  numerically ill-defined γ; the operational σ = 0.065 Hz places the
evidence/gamma_provenance.md:348:  sweep at metastability.
evidence/gamma_provenance.md:349:- **Reported (seed = 42).** γ = 1.068, R² = 0.58, n = 20 sweep
evidence/gamma_provenance.md:352:  `substrates/serotonergic_kuramoto/CALIBRATION.md` and
evidence/gamma_provenance.md:354:  σ_op ∈ [0.04, 0.12] Hz and the width of the γ ∈ [0.7, 1.3] basin.
evidence/gamma_provenance.md:356:  - Calibration basin width < 2 adjacent σ_op values (would mean γ
evidence/gamma_provenance.md:358:  - γ dependence on construction seed exceeds 0.3 across 10 seeds.
evidence/gamma_provenance.md:360:    of its values leaves γ unchanged (tested in Phase 6).
evidence/gamma_provenance.md:372:  γ-related observable, not in ledger.
evidence/gamma_provenance.md:374:  — stubs or vendored infrastructure without a γ ledger entry.
evidence/gamma_provenance.md:384:| γ ≈ 1 across independent **wild empirical** domains | T1 | **4** (EEG-FOOOF, EEG-Welch, HRV-VLF, HRV-DFA) |
evidence/gamma_provenance.md:385:| γ ≈ 1 across independent **empirical + reanalysed** domains | T1 ∪ T2 | **5** (+ zebrafish) |
evidence/gamma_provenance.md:386:| γ ≈ 1 across **empirical + first-principles** domains | T1 ∪ T2 ∪ T3 | **8** (+ gray_scott, kuramoto_market, bn_syn) |
... [1 more lines omitted; see audit/pre_closure_scan.txt]
```

## evidence/levin_bridge/README.md

_matches: 1_

```
evidence/levin_bridge/README.md:22:3. Any document outside this directory that cites a γ-vs-horizon result MUST reference either the commit SHA of the row in this CSV or the verdict file.
```

## evidence/levin_bridge/horizon_knobs.md

_matches: 9_

```
evidence/levin_bridge/horizon_knobs.md:9:**Substrates in scope after audit.** Three — MFN+, Kuramoto, BN-Syn. The **LLM multi-agent** substrate is explicitly scoped out of the bridge at this time; see final section for the existing falsification record and the conditions under which it may re-enter.
evidence/levin_bridge/horizon_knobs.md:44:## 2. Kuramoto (`substrates/kuramoto/`)
evidence/levin_bridge/horizon_knobs.md:46:**Caveat — read first.** The `substrates/kuramoto/` tree does **not** contain a canonical Kuramoto oscillator simulator of the form `dθ/dt = ω + K·Σsin(θⱼ − θᵢ)`. It is the **TradePulse** market-regime analytics platform, which uses a Kuramoto-inspired coherence proxy **Δr** over financial return series. The protocol therefore operationalises H on the **proxy** system, not on a classical oscillator network. This caveat is non-trivial and must be restated in any manuscript that cites Kuramoto-substrate results.
evidence/levin_bridge/horizon_knobs.md:49:`substrates/kuramoto/analytics/regime/src/core/tradepulse_v21.py::TradePulseV21Pipeline.run()` (lines 742–799).
evidence/levin_bridge/horizon_knobs.md:68:- Coherence `_coherence()` (`tradepulse_v21.py:177`) uses FFT phase alignment; not formally validated against classical Kuramoto order parameter `R = |Σexp(iθⱼ)|/N`. Flag this in any cross-substrate comparison.
evidence/levin_bridge/horizon_knobs.md:70:- Rank normalisation of H across substrates is unspecified; for Kuramoto-proxy, rank by `window` days only.
evidence/levin_bridge/horizon_knobs.md:116:- GPT-4o-mini run: `γ = 0.214`, `p = 0.203`, 95 % CI crosses zero — COLLAPSE regime.
evidence/levin_bridge/horizon_knobs.md:117:- README (`experiments/lm_substrate/README.md:18–19`): *"γ ≈ 0 in all conditions. API-level LLM inference is stateless — no temporal coupling between calls."*
evidence/levin_bridge/horizon_knobs.md:141:| Kuramoto (TradePulse proxy) | `window`, `ema_alpha` | `substrates/kuramoto/analytics/regime/src/core/tradepulse_v21.py` | *(to append)* |
```

## evidence/levin_bridge/mfn_plus_contract_report.md

_matches: 3_

```
evidence/levin_bridge/mfn_plus_contract_report.md:26:## 4. γ may be derivable **if** the required `(topo, cost)` mapping is explicitly defined.
evidence/levin_bridge/mfn_plus_contract_report.md:28:`core/gamma.py::compute_gamma(topo, cost)` exists and is canonical. Mapping `SimulationResult.history` → `(topo_t, cost_t)` per-step arrays is possible in principle; each candidate mapping is an independent operationalisation that must be preregistered. At grid_size ≤ 48 and steps ≤ 300 within the CFL-safe α range, no per-step mapping attempted produced γ ≈ 1 with non-trivial R² on a single run — this is a methodology note, not a falsification of the bridge.
evidence/levin_bridge/mfn_plus_contract_report.md:40:The scaffold is correct. The simulator is callable. γ is computable with a stated `(topo, cost)` choice. C is computable. What is missing is a canonical, preregistered `P` contract for MFN+. Writing any row without that contract is fabrication. Truth-preserving stop is the correct state.
```

## evidence/replications/README.md

_matches: 4_

```
evidence/replications/README.md:10:This directory is the append-only index of every independent replication attempt filed against a γ-claim — whether supporting, falsifying, or theory-revising. The registry is deliberately empty at scaffold time: zero external replications have been logged.
evidence/replications/README.md:33:The gate is **structural only**: it does not re-run any replication, does not verify γ values against the ledger, does not judge claim scope. Semantic correctness — whether the prereg meets §7, whether controls are adequate, whether the verdict is warranted — remains the reviewer's job per the protocol.
evidence/replications/README.md:37:- `evidence/PREREG.md` — the original γ-measurement preregistration log. Different artefact: PREREG.md pins *measurement pipelines* to commit SHAs; this directory pins *replication attempts* to the canonical protocol.
evidence/replications/README.md:38:- `evidence/gamma_ledger.json` — authoritative γ values per substrate. Replications link back to ledger entries they test.
```

## evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md

_matches: 24_

```
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:1:# BTCUSDT Hourly γ-Replication Report — v1.0
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:6:> **Protocol.** γ-program Phase VI (independent of §Step 23 FRED).
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:15:- **γ = 0.0045** on BTCUSDT hourly log-returns, 8759 returns over
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:20:  1/f^γ scaling regime is detectable.
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:22:  |z| < 0.2 — γ_real is **statistically indistinguishable** from
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:25:**Verdict for cross-substrate γ ≈ 1 framing.** This substrate
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:28:γ-marker. Per `CLAIM_BOUNDARY.md §3.2`, this NARROWS the
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:30:universal across all market substrates and all resolutions; at
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:71:8759 returns). With γ ≈ 0 the question of whether nperseg=512
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:81:| γ | 0.0045 |
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:88:**γ ≈ 0 with r² ≈ 0** is the signature of a white-noise spectrum.
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:103:**All three tested nulls reproduce γ ≈ 0** because the underlying
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:107:The right reading: this is NOT a "null reproduces γ thus criticality
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:109:against. It is a "no fittable γ exists in the first place" outcome.
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:111:a γ-claim, full stop.
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:123:  - FRED macro: γ ≈ 0.94, AR(1)-non-separable (γ explained by
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:125:  - BTCUSDT hourly: γ ≈ 0, white-noise spectrum (no scaling).
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:126:  Both fail to support a market-critical γ ≈ 1 claim — for
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:134:- **Does NOT** falsify γ ≈ 1 in the neural / morphogenetic lanes;
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:150:| Substrate row in `SUBSTRATE_MEASUREMENT_TABLE.yaml` | Method | γ | Verdict |
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:157:(in different ways). No support for cross-substrate γ ≈ 1 from
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:203:   whether the white-noise verdict is BTC-specific or universal
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:215:| v1.0 | 2026-04-14 | Initial BTCUSDT hourly γ-replication. γ ≈ 0, white-noise spectrum. Substrate stays `hypothesized` (neither supports nor falsifies cross-substrate γ ≈ 1 at this resolution). |
evidence/replications/binance_btcusdt_1h/REPLICATION_REPORT_BTCUSDT.md:219:**claim_status:** measured (about this report; the γ-claim it contains is `hypothesized` per CLAIM_BOUNDARY.md §6)
```

## evidence/replications/eegbci_dh_replication/REPLICATION_REPORT_EEG_DH.md

_matches: 1_

```
evidence/replications/eegbci_dh_replication/REPLICATION_REPORT_EEG_DH.md:99:- Any cross-substrate universality claim that chains HRV → EEG through
```

## evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md

_matches: 22_

```
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:1:# FRED INDPRO γ-Replication Report — v1.0
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:5:> **Protocol.** γ-program Phase VI §Step 23.
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:14:- **γ = 0.9414** on FRED INDPRO monthly log-returns, 1919–2026
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:18:- **Reason: γ is NOT separable from AR(1) null** (z = 0.74,
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:70:| γ | 0.9414 |
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:77:γ = 0.94 is within the **prior range 0.5–1.5** for `market_macro`
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:98:- **Shuffled** rejects strongly (z ≈ 18). γ is not a product of the
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:100:- **AR(1)** reproduces γ ≈ 0.89 on surrogates with matched
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:101:  autoregressive parameter. Observed γ = 0.94 is within 1σ.
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:106:- **IAAFT** reproduces γ ≈ 0.88 on surrogates that preserve the
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:107:  amplitude spectrum and randomise phases. Observed γ is within
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:108:  ~2σ. This indicates γ is primarily encoded in the **linear
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:114:the observed γ.** Per `NULL_MODEL_HIERARCHY.md §6`, this blocks
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:125:  autocorrelation produces the same γ.
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:127:  class being a cross-substrate γ-convergence contributor.
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:128:- **Does NOT license** any statement that γ ≈ 0.94 on INDPRO is
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:139:- The FRED fetch + γ-fit + null-comparison pipeline works
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:143:  producing a γ value that would otherwise be tempting to
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:151:   aperiodic method and compare γ. Is the AR(1)-non-separability
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:181:with `γ ≈ 0.94`, `claim_status = hypothesized`, and the three null
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:191:| v1.0 | 2026-04-14 | Initial FRED INDPRO γ-replication. Claim remains `hypothesized` due to AR(1) and IAAFT non-separability. |
evidence/replications/fred_indpro/REPLICATION_REPORT_FRED.md:195:**claim_status:** measured (about this replication report; the γ-claim it contains is `hypothesized`)
```

## evidence/replications/hrv_iaaft_calibration/CALIBRATION_REPORT.md

_matches: 2_

```
evidence/replications/hrv_iaaft_calibration/CALIBRATION_REPORT.md:7:> `rr_to_uniform_4hz` from `substrates.physionet_hrv.hrv_gamma_fit`.
evidence/replications/hrv_iaaft_calibration/CALIBRATION_REPORT.md:152:resampler  : substrates.physionet_hrv.hrv_gamma_fit.rr_to_uniform_4hz
```

## evidence/replications/hrv_iaaft_calibration/IAAFT_REPAIR_REPORT.md

_matches: 2_

```
evidence/replications/hrv_iaaft_calibration/IAAFT_REPAIR_REPORT.md:53:`kuramoto_iaaft` in `core/iaaft.py` keep their own alternating-
evidence/replications/hrv_iaaft_calibration/IAAFT_REPAIR_REPORT.md:70:    multivariate shape, cross-correlation destruction, kuramoto shape,
```

## evidence/replications/nsr_chf_descriptive/DISCRIMINATOR_REPORT.md

_matches: 3_

```
evidence/replications/nsr_chf_descriptive/DISCRIMINATOR_REPORT.md:16:| Cross-substrate universality | **NOT CLAIMED HERE** |
evidence/replications/nsr_chf_descriptive/DISCRIMINATOR_REPORT.md:59:**Cross-substrate universality: NOT CLAIMED HERE.**
evidence/replications/nsr_chf_descriptive/DISCRIMINATOR_REPORT.md:76:4. Δh підтверджує критичний режим, SOC або metastability.
```

## evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md

_matches: 18_

```
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:15:the failed single-γ marker — **clearly discriminates** healthy vs
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:30:"якщо γ зсувається передбачувано, marker працює" — the marker
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:35:| Record | γ (Welch VLF) | r² | Δh | h(q=2) | beat-null sep? |
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:44:- γ mean = 1.54, std = 1.18 (very wide; CHF γ even more variable than NSR)
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:49:Note CHF γ-fits often have low r² because CHF spectra are heavy-tailed
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:50:and not cleanly 1/f. The Welch γ alone is therefore unreliable as a
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:58:| γ (Welch VLF) | 0.50 | 0.44 |
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:109:- **The pivot away from single-γ to 2D fingerprint** (PR #102 →
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:110:  this PR) was correct: single-γ was too noisy across NSR; the 2D
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:114:  a universal-γ ≈ 1 claim.
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:123:- **NO** universal cross-substrate γ ≈ 1 claim — this is a
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:129:## 8. Cross-substrate γ-program update
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:136:This is the FIRST POSITIVE FINDING in the γ-program. Earlier
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:145:| FRED INDPRO | 1 | γ=0.94, AR(1)-non-sep → no support |
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:146:| BTCUSDT 1h | 1 | γ≈0, white-noise → no support |
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:147:| HRV NSR n=1 | 1 | γ=1.09 → outlier (per n=5 follow-up) |
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:148:| HRV NSR n=5 | 5 | γ varies 0.07-1.09; Δh > 0; beat-null 4/5 |
evidence/replications/physionet_chf2db_contrast/REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md:190:**γ-claim status (cardiac 2D marker):** hypothesized → **strengthened to candidate marker** (per-cohort calibration; pathology-discriminative at pilot scale)
```

## evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md

_matches: 22_

```
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:1:# PhysioNet NSR2DB HRV γ-Replication Report — v1.0
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:6:> **Protocol.** γ-program Phase IV/V cardiac lane.
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:16:**First non-market γ-replication. γ ≈ 1.09 with clean fit. 2/3 nulls rejected.**
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:18:- **γ = 1.0855**, CI95 = [0.9180, 1.2404]
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:28:this is the first substrate where γ survives BOTH shuffled AND
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:29:AR(1). But **IAAFT non-separability** means the γ value is
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:41:  AR(1); real γ is BELOW AR(1) surrogate mean of 1.51).
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:45:- Net: the γ value at VLF is encoded primarily in the **linear
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:56:| Substrate | γ | r² | shuffled | AR(1) | IAAFT |
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:63:- Show a γ value clearly near 1.0 with a clean fit.
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:69:result alone — IAAFT-passing means the "γ near 1" comes from
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:100:| γ | -slope |
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:110:- **NO** cross-substrate γ ≈ 1 universal claim — IAAFT
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:119:- **NARROWING:** the γ ≈ 1 framing for HRV is captured by linear
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:123:- **PIPELINE PROOF:** the third independent substrate-class γ-fit
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:125:  the γ-program now spans 3 substrate classes (market_macro,
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:134:   RR series per subject (not truncated), per-subject γ + median,
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:141:   secondary. Compute α₂ at scales 16-64 beats, compare to γ.
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:143:   band. Different physiology, different γ expected.
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:144:5. **Multi-database control** — Fantasia (already in gamma_ledger
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:165:| v1.0 | 2026-04-14 | Initial pilot. n=1 (nsr001). γ=1.09, r²=0.97. 2/3 nulls separable; IAAFT non-separable caps at hypothesized. |
evidence/replications/physionet_nsr2db/REPLICATION_REPORT_HRV_NSR2DB.md:169:**claim_status:** measured (about this report; the γ-claim is hypothesized)
```

## evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md

_matches: 30_

```
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:12:**γ varies enormously across 5 subjects (0.07 to 1.09).** The n=1 pilot
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:13:on nsr001 was an outlier on the high side. Mean γ ≈ 0.50, std ≈ 0.44 —
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:14:no clean cross-subject γ ≈ 1 finding.
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:19:**Beat-interval null rejects on 4/5 subjects** → the γ value (whatever
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:25:| Record | γ | r² | Δh | h(q=2) | beat-null sep? |
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:35:| **γ (Welch VLF)** | **0.5016** | **0.4436** | [0.07, 1.09] |
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:42:The n=1 pilot reported γ = 1.09, r² = 0.97 on nsr001 with the
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:43:interpretation: "γ ≈ 1 with clean fit, 2/3 nulls reject". The
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:48:| Headline γ | 1.09 | 0.50 ± 0.44 |
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:49:| Cross-subject γ ≈ 1? | "yes" | **no** — wide variability |
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:53:| Implication for γ ≈ 1 universal | "supports" | **does not support** |
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:76:- **4 of 5 subjects: beat-interval null rejects** → γ requires
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:79:  literally worse than horizontal). So nsr003 has no fittable γ
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:81:- For the 4 subjects with meaningful γ-fits, the beat-interval null
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:86:  evidence that γ requires the **temporal ordering of beats**, not
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:92:> (Δh ≈ 0.19) and γ that varies enormously per-subject (0.07 to
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:94:> γ ≈ 1 universal — but does support a "regime marker candidate" with
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:95:> per-subject calibration required, since γ requires beat-ordered
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:101:- **γ requires beat-temporal order** on subjects with fittable γ.
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:102:- **Per-subject HRV γ is a possible regime marker** — but needs
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:103:  per-subject calibration, not universal interpretation.
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:107:- **NO** universal γ ≈ 1 claim — cross-subject mean is 0.50, not 1.0.
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:109:  is now SHOWN to be inconsistent with the universal-γ-near-1 framing.
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:118:| substrate | n | γ mean | γ std | r² | Δh | beat-null |
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:133:   PhysioNet. Compare γ and Δh between healthy NSR2DB and
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:134:   pathological cohorts. Without contrast γ = 0.50 ± 0.44 is
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:141:The cardiac substrate's contribution to γ-program §3.2 cross-substrate
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:146:- γ is highly variable per subject; mean ≠ 1.
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:150:the marker is interpreted per-subject (not universal). For a
evidence/replications/physionet_nsr2db_multifractal/REPLICATION_REPORT_HRV_MULTIFRACTAL.md:167:**γ-claim status (HRV cardiac substrate):** hypothesized → narrowed
```

## experiments/README.md

_matches: 4_

```
experiments/README.md:10:| [lm_substrate](lm_substrate/) | Complete | γ ≈ 0 (null — stateless API not a substrate) |
experiments/README.md:23:- Stateless calls → γ ≈ 0 (white noise, no temporal structure)
experiments/README.md:24:- Feedback chain → γ ≈ 0 (API context window is stateless)
experiments/README.md:25:- Confirms CFP thesis: γ ≠ 0 requires closed-loop dynamics
```

## experiments/lm_substrate/README.md

_matches: 6_

```
experiments/lm_substrate/README.md:1:# LM Substrate Experiment — GPT-4o-mini γ Derivation
experiments/lm_substrate/README.md:5:| Condition | γ | CI₉₅ | p | n | Regime |
experiments/lm_substrate/README.md:13:γ ≈ 0 in all conditions. API-level LLM inference is stateless — no temporal
experiments/lm_substrate/README.md:18:γ ≠ 0 requires a closed-loop dynamical system, not isolated inference.
experiments/lm_substrate/README.md:25:- `fig_gpt4o_gamma.png` — PSD figure (stateless)
experiments/lm_substrate/README.md:31:Prediction: γ ∈ [0.9, 1.1] if metastable → **FALSIFIED**
```

## experiments/scaffolding_trap/scaffolding_trap_finding.md

_matches: 16_

```
experiments/scaffolding_trap/scaffolding_trap_finding.md:27:### γ per AI-quality band
experiments/scaffolding_trap/scaffolding_trap_finding.md:29:| Band            | γ     | Regime      | Interpretation                              |
experiments/scaffolding_trap/scaffolding_trap_finding.md:36:**Critical transition: γ crosses 1.0 between AI=0.2 and AI=0.5.**
experiments/scaffolding_trap/scaffolding_trap_finding.md:105:### Гіпотеза: threshold γ < 1.0 = trap off?
experiments/scaffolding_trap/scaffolding_trap_finding.md:109:| AI quality | γ_band | CRR_struct | CRR_shuf | Δ      | Trap |
experiments/scaffolding_trap/scaffolding_trap_finding.md:117:**Trap активний навіть при γ=0.455 (глибоко субкритичний).**
experiments/scaffolding_trap/scaffolding_trap_finding.md:120:### Чому γ не є threshold?
experiments/scaffolding_trap/scaffolding_trap_finding.md:138:**Ключове відкриття**: trap NOT driven by γ or AI quality.
experiments/scaffolding_trap/scaffolding_trap_finding.md:183:5. **γ per condition** — F3 test does not compute separate γ for structured
experiments/scaffolding_trap/scaffolding_trap_finding.md:184:   vs shuffled. Only adapter-level γ exists (across AI quality).
experiments/scaffolding_trap/scaffolding_trap_finding.md:197:   (Layer 2) becomes the signal. Is it significant? Is it γ-dependent?
experiments/scaffolding_trap/scaffolding_trap_finding.md:239:α = 0.02 — universal learning rate coefficient в цій ABM.
experiments/scaffolding_trap/scaffolding_trap_finding.md:288:### Connection to γ
experiments/scaffolding_trap/scaffolding_trap_finding.md:296:The γ of the adapter (1.83) reflects this: throughput grows faster than
experiments/scaffolding_trap/scaffolding_trap_finding.md:344:### 2. dskill/dt = 0.02 × gap × effort: universal learning law (in this ABM)
experiments/scaffolding_trap/scaffolding_trap_finding.md:367:- Independent of γ (holds at γ=0.45 and γ=1.83)
```

## governance/MIGRATION_LEDGER.md

_matches: 1_

```
governance/MIGRATION_LEDGER.md:18:| neuron7x/TradePulse | kuramoto/tradepulse | IMPORTED | substrates/kuramoto/ integrated, golden data pending | operational reproducibility risk |
```

## manuscript/XFORM_MANUSCRIPT_DRAFT.md

_matches: 110_

```
manuscript/XFORM_MANUSCRIPT_DRAFT.md:1:# Universal gamma-scaling at the edge of metastability: evidence from three independent biological substrates with simulation validation
manuscript/XFORM_MANUSCRIPT_DRAFT.md:12:We report empirical evidence for a universal scaling exponent $\gamma \approx 1.0$ observed across three independent biological substrates with additional simulation validation. **Tier 1 — Evidential (real external data):** zebrafish morphogenesis ($\gamma = 1.055$, $n = 47$, CI: $[0.89, 1.20]$, McGuirl 2020), human heart rate variability ($\gamma \approx 0.95$, CI $\approx [0.83, 1.08]$, PhysioNet NSR2DB), and human EEG during motor imagery ($\gamma \approx 1.07$, $n = 20$ subjects, CI: $[0.88, 1.25]$, PhysioNet EEGBCI). **Tier 2 — Simulation-validated:** Gray-Scott reaction-diffusion ($\gamma = 0.938$), Kuramoto oscillators at $K_c$ ($\gamma = 0.980$), and BN-Syn spiking criticality ($\gamma \approx 0.49$, honest finite-size deviation from mean-field prediction). Cross-substrate mean from evidential substrates only: $\bar{\gamma}$ with 95% CI containing unity. All Tier 1 substrates pass surrogate testing ($p < 0.05$), and three negative controls (white noise, random walk, supercritical) show $\gamma$ clearly separated from unity. The BN-Syn finite-size result ($\gamma \approx 0.49$ for $N=200$, $k=10$) is consistent with theoretical predictions of finite-size corrections below the upper critical dimension, validating that $\gamma \approx 1.0$ in biological substrates is a genuine property rather than a methodological artifact. We propose that $\gamma \approx 1.0$ constitutes a topological signature of metastability -- the dynamical regime where complex systems maintain coherent computation at the boundary between order and disorder.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:18:Complex systems across vastly different substrates -- from biological tissues to neural networks to financial markets -- share a common dynamical feature: they operate most effectively near critical points, at the boundary between ordered and disordered phases [1,2]. This regime, termed *metastability*, is characterized by long-range correlations, power-law scaling, and the capacity for flexible reconfiguration [3].
manuscript/XFORM_MANUSCRIPT_DRAFT.md:22:We introduce a complementary diagnostic: the *gamma-scaling exponent* $\gamma$, defined through the power-law relation between topological complexity $C$ and thermodynamic cost $K$:
manuscript/XFORM_MANUSCRIPT_DRAFT.md:24:$$K \sim C^{-\gamma}$$
manuscript/XFORM_MANUSCRIPT_DRAFT.md:26:where $C$ is a measure of the system's structural or information complexity and $K$ is the energetic or computational cost per unit of complexity. We present evidence that $\gamma \approx 1.0$ across five independent substrates, suggesting it may represent a universal signature of metastable computation.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:28:The extended mind thesis [4] proposes that cognitive processes extend beyond the brain into the environment. We test this framework empirically by treating the human-AI interaction loop as a measurable physical system and showing that productive cognitive coupling exhibits the same $\gamma$-scaling as biological and physical substrates.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:36:For a system with topological complexity $C$ (measuring information richness, structural diversity, or phase-space dimensionality) and thermodynamic cost $K$ (measuring energy expenditure, computational effort, or dissipation per unit complexity), we define the gamma-scaling relation:
manuscript/XFORM_MANUSCRIPT_DRAFT.md:38:$$K = A \cdot C^{-\gamma}$$
manuscript/XFORM_MANUSCRIPT_DRAFT.md:42:$$\log K = -\gamma \log C + \log A$$
manuscript/XFORM_MANUSCRIPT_DRAFT.md:44:The exponent $\gamma$ characterizes the system's efficiency-complexity tradeoff:
manuscript/XFORM_MANUSCRIPT_DRAFT.md:45:- $\gamma > 1$: *over-determined* -- cost decreases faster than complexity increases (convergent regime)
manuscript/XFORM_MANUSCRIPT_DRAFT.md:46:- $\gamma < 1$: *under-determined* -- cost decreases slower than complexity increases (divergent regime)  
manuscript/XFORM_MANUSCRIPT_DRAFT.md:47:- $\gamma = 1$: *critical balance* -- cost and complexity scale inversely at unit rate (metastable regime)
manuscript/XFORM_MANUSCRIPT_DRAFT.md:51:The gamma-scaling exponent relates to established criticality measures:
manuscript/XFORM_MANUSCRIPT_DRAFT.md:53:- **Branching ratio** $\sigma$: In spiking networks, $\sigma \approx 1.0$ indicates criticality [2]. Our BN-Syn substrate measures $\gamma = 0.950$ when $\sigma$ is tuned to the critical regime.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:55:- **Kuramoto order parameter** $r$: In coupled oscillator systems, coherence $r \in [0,1]$ measures synchronization. Our market substrate computes $\gamma$ from Kuramoto coherence trajectories, yielding $\gamma = 1.081$.¹
manuscript/XFORM_MANUSCRIPT_DRAFT.md:57:¹ $\gamma = 1.081$ refers to the market Kuramoto substrate (financial coherence trajectories, illustrative, not in Table 1). $\gamma = 0.980$ in Table 2 refers to the simulated Kuramoto oscillators at critical coupling $K_c$. These are distinct substrates measuring the same dynamical quantity in different contexts.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:59:- **Spectral radius** $\rho$: The largest eigenvalue of the system's Jacobian. In the neosynaptex cross-domain integrator, $\rho \approx 1.0$ and $\gamma \approx 1.0$ co-occur in the METASTABLE phase.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:79:**Statement:** Truth is not inevitable — it is the result of independent verification between autonomous witnesses. Within the framework of H1, intelligence is defined as a dynamical regime verified through synchronous phase shifts ($\gamma$) across independent channels of a single substrate, with coherent recovery. The absence of such cross-scale and independent reproducibility means the observed effect is an artifact of measurement or modeling.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:84:$$\forall\, S_i \in \{\text{substrates at metastability}\}:\quad \gamma_{S_i} \in [0.85, 1.15] \quad (\text{95\% CI contains } 1.0)$$
manuscript/XFORM_MANUSCRIPT_DRAFT.md:86:**Verification criterion:** H1 is supported if $\gamma \in [0.85, 1.15]$ with 95% CI containing 1.0 across $N \geq 3$ independent substrates from distinct physical domains, each passing surrogate testing ($p < 0.05$).
manuscript/XFORM_MANUSCRIPT_DRAFT.md:89:1. Measure $\gamma$ across $\geq 3$ independent substrates from distinct physical domains using Theil-Sen regression with bootstrap CI
manuscript/XFORM_MANUSCRIPT_DRAFT.md:91:3. If $\bar{\gamma}$ across substrates deviates from 1.0 by more than 2 SE $\to$ H1 rejected
manuscript/XFORM_MANUSCRIPT_DRAFT.md:92:4. If negative controls also produce $\gamma \approx 1.0$ $\to$ methodology is not discriminative, H1 cannot be tested
manuscript/XFORM_MANUSCRIPT_DRAFT.md:94:**Status:** SUPPORTED — three independent biological substrates (zebrafish, HRV PhysioNet, EEG PhysioNet), cross-substrate CI from Tier 1 contains unity. All Tier 1 IAAFT p-values $< 0.05$. Three additional simulation substrates provide theoretical validation; BN-Syn finite-size deviation ($\gamma \approx 0.49$) confirms methodology is not trivially producing $\gamma \approx 1.0$.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:100:**Statement:** The regime $\gamma \approx 1$ corresponds to a state that maximizes computational capacity at minimal cost of plasticity maintenance. This is an open claim requiring separate experimental and theoretical verification.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:103:$$\mathcal{C}_E:\quad \gamma \approx 1 \Longleftrightarrow \text{local minimum of energy dissipation while preserving plasticity}$$
manuscript/XFORM_MANUSCRIPT_DRAFT.md:114:4. If transformer achieves $\gamma \approx 1.0$ endogenously $\to$ H2 weakened
manuscript/XFORM_MANUSCRIPT_DRAFT.md:115:5. If BN-Syn holds $\gamma \approx 1.0$ at lower $C$ for equivalent $E$ $\to$ H2 supported
manuscript/XFORM_MANUSCRIPT_DRAFT.md:118:$$\gamma_{\text{dendritic}} \approx 1 \;\land\; \gamma_{\text{network}} \approx 1 \;\land\; \Delta\beta_{\text{dendritic}}(t) \sim \Delta\beta_{\text{network}}(t)$$
manuscript/XFORM_MANUSCRIPT_DRAFT.md:120:If dendritic-level $\gamma$ is indistinguishable from noise $\to$ compartmental model adds no explanatory power.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:131:- $\gamma_{\text{dendritic}}$ (compartment level)
manuscript/XFORM_MANUSCRIPT_DRAFT.md:132:- $\gamma_{\text{network}}$ (population level)
manuscript/XFORM_MANUSCRIPT_DRAFT.md:136:1. $\gamma_{\text{dendritic}}$ is stably measurable
manuscript/XFORM_MANUSCRIPT_DRAFT.md:138:3. Is not trivially identical to $\gamma_{\text{network}}$
manuscript/XFORM_MANUSCRIPT_DRAFT.md:141:**Fail-closed STOP:** If $\gamma_{\text{dendritic}} \approx \text{noise}$ $\to$ dendritic compartments are rejected. Scaling to main is FORBIDDEN until proof.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:145:### 2.5 Theoretical basis: $\gamma = 1.0$ in mean-field criticality
manuscript/XFORM_MANUSCRIPT_DRAFT.md:147:The result $\gamma = 1.0$ is not merely empirical but follows from mean-field theory of critical phenomena in multiple universality classes.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:149:**Branching process at $\sigma = 1$.** In a critical branching process, each event generates on average $\sigma = 1$ successor. The cost of propagating one unit of topological information is exactly one unit of energy [Harris, 1963]. This gives $K = C^{-1}$ directly, yielding $\gamma = 1$.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:151:**Self-organized criticality.** In the mean-field BTW sandpile [Bak, Tang & Wiesenfeld, 1987], avalanche size $S$ and duration $T$ satisfy $\langle S \rangle \sim T^{d_f/d}$. In mean-field ($d \geq d_c$), $d_f = d$, giving $\langle S \rangle \sim T^1$. The cost-complexity ratio $K/C \sim S/T = \text{const}$, yielding $\gamma = 1$.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:153:**Directed percolation universality.** Neural criticality belongs to the directed percolation universality class [Munoz et al., 1999; Beggs & Plenz, 2003]. In mean-field DP, the branching ratio $\sigma = 1$ at the critical point, and $\tau = 3/2$ (avalanche size exponent). The scaling relation $\gamma = (\tau_T - 1)/(\tau_S - 1)$ evaluates to exactly 1.0 in mean field.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:155:**Finite-size corrections.** Below the upper critical dimension $d_c$, corrections of order $\varepsilon = d_c - d$ appear, pushing $\gamma$ away from 1.0. Our BN-Syn simulation ($N=200$ neurons, $k=10$ sparse connectivity) yields $\gamma \approx 0.49$, consistent with finite-size deviations from the mean-field prediction. The observed $\gamma < 1$ in sparse networks confirms that the $\gamma \approx 1.0$ signature in biological substrates is a genuine property of those systems, not an artifact of the methodology.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:157:**Spectral connection.** At SOC, the power spectral density follows $S(f) \sim f^{-\beta}$ with $\beta = 1$ (1/f noise) [Bak et al., 1987]. The spectral exponent $\beta$ is related to the Hurst exponent $H$ via $\beta = 2H + 1$ (for fractional Brownian motion), giving $H = 0$ at criticality. In the HRV VLF range and EEG aperiodic component, $\beta \approx 1.0$ during healthy/active states corresponds to $\gamma_{\text{PSD}} \approx 1.0$, consistent with the topo-cost framework.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:167:**Note on fitting method.** We fit a deterministic scaling relation $K = A \cdot C^{-\gamma}$ in log-log space, not a power-law probability distribution. For scaling relations between two measured quantities, Theil-Sen regression on $(\log C, \log K)$ pairs is the appropriate estimator (robust to outliers, no distributional assumption on $K$). The maximum-likelihood framework of Clauset, Shalizi & Newman [14] applies to probability distributions $P(x) \sim x^{-\alpha}$; it is not applicable to scaling relations between paired observables.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:171:Bootstrap confidence intervals are computed by resampling with replacement ($B = 500$ iterations) and taking the 2.5th and 97.5th percentiles of the bootstrap distribution of $\gamma$.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:175:We apply three gates before accepting a $\gamma$ estimate:
manuscript/XFORM_MANUSCRIPT_DRAFT.md:182:A critical methodological point: the power spectral density $S(f) \sim f^{-\gamma}$ IS a topo-cost relationship. In this temporal formulation:
manuscript/XFORM_MANUSCRIPT_DRAFT.md:187:The scaling relation $S(f) = A \cdot f^{-\gamma}$ has exactly the form $K = A \cdot C^{-\gamma}$ from §2.1, where $C = f$ and $K = S(f)$. The $\gamma$ exponent extracted from the PSD via `compute_gamma(freqs, PSD)` is therefore the same quantity as the $\gamma$ extracted from spatial topo-cost pairs in the zebrafish substrate.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:189:This unification follows from the fluctuation-dissipation theorem: at thermodynamic equilibrium (and at critical points where generalized FDT holds), the spectral density of fluctuations is proportional to the system's dissipative response. At criticality, both spatial and temporal complexity-cost relationships converge to $\gamma \approx 1.0$.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:194:- **Dynamical topo-cost:** Kuramoto (volatility → 1/|returns|), BN-Syn (rate → rate CV)
manuscript/XFORM_MANUSCRIPT_DRAFT.md:196:All pass through the same `compute_gamma()` function: Theil-Sen regression on $(\log C, \log K)$ with bootstrap CI.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:200:To verify that observed $\gamma$ values are not artifacts of sample structure (e.g., autocorrelation or finite-size effects), we employ IAAFT (Iterative Amplitude Adjusted Fourier Transform) surrogates [Schreiber & Schmitz, 1996]. For each substrate, we generate $M = 199$ surrogates of the topological complexity time series. Each surrogate preserves the amplitude distribution and power spectrum of the original series but destroys the specific temporal ordering. We recompute $\gamma$ on each surrogate and calculate a two-tailed p-value: $p = (1 + \#\{|\gamma_{\text{null}}| \geq |\gamma_{\text{obs}}|\}) / (M + 1)$.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:204:To demonstrate that $\gamma \approx 1.0$ is not a trivial outcome of the methodology, we compute $\gamma$ for four classes of systems that should NOT exhibit metastable scaling:
manuscript/XFORM_MANUSCRIPT_DRAFT.md:210:If the methodology correctly detects $\gamma \approx 1.0$ only at criticality, these controls should all yield $\gamma$ far from unity or fail quality gates.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:218:| Substrate | $\gamma$ | 95% CI | $n$ | $R^2$ | IAAFT $p$ | $\log C$ range | Cutoff method | Verdict |
manuscript/XFORM_MANUSCRIPT_DRAFT.md:224:**Table 1.** Tier 1 evidential substrates. Cross-substrate mean: $\bar{\gamma} = 1.003 \pm 0.083$. $\log C$ range = natural log of topological complexity variable (see §3.4 for variable definitions). Cutoff method = how the lower bound of the fitting range was determined. *EEG $R^2$ is not applicable: $\gamma$ is computed as the per-subject mean aperiodic spectral exponent via specparam (Donoghue et al., 2020), not from log-log regression of topo-cost pairs. HRV uses VLF-range PSD of RR intervals (Peng et al., 1995). All substrates pass the quality gate $\text{range}(\log C) \geq 0.5$. Lower bound per data point: $C > 10^{-6}$ (numerical floor).
manuscript/XFORM_MANUSCRIPT_DRAFT.md:226:**DFA cross-validation (HRV).** As independent verification, we compute Detrended Fluctuation Analysis on the same RR interval series. DFA exponent $\alpha = 1.107 \pm 0.047$ ($n = 10$ subjects, range $[1.04, 1.18]$), confirming 1/f scaling. For stationary processes, $\alpha = (1 + \beta)/2$ where $\beta$ is the PSD spectral exponent; $\alpha \approx 1.1$ corresponds to $\beta \approx 1.2$, consistent with our PSD-based $\gamma = 0.885$ (the discrepancy reflects the different spectral windows used in Welch vs. DFA).
manuscript/XFORM_MANUSCRIPT_DRAFT.md:228:**Alternative model comparison.** For each Tier 1 substrate, we compare the power-law scaling model ($K = A \cdot C^{-\gamma}$, linear in log-log space) against lognormal (quadratic in log-log) and exponential ($K = A \cdot e^{-\lambda C}$) alternatives using AIC. Zebrafish: power-law preferred over lognormal ($\Delta\text{AIC} = +1.2$) and exponential ($\Delta\text{AIC} = +60.9$). HRV: power-law preferred over lognormal ($\Delta\text{AIC} = +1.5$) and exponential ($\Delta\text{AIC} = +29.7$). EEG: lognormal preferred ($\Delta\text{AIC} = -76.4$) on the full 2–35 Hz PSD, consistent with the spectral knee. Note: this AIC comparison applies to the full broad-band PSD; $\gamma$ for EEG is extracted from the aperiodic component only via specparam, which fits the $1/f$ region after removing the spectral knee — a non-overlapping analysis. Full results in `evidence/alternative_model_tests.json`.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:232:| Substrate | $\gamma$ | 95% CI | $n$ | $R^2$ | Note |
manuscript/XFORM_MANUSCRIPT_DRAFT.md:235:| Kuramoto oscillators ($K = K_c$) | 0.980 | [0.93, 1.01] | 300 | 0.42 | At critical coupling |
manuscript/XFORM_MANUSCRIPT_DRAFT.md:238:**Table 2.** Tier 2 simulation substrates. Gray-Scott and Kuramoto yield $\gamma$ near 1.0, consistent with mean-field predictions. BN-Syn ($N=200$ neurons, $k=10$) yields $\gamma \approx 0.49$, a finite-size deviation from the mean-field $\gamma = 1.0$ prediction, consistent with theoretical expectations below $d_c$ (§2.5). These substrates validate the methodology but are NOT counted toward the universality claim.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:242:| Substrate | $\gamma$ | SE | $|\gamma - 1|$ | MDE (80%) | Cohen's $d$ (vs $\gamma=0$) |
manuscript/XFORM_MANUSCRIPT_DRAFT.md:248:**Table 3.** Statistical power analysis. All substrates have Cohen's $d > 11$ (vs null $\gamma = 0$), indicating overwhelming evidence for non-zero scaling. Minimum detectable effect (MDE) at 80% power ranges from 0.18 to 0.26, meaning each substrate can reliably distinguish $\gamma = 1.0$ from $\gamma > 1.2$. Cross-substrate: $\bar{\gamma} = 1.003$, $t(2) = 0.06$ (two-sided $p > 0.9$ for $H_0: \gamma = 1.0$), confirming the mean is statistically indistinguishable from unity.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:252:| Substrate | $\gamma$ | 95% CI | $n$ | $R^2$ | CI contains 1.0 | Reason for exclusion |
manuscript/XFORM_MANUSCRIPT_DRAFT.md:258:**Table 2.** Illustrative substrates excluded from the core universality claim. Neosynaptex cross-domain is an aggregate of other substrates and therefore not independent. CNS-AI productivity classification was performed by the measured subject (single operator), introducing self-report bias; R2 values are catastrophically low, indicating the power-law model is a poor fit at the session level.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:264:$$\gamma_{\text{all}} = 1.059, \quad \text{CI} = [0.985, 1.131], \quad n = 8{,}271$$
manuscript/XFORM_MANUSCRIPT_DRAFT.md:266:The 95% confidence interval contains $\gamma = 1.0$.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:272:- $\gamma_{\text{productive}} = 1.138$, $|\gamma - 1| = 0.138$
manuscript/XFORM_MANUSCRIPT_DRAFT.md:273:- $\gamma_{\text{non-productive}} = -0.557$, $|\gamma - 1| = 1.557$
manuscript/XFORM_MANUSCRIPT_DRAFT.md:274:- $\Delta\gamma = 1.695$
manuscript/XFORM_MANUSCRIPT_DRAFT.md:280:| Type | $\gamma$ | 95% CI | $n$ |
manuscript/XFORM_MANUSCRIPT_DRAFT.md:291:| Control | $\gamma$ | $R^2$ | Verdict | Separated from $\gamma=1.0$ |
manuscript/XFORM_MANUSCRIPT_DRAFT.md:297:**Table 3.** Negative controls confirm that $\gamma \approx 1.0$ does not arise trivially from the methodology. Systems without critical dynamics show $\gamma$ clearly separated from unity, demonstrating falsifiability.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:301:To confirm that $\gamma \approx 1.0$ reflects causal dynamical structure rather than marginal distributional properties, we performed random pairing shuffles: for each Tier 1 substrate, we permuted the cost vector independently ($M = 199$ permutations), destroying the $C \leftrightarrow K$ correspondence while preserving both marginal distributions. In all three substrates, the shuffled $\gamma$ distribution collapsed to near-zero (median $|\gamma_{\text{shuffled}}| < 0.08$), while $\gamma_{\text{real}}$ remained closer to unity than any shuffled realization. This confirms that the scaling relationship is a property of the paired dynamical structure, not an artifact of the individual distributions of $C$ or $K$.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:303:| Substrate | $\gamma_{\text{real}}$ | $\gamma_{\text{shuffled}}$ (median) | Shuffled 95% CI | Separated |
manuscript/XFORM_MANUSCRIPT_DRAFT.md:311:To address variable selection bias, we tested 2 alternative $(C, K)$ proxy pairs per substrate. For zebrafish: population count vs NN_CV ($\gamma = 0.46$) and density vs 1/population ($\gamma = 2.29$). For HRV: LF band PSD (insufficient data) and full-band PSD ($\gamma = 0.89$, in band). For EEG: 8-30 Hz PSD ($\gamma = 0.57$) and 2-12 Hz PSD ($\gamma = 0.98$, in band). Result: 2/6 alternatives produced $\gamma$ in the metastable band. This confirms that $\gamma \approx 1.0$ is **not** a generic property of any complexity-cost pairing — it is specific to the theoretically motivated variable definitions (§3.4). The combination of proxy specificity (most alternatives fail) and shuffle sensitivity (destroying pairing kills the scaling) constitutes strong evidence against variable selection bias.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:315:**Figure 1** (manuscript/figures/fig1_substrates.pdf): Six-panel log-log scatter plots (2 rows x 3 columns) showing the topo-cost scaling relationship for each substrate. Row 1 (green, Tier 1 Evidential): zebrafish morphogenesis, HRV PhysioNet, EEG PhysioNet. Row 2 (blue, Tier 2 Simulation): Gray-Scott reaction-diffusion, Kuramoto oscillators, BN-Syn spiking criticality. Red lines: Theil-Sen robust regression fits. Each panel displays $\gamma$ and 95% CI.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:317:**Figure 2** (manuscript/figures/fig2_convergence.pdf): Cross-substrate $\gamma$ convergence by tier. Bar chart with 95% CI error bars. Green bars: Tier 1 evidential substrates. Blue bars: Tier 2 simulation substrates. Dashed line: $\gamma = 1.0$ reference.
manuscript/XFORM_MANUSCRIPT_DRAFT.md:319:**Figure 3** (manuscript/figures/fig3_controls.pdf): Negative control $\gamma$ values. Shaded band: metastable zone $[0.85, 1.15]$. All controls fall outside the metastable band, confirming falsifiability of the $\gamma \approx 1.0$ claim.
... [30 more lines omitted; see audit/pre_closure_scan.txt]
```

## manuscript/arxiv_submission.tex

_matches: 76_

```
manuscript/arxiv_submission.tex:50:\fancyhead[C]{\footnotesize\itshape\color{dimgray} Universal $\gamma$-scaling at the edge of metastability}
manuscript/arxiv_submission.tex:76:\title{\LARGE\bfseries Universal $\gamma$-scaling at the edge of metastability: evidence from three independent biological substrates with simulation validation}
manuscript/arxiv_submission.tex:85:\noindent We report empirical evidence for a universal scaling exponent $\gamma \approx 1.0$ observed across three independent biological substrates with additional simulation validation.
manuscript/arxiv_submission.tex:86:\textbf{Tier~1 --- Evidential (real external data):} zebrafish morphogenesis ($\gamma = 1.055$, $n = 47$, CI: [0.89, 1.20], McGuirl 2020), human heart rate variability ($\gamma = 0.885$, CI: [0.83, 1.08], PhysioNet NSR2DB), and human EEG during motor imagery ($\gamma \approx 1.07$, $n = 20$ subjects, CI: [0.88, 1.25], PhysioNet EEGBCI).
manuscript/arxiv_submission.tex:87:\textbf{Tier~2 --- Simulation-validated:} Gray--Scott reaction-diffusion ($\gamma = 0.938$), Kuramoto oscillators at $K_c$ ($\gamma = 0.980$), and BN-Syn spiking criticality ($\gamma \approx 0.49$, honest finite-size deviation from mean-field prediction).
manuscript/arxiv_submission.tex:88:Cross-substrate mean from evidential substrates only: $\bar{\gamma}$ with 95\% CI containing unity.
manuscript/arxiv_submission.tex:89:All Tier~1 substrates pass surrogate testing ($p < 0.05$), and three negative controls (white noise, random walk, supercritical) show $\gamma$ clearly separated from unity.
manuscript/arxiv_submission.tex:90:The BN-Syn finite-size result ($\gamma \approx 0.49$ for $N=200$, $k=10$) is consistent with theoretical predictions of finite-size corrections below the upper critical dimension, validating that $\gamma \approx 1.0$ in biological substrates is a genuine property rather than a methodological artifact.
manuscript/arxiv_submission.tex:91:We propose that $\gamma \approx 1.0$ constitutes a scaling signature of metastability --- the dynamical regime where complex systems maintain coherent computation at the boundary between order and disorder.
manuscript/arxiv_submission.tex:101:Complex systems across vastly different substrates --- from biological tissues to neural networks to financial markets --- share a common dynamical feature: they operate most effectively near critical points, at the boundary between ordered and disordered phases~\cite{bak1987,beggs2003}. This regime, termed \emph{metastability}, is characterized by long-range correlations, power-law scaling, and the capacity for flexible reconfiguration~\cite{maass2002}.
manuscript/arxiv_submission.tex:105:We introduce a complementary diagnostic: the \emph{gamma-scaling exponent} $\gamma$, defined through the power-law relation between topological complexity $C$ and thermodynamic cost $K$:
manuscript/arxiv_submission.tex:107:K \sim C^{-\gamma}
manuscript/arxiv_submission.tex:109:where $C$ is a measure of the system's structural or information complexity and $K$ is the energetic or computational cost per unit of complexity. We present evidence that $\gamma \approx 1.0$ across five independent substrates, suggesting it may represent a universal signature of metastable computation.
manuscript/arxiv_submission.tex:111:The extended mind thesis~\cite{clark1998} proposes that cognitive processes extend beyond the brain into the environment. We test this framework empirically by treating the human--AI interaction loop as a measurable physical system and showing that productive cognitive coupling exhibits the same $\gamma$-scaling as biological and physical substrates.
manuscript/arxiv_submission.tex:118:For a system with topological complexity $C$ (measuring information richness, structural diversity, or phase-space dimensionality) and thermodynamic cost $K$ (measuring energy expenditure, computational effort, or dissipation per unit complexity), we define the gamma-scaling relation:
manuscript/arxiv_submission.tex:120:K = A \cdot C^{-\gamma}
manuscript/arxiv_submission.tex:125:\log K = -\gamma \log C + \log A
manuscript/arxiv_submission.tex:128:The exponent $\gamma$ characterizes the system's efficiency-complexity tradeoff:
manuscript/arxiv_submission.tex:130:\item $\gamma > 1$: \emph{over-determined} --- cost decreases faster than complexity increases (convergent regime)
manuscript/arxiv_submission.tex:131:\item $\gamma < 1$: \emph{under-determined} --- cost decreases slower than complexity increases (divergent regime)
manuscript/arxiv_submission.tex:132:\item $\gamma = 1$: \emph{critical balance} --- cost and complexity scale inversely at unit rate (metastable regime)
manuscript/arxiv_submission.tex:137:The gamma-scaling exponent relates to established criticality measures:
manuscript/arxiv_submission.tex:139:\item \textbf{Branching ratio} $\sigma$: In spiking networks, $\sigma \approx 1.0$ indicates criticality~\cite{beggs2003}. Our BN-Syn substrate measures $\gamma = 0.950$ when $\sigma$ is tuned to the critical regime.
manuscript/arxiv_submission.tex:140:\item \textbf{Kuramoto order parameter} $r$: In coupled oscillator systems, coherence $r \in [0,1]$ measures synchronization. Our market substrate computes $\gamma$ from Kuramoto coherence trajectories, yielding $\gamma = 1.081$.\footnote{$\gamma = 1.081$ refers to the market Kuramoto substrate (financial coherence trajectories, illustrative). $\gamma = 0.980$ in Table~1 refers to simulated Kuramoto oscillators at critical coupling $K_c$. These are distinct substrates.}
manuscript/arxiv_submission.tex:141:\item \textbf{Spectral radius} $\rho$: The largest eigenvalue of the system's Jacobian. In the neosynaptex cross-domain integrator, $\rho \approx 1.0$ and $\gamma \approx 1.0$ co-occur in the METASTABLE phase.
manuscript/arxiv_submission.tex:160:\textbf{Statement:} Truth is not inevitable --- it is the result of independent verification between autonomous witnesses. Within the framework of H1, intelligence is defined as a dynamical regime verified through synchronous phase shifts ($\gamma$) across independent channels of a single substrate, with coherent recovery.
manuscript/arxiv_submission.tex:164:\forall\, S_i \in \{\text{substrates at metastability}\}:\; \gamma_{S_i} \in [0.85, 1.15]
manuscript/arxiv_submission.tex:168:\textbf{Verification criterion:} H1 is supported if $\gamma \in [0.85, 1.15]$ with 95\% CI containing 1.0 across $N \geq 3$ independent substrates from distinct physical domains, each passing surrogate testing ($p < 0.05$).
manuscript/arxiv_submission.tex:170:\textbf{Status: SUPPORTED} --- three independent biological substrates (zebrafish, HRV PhysioNet, EEG PhysioNet), cross-substrate CI from Tier~1 contains unity. All Tier~1 IAAFT $p$-values $< 0.05$. BN-Syn finite-size deviation ($\gamma \approx 0.49$) confirms methodology is not trivially producing $\gamma \approx 1.0$.
manuscript/arxiv_submission.tex:174:\textbf{Statement:} The regime $\gamma \approx 1$ corresponds to a state that maximizes computational capacity at minimal cost of plasticity maintenance. This is an open claim requiring separate experimental and theoretical verification.
manuscript/arxiv_submission.tex:178:\mathcal{C}_E:\quad \gamma \approx 1 \Longleftrightarrow \text{local min of dissipation preserving plasticity}
manuscript/arxiv_submission.tex:183:\subsection{Theoretical basis: $\gamma = 1.0$ in mean-field criticality}
manuscript/arxiv_submission.tex:185:The result $\gamma = 1.0$ follows from mean-field theory of critical phenomena in multiple universality classes.
manuscript/arxiv_submission.tex:187:\textbf{Branching process at $\sigma = 1$.} In a critical branching process, each event generates on average $\sigma = 1$ successor. The cost of propagating one unit of topological information is exactly one unit of energy~\cite{harris1963}. This gives $K = C^{-1}$ directly, yielding $\gamma = 1$.
manuscript/arxiv_submission.tex:189:\textbf{Self-organized criticality.} In the mean-field BTW sandpile~\cite{bak1987}, avalanche size $S$ and duration $T$ satisfy $\langle S \rangle \sim T^{d_f/d}$. In mean-field ($d \geq d_c$), $d_f = d$, giving $\langle S \rangle \sim T^1$. The cost-complexity ratio $K/C \sim S/T = \text{const}$, yielding $\gamma = 1$.
manuscript/arxiv_submission.tex:191:\textbf{Directed percolation universality.} Neural criticality belongs to the directed percolation universality class~\cite{munoz1999,beggs2003}. In mean-field DP, the branching ratio $\sigma = 1$ at the critical point, and $\tau = 3/2$ (avalanche size exponent). The scaling relation $\gamma = (\tau_T - 1)/(\tau_S - 1)$ evaluates to exactly $1.0$ in mean field.
manuscript/arxiv_submission.tex:193:\textbf{Finite-size corrections.} Below the upper critical dimension $d_c$, corrections of order $\varepsilon = d_c - d$ appear, pushing $\gamma$ away from $1.0$. Our BN-Syn simulation ($N\!=\!200$ neurons, $k\!=\!10$ sparse connectivity) yields $\gamma \approx 0.49$, consistent with finite-size deviations from the mean-field prediction.
manuscript/arxiv_submission.tex:195:\textbf{Spectral connection.} At SOC, the power spectral density follows $S(f) \sim f^{-\beta}$ with $\beta = 1$ ($1/f$ noise)~\cite{bak1987}. The spectral exponent $\beta$ is related to the Hurst exponent $H$ via $\beta = 2H + 1$ (for fractional Brownian motion), giving $H = 0$ at criticality. In the HRV VLF range and EEG aperiodic component, $\beta \approx 1.0$ during healthy/active states corresponds to $\gamma_{\text{PSD}} \approx 1.0$, consistent with the topo-cost framework.
manuscript/arxiv_submission.tex:204:\textbf{Note on fitting method.} We fit a deterministic scaling relation $K = A \cdot C^{-\gamma}$ in log-log space, not a power-law probability distribution. For scaling relations between two measured quantities, Theil--Sen regression on $(\log C, \log K)$ pairs is the appropriate estimator. The MLE framework of Clauset, Shalizi \& Newman~\cite{clauset2009} applies to probability distributions $P(x) \sim x^{-\alpha}$; it is not applicable to scaling relations between paired observables.
manuscript/arxiv_submission.tex:208:Bootstrap confidence intervals are computed by resampling with replacement ($B = 500$ iterations) and taking the 2.5th and 97.5th percentiles of the bootstrap distribution of $\gamma$.
manuscript/arxiv_submission.tex:212:We apply three gates before accepting a $\gamma$ estimate:
manuscript/arxiv_submission.tex:221:A critical methodological point: the power spectral density $S(f) \sim f^{-\gamma}$ IS a topo-cost relationship. In this temporal formulation:
manuscript/arxiv_submission.tex:227:The scaling relation $S(f) = A \cdot f^{-\gamma}$ has exactly the form $K = A \cdot C^{-\gamma}$ from \S2.1, where $C = f$ and $K = S(f)$.
manuscript/arxiv_submission.tex:231:To verify that observed $\gamma$ values are not artifacts of sample structure, we employ IAAFT (Iterative Amplitude Adjusted Fourier Transform) surrogates. For each substrate, we generate $M = 199$ surrogates preserving the amplitude distribution and power spectrum but destroying temporal ordering. We compute a two-tailed $p$-value:
manuscript/arxiv_submission.tex:233:p = \frac{1 + \#\{|\gamma_{\text{null}}| \geq |\gamma_{\text{obs}}|\}}{M + 1}
manuscript/arxiv_submission.tex:238:To demonstrate that $\gamma \approx 1.0$ is not a trivial outcome of the methodology, we compute $\gamma$ for four classes of systems that should NOT exhibit metastable scaling:
manuscript/arxiv_submission.tex:251:Table~\ref{tab:all_substrates} summarizes $\gamma$-scaling across all substrates. All three Tier~1 substrates fall within the metastable band ($|\gamma - 1| < 0.15$) with cross-substrate mean $\bar{\gamma} = 1.003 \pm 0.083$.
manuscript/arxiv_submission.tex:253:\textbf{DFA cross-validation (HRV).} DFA exponent $\alpha = 1.107 \pm 0.047$ ($n = 10$ subjects, range $[1.04, 1.18]$), confirming $1/f$ scaling. For stationary processes, $\alpha = (1 + \beta)/2$; $\alpha \approx 1.1$ corresponds to $\beta \approx 1.2$, consistent with our PSD-based $\gamma = 0.885$.
manuscript/arxiv_submission.tex:257:Gray--Scott and Kuramoto yield $\gamma$ near 1.0, consistent with mean-field predictions (Table~\ref{tab:all_substrates}). BN-Syn ($N\!=\!200$, $k\!=\!10$) yields $\gamma \approx 0.49$, a finite-size deviation confirming the methodology does not trivially produce $\gamma \approx 1.0$.
manuscript/arxiv_submission.tex:259:\textbf{Alternative model comparison.} For each Tier~1 substrate, we compare the power-law scaling model against lognormal (quadratic in log-log) and exponential ($K = A e^{-\lambda C}$) alternatives using AIC. Zebrafish: power-law preferred ($\Delta\text{AIC}_{\text{ln}} = +1.2$, $\Delta\text{AIC}_{\text{exp}} = +60.9$). HRV: power-law preferred ($\Delta\text{AIC}_{\text{ln}} = +1.5$, $\Delta\text{AIC}_{\text{exp}} = +29.7$). EEG: lognormal preferred ($\Delta\text{AIC} = -76.4$) on the full 2--35~Hz PSD, consistent with the spectral knee. Note: this AIC comparison applies to the full broad-band PSD; $\gamma$ for EEG is extracted from the aperiodic component only via specparam, which fits the $1/f$ region after removing the spectral knee --- a non-overlapping analysis.
manuscript/arxiv_submission.tex:263:All Tier~1 substrates have Cohen's $d > 11$ (vs null $\gamma = 0$), indicating overwhelming evidence for non-zero scaling. Cross-substrate: $\bar{\gamma} = 1.003$, $t(2) = 0.06$, $p > 0.9$ for $H_0\!: \gamma = 1.0$ (Table~\ref{tab:power_controls}).
manuscript/arxiv_submission.tex:265:\textbf{Power caveat.} The zebrafish substrate ($n = 47$) has CI width $\sim$0.41 and MDE of $\Delta\gamma = 0.35$ at 80\% power. This means values in the range $\gamma \in [0.70, 1.35]$ cannot be reliably distinguished from $\gamma = 1.0$ with this sample size. The convergence of three independent substrates to the metastable band mitigates this limitation, but replication with larger $n$ is needed to narrow the individual CIs.
manuscript/arxiv_submission.tex:269:Systems without critical dynamics show $\gamma$ clearly separated from unity (Table~\ref{tab:power_controls}), confirming falsifiability.
manuscript/arxiv_submission.tex:278:\caption{Topo-cost scaling across six substrates. \emph{Row~1} (Tier~1, evidential): zebrafish morphogenesis, HRV PhysioNet, EEG PhysioNet. \emph{Row~2} (Tier~2, simulation): Gray--Scott, Kuramoto, BN-Syn. Red lines: Theil--Sen robust regression. Each panel shows $\gamma$ and 95\% CI.}
manuscript/arxiv_submission.tex:285:\caption{Cross-substrate $\gamma$ convergence by tier. Green: Tier~1 (evidential). Blue: Tier~2 (simulation). Dashed line: $\gamma = 1.0$ reference. Error bars: 95\% bootstrap CI. Note: overlapping CIs across Tier~1 substrates are consistent with the hypothesis that all share a common $\gamma \approx 1.0$; the wide individual CIs reflect small per-substrate $n$.}
manuscript/arxiv_submission.tex:292:\caption{Negative controls. Shaded band: metastable zone $[0.85, 1.15]$. All controls fall outside, confirming falsifiability of the $\gamma \approx 1.0$ claim.}
manuscript/arxiv_submission.tex:298:\caption{Gamma-scaling across all substrates. Tier~1 (evidential, real external data) and Tier~2 (simulation-validated). Cross-substrate mean from Tier~1: $\bar{\gamma} = 1.003 \pm 0.083$, 95\% CI containing unity. $^\dagger$EEG $R^2$ is not applicable: $\gamma$ is computed as the per-subject mean aperiodic spectral exponent via specparam, not from log-log regression of topo-cost pairs.}
manuscript/arxiv_submission.tex:303:\textbf{Tier} & \textbf{Substrate} & $\gamma$ & \textbf{95\% CI} & $n$ & $R^2$ & \textbf{IAAFT} $p$ & $\ln C$ range \\
manuscript/arxiv_submission.tex:310:2 & Kuramoto oscillators ($K_c$) & 0.980 & [0.93, 1.01] & 300 & 0.42 & --- & --- \\
manuscript/arxiv_submission.tex:318:\caption{Statistical power (Tier~1 substrates) and negative controls. Left: all substrates have Cohen's $d > 11$. Right: all controls show $\gamma$ clearly separated from unity.}
manuscript/arxiv_submission.tex:326:\textbf{Substrate} & $\gamma$ & SE & $|\gamma\!-\!1|$ & MDE & $d$ \\
manuscript/arxiv_submission.tex:340:\textbf{Control} & $\gamma$ & $R^2$ & \textbf{Verdict} & $\Delta$ \\
manuscript/arxiv_submission.tex:353:\subsection{Universality of gamma}
manuscript/arxiv_submission.tex:355:Three independent biological substrates --- zebrafish morphogenesis, human cardiac rhythm, and human EEG during motor imagery --- all yield $\gamma$ values within the metastable band ($|\gamma - 1| < 0.15$). Each substrate independently passes IAAFT surrogate testing ($p < 0.05$), confirming that the observed $\gamma$ values are not artifacts of autocorrelation or spectral structure. The cross-substrate mean $\bar{\gamma} = 1.003$ with $t(2) = 0.06$ ($p > 0.9$ for $H_0\!: \gamma = 1.0$) is statistically indistinguishable from unity.
manuscript/arxiv_submission.tex:357:The cross-substrate mean has a 95\% CI containing unity. Two simulation substrates (Gray--Scott, Kuramoto) further corroborate the $\gamma \approx 1.0$ prediction at criticality. Critically, the BN-Syn spiking network ($N\!=\!200$, $k\!=\!10$, $\sigma\!=\!1$) yields $\gamma \approx 0.49$ --- an honest finite-size deviation from the mean-field prediction.
manuscript/arxiv_submission.tex:361:We speculate that the $\gamma \approx 1.0$ signature may distinguish phase-dynamic systems (which encode information in spike timing and phase coherence) from rate-based architectures (which encode in activation magnitudes). Transformer architectures achieve remarkable performance through parameter scaling~\cite{vaswani2017}, but operate within a rate-based paradigm. Whether rate-based systems can endogenously achieve $\gamma \approx 1.0$ remains an open empirical question not addressed by the data in this paper.
manuscript/arxiv_submission.tex:365:Why should the Hurst exponent $H$ in zebrafish morphogenesis and $H$ in financial markets produce the same $\gamma \approx 1.0$? The answer lies in universality class:
manuscript/arxiv_submission.tex:368:\item \textbf{SOC.} Systems that self-tune to the edge of instability generically produce $1/f$ noise ($\beta \approx 1$, $H \approx 0$, $\gamma \approx 1$).
manuscript/arxiv_submission.tex:369:\item \textbf{RG universality.} Critical exponents depend only on symmetry and spatial dimension, not microscopic details.
manuscript/arxiv_submission.tex:370:\item \textbf{Fluctuation-dissipation connection.} $\gamma = -d(\log K)/d(\log C)$ is constrained by the FDT at criticality.
manuscript/arxiv_submission.tex:375:The human--AI cognitive loop data extends the scaling relation into cognition, with critical caveats. The aggregate $\gamma_{\text{all}} = 1.059$ (CI containing 1.0) is suggestive but not evidential: the productivity classification was performed by the measured subject, introducing self-report bias, and per-session $R^2 = 0.12$.
manuscript/arxiv_submission.tex:379:Following Clark and Chalmers~\cite{clark1998}, one may speculatively interpret human--AI cognitive coupling as a dynamical system amenable to $\gamma$-scaling analysis. Whether such coupling exhibits measurable criticality signatures remains an open question requiring independent replication with blind labeling (see Limitations).
manuscript/arxiv_submission.tex:391:\item \textbf{Statistical power at small $n$}: Zebrafish ($n = 47$) has CI width $\sim$0.41 with MDE of $\Delta\gamma = 0.35$ at 80\% power.
manuscript/arxiv_submission.tex:403:We present empirical evidence that a scaling exponent $\gamma \approx 1.0$ appears across three independent biological substrates: zebrafish morphogenesis ($\gamma = 1.055$), human cardiac rhythm ($\gamma = 0.885$), and human EEG during motor imagery ($\gamma \approx 1.07$). All three evidential substrates fall within the metastable band ($|\gamma - 1| < 0.15$), with cross-substrate 95\% CI containing unity. All pass surrogate testing ($p < 0.05$). Three simulation substrates provide theoretical validation: Gray--Scott ($\gamma = 0.938$) and Kuramoto ($\gamma = 0.980$) confirm $\gamma \approx 1.0$ at criticality, while BN-Syn ($\gamma \approx 0.49$, $N\!=\!200$) demonstrates the expected finite-size deviation.
manuscript/arxiv_submission.tex:405:We propose that $\gamma \approx 1.0$ is a scaling signature of metastability in substrates that already operate in a moderate-topological-variability regime --- a \textbf{substrate-specific candidate condition} for coherent computation at the edge of chaos, not a substrate-independent universal. Substrate-independence was empirically contradicted by the 2026-04-14 HRV n=5 pilot ($\gamma$ mean $0.50 \pm 0.44$ across subjects). If confirmed by independent replication within each substrate, this finding may still have implications for AI alignment (productive coupling has a measurable signature), cognitive enhancement ($\gamma$ as a real-time, per-substrate-calibrated diagnostic), and the physics of intelligence (metastability as a per-substrate regime marker rather than a universal law).
manuscript/arxiv_submission.tex:410:All code, data processing pipelines, and proof bundles are available at \url{github.com/neuron7xLab}. The gamma probe pipeline and proof bundle are included in the neosynaptex repository.
```

## manuscript/hrv_bounded_preprint_skeleton.md

_matches: 45_

```
manuscript/hrv_bounded_preprint_skeleton.md:1:# A Two-Branch Honest Report on γ-Scaling and Multifractal Width in Human Heart-Rate Variability — Skeleton
manuscript/hrv_bounded_preprint_skeleton.md:15:> - §5.3 cross-subject γ on n=116: **Branch B FALSIFIED** under
manuscript/hrv_bounded_preprint_skeleton.md:17:>   p = 0.001) and a bootstrap CI (healthy mean γ CI95 =
manuscript/hrv_bounded_preprint_skeleton.md:18:>   [1.067, 1.237], excludes 1.0). Universal γ ≈ 1 at the cardiac
manuscript/hrv_bounded_preprint_skeleton.md:36:> B reports a negative cross-subject γ finding at pilot scale
manuscript/hrv_bounded_preprint_skeleton.md:58:at scale, cross-subject γ):** at the VLF band [0.003, 0.04] Hz,
manuscript/hrv_bounded_preprint_skeleton.md:59:healthy-cohort γ at n=72 has mean 1.143 with a 95 % bootstrap CI
manuscript/hrv_bounded_preprint_skeleton.md:61:H₀: γ = 1 at p = 10⁻³ (§5.3). Pathology γ is shifted further upward
manuscript/hrv_bounded_preprint_skeleton.md:63:canonical, §5.3.1) the universal γ ≈ 1 framing at the cardiac
manuscript/hrv_bounded_preprint_skeleton.md:64:substrate is rejected — they just disagree on whether γ is biased
manuscript/hrv_bounded_preprint_skeleton.md:75:- **Problem.** Cross-paper γ comparisons are noisy; null-model
manuscript/hrv_bounded_preprint_skeleton.md:80:     from *cross-subject universal γ* (Branch B), reported with
manuscript/hrv_bounded_preprint_skeleton.md:88:  - No cross-substrate universal γ ≈ 1.
manuscript/hrv_bounded_preprint_skeleton.md:97:- **RR truncation.** Per-pipeline: 20 000 beats for the MFDFA/γ
manuscript/hrv_bounded_preprint_skeleton.md:107:### 3.1 γ-fit
manuscript/hrv_bounded_preprint_skeleton.md:131:separable — expected, because γ at the VLF band is a linear spectral
manuscript/hrv_bounded_preprint_skeleton.md:138:necessary condition for Branch B's γ result to be attributed to
manuscript/hrv_bounded_preprint_skeleton.md:316:## 5. Results — Branch B (falsified at n=116, cross-subject γ)
manuscript/hrv_bounded_preprint_skeleton.md:320:- Per-subject γ: `[1.0855, 0.0724, 0.418, 0.367, 0.566]`.
manuscript/hrv_bounded_preprint_skeleton.md:322:- Beat-interval null separates on 4/5 subjects at `z > 3` (γ **does**
manuscript/hrv_bounded_preprint_skeleton.md:328:- The cardiac substrate does **not** carry γ ≈ 1 at the pilot
manuscript/hrv_bounded_preprint_skeleton.md:330:- The "per-subject cardiac γ" is a subject-dependent quantity, not a
manuscript/hrv_bounded_preprint_skeleton.md:332:- This result **does not** rule out a per-subject calibrated γ as a
manuscript/hrv_bounded_preprint_skeleton.md:333:  state marker; it rules out an uncalibrated γ as a population
manuscript/hrv_bounded_preprint_skeleton.md:336:  `docs/REPLICATION_PROTOCOL.md` §3) against the universal-γ
manuscript/hrv_bounded_preprint_skeleton.md:339:### 5.3 Full cohort — cross-subject γ at n=116
manuscript/hrv_bounded_preprint_skeleton.md:341:Per-subject γ from Welch PSD (nperseg = 1024, fs = 4 Hz) with Theil-
manuscript/hrv_bounded_preprint_skeleton.md:343:``scripts.run_gamma_full_cohort`` and analysed by
manuscript/hrv_bounded_preprint_skeleton.md:345:`results/hrv_gamma/branch_b_analysis.json`).
manuscript/hrv_bounded_preprint_skeleton.md:347:**Per-group γ distribution (n=116):**
manuscript/hrv_bounded_preprint_skeleton.md:349:| Group               | n  | γ mean ± sd     | 95 % bootstrap CI on mean | Range             |
manuscript/hrv_bounded_preprint_skeleton.md:354:**H₀: E[γ] = 1 on the healthy cohort** (two-sided one-sample
manuscript/hrv_bounded_preprint_skeleton.md:358:- 95 % bootstrap CI on healthy mean γ = [1.067, 1.237] — **excludes
manuscript/hrv_bounded_preprint_skeleton.md:363:converge on the same conclusion: a universal cross-subject γ ≈ 1 at
manuscript/hrv_bounded_preprint_skeleton.md:366:**Healthy vs pathology γ contrast:**
manuscript/hrv_bounded_preprint_skeleton.md:376:Pathology γ is shifted **upwards** relative to healthy (pathology
manuscript/hrv_bounded_preprint_skeleton.md:379:like" (γ closer to 1, shorter memory) spectral scaling than CHF.
manuscript/hrv_bounded_preprint_skeleton.md:387:NSR pilot records through the canonical pipeline gives mean γ ≈
manuscript/hrv_bounded_preprint_skeleton.md:388:1.15 (not the pilot's 0.50). **Both pipelines falsify the universal
manuscript/hrv_bounded_preprint_skeleton.md:389:γ ≈ 1 framing, but in opposite directions** — the pilot showed
manuscript/hrv_bounded_preprint_skeleton.md:390:γ < 1 on average; the canonical pipeline at scale shows γ > 1.
manuscript/hrv_bounded_preprint_skeleton.md:412:  - Any paper that claims "γ ≈ 1 is a universal cardiac invariant"
manuscript/hrv_bounded_preprint_skeleton.md:452:| 0.2     | 2026-04-14 | n=116 panel-level Branch A contrast landed (§4.2). MFDFA full-cohort marker (§4.3) + Branch B cross-subject γ (§5.3) still reserved. |
manuscript/hrv_bounded_preprint_skeleton.md:453:| 0.3     | 2026-04-14 | n=116 MFDFA marker + 7-seed blind-validation executed (§4.3). Branch A MFDFA **NOT PROMOTED**. Pilot pipeline discrepancy documented in §4.3.1. Branch B full-cohort γ (§5.3) still pending. |
manuscript/hrv_bounded_preprint_skeleton.md:455:| 0.5     | 2026-04-15 | Branch B full-cohort γ landed (§5.3). Healthy mean γ = 1.143, 95 % bootstrap CI [1.067, 1.237] excludes 1.0; one-sample t-test rejects H₀: γ = 1 at p = 0.001. **Universal γ ≈ 1 at the cardiac substrate is FALSIFIED at n=116.** Pipeline caveat in §5.3.1 notes that both pipelines falsify γ ≈ 1 but in opposite directions. |
```

## substrates/bn_syn/.github/QUALITY_LEDGER.md

_matches: 1_

```
substrates/bn_syn/.github/QUALITY_LEDGER.md:700:Property-based testing exhaustively validates universal invariants across parameter spaces. Catches edge cases that unit tests miss.
```

## substrates/bn_syn/docs/BIBLIOGRAPHY.md

_matches: 6_

```
substrates/bn_syn/docs/BIBLIOGRAPHY.md:42:| **Gamma scaling** | `gamma/` | McGuirl+ 2020 | A |
substrates/bn_syn/docs/BIBLIOGRAPHY.md:107:**[A14]** Tognoli E., Kelso J.A.S. (2014). The metastable brain. *Neuron*, 81(1), 35--48. DOI: [10.1016/j.neuron.2013.12.022](https://doi.org/10.1016/j.neuron.2013.12.022)
substrates/bn_syn/docs/BIBLIOGRAPHY.md:120:Winnerless competition — metastable sequential dynamics.
substrates/bn_syn/docs/BIBLIOGRAPHY.md:125:**[A20]** Buzsáki G., Wang X.-J. (2012). Mechanisms of gamma oscillations. *Annu. Rev. Neurosci.*, 35, 203--225. DOI: [10.1146/annurev-neuro-062111-150444](https://doi.org/10.1146/annurev-neuro-062111-150444)
substrates/bn_syn/docs/BIBLIOGRAPHY.md:138:TDA gamma measurement on biological patterning — γ_WT = +1.043.
substrates/bn_syn/docs/BIBLIOGRAPHY.md:151:Coordination dynamics and metastability — conceptual foundation.
```

## substrates/bn_syn/docs/QUALITY_INDEX.md

_matches: 1_

```
substrates/bn_syn/docs/QUALITY_INDEX.md:96:- Tests universal invariants (determinism, finiteness, boundedness)
```

## substrates/bn_syn/docs/QUALITY_INFRASTRUCTURE.md

_matches: 1_

```
substrates/bn_syn/docs/QUALITY_INFRASTRUCTURE.md:13:3. **Property Testing** - Hypothesis-based testing for universal invariants
```

## substrates/bn_syn/docs/TESTING_MUTATION.md

_matches: 1_

```
substrates/bn_syn/docs/TESTING_MUTATION.md:221:5. **Write property tests** for universal invariants (no `max_examples` overrides)
```

## substrates/hippocampal_ca1/docs/BIBLIOGRAPHY.md

_matches: 6_

```
substrates/hippocampal_ca1/docs/BIBLIOGRAPHY.md:37:| **Theta-gamma coupling** | Lisman & Jensen 2013 [F] |
substrates/hippocampal_ca1/docs/BIBLIOGRAPHY.md:171:- Synaptic scaling mechanism: W ← W · exp(γ(ν* - ν))
substrates/hippocampal_ca1/docs/BIBLIOGRAPHY.md:227:*The theta-gamma neural code*
substrates/hippocampal_ca1/docs/BIBLIOGRAPHY.md:232:- Theta phase organizes gamma cycles
substrates/hippocampal_ca1/docs/BIBLIOGRAPHY.md:233:- Items per gamma cycle encode individual memories
substrates/hippocampal_ca1/docs/BIBLIOGRAPHY.md:462:  title = {The theta-gamma neural code},
```

## substrates/kuramoto/CHANGELOG.md

_matches: 2_

```
substrates/kuramoto/CHANGELOG.md:95:- **Core Indicators**: Kuramoto oscillators, Ricci flow curvature, Shannon entropy, Hurst exponent, 50+ technical indicators.
substrates/kuramoto/CHANGELOG.md:97:- **TradePulseCompositeEngine**: High-level API combining Kuramoto synchronization with Ricci flow geometry.
```

## substrates/kuramoto/CONTRIBUTING.md

_matches: 1_

```
substrates/kuramoto/CONTRIBUTING.md:171:git checkout -b refactor/simplify-kuramoto
```

## substrates/kuramoto/PROJECT_DEVELOPMENT_STAGE.md

_matches: 1_

```
substrates/kuramoto/PROJECT_DEVELOPMENT_STAGE.md:33:   - ✅ Geometric Market Intelligence (Kuramoto oscillators, Ricci flow, entropy measures)
```

## substrates/kuramoto/README.md

_matches: 11_

```
substrates/kuramoto/README.md:45:- **Geometric Market Indicators**: Kuramoto oscillators, Ricci flow, entropy measures for deep market analysis
substrates/kuramoto/README.md:65:**Kuramoto Oscillators** — Detect synchronization patterns in market dynamics  
substrates/kuramoto/README.md:285:2. **Market Analysis** — Detects regime using Kuramoto-Ricci indicators
substrates/kuramoto/README.md:320:from core.indicators.kuramoto_ricci_composite import TradePulseCompositeEngine
substrates/kuramoto/README.md:342:from core.indicators import KuramotoIndicator
substrates/kuramoto/README.md:349:indicator = KuramotoIndicator(window=80, coupling=0.9)
substrates/kuramoto/README.md:351:def kuramoto_signal(series: np.ndarray) -> np.ndarray:
substrates/kuramoto/README.md:362:    kuramoto_signal,
substrates/kuramoto/README.md:364:    strategy_name="kuramoto_demo",
substrates/kuramoto/README.md:669:from tradepulse.indicators import MultiscaleKuramoto
substrates/kuramoto/README.md:671:indicator = MultiscaleKuramoto(
```

## substrates/kuramoto/SETUP.md

_matches: 2_

```
substrates/kuramoto/SETUP.md:86:python -c "from core.indicators.kuramoto import compute_phase; print('✅ Setup complete!')"
substrates/kuramoto/SETUP.md:239:python -c "from core.indicators.kuramoto import compute_phase; print('✅ Core imports OK')"
```

## substrates/kuramoto/SYSTEM_OPTIMIZATION_SUMMARY.md

_matches: 1_

```
substrates/kuramoto/SYSTEM_OPTIMIZATION_SUMMARY.md:18:   - Safeguards: synchrony throttling via Kuramoto order parameter, desync downscaling, deterministic fallback when the runtime TACL provider is unavailable.
```

## substrates/kuramoto/TESTING.md

_matches: 1_

```
substrates/kuramoto/TESTING.md:327:The CI pipeline enforces coverage on the reliability-critical surface (Kuramoto
```

## substrates/kuramoto/analytics/regime/README.md

_matches: 3_

```
substrates/kuramoto/analytics/regime/README.md:39:- **Topological Analysis**: Monitor market topology changes via Ricci flow and Kuramoto synchronization
substrates/kuramoto/analytics/regime/README.md:84:- `core.indicators`: Kuramoto, Ricci flow, Hurst exponent indicators
substrates/kuramoto/analytics/regime/README.md:238:Topological features (Ricci curvature, Kuramoto sync) capture structural market properties robust to noise:
```

## substrates/kuramoto/artifacts/working_stack/20260328T151401/00_reality_map.md

_matches: 2_

```
substrates/kuramoto/artifacts/working_stack/20260328T151401/00_reality_map.md:17:1. `examples/quick_start.py` — primary demo (synthetic data + Kuramoto-Ricci analysis)
substrates/kuramoto/artifacts/working_stack/20260328T151401/00_reality_map.md:23:- Repo name: "Kuramoto-synchronization-model-main" vs product name "TradePulse"
```

## substrates/kuramoto/config/dopamine.yaml

_matches: 1_

```
substrates/kuramoto/config/dopamine.yaml:5:discount_gamma: 0.98
```

## substrates/kuramoto/config/profiles/aggressive.yaml

_matches: 1_

```
substrates/kuramoto/config/profiles/aggressive.yaml:6:discount_gamma: 0.99  # Higher discount for longer-term planning
```

## substrates/kuramoto/config/profiles/conservative.yaml

_matches: 1_

```
substrates/kuramoto/config/profiles/conservative.yaml:6:discount_gamma: 0.95  # Lower discount for more cautious value estimates
```

## substrates/kuramoto/config/profiles/normal.yaml

_matches: 1_

```
substrates/kuramoto/config/profiles/normal.yaml:6:discount_gamma: 0.98
```

## substrates/kuramoto/configs/README.md

_matches: 4_

```
substrates/kuramoto/configs/README.md:6:- `kuramoto_ricci_composite.yaml` – reference configuration for the Kuramoto–Ricci composite integration workflow.
substrates/kuramoto/configs/README.md:8:## Kuramoto–Ricci composite structure
substrates/kuramoto/configs/README.md:10:Configuration files consumed by `scripts/integrate_kuramoto_ricci.py` follow this structure:
substrates/kuramoto/configs/README.md:13:kuramoto:
```

## substrates/kuramoto/configs/demo.yaml

_matches: 1_

```
substrates/kuramoto/configs/demo.yaml:37:  risk_gamma: 15.0   # чутливість динамічного ліміту до CVaR (експон. демпфування)
```

## substrates/kuramoto/configs/dopamine.yaml

_matches: 1_

```
substrates/kuramoto/configs/dopamine.yaml:2:discount_gamma: 0.98
```

## substrates/kuramoto/configs/kuramoto_ricci_composite.yaml

_matches: 1_

```
substrates/kuramoto/configs/kuramoto_ricci_composite.yaml:2:kuramoto:
```

## substrates/kuramoto/configs/quality/heavy_math_jobs.yaml

_matches: 7_

```
substrates/kuramoto/configs/quality/heavy_math_jobs.yaml:3:  kuramoto_validation:
substrates/kuramoto/configs/quality/heavy_math_jobs.yaml:4:    description: "Cross-check Kuramoto multi-scale outputs against golden dataset"
substrates/kuramoto/configs/quality/heavy_math_jobs.yaml:5:    entrypoint: "python scripts/integrate_kuramoto_ricci.py --mode kuramoto --config configs/kuramoto_ricci_composite.yaml"
substrates/kuramoto/configs/quality/heavy_math_jobs.yaml:12:      - reports/heavy_math/kuramoto/metrics.json
substrates/kuramoto/configs/quality/heavy_math_jobs.yaml:13:      - reports/heavy_math/kuramoto/timeseries.parquet
substrates/kuramoto/configs/quality/heavy_math_jobs.yaml:20:    entrypoint: "python scripts/integrate_kuramoto_ricci.py --mode ricci --config configs/kuramoto_ricci_composite.yaml"
substrates/kuramoto/configs/quality/heavy_math_jobs.yaml:34:    entrypoint: "python scripts/integrate_kuramoto_ricci.py --mode hurst --config configs/kuramoto_ricci_composite.yaml"
```

## substrates/kuramoto/configs/serotonin.yaml

_matches: 1_

```
substrates/kuramoto/configs/serotonin.yaml:28:  gamma: 0.4              # Weight for cumulative losses (with quadratic component)
```

## substrates/kuramoto/core/indicators/README.md

_matches: 23_

```
substrates/kuramoto/core/indicators/README.md:15:The `core/indicators` module provides advanced geometric and phase-synchrony indicators for algorithmic trading signal generation. This module implements cutting-edge mathematical techniques including Kuramoto oscillator analysis, Ricci flow curvature detection, multi-scale coherence analysis, and entropy-based market regime classification.
substrates/kuramoto/core/indicators/README.md:26:- **Phase Synchronization Analysis**: Compute Kuramoto order parameters to detect collective market behavior and phase coherence across assets
substrates/kuramoto/core/indicators/README.md:38:| `KuramotoIndicator` | Class | `trading.py` | Production-ready Kuramoto order parameter calculator with configurable coupling strength |
substrates/kuramoto/core/indicators/README.md:41:| `TradePulseCompositeEngine` | Class | `kuramoto_ricci_composite.py` | Primary signal generator combining Kuramoto, Ricci, and topology analysis |
substrates/kuramoto/core/indicators/README.md:42:| `MultiScaleKuramoto` | Class | `multiscale_kuramoto.py` | Multi-timeframe Kuramoto analysis with consensus detection |
substrates/kuramoto/core/indicators/README.md:46:| `compute_phase()` | Function | `kuramoto.py` | Convert price series to analytic signal phases via Hilbert transform |
substrates/kuramoto/core/indicators/README.md:47:| `compute_phase_gpu()` | Function | `kuramoto.py` | GPU-accelerated phase computation using CuPy |
substrates/kuramoto/core/indicators/README.md:48:| `kuramoto_order()` | Function | `kuramoto.py` | Calculate Kuramoto order parameter R from phase array |
substrates/kuramoto/core/indicators/README.md:61:- `kuramoto.yaml`: Kuramoto oscillator parameters (window, coupling, gpu_enabled)
substrates/kuramoto/core/indicators/README.md:92:├── kuramoto.py                      # Phase synchronization, Kuramoto order
substrates/kuramoto/core/indicators/README.md:95:├── multiscale_kuramoto.py           # Multi-timeframe Kuramoto analysis
substrates/kuramoto/core/indicators/README.md:96:├── kuramoto_ricci_composite.py      # TradePulseCompositeEngine (main signal)
substrates/kuramoto/core/indicators/README.md:133:  - Mathematical correctness of Kuramoto order parameter
substrates/kuramoto/core/indicators/README.md:157:  - Kuramoto order R always in [0, 1]
substrates/kuramoto/core/indicators/README.md:164:### Basic Kuramoto Analysis
substrates/kuramoto/core/indicators/README.md:166:from core.indicators import KuramotoIndicator
substrates/kuramoto/core/indicators/README.md:170:indicator = KuramotoIndicator(window=80, coupling=0.9)
substrates/kuramoto/core/indicators/README.md:203:from core.indicators import MultiScaleKuramoto, TimeFrame
substrates/kuramoto/core/indicators/README.md:213:analyzer = MultiScaleKuramoto(timeframes=timeframes)
substrates/kuramoto/core/indicators/README.md:227:    ('kuramoto', KuramotoIndicator(window=80)),
substrates/kuramoto/core/indicators/README.md:240:from core.indicators import cache_indicator, KuramotoIndicator
substrates/kuramoto/core/indicators/README.md:244:    KuramotoIndicator(window=80),
substrates/kuramoto/core/indicators/README.md:259:- **Kuramoto Order**: O(n) for n-length price series
```

## substrates/kuramoto/core/neuro/README_ECS_REGULATOR.md

_matches: 3_

```
substrates/kuramoto/core/neuro/README_ECS_REGULATOR.md:15:Integrates with Kuramoto-Ricci phase analysis from TradePulse:
substrates/kuramoto/core/neuro/README_ECS_REGULATOR.md:192:### 2. Kuramoto-Ricci Phase Integration
substrates/kuramoto/core/neuro/README_ECS_REGULATOR.md:201:# Get market phase from Kuramoto-Ricci analysis
```

## substrates/kuramoto/core/neuro/serotonin/README.md

_matches: 1_

```
substrates/kuramoto/core/neuro/serotonin/README.md:76:| gamma | number | minimum=0.0; required | Weight for cumulative losses |
```

## substrates/kuramoto/core/strategies/README.md

_matches: 11_

```
substrates/kuramoto/core/strategies/README.md:213:from core.indicators import KuramotoIndicator
substrates/kuramoto/core/strategies/README.md:237:    """Simple momentum strategy using Kuramoto indicator"""
substrates/kuramoto/core/strategies/README.md:238:    indicator = KuramotoIndicator(window=80, coupling=0.9)
substrates/kuramoto/core/strategies/README.md:328:from core.indicators import KuramotoIndicator, HurstIndicator
substrates/kuramoto/core/strategies/README.md:336:        ("kuramoto", KuramotoIndicator(window=80)),
substrates/kuramoto/core/strategies/README.md:340:        # Buy when Kuramoto > 0.75 AND Hurst > 0.6 (trending)
substrates/kuramoto/core/strategies/README.md:342:            condition=lambda ctx: ctx.indicators.kuramoto > 0.75 and ctx.indicators.hurst > 0.6,
substrates/kuramoto/core/strategies/README.md:343:            action=dsl.signal("BUY", confidence=lambda ctx: ctx.indicators.kuramoto),
substrates/kuramoto/core/strategies/README.md:345:        # Sell when Kuramoto < 0.25 AND Hurst < 0.4 (mean-reverting)
substrates/kuramoto/core/strategies/README.md:347:            condition=lambda ctx: ctx.indicators.kuramoto < 0.25 and ctx.indicators.hurst < 0.4,
substrates/kuramoto/core/strategies/README.md:348:            action=dsl.signal("SELL", confidence=lambda ctx: 1.0 - ctx.indicators.kuramoto),
```

## substrates/kuramoto/cortex_service/ARCHITECTURE.md

_matches: 1_

```
substrates/kuramoto/cortex_service/ARCHITECTURE.md:70:    SignalService->>EnsembleSync: kuramoto_order_parameter()
```

## substrates/kuramoto/data/README.md

_matches: 1_

```
substrates/kuramoto/data/README.md:97:from core.indicators.kuramoto_ricci_composite import TradePulseCompositeEngine
```

## substrates/kuramoto/docs/API.md

_matches: 22_

```
substrates/kuramoto/docs/API.md:11:  - [Kuramoto Indicators](#kuramoto-indicators)
substrates/kuramoto/docs/API.md:32:from core.indicators.kuramoto_ricci_composite import TradePulseCompositeEngine
substrates/kuramoto/docs/API.md:53:The main entry point for market regime analysis combining Kuramoto synchronization with Ricci flow curvature.
substrates/kuramoto/docs/API.md:55:**Module:** `core.indicators.kuramoto_ricci_composite`
substrates/kuramoto/docs/API.md:61:    kuramoto_config: Optional[Dict] = None,
substrates/kuramoto/docs/API.md:71:| `kuramoto_config` | `Dict` | `None` | Configuration for MultiScaleKuramoto analyzer |
substrates/kuramoto/docs/API.md:79:    "R_strong_emergent": 0.8,       # Kuramoto R threshold for strong emergence
substrates/kuramoto/docs/API.md:80:    "R_proto_emergent": 0.4,        # Kuramoto R threshold for proto-emergence
substrates/kuramoto/docs/API.md:92:from core.indicators.kuramoto_ricci_composite import TradePulseCompositeEngine
substrates/kuramoto/docs/API.md:96:    kuramoto_config={
substrates/kuramoto/docs/API.md:142:| `kuramoto_R` | `float` | Kuramoto order parameter |
substrates/kuramoto/docs/API.md:149:from core.indicators.kuramoto_ricci_composite import (
substrates/kuramoto/docs/API.md:193:### Kuramoto Indicators
substrates/kuramoto/docs/API.md:195:**Module:** `core.indicators.kuramoto`
substrates/kuramoto/docs/API.md:210:#### kuramoto_order
substrates/kuramoto/docs/API.md:213:kuramoto_order(phases: np.ndarray) -> float
substrates/kuramoto/docs/API.md:216:Compute Kuramoto order parameter (synchronization measure).
substrates/kuramoto/docs/API.md:226:from core.indicators.kuramoto import compute_phase, kuramoto_order
substrates/kuramoto/docs/API.md:229:R = kuramoto_order(phases[-200:])
substrates/kuramoto/docs/API.md:230:print(f"Kuramoto R: {R:.3f}")
substrates/kuramoto/docs/API.md:332:from core.indicators import KuramotoIndicator
substrates/kuramoto/docs/API.md:334:indicator = KuramotoIndicator(window=80, coupling=0.9)
```

## substrates/kuramoto/docs/CALIBRATION_GUIDE.md

_matches: 3_

```
substrates/kuramoto/docs/CALIBRATION_GUIDE.md:85:- `discount_gamma`: Future reward discount factor
substrates/kuramoto/docs/CALIBRATION_GUIDE.md:283:| `discount_gamma` | 0.90-0.999 | 0.98 | Future reward discount factor |
substrates/kuramoto/docs/CALIBRATION_GUIDE.md:288:- Higher `discount_gamma` = more long-term oriented
```

## substrates/kuramoto/docs/CALIBRATION_PARAMETER_REFERENCE.md

_matches: 4_

```
substrates/kuramoto/docs/CALIBRATION_PARAMETER_REFERENCE.md:102:| `discount_gamma` | (0.0, 1.0) | - | 0.98 | - | Future reward discount factor |
substrates/kuramoto/docs/CALIBRATION_PARAMETER_REFERENCE.md:107:- 0 < `discount_gamma` < 1.0
substrates/kuramoto/docs/CALIBRATION_PARAMETER_REFERENCE.md:113:- Higher `discount_gamma` = more long-term oriented
substrates/kuramoto/docs/CALIBRATION_PARAMETER_REFERENCE.md:393:- [ ] Dopamine: 0 < `discount_gamma` < 1.0
```

## substrates/kuramoto/docs/CONCEPTUAL_ARCHITECTURE_UA.md

_matches: 4_

```
substrates/kuramoto/docs/CONCEPTUAL_ARCHITECTURE_UA.md:40:            KURA[Kuramoto<br/>Синхронізація]
substrates/kuramoto/docs/CONCEPTUAL_ARCHITECTURE_UA.md:156:        Kuramoto осцилятори
substrates/kuramoto/docs/CONCEPTUAL_ARCHITECTURE_UA.md:397:        KURA_SIG[Kuramoto сигнал]
substrates/kuramoto/docs/CONCEPTUAL_ARCHITECTURE_UA.md:729:        Ind->>Ind: Kuramoto синхронізація
```

## substrates/kuramoto/docs/GABAInhibitionGate.md

_matches: 4_

```
substrates/kuramoto/docs/GABAInhibitionGate.md:69:If enabled, gamma/theta modulation is
substrates/kuramoto/docs/GABAInhibitionGate.md:71:M = 1 + 0.2\sin(2π f_γ t) + 0.15\sin(2π f_θ t),
substrates/kuramoto/docs/GABAInhibitionGate.md:73:with $f_γ=40$ Hz and $f_θ=8$ Hz. Otherwise $M=1$.
substrates/kuramoto/docs/GABAInhibitionGate.md:127:  - `cycle_multiplier`: gamma/theta modulation applied this step.
```

## substrates/kuramoto/docs/GITHUB_METADATA.md

_matches: 4_

```
substrates/kuramoto/docs/GITHUB_METADATA.md:10:Enterprise-grade algorithmic trading platform with geometric market indicators — Kuramoto, Ricci flow, entropy analysis.
substrates/kuramoto/docs/GITHUB_METADATA.md:16:TradePulse is an enterprise-grade algorithmic trading platform that combines advanced geometric market indicators (Kuramoto synchronization, Ricci flow curvature, entropy measures) with production-ready infrastructure. Built for quantitative researchers, day traders, and financial institutions who need to transition seamlessly from research to live execution.
substrates/kuramoto/docs/GITHUB_METADATA.md:48:kuramoto
substrates/kuramoto/docs/GITHUB_METADATA.md:66:trading, algorithmic-trading, quantitative-finance, backtesting, market-analysis, python, fastapi, numpy, pandas, pytorch, kuramoto, ricci-flow, geometric-indicators, entropy-analysis, technical-analysis, framework, enterprise
```

## substrates/kuramoto/docs/HPC_AI_V4.md

_matches: 6_

```
substrates/kuramoto/docs/HPC_AI_V4.md:54:δ_t = r_{t+1} + γ V(s_{t+1}) − V(s_t)
substrates/kuramoto/docs/HPC_AI_V4.md:92:- **Input**: OHLCV + Kuramoto-Ricci indicators (10 dimensions)
substrates/kuramoto/docs/HPC_AI_V4.md:113:- **Output**: Binary decision (hold if metastable transition detected)
substrates/kuramoto/docs/HPC_AI_V4.md:225:    "gamma": 0.99,             # RL discount factor
substrates/kuramoto/docs/HPC_AI_V4.md:235:- **pwpe_threshold**: 0.2 (metastable gate trigger)
substrates/kuramoto/docs/HPC_AI_V4.md:258:✓ **Kuramoto-Ricci Integration**: Multi-scale market synchronization  
```

## substrates/kuramoto/docs/NEURO_OPTIMIZATION_SUMMARY.md

_matches: 2_

```
substrates/kuramoto/docs/NEURO_OPTIMIZATION_SUMMARY.md:163:- `discount_gamma`: [0.90, 0.999]
substrates/kuramoto/docs/NEURO_OPTIMIZATION_SUMMARY.md:307:    'dopamine': {'discount_gamma': 0.99, 'learning_rate': 0.01},
```

## substrates/kuramoto/docs/SEROTONIN_DEPLOYMENT_GUIDE.md

_matches: 1_

```
substrates/kuramoto/docs/SEROTONIN_DEPLOYMENT_GUIDE.md:160:gamma: 0.32              # Cumulative losses weight
```

## substrates/kuramoto/docs/SEROTONIN_IMPROVEMENTS_V2.4.0.md

_matches: 1_

```
substrates/kuramoto/docs/SEROTONIN_IMPROVEMENTS_V2.4.0.md:118:loss_contribution = gamma * (cum_losses + 0.5 * cum_losses ** 2)
```

## substrates/kuramoto/docs/TEST_ARCHITECTURE.md

_matches: 3_

```
substrates/kuramoto/docs/TEST_ARCHITECTURE.md:170:def test_kuramoto_indicator_performance(benchmark) -> None:
substrates/kuramoto/docs/TEST_ARCHITECTURE.md:171:    """Validate Kuramoto indicator performance stays within budget.
substrates/kuramoto/docs/TEST_ARCHITECTURE.md:176:    indicator = KuramotoIndicator(window=50)
```

## substrates/kuramoto/docs/TEST_OPTIMIZATION_RECOMMENDATIONS.md

_matches: 3_

```
substrates/kuramoto/docs/TEST_OPTIMIZATION_RECOMMENDATIONS.md:98:    indicator = KuramotoIndicator(window=20)
substrates/kuramoto/docs/TEST_OPTIMIZATION_RECOMMENDATIONS.md:128:    indicator = KuramotoIndicator(window=100)
substrates/kuramoto/docs/TEST_OPTIMIZATION_RECOMMENDATIONS.md:139:        KuramotoIndicator(window=-1)
```

## substrates/kuramoto/docs/TEST_QUALITY_IMPROVEMENTS.md

_matches: 3_

```
substrates/kuramoto/docs/TEST_QUALITY_IMPROVEMENTS.md:210:4. **tests/unit/test_kuramoto_ricci_composite.py** (33 tests, no module docstring)
substrates/kuramoto/docs/TEST_QUALITY_IMPROVEMENTS.md:211:5. **tests/unit/test_indicators_kuramoto.py** (27 tests, no module docstring)
substrates/kuramoto/docs/TEST_QUALITY_IMPROVEMENTS.md:286:- Kuramoto indicator tests (27+ tests)
```

## substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md

_matches: 13_

```
substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md:70:python -c "from core.indicators.kuramoto import compute_phase; import numpy as np; phases = compute_phase(np.array([100,101,102])); print('API ready, phases:', phases)"
substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md:279:    print(f"Kuramoto Order: {analysis['R']:.4f}")
substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md:368:  - Kuramoto Order Parameter (R) - Phase synchronization
substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md:510:from core.indicators.kuramoto import compute_phase, kuramoto_order
substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md:519:# Compute Kuramoto order parameter
substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md:521:R = kuramoto_order(phases[-200:])
substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md:522:print(f"Kuramoto Order: {R:.4f}")
substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md:543:from core.indicators.kuramoto_ricci_composite import TradePulseCompositeEngine
substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md:685:        "indicators": ["kuramoto", "entropy", "hurst"]
substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md:689:print(f"Kuramoto Order: {result['kuramoto']}")
substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md:713:        "indicators": ["kuramoto", "entropy"]
substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md:734:from core.indicators.kuramoto_ricci_composite import TradePulseCompositeEngine
substrates/kuramoto/docs/USER_INTERACTION_GUIDE.md:794:from core.indicators.kuramoto_ricci_composite import TradePulseCompositeEngine
```

## substrates/kuramoto/docs/WORKING_STACK.md

_matches: 2_

```
substrates/kuramoto/docs/WORKING_STACK.md:8:(Kuramoto synchronization, Ricci curvature, entropy production, neuro-inspired controllers).
substrates/kuramoto/docs/WORKING_STACK.md:38:# Quick demo — generates synthetic data, runs Kuramoto-Ricci analysis
```

## substrates/kuramoto/docs/adr/0001-fractal-indicator-composition-architecture.md

_matches: 2_

```
substrates/kuramoto/docs/adr/0001-fractal-indicator-composition-architecture.md:107:   - Identify candidate indicators (Kuramoto, Ricci, entropy measures)
substrates/kuramoto/docs/adr/0001-fractal-indicator-composition-architecture.md:145:- Migrate Kuramoto and Ricci indicators
```

## substrates/kuramoto/docs/agent.md

_matches: 1_

```
substrates/kuramoto/docs/agent.md:61:- `R` – Kuramoto order (synchrony) 【F:core/agent/strategy.py†L101-L113】
```

## substrates/kuramoto/docs/api_examples.md

_matches: 11_

```
substrates/kuramoto/docs/api_examples.md:20:from core.indicators.kuramoto import compute_phase, kuramoto_order
substrates/kuramoto/docs/api_examples.md:27:# Kuramoto synchronization
substrates/kuramoto/docs/api_examples.md:29:R = kuramoto_order(phases)
substrates/kuramoto/docs/api_examples.md:30:print(f"Kuramoto Order: {R:.4f}")
substrates/kuramoto/docs/api_examples.md:45:from core.indicators.kuramoto import MultiAssetKuramotoFeature
substrates/kuramoto/docs/api_examples.md:56:feature = MultiAssetKuramotoFeature(window=3)
substrates/kuramoto/docs/api_examples.md:66:from core.indicators.kuramoto_ricci_composite import TradePulseCompositeEngine
substrates/kuramoto/docs/api_examples.md:89:from core.indicators.kuramoto import KuramotoOrderFeature
substrates/kuramoto/docs/api_examples.md:101:        KuramotoOrderFeature(window=50, name="sync"),
substrates/kuramoto/docs/api_examples.md:472:from core.indicators.kuramoto import kuramoto_order, compute_phase
substrates/kuramoto/docs/api_examples.md:490:        R = kuramoto_order(phases)
```

## substrates/kuramoto/docs/architecture/CONCEPTUAL_ARCHITECTURE.md

_matches: 4_

```
substrates/kuramoto/docs/architecture/CONCEPTUAL_ARCHITECTURE.md:22:  - 📊 Indicators (Kuramoto, Ricci Flow, Entropy, Technical)
substrates/kuramoto/docs/architecture/CONCEPTUAL_ARCHITECTURE.md:59:4. Parallel indicator calculation (Kuramoto, Ricci, Entropy)
substrates/kuramoto/docs/architecture/CONCEPTUAL_ARCHITECTURE.md:84:- Kuramoto Oscillators — synchronization-based market analysis
substrates/kuramoto/docs/architecture/CONCEPTUAL_ARCHITECTURE.md:108:3. **Signal Generation**: Kuramoto, Ricci, Entropy signals → Composite signal
```

## substrates/kuramoto/docs/architecture/system_modules_reference.md

_matches: 1_

```
substrates/kuramoto/docs/architecture/system_modules_reference.md:55:`TradePulseCompositeEngine` in `core/indicators/kuramoto_ricci_composite.py` fuses Kuramoto
```

## substrates/kuramoto/docs/calibration/CONTROLLER_INVENTORY.md

_matches: 2_

```
substrates/kuramoto/docs/calibration/CONTROLLER_INVENTORY.md:51:- Learning rates (learning_rate_v, discount_gamma)
substrates/kuramoto/docs/calibration/CONTROLLER_INVENTORY.md:58:- 0 < discount_gamma < 1.0
```

## substrates/kuramoto/docs/configuration.md

_matches: 15_

```
substrates/kuramoto/docs/configuration.md:12:1. **Command line overrides** – values passed to `load_kuramoto_ricci_config(..., cli_overrides=...)`
substrates/kuramoto/docs/configuration.md:18:   `config_file` (defaults to `configs/kuramoto_ricci_composite.yaml`).
substrates/kuramoto/docs/configuration.md:28:kuramoto:
substrates/kuramoto/docs/configuration.md:59:The Kuramoto–Ricci integration script demonstrates CLI overrides:
substrates/kuramoto/docs/configuration.md:62:python scripts/integrate_kuramoto_ricci.py \
substrates/kuramoto/docs/configuration.md:64:  --config configs/kuramoto_ricci_composite.yaml \
substrates/kuramoto/docs/configuration.md:65:  --config-override kuramoto.base_window=256 \
substrates/kuramoto/docs/configuration.md:71:`--config-override kuramoto.timeframes=['M1','M5','H1']`.
substrates/kuramoto/docs/configuration.md:123:Python modules should use `load_kuramoto_ricci_config` to obtain a fully merged
substrates/kuramoto/docs/configuration.md:124:`KuramotoRicciIntegrationConfig` instance:
substrates/kuramoto/docs/configuration.md:127:from core.config import load_kuramoto_ricci_config
substrates/kuramoto/docs/configuration.md:129:cfg = load_kuramoto_ricci_config("configs/kuramoto_ricci_composite.yaml")
substrates/kuramoto/docs/configuration.md:137:from core.config import load_kuramoto_ricci_config, parse_cli_overrides
substrates/kuramoto/docs/configuration.md:139:overrides = parse_cli_overrides(["kuramoto.base_window=512"])
substrates/kuramoto/docs/configuration.md:140:cfg = load_kuramoto_ricci_config("configs/custom.yaml", cli_overrides=overrides)
```

## substrates/kuramoto/docs/contracts/interface-contracts.md

_matches: 1_

```
substrates/kuramoto/docs/contracts/interface-contracts.md:430:        features = ["sma_20", "ema_50", "kuramoto_sync"]
```

## substrates/kuramoto/docs/data/extended_market_sample.md

_matches: 1_

```
substrates/kuramoto/docs/data/extended_market_sample.md:111:from core.indicators.kuramoto_ricci_composite import TradePulseCompositeEngine
```

## substrates/kuramoto/docs/data/orchestrator_configs.md

_matches: 3_

```
substrates/kuramoto/docs/data/orchestrator_configs.md:48:    "discount_gamma": float,             // Discount factor for future rewards
substrates/kuramoto/docs/data/orchestrator_configs.md:71:   - Indicators: Kuramoto synchronization, Ricci flow, entropy
substrates/kuramoto/docs/data/orchestrator_configs.md:135:        discount_gamma: float = Field(ge=0, le=1)
```

## substrates/kuramoto/docs/examples/README.md

_matches: 12_

```
substrates/kuramoto/docs/examples/README.md:56:from core.indicators.kuramoto import compute_phase, kuramoto_order
substrates/kuramoto/docs/examples/README.md:64:# Compute Kuramoto order
substrates/kuramoto/docs/examples/README.md:66:R = kuramoto_order(phases[-200:])
substrates/kuramoto/docs/examples/README.md:67:print(f"Kuramoto Order: {R:.3f}")
substrates/kuramoto/docs/examples/README.md:122:from core.indicators.kuramoto import compute_phase, kuramoto_order
substrates/kuramoto/docs/examples/README.md:135:        R = kuramoto_order(phases)
substrates/kuramoto/docs/examples/README.md:298:from core.indicators.kuramoto import KuramotoOrder
substrates/kuramoto/docs/examples/README.md:306:block.add_feature(KuramotoOrder(window=200))
substrates/kuramoto/docs/examples/README.md:326:from core.indicators.kuramoto import compute_phase, kuramoto_order
substrates/kuramoto/docs/examples/README.md:338:R = kuramoto_order(phases[-200:])
substrates/kuramoto/docs/examples/README.md:358:from core.indicators.kuramoto import compute_phase, kuramoto_order
substrates/kuramoto/docs/examples/README.md:373:        R = kuramoto_order(phases[-200:])
```

## substrates/kuramoto/docs/extending.md

_matches: 2_

```
substrates/kuramoto/docs/extending.md:176:from .kuramoto import KuramotoOrder
substrates/kuramoto/docs/extending.md:182:    "KuramotoOrder",
```

## substrates/kuramoto/docs/falsification/serotonin_v2_3_1.md

_matches: 1_

```
substrates/kuramoto/docs/falsification/serotonin_v2_3_1.md:19:- Track telemetry: `serotonin_tonic_level`, `serotonin_phasic_level`, `serotonin_gate_level`, `serotonin_sensitivity`, `serotonin_level`, `serotonin_alpha_drift`, `serotonin_beta_drift`, `serotonin_gamma_drift`.
```

## substrates/kuramoto/docs/faq.md

_matches: 5_

```
substrates/kuramoto/docs/faq.md:11:TradePulse is an advanced algorithmic trading framework that combines geometric and topological market analysis (Kuramoto synchronization, Ricci curvature, entropy metrics) with modern backtesting and execution capabilities.
substrates/kuramoto/docs/faq.md:94:- Kuramoto synchronization (phase coherence)
substrates/kuramoto/docs/faq.md:107:### How do Kuramoto and Ricci indicators work?
substrates/kuramoto/docs/faq.md:109:- **Kuramoto Order Parameter (R)**: Measures synchronization between price oscillators. High R (close to 1) indicates strong coordination, low R indicates chaos.
substrates/kuramoto/docs/faq.md:264:from core.indicators.kuramoto import compute_phase_gpu
```

## substrates/kuramoto/docs/indicators.md

_matches: 18_

```
substrates/kuramoto/docs/indicators.md:25:| Kuramoto Order | Phase synchronisation for collective trend detection | Complex order parameter R = \|⟨e^(iθ)⟩\| | [`core/indicators/kuramoto.py`](../core/indicators/kuramoto.py) |
substrates/kuramoto/docs/indicators.md:32:| Composite Blocks | Multi-metric regime detectors | Combined indicators | [`core/indicators/kuramoto_ricci_composite.py`](../core/indicators/kuramoto_ricci_composite.py) |
substrates/kuramoto/docs/indicators.md:34:### Kuramoto Synchronisation
substrates/kuramoto/docs/indicators.md:37:The Kuramoto order parameter quantifies phase coherence among N oscillators:
substrates/kuramoto/docs/indicators.md:50:  a deterministic FFT fallback. 【F:core/indicators/kuramoto.py†L1-L40】
substrates/kuramoto/docs/indicators.md:51:- `kuramoto_order` computes \|mean(exp(iθ))\| to summarise synchrony; higher
substrates/kuramoto/docs/indicators.md:52:  values imply coherent trends. 【F:core/indicators/kuramoto.py†L42-L60】
substrates/kuramoto/docs/indicators.md:53:- Feature wrappers (`KuramotoOrderFeature`, `MultiAssetKuramotoFeature`) expose
substrates/kuramoto/docs/indicators.md:54:  the indicator through the feature pipeline. 【F:core/indicators/kuramoto.py†L91-L111】
substrates/kuramoto/docs/indicators.md:65:from core.indicators.kuramoto import compute_phase, kuramoto_order
substrates/kuramoto/docs/indicators.md:67:R = kuramoto_order(phases[-200:])
substrates/kuramoto/docs/indicators.md:233:`core/indicators/kuramoto_ricci_composite.py` demonstrates how to combine the
substrates/kuramoto/docs/indicators.md:239:- **Trend Strength:** Combine Kuramoto R with Hurst H
substrates/kuramoto/docs/indicators.md:255:from core.indicators.kuramoto import KuramotoOrderFeature
substrates/kuramoto/docs/indicators.md:262:        KuramotoOrderFeature(name="R"),
substrates/kuramoto/docs/indicators.md:293:5. **Kuramoto ↔ Hurst:** High R suggests H > 0.5 (persistent synchronization)
substrates/kuramoto/docs/indicators.md:297:| Regime | Kuramoto R | Hurst H | Entropy ΔH | Ricci κ |
substrates/kuramoto/docs/indicators.md:321:- **Kuramoto:** Acebrón et al. (2005). The Kuramoto model. Rev. Mod. Phys.
```

## substrates/kuramoto/docs/math.md

_matches: 9_

```
substrates/kuramoto/docs/math.md:12:1. [Phase Synchronization & Kuramoto Model](#phase-synchronization--kuramoto-model)
substrates/kuramoto/docs/math.md:22:## Phase Synchronization & Kuramoto Model
substrates/kuramoto/docs/math.md:48:### Kuramoto Order Parameter
substrates/kuramoto/docs/math.md:73:- Kuramoto, Y. (1975). Self-entrainment of coupled non-linear oscillators. Lecture Notes in Physics, 39.
substrates/kuramoto/docs/math.md:74:- Acebrón, J. A., et al. (2005). The Kuramoto model. Reviews of Modern Physics, 77(1), 137.
substrates/kuramoto/docs/math.md:241:δ(t) = r(t) + γ·V(s_{t+1}) - V(s_t)
substrates/kuramoto/docs/math.md:285:1. Kuramoto, Y. (1984). Chemical Oscillations, Waves, and Turbulence. Springer.
substrates/kuramoto/docs/math.md:291:1. Acebrón, J. A., et al. (2005). The Kuramoto model. Reviews of Modern Physics, 77(1).
substrates/kuramoto/docs/math.md:315:- **Kuramoto:** `core/indicators/kuramoto.py`
```

## substrates/kuramoto/docs/math/inventory.md

_matches: 85_

```
substrates/kuramoto/docs/math/inventory.md:20:### Kuramoto phase + order parameter (`core/indicators/kuramoto.py`)
substrates/kuramoto/docs/math/inventory.md:21:- **Symbolic name:** Observed in code: analytic signal phase \(\theta(t) = \arg(x + i\,\mathcal{H}\{x\})\) and Kuramoto order parameter \(R = |\frac{1}{N}\sum e^{i\theta_j}|\). (core/indicators/kuramoto.py:245-319, 397-483)
substrates/kuramoto/docs/math/inventory.md:22:- **Code location(s):** `core/indicators/kuramoto.py` (functions and features), `core/indicators/trading.py` (wrappers). (core/indicators/kuramoto.py:1-772; core/indicators/trading.py:1-630)
substrates/kuramoto/docs/math/inventory.md:23:- **Type:** Observed in code: deterministic, discrete-time transforms on arrays. (core/indicators/kuramoto.py:245-562)
substrates/kuramoto/docs/math/inventory.md:24:- **Inputs/outputs:** Observed in code: 1D/2D arrays of real/complex phases, optional weights; outputs are phase arrays and \(R\) scalars/series. (core/indicators/kuramoto.py:245-562, 397-520)
substrates/kuramoto/docs/math/inventory.md:25:- **Implicit assumptions:** Observed in code: input arrays are 1D or 2D and finite after sanitization; weights broadcastable and non-negative. (core/indicators/kuramoto.py:332-351, 492-547)
substrates/kuramoto/docs/math/inventory.md:26:- **Known or suspected weaknesses:** Observed in code: denormal suppression (1e-8) and clipping to \([0,1]\) for \(R\). (core/indicators/kuramoto.py:142-147, 204-211, 454-480)
substrates/kuramoto/docs/math/inventory.md:29:- Functions: `compute_phase`, `kuramoto_order`, `_kuramoto_order_jit`, `_kuramoto_order_2d_jit`, `multi_asset_kuramoto`, `compute_phase_gpu`. (core/indicators/kuramoto.py:78-744)
substrates/kuramoto/docs/math/inventory.md:30:- Constants/thresholds: denormal threshold `1e-8` and clamp to `1.0`. (core/indicators/kuramoto.py:142-147, 204-211, 454-480)
substrates/kuramoto/docs/math/inventory.md:31:- Backend selection logic: SciPy fast-path, NumPy FFT fallback, CuPy GPU path. (core/indicators/kuramoto.py:344-387, 623-666)
substrates/kuramoto/docs/math/inventory.md:32:- Input validation: 1D/2D checks and `out` shape/dtype checks. (core/indicators/kuramoto.py:334-341, 492-512)
substrates/kuramoto/docs/math/inventory.md:35:- **Definition:** Observed in code: phase from analytic signal and order parameter from cosine/sine aggregation. (core/indicators/kuramoto.py:245-319, 397-419)
substrates/kuramoto/docs/math/inventory.md:36:- **Domain:** Observed in code: `compute_phase` expects 1D array and validates `out` shape/dtype; `kuramoto_order` expects 1D or 2D array. (core/indicators/kuramoto.py:334-341, 492-512)
substrates/kuramoto/docs/math/inventory.md:37:- **Range:** Observed in code: \(R\) clipped to \([0,1]\) with denormal suppression to 0.0. (core/indicators/kuramoto.py:142-147, 204-211, 454-480)
substrates/kuramoto/docs/math/inventory.md:38:- **Invariants:** Observed in code: non-finite inputs excluded from aggregation. (core/indicators/kuramoto.py:129-137, 514-519)
substrates/kuramoto/docs/math/inventory.md:39:- **Failure modes:** Observed in code: empty arrays return 0.0 or empty arrays; invalid shapes raise `ValueError`. (core/indicators/kuramoto.py:120-137, 334-341, 492-512, 354-356)
substrates/kuramoto/docs/math/inventory.md:40:- **Approximation notes:** Observed in code: Hilbert transform computed via FFT-based approximation when SciPy unavailable. (core/indicators/kuramoto.py:268-387)
substrates/kuramoto/docs/math/inventory.md:41:- **Complexity:** Observed in code: O(N log N) for Hilbert transform, O(N·T) for order parameter. (core/indicators/kuramoto.py:299-301, 458-460)
substrates/kuramoto/docs/math/inventory.md:42:- **Determinism:** Observed in code: no RNG usage in phase/order parameter functions. (core/indicators/kuramoto.py:245-562)
substrates/kuramoto/docs/math/inventory.md:44:### Multi-scale Kuramoto synchronization (`core/indicators/multiscale_kuramoto.py`)
substrates/kuramoto/docs/math/inventory.md:45:- **Symbolic name:** Observed in code: per-timeframe Kuramoto order parameter and cross-scale coherence with consensus \(R\). (core/indicators/multiscale_kuramoto.py:42-118, 400-520)
substrates/kuramoto/docs/math/inventory.md:46:- **Code location(s):** `core/indicators/multiscale_kuramoto.py`. (core/indicators/multiscale_kuramoto.py:1-768)
substrates/kuramoto/docs/math/inventory.md:47:- **Type:** Observed in code: deterministic, discrete-time resampling and aggregation. (core/indicators/multiscale_kuramoto.py:90-210, 400-650)
substrates/kuramoto/docs/math/inventory.md:48:- **Inputs/outputs:** Observed in code: `DatetimeIndex` price series; outputs `MultiScaleResult` with consensus and coherence. (core/indicators/multiscale_kuramoto.py:90-160, 430-520)
substrates/kuramoto/docs/math/inventory.md:49:- **Implicit assumptions:** Observed in code: `DatetimeIndex` required for resampling; forward-fill used. (core/indicators/multiscale_kuramoto.py:99-124, 146-169)
substrates/kuramoto/docs/math/inventory.md:50:- **Known or suspected weaknesses:** Observed in code: resampling forward-fill determines derived series. (core/indicators/multiscale_kuramoto.py:146-169)
substrates/kuramoto/docs/math/inventory.md:53:- Functions/classes: `FractalResampler`, `MultiScaleKuramoto`, `TimeFrame`, `MultiScaleResult`. (core/indicators/multiscale_kuramoto.py:35-520)
substrates/kuramoto/docs/math/inventory.md:54:- Constants/thresholds: timeframe enum values (seconds). (core/indicators/multiscale_kuramoto.py:40-68)
substrates/kuramoto/docs/math/inventory.md:55:- Backend selection logic: optional SciPy signal module imported and used when available. (core/indicators/multiscale_kuramoto.py:28-34, 280-310)
substrates/kuramoto/docs/math/inventory.md:56:- Input validation: `DatetimeIndex` enforced in `FractalResampler.__post_init__`. (core/indicators/multiscale_kuramoto.py:99-108)
substrates/kuramoto/docs/math/inventory.md:59:- **Definition:** Observed in code: compute per-timeframe Kuramoto \(R\) and cross-scale coherence from resampled series. (core/indicators/multiscale_kuramoto.py:400-520)
substrates/kuramoto/docs/math/inventory.md:60:- **Domain:** Observed in code: `DatetimeIndex` series, resample frequencies from `TimeFrame`. (core/indicators/multiscale_kuramoto.py:99-124, 40-68)
substrates/kuramoto/docs/math/inventory.md:61:- **Range:** Observed in code: coherence and \(R\) values are derived from cos/sin aggregation and clipped in underlying Kuramoto computations. (core/indicators/multiscale_kuramoto.py:400-520; core/indicators/kuramoto.py:142-147, 204-211)
substrates/kuramoto/docs/math/inventory.md:62:- **Invariants:** Observed in code: cached resamples reused for deterministic reuse ratio. (core/indicators/multiscale_kuramoto.py:123-209)
substrates/kuramoto/docs/math/inventory.md:63:- **Failure modes:** Observed in code: resampling errors may raise `ValueError` when `strict=True`. (core/indicators/multiscale_kuramoto.py:186-205)
substrates/kuramoto/docs/math/inventory.md:64:- **Approximation notes:** Observed in code: uses resampling + last/ffill to construct coarser series. (core/indicators/multiscale_kuramoto.py:146-169)
substrates/kuramoto/docs/math/inventory.md:65:- **Complexity:** Observed in code: resample loops over requested timeframes. (core/indicators/multiscale_kuramoto.py:173-205)
substrates/kuramoto/docs/math/inventory.md:66:- **Determinism:** Observed in code: no RNG usage. (core/indicators/multiscale_kuramoto.py:1-520)
substrates/kuramoto/docs/math/inventory.md:116:### Kuramoto–Ricci composite regime classifier (`core/indicators/kuramoto_ricci_composite.py`)
substrates/kuramoto/docs/math/inventory.md:117:- **Symbolic name:** Observed in code: rule-based phase classifier and signals derived from \(R\), coherence, curvature, and transition score. (core/indicators/kuramoto_ricci_composite.py:34-200)
substrates/kuramoto/docs/math/inventory.md:118:- **Code location(s):** `core/indicators/kuramoto_ricci_composite.py`. (core/indicators/kuramoto_ricci_composite.py:1-320)
substrates/kuramoto/docs/math/inventory.md:119:- **Type:** Observed in code: deterministic decision logic. (core/indicators/kuramoto_ricci_composite.py:34-200)
substrates/kuramoto/docs/math/inventory.md:120:- **Inputs/outputs:** Observed in code: `MultiScaleResult`, `TemporalRicciResult`, static Ricci; outputs `CompositeSignal`. (core/indicators/kuramoto_ricci_composite.py:106-200)
substrates/kuramoto/docs/math/inventory.md:121:- **Implicit assumptions:** Observed in code: fixed threshold parameters passed at initialization. (core/indicators/kuramoto_ricci_composite.py:44-70)
substrates/kuramoto/docs/math/inventory.md:122:- **Known or suspected weaknesses:** Observed in code: threshold-based logic (PROXY for continuous dynamics). (core/indicators/kuramoto_ricci_composite.py:72-151)
substrates/kuramoto/docs/math/inventory.md:125:- Functions/classes: `KuramotoRicciComposite`, `CompositeSignal`, `MarketPhase`. (core/indicators/kuramoto_ricci_composite.py:18-200)
substrates/kuramoto/docs/math/inventory.md:126:- Constants/thresholds: default thresholds in `KuramotoRicciComposite.__init__`. (core/indicators/kuramoto_ricci_composite.py:44-70)
substrates/kuramoto/docs/math/inventory.md:127:- Backend selection logic: none observed. (core/indicators/kuramoto_ricci_composite.py:1-200)
substrates/kuramoto/docs/math/inventory.md:128:- Input validation: none observed. (core/indicators/kuramoto_ricci_composite.py:1-200)
substrates/kuramoto/docs/math/inventory.md:131:- **Definition:** Observed in code: phase = rule on \(R\), curvature, transition; confidence/entry/exit/risk computed via piecewise formulas. (core/indicators/kuramoto_ricci_composite.py:72-151)
substrates/kuramoto/docs/math/inventory.md:132:- **Domain:** Observed in code: expects scalar metrics from upstream results. (core/indicators/kuramoto_ricci_composite.py:106-140)
substrates/kuramoto/docs/math/inventory.md:133:- **Range:** Observed in code: confidence, entry, exit, risk are clipped to fixed bounds. (core/indicators/kuramoto_ricci_composite.py:86-151)
substrates/kuramoto/docs/math/inventory.md:134:- **Invariants:** Observed in code: output signal fields populated for every call. (core/indicators/kuramoto_ricci_composite.py:106-140)
substrates/kuramoto/docs/math/inventory.md:135:- **Failure modes:** Not in code; removed. (core/indicators/kuramoto_ricci_composite.py:1-320)
substrates/kuramoto/docs/math/inventory.md:136:- **Approximation notes:** PROXY: phase classification uses threshold logic rather than continuous model. (core/indicators/kuramoto_ricci_composite.py:72-151)
substrates/kuramoto/docs/math/inventory.md:137:- **Complexity:** Not in code; removed. (core/indicators/kuramoto_ricci_composite.py:1-320)
substrates/kuramoto/docs/math/inventory.md:138:- **Determinism:** Observed in code: no RNG usage. (core/indicators/kuramoto_ricci_composite.py:1-200)
substrates/kuramoto/docs/math/inventory.md:261:- **Symbolic name:** Observed in code: entropy, Hurst, Kuramoto, and microstructure features computed per timeframe. (core/indicators/hierarchical_features.py:88-260)
substrates/kuramoto/docs/math/inventory.md:275:- **Definition:** Observed in code: entropy via histogram counts, Kuramoto via phase aggregation, Hurst via `hurst_exponent`. (core/indicators/hierarchical_features.py:46-260)
substrates/kuramoto/docs/math/inventory.md:277:- **Range:** Observed in code: entropy returns 0.0 on invalid input; Kuramoto clipped via underlying functions. (core/indicators/hierarchical_features.py:46-80, 170-210; core/indicators/kuramoto.py:142-147)
substrates/kuramoto/docs/math/inventory.md:333:- **Symbolic name:** Observed in code: Kuramoto \(R\), Hurst \(H\), VPIN. (core/indicators/trading.py:331-626)
substrates/kuramoto/docs/math/inventory.md:341:- Functions/classes: `KuramotoIndicator`, `HurstIndicator`, `VPINIndicator`. (core/indicators/trading.py:331-626)
substrates/kuramoto/docs/math/inventory.md:347:- **Definition:** Observed in code: wrappers call underlying Kuramoto/Hurst/VPIN computations. (core/indicators/trading.py:364-626)
substrates/kuramoto/docs/math/inventory.md:349:- **Range:** Observed in code: Kuramoto and Hurst outputs rely on underlying bounded outputs. (core/indicators/trading.py:364-504; core/indicators/kuramoto.py:142-147; core/indicators/hurst.py:430-450)
substrates/kuramoto/docs/math/inventory.md:364:- **Inputs/outputs:** Observed in code: return observation, Kuramoto \(R\), Ricci \(\kappa\), optional entropy; outputs pulse and precision. (core/neuro/amm.py:120-190)
substrates/kuramoto/docs/math/inventory.md:375:- **Definition:** Observed in code: EMA prediction, EW variance, precision \(\pi\) from variance/entropy/Kuramoto/Ricci, pulse from tanh and homeostasis. (core/neuro/amm.py:120-190)
substrates/kuramoto/docs/math/inventory.md:756:### Kuramoto synchrony adapter (`src/tradepulse/features/kuramoto.py`)
substrates/kuramoto/docs/math/inventory.md:757:- **Symbolic name:** Observed in code: Kuramoto order parameter \(R\) and \(\Delta R\). (src/tradepulse/features/kuramoto.py:90-160)
substrates/kuramoto/docs/math/inventory.md:758:- **Code location(s):** `src/tradepulse/features/kuramoto.py`. (src/tradepulse/features/kuramoto.py:1-180)
substrates/kuramoto/docs/math/inventory.md:759:- **Type:** Observed in code: deterministic. (src/tradepulse/features/kuramoto.py:60-160)
substrates/kuramoto/docs/math/inventory.md:760:- **Inputs/outputs:** Observed in code: price DataFrame; outputs series for R, delta_R, labels. (src/tradepulse/features/kuramoto.py:70-160)
substrates/kuramoto/docs/math/inventory.md:761:- **Implicit assumptions:** Observed in code: `DatetimeIndex` required; window length must be <= data length. (src/tradepulse/features/kuramoto.py:82-100)
substrates/kuramoto/docs/math/inventory.md:762:- **Known or suspected weaknesses:** Observed in code: PROXY phase computed via arctan of rolling stats (simplified). (src/tradepulse/features/kuramoto.py:110-136)
substrates/kuramoto/docs/math/inventory.md:765:- Functions/classes: `KuramotoSynchrony`, `KuramotoResult`. (src/tradepulse/features/kuramoto.py:17-160)
substrates/kuramoto/docs/math/inventory.md:766:- Constants/thresholds: default thresholds in constructor. (src/tradepulse/features/kuramoto.py:36-66)
substrates/kuramoto/docs/math/inventory.md:767:- Backend selection logic: none observed. (src/tradepulse/features/kuramoto.py:1-160)
substrates/kuramoto/docs/math/inventory.md:768:- Input validation: `DatetimeIndex` and length check. (src/tradepulse/features/kuramoto.py:82-100)
substrates/kuramoto/docs/math/inventory.md:771:- **Definition:** Observed in code: compute phases, \(R\), \(\Delta R\), label via rolling thresholds. (src/tradepulse/features/kuramoto.py:104-160)
substrates/kuramoto/docs/math/inventory.md:772:- **Domain:** Observed in code: DatetimeIndex and sufficient length. (src/tradepulse/features/kuramoto.py:82-100)
substrates/kuramoto/docs/math/inventory.md:773:- **Range:** Observed in code: \(R\) is magnitude of mean complex phase. (src/tradepulse/features/kuramoto.py:122-140)
... [5 more lines omitted; see audit/pre_closure_scan.txt]
```

## substrates/kuramoto/docs/monitoring.md

_matches: 1_

```
substrates/kuramoto/docs/monitoring.md:372:        'indicator': 'kuramoto',
```

## substrates/kuramoto/docs/neuro_optimization_guide.md

_matches: 1_

```
substrates/kuramoto/docs/neuro_optimization_guide.md:489:        'discount_gamma': 0.99,
```

## substrates/kuramoto/docs/neurodecision_stack.md

_matches: 2_

```
substrates/kuramoto/docs/neurodecision_stack.md:26:- **RPE**: \( \delta_t = r_t + \gamma V_{t+1} - V_t \), with \(\lambda = 0\).
substrates/kuramoto/docs/neurodecision_stack.md:38:| Dopamine | `discount_gamma`, `burst_factor`, `base_temperature`, `rpe_var_release_threshold` | TD learning, phasic scaling, exploration temperature, and release gate tuning. |
```

## substrates/kuramoto/docs/neuroecon.md

_matches: 3_

```
substrates/kuramoto/docs/neuroecon.md:20:    gamma: float = 0.95,
substrates/kuramoto/docs/neuroecon.md:33:- `gamma`: коефіцієнт дисконтування майбутніх нагород.
substrates/kuramoto/docs/neuroecon.md:55:core = AdvancedNeuroEconCore(hidden_dim=32, gamma=0.9, alpha=0.05)
```

## substrates/kuramoto/docs/neuromodulators/dopamine.md

_matches: 6_

```
substrates/kuramoto/docs/neuromodulators/dopamine.md:52:    discount_gamma: Optional[float] = None,
substrates/kuramoto/docs/neuromodulators/dopamine.md:78:δ = r + γ·V' − V
substrates/kuramoto/docs/neuromodulators/dopamine.md:82:- γ ∈ (0, 1] (strictly positive)
substrates/kuramoto/docs/neuromodulators/dopamine.md:84:- sign(δ) matches sign(r) when V'≈V and γ=1
substrates/kuramoto/docs/neuromodulators/dopamine.md:90:    rpe = r + gamma * next_value - value
substrates/kuramoto/docs/neuromodulators/dopamine.md:324:- `gamma ∈ (0, 1]`
```

## substrates/kuramoto/docs/neuromodulators/dopamine_v1_enhancements.md

_matches: 8_

```
substrates/kuramoto/docs/neuromodulators/dopamine_v1_enhancements.md:32:- Strict γ ∈ (0, 1] validation (was [0, 1])
substrates/kuramoto/docs/neuromodulators/dopamine_v1_enhancements.md:39:rpe = r + gamma * next_value - value
substrates/kuramoto/docs/neuromodulators/dopamine_v1_enhancements.md:43:    rpe = float(reward + gamma * next_value - value)
substrates/kuramoto/docs/neuromodulators/dopamine_v1_enhancements.md:45:    context = {"reward": reward, "value": value, "next_value": next_value, "gamma": gamma}
substrates/kuramoto/docs/neuromodulators/dopamine_v1_enhancements.md:106:self._cache_discount_gamma
substrates/kuramoto/docs/neuromodulators/dopamine_v1_enhancements.md:222:4. **Strict Validation** - γ strictly in (0, 1], not [0, 1]
substrates/kuramoto/docs/neuromodulators/dopamine_v1_enhancements.md:320:- RPE validation: γ ∈ (0, 1] (was [0, 1])
substrates/kuramoto/docs/neuromodulators/dopamine_v1_enhancements.md:332:- Stricter γ validation may reject edge cases
```

## substrates/kuramoto/docs/neuromodulators_dopamine.md

_matches: 4_

```
substrates/kuramoto/docs/neuromodulators_dopamine.md:7:1. **TD(0) RPE** – `δ = r + γ · V' − V` із λ = 0 та насиченням `γ ∈ (0, 1]`.
substrates/kuramoto/docs/neuromodulators_dopamine.md:29:| `rpe` | TD(0) помилка з останнім застосованим `discount_gamma`. |
substrates/kuramoto/docs/neuromodulators_dopamine.md:72:| TD / Value | `discount_gamma`, `learning_rate_v` | TD(0) оцінка вартості. |
substrates/kuramoto/docs/neuromodulators_dopamine.md:82:Конфігурація проходить сувору валідацію: наявність усіх ключів, діапазони (`temp_adapt_min_base ≤ temp_adapt_max_base`, `discount_gamma ∈ (0, 1]`, `ddm_eps > 0` тощо) та відсутність сторонніх полів.
```

## substrates/kuramoto/docs/operational_handbook.md

_matches: 1_

```
substrates/kuramoto/docs/operational_handbook.md:168:  [`tests/unit/indicators/test_kuramoto_fallbacks.py`](../tests/unit/indicators/test_kuramoto_fallbacks.py)
```

## substrates/kuramoto/docs/performance.md

_matches: 2_

```
substrates/kuramoto/docs/performance.md:47:from core.indicators.kuramoto import compute_phase, KuramotoOrderFeature
substrates/kuramoto/docs/performance.md:370:from core.indicators.kuramoto import compute_phase_gpu
```

## substrates/kuramoto/docs/quality_gates.md

_matches: 1_

```
substrates/kuramoto/docs/quality_gates.md:29:   `configs/quality/heavy_math_jobs.yaml` execute Kuramoto, Ricci, and Hurst
```

## substrates/kuramoto/docs/quickstart.md

_matches: 4_

```
substrates/kuramoto/docs/quickstart.md:72:python -c "from core.indicators.kuramoto import compute_phase; print('OK')"
substrates/kuramoto/docs/quickstart.md:147:from core.indicators.kuramoto import compute_phase, kuramoto_order
substrates/kuramoto/docs/quickstart.md:157:R = kuramoto_order(phases[-200:])
substrates/kuramoto/docs/quickstart.md:162:print(f"Kuramoto Order: {R:.3f}")
```

## substrates/kuramoto/docs/releases/v0.1.0.md

_matches: 4_

```
substrates/kuramoto/docs/releases/v0.1.0.md:12:- **Kuramoto Synchronization** — Detecting collective oscillation patterns in price dynamics
substrates/kuramoto/docs/releases/v0.1.0.md:22:- **50+ Indicators** — Geometric (Kuramoto, Ricci) + classical technical indicators
substrates/kuramoto/docs/releases/v0.1.0.md:58:from core.indicators.kuramoto_ricci_composite import TradePulseCompositeEngine
substrates/kuramoto/docs/releases/v0.1.0.md:134:- Synchronization theory (Kuramoto model)
```

## substrates/kuramoto/docs/requirements/traceability_matrix.md

_matches: 1_

```
substrates/kuramoto/docs/requirements/traceability_matrix.md:7:| REQ-001 | Fractal Indicator Composition | [`core/indicators/fractal_gcl.py`](../../core/indicators/fractal_gcl.py), [`core/indicators/multiscale_kuramoto.py`](../../core/indicators/multiscale_kuramoto.py) | N/A | N/A | [Dataset Catalog](../dataset_catalog.md) | [MLOps Orchestration](../devops/mlops-orchestration.md) | [Operational Readiness](../operational_readiness_runbooks.md), [Model Rollback](../runbook_model_rollback.md) | [`tests/test_fractal_gcl.py`](../../tests/test_fractal_gcl.py), [`tests/unit/test_indicators_kuramoto_multiscale.py`](../../tests/unit/test_indicators_kuramoto_multiscale.py) |
```

## substrates/kuramoto/docs/roadmap/platform_initiatives.md

_matches: 1_

```
substrates/kuramoto/docs/roadmap/platform_initiatives.md:49:  2. Patch build scripts (Python, Rust, Go) for cross-compilation and universal binary output.
```

## substrates/kuramoto/docs/runbook_data_incident.md

_matches: 1_

```
substrates/kuramoto/docs/runbook_data_incident.md:55:3. Execute comparative indicator checks to ensure derived features (Kuramoto,
```

## substrates/kuramoto/docs/spec_fhmc.md

_matches: 1_

```
substrates/kuramoto/docs/spec_fhmc.md:49:\delta_r=r+\gamma V(s')-V(s),\quad
```

## substrates/kuramoto/docs/thermodynamics/METRICS_FORMALIZATION.md

_matches: 2_

```
substrates/kuramoto/docs/thermodynamics/METRICS_FORMALIZATION.md:240:Q(s, a) ← Q(s, a) + α · [r + γ · max_a' Q(s', a') - Q(s, a)]
substrates/kuramoto/docs/thermodynamics/METRICS_FORMALIZATION.md:245:- **γ**: Discount factor (0.95)
```

## substrates/kuramoto/docs/troubleshooting.md

_matches: 2_

```
substrates/kuramoto/docs/troubleshooting.md:118:from core.indicators.kuramoto import compute_phase  # No GPU
substrates/kuramoto/docs/troubleshooting.md:585:from core.indicators.kuramoto import compute_phase_gpu
```

## substrates/kuramoto/docs/ui_what_if.md

_matches: 1_

```
substrates/kuramoto/docs/ui_what_if.md:18:- **Parameter panel** – Sliders and numeric inputs grouped by indicator (Kuramoto,
```

## substrates/kuramoto/examples/README.md

_matches: 3_

```
substrates/kuramoto/examples/README.md:22:- Basic indicator usage (Kuramoto, Entropy)
substrates/kuramoto/examples/README.md:84:- Kuramoto-Ricci composite analysis
substrates/kuramoto/examples/README.md:210:  Kuramoto Order: 0.7234
```

## substrates/kuramoto/interfaces/README.md

_matches: 2_

```
substrates/kuramoto/interfaces/README.md:191:- **Multi-Indicator Analysis**: Kuramoto, Entropy, Hurst, Ricci
substrates/kuramoto/interfaces/README.md:354:    print(f"Kuramoto Order: {analysis['R']}")
```

## substrates/kuramoto/neurotrade_pro/NEURO-MODEL-MAPPING.md

_matches: 1_

```
substrates/kuramoto/neurotrade_pro/NEURO-MODEL-MAPPING.md:12:- EMH triggers: hypoxia/VEGF, infection & IFNγ/STAT1, C/EBPβ emergency granulopoiesis, CXCL12/CXCR4 axis, cytokines (G/GM-CSF, IL-6, EPO), TLR→G-CSF.
```

## substrates/kuramoto/neurotrade_pro/conf/config.yml

_matches: 1_

```
substrates/kuramoto/neurotrade_pro/conf/config.yml:4:  gamma: 0.05
```

## substrates/kuramoto/reports/ENGINEERING_REPORT.md

_matches: 4_

```
substrates/kuramoto/reports/ENGINEERING_REPORT.md:64:  - Kuramoto fallbacks: 10 tests
substrates/kuramoto/reports/ENGINEERING_REPORT.md:152:| kuramoto.compute_phase[128k] | 4.831ms | 9.304ms | -48.08% | ✅ OK |
substrates/kuramoto/reports/ENGINEERING_REPORT.md:153:| kuramoto.order[4096x12] | 0.618ms | 2.350ms | -73.71% | ✅ OK |
substrates/kuramoto/reports/ENGINEERING_REPORT.md:157:- **test_kuramoto_order_matrix**: 617.81μs median (1,617.76 ops/sec)
```

## substrates/kuramoto/reports/RELEASE_READINESS_REPORT.md

_matches: 5_

```
substrates/kuramoto/reports/RELEASE_READINESS_REPORT.md:79:  - Kuramoto fallbacks
substrates/kuramoto/reports/RELEASE_READINESS_REPORT.md:91:- `core.indicators.kuramoto`: 93%+ ✅
substrates/kuramoto/reports/RELEASE_READINESS_REPORT.md:115:| kuramoto.compute_phase[128k] | 4.831ms | 9.304ms | -48.08% | ✅ OK |
substrates/kuramoto/reports/RELEASE_READINESS_REPORT.md:116:| kuramoto.order[4096x12] | 0.618ms | 2.350ms | -73.71% | ✅ OK |
substrates/kuramoto/reports/RELEASE_READINESS_REPORT.md:414:- **Geometric Market Indicators:** Kuramoto oscillators, Ricci flow, entropy measures
```

## substrates/kuramoto/reports/RELIABILITY_PERF_AUDIT.md

_matches: 2_

```
substrates/kuramoto/reports/RELIABILITY_PERF_AUDIT.md:90:- `core/indicators/` – Technical indicators (Ricci, Kuramoto, etc.)
substrates/kuramoto/reports/RELIABILITY_PERF_AUDIT.md:706:   - Kuramoto oscillators: `@njit(cache=True, fastmath=True)` in `core/indicators/kuramoto.py`
```

## substrates/kuramoto/reports/TECH_DEBT_REGISTRY.md

_matches: 4_

```
substrates/kuramoto/reports/TECH_DEBT_REGISTRY.md:23:  - Локація: `core/indicators/__init__.py`, `core/indicators/multiscale_kuramoto.py`  
substrates/kuramoto/reports/TECH_DEBT_REGISTRY.md:24:  - Опис / Причина: Публічний API експортує `MultiScaleKuramotoFeature`, `TimeFrame`, `WaveletWindowSelector`, яких модуль не надає; імпорт ламає весь пакет.  
substrates/kuramoto/reports/TECH_DEBT_REGISTRY.md:33:  - Локація: `core/indicators/multiscale_kuramoto.py`  
substrates/kuramoto/reports/TECH_DEBT_REGISTRY.md:43:  - Локація: `core/indicators/multiscale_kuramoto.py`  
```

## substrates/kuramoto/reports/ci_cd_health_review.md

_matches: 1_

```
substrates/kuramoto/reports/ci_cd_health_review.md:13:- Within the indicators package, files such as `multiscale_kuramoto.py`, `temporal_ricci.py`, and `kuramoto.py` are highlighted as critical due to missing fallback-path tests and edge-case coverage.
```

## substrates/kuramoto/reports/coverage_analysis_report.md

_matches: 6_

```
substrates/kuramoto/reports/coverage_analysis_report.md:7:The latest regression run focused on the reliability-critical surface area that guards live trading cutovers: the Kuramoto
substrates/kuramoto/reports/coverage_analysis_report.md:24:_Source_: `pytest tests/unit/indicators/test_kuramoto_fallbacks.py tests/unit/utils/test_security.py tests/unit/utils/test_slo.py --cov=core.indicators.kuramoto --cov=core.utils.security --cov=core.utils.slo`【c97d7a†L1-L8】
substrates/kuramoto/reports/coverage_analysis_report.md:30:| `core.indicators.kuramoto` | 92.00 % | 92 / 100 | 8 | ▲ +8.42 pp | GPU and FFT fallbacks plus feature wrappers covered.【F:tests/unit/indicators/test_kuramoto_fallbacks.py†L1-L166】 |
substrates/kuramoto/reports/coverage_analysis_report.md:37:### `core.indicators.kuramoto`
substrates/kuramoto/reports/coverage_analysis_report.md:39:  float32 metadata paths, ensuring degraded modes emit metrics and remain numerically stable.【F:tests/unit/indicators/test_kuramoto_fallbacks.py†L1-L166】【F:core/indicators/kuramoto.py†L1-L189】
substrates/kuramoto/reports/coverage_analysis_report.md:67:   `configs/quality/critical_surface.toml` to ensure the Kuramoto indicator,
```

## substrates/kuramoto/reports/prod_cutover_readiness_checklist.md

_matches: 3_

```
substrates/kuramoto/reports/prod_cutover_readiness_checklist.md:14:- [x] **Operational metrics exported** – Kuramoto feature instrumentation emits structured metrics for collectors.
substrates/kuramoto/reports/prod_cutover_readiness_checklist.md:17:- [x] **Coverage guard** – Reliability-critical modules (`kuramoto`, `slo`, `security`) maintain >93% unit test coverage.
substrates/kuramoto/reports/prod_cutover_readiness_checklist.md:25:- [x] **Indicator degradation** – Kuramoto GPU fallback and CPU-only execution paths validated via dedicated unit tests.
```

## substrates/kuramoto/reports/release_readiness.md

_matches: 3_

```
substrates/kuramoto/reports/release_readiness.md:4:TradePulse provides a functional core for algorithmic trading — including indicator computation, a walk-forward backtester, and a CLI that links indicators to execution workflows — but the project is **not yet ready for a production-grade release**. The latest sprint tightened operational guardrails: reliability-critical modules (`core.indicators.kuramoto`, `core.utils.slo`, and `core.utils.security`) now sit above 93 % unit coverage, GPU fallbacks and auto-rollback flows are regression-tested, and a production cutover readiness checklist formalises SLO, alerting, on-call, and incident playbook expectations. Nevertheless, broader platform coverage remains well below the 98 % target and several product-facing capabilities are incomplete.
substrates/kuramoto/reports/release_readiness.md:12:- **Coverage below strategic target.** Core reliability surfaces now exceed 93 % coverage, but the overall codebase still sits near 67 %, far from the documented 98 % ambition. Focus next on backtest/execution stratification and data ingestion paths. 【F:tests/unit/indicators/test_kuramoto_fallbacks.py†L1-L166】【F:tests/unit/utils/test_slo.py†L1-L104】【F:tests/unit/utils/test_security.py†L1-L60】【c97d7a†L1-L8】
substrates/kuramoto/reports/release_readiness.md:23:- **Monitoring & alerting** – Kuramoto GPU fallback emits warnings, metric collectors are exercised in tests, and alert coverage is itemised in the readiness checklist. 【F:core/indicators/kuramoto.py†L1-L189】【F:tests/unit/indicators/test_kuramoto_fallbacks.py†L1-L166】【F:reports/prod_cutover_readiness_checklist.md†L24-L31】
```

## substrates/kuramoto/reports/technical_debt_assessment.md

_matches: 4_

```
substrates/kuramoto/reports/technical_debt_assessment.md:4:- `pytest` fails during import because `core.indicators.multiscale_kuramoto` does not define the symbols exported in `core.indicators.__init__` (`MultiScaleKuramotoFeature`, `TimeFrame`, and `WaveletWindowSelector`). This makes the entire indicator package unusable for the multi-scale workflow and blocks the integration test suite.【F:core/indicators/__init__.py†L15-L74】【F:core/indicators/multiscale_kuramoto.py†L1-L155】【077c7e†L1-L17】
substrates/kuramoto/reports/technical_debt_assessment.md:7:- The multi-scale Kuramoto module only implements procedural helpers and a `MultiScaleKuramoto` class. It never exposes a feature wrapper or the time-frame utilities promised by the public API, so higher-level blocks cannot be composed from it.【F:core/indicators/multiscale_kuramoto.py†L1-L155】
substrates/kuramoto/reports/technical_debt_assessment.md:8:- `MultiScaleKuramoto.analyze` silently skips any timeframe with fewer than `window + 5` samples and returns zero consensus without signalling which scales were dropped, making downstream decisions opaque.【F:core/indicators/multiscale_kuramoto.py†L138-L155】
substrates/kuramoto/reports/technical_debt_assessment.md:9:- The autocorrelation window selector has no safeguards against constant price series beyond returning the minimum window, which can amplify noise on illiquid assets.【F:core/indicators/multiscale_kuramoto.py†L40-L62】
```

## substrates/kuramoto/scripts/README.md

_matches: 1_

```
substrates/kuramoto/scripts/README.md:114:- **[integrate_kuramoto_ricci.py](README_integrate_kuramoto_ricci.md)** - Run Kuramoto-Ricci composite integration pipeline
```

## substrates/kuramoto/scripts/README_export_tradepulse_schema.md

_matches: 1_

```
substrates/kuramoto/scripts/README_export_tradepulse_schema.md:55:- Nested structures (Kuramoto, Ricci, data sources, etc.)
```

## substrates/kuramoto/scripts/README_generate_sample_ohlcv.md

_matches: 1_

```
substrates/kuramoto/scripts/README_generate_sample_ohlcv.md:139:from core.indicators.kuramoto_ricci_composite import TradePulseCompositeEngine
```

## substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md

_matches: 28_

```
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:1:# integrate_kuramoto_ricci.py
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:3:Run the Kuramoto-Ricci composite integration pipeline for advanced market analysis.
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:7:This CLI utility executes the Kuramoto-Ricci composite integration pipeline, which combines:
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:8:- **Kuramoto oscillator synchronization**: Measures market coupling and phase transitions
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:19:python scripts/integrate_kuramoto_ricci.py \
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:26:python scripts/integrate_kuramoto_ricci.py \
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:28:  --config configs/kuramoto_ricci.yaml
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:34:python scripts/integrate_kuramoto_ricci.py \
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:36:  --output reports/kuramoto-ricci-$(date +%Y%m%d)
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:42:python scripts/integrate_kuramoto_ricci.py \
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:44:  --config-override kuramoto.coupling_strength=0.5 \
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:51:python scripts/integrate_kuramoto_ricci.py \
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:59:python scripts/integrate_kuramoto_ricci.py \
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:80:kuramoto:
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:93:  weight_kuramoto: 0.6
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:100:--config-override kuramoto.coupling_strength=0.5
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:101:--config-override composite.weight_kuramoto=0.7
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:108:- `composite_indicators.csv`: Combined Kuramoto-Ricci signals
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:109:- `kuramoto_analysis.json`: Synchronization metrics
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:127:python scripts/integrate_kuramoto_ricci.py \
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:137:python scripts/integrate_kuramoto_ricci.py \
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:140:  --config-override kuramoto.coupling_strength=0.8 \
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:148:python scripts/integrate_kuramoto_ricci.py \
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:158:  python scripts/integrate_kuramoto_ricci.py \
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:160:    --output reports/kuramoto-ricci/${asset} \
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:174:export KURAMOTO_RICCI_OUTPUT_DIR=/results/kuramoto-ricci
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:176:python scripts/integrate_kuramoto_ricci.py --data data/sample.csv
substrates/kuramoto/scripts/README_integrate_kuramoto_ricci.md:194:- Kuramoto coupling iterations
```

## substrates/kuramoto/scripts/README_smoke_e2e.md

_matches: 3_

```
substrates/kuramoto/scripts/README_smoke_e2e.md:12:- Indicator calculation (Kuramoto-Ricci composite)
substrates/kuramoto/scripts/README_smoke_e2e.md:91:- Incorporates Kuramoto-Ricci metrics
substrates/kuramoto/scripts/README_smoke_e2e.md:341:- `integrate_kuramoto_ricci.py`: Run detailed indicator analysis
```

## substrates/kuramoto/src/tradepulse/core/neuro/README_OPTIMIZATION.md

_matches: 1_

```
substrates/kuramoto/src/tradepulse/core/neuro/README_OPTIMIZATION.md:52:    'dopamine': {'discount_gamma': 0.99, 'learning_rate': 0.01},
```

## substrates/kuramoto/src/tradepulse/core/neuro/README_ORCHESTRATOR.md

_matches: 6_

```
substrates/kuramoto/src/tradepulse/core/neuro/README_ORCHESTRATOR.md:186:print(f"Discount Gamma: {output.learning_loop.discount_gamma}")
substrates/kuramoto/src/tradepulse/core/neuro/README_ORCHESTRATOR.md:238:    "discount_gamma": 0.99,
substrates/kuramoto/src/tradepulse/core/neuro/README_ORCHESTRATOR.md:263:    "discount_gamma": 0.99,
substrates/kuramoto/src/tradepulse/core/neuro/README_ORCHESTRATOR.md:267:    "update_rule": "delta = reward + gamma * V_next - V_current; V_current += learning_rate * delta"
substrates/kuramoto/src/tradepulse/core/neuro/README_ORCHESTRATOR.md:361:Update Rule: δ = r + γ·V' - V
substrates/kuramoto/src/tradepulse/core/neuro/README_ORCHESTRATOR.md:367:  γ = Discount factor (0.99)
```

## substrates/kuramoto/tests/TEST_PLAN.md

_matches: 1_

```
substrates/kuramoto/tests/TEST_PLAN.md:19:| Resilience scenarios | Restart safety, cache recovery | `tests/integration/test_market_cassettes.py`, `tests/unit/test_kuramoto_ricci_composite.py`, `tests/nightly/test_heavy_workflows.py::test_failover_recovery` | Market cassette recordings in `tests/fixtures/market_cassettes/` | Simulates degraded network and verifies signal history idempotency. |
```

## substrates/kuramoto/tests/performance/README.md

_matches: 2_

```
substrates/kuramoto/tests/performance/README.md:7:### kuramoto.compute_phase[128k]
substrates/kuramoto/tests/performance/README.md:14:### kuramoto.order[4096x12]
```

## substrates/kuramoto/tradepulse/neural_controller/INTEGRATION_PATCH.md

_matches: 3_

```
substrates/kuramoto/tradepulse/neural_controller/INTEGRATION_PATCH.md:10:    KuramotoSync,
substrates/kuramoto/tradepulse/neural_controller/INTEGRATION_PATCH.md:17:kuramoto = KuramotoSync()
substrates/kuramoto/tradepulse/neural_controller/INTEGRATION_PATCH.md:18:bridge = NeuralTACLBridge(neural, tacl, kuramoto)
```

## substrates/kuramoto/tradepulse/neural_controller/README.md

_matches: 4_

```
substrates/kuramoto/tradepulse/neural_controller/README.md:14:- TACL bridge with configurable generations plus Kuramoto-based synchrony throttle.
substrates/kuramoto/tradepulse/neural_controller/README.md:28:    KuramotoSync,
substrates/kuramoto/tradepulse/neural_controller/README.md:34:kuramoto = KuramotoSync()
substrates/kuramoto/tradepulse/neural_controller/README.md:35:bridge = NeuralTACLBridge(neural, tacl, kuramoto)
```

## substrates/kuramoto/tradepulse/neural_controller/config/neural_params.yaml

_matches: 1_

```
substrates/kuramoto/tradepulse/neural_controller/config/neural_params.yaml:7:  gamma: 0.05
```

## substrates/kuramoto/СТАН_РОЗВИТКУ_ПРОЄКТУ.md

_matches: 1_

```
substrates/kuramoto/СТАН_РОЗВИТКУ_ПРОЄКТУ.md:33:   - ✅ Geometric Market Intelligence (Kuramoto oscillators, Ricci flow, entropy measures)
```

## substrates/mfn/CHANGELOG.md

_matches: 6_

```
substrates/mfn/CHANGELOG.md:11:- **Interpretability Engine** — 6-component read-only auditor for gamma-scaling mechanism
substrates/mfn/CHANGELOG.md:20:  - gamma healthy=-5.753, pathological=-4.021, Cohen's d=39.4, p<0.0001
substrates/mfn/CHANGELOG.md:32:- **gamma-scaling**: Theil-Sen robust estimator + bootstrap CI95 + permutation p-value
substrates/mfn/CHANGELOG.md:37:- `_compute_gamma_robust()` — publication-grade gamma with full statistics
substrates/mfn/CHANGELOG.md:76:- **γ-scaling on real tissue**: γ = +1.487 on brain organoids (Zenodo 10301912)
substrates/mfn/CHANGELOG.md:85:- Kuramoto synchronization: `kuramoto_order_parameter()`, `kuramoto_trajectory()`
```

## substrates/mfn/MASTER_CONTEXT.md

_matches: 7_

```
substrates/mfn/MASTER_CONTEXT.md:68:| γ_organoid | +1.487 ± 0.208 | First measurement on real brain organoids |
substrates/mfn/MASTER_CONTEXT.md:91:| MFN+ | src/mycelium_fractal_net/ | Morphogenetic integrity + gamma-scaling |
substrates/mfn/MASTER_CONTEXT.md:94:  gamma emerges as CONSEQUENCE of inter-layer coherence.
substrates/mfn/MASTER_CONTEXT.md:96:  tau_control never reads gamma. interpretability reads gamma read-only, post-hoc.
substrates/mfn/MASTER_CONTEXT.md:105:# result.gamma_report.label: EMERGENT / NOT_EMERGED / INSUFFICIENT_DATA
substrates/mfn/MASTER_CONTEXT.md:109:  INV-1: NFIStateContract has no field named gamma
substrates/mfn/MASTER_CONTEXT.md:180:- **Phase 3 evidence** — real simulation gamma: healthy=-5.753, pathological=-4.021, Cohen's d=39.4
```

## substrates/mfn/README.md

_matches: 6_

```
substrates/mfn/README.md:59:| Kuramoto synchronization | -- | -- | -- | -- | -- | -- | **Yes** |
substrates/mfn/README.md:173:### Biological γ-Scaling (First Measurement on Real Tissue)
substrates/mfn/README.md:176:# γ measured on brain organoids (Zenodo 10301912): 64 organoids, 1407 images
substrates/mfn/README.md:177:# WT2D (healthy):     γ = +1.487 ± 0.208
substrates/mfn/README.md:178:# 3D spheroids:       γ = +0.721 (median)
substrates/mfn/README.md:379:├── analytics/      InvariantOperator, TDA, bifiltration, Kuramoto, entropy production
```

## substrates/mfn/RELEASE_NOTES.md

_matches: 4_

```
substrates/mfn/RELEASE_NOTES.md:11:- **Interpretability Engine** — 6-component read-only auditor: feature extraction (thermodynamic + topological + fractal + causal), attribution graphs, causal rule tracing, gamma diagnostics, linear state probes, PRR-ready reports.
substrates/mfn/RELEASE_NOTES.md:21:- **4 Mathematical Bug Fixes** — D_box adaptive Otsu threshold, equilibrium_distance normalization, gamma bootstrap CI95 + p-value, Gray-Scott potential mode.
substrates/mfn/RELEASE_NOTES.md:23:- **Phase 3 Real Simulation Evidence** — gamma healthy = -5.753 +/- 0.037 vs pathological = -4.021 +/- 0.050, Cohen's d = 39.4, p < 0.0001. 5 PRR tables generated.
substrates/mfn/RELEASE_NOTES.md:34:Architectural law: gamma is NEVER a control target. Recovery reads F, betti, D_box. Never gamma.
```

## substrates/mfn/docs/BIBLIOGRAPHY.md

_matches: 6_

```
substrates/mfn/docs/BIBLIOGRAPHY.md:40:| **Kuramoto sync** | `sync/` | Kuramoto 1984; Acebrón+ 2005 | F, A |
substrates/mfn/docs/BIBLIOGRAPHY.md:55:**[F2]** Kuramoto Y. (1984). *Chemical Oscillations, Waves, and Turbulence*. Springer. DOI: [10.1007/978-3-642-69689-3](https://doi.org/10.1007/978-3-642-69689-3)
substrates/mfn/docs/BIBLIOGRAPHY.md:56:Phase-oscillator coupling — Kuramoto synchronization module.
substrates/mfn/docs/BIBLIOGRAPHY.md:131:**[A18]** Acebrón J.A. et al. (2005). The Kuramoto model. *Rev. Mod. Phys.*, 77(1), 137--185. DOI: [10.1103/RevModPhys.77.137](https://doi.org/10.1103/RevModPhys.77.137)
substrates/mfn/docs/BIBLIOGRAPHY.md:132:Kuramoto review — synchronization measurement.
substrates/mfn/docs/BIBLIOGRAPHY.md:199:| Kuramoto 1984 | **x** | **x** | | **x** | | |
```

## substrates/mfn/docs/RELEASE_NOTES.md

_matches: 4_

```
substrates/mfn/docs/RELEASE_NOTES.md:11:- **Interpretability Engine** — 6-component read-only auditor: feature extraction (thermodynamic + topological + fractal + causal), attribution graphs, causal rule tracing, gamma diagnostics, linear state probes, PRR-ready reports.
substrates/mfn/docs/RELEASE_NOTES.md:21:- **4 Mathematical Bug Fixes** — D_box adaptive Otsu threshold, equilibrium_distance normalization, gamma bootstrap CI95 + p-value, Gray-Scott potential mode.
substrates/mfn/docs/RELEASE_NOTES.md:23:- **Phase 3 Real Simulation Evidence** — gamma healthy = -5.753 +/- 0.037 vs pathological = -4.021 +/- 0.050, Cohen's d = 39.4, p < 0.0001. 5 PRR tables generated.
substrates/mfn/docs/RELEASE_NOTES.md:34:Architectural law: gamma is NEVER a control target. Recovery reads F, betti, D_box. Never gamma.
```

## substrates/mfn/docs/RESULTS.md

_matches: 2_

```
substrates/mfn/docs/RESULTS.md:53:| Physarum | dD/dt = \|Q\|^γ − αD | Tero et al. (2010) *Science* 327:439 |
substrates/mfn/docs/RESULTS.md:54:| Anastomosis | dC/dt = D∇²C + S(B,C) − γRBC | Du et al. (2019) *J. Theor. Biol.* 462:354 |
```

## substrates/mfn/docs/THERMODYNAMIC_KERNEL.md

_matches: 4_

```
substrates/mfn/docs/THERMODYNAMIC_KERNEL.md:21:-0.05 < λ₁ < 0.05  →  METASTABLE  →  gate OPEN only if allow_metastable=True
substrates/mfn/docs/THERMODYNAMIC_KERNEL.md:26:**Why metastable matters:** Turing pattern formation IS a controlled instability.
substrates/mfn/docs/THERMODYNAMIC_KERNEL.md:67:    allow_metastable=True,      # allow Turing zone
substrates/mfn/docs/THERMODYNAMIC_KERNEL.md:76:# [THERMO] gate=OPEN verdict=metastable λ₁=-0.012 drift=4.2e-05 steps=60 adaptive=0
```

## substrates/mfn/docs/adr/0007-mwc-allosteric-model.md

_matches: 2_

```
substrates/mfn/docs/adr/0007-mwc-allosteric-model.md:29:- L₀ = 5000 (Chang et al. 1996, GABA-A α1β3γ2)
substrates/mfn/docs/adr/0007-mwc-allosteric-model.md:37:- EC50 is now ~8-12 μM for muscimol on α1β3γ2, matching published range (5-15 μM)
```

## substrates/mfn/docs/architecture/ARCHITECTURE_AUDIT.md

_matches: 1_

```
substrates/mfn/docs/architecture/ARCHITECTURE_AUDIT.md:16:├── interpretability/  # READ-ONLY: feature extraction, attribution, gamma diagnostics
```

## substrates/mfn/docs/architecture/DATA_CONTRACTS.md

_matches: 1_

```
substrates/mfn/docs/architecture/DATA_CONTRACTS.md:33:gamma (scaling)     ← gamma_diagnostic() OR _compute_gamma() → diagnostic string/dict
```

## substrates/mfn/docs/architecture/LAYERING_RULES.md

_matches: 3_

```
substrates/mfn/docs/architecture/LAYERING_RULES.md:34:4. **gamma is diagnostic output, never control input.**
substrates/mfn/docs/architecture/LAYERING_RULES.md:35:   No module in L7-L8 may use gamma as threshold, reward, or objective.
substrates/mfn/docs/architecture/LAYERING_RULES.md:44:- Tests: `test_tau_control.py::test_no_gamma_in_interface`
```

## substrates/mfn/results/zebrafish_real/zebrafish_gamma_report.md

_matches: 6_

```
substrates/mfn/results/zebrafish_real/zebrafish_gamma_report.md:1:# Zebrafish gamma-Scaling Validation Report
substrates/mfn/results/zebrafish_real/zebrafish_gamma_report.md:8:| Phenotype | gamma | R2 | p-value | CI95 | gamma~1.0? | Verdict |
substrates/mfn/results/zebrafish_real/zebrafish_gamma_report.md:16:gamma_organoid (Vasylenko 2026, Zenodo 10301912) = **1.487 +/- 0.208**
substrates/mfn/results/zebrafish_real/zebrafish_gamma_report.md:17:Wild-type gamma in organoid CI [1.279, 1.695]: **False**
substrates/mfn/results/zebrafish_real/zebrafish_gamma_report.md:23:> Hypothesis (Vasylenko-Levin-Tononi): Wild-type gamma ~ +1.0, Mutant gamma != 1.0.
substrates/mfn/results/zebrafish_real/zebrafish_gamma_report.md:31:- Vasylenko (2026) gamma-scaling on brain organoids. Zenodo 10301912
```

## substrates/mfn/results/zebrafish_validation/zebrafish_gamma_report.md

_matches: 6_

```
substrates/mfn/results/zebrafish_validation/zebrafish_gamma_report.md:1:# Zebrafish gamma-Scaling Validation Report
substrates/mfn/results/zebrafish_validation/zebrafish_gamma_report.md:8:| Phenotype | gamma | R2 | p-value | CI95 | gamma~1.0? | Verdict |
substrates/mfn/results/zebrafish_validation/zebrafish_gamma_report.md:16:gamma_organoid (Vasylenko 2026, Zenodo 10301912) = **1.487 +/- 0.208**
substrates/mfn/results/zebrafish_validation/zebrafish_gamma_report.md:17:Wild-type gamma in organoid CI [1.279, 1.695]: **False**
substrates/mfn/results/zebrafish_validation/zebrafish_gamma_report.md:23:> Hypothesis (Vasylenko-Levin-Tononi): Wild-type gamma ~ +1.0, Mutant gamma != 1.0.
substrates/mfn/results/zebrafish_validation/zebrafish_gamma_report.md:31:- Vasylenko (2026) gamma-scaling on brain organoids. Zenodo 10301912
```

## substrates/mlsdm/docs/APHASIA_SPEC.md

_matches: 2_

```
substrates/mlsdm/docs/APHASIA_SPEC.md:7:> **Implementation Note:** As of v1.2.0, the Aphasia-Broca detection and repair functionality is now implemented as a pluggable **Speech Governor** (`AphasiaSpeechGovernor`) that integrates with the universal Speech Governance framework in `LLMWrapper`. As of v1.3.0, the system uses `PipelineSpeechGovernor` for composable, deterministic governance pipelines with failure isolation. See the [Speech Governance](#speech-governance-integration) section for details.
substrates/mlsdm/docs/APHASIA_SPEC.md:598:**As of MLSDM v1.2.0**, Aphasia-Broca detection and repair is implemented as a pluggable **Speech Governor** that integrates with the universal Speech Governance framework.
```

## substrates/mlsdm/docs/ARCHITECTURE_SPEC.md

_matches: 1_

```
substrates/mlsdm/docs/ARCHITECTURE_SPEC.md:24:MLSDM (Multi-Level Synaptic Dynamic Memory) Governed Cognitive Memory is a neurobiologically-grounded cognitive architecture that provides universal LLM wrapping with moral governance, phase-based memory, cognitive rhythm enforcement, and language pathology detection via the Aphasia-Broca model [@benna2016_synaptic; @fusi2005_cascade; @gabriel2020_alignment].
```

## substrates/mlsdm/docs/DOCUMENTATION_FORMALIZATION_PROTOCOL.md

_matches: 1_

```
substrates/mlsdm/docs/DOCUMENTATION_FORMALIZATION_PROTOCOL.md:461:- Related: Theta-gamma coupling in NPC
```

## substrates/mlsdm/docs/IMPLEMENTATION_SUMMARY.md

_matches: 2_

```
substrates/mlsdm/docs/IMPLEMENTATION_SUMMARY.md:20:1. Create universal wrapper around ANY LLM with guarantees:
substrates/mlsdm/docs/IMPLEMENTATION_SUMMARY.md:477:**Branch**: copilot/create-universal-llm-wrapper
```

## substrates/mlsdm/docs/NEURO_FOUNDATIONS.md

_matches: 1_

```
substrates/mlsdm/docs/NEURO_FOUNDATIONS.md:60:- Multiple metastable states buffer against noise
```

## substrates/mlsdm/docs/SCIENTIFIC_RATIONALE.md

_matches: 1_

```
substrates/mlsdm/docs/SCIENTIFIC_RATIONALE.md:75:2. **Engineering Pragmatism**: Wrapper-based governance is universal (works with any LLM), interpretable (explicit constraint modules), and deployable (no model modification required).
```

## substrates/mlsdm/docs/bibliography/REFERENCES_APA7.md

_matches: 1_

```
substrates/mlsdm/docs/bibliography/REFERENCES_APA7.md:195:| Kuramoto 1984 | | | **x** | **x** | **x** | |
```

## substrates/serotonergic_kuramoto/CALIBRATION.md

_matches: 24_

```
substrates/serotonergic_kuramoto/CALIBRATION.md:1:# Serotonergic Kuramoto — Calibration Report
substrates/serotonergic_kuramoto/CALIBRATION.md:4:> See `evidence/gamma_provenance.md` for the tier definition.
substrates/serotonergic_kuramoto/CALIBRATION.md:8:> cross-concentration sweep yields γ ≈ 1.068, R² ≈ 0.58. This is not a
substrates/serotonergic_kuramoto/CALIBRATION.md:9:> knife-edge: γ ∈ [0.7, 1.3] holds over σ_op ∈ [0.058, 0.068] Hz — a
substrates/serotonergic_kuramoto/CALIBRATION.md:32:(R² ≈ 0, γ sign-indeterminate).
substrates/serotonergic_kuramoto/CALIBRATION.md:34:To make the spec-literal `K_base = 2.0` land on metastability, we
substrates/serotonergic_kuramoto/CALIBRATION.md:48:for γ. With σ_op = 0.065 Hz (empirical K_c ≈ 0.645 rad/s),
substrates/serotonergic_kuramoto/CALIBRATION.md:51:therefore **crosses the Kuramoto phase transition** (at c ≈ 0.96),
substrates/serotonergic_kuramoto/CALIBRATION.md:62:| γ (sweep, seed = 42) | 1.0677 |
substrates/serotonergic_kuramoto/CALIBRATION.md:71:at 0.002–0.004 Hz resolution and records γ, R² at every point:
substrates/serotonergic_kuramoto/CALIBRATION.md:73:| σ_op (Hz) | γ | R² | In [0.7, 1.3]? |
substrates/serotonergic_kuramoto/CALIBRATION.md:88:**Monotonicity:** γ is smooth and monotone in σ_op across the full
substrates/serotonergic_kuramoto/CALIBRATION.md:89:sweep. Successive |Δγ| values between adjacent grid points stay
substrates/serotonergic_kuramoto/CALIBRATION.md:94:independent of whether γ is in-basin. The log-log fit quality is a
substrates/serotonergic_kuramoto/CALIBRATION.md:106:2. **Seed fragility.** γ at the reference σ_op varies by more than 0.3
substrates/serotonergic_kuramoto/CALIBRATION.md:111:   permutation of its values across sweep points leaves γ unchanged.
substrates/serotonergic_kuramoto/CALIBRATION.md:113:4. **Non-monotonicity.** If a finer sweep reveals γ(σ) is not monotone
substrates/serotonergic_kuramoto/CALIBRATION.md:125:from substrates.serotonergic_kuramoto.adapter import (
substrates/serotonergic_kuramoto/CALIBRATION.md:126:    SerotonergicKuramotoAdapter, _sweep_gamma,
substrates/serotonergic_kuramoto/CALIBRATION.md:128:a = SerotonergicKuramotoAdapter(concentration=0.5, seed=42)
substrates/serotonergic_kuramoto/CALIBRATION.md:129:print(_sweep_gamma(a))   # expect (1.0677..., 0.5826...)
substrates/serotonergic_kuramoto/CALIBRATION.md:137:as strong evidence for γ ≈ 1 and that the serotonergic Kuramoto entry
substrates/serotonergic_kuramoto/CALIBRATION.md:138:is best read as "a calibrated model that is consistent with the γ ≈ 1
substrates/serotonergic_kuramoto/CALIBRATION.md:141:The provenance taxonomy in `evidence/gamma_provenance.md` reflects
```

## tools/audit/canon_reference_allowlist.yaml

_matches: 1_

```
tools/audit/canon_reference_allowlist.yaml:37:  - path: notebooks/levin_bridge/gamma_vs_horizon_analysis.ipynb
```
