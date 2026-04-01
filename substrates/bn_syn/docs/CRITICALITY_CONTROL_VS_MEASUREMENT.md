# Criticality: Runtime Proxy vs Offline Measurement

## Runtime control (proxy)
**Goal:** stabilize dynamics around a target regime for homeostatic regulation.

Example proxy:
- σ_proxy(k) = A(k) / (A(k-1) + ε)

**Constraints**
- Label as **proxy** in code + docs.
- Avoid claims of validated criticality from σ_proxy.

## Offline validation (measurement)
**Goal:** evidence-grade criticality assessment.

Minimum protocol:
1) Avalanche detection with explicit binning policy
2) ≥ 1,000 avalanches in scaling region
3) MLE fitting for α, τ
4) x_min selection via KS minimization
5) Monte Carlo GoF (p > 0.1)
6) Likelihood ratio vs alternatives (e.g., log-normal)
7) Subsampling correction using MR estimator

Claims about critical exponents or σ ranges bind to claim identifiers.
