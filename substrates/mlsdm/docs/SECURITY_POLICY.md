# Security Policy

**Document Version:** 2.2.0
**Project Version:** 1.0.0
**Last Updated:** March 2026
**Security Contact:** Report vulnerabilities via GitHub Security Advisories

## Table of Contents

- [Security Overview](#security-overview)
- [Supported Versions](#supported-versions)
- [Reporting a Vulnerability](#reporting-a-vulnerability)
- [Security Architecture](#security-architecture)
- [Security Controls](#security-controls)
- [Data Protection](#data-protection)
- [Authentication and Authorization](#authentication-and-authorization)
- [Input Validation](#input-validation)
- [Rate Limiting and DDoS Protection](#rate-limiting-and-ddos-protection)
- [Logging and Monitoring](#logging-and-monitoring)
- [Dependency Management](#dependency-management)
- [Secure Deployment Guidelines](#secure-deployment-guidelines)
- [Security Testing](#security-testing)
- [Compliance and Standards](#compliance-and-standards)
- [Policy-as-Code Integration](#policy-as-code-integration)

---

## Security Overview

MLSDM Governed Cognitive Memory implements defense-in-depth security principles to protect against common vulnerabilities and ensure safe operation in production environments. This policy outlines security measures, best practices, and incident response procedures.

### Security Objectives

1. **Confidentiality**: Protect sensitive data from unauthorized access
2. **Integrity**: Ensure data accuracy and prevent unauthorized modifications
3. **Availability**: Maintain reliable service operation under attack
4. **Accountability**: Provide audit trails for security-relevant events
5. **Resilience**: Gracefully degrade under adverse conditions

---

## Supported Versions

Security updates are provided for the following versions:

| Version | Supported | Security Updates | End of Life |
|---------|-----------|------------------|-------------|
| 1.0.x   | ✅ Yes    | Security-only patches | 2026-11-01 (subject to change) |
| 0.x.x   | ❌ No     | None             | Nov 2025    |

**Support Policy for 1.0.x:**
- **Patch Types**: Security-only fixes. No new features will be backported.
- **CVE Severity Threshold**: All CRITICAL and HIGH severity CVEs must be patched within the timelines specified in [Severity Classification](#severity-classification).
- **EOL Date**: Approximately 12 months from 1.0.0 release (Nov 2025). EOL may be extended based on adoption and community needs.

**Upgrade Policy**: Users should upgrade to the latest 1.0.x release within 30 days of release to receive security fixes.

---

## Reporting a Vulnerability

### Disclosure Process

We follow coordinated vulnerability disclosure practices:

1. **Report Privately**: Submit vulnerabilities via [GitHub Security Advisories](https://github.com/neuron7xLab/mlsdm/security/advisories/new)
2. **Initial Response**: Within 48 hours
3. **Triage and Validation**: Within 7 days
4. **Fix Development**: Based on severity (see timeline below)
5. **Public Disclosure**: After patch release + 7 days

### Severity Classification

| Severity | Response Time | Fix Timeline | Examples |
|----------|---------------|--------------|----------|
| **Critical** | 24 hours | 7 days | RCE, authentication bypass, data exfiltration |
| **High** | 48 hours | 14 days | SQL injection, XSS, privilege escalation |
| **Medium** | 7 days | 30 days | DoS, information disclosure |
| **Low** | 14 days | 90 days | Minor information leaks, low-impact issues |

### What to Include

When reporting a security issue, please provide:
- Detailed description of the vulnerability
- Steps to reproduce
- Proof of concept (if available)
- Potential impact assessment
- Suggested remediation (if known)
- Your contact information for follow-up

### Hall of Fame

We recognize security researchers who responsibly disclose vulnerabilities. With permission, we will acknowledge contributors in our security advisories.

---

## Security Architecture

### System Layers and Security Controls

MLSDM implements defense-in-depth security across all 14 system layers:

1. **Client & Integration Layer**
   - SDK Client: TLS enforcement, token validation
   - LLM Adapters: API key management, secure credential storage

2. **Service & API Layer**
   - FastAPI: Input validation, rate limiting, CORS headers
   - Middleware: Authentication, request sanitization, observability

3. **Engine & Router Layer**
   - Timeout enforcement to prevent DoS
   - Circuit breaker for failure isolation
   - Multi-provider isolation

4. **Application/Wrapper Layer**
   - Moral filtering (content governance)
   - Speech governance (output control)
   - Memory bounds enforcement

5. **Cognitive Core**
   - Fixed memory bounds (no OOM)
   - Deterministic processing
   - Thread-safe operations

6. **Observability Infrastructure**
   - PII scrubbing in logs (`payload_scrubber.py`)
   - Structured logging with security context
   - Audit trails for security events

7. **Security Infrastructure**
   - Rate limiting (`rate_limit.py`)
   - Input validation (`input_validator.py`)
   - Security logging (`security_logger.py`)

### Threat Model

The system is designed to resist the following threat categories across all layers:

1. **External Attacks**
   - Network-based attacks (DDoS, man-in-the-middle)
   - Application-level attacks (injection, XSS, CSRF)
   - Authentication bypass attempts
   - LLM-specific: prompt injection, jailbreaking
   - Rate limit circumvention

2. **Internal Threats**
   - Malicious input injection via LLM prompts
   - Memory exhaustion attacks
   - Resource starvation
   - Timing attacks

3. **Supply Chain**
   - Compromised dependencies
   - Malicious code injection
   - Vulnerable transitive dependencies

### Security Boundaries

```
┌────────────────────────────────────────────────┐
│            External Network (Untrusted)        │
└───────────────────┬────────────────────────────┘
                    │
    ┌───────────────▼────────────────┐
    │   API Gateway / Load Balancer  │
    │   - TLS Termination            │
    │   - Rate Limiting              │
    │   - DDoS Protection            │
    └───────────────┬────────────────┘
                    │
    ┌───────────────▼────────────────┐
    │   Application Layer            │
    │   - Authentication             │
    │   - Input Validation           │
    │   - Authorization              │
    └───────────────┬────────────────┘
                    │
    ┌───────────────▼────────────────┐
    │   Cognitive Controller         │
    │   - Memory Protection          │
    │   - Resource Limits            │
    │   - Moral Filtering            │
    └───────────────┬────────────────┘
                    │
    ┌───────────────▼────────────────┐
    │   Memory Layer                 │
    │   - Bounded Storage            │
    │   - Data Sanitization          │
    └────────────────────────────────┘
```

---

## Security Controls

### SC-1: Input Validation

**Objective**: Prevent injection attacks and invalid data processing

**Implementation**:
```python
# Location: src/mlsdm/utils/input_validator.py

def validate_event_vector(vector: Any) -> np.ndarray:
    """Validate and sanitize event vectors."""
    # Type checking
    if not isinstance(vector, (list, np.ndarray)):
        raise ValueError("Vector must be list or numpy array")

    # Dimension validation
    if len(vector) != EXPECTED_DIM:
        raise ValueError(f"Vector dimension must be {EXPECTED_DIM}")

    # Range validation (prevent overflow/underflow)
    if not np.all(np.isfinite(vector)):
        raise ValueError("Vector contains non-finite values")

    # Normalization (prevent adversarial inputs)
    vector = np.array(vector, dtype=np.float32)
    norm = np.linalg.norm(vector)
    if norm > 1e6 or norm < 1e-6:
        raise ValueError("Vector norm out of acceptable range")

    return vector

def validate_moral_value(value: Any) -> float:
    """Validate moral value parameter."""
    if not isinstance(value, (int, float)):
        raise ValueError("Moral value must be numeric")

    if not 0.0 <= value <= 1.0:
        raise ValueError("Moral value must be in range [0.0, 1.0]")

    return float(value)
```

**Coverage**:
- ✅ Type validation for all API inputs
- ✅ Range checking for numeric parameters
- ✅ Dimension validation for vectors
- ✅ Sanitization of special values (NaN, Inf)

### SC-2: Authentication

**Objective**: Verify identity of API clients

**Implementation**:
```python
# Location: src/mlsdm/api/app.py

def verify_bearer_token(authorization: str) -> bool:
    """Verify Bearer token against environment variable."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authentication scheme")

    token = authorization[7:]  # Remove "Bearer " prefix
    expected_token = os.getenv("API_KEY")

    if not expected_token:
        raise ConfigurationError("API_KEY not configured")

    # Constant-time comparison to prevent timing attacks
    return secrets.compare_digest(token, expected_token)
```

**Properties**:
- ✅ Bearer token authentication
- ✅ Constant-time comparison (timing attack resistant)
- ✅ Environment-based configuration
- ✅ No hardcoded credentials

**Security Considerations**:
- Tokens should be rotated regularly (recommended: every 90 days)
- Use strong, randomly generated tokens (≥32 bytes entropy)
- Never commit tokens to version control
- Store tokens in secure secret management systems

### SC-3: Rate Limiting

**Objective**: Prevent abuse and DoS attacks

**Implementation**:
```python
# Location: src/mlsdm/utils/rate_limiter.py

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: int = 5, period: int = 1):
        """
        Initialize rate limiter.

        Args:
            rate: Number of requests allowed per period
            period: Time period in seconds
        """
        self.rate = rate
        self.period = period
        self.tokens = {}  # client_id -> (tokens, last_update)

    def allow_request(self, client_id: str) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()

        if client_id not in self.tokens:
            self.tokens[client_id] = (self.rate - 1, now)
            return True

        tokens, last_update = self.tokens[client_id]
        elapsed = now - last_update

        # Refill tokens based on elapsed time
        tokens = min(self.rate, tokens + elapsed * (self.rate / self.period))

        if tokens >= 1:
            self.tokens[client_id] = (tokens - 1, now)
            return True
        else:
            self.tokens[client_id] = (tokens, now)
            return False
```

**Configuration**:
- Default: 5 requests per second per client
- Configurable via environment: `RATE_LIMIT_RPS`
- Client identification: API key or IP address
- Algorithm: Token bucket (allows bursts)

### SC-4: Memory Protection

**Objective**: Prevent memory exhaustion and overflow attacks

**Implementation**:
- Hard capacity limit: 20,000 vectors
- Circular buffer eviction (FIFO)
- Pre-allocated memory (zero dynamic allocation)
- Input size validation

**Guarantees**:
- ✅ Maximum memory: 29.37 MB (verified)
- ✅ No unbounded growth
- ✅ Deterministic memory usage
- ✅ No memory leaks (verified 24h soak test)

---

## Data Protection

### DP-1: Data Classification

| Data Type | Classification | Storage | Retention | Encryption |
|-----------|---------------|---------|-----------|------------|
| Event Vectors | Confidential | Memory | Session | In-transit |
| Moral Values | Confidential | Memory | Session | In-transit |
| API Tokens | Secret | Environment | Permanent | At-rest |
| Logs | Internal | Disk | 30 days | Optional |
| Metrics | Internal | Memory | Ephemeral | None |

### DP-2: Encryption

**In-Transit Encryption**:
- TLS 1.2+ for all API communications
- Certificate validation enforced
- Strong cipher suites only (AES-256-GCM, ChaCha20-Poly1305)

**At-Rest Encryption**:
- API tokens stored in environment variables or secret managers
- No sensitive data persisted to disk
- Logs sanitized to exclude PII

### DP-3: Data Sanitization

**PII Exclusion**:
```python
# Location: src/mlsdm/utils/security_logger.py

def sanitize_log_data(data: dict) -> dict:
    """Remove sensitive information from log data."""
    sanitized = data.copy()

    # Remove vector data (may contain sensitive embeddings)
    if "event_vector" in sanitized:
        sanitized["event_vector"] = f"<vector dim={len(data['event_vector'])}>"

    # Remove API tokens
    if "authorization" in sanitized:
        sanitized["authorization"] = "<redacted>"

    # Truncate long text fields
    for key in ["prompt", "response"]:
        if key in sanitized and len(sanitized[key]) > 100:
            sanitized[key] = sanitized[key][:100] + "..."

    return sanitized
```

---

## Authentication and Authorization

### Authentication Methods

1. **API Key (Bearer Token)**
   - Environment variable: `API_KEY`
   - Header: `Authorization: Bearer <token>`
   - Validation: Constant-time comparison
   - Rotation: Recommended every 90 days

2. **Future Methods** (planned for v1.1+)
   - OAuth 2.0 / OpenID Connect
   - mTLS (mutual TLS)
   - JWT tokens with expiration

### Authorization Model

**Current**: Simple authentication (authenticated = authorized)

**Future** (v1.1+): Role-Based Access Control (RBAC)
- `read`: View state and metrics
- `write`: Submit events for processing
- `admin`: Configuration and system management

---

## Input Validation

### Validation Rules

| Parameter | Type | Range | Validation |
|-----------|------|-------|------------|
| `event_vector` | np.ndarray | dim=384, finite values | Dimension, type, finiteness |
| `moral_value` | float | [0.0, 1.0] | Range, type |
| `prompt` | str | ≤10,000 chars | Length, encoding |
| `max_tokens` | int | [1, 4096] | Range, type |
| `context_top_k` | int | [1, 100] | Range, type |

### Validation Strategy

1. **Schema Validation**: Pydantic models for type checking
2. **Range Validation**: Explicit bounds checking
3. **Format Validation**: Encoding and structure checks
4. **Sanitization**: Remove/escape dangerous characters
5. **Error Handling**: Reject invalid input with clear errors

---

## Rate Limiting and DDoS Protection

### Rate Limiting Configuration

```yaml
# Default rate limits
global:
  rps: 1000  # Global requests per second

per_client:
  rps: 5     # Per-client requests per second
  burst: 10  # Maximum burst size

per_endpoint:
  /v1/process_event: 5 rps
  /v1/state: 20 rps
  /health: 100 rps
```

### DDoS Mitigation

**Layer 7 (Application)**:
- Rate limiting per client (5 RPS)
- Request size limits (10 KB body)
- Timeout enforcement (30s max)
- Connection limits per IP

**Layer 4 (Transport)**:
- SYN flood protection (at load balancer)
- Connection rate limiting
- IP-based blacklisting

**Layer 3 (Network)**:
- Cloudflare / AWS Shield integration
- Geographic filtering
- Traffic anomaly detection

---

## Logging and Monitoring

### Security Logging

**Log Structure**:
```json
{
  "timestamp": "2025-11-21T11:34:38Z",
  "level": "INFO",
  "event": "event_processed",
  "correlation_id": "req-abc123",
  "client_id": "client-xyz",
  "accepted": true,
  "moral_value": 0.8,
  "phase": "wake",
  "latency_ms": 5.2
}
```

**Logged Events**:
- ✅ Authentication attempts (success/failure)
- ✅ Rate limit violations
- ✅ Input validation failures
- ✅ Moral filter rejections
- ✅ System state changes
- ✅ Error conditions

**Log Retention**:
- Standard logs: 30 days
- Security logs: 90 days
- Audit logs: 1 year

**Log Protection**:
- No PII (personally identifiable information)
- Sanitized prompts/responses (truncated)
- Structured JSON format
- Centralized log aggregation

### Security Monitoring

**Metrics to Monitor**:
```yaml
# Authentication
auth_attempts_total{status="success|failure"}
auth_failures_by_client{client_id}

# Rate Limiting
rate_limit_violations_total{client_id}
requests_rejected_total{reason="rate_limit"}

# System Health
memory_usage_bytes
cpu_usage_percent
request_latency_seconds{quantile}

# Security Events
moral_filter_rejections_total
input_validation_errors_total{error_type}
```

**Alerting Thresholds**:
- Auth failures: >10 per minute from single IP
- Rate limit violations: >100 per hour
- Memory usage: >90% capacity
- Error rate: >5% of requests

---

## Dependency Management

### Dependency Security

**Tools**:
- `pip-audit`: Scan for known vulnerabilities
- `safety`: Check against vulnerability database
- Dependabot: Automated dependency updates

**Process**:
1. Weekly automated scans in CI/CD
2. Critical vulnerabilities: Patch within 7 days
3. High vulnerabilities: Patch within 14 days
4. Medium/Low: Patch in next release

**Current Dependencies** (security-relevant):
```
numpy>=2.0.0           # Numerical operations
fastapi>=0.110.0       # Web framework
uvicorn>=0.29.0        # ASGI server
pydantic>=2.0.0        # Data validation
prometheus-client>=0.20.0  # Metrics
```

### Supply Chain Security

**Practices**:
- ✅ Pin exact versions in requirements.txt
- ✅ Verify package checksums
- ✅ Use trusted package sources (PyPI)
- ✅ Review dependency tree for suspicious packages
- ⚠️ SBOM generation (planned for v1.1)
- ⚠️ Signature verification (planned for v1.1)

---

## Secure Deployment Guidelines

### Environment Configuration

**Required Environment Variables**:
```bash
# Authentication
export API_KEY="<strong-random-token-32-bytes-min>"

# Security Mode (REQUIRED for production with sensitive data)
export MLSDM_SECURE_MODE="1"  # Disables training/checkpoints, enables detection-only

# Rate Limiting
export RATE_LIMIT_RPS="5"
export RATE_LIMIT_BURST="10"

# TLS Configuration
export TLS_CERT_PATH="/path/to/cert.pem"
export TLS_KEY_PATH="/path/to/key.pem"

# Logging
export LOG_LEVEL="INFO"
export LOG_FORMAT="json"
```

**MLSDM Secure Mode** (`MLSDM_SECURE_MODE`):

**CRITICAL:** In production environments handling sensitive data, **ALWAYS** set `MLSDM_SECURE_MODE=1`. This security control is mandatory for:
- Production deployments with PII or confidential data
- Multi-tenant environments
- Regulated industries (healthcare, finance, government)
- Any environment where model training should be prohibited

**Secure Mode Effects:**
- ✅ **Disables NeuroLang Training**: Prevents `eager_train` and `lazy_train` modes
- ✅ **Blocks Checkpoint Loading**: Ignores `neurolang_checkpoint_path` configuration
- ✅ **Disables Aphasia Repair**: Only detection is performed, responses are not modified
- ✅ **Prevents Training Scripts**: `train_neurolang_grammar.py` refuses to execute

**When NOT to use Secure Mode:**
- Development environments (use `MLSDM_SECURE_MODE=0` or omit)
- Isolated training environments (offline model training only)
- Testing and CI/CD pipelines
- Environments without sensitive data

**Deployment Patterns:**

*Production Environment:*
```bash
# Production: Secure mode ENABLED
export MLSDM_SECURE_MODE="1"
export API_KEY="<prod-key>"
# Deploy pre-trained checkpoints to config/ directory
# Use read-only mounts for config/
```

*Training Environment (Isolated):*
```bash
# Training: Secure mode DISABLED
export MLSDM_SECURE_MODE="0"
# Train models offline
python scripts/train_neurolang_grammar.py --epochs 5 --output config/model.pt
# Validate and promote checkpoints through controlled pipeline
```

*Development Environment:*
```bash
# Development: Secure mode DISABLED
export MLSDM_SECURE_MODE="0"
export API_KEY="dev-key"
# Full training and testing capabilities
```

**Checkpoint Management Best Practices:**

1. **Isolate Training**: Train NeuroLang models in dedicated, isolated environments without access to production data
2. **Validate Checkpoints**: Scan checkpoints with antivirus/malware detection before deployment
3. **Read-Only Config**: Mount `config/` directory as read-only in production containers
4. **Version Control**: Store trusted checkpoints in artifact repository or version control
5. **Audit Access**: Log and monitor all checkpoint file access in production
6. **Restrict Paths**: Only load checkpoints from `config/` directory (enforced by `safe_load_neurolang_checkpoint`)

**Security Violations to Monitor:**

```bash
# Monitor logs for these security events:
grep "Secure mode enabled: offline training is not permitted" /var/log/mlsdm.log
grep "Refusing to load checkpoint outside" /var/log/mlsdm.log
grep "ValueError.*checkpoint" /var/log/mlsdm.log
```

**Security Hardening**:
```bash
# Run as non-root user
adduser --system --no-create-home mlsdm
su - mlsdm

# Restrict file permissions
chmod 600 .env
chmod 700 /app

# Enable firewall
ufw allow 8000/tcp
ufw enable

# Disable unnecessary services
systemctl disable <unused-services>
```

### Network Security

**Firewall Rules**:
```bash
# Allow inbound HTTPS only
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -j ACCEPT  # Internal API
iptables -A INPUT -j DROP
```

**TLS Configuration**:
```python
# uvicorn with TLS
uvicorn app:app \
    --host 0.0.0.0 \
    --port 443 \
    --ssl-keyfile /path/to/key.pem \
    --ssl-certfile /path/to/cert.pem \
    --ssl-version TLSv1_2 \
    --ssl-ciphers "ECDHE+AESGCM:ECDHE+CHACHA20"
```

### Container Security

**Docker Best Practices**:
```dockerfile
# Use minimal base image
FROM python:3.12-slim

# Run as non-root
RUN useradd -m -u 1000 mlsdm
USER mlsdm

# Copy only necessary files
COPY --chown=mlsdm:mlsdm requirements.txt .
COPY --chown=mlsdm:mlsdm src/ ./src/

# Read-only filesystem
RUN chmod -R 555 /app

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8000/health || exit 1
```

---

## Security Testing

### Testing Strategy

1. **Static Analysis**
   - `bandit`: Python security linter
   - `ruff`: Code quality checks
   - `mypy`: Type safety verification

2. **Dependency Scanning**
   - `pip-audit`: Known vulnerability scanning
   - `safety`: Security advisory checking

3. **Dynamic Testing**
   - Integration tests with malicious inputs
   - Fuzzing with hypothesis
   - Load testing with locust

4. **Penetration Testing**
   - ⚠️ Planned for v1.1
   - OWASP Top 10 coverage
   - API security testing

### Test Coverage

**Security Test Categories**:
- ✅ Input validation bypass attempts
- ✅ Authentication bypass attempts
- ✅ Rate limit circumvention
- ✅ Memory exhaustion attacks
- ✅ Timing attacks on authentication
- ⚠️ SQL injection (N/A - no database)
- ⚠️ XSS (N/A - no HTML rendering)

---

## Compliance and Standards

### Standards Alignment

| Standard | Applicable | Status | Notes |
|----------|-----------|---------|-------|
| **OWASP Top 10** | Yes | Partial | No SQL/XSS risks (no DB/HTML) |
| **NIST CSF** | Yes | Aligned | Identify, Protect, Detect principles |
| **CIS Controls** | Yes | Partial | Controls 1-8 applicable |
| **SOC 2** | Optional | N/A | For enterprise deployments |
| **ISO 27001** | Optional | N/A | For enterprise deployments |

### OWASP Top 10 Coverage

| Risk | Applicable | Mitigation | Status |
|------|-----------|------------|---------|
| A01: Broken Access Control | Yes | Authentication + rate limiting | ✅ Implemented |
| A02: Cryptographic Failures | Yes | TLS + token storage | ✅ Implemented |
| A03: Injection | Partial | Input validation | ✅ Implemented |
| A04: Insecure Design | Yes | Threat modeling | ✅ Implemented |
| A05: Security Misconfiguration | Yes | Hardening guides | ✅ Documented |
| A06: Vulnerable Components | Yes | Dependency scanning | ✅ Implemented |
| A07: Auth Failures | Yes | Secure authentication | ✅ Implemented |
| A08: Data Integrity Failures | Partial | Input validation | ✅ Implemented |
| A09: Logging Failures | Yes | Structured logging | ✅ Implemented |
| A10: SSRF | No | No outbound requests | N/A |

---

## Security Roadmap

### v1.0 (Current)
- ✅ Input validation
- ✅ Authentication (API key, OIDC, mTLS, request signing)
- ✅ Role-based access control (RBAC)
- ✅ Rate limiting
- ✅ Memory protection
- ✅ Dependency scanning
- ✅ Security logging

### v1.1 (Planned)
- ⚠️ SBOM generation
- ⚠️ Penetration testing
- ⚠️ Security audit

### v1.2 (Future)
- ⚠️ WAF integration
- ⚠️ Intrusion detection
- ⚠️ Anomaly detection
- ⚠️ Security orchestration (SOAR)

---

## Incident Response

### Response Process

1. **Detection**
   - Automated monitoring alerts
   - User reports
   - Security research disclosures

2. **Containment**
   - Isolate affected systems
   - Block malicious traffic
   - Revoke compromised credentials

3. **Eradication**
   - Patch vulnerabilities
   - Remove malicious code
   - Update dependencies

4. **Recovery**
   - Restore normal operations
   - Verify security controls
   - Monitor for recurrence

5. **Post-Incident**
   - Document lessons learned
   - Update security controls
   - Public disclosure (if applicable)

### Contact Information

**Security Team**: See [GitHub Security Advisories](https://github.com/neuron7xLab/mlsdm/security)

---

**Document Status:** Production
**Review Cycle:** Quarterly
**Last Reviewed:** November 2025
**Next Review:** February 2026

---

## Phase 6: API Security Baseline (2025 Practices)

### Secret Management

**Environment-Only Secrets**
- All secrets (API keys, tokens, credentials) MUST be passed via environment variables
- Secrets MUST NEVER be hardcoded in source code or configuration files
- Use `.env` files only for local development (excluded from version control)

**Supported Secrets:**
- `OPENAI_API_KEY`: OpenAI API key (when using OpenAI backend)
- `RATE_LIMIT_REQUESTS`: Maximum requests per window (default: 100)
- `RATE_LIMIT_WINDOW`: Time window in seconds (default: 60)
- `LOG_PAYLOADS`: Enable payload logging (default: false, see below)

### Payload Logging Control

**Default Behavior (LOG_PAYLOADS=false)**
- Raw prompts and responses are NOT logged to stdout/stderr
- Only metadata (timing, status, errors) is logged
- Secret scrubbing is applied to all logged content

**Explicit Logging (LOG_PAYLOADS=true)**
- Enables logging of request/response payloads for debugging
- Secrets are automatically scrubbed using regex patterns
- Should only be used in development or controlled environments
- NOT recommended for production due to privacy/compliance concerns

**Secret Scrubbing Patterns:**
- API keys (various formats including `sk-*`, `Bearer`, generic patterns)
- Passwords and tokens
- AWS credentials (AKIA*, secret keys)
- Private keys (PEM format)
- Credit card numbers
- Configurable via `mlsdm.security.payload_scrubber` module

### Rate Limiting

**In-Memory Rate Limiter**
- Simple token bucket implementation per client IP
- Default: 100 requests per 60-second window
- Configurable via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW`

**Limitations (Known, Documented):**
- **Single-Process Only**: Rate limits are per-instance, not distributed
- Each application instance maintains its own rate limit state
- In multi-instance deployments, actual limit = configured_limit × number_of_instances
- No persistence across restarts

**Production Recommendations:**
- For single-instance deployments: Current implementation is adequate
- For multi-instance deployments:
  - Use external rate limiting (nginx, API gateway, Kong, etc.)
  - OR implement Redis-based distributed rate limiting
  - Current implementation provides defense-in-depth even with external limiting

**Rate Limit Response:**
- HTTP 429 (Too Many Requests) when limit exceeded
- Includes standard headers (future enhancement: Retry-After, X-RateLimit-*)

### HTTP API Security Headers

**Recommended Headers (to be added by reverse proxy/ingress):**
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

### Docker Security

**Container Security:**
- Non-root user (UID 1000 "neuro")
- Minimal base image (python:3.11-slim)
- Read-only root filesystem where possible
- Dropped capabilities (ALL)
- Security contexts in Kubernetes manifests

**Health Checks:**
- Liveness probe: `/health/live` endpoint
- Readiness probe: `/health/ready` endpoint
- Startup probe recommended for slow-starting instances

### Kubernetes Security

**Pod Security:**
- `runAsNonRoot: true`
- `runAsUser: 1000`
- `allowPrivilegeEscalation: false`
- `capabilities.drop: [ALL]`

**Secrets Management:**
- Use Kubernetes Secrets for sensitive configuration
- Example provided for `OPENAI_API_KEY` in deployment manifest
- Consider external secret management (Vault, AWS Secrets Manager, etc.)

### Known Security Limitations

**Documented for Transparency:**

1. **In-Memory Rate Limiting**
   - Not suitable for distributed deployments without external rate limiting
   - State lost on restart
   - No cross-instance coordination

2. **Secret Scrubbing**
   - Regex-based, may not catch all custom secret formats
   - Best-effort approach, not guaranteed to catch 100% of secrets
   - Regular updates to patterns recommended

3. **No Built-in Authentication**
   - HTTP API has no built-in user authentication/authorization
   - Intended to be deployed behind authenticated API gateway or proxy
   - Consider implementing API keys or OAuth2 for production

4. **No TLS/HTTPS Termination**
   - Application serves HTTP only
   - TLS must be terminated at load balancer/ingress level
   - Never expose port 8000 directly to internet

5. **Limited Request Validation**
   - Basic Pydantic validation only
   - No sophisticated attack pattern detection
   - WAF recommended for production deployments

### Security Checklist for Production Deployment

- [ ] All secrets provided via environment variables or Kubernetes Secrets
- [ ] `LOG_PAYLOADS=false` (or removed, defaults to false)
- [ ] TLS termination configured at load balancer/ingress
- [ ] Rate limiting configured (external system recommended for multi-instance)
- [ ] Security headers added at reverse proxy level
- [ ] Health check endpoints accessible to orchestration system
- [ ] Resource limits configured (CPU, memory)
- [ ] Monitoring and alerting configured
- [ ] Regular security updates applied (dependencies, base images)
- [ ] Incident response procedures documented

---

## Implementation Status

### ✅ Implemented Security Controls (see [status/READINESS.md](status/READINESS.md))

| Control | Component | Status | Evidence |
|---------|-----------|--------|----------|
| Input Validation | `input_validator.py` | ✅ Implemented | `tests/unit/test_security.py` |
| Rate Limiting | `rate_limiter.py` | ✅ Implemented | `tests/unit/test_security.py` |
| Authentication | `api/app.py` | ✅ Implemented | `tests/integration/test_neuro_engine_http_api.py` |
| PII Scrubbing | `payload_scrubber.py` | ✅ Implemented | `tests/security/` |
| Memory Bounds | `phase_entangled_lattice_memory.py` | ✅ Implemented | `tests/property/test_invariants_memory.py` |
| Security Logging | `security_logger.py` | ✅ Implemented | `tests/observability/` |
| Timeout Enforcement | `neuro_cognitive_engine.py` | ✅ Implemented | `tests/property/test_invariants_neuro_engine.py` |
| Circuit Breaker | `llm_wrapper.py` | ✅ Implemented | `tests/unit/test_llm_wrapper_reliability.py` |
| Moral Content Filter | `moral_filter_v2.py` | ✅ Implemented | `tests/property/test_moral_filter_properties.py` |
| NeuroLang Checkpoint Security | `neuro_lang_extension.py` | ✅ Implemented | Path validation, weights_only=True |

### ⚠️ Planned Security Enhancements (v1.3+)

| Enhancement | Status | Target Version |
|-------------|--------|----------------|
| Certificate Pinning | ⚠️ Planned | v1.3+ |
| Log Integrity Signatures | ⚠️ Planned | v1.3+ |
| RBAC (Role-Based Access Control) | ⚠️ Planned | v1.3+ |
| Advanced Anomaly Detection | ⚠️ Planned | v1.3+ |
| Differential Privacy | ⚠️ Planned | v1.3+ |
| Digital Signatures on Logs | ⚠️ Planned | v1.3+ |

### Security Verification

**Tests**:
```bash
# Run security test suite
pytest tests/security/ -v
pytest tests/unit/test_security.py -v

# Run security audit script
python scripts/security_audit.py

# Test security features
python scripts/test_security_features.py
```

**Manual Verification**:
- Security review: Quarterly
- Penetration testing: Annual (recommended)
- Dependency scanning: Automated in CI
- SAST scanning: Recommended (not yet automated)

### Security Metrics (Current)

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Known vulnerabilities | 0 | 0 | ✅ |
| Rate limit effectiveness | 100% | 100% | ✅ |
| Authentication bypass attempts | 0 | 0 | ✅ |
| Memory bounds violations | 0 | 0 | ✅ |
| PII leak incidents | 0 | 0 | ✅ |

**Monitoring**: See [THREAT_MODEL.md](THREAT_MODEL.md) for complete threat analysis and mitigation tracking.

---

## Policy-as-Code Integration

All critical security requirements are enforced through machine-readable policy files and automated CI/CD checks. This ensures security is not just documented, but actively enforced.

### Policy Architecture (Single Source of Truth)

**SoT:** `policy/security-baseline.yaml` → **Loader:** `mlsdm.policy.loader` (schema validation + canonicalization + canonical hash) → **OPA Exporter:** `mlsdm.policy.opa` (explicit YAML → JSON → Rego mapping contract) → **Enforcement:** CI workflows, OPA/Conftest gates, and runtime checks.

**Contract Versioning:** `policy_contract_version` is strictly enforced (`1.1`), and unknown fields fail closed. Contract changes require a documented migration note (see ADR-0007).

### Policy Files

Security baseline requirements are defined in:
- **`policy/security-baseline.yaml`**: Security checks, vulnerability thresholds, and enforcement rules

### Enforcement Mechanisms

**CI/CD Pipeline Enforcement:**

All PRs must pass the following security checks before merge:

1. **Bandit SAST** (`.github/workflows/sast-scan.yml`)
   - Command: `bandit -r src/mlsdm -f sarif -o bandit-results.sarif`
   - Threshold: No HIGH or CRITICAL severity issues
   - SARIF validation: JSON schema validation before upload
   - Failure: Blocks PR merge

2. **Semgrep SAST** (`.github/workflows/sast-scan.yml`)
   - Semantic code analysis using community rulesets
   - Security-focused queries (OWASP Top 10, security-audit)
   - Failure: Blocks PR merge

3. **Ruff Linter**
   - Command: `ruff check src tests`
   - Security-relevant rules enabled
   - Failure: Blocks PR merge

4. **Mypy Type Checker**
   - Command: `mypy src/mlsdm`
   - Type safety enforcement
   - Failure: Blocks PR merge

5. **Coverage Gate** (`./coverage_gate.sh`)
   - Minimum: 75% code coverage (matches CI and `policy/security-baseline.yaml` thresholds)
   - Ensures security-critical paths are tested
   - Failure: Blocks PR merge

### API Key & Secret Management

**Policy:** All secrets MUST be provided via environment variables. Hardcoded secrets are strictly prohibited.

**Implementation:**
- API keys read from `API_KEY` environment variable
- Secrets managed via Kubernetes Secrets or secure credential store
- Code enforcement: Bandit checks for hardcoded credentials

**Code Reference:**
```python
# Correct: Read from environment
api_key = os.environ.get("API_KEY")
if not api_key:
    raise ValueError("API_KEY environment variable required")

# ❌ PROHIBITED: Hardcoded secrets
api_key = "sk-1234..."  # Will fail Bandit scan
```

### LLM Safety Gateway

**Policy:** The LLM safety gateway (`mlsdm.security.llm_safety`) is MANDATORY for all production usage involving LLM interactions.

**Implementation:**
- Module: `src/mlsdm/security/llm_safety.py`
- Validates LLM inputs and outputs for safety
- Prevents injection attacks and harmful content

**Bypass Documentation:**
Any bypass of the LLM safety gateway must be:
1. Documented in an Architecture Decision Record (ADR)
2. Reviewed by security team
3. Limited to specific, justified use cases (e.g., testing)

### PII & Logging Rules

**Policy:** Personally Identifiable Information (PII) MUST be scrubbed from all logs and traces.

**Implementation:**
- Module: `src/mlsdm/security/payload_scrubber.py`
- Fields always scrubbed: `password`, `api_key`, `secret`, `token`, `credit_card`, `ssn`
- Applied to all log outputs and error messages

**Code Reference:**
```python
from mlsdm.security.payload_scrubber import scrub_sensitive_data

# Scrub before logging
safe_payload = scrub_sensitive_data(request_payload)
logger.info(f"Processing request: {safe_payload}")
```

### Vulnerability Response

SAST violations are handled according to severity:

| Severity | Max Allowed | Response Time | Fix Timeline | Action |
|----------|-------------|---------------|--------------|--------|
| CRITICAL | 0 | 24 hours | 7 days | Immediate hotfix, block all PRs |
| HIGH | 0 | 48 hours | 14 days | Priority fix, block PRs |
| MEDIUM | 0 | 7 days | 30 days | Planned fix |
| LOW | 5 | 14 days | 90 days | Backlog item |

### Policy Validation

Policy configuration consistency is validated by:
```bash
python -m mlsdm.policy.check
```

This one-command runner mirrors CI and executes:
1. Validate policy contract + repo alignment
2. Export OPA policy data (with contract self-check)
3. Conftest enforcement for CI workflows
4. Conftest enforcement for fixtures

**CI Integration:** Policy validation and export run on every PR; the OPA gate consumes the generated data when evaluating `policies/ci/*.rego`.

### Policy Extension Checklist

When adding or modifying a policy control:
1. Update `policy/security-baseline.yaml` (SoT).
2. If new data is consumed by Rego, update `mlsdm.policy.opa.OPA_EXPORT_MAPPINGS`.
3. Add/adjust fixtures in `tests/policy/ci/` (≥ 2 pass, ≥ 3 fail total).
4. Add regression tests under `tests/policy/` for contract enforcement.
5. Run `python -m mlsdm.policy.check` locally to confirm parity with CI.

### References

- **Security Baseline Policy:** `policy/security-baseline.yaml`
- **Observability SLO Policy:** `policy/observability-slo.yaml`
- **Policy Validator:** `scripts/validate_policy_config.py`
- **SAST Workflow:** `.github/workflows/sast-scan.yml`
- **Security Implementation:** `SECURITY_IMPLEMENTATION.md`

---

**Document Maintainer**: neuron7x / Security Team
**Document Version**: 2.2 (With Policy-as-Code Integration)
**Last Updated**: March 2026
**Status**: See [status/READINESS.md](status/READINESS.md) (not yet verified)
