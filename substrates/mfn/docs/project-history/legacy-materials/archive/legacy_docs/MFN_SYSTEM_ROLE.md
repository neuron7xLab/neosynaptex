# MyceliumFractalNet – System Role & External Contract

**Document Version**: 1.0  
**Target Version**: MyceliumFractalNet v4.1.0  
**Status**: Initial Draft  
**Last Updated**: 2025-11-29

---

## 1. System Context (High-Level)

MyceliumFractalNet (MFN) is a **bio-inspired computational module** designed for fractal field generation, morphogenetic pattern analysis, and feature extraction. The system combines neurophysiology (Nernst-Planck electrochemistry), reaction-diffusion dynamics (Turing morphogenesis), and fractal geometry analysis into a unified computational pipeline.

**System Label**: MFN is a **fractal morphogenetic feature engine** — a computational module that transforms simulation parameters into structured feature vectors suitable for downstream machine learning, analysis, or decision-making systems.

> **Note**: The external higher-level system specification (SYSTEM_SPEC) that would define MFN's precise role in a larger architecture (e.g., neuroeconomic trading system, multi-agent decision platform) has not yet been provided. This document describes MFN's capabilities and boundaries based on the current implementation and documentation. The I/O contracts described here are conceptual and subject to refinement when the system context is formalized.

---

## 2. MFN Responsibility & Boundaries

### 2.1 Responsibilities (In-Scope)

Based on the current implementation (see [TECHNICAL_AUDIT.md](TECHNICAL_AUDIT.md), where `code_core` status is READY):

1. **Membrane Potential Computation** — Calculate equilibrium potentials using the Nernst equation with validated biophysical parameters (R, F, T) and ion concentration clamping.

2. **Reaction-Diffusion Field Simulation** — Generate 2D potential fields with Turing morphogenesis (activator-inhibitor dynamics), discrete Laplacian diffusion, and growth event injection.

3. **Fractal Dimension Analysis** — Estimate box-counting fractal dimension of binary patterns derived from simulated fields (D ∈ [1.4, 1.9] for biological patterns).

4. **IFS Fractal Generation** — Generate fractal point clouds using Iterated Function Systems with Lyapunov exponent tracking for stability assessment.

5. **Feature Extraction Pipeline** — Extract 18 standardized features from field history (D_box, V_stats, temporal features, structural features) via the `analytics` module.

6. **STDP Plasticity Modeling** — Provide Spike-Timing Dependent Plasticity weight updates based on neurophysiology parameters (τ±=20ms, A+=0.01, A-=0.012).

7. **Sparse Attention Mechanism** — Implement top-k sparse attention (default k=4) for efficient attention computation with O(n·k) complexity.

8. **Byzantine-Robust Aggregation** — Provide Hierarchical Krum aggregation for federated learning scenarios with 20% Byzantine tolerance.

9. **Deterministic Reproducibility** — Ensure bit-identical outputs for identical seeds and parameters.

10. **Configuration Management** — Support predefined configurations (small/medium/large) for different computational budgets.

### 2.2 Non-Responsibilities (Out-of-Scope)

MFN explicitly does **not** handle and should **not** be extended to include:

1. **Order/Trade Execution** — MFN does not place, manage, or route orders. Trade execution is the responsibility of external order management systems.

2. **Market Data Acquisition** — MFN does not connect to exchanges, brokers, or data providers. Raw market data must be pre-processed and injected by upstream systems.

3. **Portfolio State Management** — MFN does not track positions, balances, or account states. Portfolio state is managed by external systems.

4. **Risk Engine / Risk Limits** — MFN does not enforce position limits, drawdown controls, or risk thresholds. Risk management is a separate system responsibility.

5. **User Interface / Visualization** — MFN does not provide UI components, dashboards, or interactive visualizations. It is a headless computational module.

6. **Data Persistence / Storage** — MFN does not manage databases, time-series stores, or historical data archives. Parquet export for datasets is the only persistence mechanism.

7. **Orchestration / Workflow Management** — MFN does not coordinate multi-step workflows, job scheduling, or pipeline orchestration.

8. **External Service Integration** — MFN does not integrate with message queues (Kafka, RabbitMQ), cloud services (AWS, GCP), or third-party APIs.

