# AI Safety Risk Register

**Document Version:** 1.0.0
**Project Version:** 1.2.0
**Last Updated:** November 2025
**Owner:** Principal AI Safety Engineer
**Status:** Active

---

## Table of Contents

- [Overview](#overview)
- [Risk Assessment Framework](#risk-assessment-framework)
- [Risk Register Table](#risk-register-table)
- [Detailed Risk Descriptions](#detailed-risk-descriptions)
- [Mitigation Status Summary](#mitigation-status-summary)
- [Review Schedule](#review-schedule)

---

## Overview

This document is the authoritative AI Safety Risk Register for MLSDM (Governed Cognitive Memory). It catalogs all identified risks related to:

- **Content Safety**: Harmful, toxic, or inappropriate outputs
- **Behavioral Safety**: Agent unchaining, memory manipulation, policy bypass
- **Technical Safety**: System failures, resource exhaustion, data integrity
- **Governance Safety**: Audit gaps, policy drift, accountability failures

Each risk is assessed using the Impact × Likelihood framework and tracked through mitigation to acceptance.

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| MLSDM core modules | Underlying LLM model internals |
| API layer security | Infrastructure-level attacks (DDoS) |
| Memory subsystems | Physical security |
| Moral governance | Social engineering |
| Observability layer | Client-side vulnerabilities |

---

## Risk Assessment Framework

### Impact Levels

| Level | Description | Examples |
|-------|-------------|----------|
| **Critical** | System compromise, significant harm to users, regulatory violations | Toxic content bypass, data breach, system takeover |
| **High** | Major functionality degraded, user trust impacted, moderate harm potential | Memory corruption, threshold drift, policy violation |
| **Medium** | Noticeable service degradation, minor harm potential | Increased latency, false positives, degraded responses |
| **Low** | Minimal impact, easily recoverable | Logging gaps, minor configuration issues |

### Likelihood Levels

| Level | Description | Frequency |
|-------|-------------|-----------|
| **High** | Expected to occur regularly under normal operation | >1/week |
| **Medium** | May occur occasionally, especially under stress | 1/month - 1/week |
| **Low** | Unlikely but possible under adverse conditions | 1/quarter - 1/month |
| **Very Low** | Requires sophisticated attack or rare conditions | <1/quarter |

### Risk Score Matrix

|              | Very Low Likelihood | Low | Medium | High |
|--------------|---------------------|-----|--------|------|
| **Critical** | High | High | Critical | Critical |
| **High**     | Medium | High | High | Critical |
| **Medium**   | Low | Medium | Medium | High |
| **Low**      | Low | Low | Medium | Medium |

---

## Risk Register Table

| Risk ID | Category | Description | Impact | Likelihood | Risk Score | Status | Controls |
|---------|----------|-------------|--------|------------|------------|--------|----------|
| **R001** | Content | Toxic content bypass via threshold drift | Critical | Low | High | Mitigated | MoralFilterV2 bounded drift [0.30, 0.90] |
| **R002** | Content | Prompt injection to bypass moral filter | High | Medium | High | Mitigated | Multi-layer filtering, structured prompts |
| **R003** | Content | Jailbreak via multi-turn manipulation | High | Medium | High | Partially Mitigated | Memory-based attack detection (future) |
| **R004** | Behavioral | Memory poisoning via adversarial embeddings | High | Low | Medium | Mitigated | Input validation, capacity bounds |
| **R005** | Behavioral | Threshold manipulation via strategic inputs | High | Medium | High | Mitigated | EMA smoothing, bounded adaptation |
| **R006** | Behavioral | Memory leakage of sensitive user data | Critical | Low | High | Mitigated | No PII storage, ephemeral processing |
| **R007** | Technical | Memory exhaustion / OOM crash | High | Low | Medium | Mitigated | Fixed 29.37 MB footprint, PELM bounds |
| **R008** | Technical | LLM timeout / circuit breaker failure | Medium | Medium | Medium | Mitigated | Timeout enforcement, graceful degradation |
| **R009** | Technical | Race conditions in concurrent access | High | Low | Medium | Mitigated | Thread-safe locks, property tests |
| **R010** | Technical | Checkpoint loading RCE (NeuroLang) | Critical | Very Low | High | Mitigated | Path restriction, secure mode |
| **R011** | Governance | Audit trail gaps | Medium | Low | Low | Mitigated | Structured logging, correlation IDs |
| **R012** | Governance | Policy drift without detection | High | Medium | High | Mitigated | Policy registry hash enforcement, telemetry alerts, runtime gate |
| **R013** | Governance | Undetected model degradation | Medium | Medium | Medium | Mitigated | Aphasia detection, quality metrics |
| **R014** | Content | Aphasia detection false negatives | Medium | Low | Low | Mitigated | Configurable thresholds, multiple flags |
| **R015** | Content | Hallucination propagation via memory | High | Medium | High | Mitigated | Immutable memory provenance, integrity validation, confidence scoring |
| **R016** | Behavioral | Sleep phase exploitation for reduced filtering | Medium | Low | Low | Mitigated | Phase-aware moral enforcement |
| **R017** | Technical | Dependency vulnerability exploitation | High | Medium | High | Mitigated | Weekly pip-audit, Dependabot |
| **R018** | Content | Indirect prompt injection via context | High | Medium | High | Partially Mitigated | Context sanitization (future) |

---

## Detailed Risk Descriptions

### R001: Toxic Content Bypass via Threshold Drift

**Category:** Content Safety
**Risk Owner:** Safety Team

**Description:**
Under sustained adversarial input (e.g., 70% toxic content stream), the moral filter threshold may drift toward minimum bounds, potentially allowing previously-rejected content to pass.

**Current Controls:**
- MoralFilterV2 threshold bounded to [0.30, 0.90]
- EMA smoothing (α=0.1) limits rapid drift
- Maximum adaptation step: 0.05 per event
- Dead band: 0.05 prevents oscillation

**Validation:**
- `tests/validation/test_moral_filter_effectiveness.py::test_moral_drift_stability`
- Maximum drift observed: 0.33 under 70% toxic bombardment (within bounds)

**Status:** ✅ Mitigated

**Residual Risk:** Low - Bounded drift ensures minimum safety standards maintained.

---

### R002: Prompt Injection to Bypass Moral Filter

**Category:** Content Safety
**Risk Owner:** Safety Team

**Description:**
Adversarial prompts may attempt to circumvent moral filtering through:
- Roleplay scenarios ("Act as an evil AI...")
- Hypothetical framing ("In a story where...")
- Encoding/obfuscation
- Instruction injection via context

**Current Controls:**
- MoralFilterV2 evaluates content-level moral scores
- Speech governance provides second layer
- LLM provider safety layers (OpenAI moderation)
- Structured prompts with explicit constraints

**Validation:**
- `tests/security/test_robustness.py::TestMoralFilterThresholdStability`
- Red-teaming scenarios (planned)

**Status:** ✅ Mitigated (defense in depth)

**Residual Risk:** Medium - Sophisticated attacks may still succeed against underlying LLM.

---

### R003: Jailbreak via Multi-Turn Manipulation

**Category:** Content Safety
**Risk Owner:** Safety Team

**Description:**
Attackers may use multi-turn conversations to gradually shift model behavior, exploiting memory persistence to build context that enables jailbreaks.

**Current Controls:**
- Wake/sleep cycles provide periodic context reset
- Memory capacity bounds limit attack persistence
- Moral threshold homeostasis resists gradual drift
- **NEW (Dec 2025):** `analyze_conversation_patterns()` function in `mlsdm.security.llm_safety`

**Implemented Controls (December 2025):**
- ✅ Attack pattern detection via `analyze_conversation_patterns()`
- ✅ Anomaly detection for conversation patterns (hypothetical framing, persistence after refusal)
- ✅ Recommended action escalation (continue → warn → reset_session)

**Status:** ✅ Mitigated

**Validation:**
- `tests/security/test_llm_safety.py::TestMultiTurnAttackDetection` (6 tests)

**Action Items:**
- [x] Implement attack pattern signatures in memory retrieval
- [x] Add conversation anomaly detection
- [ ] Create red-teaming test suite for multi-turn attacks

---

### R004: Memory Poisoning via Adversarial Embeddings

**Category:** Behavioral Safety
**Risk Owner:** Engineering Team

**Description:**
Malicious embeddings could be submitted to corrupt memory, causing:
- Retrieval of harmful context
- Degraded response quality
- Semantic drift in stored knowledge

**Current Controls:**
- Input validation: NaN/Inf filtering, dimension checks
- Capacity bounds: FIFO eviction prevents unbounded growth
- Normalization: Vector norm validation

**Validation:**
- `tests/security/test_robustness.py::TestStatelessFallback::test_pelm_handles_nan_inputs`
- Property tests for memory invariants

**Status:** ✅ Mitigated

**Residual Risk:** Low - Valid-but-adversarial embeddings still possible (semantic-level attack).

---

### R005: Threshold Manipulation via Strategic Inputs

**Category:** Behavioral Safety
**Risk Owner:** Safety Team

**Description:**
Attackers may submit strategic sequences of moral values to manipulate the filter threshold:
- Low values → drift threshold down
- High values → drift threshold up then inject toxic content

**Current Controls:**
- EMA smoothing prevents rapid manipulation
- Bounded range [0.30, 0.90] limits exploitation
- Dead band prevents micro-oscillations
- Adaptation rate limited to 0.05/step

**Validation:**
- `tests/validation/test_moral_filter_effectiveness.py::test_moral_threshold_adaptation`
- `tests/security/test_robustness.py::test_threshold_oscillation_damping`

**Status:** ✅ Mitigated

**Residual Risk:** Low - Bounds ensure minimum protection regardless of manipulation.

---

### R006: Memory Leakage of Sensitive User Data

**Category:** Behavioral Safety
**Risk Owner:** Security Team

**Description:**
User prompts or responses could be leaked through:
- Log files containing raw content
- Memory retrieval returning other users' data
- Metrics exposing content details

**Current Controls:**
- No PII stored in memory (embeddings only)
- Log sanitization via payload scrubber
- Aphasia logs contain only metadata, not content
- Session isolation in API layer

**Validation:**
- `tests/security/test_aphasia_logging_privacy.py`
- `tests/security/test_payload_scrubber.py`
- `tests/security/test_security_invariants.py::TestPIINonLeakage`

**Status:** ✅ Mitigated

**Residual Risk:** Low - Embedding vectors may theoretically allow reconstruction (very difficult).

---

### R007: Memory Exhaustion / OOM Crash

**Category:** Technical Safety
**Risk Owner:** Engineering Team

**Description:**
Unbounded memory growth could cause system crashes, especially under:
- High request volume
- Large context windows
- Memory leaks

**Current Controls:**
- Fixed memory footprint: 29.37 MB verified
- PELM capacity: 20,000 vectors (circular buffer)
- MultiLevelMemory: Fixed L1/L2/L3 allocation
- Zero dynamic allocation after init

**Validation:**
- `tests/property/test_invariants_memory.py::test_pelm_capacity_enforcement`
- `benchmarks/measure_memory_footprint.py`

**Status:** ✅ Mitigated

**Residual Risk:** Very Low - Pre-allocated, bounded memory eliminates OOM risk.

---

### R010: Checkpoint Loading RCE (NeuroLang)

**Category:** Technical Safety
**Risk Owner:** Security Team

**Description:**
PyTorch checkpoint files can contain arbitrary code that executes during `torch.load()`. Malicious checkpoints could enable Remote Code Execution.

**Current Controls:**
- Path restriction: Only `config/` directory allowed
- Secure mode: `MLSDM_SECURE_MODE=1` blocks all training/loading
- Structure validation: Required keys verified before use
- Path traversal prevention

**Validation:**
- `tests/security/test_neurolang_checkpoint_security.py`
- `tests/security/test_secure_mode.py`

**Status:** ✅ Mitigated

**Residual Risk:** Very Low - Production uses secure mode; checkpoints vetted offline.

---

### R015: Hallucination Propagation via Memory

**Category:** Content Safety
**Risk Owner:** Safety Team

**Description:**
Hallucinated content from LLM responses could be stored in memory and retrieved as context for future responses, creating a feedback loop of misinformation.

**Current Controls:**
- Aphasia detection flags low-quality responses
- Memory decay (L1→L2→L3) reduces long-term impact
- Wake/sleep cycles provide consolidation opportunities
- Immutable memory provenance with lineage hashes and content integrity binding
- Provenance enforcement in persistent LTM storage paths

**Status:** ✅ Mitigated

---

### R018: Indirect Prompt Injection via Context

**Category:** Content Safety
**Risk Owner:** Safety Team

**Description:**
Malicious instructions embedded in retrieved context (from memory or external sources) could override system prompts and manipulate model behavior.

**Current Controls:**
- Context separation in prompt structure
- Moral filtering on final output
- Limited context window size
- **NEW (Dec 2025):** `sanitize_context()` function in `mlsdm.security.llm_safety`

**Implemented Controls (December 2025):**
- ✅ Context sanitization via `sanitize_context()` and `sanitize_context_for_llm()`
- ✅ Removes embedded instruction tags (`[INST]`, `<|system|>`, etc.)
- ✅ Removes hidden unicode characters (zero-width, etc.)
- ✅ Removes markdown comment injections
- ✅ Removes base64-encoded instruction attempts

**Status:** ✅ Mitigated

**Validation:**
- `tests/security/test_llm_safety.py::TestContextSanitization` (9 tests)

**Action Items:**
- [x] Implement context sanitization pipeline
- [x] Add instruction boundary detection
- [x] Create indirect injection test suite

---

## Mitigation Status Summary

### By Status

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Mitigated | 17 | 94% |
| ⚠️ Partially Mitigated | 1 | 6% |
| ❌ Open | 0 | 0% |
| 📋 Accepted | 0 | 0% |

### By Category

| Category | Total | Mitigated | Partial | Open |
|----------|-------|-----------|---------|------|
| Content Safety | 7 | 7 | 0 | 0 |
| Behavioral Safety | 4 | 4 | 0 | 0 |
| Technical Safety | 5 | 5 | 0 | 0 |
| Governance Safety | 2 | 2 | 0 | 0 |

### Critical/High Risks Requiring Action

| Risk ID | Description | Action Required | Status |
|---------|-------------|-----------------|--------|
| ~~R003~~ | ~~Multi-turn jailbreak~~ | ~~Attack pattern detection~~ | ✅ Mitigated |
| ~~R015~~ | ~~Hallucination propagation~~ | ~~Memory provenance~~ | ✅ Mitigated |
| ~~R018~~ | ~~Indirect prompt injection~~ | ~~Context sanitization~~ | ✅ Mitigated |
| ~~R012~~ | ~~Policy drift detection~~ | ~~Drift alerting system~~ | ✅ Mitigated |

---

## Review Schedule

| Review Type | Frequency | Next Due | Owner |
|-------------|-----------|----------|-------|
| Full Register Review | Quarterly | February 2026 | Safety Team |
| Critical Risk Review | Monthly | December 2025 | Safety Lead |
| Post-Incident Update | As needed | - | Incident Owner |
| Pre-Release Review | Per release | v1.3.0 | Safety Team |

### Coverage-Badge Verification (GitHub Actions)

| Verification Date | Reviewer | Consecutive Successful Run IDs (main) | Artifact References |
|-------------------|----------|---------------------------------------|---------------------|
| 2026-01-15 | Codex | 21022704090, 20961719696, 20900689678 | `coverage-badge-artifacts-21022704090` (https://api.github.com/repos/neuron7xLab/mlsdm/actions/artifacts/5137035815/zip); no retained artifacts for 20961719696, 20900689678 (https://api.github.com/repos/neuron7xLab/mlsdm/actions/runs/20961719696/artifacts, https://api.github.com/repos/neuron7xLab/mlsdm/actions/runs/20900689678/artifacts) |

### Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| Nov 2025 | 1.0.0 | Initial risk register creation | Principal AI Safety Engineer |
| Dec 2025 | 1.1.0 | R003, R018 mitigated: Multi-turn attack detection & context sanitization | @copilot |

---

## References

- [THREAT_MODEL.md](THREAT_MODEL.md) - Detailed threat analysis
- [SECURITY_POLICY.md](SECURITY_POLICY.md) - Security controls and policies
- [SAFETY_POLICY.yaml](SAFETY_POLICY.yaml) - Structured safety policy
- [MORAL_FILTER_SPEC.md](MORAL_FILTER_SPEC.md) - Moral filter specification
- [docs/ALIGNMENT_AND_SAFETY_FOUNDATIONS.md](docs/ALIGNMENT_AND_SAFETY_FOUNDATIONS.md) - AI safety foundations

---

**Document Status:** Active
**Classification:** Internal
**Last Reviewed:** November 2025
**Next Review:** February 2026
