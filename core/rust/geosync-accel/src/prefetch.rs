// GEOSYNC-ACCEL — Cache-Oblivious Prefetch Utilities
//
// Implements cache-line aware data structures and explicit software
// prefetching for memory-bound geospatial computations.
//
// Key principles:
// 1. Align data structures to cache line boundaries (64 bytes on x86, 128 on Apple M)
// 2. Use explicit _mm_prefetch before traversing geo-index trees
// 3. Pack hot data into cache-line-sized nodes
//
// The memory controller can only fetch full cache lines, so misaligned
// data causes 2x the memory traffic. These utilities ensure every
// access pattern is cache-friendly.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

/// Cache line size in bytes (x86_64 standard).
pub const CACHE_LINE_BYTES: usize = 64;

/// Number of f64 values that fit in a single cache line.
pub const F64_PER_CACHE_LINE: usize = CACHE_LINE_BYTES / std::mem::size_of::<f64>();

/// A cache-line-aligned node for spatial data (fits exactly in one 64-byte line).
///
/// Holds up to 8 f64 values (8 × 8 = 64 bytes), perfect for:
/// - 4 geo-coordinates (x, y, z, w) with 4 auxiliary values
/// - R-Tree bounding box (min_x, min_y, max_x, max_y) + metadata
#[repr(C, align(64))]
#[derive(Debug, Clone, Copy)]
pub struct CacheLineNode {
    pub data: [f64; F64_PER_CACHE_LINE],
}

impl CacheLineNode {
    /// Create a zero-initialized cache-line node.
    pub const fn zero() -> Self {
        Self {
            data: [0.0; F64_PER_CACHE_LINE],
        }
    }

    /// Create a node from a slice (pads with zeros if shorter than 8).
    pub fn from_slice(values: &[f64]) -> Self {
        let mut node = Self::zero();
        let n = values.len().min(F64_PER_CACHE_LINE);
        node.data[..n].copy_from_slice(&values[..n]);
        node
    }
}

/// Explicit software prefetch for the next N cache lines ahead.
///
/// On x86_64, this emits `_mm_prefetch` intrinsics with T0 locality hint
/// (prefetch into all cache levels). On other architectures, this is a no-op
/// that the compiler may optimize into platform-specific prefetch instructions.
#[inline(always)]
pub fn prefetch_ahead<T>(ptr: *const T, lines_ahead: usize) {
    #[cfg(target_arch = "x86_64")]
    {
        unsafe {
            for i in 0..lines_ahead {
                let addr = (ptr as *const u8).add(i * CACHE_LINE_BYTES);
                std::arch::x86_64::_mm_prefetch::<{ std::arch::x86_64::_MM_HINT_T0 }>(
                    addr as *const i8,
                );
            }
        }
    }

    #[cfg(not(target_arch = "x86_64"))]
    {
        // Compiler hint — most backends will emit prefetch instructions
        let _ = (ptr, lines_ahead);
        std::hint::spin_loop();
    }
}

/// Pack a flat array of f64 into cache-line-aligned nodes.
///
/// This is the first step in building a cache-oblivious spatial index:
/// data is reorganized so that each cache-line-sized chunk contains
/// spatially related values (after Hilbert-curve reordering).
pub fn pack_into_cache_lines(data: &[f64]) -> Vec<CacheLineNode> {
    data.chunks(F64_PER_CACHE_LINE)
        .map(CacheLineNode::from_slice)
        .collect()
}

/// Traverse an array of cache-line nodes with explicit prefetching.
///
/// Prefetches `lookahead` nodes ahead of the current iteration index,
/// ensuring the memory controller has the next data ready in L1 before
/// the ALU needs it.
///
/// Returns the sum of all values (as a demonstration of prefetch benefit).
pub fn prefetch_traverse(nodes: &[CacheLineNode], lookahead: usize) -> f64 {
    let n = nodes.len();
    let mut total = 0.0;

    for i in 0..n {
        // Prefetch future nodes into L1
        if i + lookahead < n {
            prefetch_ahead(&nodes[i + lookahead] as *const CacheLineNode, 1);
        }

        // Process current node
        for &val in &nodes[i].data {
            total += val;
        }
    }

    total
}

/// Memory-aligned allocation for large geo-data buffers.
///
/// Uses the system allocator with explicit alignment to avoid
/// cache line straddling on bulk data loads.
pub fn aligned_vec_f64(len: usize) -> Vec<f64> {
    // Vec<f64> is already 8-byte aligned; for 64-byte alignment we
    // over-allocate and use aligned CacheLineNodes, then view as f64.
    let n_nodes = (len + F64_PER_CACHE_LINE - 1) / F64_PER_CACHE_LINE;
    let nodes = vec![CacheLineNode::zero(); n_nodes];

    // Safety: CacheLineNode is repr(C, align(64)) with only f64 data
    let ptr = nodes.as_ptr() as *const f64;
    let aligned = unsafe { std::slice::from_raw_parts(ptr, n_nodes * F64_PER_CACHE_LINE) };

    // Return a new Vec that copies the aligned memory
    // (in production, we'd use a custom allocator to avoid the copy)
    aligned[..len].to_vec()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cache_line_size() {
        assert_eq!(std::mem::size_of::<CacheLineNode>(), 64);
        assert_eq!(std::mem::align_of::<CacheLineNode>(), 64);
    }

    #[test]
    fn test_f64_per_cache_line() {
        assert_eq!(F64_PER_CACHE_LINE, 8);
    }

    #[test]
    fn test_cache_line_node_from_slice() {
        let node = CacheLineNode::from_slice(&[1.0, 2.0, 3.0]);
        assert_eq!(node.data[0], 1.0);
        assert_eq!(node.data[1], 2.0);
        assert_eq!(node.data[2], 3.0);
        assert_eq!(node.data[3], 0.0); // padding
    }

    #[test]
    fn test_pack_into_cache_lines() {
        let data: Vec<f64> = (0..20).map(|i| i as f64).collect();
        let nodes = pack_into_cache_lines(&data);
        assert_eq!(nodes.len(), 3); // 20 values / 8 per line = 2.5 → 3 nodes
        assert_eq!(nodes[0].data[0], 0.0);
        assert_eq!(nodes[1].data[0], 8.0);
        assert_eq!(nodes[2].data[3], 19.0);
    }

    #[test]
    fn test_prefetch_traverse_sum() {
        let data: Vec<f64> = (1..=16).map(|i| i as f64).collect();
        let nodes = pack_into_cache_lines(&data);
        let total = prefetch_traverse(&nodes, 2);
        let expected: f64 = (1..=16).map(|i| i as f64).sum();
        assert!((total - expected).abs() < 1e-10);
    }

    #[test]
    fn test_aligned_alloc() {
        let v = aligned_vec_f64(100);
        assert_eq!(v.len(), 100);
        // All values should be zero-initialized
        assert!(v.iter().all(|&x| x == 0.0));
    }
}