> **Note (v4.1 Update)**: Basic production infrastructure is now available including API key authentication, rate limiting, and Prometheus metrics. See [TECHNICAL_AUDIT.md](TECHNICAL_AUDIT.md) and README.md for details.

---

## 3. Upstream & Downstream Systems

### 3.1 Upstream Systems

Systems that **provide data to** MFN:

| System | Description | Data Provided |
|--------|-------------|---------------|
| **Parameter Configurator** | Provides simulation configuration | Grid size, steps, diffusion coefficients, Turing thresholds, seed values |
| **Data Preprocessor** | (Planned) Transforms raw input data | Normalized input tensors, initial field states (if external initialization is needed) |
| **Orchestration Layer** | (Planned) Triggers simulation runs | Batch job requests, validation requests |
| **Federated Clients** | (For federated learning mode) | Client gradient tensors for aggregation |

> **Current Status**: In v4.1, MFN operates as a standalone module. Parameter injection occurs via CLI arguments, API requests, or direct Python calls. No formal upstream system integration exists.

### 3.2 Downstream Systems

Systems that **consume outputs from** MFN:

| System | Description | How MFN Output Is Used |
|--------|-------------|------------------------|
| **ML Model / Policy Agent** | (Planned) Decision-making component | Consumes 18-feature vectors for regime detection, signal generation, or policy input |
| **Risk Module** | (Planned) Risk assessment system | Uses fractal dimension, stability metrics for regime change detection |
| **Analytics Dashboard** | (Planned) Visualization layer | Displays field statistics, feature distributions, Lyapunov exponents |
| **Dataset Storage** | Parquet file system | Stores generated datasets for offline analysis and model training |
| **Federated Coordinator** | (For federated learning mode) | Receives aggregated gradient from Krum aggregator |

> **Current Status**: In v4.1, downstream consumption is primarily via direct Python return values, API JSON responses, or parquet file export. No formal downstream system integration exists.

---

## 4. External I/O Contract

### 4.1 Input Channels

| Channel | Conceptual Description | Data Type (Concept-Level) | Provider System |
|---------|------------------------|---------------------------|-----------------|
| `simulation_params` | Configuration for field simulation | Dict/Struct: grid_size, steps, alpha, turing_enabled, seed | Parameter Configurator / CLI / API |
| `nernst_params` | Ion electrochemistry parameters | Dict/Struct: z_valence, concentration_out, concentration_in, temperature | Direct call / API |
| `initial_field` | (Optional) Pre-initialized potential field | 2D float array (N×N), values in [-95, 40] mV | Data Preprocessor (not yet implemented) |
| `feature_config` | Feature extraction configuration | FeatureConfig dataclass | Direct call / default |
| `client_gradients` | Gradient tensors from federated clients | List of 1D tensors (d-dimensional) | Federated Clients |
| `random_seed` | Seed for deterministic reproducibility | Integer | Orchestration / CLI / API |

### 4.2 Output Channels

| Channel | Conceptual Description | Data Type (Concept-Level) | Consumer System |
|---------|------------------------|---------------------------|-----------------|
| `potential_field` | Final simulated 2D field | 2D float array (N×N), values in Volts | ML Model / Analytics |
| `growth_events` | Count of growth events during simulation | Integer | Analytics / Logging |
| `feature_vector` | 18 extracted features | FeatureVector dataclass (D_box, V_mean, dV_max, f_active, etc.) | ML Model / Policy Agent |
| `feature_array` | Feature vector as numpy array | 1D float array (18,) | ML pipelines |
| `nernst_potential` | Computed membrane potential | Float (Volts) | Validation / Physics checks |
| `fractal_dimension` | Box-counting dimension | Float ∈ [0, 2] | Regime detection / Analytics |
| `lyapunov_exponent` | Dynamical stability metric | Float (negative = stable) | Stability monitoring |
| `aggregated_gradient` | Byzantine-robust aggregated gradient | 1D tensor | Federated Coordinator |
| `validation_metrics` | Full validation cycle results | Dict: loss_start, loss_final, pot_min, pot_max, etc. | Quality assurance / CI |

---

## 5. Alignment with Current Implementation

### 5.1 Overall Status

Per [TECHNICAL_AUDIT.md](TECHNICAL_AUDIT.md):

- **overall_type**: `partial_implementation`
- **Maturity Level**: 3.5 / 5 (Partial Production Ready Component)

### 5.2 Role Coverage Map

