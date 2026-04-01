# Non-Goals

MyceliumFractalNet v4.1.0 is scoped as a **deterministic morphology-aware field analytics engine**. The following are explicitly outside the project scope:

| Non-goal | Rationale |
|----------|-----------|
| General-purpose neural architecture | MFN is a domain-specific simulation and analysis tool, not a deep learning framework. |
| Distributed cloud platform | The engine is designed for single-node deterministic computation. |
| Federated production system | `core/federated.py` is frozen. Federation was explored and descoped. |
| WebSocket-first streaming | WebSocket adapters are frozen. REST API is the stable transport. |
| Cryptography product | `crypto/` is deprecated. Signing is limited to artifact attestation via Ed25519. |
| Real-time signal processing | Batch-mode pipeline with offline analysis. Not designed for streaming data. |
| GPU-first computation | CPU determinism is the priority. GPU acceleration is a future optional extension. |

The v1 contract covers: **SDK, CLI, REST API, report pipeline, scenario presets, scientific validation, and benchmarks.**
