# MFN Security Documentation

**Version:** v4.1.0  
**Last Updated:** 2025-12-01  
**Status:** Production Ready

---

## Executive Summary

MyceliumFractalNet implements comprehensive security measures to protect sensitive data, ensure secure API access, and comply with industry standards including GDPR and SOC 2. This document describes the security architecture, implemented controls, and best practices for secure deployment.

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Security Layers                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  Transport Layer     │  TLS 1.2+, HTTPS enforcement                      │
├─────────────────────────────────────────────────────────────────────────┤
│  Authentication      │  API Key (X-API-Key header)                       │
├─────────────────────────────────────────────────────────────────────────┤
│  Authorization       │  Role-based access, endpoint protection           │
├─────────────────────────────────────────────────────────────────────────┤
│  Rate Limiting       │  Token bucket algorithm, per-endpoint limits      │
├─────────────────────────────────────────────────────────────────────────┤
│  Input Validation    │  SQL injection, XSS, CSRF prevention              │
├─────────────────────────────────────────────────────────────────────────┤
│  Audit Logging       │  Structured JSON logs, compliance-ready           │
├─────────────────────────────────────────────────────────────────────────┤
│  Data Encryption     │  AES-128-CBC with HMAC-SHA256                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Authentication

### API Key Authentication

All protected API endpoints require authentication via the `X-API-Key` header.

```bash
# Authenticated request
curl -H "X-API-Key: your-api-key" https://api.example.com/validate
```

### Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `MFN_API_KEY_REQUIRED` | Require API key for protected endpoints | `false` (dev), `true` (prod) |
| `MFN_API_KEY` | Primary API key | — |
| `MFN_API_KEYS` | Comma-separated list of valid keys | — |

### Public Endpoints

The following endpoints do not require authentication:
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /docs` - API documentation (dev only)

### Security Properties

- **Constant-time comparison**: API keys are validated using `secrets.compare_digest()` to prevent timing attacks
- **No key exposure**: API keys are never logged or included in error responses
- **Multiple keys supported**: Allows key rotation without downtime

---

## 2. Rate Limiting

### Token Bucket Algorithm

Rate limiting prevents API abuse using the token bucket algorithm:
- Tokens are refilled at a configurable rate
- Each request consumes one token
- When tokens are exhausted, requests receive HTTP 429

### Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `MFN_RATE_LIMIT_ENABLED` | Enable rate limiting | `false` (dev), `true` (prod) |
| `MFN_RATE_LIMIT_REQUESTS` | Max requests per window | 100 |
| `MFN_RATE_LIMIT_WINDOW` | Window size in seconds | 60 |

### Per-Endpoint Limits

| Endpoint | Limit (requests/min) | Rationale |
|----------|---------------------|-----------|
| `/health` | 1000 | Health checks should be frequent |
| `/nernst` | 200 | Lightweight computation |
| `/validate` | 50 | Expensive computation |
| `/simulate` | 50 | Expensive computation |
| `/federated/aggregate` | 50 | Expensive computation |

### Response Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
Retry-After: 30  (only on 429)
```

---

## 3. Input Validation

### SQL Injection Prevention

All string inputs are scanned for SQL injection patterns:

```python
from mycelium_fractal_net.security import detect_sql_injection

# Detects patterns like:
# - SELECT, INSERT, UPDATE, DELETE, DROP
# - Comment sequences (--), semicolons
# - OR/AND with equality checks
```

### XSS Prevention

HTML special characters are automatically escaped:

```python
from mycelium_fractal_net.security import sanitize_string

# Input: "<script>alert('xss')</script>"
# Output: "&lt;script&gt;alert('xss')&lt;/script&gt;"
```

### Numeric Range Validation

All numeric inputs are validated against acceptable ranges:

```python
from mycelium_fractal_net.security import validate_numeric_range

# Validates grid_size, steps, epochs, etc.
validate_numeric_range(grid_size, min_value=8, max_value=512)
```

---

## 4. Data Encryption