| Desired Capability | Implementation Status | Evidence |
|--------------------|----------------------|----------|
| Nernst equation solver | ✅ READY | `src/mycelium_fractal_net/core/membrane_engine.py` |
| Turing morphogenesis | ✅ READY | `src/mycelium_fractal_net/core/reaction_diffusion_engine.py` |
| Box-counting dimension | ✅ READY | `src/mycelium_fractal_net/core/fractal_growth_engine.py` |
| IFS fractal generation | ✅ READY | `src/mycelium_fractal_net/model.py:362-432` |
| STDP plasticity | ✅ READY | `src/mycelium_fractal_net/model.py:435-576` |
| Sparse attention | ✅ READY | `src/mycelium_fractal_net/model.py:578-694` |
| Hierarchical Krum | ✅ READY | `src/mycelium_fractal_net/model.py:697-904` |
| 18-feature extraction | ✅ READY | `analytics/fractal_features.py` |
| REST API | ✅ READY | `api.py` (with auth, rate limiting, metrics) |
| API Authentication | ✅ READY | `integration/auth.py` (X-API-Key middleware) |
| Rate Limiting | ✅ READY | `integration/rate_limiter.py` |
| Prometheus Metrics | ✅ READY | `integration/metrics.py` (/metrics endpoint) |
| Structured Logging | ✅ READY | `integration/logging_config.py` (JSON format, request IDs) |
| External system integration | 🔴 PLANNED | Not yet implemented |
| Upstream data connectors | 🔴 PLANNED | Not yet implemented |
| Downstream event publishing | 🔴 PLANNED | Not yet implemented |

### 5.3 Gap Summary

The core computational capabilities (fractal field generation, feature extraction, federated aggregation) are production-ready. Basic production infrastructure (authentication, rate limiting, metrics, logging) is implemented. The remaining gaps exist primarily in:

1. **Integration layer** — No formal contracts with upstream/downstream systems
2. **External I/O** — No streaming, message queue, or gRPC interfaces
3. **Secrets Management** — No integration with secrets vault (HashiCorp Vault, AWS Secrets Manager)

---

## 6. Open Questions & TODOs

The following items require clarification before finalizing the system role:

### 6.1 System Context Questions

1. What is the precise role of MFN in the larger system architecture? (Awaiting SYSTEM_SPEC)

2. Is MFN a synchronous computation module or should it support asynchronous/streaming operation?

3. What is the expected call frequency and latency budget for MFN computations?

### 6.2 Input/Output Questions

4. What is the exact format of market data input (if MFN will receive external data)?

5. Should MFN accept pre-initialized fields from external systems, or always generate from parameters?

6. Which output channels should be event-driven (push) vs request-driven (pull)?

7. Should feature vectors be published to a message queue or only returned synchronously?

### 6.3 Boundary Questions

8. Should risk-related signals (e.g., regime change indicators) be a separate MFN output channel or computed by a downstream module using MFN features?

9. Who is responsible for feature normalization — MFN or the consuming ML model?

10. Should MFN support incremental/streaming field updates, or only batch simulation?

### 6.4 Integration Questions

11. What authentication mechanism should the API use (API keys, OAuth, mTLS)?

12. What observability stack should MFN integrate with (Prometheus, OpenTelemetry, other)?

13. Should MFN publish its outputs via gRPC, Kafka, or REST webhooks?

### 6.5 Operational Questions

14. What is the SLA for MFN computation (availability, latency percentiles)?

15. How should MFN handle computation failures — retry, fallback, or propagate error?

---

## 7. References

| Document | Path | Description |
|----------|------|-------------|
| Technical Audit | [TECHNICAL_AUDIT.md](TECHNICAL_AUDIT.md) | Current implementation status (source of truth) |
| Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture and module interactions |
| Math Model | [MFN_MATH_MODEL.md](MFN_MATH_MODEL.md) | Mathematical formalization (PDEs, Nernst) |
| Integration Spec | [MFN_INTEGRATION_SPEC.md](MFN_INTEGRATION_SPEC.md) | Repository layout and API specification |
| Roadmap | [ROADMAP.md](ROADMAP.md) | Development roadmap (v4.1 → v4.2+) |

---

*Document maintained by: System Architecture Team*  
*Awaiting: SYSTEM_SPEC for external context refinement*  
*Last updated: 2025-11-29*
