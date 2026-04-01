# Critical Subsystem Contracts (Executable Documentation)

**Scope:** Security middleware, configuration system, state & memory lifecycle, observability, provider/adapters.
**Guarantee:** Every default/contract listed here is tied to a symbol in code and enforced by tests or scripts.

---

## Security Middleware (OIDC / RBAC / Signing / mTLS)

### Objective
Provide default-safe request gating with explicit opt-in overrides while preserving public documentation endpoints.

### Contracts (inputs/outputs)
| Contract | Definition (code) | Enforcement |
| --- | --- | --- |
| Public paths skipped by security checks. | `mlsdm.security.path_utils.DEFAULT_PUBLIC_PATHS` | `scripts/verify_security_skip_invariants.py` |
| Middleware `skip_paths` defaults to public paths when not provided. | `mlsdm.security.oidc.OIDCAuthMiddleware`, `mlsdm.security.mtls.MTLSMiddleware`, `mlsdm.security.signing.SigningMiddleware`, `mlsdm.security.rbac.RBACMiddleware` | `scripts/verify_security_skip_invariants.py` |

```json
{"doc_contract":"security.default_public_paths","source":"mlsdm.security.path_utils.DEFAULT_PUBLIC_PATHS","value":["/health","/docs","/redoc","/openapi.json"]}
```

### Invariants
- Skip-path matching is boundary-safe (e.g., `/docs` does not match `/docs2`). Defined in `mlsdm.security.path_utils.is_path_match`. Enforced by `scripts/verify_security_skip_invariants.py`.

### Failure modes
- If security middleware is enabled and a path is not skipped, requests may be rejected (status codes depend on middleware implementation). Defined in middleware classes above. **Exact HTTP status per middleware is implementation-defined and not documented here.**

### Override knobs
- `skip_paths`: list of paths to exempt. Must include all default public paths to avoid regressions.

### Operator-safe override example
```python
# Safe: preserves default public documentation and health endpoints
skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/status"]
```

### Verification
- `make verify-security-skip`
- `python scripts/verify_docs_contracts.py`

---

## Configuration System

### Objective
Provide deterministic runtime configuration with explicit environment overrides and validated engine config files.

### Contracts (inputs/outputs)
| Contract | Definition (code) | Enforcement |
| --- | --- | --- |
| Runtime mode defaults to `dev` if unset/invalid. | `mlsdm.config.runtime.get_runtime_mode` | `tests/contracts/test_docs_contracts.py::test_runtime_default_mode` |
| Mode defaults (subset) for `dev`, `local-prod`, `cloud-prod`, `agent-api` are stable. | `mlsdm.config.runtime._get_mode_defaults` | `tests/contracts/test_docs_contracts.py::test_runtime_mode_defaults_subset` |
| `DISABLE_RATE_LIMIT` inverts `rate_limit_enabled` when set. | `mlsdm.config.runtime.get_runtime_config` | `tests/contracts/test_docs_contracts.py::test_disable_rate_limit_inversion` |
| Engine config path default is `config/default_config.yaml`. | `mlsdm.config.runtime.EngineConfig.config_path` | `tests/contracts/test_docs_contracts.py::test_runtime_config_path_default` |
| Unknown top-level keys in engine config are rejected. | `mlsdm.utils.config_schema.SystemConfig` (`extra="forbid"`) | `tests/unit/test_config_validation.py::TestSystemConfig::test_unknown_fields_rejected` |

```json
{"doc_contract":"runtime.default_mode","source":"mlsdm.config.runtime.get_runtime_mode","value":"dev"}
```

```json
{"doc_contract":"runtime.mode_defaults_subset","source":"mlsdm.config.runtime._get_mode_defaults","value":{"dev":{"server":{"workers":1,"log_level":"debug"},"security":{"rate_limit_enabled":false,"secure_mode":false},"observability":{"json_logging":false,"tracing_enabled":false},"engine":{"config_path":"config/default_config.yaml"}},"local-prod":{"server":{"workers":2,"log_level":"info"},"security":{"rate_limit_enabled":true,"secure_mode":true},"observability":{"json_logging":true,"tracing_enabled":false},"engine":{"config_path":"config/production.yaml"}},"cloud-prod":{"server":{"workers":4,"log_level":"info"},"security":{"rate_limit_enabled":true,"secure_mode":true},"observability":{"json_logging":true,"tracing_enabled":true},"engine":{"config_path":"config/production.yaml"}},"agent-api":{"server":{"workers":2,"log_level":"info"},"security":{"rate_limit_enabled":true,"secure_mode":true},"observability":{"json_logging":true,"tracing_enabled":false},"engine":{"config_path":"config/production.yaml"}}}}
```

### Invariants
- Configuration schema validation is strict; unknown top-level keys are rejected. Defined in `mlsdm.utils.config_schema.SystemConfig` (`extra="forbid"`).
- Config files must be YAML/INI; other extensions are rejected. Defined in `mlsdm.utils.config_loader.ConfigLoader.load_config`.

### Failure modes
- Invalid config files raise `ValueError` with validation details. Defined in `mlsdm.utils.config_loader.ConfigLoader.load_config`.
- Missing config files raise `FileNotFoundError`, except when `CONFIG_PATH` is `config/default_config.yaml` and the packaged default resource is used. Defined in `mlsdm.utils.config_loader.ConfigLoader.load_config`.