### At-Rest Encryption

Sensitive data can be encrypted using the built-in encryption utilities:

```python
from mycelium_fractal_net.security import encrypt_data, decrypt_data, generate_key

# Generate encryption key
key = generate_key()  # 32-byte secure random key

# Encrypt sensitive data
ciphertext = encrypt_data("sensitive data", key)

# Decrypt when needed
plaintext = decrypt_data(ciphertext, key)
```

### Security Properties

- **Key derivation**: PBKDF2 with 100,000 iterations
- **Random IV**: Each encryption uses a unique 16-byte IV
- **Authentication**: HMAC-SHA256 prevents tampering
- **URL-safe encoding**: Base64 output for easy storage

### Production Encryption

For high-security production use cases requiring regulatory compliance
(PCI-DSS, HIPAA), consider using the `cryptography` library with
Fernet or AES-GCM encryption:

```python
from cryptography.fernet import Fernet

# Generate key and encrypt
key = Fernet.generate_key()
f = Fernet(key)
ciphertext = f.encrypt(b"sensitive data")
plaintext = f.decrypt(ciphertext)
```

### Key Management

Production deployments should:
1. Store encryption keys in a secrets manager (HashiCorp Vault, AWS Secrets Manager)
2. Rotate keys periodically (recommend: every 90 days)
3. Never commit keys to source control

---

## 5. Audit Logging

### Structured Logging

All security-relevant events are logged in JSON format:

```json
{
  "audit_event": true,
  "timestamp": "2025-12-01T10:30:00.000Z",
  "action": "authentication_failure",
  "severity": "WARNING",
  "category": "authentication",
  "user_id": "user***",
  "source_ip": "192.xxx.xxx.xxx",
  "request_id": "abc-123",
  "details": {"reason": "invalid_api_key"}
}
```

### Audit Events

| Event | Category | Severity | Trigger |
|-------|----------|----------|---------|
| `authentication_success` | authentication | INFO | Successful API key validation |
| `authentication_failure` | authentication | WARNING | Invalid or missing API key |
| `access_granted` | authorization | INFO | Access to protected resource |
| `access_denied` | authorization | WARNING | Unauthorized access attempt |
| `rate_limit_exceeded` | security | WARNING | Rate limit exceeded |
| `suspicious_activity` | security | ERROR | Potential attack detected |

### Data Redaction

Sensitive data is automatically redacted in logs:
- **IP addresses**: First octet preserved (e.g., `192.xxx.xxx.xxx`)
- **User IDs**: First 4 characters preserved
- **API keys**: Completely redacted

---

## 6. Request Tracing

### Request ID

Every request includes a unique identifier for tracing:

```
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

### Usage

```bash
# Client provides request ID
curl -H "X-Request-ID: my-trace-123" https://api.example.com/validate

# Response includes same ID
# X-Request-ID: my-trace-123
```

### Log Correlation

Request IDs are included in all log entries for easy correlation:

```json
{"request_id": "my-trace-123", "action": "api_request", ...}
```

---

## 7. CORS Configuration

### Production Settings

```python
# Production: Explicit origin whitelist
MFN_CORS_ORIGINS="https://app.example.com,https://admin.example.com"
```

### Development Settings

```python
# Development: Allow all origins (NOT for production!)
MFN_ENV=dev  # Automatically allows all origins
```

---

## 8. Secrets Management

The secrets manager provides a safe, flexible way to inject credentials without
hard-coding them into configuration files or images.

**Backends**

- `env` (default): reads `MFN_API_KEY`, `MFN_API_KEYS`, and other secrets
  directly from environment variables. For Kubernetes, you can mount
  `mfn-secrets` and point `MFN_API_KEY_FILE` or `MFN_API_KEYS_FILE` to the
  mounted files.
- `file`: read a JSON or `.env` style mapping via `MFN_SECRETS_FILE`.
- `aws`: load from AWS Secrets Manager. Configure `MFN_SECRETS_AWS_NAME` and
  optionally `MFN_SECRETS_AWS_REGION`.
- `vault`: load from HashiCorp Vault KV v2 using `MFN_SECRETS_VAULT_URL`,
  `MFN_SECRETS_VAULT_PATH`, and the token stored in `MFN_VAULT_TOKEN`.

> Secrets files must be UTF-8 encoded text and are capped at 64KB to prevent
> accidental binary uploads or oversized payloads.

**Environment variables**

```bash
export MFN_SECRETS_BACKEND=env           # env|file|aws|vault
export MFN_API_KEY_FILE=/var/run/secrets/api_key
export MFN_API_KEYS_FILE=/var/run/secrets/api_keys
export MFN_SECRETS_FILE=/etc/mfn/secrets.json
```

**Python API**

```python
from mycelium_fractal_net.security import SecretManager

