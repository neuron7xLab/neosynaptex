# SERO v0.6 — SSDF/SLSA Compliance Mapping

**Version:** SERO v0.6 · NCE v0.5  
**Date:** 2026-03-01  
**Status:** Working draft — evidence artifacts linked to simulation outputs

---

## Purpose

This document maps every material SERO/NCE mechanism to (a) the corresponding NIST SSDF practice, (b) the SLSA supply-chain control, and (c) the evidence artifact that can be audited or reproduced. It is not a marketing declaration — it is a cross-reference table intended for procurement, security audit, and governance review.

**What this document is NOT:**  
SERO is a reference architecture, not a certified product. This mapping documents design intent and implemented behaviors. Independent validation against specific deployment environments is required before making compliance claims.

---

## 1. SSDF Mapping (NIST SP 800-218 v1.1)

SSDF is organized into four practice groups: **PW** (Produce Well-Secured Software), **PO** (Prepare the Organization), **RV** (Respond to Vulnerabilities), **PS** (Protect the Software).

### 1.1 PW — Produce Well-Secured Software

| SSDF Practice | SSDF Sub-Practice | SERO/NCE Mechanism | Evidence Artifact | Status |
|---|---|---|---|---|
| PW.1 — Security Requirements | PW.1.1: Define security requirements | Eq.4 safety invariant (T(t) ≥ T_min > 0) defines non-negotiable operational floor | `sero_m1_coupled.py` `verify_invariants()` | ✓ Implemented |
| PW.1 | PW.1.2: Adhere to requirements throughout development | All equations carry explicit invariants; M1 chaos suite enforces them at every tick | `m1_coupled_report.json` — 8 scenarios, 395 ticks, 0 violations | ✓ Implemented |
| PW.4 — Secure Design | PW.4.1: Use secure design principles | Separation of cognitive loop (NCE, seconds) from control loop (HVR, milliseconds) via CognitiveBus; no blocking on slow path | `sero_m1_coupled.py` `CognitiveBus` class | ✓ Implemented |
| PW.4 | PW.4.2: Apply defense-in-depth | Three independent protection layers: (1) HVR throughput control, (2) adaptive α ODE, (3) Bayesian immune — each operates independently | `M1CoupledEngine.step()` — layers 1-3 called sequentially | ✓ Implemented |
| PW.5 — Secure Implementation | PW.5.1: Follow secure coding practices | Explicit division-by-zero guards (π→0 boundary), hard clamps [α_min, α_max], EWMA stability via bounded damping (Eq.7) | `CoupledStressAggregator.cognitive_gain()`, `AdaptiveAlpha.step()` | ✓ Implemented |
| PW.6 — Secure Testing | PW.6.1: Plan for security testing | 8-scenario chaos suite with explicit PASS/FAIL criteria; 5 falsifiable predictions | `baseline_comparison.py` — 5/5 predictions verified | ✓ Implemented |
| PW.6 | PW.6.2: Perform security testing | Chaos scenarios include adversarial: S6 (single-detector attack), S4 (false alarm injection), S3 (NCE silence/DoS) | `m1_coupled_report.json` scenarios 3, 4, 6 | ✓ Implemented |
| PW.7 — Vulnerability Remediation Prep | PW.7.2: Track and address vulnerabilities | Proxy-Bayes calibration (Eq.21 extended) updates detector reliability from ΔF_proxy observations; FP rate tracked per detector | `ProxyBayesImmune.proxy_calibrate()` — online Beta-Binomial update | ✓ Implemented |

### 1.2 PO — Prepare the Organization

| SSDF Practice | SSDF Sub-Practice | SERO/NCE Mechanism | Evidence Artifact | Status |
|---|---|---|---|---|
| PO.1 — Security Policies | PO.1.1: Create policies for security | NCE precision hierarchy defines epistemic class of each claim: GIVEN / INFERRED / SPECULATED | `nce_v0.5.md` Section 2 — calibration gates | ✓ Defined |
| PO.2 — Security Roles | PO.2.2: Ensure personnel understand roles | HVR / NCE Auditor / Immune Swarm roles are protocol-first: defined independently of model implementation | `sero_whitepaper_v0.5.pdf` Section 3 | ✓ Defined |
| PO.3 — Third-Party Security | PO.3.2: Govern software supply chain | CI/CD layer models releases as hypotheses; rollback gate activates when expected free energy exceeds threshold | Whitepaper Section 5 — Active Inference CI/CD | ⚠ Conceptual only — M4+ |
| PO.4 — Security Toolchain | PO.4.1: Use security toolchain | Immune Swarm detectors (static_analysis, dynamic_analysis, anomaly_detection, fuzzing) map directly to standard SAST/DAST/fuzzing toolchain | `ProxyBayesImmune.detectors` dict | ✓ Implemented |

