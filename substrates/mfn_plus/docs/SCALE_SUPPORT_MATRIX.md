# Scale Support Matrix

## Grid Size Support

| Grid | Status | Memory (history=60) | Runtime (N=32 ref) | Notes |
|------|--------|--------------------|--------------------|-------|
| 16×16 | Supported | ~1 MB | ~0.1s | Unit tests |
| 32×32 | Supported (default) | ~5 MB | ~0.3s | Golden hashes calibrated |
| 64×64 | Supported | ~20 MB | ~2s | Production benchmark |
| 128×128 | Supported | ~80 MB | ~15s | With numba acceleration |
| 256×256 | Supported | ~300 MB | ~60s | Fused kernels (16.7× speedup) |
| 512×512 | Production-ready | ~1.2 GB | ~5min | Requires memmap backend for history |
| 1024×1024 | Experimental | ~5 GB | ~30min | OOM profiling incomplete |

## Memory Budget

```
memory_bytes ≈ 8 × N² × (T + 5)

  8       = sizeof(float64)
  N²      = grid cells
  T       = history frames
  5       = field + activator + inhibitor + alpha_field + laplacian buffer
```

### Memmap Backend

For N ≥ 256 with long histories (T > 100):
```python
seq = mfn.simulate(spec, history_backend="memmap")
# History stored on disk, memory-mapped for access
# Cleanup: mfn.cleanup_history_memmap(seq.metadata["history_memmap_path"])
```

## Acceleration Options

| Backend | Grid Size | Speedup | Requirements |
|---------|-----------|---------|-------------|
| NumPy (default) | All | 1× | numpy |
| Numba JIT | All | ~2× Laplacian | numba (`pip install mfn[accel]`) |
| Fused kernels | N ≥ 128 | 16.7× at N=256 | numba (`pip install mfn[accel]`) |
| PyTorch float32 | N ≥ 256 | 3.7× at N=256 | torch + CUDA |

## Policy

- **N ≤ 512:** fully supported, benchmarked, golden-hash compatible
- **N = 1024:** opt-in with explicit warning, no golden hashes
- **N > 1024:** not tested, use at own risk
