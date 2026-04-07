# H_φγ Protocol — Phi-Gamma Invariant

## Hypothesis

When the spectral scaling exponent γ(t) → 1.0 (unity regime), the
attention ratio R(t) = E_core(t) / E_periphery(t) converges to
φ ≈ 1.618 or φ⁻¹ ≈ 0.618 across independent neosynaptex substrates.

## Definitions

| Symbol | Value | Meaning |
|--------|-------|---------|
| φ | 1.6180339887498949 | Golden ratio |
| φ⁻¹ | 0.6180339887498949 | Reciprocal golden ratio |
| ε | 0.10 | Unity window tolerance |
| γ(t) | PSD slope | Spectral scaling exponent per window |
| R(t) | E_core / E_periphery | Energy ratio |
| δ | 1e-12 | Denominator guard |

## Three Ratio Methods

- **R1 (topology-energy):** Core/periphery by weighted-degree centrality.
  Top 38.2% of nodes by centrality form the core.
- **R2 (spectral-core):** Core = dominant PSD modes covering top 38.2%
  of spectral energy. Periphery = residual modes.
- **R3 (predictive-allocation):** Core = features with top 38.2% of
  next-step AR(1) prediction weight. Periphery = rest.

## Null Models

1. **Temporal shuffle** — destroys temporal order, preserves amplitude.
2. **Topology shuffle** — random core/periphery assignment, preserves sizes.
3. **Phase randomization** — preserves power spectrum, destroys phases.

## Verdict Logic

| Verdict | Conditions |
|---------|------------|
| **support** | n_unity ≥ 30, CI width < 0.5, median closer to φ/φ⁻¹ than null, p < 0.05 |
| **reject** | n_unity ≥ 30, median NOT near φ/φ⁻¹, null NOT rejected |
| **insufficient** | n_unity < 30, or CI too wide |

## Execution

```bash
python -m analysis.phi_gamma_invariant \
  --config experiments/phi_gamma_config.yaml \
  --out evidence/phi_gamma/phi_gamma_report.json
```

## Tests

```bash
pytest tests/test_phi_gamma_invariant.py -v
```
