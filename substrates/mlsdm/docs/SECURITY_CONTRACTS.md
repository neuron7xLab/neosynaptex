# Security Contracts

## Objective
Document the default public endpoints, skip-path matching semantics, and fail-closed behavior for security middleware.

## Contracts
| Contract | Code owner (source of truth) | Enforcement |
| --- | --- | --- |
| Default public paths are `/health`, `/docs`, `/redoc`, `/openapi.json`. | `mlsdm.security.path_utils.DEFAULT_PUBLIC_PATHS` | `scripts/verify_docs_claims_against_code.py`, `scripts/verify_security_skip_invariants.py` |
| Security middleware defaults `skip_paths` to `DEFAULT_PUBLIC_PATHS`. | `mlsdm.security.oidc.OIDCAuthMiddleware`, `mlsdm.security.mtls.MTLSMiddleware`, `mlsdm.security.signing.SigningMiddleware`, `mlsdm.security.rbac.RBACMiddleware` | `scripts/verify_security_skip_invariants.py`, `tests/unit/security/test_path_utils.py::TestMiddlewareDefaultParity` |
| Non-skipped paths fail closed when auth/validation errors occur. | `mlsdm.security.oidc.OIDCAuthMiddleware`, `mlsdm.security.mtls.MTLSMiddleware`, `mlsdm.security.signing.SigningMiddleware`, `mlsdm.security.rbac.RBACMiddleware` | `tests/unit/security/test_security_skip_invariants.py` |

```json
{"doc_claim":"security.default_public_paths","source":"mlsdm.security.path_utils.DEFAULT_PUBLIC_PATHS","value":["/health","/docs","/redoc","/openapi.json"]}
```

## Invariants
- Skip-path matching is boundary-safe (exact match or `/path/` prefix). Defined in `mlsdm.security.path_utils.is_path_match`. Enforced by `tests/unit/security/test_path_utils.py::TestPathSkipMatching`.

## Failure modes
- When authentication or validation errors occur on non-skipped paths, the middleware raises an HTTP error or returns an error response (fail closed). Defined in middleware `dispatch` methods listed above. Enforced by `tests/unit/security/test_security_skip_invariants.py`.

## Overrides
- `skip_paths` (all security middleware): list of paths exempt from checks. Defaults to `DEFAULT_PUBLIC_PATHS`.
- `require_auth_paths` (OIDC only): list of paths that require authentication when OIDC is enabled.

### Operator-safe overrides
**Safe default-preserving example**
```python
skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/status"]
```

**Intentional hardening (protect `/docs` and `/redoc`)**
```python
# Start from canonical defaults and explicitly remove documentation endpoints.
skip_paths = ["/health", "/docs", "/redoc", "/openapi.json"]
filtered_skip_paths = [path for path in skip_paths if path not in {"/docs", "/redoc"}]
```

## Verification
- `make verify-docs`
- `make verify-security-skip`
- `pytest tests/unit/security/test_security_skip_invariants.py -q`
