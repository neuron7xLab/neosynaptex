# Experimental GPU-backed Memory (FractalPELMGPU)

## Status: EXPERIMENTAL

This module provides an optional GPU/CPU backend for phase-aware retrieval.
It is **not** part of the stable MLSDM API and is intended for research and
benchmarking purposes only.

## Overview

`FractalPELMGPU` is an experimental memory implementation that provides:

- GPU acceleration when CUDA is available (falls back to CPU)
- Batch operations for storing and retrieving vectors
- Phase-aware retrieval with configurable scoring

## Requirements

Requires PyTorch (not installed by default):

```bash
pip install mlsdm[neurolang]
# or directly:
pip install torch>=2.0.0
```

## API

The class is located in `mlsdm.memory.experimental`:

```python
from mlsdm.memory.experimental import FractalPELMGPU

# Create memory (auto-detects device: cuda if available, else cpu)
memory = FractalPELMGPU(
    dimension=384,      # Embedding dimension
    capacity=100_000,   # Maximum vectors to store
    device=None,        # "cuda", "cpu", or None for auto-detect
    use_amp=True,       # Automatic mixed precision (CUDA only)
    fractal_weight=0.3, # Distance weighting parameter [0, 1]
)

# Store vectors (raises RuntimeError if capacity exceeded)
memory.batch_entangle(vectors, phases, metadatas=None)

# Retrieve similar vectors
results = memory.retrieve(query_vector, current_phase, top_k=5)
# Returns: [(score, vector_np, metadata), ...]

# Batch retrieve
results = memory.batch_retrieve(query_vectors, current_phases, top_k=5)

# Reset memory
memory.reset()
```

## Scoring Formula

The retrieval score combines three factors:

```
score = clamp(cos_sim × phase_sim × distance_factor, 0, 1)
```

Where:
- `cos_sim = (q · v) / (‖q‖ × ‖v‖ + ε)` — cosine similarity (can be negative for opposite vectors)
- `phase_sim = exp(-|φ_q - φ_v|)` — phase similarity, peaks at 1.0 when phases match
- `distance_factor = clamp(1 - fractal_weight × log1p(‖q - v‖), 0, 1)` — distance penalty
- `ε = 1e-12` — numerical stability constant
- `fractal_weight` — engineering hyperparameter controlling distance influence

The final score is clamped to [0, 1].

### Scoring Behavior

- **Identical vector and phase**: score ≈ 1.0
- **Larger Euclidean distance**: lower score (monotonically decreasing)
- **Larger phase difference**: lower score (monotonically decreasing)
- **Opposite vectors** (cos_sim ≈ -1): score ≈ 0 due to final clamp

## Differences from Core PELM

| Aspect | PhaseEntangledLatticeMemory | FractalPELMGPU |
|--------|----------------------------|----------------|
| Location | `mlsdm.memory` | `mlsdm.memory.experimental` |
| Dependencies | numpy only | requires torch |
| Device | CPU only | CPU or GPU |
| Capacity | Ring buffer (overwrites) | Strict (raises RuntimeError) |
| Storage | float32 | float16 vectors, float32 phases/norms |
| Status | Production | Experimental |

## Benchmark

A benchmark script is available for manual testing:

```bash
python benchmarks/benchmark_fractal_pelm_gpu.py
```

This runs on CPU by default and compares with GPU if CUDA is available.
The script handles missing CUDA gracefully and outputs CPU-only results.

## Notes

- This module does **not** integrate with the core MLSDM pipeline
- The API may change in future versions without notice
- For production use, prefer `PhaseEntangledLatticeMemory` from `mlsdm.memory`
- Capacity is strictly enforced; exceeding it raises `RuntimeError`
