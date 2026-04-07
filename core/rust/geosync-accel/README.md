# GEOSYNC-ACCEL

**High-Performance Rust Accelerator for Neosynaptex Gamma-Scaling (2026 Standard)**

## Architecture

```
Python (numpy/scipy)
    ↕  zero-copy via DLPack / Arrow C-Data Interface
geosync_accel (PyO3 extension)
    ↕  SIMD-dispatched kernels + Rayon parallel bootstrap
Rust core (AVX-512 / AVX2+FMA / NEON / scalar fallback)
```

## Components

| Module | Purpose |
|--------|---------|
| `gamma_kernel.rs` | SIMD-accelerated Theil-Sen regression + parallel bootstrap |
| `hilbert.rs` | Hilbert curve spatial indexing for cache-optimal memory layout |
| `dlpack.rs` | DLPack v1.0 zero-copy tensor exchange via PyCapsule |
| `arrow_ffi.rs` | Arrow C-Data Interface for columnar data exchange |
| `prefetch.rs` | Cache-line aligned structures + explicit software prefetching |
| `io_uring_bridge.rs` | io_uring kernel-bypass I/O abstraction |
| `lib.rs` | PyO3 module entry point with GIL-released computation |

## Performance Engineering

### 1. ABI Evolution: DLPack + Arrow C-Data (Zero-Copy)
- No `numpy` dependency in Rust — data exchanged via `PyCapsule`
- DLPack protocol for PyTorch/JAX/CuPy interop
- Arrow C-Data for Polars/DuckDB/GeoParquet interop
- Hardware-agnostic: CPU, GPU, NPU, Unified Memory

### 2. SIMD Dispatch (Function Multi-Versioning)
- Runtime CPU detection: `is_x86_feature_detected!`
- AVX-512F, AVX2+FMA, SSE4.2, NEON auto-selection
- No `target-cpu=native` — safe for PyPI wheel distribution
- Explicit intrinsics for hot paths (`_mm512_*`, `_mm256_*`)

### 3. PGO + BOLT + Cross-Language LTO
```bash
# Stage 1: Instrument
RUSTFLAGS="-Cprofile-generate=/tmp/pgo-data" cargo build --profile pgo-instrument

# Run benchmarks to generate profile
cargo bench --profile pgo-instrument

# Stage 2: Merge and optimize
llvm-profdata merge -o /tmp/pgo-data/merged.profdata /tmp/pgo-data/

RUSTFLAGS="-Cprofile-use=/tmp/pgo-data/merged.profdata" cargo build --profile pgo-optimize

# Stage 3: BOLT post-link optimization
llvm-bolt target/pgo-optimize/libgeosync_accel.so \
    -o target/pgo-optimize/libgeosync_accel.bolt.so \
    -data=perf.fdata \
    -reorder-blocks=ext-tsp \
    -reorder-functions=hfsort+
```

### 4. Cache-Oblivious Data Structures
- `CacheLineNode`: 64-byte aligned struct (one L1 cache line)
- Hilbert curve reordering for spatial locality
- Explicit `_mm_prefetch` before geo-index traversal
- `snmalloc`-compatible allocation patterns

### 5. Lock-Free I/O (io_uring)
- Ring buffer abstraction for kernel-bypass file I/O
- DMA-aligned buffer pool (4 KiB pages)
- Thread-per-core reactor pattern
- Full GIL isolation via `py.allow_threads()`

## Build

```bash
# Development (with maturin)
cd core/rust/geosync-accel
pip install maturin
maturin develop --release

# Or cargo-only (library tests)
cargo test
cargo bench
```

## Usage

```python
from core.accel import compute_gamma_accel, hilbert_sort, simd_info

# Automatic Rust/numpy dispatch
result = compute_gamma_accel(topo_data, cost_data)
print(f"gamma = {result['gamma']:.4f} (backend: {ACCEL_BACKEND})")

# Hilbert-curve spatial reordering
indices = hilbert_sort(geo_coordinates, order=16)

# System capabilities
info = simd_info()
print(f"SIMD: {info['simd_level']}, cores: {info['num_cores']}")
```

## Release Profile (Cargo.toml)

```toml
[profile.release]
opt-level = 3
lto = "fat"
codegen-units = 1
panic = "abort"
strip = "symbols"
```

With `.cargo/config.toml` LLVM flags:
- `-C llvm-args=-polly` — Polyhedral optimizer
- `-C llvm-args=-enable-loop-interchange` — Loop interchange
- `-C inline-threshold=275` — Aggressive inlining
