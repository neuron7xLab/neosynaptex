# Deprecation Policy

## Standard

When a public symbol, module, or behavior is deprecated:

1. **Warning** — `DeprecationWarning` emitted on first use with migration instructions.
2. **Documentation** — Entry added to [PUBLIC_API_CONTRACT.md](PUBLIC_API_CONTRACT.md) deprecated table.
3. **Timeline** — Minimum one minor version before removal (typically until next major).
4. **Migration guide** — Alternative documented in warning message and changelog.

## Current Deprecations

| Symbol / Module | Deprecated in | Removal in | Alternative |
|----------------|---------------|------------|-------------|
| `crypto/` | v4.1.0 | v5.0.0 | `artifact_bundle.py` for Ed25519 signing |
| `core/federated.py` | v4.0.0 | v5.0.0 | External federated learning frameworks |
| `core/stdp.py` | v4.0.0 | v5.0.0 | Standalone STDP implementations |
| `integration/ws_*` | v4.0.0 | v5.0.0 | Standard WebSocket libraries |
| Root `api.py` shim | v4.1.0 | **Removed** | `from mycelium_fractal_net.api import app` |
| Root `analytics/` shim | v4.1.0 | **Removed** | `from mycelium_fractal_net.analytics.legacy_features import ...` |
| Root `experiments/` shim | v4.1.0 | **Removed** | `from mycelium_fractal_net.experiments.generate_dataset import ...` |

## Classification

| Change type | Deprecation required | Notice period |
|------------|---------------------|---------------|
| Remove public function | Yes | 1 minor version |
| Remove public type | Yes | 1 minor version |
| Rename public symbol | Yes (alias + warning) | 1 minor version |
| Change default parameter | No (if backward-compatible) | N/A |
| Remove internal symbol | No | N/A |
| Change frozen module | No (frozen = no guarantees) | N/A |
