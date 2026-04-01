# Test Data Fixtures

This directory contains minimal synthetic test data for MyceliumFractalNet validation.

## Fixtures Overview

| File | Size | Purpose |
|------|------|---------|
| `edge_cases.json` | ~2KB | Extreme/boundary parameter values for testing |
| `sample_features.json` | ~3KB | Example feature vectors from different scenarios |

## Usage

```python
import json
from pathlib import Path

# Load edge cases
fixtures_dir = Path(__file__).parent
with open(fixtures_dir / "edge_cases.json") as f:
    edge_cases = json.load(f)

# Access specific scenarios
nernst_edge = edge_cases["nernst"]["extreme_concentration"]
turing_edge = edge_cases["turing"]["boundary_diffusion"]
```

## Edge Case Categories

### Nernst Potentials
- Extreme concentration ratios (very high/low)
- Temperature boundaries (273K - 320K)
- Different ion valences (+1, +2, -1, -2)

### Turing Morphogenesis
- Boundary diffusion coefficients
- Threshold boundary values
- Long simulation edge cases

### Fractal Analysis
- Small grid sizes (4x4)
- Large iteration counts
- Sparse vs dense fields

### STDP Plasticity
- Boundary time constants (5ms, 100ms)
- Extreme timing differences
- Simultaneous spike timing

## Validation Against Literature

All expected values are derived from:
- Hille B (2001) "Ion Channels of Excitable Membranes"
- Bi & Poo (1998) J. Neuroscience
- Fricker et al. (2017) Fungal Biology Reviews

---

*Last Updated: 2025-11-30*
