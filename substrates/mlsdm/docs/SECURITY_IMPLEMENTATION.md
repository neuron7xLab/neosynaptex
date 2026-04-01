# Security Implementation Guide

This document provides comprehensive details about the security features implemented in the MLSDM Governed Cognitive Memory system.

## Table of Contents

1. [Overview](#overview)
2. [Security Features](#security-features)
3. [Rate Limiting](#rate-limiting)
4. [Input Validation](#input-validation)
5. [Security Logging](#security-logging)
6. [Authentication](#authentication)
7. [Dependency Security](#dependency-security)
8. [Best Practices](#best-practices)
9. [Testing](#testing)

## Overview

The MLSDM Governed Cognitive Memory system implements multiple layers of security controls to protect against common threats outlined in the THREAT_MODEL.md. All security features are designed according to SECURITY_POLICY.md requirements.

### Security Principles

- **Defense in Depth**: Multiple layers of security controls
- **Fail Secure**: System fails safely when errors occur
- **Least Privilege**: Components have minimal required permissions
- **Privacy by Design**: No PII stored or logged
- **Audit Everything**: Comprehensive security event logging

## Security Features

### Implemented Features

✅ **Rate Limiting** - 5 RPS per client using leaky bucket algorithm
✅ **Input Validation** - Comprehensive validation and sanitization
✅ **Security Logging** - Structured JSON logs with correlation IDs
✅ **Authentication** - Bearer token with OAuth2 scheme
✅ **Dependency Scanning** - Automated vulnerability detection
✅ **Error Handling** - Safe error messages (no information disclosure)

## Rate Limiting

### Implementation

The rate limiter uses a **leaky bucket algorithm** to provide smooth rate limiting across clients.

**Location**: `src/mlsdm/utils/rate_limiter.py`

**Configuration**:
- Rate: 5 requests per second (RPS)
- Burst capacity: 10 requests
- Per-client tracking using pseudonymized identifiers

### Usage

```python
from mlsdm.utils.rate_limiter import RateLimiter

# Initialize rate limiter
limiter = RateLimiter(rate=5.0, capacity=10)

# Check if request is allowed
if limiter.is_allowed(client_id):
    # Process request
    pass
else:
    # Return 429 Too Many Requests
    raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

### Features

- **Thread-safe**: Safe for concurrent use
- **Per-client limits**: Independent limits for each client
- **Automatic refill**: Tokens refill over time based on rate
- **Cleanup**: Automatic cleanup of old client entries

### Testing

```bash
python -m pytest tests/unit/test_rate_limiter.py -v
```

## Input Validation

### Implementation

Comprehensive input validation prevents injection attacks, data corruption, and ensures data integrity.

**Location**: `src/mlsdm/utils/input_validator.py`

### Validation Features

1. **Vector Validation**
   - Dimension checking
   - NaN/Inf detection
   - Size limits (max 100,000 dimensions)
   - Optional normalization

2. **Moral Value Validation**
   - Range checking [0.0, 1.0]
   - Type validation
   - NaN/Inf rejection

3. **String Sanitization**
   - Null byte removal (injection prevention)
   - Control character filtering
   - Length limits (default 10,000 chars)
   - Optional newline handling

4. **Numeric Range Validation**
   - Min/max bounds checking
   - Type validation
   - NaN/Inf rejection

### Usage Examples

```python
from mlsdm.utils.input_validator import InputValidator

validator = InputValidator()

# Validate vector
try:
    vector = validator.validate_vector(
        [1.0, 2.0, 3.0],
        expected_dim=3,
        normalize=True
    )
except ValueError as e:
    # Handle validation error
    logger.error(f"Invalid vector: {e}")

# Validate moral value
try:
    moral_value = validator.validate_moral_value(0.75)
except ValueError as e:
    # Handle validation error
    logger.error(f"Invalid moral value: {e}")

# Sanitize string
try:
    safe_string = validator.sanitize_string(
        user_input,
        max_length=1000,
        allow_newlines=False
    )
except ValueError as e:
    # Handle validation error
    logger.error(f"Invalid string: {e}")
```

### Constants

```python
MAX_VECTOR_SIZE = 100_000      # Maximum vector dimension
MAX_ARRAY_ELEMENTS = 1_000_000 # Maximum array size
MIN_MORAL_VALUE = 0.0          # Minimum moral value
MAX_MORAL_VALUE = 1.0          # Maximum moral value
```

### Testing

```bash
python -m pytest tests/unit/test_input_validator.py -v
```

## Security Logging

### Implementation

Structured security logging system with correlation IDs for tracking requests across components. **No PII is logged.**

**Location**: `src/mlsdm/utils/security_logger.py`

### Event Types

- **Authentication**: Success/failure/missing
- **Authorization**: Access denied
- **Rate Limiting**: Exceeded/warning
- **Input Validation**: Invalid input/dimension mismatch
- **State Changes**: Important system state changes
- **Anomalies**: Detected anomalies/threshold breaches
- **System**: Startup/shutdown/errors

### Log Format

All logs are structured JSON with the following fields:

```json
{
  "timestamp": 1234567890.123,
  "correlation_id": "uuid-string",
  "event_type": "auth_failure",
  "message": "Authentication failed: Invalid token",
  "client_id": "pseudonymized-hash",
  "data": {
    "reason": "Invalid token"
  }
}
```

### Usage

```python
from mlsdm.utils.security_logger import get_security_logger

logger = get_security_logger()

# Log authentication events
logger.log_auth_success(client_id="abc123")
logger.log_auth_failure(client_id="abc123", reason="Invalid token")

# Log rate limiting
logger.log_rate_limit_exceeded(client_id="abc123")

# Log validation errors
logger.log_invalid_input(client_id="abc123", error_message="Dimension mismatch")

# Log state changes
logger.log_state_change(
    change_type="phase_transition",
    details={"from": "wake", "to": "sleep"}
)

# Log anomalies
logger.log_anomaly(
    anomaly_type="threshold_breach",
    description="Moral filter exceeded bounds",
    severity="high"
)
```

### Privacy Protection

The logger **automatically filters** PII fields:
- `email`
- `username`
- `password`
- `token`

Client identifiers are **pseudonymized** using SHA256 hashing.

### Testing

```bash
python -m pytest tests/unit/test_security_logger.py -v
```

## Authentication

### Implementation

OAuth2 Bearer token authentication with enhanced security logging.

**Location**: `src/mlsdm/api/app.py`

### Configuration

Set the API key via environment variable:

```bash
export API_KEY="your-secure-api-key-here"
```

If `API_KEY` is not set, authentication is disabled (for development only).

### Request Format

```http
GET /v1/state/
Authorization: Bearer your-api-key-here
```

### Security Features

- Bearer token validation
- Failed attempt logging
- Pseudonymized client tracking
- No token exposure in logs

### Client Identification

Clients are identified using a pseudonymized hash:

```python
# SHA256(IP_address:User-Agent)[:16]
client_id = hashlib.sha256(f"{ip}:{user_agent}".encode()).hexdigest()[:16]
```

This allows rate limiting and audit tracking without storing PII.

## Dependency Security

### Automated Scanning

The system includes automated dependency vulnerability scanning using `pip-audit`.

### Running Security Audit

```bash
# Basic scan
python scripts/security_audit.py

# Scan and attempt to fix vulnerabilities
python scripts/security_audit.py --fix

# Scan installed environment explicitly (optional)
python scripts/security_audit.py --env

# Generate report file
python scripts/security_audit.py --report security_report.txt
```

### What Gets Checked

1. **Dependency Vulnerabilities**: Known CVEs in dependencies
2. **Configuration Files**: Presence of SECURITY_POLICY.md, THREAT_MODEL.md
3. **Security Implementations**: Rate limiter, validator, logger, tests

### CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/security.yml
- name: Security Audit
  run: |
    python scripts/security_audit.py
```

### Remediation

When vulnerabilities are found:

1. Review the vulnerability details
2. Check if a fix is available
3. Update the dependency: `pip install --upgrade package-name`
4. Test the system thoroughly
5. Re-run security audit

## Best Practices

### Development

1. **Never commit secrets** to source control
2. **Use environment variables** for configuration
3. **Validate all inputs** before processing
4. **Log security events** appropriately
5. **Test security features** regularly

### Deployment

1. **Set strong API keys** (min 32 characters, random)
2. **Use TLS/HTTPS** for all API endpoints
3. **Enable rate limiting** in production
4. **Monitor security logs** regularly
5. **Keep dependencies updated**

### API Usage

1. **Protect API keys** (never expose in client code)
2. **Rotate keys periodically** (every 90 days recommended)
3. **Use HTTPS only** for API requests
4. **Respect rate limits** (5 RPS)
5. **Handle errors gracefully**

### Code Review Checklist

- [ ] Input validation on all external inputs
- [ ] Error handling doesn't expose sensitive info
- [ ] Security events are logged
- [ ] No hardcoded secrets
- [ ] Rate limiting applied to endpoints
- [ ] Authentication required where appropriate
- [ ] Dependencies are up to date
- [ ] Tests cover security scenarios

## Testing

### Running Security Tests

```bash
# All security tests
python -m pytest tests/security -v

# Specific test classes
python -m pytest tests/unit/test_rate_limiter.py -v
python -m pytest tests/unit/test_input_validator.py -v
python -m pytest tests/unit/test_security_logger.py -v

# Integration tests
python -m pytest tests/security/test_security_invariants.py -v
```

### Test Coverage

The security test suite covers:

- ✅ Rate limiting (10 test cases)
- ✅ Input validation (20+ test cases)
- ✅ Security logging (12 test cases)
- ✅ Integration scenarios (3 test cases)

### Manual Testing

Test rate limiting:

```python
import requests
import time

# Make 6 rapid requests (5 should succeed, 6th should fail)
for i in range(6):
    response = requests.get(
        "http://localhost:8000/v1/state/",
        headers={"Authorization": "Bearer test_key"}
    )
    print(f"Request {i+1}: {response.status_code}")
    time.sleep(0.1)
```

Expected output:
```
Request 1: 200
Request 2: 200
Request 3: 200
Request 4: 200
Request 5: 200
Request 6: 429  # Rate limited!
```

## Security Metrics

Monitor these metrics in production:

- **Rate limit hits** per client per hour
- **Authentication failures** per hour
- **Input validation errors** per hour
- **Anomaly detections** per day
- **Dependency vulnerabilities** (scan weekly)

## Incident Response

If a security incident is detected:

1. **Isolate**: Disable affected API keys
2. **Investigate**: Review security logs
3. **Remediate**: Apply fixes
4. **Document**: Record findings
5. **Review**: Update security measures

## Contact

For security issues, please follow the responsible disclosure process outlined in SECURITY_POLICY.md.

## SAST Scanning

### Bandit Security Scanner

**Purpose**: Static Application Security Testing (SAST) to identify security vulnerabilities in Python code.

**Workflow**: `.github/workflows/sast-scan.yml`

**Command**:
```bash
bandit -r src/mlsdm \
  -f sarif \
  -o bandit-results.sarif \
  --severity-level medium \
  --confidence-level medium
```

**SARIF Validation**: Before uploading results to GitHub Security, the SARIF JSON is validated:

```python
import json

with open("bandit-results.sarif", "r", encoding="utf-8") as f:
    data = json.load(f)  # Will raise JSONDecodeError if invalid
print(f"✓ SARIF JSON validation passed")
```

**Enforcement**:
- HIGH/CRITICAL severity issues BLOCK PR merge
- SARIF must be valid JSON (schema validated)
- Upload only happens after validation passes

**Manual Run**:
```bash
# Install bandit with SARIF support
pip install bandit[sarif]

# Run scan
bandit -r src/mlsdm -f sarif -o bandit-results.sarif

# Validate SARIF
python -c "import json; json.load(open('bandit-results.sarif'))"

# Check for high severity issues
bandit -r src/mlsdm --severity-level high --confidence-level high
```

**False Positives**: If Bandit reports a false positive:
1. Review the finding carefully
2. If truly a false positive, add `# nosec` comment with justification
3. Document the suppression in PR description
4. Require security team review

Example:
```python
# Safe: API key from environment, not hardcoded
api_key = os.environ.get("API_KEY")  # nosec B108
```

### Semgrep Security Analysis

**Purpose**: Semantic code analysis for security patterns using community rulesets.

**Workflow**: `.github/workflows/sast-scan.yml`

**Features**:
- OWASP Top 10 vulnerability detection
- Security audit patterns
- Python-specific security rules
- Taint tracking and data flow analysis

**CI Integration**: Runs automatically on all PRs and blocks on findings.

**Note**: Semgrep complements Bandit by providing additional semantic analysis capabilities.

## Version History

- **v1.1.0** (2025-12-07): Enhanced SAST integration
  - Bandit SARIF with JSON validation
  - Policy-as-code enforcement
  - Documented exact commands and workflows

- **v1.0.0** (2025-11-20): Initial security implementation
  - Rate limiting (leaky bucket)
  - Input validation and sanitization
  - Security audit logging
  - Dependency scanning
  - Comprehensive test suite

---

**Remember**: Security is a continuous process. Regularly review and update security measures as the system evolves.