### 1.3 RV — Respond to Vulnerabilities

| SSDF Practice | SSDF Sub-Practice | SERO/NCE Mechanism | Evidence Artifact | Status |
|---|---|---|---|---|
| RV.1 — Vulnerability Identification | RV.1.1: Gather vulnerability reports | CognitiveBus receives async π_NCE signals; immune defense aggregates multi-detector evidence | `CognitiveBus.update()`, `ProxyBayesImmune.evaluate()` | ✓ Implemented |
| RV.1 | RV.1.2: Assess vulnerabilities | Bayesian posterior P(threat|evidence) = σ(Λ) with precision-weighted detector contributions (Eq.19-22) | `ProxyBayesImmune.evaluate()` returns log_odds, posterior, contributions | ✓ Implemented |
| RV.2 — Vulnerability Response | RV.2.1: Respond to identified vulnerabilities | Escalation gate (τ_esc = 0.80) triggers when posterior > 0.80 AND ≥2 independent detectors active | `ProxyBayesImmune.evaluate()` structural dual-signal gate | ✓ Implemented |
| RV.2 | RV.2.2: Prioritize vulnerability responses | Detector trust weights (π_j_eff) encode epistemic class priority: static_analysis=0.90 > dynamic=0.85 > anomaly=0.60 > fuzzing=0.55 | `DetectorState.pi_base` values — NCE precision hierarchy | ✓ Implemented |
| RV.3 — Vulnerability Disclosure | RV.3.1: Analyze and report | Proxy calibration log and escalation log are machine-readable, timestamped per tick | `immune.calibration_log`, `immune.escalation_log` — JSON arrays | ✓ Implemented |

### 1.4 PS — Protect the Software

| SSDF Practice | SSDF Sub-Practice | SERO/NCE Mechanism | Evidence Artifact | Status |
|---|---|---|---|---|
| PS.1 — Software Integrity | PS.1.1: Protect software releases | Active Inference CI/CD: release decision based on expected free energy; stop/rollback if FE exceeds threshold | Whitepaper Section 5 — `Ψ_F` velocity gate | ⚠ Whitepaper only — M3+ |
| PS.2 — Software Integrity Verification | PS.2.1: Verify software release integrity | Immune Swarm detectors (static+dynamic analysis) run on every candidate artifact before admission | Architecture defined; no M1 implementation | ⚠ Architecture only |
| PS.3 — Software Provenance | PS.3.1: Archive and protect each release | SLSA provenance mapping — see Section 2 below | Section 2 | ⚠ Partial |

---

## 2. SLSA Mapping (Supply-chain Levels for Software Artifacts)

SLSA defines four levels of supply-chain integrity: L0 (no guarantee) → L3 (highest guarantee).

| SLSA Requirement | Level | SERO Mechanism | Evidence | SERO Level |
|---|---|---|---|---|
| Build process scripted | L1 | M1 simulation is a single-command reproducible script (`python sero_m1_coupled.py`) | `sero_m1_coupled.py` — deterministic with `random.seed(42)` | L1 ✓ |
| Build isolated from developer machine | L2 | Not implemented — runs locally | — | L1 only |
| Provenance generated during build | L2 | JSON reports auto-generated per run with version, date, scenario results | `m1_coupled_report.json` | Partial L2 |
| Provenance signed by build service | L3 | Not implemented | — | Not achieved |
| Hermeticity (no external dependencies during build) | L3 | M1 uses stdlib only (math, json, random, statistics) | `sero_m1_coupled.py` imports | L3 ✓ for simulation |
| Release artifacts include provenance | L2 | JSON report is output artifact alongside code | `baseline_comparison_report.json` | Partial L2 |
| Two-party review for production builds | L4 | NCE dual-auditor gate (Auditor + Senior NCE) defined in protocol | `nce_v0.5.md` Section 3 — reductio gate | Architecture only |

**Current SERO SLSA Status:** L1 achieved for simulation artifacts. L2 partial (provenance generated but not signed). Gap to L2 full: CI build isolation + signed provenance. Gap to L3: verified build service.

---

## 3. Explicit Gaps and Open Items

