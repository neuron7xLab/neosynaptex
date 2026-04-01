# Configuration Contracts

## Objective
Define the runtime configuration schema, validation behavior, and failure modes for MLSDM configuration inputs.

## Contracts
| Contract | Code owner (source of truth) | Enforcement |
| --- | --- | --- |
| Runtime configuration defaults and environment overrides are defined in `get_runtime_config`. | `mlsdm.config.runtime.get_runtime_config` | `tests/contracts/test_docs_contracts.py` |
| Runtime mode defaults originate from `_get_mode_defaults` and fall back to `dev` when `MLSDM_RUNTIME_MODE` is unset/invalid. | `mlsdm.config.runtime._get_mode_defaults`, `mlsdm.config.runtime.get_runtime_mode` | `tests/contracts/test_docs_contracts.py` |
| Engine/system configuration schema is the `SystemConfig` Pydantic model and rejects unknown top-level keys. | `mlsdm.utils.config_schema.SystemConfig` (`extra="forbid"`) | `tests/unit/test_config_validation.py::TestSystemConfig::test_unknown_fields_rejected` |
| ConfigLoader accepts YAML/INI only and validates against `SystemConfig` when `validate=True`. | `mlsdm.utils.config_loader.ConfigLoader.load_config` | `tests/unit/test_config_loader.py::TestYAMLLoading::test_unsupported_format` |
| `config/default_config.yaml` loads from packaged resources when the file is missing on disk. | `mlsdm.utils.config_loader.ConfigLoader.load_config` | `tests/packaging/test_config_fallback.py::test_default_config_resource_fallback` |

## Schema location
- Runtime schema: `src/mlsdm/config/runtime.py` (`RuntimeConfig`, `ServerConfig`, `SecurityConfig`, `ObservabilityConfig`, `EngineConfig`).
- Engine/system schema: `src/mlsdm/utils/config_schema.py` (`SystemConfig` and sub-models).

## Invariants
- Unknown top-level config keys are rejected (`extra="forbid"`). Defined in `mlsdm.utils.config_schema.SystemConfig`.
- Validation errors surface as `ValueError` with schema context when using `ConfigLoader.load_config(..., validate=True)`.

## Failure modes
- Unsupported file extensions raise `ValueError` (only `.yaml`, `.yml`, `.ini` accepted).
- Missing config files raise `FileNotFoundError`, except when `CONFIG_PATH` is `config/default_config.yaml` and the packaged resource is available.
- Invalid schema inputs raise `ValueError` with validation details.

## Overrides
- Runtime overrides use environment variables listed in `mlsdm.config.runtime.get_runtime_config` (e.g., `MLSDM_RUNTIME_MODE`, `HOST`, `PORT`, `DISABLE_RATE_LIMIT`, `CONFIG_PATH`).
- Engine/system overrides use `mlsdm.utils.config_loader.ConfigLoader` with `MLSDM_`-prefixed environment variables and `__` for nested keys.

## Verification
- `pytest tests/contracts/test_docs_contracts.py -q`
- `pytest tests/unit/test_config_validation.py -q`
- `pytest tests/unit/test_config_loader.py -q`
- `pytest tests/packaging/test_config_fallback.py -q`