### Override knobs
- Runtime: `MLSDM_RUNTIME_MODE`, `HOST`, `PORT`, `MLSDM_WORKERS`, `MLSDM_RELOAD`, `MLSDM_LOG_LEVEL`, `MLSDM_TIMEOUT_KEEP_ALIVE`, `DISABLE_RATE_LIMIT`, `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`, `MLSDM_SECURE_MODE`, `LOG_LEVEL`, `JSON_LOGGING`, `ENABLE_METRICS`, `OTEL_TRACING_ENABLED`, `OTEL_SDK_DISABLED`, `OTEL_EXPORTER_TYPE`, `OTEL_SERVICE_NAME`, `LLM_BACKEND`, `EMBEDDING_DIM`, `ENABLE_FSLGS`, `MLSDM_ENGINE_ENABLE_METRICS`, `CONFIG_PATH`, `MLSDM_DEBUG`.
- Engine config file: YAML/INI contents validated against `mlsdm.utils.config_schema.SystemConfig`.

### Verification
- `python scripts/verify_docs_contracts.py`
- `pytest tests/contracts/test_docs_contracts.py -q`

---

## State & Memory Lifecycle

### Objective
Ensure persisted system state is validated against a strict schema with explicit invariants.

### Contracts (inputs/outputs)
| Contract | Definition (code) | Enforcement |
| --- | --- | --- |
| Schema version is `1`. | `mlsdm.state.system_state_schema.CURRENT_SCHEMA_VERSION` | `tests/state/test_system_state_integrity.py` |
| Memory state vectors must match declared dimension. | `mlsdm.state.system_state_schema.MemoryStateRecord.validate_state_dimensions` | `tests/state/test_system_state_integrity.py` |
| `created_at <= updated_at` for records. | `mlsdm.state.system_state_schema.SystemStateRecord.validate_timestamps` | `tests/state/test_system_state_integrity.py` |

### Invariants
- All `lambda_*` decay rates are `(0, 1]` and thresholds `theta_*` are `> 0`. Defined in `mlsdm.state.system_state_schema.MemoryStateRecord` field constraints.

### Failure modes
- Invalid schema inputs raise `ValueError` during validation. Defined in `mlsdm.state.system_state_schema` validators.

### Override knobs
- None. State schema is enforced; any overrides must occur by changing validated fields in the persisted state payload.

### Verification
- `pytest tests/state/test_system_state_integrity.py -q`

---

## Observability

### Objective
Provide structured logging with optional OpenTelemetry trace context, without requiring OTEL dependencies.

### Contracts (inputs/outputs)
| Contract | Definition (code) | Enforcement |
| --- | --- | --- |
| OTEL integration is optional; trace context fields are empty when OTEL is unavailable. | `mlsdm.observability.logger.OTEL_AVAILABLE`, `mlsdm.observability.logger.get_current_trace_context` | `tests/observability/test_tracing_no_otel.py` |
| Trace context filter injects `trace_id`/`span_id` into log records when enabled. | `mlsdm.observability.logger.TraceContextFilter` | `tests/observability/test_trace_context_logging.py` |

### Invariants
- When OTEL is unavailable, `get_current_trace_context` returns empty IDs. Defined in `mlsdm.observability.logger.get_current_trace_context`.

### Failure modes
- If OTEL is enabled but not installed, tracing configuration remains disabled; behavior is `no-op` rather than failing at import. Defined in `mlsdm.observability.logger` and `mlsdm.observability.tracing` import guards.

### Override knobs
- `LOG_LEVEL`, `JSON_LOGGING`, `ENABLE_METRICS`, `OTEL_TRACING_ENABLED`, `OTEL_SDK_DISABLED`, `OTEL_EXPORTER_TYPE`, `OTEL_SERVICE_NAME` (runtime config).

### Verification
- `pytest tests/observability/test_tracing_no_otel.py -q`
- `pytest tests/observability/test_trace_context_logging.py -q`

---

## Provider/Adapters

### Objective
Select LLM providers deterministically from environment variables, with safe local defaults.

### Contracts (inputs/outputs)
| Contract | Definition (code) | Enforcement |
| --- | --- | --- |
| `LLM_BACKEND` defaults to `local_stub` when unset. | `mlsdm.adapters.provider_factory.build_provider_from_env` | `tests/contracts/test_docs_contracts.py::test_llm_backend_default` |
| `MULTI_LLM_BACKENDS` empty defaults to a local stub provider map. | `mlsdm.adapters.provider_factory.build_multiple_providers_from_env` | `tests/unit/test_provider_factory.py::test_build_multiple_providers_empty` |
| Invalid backend names raise `ValueError`. | `mlsdm.adapters.provider_factory.build_provider_from_env` | `tests/unit/test_provider_factory.py::test_build_provider_invalid_backend` |

### Invariants
- `LLM_BACKEND` is normalized to lower case and trimmed. Defined in `mlsdm.adapters.provider_factory.build_provider_from_env`.

### Failure modes
- Missing API keys for `openai`/`anthropic` providers raise `ValueError`. Defined in `mlsdm.adapters.provider_factory.build_provider_from_env` and provider constructors.

### Override knobs
- `LLM_BACKEND`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `LOCAL_STUB_PROVIDER_ID`, `MULTI_LLM_BACKENDS`.

### Verification
- `pytest tests/contracts/test_docs_contracts.py -q`
- `pytest tests/unit/test_provider_factory.py -q`

---

## Contract Evidence Ledger

See `docs/CLAIM_EVIDENCE_LEDGER.md` for the full claim inventory and evidence map.
