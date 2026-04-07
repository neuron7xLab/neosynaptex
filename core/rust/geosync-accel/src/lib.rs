// GEOSYNC-ACCEL — Main Library Entry Point
//
// PyO3 module that exposes all Rust-accelerated kernels to Python.
// This is the single entry point for the `geosync_accel` Python extension.
//
// Architecture:
//   Python (numpy/scipy) ←→ geosync_accel (PyO3) ←→ Rust kernels
//                         ↕                        ↕
//                      DLPack/Arrow             SIMD/Rayon
//                      zero-copy                parallel
//
// The module provides:
// 1. `compute_gamma()` — SIMD-accelerated gamma-scaling regression
// 2. `hilbert_sort()` — Cache-optimal spatial reordering
// 3. `export_dlpack()` / `import_dlpack()` — Zero-copy tensor exchange
// 4. `export_arrow()` — Arrow C-Data capsule export
// 5. `simd_info()` — Runtime CPU feature detection report
// 6. `euclidean_distances()` — SIMD-dispatched distance computation
//
// SPDX-License-Identifier: AGPL-3.0-or-later

pub mod arrow_ffi;
pub mod dlpack;
pub mod gamma_kernel;
pub mod hilbert;
pub mod io_uring_bridge;
pub mod prefetch;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

// ═══════════════════════════════════════════════════════════════════
// PyO3 Python-visible functions
// ═══════════════════════════════════════════════════════════════════

/// Compute gamma-scaling via Theil-Sen robust regression (Rust-accelerated).
///
/// This is the drop-in replacement for `core.gamma.compute_gamma()`.
/// Uses SIMD-hinted math and Rayon-parallel bootstrap for ~10-50x speedup.
///
/// Args:
///     topo: list[float] — Topological complexity values
///     cost: list[float] — Thermodynamic cost values
///     min_pairs: int — Minimum valid data points (default: 5)
///     log_range_gate: float — Minimum log-range of topo (default: 0.5)
///     r2_gate: float — Minimum R² for verdict (default: 0.3)
///     bootstrap_n: int — Number of bootstrap iterations (default: 500)
///     seed: int — RNG seed for reproducibility (default: 42)
///
/// Returns:
///     dict with keys: gamma, r2, ci_low, ci_high, n_valid, verdict, bootstrap_gammas
#[pyfunction]
#[pyo3(signature = (topo, cost, min_pairs=5, log_range_gate=0.5, r2_gate=0.3, bootstrap_n=500, seed=42))]
fn compute_gamma(
    py: Python<'_>,
    topo: Vec<f64>,
    cost: Vec<f64>,
    min_pairs: usize,
    log_range_gate: f64,
    r2_gate: f64,
    bootstrap_n: usize,
    seed: u64,
) -> PyResult<PyObject> {
    // Release the GIL during computation
    let result = py.allow_threads(|| {
        gamma_kernel::compute_gamma(&topo, &cost, min_pairs, log_range_gate, r2_gate, bootstrap_n, seed)
    });

    let dict = PyDict::new(py);
    dict.set_item("gamma", result.gamma)?;
    dict.set_item("r2", result.r2)?;
    dict.set_item("ci_low", result.ci_low)?;
    dict.set_item("ci_high", result.ci_high)?;
    dict.set_item("n_valid", result.n_valid)?;
    dict.set_item("verdict", result.verdict.as_str())?;
    dict.set_item(
        "bootstrap_gammas",
        PyList::new(py, &result.bootstrap_gammas)?,
    )?;

    Ok(dict.into())
}

/// Sort geo-coordinates by Hilbert curve index for cache-optimal access.
///
/// Returns permutation indices that reorder points along the Hilbert curve,
/// maximizing spatial cache locality for subsequent R-Tree/KNN operations.
///
/// Args:
///     coords: list[tuple[float, float]] — (x, y) coordinate pairs
///     order: int — Hilbert curve order (default: 16, max: 32)
///
/// Returns:
///     list[int] — Permutation indices for Hilbert-optimal ordering
#[pyfunction]
#[pyo3(signature = (coords, order=16))]
fn hilbert_sort(coords: Vec<(f64, f64)>, order: u32) -> PyResult<Vec<usize>> {
    Ok(hilbert::hilbert_sort_indices(&coords, order))
}

/// Compute Hilbert curve indices for a batch of coordinates.
///
/// Args:
///     coords: list[tuple[float, float]] — (x, y) coordinate pairs
///     order: int — Hilbert curve order (default: 16)
///
/// Returns:
///     list[int] — Hilbert indices (u64)
#[pyfunction]
#[pyo3(signature = (coords, order=16))]
fn hilbert_indices(py: Python<'_>, coords: Vec<(f64, f64)>, order: u32) -> PyResult<Vec<u64>> {
    Ok(py.allow_threads(|| hilbert::batch_hilbert_indices(&coords, order)))
}

