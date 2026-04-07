// GEOSYNC-ACCEL — Hilbert Curve Spatial Indexing
//
// Implements Hilbert curve encoding for cache-oblivious spatial data layout.
// Spatial coordinates are mapped to a 1-D Hilbert index that preserves
// spatial locality — nearby points in 2D/3D space map to nearby indices.
//
// This is critical for geospatial R-Tree and KNN performance because it
// guarantees that spatially close points reside in the same cache line
// and memory page, maximizing L1/L2 hit rates.
//
// The implementation uses the standard bit-interleaving approach with
// Gray code transforms for the Hilbert curve.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

/// Hilbert curve order (bits per dimension). Order 32 covers full u64 range.
pub const DEFAULT_ORDER: u32 = 32;

/// Encode a 2D coordinate into a Hilbert curve index.
///
/// The input coordinates are on a [0, 2^order - 1] integer grid.
/// Returns a u64 Hilbert index that preserves spatial locality.
pub fn xy_to_hilbert(mut x: u32, mut y: u32, order: u32) -> u64 {
    let n = 1u32 << order;
    let mut d: u64 = 0;

    let mut s = n >> 1;
    while s > 0 {
        let rx = if (x & s) > 0 { 1u32 } else { 0 };
        let ry = if (y & s) > 0 { 1u32 } else { 0 };
        d += (s as u64 * s as u64) * ((3 * rx) ^ ry) as u64;
        rot(s, &mut x, &mut y, rx, ry);
        s >>= 1;
    }

    d
}

/// Decode a Hilbert curve index back to 2D coordinates.
pub fn hilbert_to_xy(mut d: u64, order: u32) -> (u32, u32) {
    let n = 1u32 << order;
    let mut x: u32 = 0;
    let mut y: u32 = 0;

    let mut s: u32 = 1;
    while s < n {
        let rx = (1 & (d / 2)) as u32;
        let ry = (1 & (d ^ rx as u64)) as u32;
        rot(s, &mut x, &mut y, rx, ry);
        x = x.wrapping_add(s * rx);
        y = y.wrapping_add(s * ry);
        d /= 4;
        s <<= 1;
    }

    (x, y)
}

/// Rotate/flip a quadrant in the Hilbert curve.
fn rot(n: u32, x: &mut u32, y: &mut u32, rx: u32, ry: u32) {
    if ry == 0 {
        if rx == 1 {
            *x = n.wrapping_sub(1).wrapping_sub(*x);
            *y = n.wrapping_sub(1).wrapping_sub(*y);
        }
        std::mem::swap(x, y);
    }
}

/// Normalize floating-point geo-coordinates to Hilbert grid indices.
///
/// Maps (lon, lat) from their bounding box to [0, 2^order - 1] integer grid.
pub fn normalize_to_grid(
    coords: &[(f64, f64)],
    order: u32,
) -> Vec<(u32, u32)> {
    if coords.is_empty() {
        return Vec::new();
    }

    let max_val = (1u64 << order) - 1;

    let (min_x, max_x, min_y, max_y) = coords.iter().fold(
        (f64::INFINITY, f64::NEG_INFINITY, f64::INFINITY, f64::NEG_INFINITY),
        |(mnx, mxx, mny, mxy), &(x, y)| {
            (mnx.min(x), mxx.max(x), mny.min(y), mxy.max(y))
        },
    );

    let range_x = (max_x - min_x).max(1e-15);
    let range_y = (max_y - min_y).max(1e-15);

    coords
        .iter()
        .map(|&(x, y)| {
            let gx = (((x - min_x) / range_x) * max_val as f64).round() as u32;
            let gy = (((y - min_y) / range_y) * max_val as f64).round() as u32;
            (gx, gy)
        })
        .collect()
}

/// Sort geo-coordinates by Hilbert curve index for cache-optimal access.
///
/// Returns indices that would sort the points along the Hilbert curve.
/// Access patterns following this order maximize spatial cache locality.
pub fn hilbert_sort_indices(coords: &[(f64, f64)], order: u32) -> Vec<usize> {
    let grid = normalize_to_grid(coords, order);
    let mut indexed: Vec<(usize, u64)> = grid
        .iter()
        .enumerate()
        .map(|(i, &(gx, gy))| (i, xy_to_hilbert(gx, gy, order)))
        .collect();

    indexed.sort_unstable_by_key(|&(_, h)| h);
    indexed.into_iter().map(|(i, _)| i).collect()
}

/// Reorder a data array according to Hilbert-sorted indices.
///
/// This produces a cache-friendly memory layout where spatially
/// adjacent points occupy contiguous cache lines.
pub fn hilbert_reorder<T: Clone>(data: &[T], indices: &[usize]) -> Vec<T> {
    indices.iter().map(|&i| data[i].clone()).collect()
}

/// Compute Hilbert indices for a batch of coordinates (parallel via Rayon).
pub fn batch_hilbert_indices(coords: &[(f64, f64)], order: u32) -> Vec<u64> {
    use rayon::prelude::*;

    let grid = normalize_to_grid(coords, order);
    grid.par_iter()
        .map(|&(gx, gy)| xy_to_hilbert(gx, gy, order))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hilbert_roundtrip() {
        for x in 0..16u32 {
            for y in 0..16u32 {
                let d = xy_to_hilbert(x, y, 4);
                let (rx, ry) = hilbert_to_xy(d, 4);
                assert_eq!((x, y), (rx, ry), "Roundtrip failed for ({x}, {y})");
            }
        }
    }

    #[test]
    fn test_hilbert_locality() {
        // Adjacent Hilbert indices should correspond to spatially close points
        let d1 = xy_to_hilbert(5, 5, 8);
        let d2 = xy_to_hilbert(5, 6, 8);
        let d3 = xy_to_hilbert(100, 100, 8);

        // (5,5) and (5,6) should be closer in Hilbert space than (5,5) and (100,100)
        let diff_close = (d1 as i64 - d2 as i64).unsigned_abs();
        let diff_far = (d1 as i64 - d3 as i64).unsigned_abs();
        assert!(
            diff_close < diff_far,
            "Spatial locality violated: close={diff_close}, far={diff_far}"
        );
    }

    #[test]
    fn test_hilbert_sort_preserves_locality() {
        let coords = vec![
            (0.0, 0.0),
            (100.0, 100.0),
            (1.0, 1.0),
            (99.0, 99.0),
            (50.0, 50.0),
        ];
        let indices = hilbert_sort_indices(&coords, 16);
        assert_eq!(indices.len(), 5);

        // After sorting, (0,0) and (1,1) should be adjacent
        let pos_00 = indices.iter().position(|&i| i == 0).unwrap();
        let pos_11 = indices.iter().position(|&i| i == 2).unwrap();
        assert!(
            (pos_00 as isize - pos_11 as isize).unsigned_abs() <= 2,
            "Nearby points should be close in Hilbert order"
        );
    }

    #[test]
    fn test_normalize_to_grid() {
        let coords = vec![(0.0, 0.0), (1.0, 1.0), (0.5, 0.5)];
        let grid = normalize_to_grid(&coords, 8);
        assert_eq!(grid[0], (0, 0));
        assert_eq!(grid[1], (255, 255));
        assert_eq!(grid[2], (128, 128)); // approximately center
    }

    #[test]
    fn test_empty_coords() {
        let coords: Vec<(f64, f64)> = vec![];
        let indices = hilbert_sort_indices(&coords, 16);
        assert!(indices.is_empty());
    }
}
