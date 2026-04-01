# Threat Model

**Document Version:** 1.0.0
**Project Version:** 1.0.0
**Last Updated:** November 2025
**Threat Modeling Framework:** STRIDE + Attack Trees

## Table of Contents

- [Overview](#overview)
- [Assets and Trust Boundaries](#assets-and-trust-boundaries)
- [STRIDE Analysis](#stride-analysis)
- [Attack Trees](#attack-trees)
- [Threat Scenarios](#threat-scenarios)
- [Mitigation Summary](#mitigation-summary)
- [Residual Risks](#residual-risks)

---

## Overview

This threat model identifies security threats to MLSDM Governed Cognitive Memory using the STRIDE methodology and attack tree analysis. It covers threats to confidentiality, integrity, availability, and accountability.

### Methodology

- **STRIDE**: Systematic threat categorization (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)
- **Attack Trees**: Hierarchical decomposition of attack paths
- **Risk Rating**: Likelihood × Impact (High, Medium, Low)

### Threat Model Scope

**In Scope:**
- API endpoints and authentication
- Memory subsystem and data processing
- Deployment configurations
- Dependencies and supply chain

**Out of Scope:**
- Physical security (assumed cloud/datacenter)
- Social engineering (assumed security training)
- Client-side attacks (client responsibility)

---

## Assets and Trust Boundaries

### Critical Assets

| Asset | Confidentiality | Integrity | Availability | Owner |
|-------|----------------|-----------|--------------|-------|
| **Event Vectors** | High | High | Medium | User |
| **Moral Values** | Medium | High | Medium | User |
| **API Tokens** | Critical | Critical | Low | System |
| **System State** | Low | High | High | System |
| **LLM Responses** | High | High | High | User |

### Trust Boundaries

```
┌─────────────────────────────────────────────────┐
│         Untrusted Zone (Internet)               │
│  - User clients                                 │
│  - Malicious actors                             │
│  - Public networks                              │
└──────────────────┬──────────────────────────────┘
                   │ TLS
    ┌──────────────▼───────────────┐
    │   DMZ (Load Balancer/WAF)    │
    │  - TLS termination           │
    │  - Rate limiting             │
    │  - Authentication            │
    └──────────────┬───────────────┘
                   │
    ┌──────────────▼───────────────┐
    │  Application Zone (MLSDM)    │
    │  - Input validation          │
    │  - Business logic            │
    │  - Memory management         │
    └──────────────┬───────────────┘
                   │
    ┌──────────────▼───────────────┐
    │   Backend Zone (LLM APIs)    │
    │  - OpenAI / Anthropic        │
    │  - Embedding services        │
    └──────────────────────────────┘
```

---

## STRIDE Analysis

### S - Spoofing

**Threat:** Attacker impersonates legitimate user to access system

| Attack Vector | Likelihood | Impact | Risk | Mitigation |
|--------------|------------|--------|------|------------|
| Stolen API tokens | Medium | High | **High** | Token rotation, rate limiting, audit logging |
| Token brute-force | Low | High | Medium | Strong token entropy (≥256 bits), rate limiting |
| Session hijacking | Low | Medium | Low | Short-lived tokens, TLS enforcement |

**Mitigations:**
- ✅ Bearer token authentication with strong entropy
- ✅ Constant-time token comparison (timing attack resistant)
- ✅ TLS 1.2+ for all communications
- ✅ Structured audit logging with correlation IDs
- ⚠️ Token rotation not automated (v1.1 planned)
- ⚠️ Multi-factor authentication not supported (v1.1 planned)

---

### T - Tampering

**Threat:** Attacker modifies data in transit or at rest

| Attack Vector | Likelihood | Impact | Risk | Mitigation |
|--------------|------------|--------|------|------------|
| Man-in-the-middle (MITM) | Low | High | Medium | TLS enforcement, certificate pinning |
| Input manipulation | High | Medium | **High** | Strict input validation, type checking |
| Memory corruption | Low | High | Medium | Bounded memory, input sanitization |
| Log tampering | Medium | Medium | Medium | Immutable log storage, integrity checks |

**Mitigations:**
- ✅ TLS 1.2+ encryption in transit
- ✅ Strict input validation (type, range, dimension)
- ✅ Immutable audit logs (append-only)
- ✅ Bounded memory prevents buffer overflows
- ✅ Input sanitization (NaN, Inf filtering)
- ⚠️ Certificate pinning not implemented (optional)
- ⚠️ Log integrity signatures not implemented (v1.1 planned)

---

### R - Repudiation

**Threat:** User denies performing an action without proof

| Attack Vector | Likelihood | Impact | Risk | Mitigation |
|--------------|------------|--------|------|------------|
| Deny event submission | Medium | Low | Low | Correlation IDs, structured logs |
| Deny API access | Low | Low | Low | Authentication logs |

**Mitigations:**
- ✅ Correlation IDs for request tracing
- ✅ Structured JSON logging with timestamps
- ✅ Authentication attempt logging
- ✅ Event acceptance/rejection logging
- ✅ 90-day log retention for audit trails
- ⚠️ Digital signatures on logs not implemented (v1.1 planned)
- ⚠️ Non-repudiation guarantees limited (best-effort logging)

---

### I - Information Disclosure

**Threat:** Unauthorized access to sensitive information

| Attack Vector | Likelihood | Impact | Risk | Mitigation |
|--------------|------------|--------|------|------------|
| Log PII leakage | Medium | Medium | Medium | PII sanitization in logs |
| Vector exfiltration | Low | High | Medium | Authentication, rate limiting |
| Error message leaks | Medium | Low | Low | Generic error messages |
| Timing attacks | Low | Low | Low | Constant-time operations |

**Mitigations:**
- ✅ No PII stored in system
- ✅ Pseudonymized event vectors
- ✅ Log sanitization (truncate prompts/responses)
- ✅ Generic error messages to clients
- ✅ Constant-time authentication comparison
- ✅ TLS encryption for data in transit
- ⚠️ Vector anonymization not guaranteed (depends on embeddings)
- ⚠️ Differential privacy not implemented

---

### D - Denial of Service (DoS)

**Threat:** Attacker prevents legitimate access to system

| Attack Vector | Likelihood | Impact | Risk | Mitigation |
|--------------|------------|--------|------|------------|
| High request rate | High | High | **High** | Rate limiting (5 RPS per client) |
| Memory exhaustion | Medium | High | **High** | Fixed capacity (20k vectors) |
| CPU exhaustion | Medium | Medium | Medium | Request timeouts, resource limits |
| Slow-read attacks | Low | Medium | Low | Connection timeouts |

**Mitigations:**
- ✅ Rate limiting: 5 RPS per client (token bucket)
- ✅ Global rate limit: 1000 RPS
- ✅ Fixed memory capacity: 20k vectors (no unbounded growth)
- ✅ Request timeout: 30 seconds
- ✅ Connection limits per IP
- ✅ Kubernetes resource limits (CPU/memory)
- ⚠️ Distributed DoS protection depends on infrastructure (Cloudflare/AWS Shield)
- ⚠️ Advanced anomaly detection not implemented (v1.1 planned)

---

### E - Elevation of Privilege

**Threat:** Attacker gains unauthorized permissions

| Attack Vector | Likelihood | Impact | Risk | Mitigation |
|--------------|------------|--------|------|------------|
| Container escape | Low | Critical | Medium | Non-root containers, read-only filesystem |
| API abuse | Medium | Medium | Medium | Authentication, rate limiting |
| Dependency exploit | Medium | High | **High** | Dependency scanning, regular updates |

**Mitigations:**
- ✅ Non-root container execution (UID 1000)
- ✅ Read-only filesystem where possible
- ✅ Least-privilege runtime (no unnecessary capabilities)
- ✅ Dependency vulnerability scanning (pip-audit)
- ✅ Multi-layer authentication (API key, OIDC, mTLS, signing)
- ✅ Role-based access control (RBAC) implemented with role hierarchy
- ⚠️ Network policies not enforced (depends on deployment)

---

## Attack Trees

### Root: System Compromise

```
[System Compromise]
    |
    ├── [Unauthorized Access]
    │       ├── [Stolen Credentials] (Medium risk)
    │       │       ├── Token theft from logs
    │       │       ├── Token interception (MITM)
    │       │       └── Social engineering
    │       └── [Authentication Bypass] (Low risk)
    │               ├── Implementation bug
    │               └── Timing attack
    |
    ├── [Data Exfiltration]
    │       ├── [API Abuse] (Medium risk)
    │       │       ├── Excessive retrieval requests
    │       │       └── Rate limit bypass
    │       └── [Memory Dump] (Low risk)
    │               └── Container escape
    |
    ├── [Service Disruption]
    │       ├── [DoS Attack] (High risk)
    │       │       ├── Request flooding
    │       │       ├── Memory exhaustion
    │       │       └── CPU exhaustion
    │       └── [Malicious Input] (Medium risk)
    │               ├── Adversarial vectors
    │               └── Moral value manipulation
    |
    └── [Supply Chain Attack]
            ├── [Compromised Dependency] (Medium risk)
            │       ├── Malicious package
            │       └── Vulnerability exploit
            └── [Build Process] (Low risk)
                    └── Compromised CI/CD
```

### Attack Path Analysis

#### High-Risk Path: DoS via Request Flooding

```
1. Attacker obtains valid API token
   ├── Phishing
   ├── Log scanning
   └── Insider threat

2. Attacker floods API with requests
   ├── Distributed sources (DDoS)
   └── Single source (high-rate)

3. System overwhelmed
   ├── Rate limiter saturated
   ├── Connection pool exhausted
   └── CPU/memory limits reached

4. Legitimate users denied service
```

**Mitigations:**
- ✅ Token bucket rate limiting (5 RPS per client)
- ✅ Global rate limit (1000 RPS)
- ✅ Kubernetes resource limits
- ⚠️ DDoS protection (infrastructure-dependent)

#### Medium-Risk Path: Memory Exhaustion

```
1. Attacker submits maximum-size vectors

2. Memory fills to capacity (20k vectors)

3. Circular buffer starts evicting old data

4. Potential data loss / degraded performance
```

**Mitigations:**
- ✅ Fixed capacity (20k vectors)
- ✅ Circular buffer (FIFO eviction)
- ✅ No unbounded growth
- ✅ Graceful degradation

---

## Threat Scenarios

### Scenario 1: Token Compromise

**Description:** Attacker obtains API token from exposed logs or intercepted traffic

**Attack Steps:**
1. Scan public GitHub repositories for leaked tokens
2. Use token to authenticate API requests
3. Submit malicious events to corrupt memory
4. Exfiltrate system state via `/v1/state` endpoint

**Impact:**
- Unauthorized data access
- Memory corruption with adversarial vectors
- Service disruption

**Likelihood:** Medium
**Impact:** High
**Risk:** **High**

**Mitigations:**
- Token rotation policy (90 days)
- Rate limiting per token (5 RPS)
- Audit logging of all API calls
- Anomaly detection (v1.1 planned)

---

### Scenario 2: Adversarial Input Attack

**Description:** Attacker submits crafted vectors to manipulate moral threshold

**Attack Steps:**
1. Submit low-moral events repeatedly (moral_value < 0.1)
2. Force moral threshold to converge to minimum (0.30)
3. Submit high-moral malicious content that now passes
4. Bypass moral filtering at reduced threshold

**Impact:**
- Moral governance bypass
- Injection of unfiltered content

**Likelihood:** Medium
**Impact:** Medium
**Risk:** Medium

**Mitigations:**
- Bounded threshold range [0.30, 0.90]
- Gradual adaptation (0.05 per step)
- EMA smoothing (α=0.1) prevents rapid changes
- Drift monitoring alerts (planned v1.1)

---

### Scenario 3: Dependency Vulnerability Exploitation

**Description:** Attacker exploits known vulnerability in third-party package

**Attack Steps:**
1. Identify vulnerable dependency (e.g., numpy, fastapi)
2. Exploit vulnerability via crafted API request
3. Achieve remote code execution or data exfiltration

**Impact:**
- System compromise
- Data breach
- Service disruption

**Likelihood:** Medium
**Impact:** Critical
**Risk:** **High**

**Mitigations:**
- Weekly dependency scanning (pip-audit)
- Automated security updates (Dependabot)
- Pinned versions in requirements.txt
- Fast patch deployment (7-14 days for critical)

---

## Mitigation Summary

### Implemented Controls

| Control | Type | Status | Coverage |
|---------|------|--------|----------|
| **Authentication** | Preventive | ✅ Implemented | All API endpoints |
| **Rate Limiting** | Preventive | ✅ Implemented | Per-client and global |
| **Input Validation** | Preventive | ✅ Implemented | All inputs |
| **TLS Encryption** | Preventive | ✅ Implemented | All communications |
| **Memory Bounds** | Preventive | ✅ Implemented | QILM and synaptic memory |
| **Audit Logging** | Detective | ✅ Implemented | All security events |
| **Dependency Scanning** | Detective | ✅ Implemented | CI/CD pipeline |
| **Non-root Containers** | Preventive | ✅ Implemented | Deployment |

### Planned Controls (v1.1+)

| Control | Type | Timeline | Priority |
|---------|------|----------|----------|
| **RBAC** | Preventive | Q1 2026 | High |
| **Token Rotation** | Preventive | Q1 2026 | High |
| **Anomaly Detection** | Detective | Q2 2026 | Medium |
| **WAF Integration** | Preventive | Q2 2026 | Medium |
| **MFA** | Preventive | Q2 2026 | Low |
| **SBOM** | Detective | Q1 2026 | Medium |

---

## NeuroLang / Aphasia Security Controls

**Added:** November 2025
**Version:** 1.0.0

The NeuroLang grammar module and Aphasia-Broca detection system introduce specialized security considerations due to their use of PyTorch checkpoints, offline training capabilities, and access to sensitive LLM responses. This section documents the security controls implemented to mitigate these risks.

### Threat: Malicious Checkpoint Loading

**Risk:** An attacker could provide a malicious PyTorch checkpoint file containing arbitrary code that executes during `torch.load()`, leading to remote code execution (RCE).

**Mitigations:**
- ✅ **Path Restriction**: `safe_load_neurolang_checkpoint()` restricts checkpoint loading to the `config/` directory only
- ✅ **Structure Validation**: Checkpoints are validated to contain required keys (`actor`, `critic`) before loading
- ✅ **Type Checking**: Checkpoint must be a dictionary; other types are rejected
- ✅ **Path Traversal Prevention**: All paths are resolved and validated to prevent `../` attacks

**Implementation:**
```python
# Only checkpoints in config/ can be loaded
ALLOWED_CHECKPOINT_DIR = Path("config").resolve()

def safe_load_neurolang_checkpoint(path, device):
    # Validates path is within ALLOWED_CHECKPOINT_DIR
    # Validates checkpoint structure before loading
```

**Attack Scenario Blocked:**
```python
# Attacker tries to load malicious checkpoint from /tmp
NeuroLangWrapper(checkpoint_path="/tmp/evil.pt")  # ❌ ValueError raised
```

### Threat: Sensitive Data Leakage via Logs

**Risk:** Aphasia detection/repair logs could leak sensitive user prompts or LLM responses, exposing PII or confidential information.

**Mitigations:**
- ✅ **Metadata-Only Logging**: Aphasia logs contain only decision metadata (decision, severity, flags)
- ✅ **No Content Logging**: Prompts and responses are never logged
- ✅ **Aggregated Metrics Only**: Only statistical information is logged, not raw text

**Implementation:**
```python
# Aphasia logging only logs metadata
log_aphasia_event(AphasiaLogEvent(
    decision="repaired",
    is_aphasic=True,
    severity=0.75,
    flags=["short_sentences"],
    # NO prompt or response content
))
```

**Log Example (Safe):**
```
[APHASIA] decision=repaired is_aphasic=True severity=0.750 flags=short_sentences,low_function_words
```

### Threat: Unauthorized Training in Production

**Risk:** Attackers could trigger offline model training in production environments, consuming resources and potentially introducing backdoors through poisoned training data.

**Mitigations:**
- ✅ **Secure Mode**: `MLSDM_SECURE_MODE` environment variable blocks all training operations
- ✅ **Training Script Guard**: `train_neurolang_grammar.py` refuses to run when secure mode is enabled
- ✅ **Forced Disable**: Secure mode overrides all NeuroLang configuration to disabled state
- ✅ **Repair Prevention**: Secure mode disables aphasia repair (detection only)

**Implementation:**
```python
# In production, set MLSDM_SECURE_MODE=1
if is_secure_mode_enabled():
    neurolang_mode = "disabled"
    neurolang_checkpoint_path = None
    aphasia_repair_enabled = False
```

**Secure Mode Effects:**
- Training: ❌ Blocked (eager_train, lazy_train disabled)
- Checkpoint Loading: ❌ Blocked (ignored even if configured)
- Aphasia Repair: ❌ Blocked (detection only, no response modification)
- Aphasia Detection: ✅ Allowed (read-only analysis)

### Control Validation

All security controls are validated through comprehensive test suites:

**Checkpoint Security Tests** (`tests/security/test_neurolang_checkpoint_security.py`):
- ✅ Path outside `config/` is rejected
- ✅ Non-existent checkpoints raise `FileNotFoundError`
- ✅ Invalid checkpoint structure raises `ValueError`
- ✅ Valid checkpoints load successfully

**Secure Mode Tests** (`tests/security/test_secure_mode.py`):
- ✅ Secure mode detection from environment variable
- ✅ Forces `neurolang_mode="disabled"`
- ✅ Ignores checkpoint paths
- ✅ Disables aphasia repair
- ✅ Generation works without training

**Privacy Tests** (`tests/security/test_aphasia_logging_privacy.py`):
- ✅ Prompts never appear in logs
- ✅ Responses never appear in logs
- ✅ Only metadata is logged
- ✅ Multiple generations don't leak secrets

### Deployment Recommendations

**Production Environments:**
1. **ALWAYS** set `MLSDM_SECURE_MODE=1` on all production nodes
2. Train models offline in isolated development environments
3. Deploy pre-trained checkpoints to `config/` directory only
4. Monitor for unauthorized training attempts via audit logs
5. Restrict write access to `config/` directory at filesystem level

**Development Environments:**
1. Use `MLSDM_SECURE_MODE=0` for development and testing
2. Train models in isolated, non-production environments
3. Validate checkpoints before promoting to production
4. Review aphasia logs for unexpected patterns

**Checkpoint Management:**
- Store trusted checkpoints in version control or artifact repository
- Scan checkpoints with antivirus/malware detection before deployment
- Use read-only mounts for `config/` in production containers
- Rotate/update checkpoints through controlled deployment pipelines only

### Monitoring and Detection

**Indicators of Compromise:**
- Training operations in production (audit log: `SystemExit: Secure mode enabled`)
- Checkpoint load attempts outside `config/` (audit log: `ValueError: Refusing to load`)
- Unexpected changes to files in `config/` directory
- Anomalous GPU/CPU usage patterns

**Response Procedures:**
1. Immediately investigate checkpoint load failures
2. Review filesystem audit logs for unauthorized writes to `config/`
3. Verify `MLSDM_SECURE_MODE` is enabled on all production nodes
4. Quarantine suspicious checkpoint files for forensic analysis

---

## Residual Risks

### Accepted Risks

| Risk | Rationale | Compensating Controls |
|------|-----------|----------------------|
| **Vector re-identification** | Embedding models may preserve PII | User responsibility to sanitize inputs |
| **DDoS at scale** | Infrastructure-level attack | Depends on cloud provider protections |
| **Social engineering** | Human factor attacks | Security awareness training (user responsibility) |
| **Zero-day exploits** | Unknown vulnerabilities | Fast patching process, defense-in-depth |

### Risk Acceptance

- Residual risks accepted for v1.0 release
- Continuous monitoring and re-assessment
- Escalation path for emerging threats

---

## Review and Updates

**Review Schedule:** Quarterly or after major changes
**Last Reviewed:** November 2025
**Next Review:** February 2026
**Owner:** Security Team

---

**Note:** This threat model is a living document and will be updated as new threats emerge or mitigations are implemented.