/// Export a float64 array as a DLPack PyCapsule (zero-copy).
///
/// The returned capsule follows the `__dlpack__` protocol and can be
/// consumed by PyTorch (`torch.from_dlpack()`), JAX, CuPy, etc.
///
/// Args:
///     data: list[float] — Data to export
///
/// Returns:
///     PyCapsule — DLPack capsule containing the tensor
#[pyfunction]
fn export_dlpack(py: Python<'_>, data: Vec<f64>) -> PyResult<PyObject> {
    dlpack::vec_to_dlpack_capsule(py, data)
}

/// Export a float64 array as Arrow C-Data PyCapsules.
///
/// Returns a (schema_capsule, array_capsule) tuple that follows the
/// Arrow PyCapsule Interface. Can be consumed by PyArrow, Polars, DuckDB.
///
/// Args:
///     data: list[float] — Data to export
///
/// Returns:
///     tuple[PyCapsule, PyCapsule] — (ArrowSchema, ArrowArray) capsules
#[pyfunction]
fn export_arrow(py: Python<'_>, data: Vec<f64>) -> PyResult<(PyObject, PyObject)> {
    arrow_ffi::export_f64_array_to_capsules(py, data)
}

/// SIMD-dispatched Euclidean distance computation.
///
/// Computes the distance from each point (ax[i], ay[i]) to target (bx, by).
/// Automatically selects the best SIMD path (AVX-512 > AVX2+FMA > scalar).
///
/// Args:
///     ax: list[float] — X coordinates of source points
///     ay: list[float] — Y coordinates of source points
///     bx: float — X coordinate of target point
///     by: float — Y coordinate of target point
///
/// Returns:
///     list[float] — Distances from each source point to target
#[pyfunction]
fn euclidean_distances(
    py: Python<'_>,
    ax: Vec<f64>,
    ay: Vec<f64>,
    bx: f64,
    by: f64,
) -> PyResult<Vec<f64>> {
    Ok(py.allow_threads(|| gamma_kernel::euclidean_distance(&ax, &ay, bx, by)))
}

/// Report the detected SIMD capability level and system info.
///
/// Returns:
///     dict with keys: simd_level, cache_line_bytes, num_cores, features
#[pyfunction]
fn simd_info(py: Python<'_>) -> PyResult<PyObject> {
    let level = gamma_kernel::detect_simd_level();
    let dict = PyDict::new(py);

    dict.set_item(
        "simd_level",
        match level {
            gamma_kernel::SimdLevel::Scalar => "scalar",
            gamma_kernel::SimdLevel::Sse42 => "sse4.2",
            gamma_kernel::SimdLevel::Avx2Fma => "avx2+fma",
            gamma_kernel::SimdLevel::Avx512f => "avx512f",
        },
    )?;
    dict.set_item("cache_line_bytes", prefetch::CACHE_LINE_BYTES)?;
    dict.set_item("f64_per_cache_line", prefetch::F64_PER_CACHE_LINE)?;
    dict.set_item(
        "num_cores",
        std::thread::available_parallelism()
            .map(|n| n.get())
            .unwrap_or(1),
    )?;

    // Feature flags
    let features = PyList::empty(py);
    #[cfg(target_arch = "x86_64")]
    {
        if is_x86_feature_detected!("sse4.2") {
            features.append("sse4.2")?;
        }
        if is_x86_feature_detected!("avx2") {
            features.append("avx2")?;
        }
        if is_x86_feature_detected!("fma") {
            features.append("fma")?;
        }
        if is_x86_feature_detected!("avx512f") {
            features.append("avx512f")?;
        }
    }
    #[cfg(target_arch = "aarch64")]
    {
        features.append("neon")?;
    }
    dict.set_item("features", features)?;

    Ok(dict.into())
}

// ═══════════════════════════════════════════════════════════════════
// PyO3 Module Registration
// ═══════════════════════════════════════════════════════════════════

/// GEOSYNC-ACCEL Python extension module.
///
/// High-performance Rust accelerator for neosynaptex gamma-scaling
/// computations with DLPack/Arrow zero-copy ABI, SIMD dispatch,
/// Hilbert-curve spatial indexing, and cache-oblivious data structures.
#[pymodule]
fn geosync_accel(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_gamma, m)?)?;
    m.add_function(wrap_pyfunction!(hilbert_sort, m)?)?;
    m.add_function(wrap_pyfunction!(hilbert_indices, m)?)?;
    m.add_function(wrap_pyfunction!(export_dlpack, m)?)?;
    m.add_function(wrap_pyfunction!(export_arrow, m)?)?;
    m.add_function(wrap_pyfunction!(euclidean_distances, m)?)?;
    m.add_function(wrap_pyfunction!(simd_info, m)?)?;

    // Module metadata
    m.add("__version__", "0.1.0")?;
    m.add("__doc__", "GEOSYNC-ACCEL: Rust-accelerated gamma-scaling with DLPack/Arrow zero-copy ABI")?;

    Ok(())
}