This section documents what SERO does NOT yet provide, to prevent overclaiming.

| Gap | Area | Impact | Target Milestone |
|---|---|---|---|
| Full Lyapunov proof for coupled system | Mathematical | Stability proven for α subsystem only; full (T, S, α, π_NCE) state space requires composite Lyapunov function | M4+ |
| Active Inference CI/CD implementation | PO.3, PS.1 | Whitepaper describes release-as-hypothesis model; no executable implementation | M3 |
| Ground truth for proxy calibration | RV.1, RV.3 | Proxy ΔF calibration confounds regulatory effect with threat reality; requires human-confirmed labels for high-stakes deployments | M3 |
| β (cognitive gain) calibration procedure | Mathematical | β=2.0 is reference value; environment-specific optimal β requires calibration suite analogous to α sensitivity analysis | M2 |
| Signed provenance for build artifacts | SLSA L2 | JSON reports generated but not signed by build service | Tooling decision |
| MAPE-K interoperability spec | Architecture | SERO roles (HVR/Immune/Glial) map to Monitor/Analyze/Plan/Execute but interface format not standardized | M5 |
| SWE-bench contamination mitigation | Benchmark | Immune Swarm "plausible but incorrect patch" risk acknowledged; evaluation methodology against contaminated benchmarks not defined | M4+ |

---

## 4. Falsifiable Claims Registry

Cross-reference: each claim links to a verifiable test.

| ID | Claim | Type | Test | Result |
|---|---|---|---|---|
| C1 | T(t) ≥ T_min = 0.05 at every tick | Mathematical (Eq.3+4) | `verify_invariants()` → `safety_invariant` | ✓ PASS — 395/395 ticks |
| C2 | Stress bounded: |S(t)| ≤ S_max | Mathematical (Eq.7) | `verify_invariants()` → `stress_bounded` | ✓ PASS — all scenarios |
| C3 | α(t) ∈ [α_min, α_max] always | Mathematical (Eq.18 + hard clamp) | `verify_invariants()` → `alpha_bounded` | ✓ PASS — all scenarios |
| C4 | Single-detector attack: escalation probability < threshold | Bayesian (Eq.19 + p0=0.02 + cap=3.0) | S6 scenario, `false_escalations` | ✓ PASS — 0 escalations |
| C5 | Dual-detector real threat: escalation triggered | Bayesian (Eq.19) | S5 scenario, `escalation_log` | ✓ PASS — 20 escalations in threat window |
| C6 | NCE silence (20 ticks): system survives | CognitiveBus decay law | S3 scenario, `safety_invariant` | ✓ PASS |
| C7 | Cognitive collapse alone (π→0.12): no false stress spike | Eq.15 (stress requires prediction error, not just π) | S8 scenario, `stress_h` all < 0.001 | ✓ PASS |
| C8 | M1 shed depth proportional to fault severity | Eq.3 + Eq.15 (cognitive gain × prediction error) | P2 prediction: std(min_T_M1) > std(min_T_B) | ✓ PASS |
| C9 | No false shedding under noise/cognitive-only stress | Eq.3 + Eq.18 NCE term | P3 prediction: avail@90% ≥ 0.90 for S4/S6/S8 | ✓ PASS — 3/3 scenarios |
| C10 | Full Lyapunov stability of coupled system | Open — not yet proven | Composite Lyapunov function required | ⚠ OPEN |
| C11 | Proxy calibration converges to correct detector reliability | Empirical | Requires labeled validation set | ⚠ OPEN |

---

## 5. Reproduction Instructions

Any engineer can verify all implemented claims (C1–C9) in under 5 minutes:

```bash
# Requirements: Python 3.9+, stdlib only (no external packages)
python sero_m1_coupled.py   # → m1_coupled_report.json  (8 scenarios, all PASS)
python baseline_comparison.py  # → baseline_comparison_report.json  (5/5 predictions)
```

Outputs are deterministic (fixed `random.seed(42)`). Expected result: `GLOBAL RESULT: ✓ ALL PASS` and `PREDICTIONS PASSED: 5/5`.

To falsify C4 (single-detector gate): modify `ProxyBayesImmune.__init__` to set `prior_p0=0.50` — posterior will exceed threshold from single detector. The gate is sensitive to prior choice; p0=0.02 is documented in code with rationale.

---

*Document status: INFERRED from implemented code + whitepaper. Claims C1–C9: GIVEN (executable). Claims C10–C11: SPECULATED (requires further work). All open items documented in Section 3.*
