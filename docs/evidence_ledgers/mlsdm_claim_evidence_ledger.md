# Claim Inventory and Evidence Ledger

**Scope:** Critical operator-facing claims that include defaults, behavior, or contracts.
**Method:** Each claim is tied to a defining symbol (code) and an enforcement point (test or script). If enforcement is missing, it is called out explicitly.

## Ledger

| ID | Claim | Defined In (source of truth) | Enforced By | Status |
| --- | --- | --- | --- | --- |
| SEC-001 | Default public paths are `/health`, `/docs`, `/redoc`, `/openapi.json`. | `mlsdm.security.path_utils.DEFAULT_PUBLIC_PATHS` | `scripts/verify_security_skip_invariants.py` | ✅ Backed |
| SEC-002 | Security middlewares (OIDC, mTLS, signing, RBAC) default `skip_paths` to `DEFAULT_PUBLIC_PATHS`. | `mlsdm.security.oidc.OIDCAuthMiddleware`, `mlsdm.security.mtls.MTLSMiddleware`, `mlsdm.security.signing.SigningMiddleware`, `mlsdm.security.rbac.RBACMiddleware` | `scripts/verify_security_skip_invariants.py` | ✅ Backed |
| SEC-003 | Skip-path matching is boundary-safe (exact match or `/path/` prefix). | `mlsdm.security.path_utils.is_path_match` | `tests/unit/security/test_path_utils.py::TestPathSkipMatching` | ✅ Backed |
| SEC-004 | Security middleware fail closed on non-skipped paths when auth/validation errors occur. | `mlsdm.security.oidc.OIDCAuthMiddleware`, `mlsdm.security.mtls.MTLSMiddleware`, `mlsdm.security.signing.SigningMiddleware`, `mlsdm.security.rbac.RBACMiddleware` | `tests/unit/security/test_security_skip_invariants.py` | ✅ Backed |
| CFG-001 | Runtime mode defaults to `dev` when `MLSDM_RUNTIME_MODE` is absent/invalid. | `mlsdm.config.runtime.get_runtime_mode` | `tests/contracts/test_docs_contracts.py::test_runtime_default_mode` | ✅ Backed |
| CFG-002 | Runtime mode defaults (subset) for `dev`, `local-prod`, `cloud-prod`, `agent-api` are stable and documented. | `mlsdm.config.runtime._get_mode_defaults` | `tests/contracts/test_docs_contracts.py::test_runtime_mode_defaults_subset` | ✅ Backed |
| CFG-003 | `DISABLE_RATE_LIMIT` inverts `rate_limit_enabled` when set. | `mlsdm.config.runtime.get_runtime_config` | `tests/contracts/test_docs_contracts.py::test_disable_rate_limit_inversion` | ✅ Backed |
| CFG-004 | `CONFIG_PATH` defaults to `config/default_config.yaml` for runtime engine config. | `mlsdm.config.runtime.EngineConfig.config_path` | `tests/contracts/test_docs_contracts.py::test_runtime_config_path_default` | ✅ Backed |
| CFG-005 | Unknown top-level keys in engine config are rejected. | `mlsdm.utils.config_schema.SystemConfig` (`extra="forbid"`) | `tests/unit/test_config_validation.py::TestSystemConfig::test_unknown_fields_rejected` | ✅ Backed |
| CFG-006 | ConfigLoader only accepts YAML/INI; other extensions raise `ValueError`. | `mlsdm.utils.config_loader.ConfigLoader.load_config` | `tests/unit/test_config_loader.py::TestYAMLLoading::test_unsupported_format` | ✅ Backed |
| CFG-007 | `config/default_config.yaml` loads from packaged resource when file is missing. | `mlsdm.utils.config_loader.ConfigLoader.load_config` | `tests/packaging/test_config_fallback.py::test_default_config_resource_fallback` | ✅ Backed |
| STATE-001 | System state schema version is `1`. | `mlsdm.state.system_state_schema.CURRENT_SCHEMA_VERSION` | `tests/state/test_system_state_integrity.py::TestSystemStateRecord` | ✅ Backed |
| STATE-002 | Memory state vectors must match declared dimension and enforce gating/threshold bounds. | `mlsdm.state.system_state_schema.MemoryStateRecord` validators | `tests/state/test_system_state_integrity.py::TestMemoryStateRecord` | ✅ Backed |
| OBS-001 | OpenTelemetry integration is optional; trace context fields are empty when OTEL is unavailable. | `mlsdm.observability.logger.OTEL_AVAILABLE`, `mlsdm.observability.logger.get_current_trace_context` | `tests/observability/test_tracing_no_otel.py` | ✅ Backed |
| ADAPT-001 | `LLM_BACKEND` defaults to `local_stub` when unset. | `mlsdm.adapters.provider_factory.build_provider_from_env` | `tests/contracts/test_docs_contracts.py::test_llm_backend_default` | ✅ Backed |
| ADAPT-002 | Empty `MULTI_LLM_BACKENDS` yields a default local stub provider. | `mlsdm.adapters.provider_factory.build_multiple_providers_from_env` | `tests/unit/test_provider_factory.py::test_build_multiple_providers_empty` | ✅ Backed |

## Gaps

None identified for the claims documented in `docs/CONTRACTS_CRITICAL_SUBSYSTEMS.md`.