manager = SecretManager()  # auto-configured from environment
api_key = manager.get_secret("MFN_API_KEY", required=True)
api_keys = manager.get_list("MFN_API_KEYS")
```

---

## 9. Compliance

### GDPR Compliance

| Requirement | Implementation |
|-------------|----------------|
| Data minimization | Audit logs redact personal identifiers |
| Right to erasure | No persistent storage of personal data |
| Consent | API key represents consent to process data |
| Security measures | Encryption, access control, audit logging |

### SOC 2 Compliance

| Control | Implementation |
|---------|----------------|
| Access controls | API key authentication, rate limiting |
| Audit trails | Structured JSON audit logs |
| System monitoring | Prometheus metrics, request logging |
| Incident response | Suspicious activity detection |

---

## 10. Security Best Practices

### Deployment Checklist

- [ ] Set `MFN_ENV=prod` for production deployments
- [ ] Configure `MFN_API_KEY` with a strong, random key
- [ ] Enable rate limiting (`MFN_RATE_LIMIT_ENABLED=true`)
- [ ] Configure explicit CORS origins (`MFN_CORS_ORIGINS`)
- [ ] Deploy behind HTTPS-enabled load balancer
- [ ] Store secrets in a secrets manager
- [ ] Enable log aggregation for audit trails
- [ ] Set up alerting for security events

### API Key Generation

```bash
# Generate a secure API key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Environment Variables

```bash
# Production environment
export MFN_ENV=prod
export MFN_API_KEY_REQUIRED=true
export MFN_API_KEY="your-generated-key-here"
export MFN_RATE_LIMIT_ENABLED=true
export MFN_CORS_ORIGINS="https://your-app.example.com"
export MFN_LOG_FORMAT=json
```

---

## 10. Security Testing

### Running Security Tests

```bash
# Run all security tests
pytest tests/security/ -v

# Run specific test categories
pytest tests/security/test_encryption.py -v
pytest tests/security/test_input_validation.py -v
pytest tests/security/test_audit.py -v
pytest tests/security/test_authorization.py -v
```

### Static Analysis

```bash
# Run Bandit security scanner
bandit -r src/ -ll

# Check dependencies for vulnerabilities
pip-audit --strict
```

---

## 11. Incident Response

### Security Event Types

1. **Authentication failures**: Multiple failed API key attempts
2. **Rate limit violations**: Excessive requests from single source
3. **Input validation failures**: Potential injection attempts
4. **Suspicious patterns**: SQL injection, XSS attempts

### Response Procedures

1. **Detection**: Monitor audit logs for security events
2. **Analysis**: Review request details and patterns
3. **Containment**: Block offending IP/API key if needed
4. **Recovery**: Reset credentials if compromised
5. **Review**: Update security controls as needed

---

## 12. Version History

| Version | Date | Changes |
|---------|------|---------|
| 4.1.0 | 2025-12-01 | Added security module with encryption, input validation, audit logging |
| 4.0.0 | 2025-11-29 | Initial API key authentication, rate limiting, metrics |

---

*For questions or security concerns, please contact the security team or open a confidential issue in the repository.*
