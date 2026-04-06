use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn bench_gamma_computation(c: &mut Criterion) {
    // Generate synthetic power-law data: K = 100 * C^(-1.0)
    let n = 200;
    let topo: Vec<f64> = (1..=n).map(|i| i as f64).collect();
    let cost: Vec<f64> = topo.iter().map(|&c| 100.0 / c).collect();

    c.bench_function("compute_gamma_n200_b100", |b| {
        b.iter(|| {
            geosync_accel::gamma_kernel::compute_gamma(
                black_box(&topo),
                black_box(&cost),
                5,
                0.5,
                0.3,
                100,
                42,
            )
        })
    });

    c.bench_function("compute_gamma_n200_b500", |b| {
        b.iter(|| {
            geosync_accel::gamma_kernel::compute_gamma(
                black_box(&topo),
                black_box(&cost),
                5,
                0.5,
                0.3,
                500,
                42,
            )
        })
    });

    c.bench_function("theil_sen_slope_n200", |b| {
        let log_t: Vec<f64> = topo.iter().map(|t| t.ln()).collect();
        let log_c: Vec<f64> = cost.iter().map(|c| c.ln()).collect();
        b.iter(|| geosync_accel::gamma_kernel::theil_sen_slope(black_box(&log_t), black_box(&log_c)))
    });
}

fn bench_hilbert_curve(c: &mut Criterion) {
    let coords: Vec<(f64, f64)> = (0..10_000)
        .map(|i| {
            let x = (i as f64 * 0.1).sin() * 180.0;
            let y = (i as f64 * 0.07).cos() * 90.0;
            (x, y)
        })
        .collect();

    c.bench_function("hilbert_sort_10k", |b| {
        b.iter(|| geosync_accel::hilbert::hilbert_sort_indices(black_box(&coords), 16))
    });

    c.bench_function("hilbert_indices_10k", |b| {
        b.iter(|| geosync_accel::hilbert::batch_hilbert_indices(black_box(&coords), 16))
    });
}

fn bench_prefetch_traverse(c: &mut Criterion) {
    let data: Vec<f64> = (0..100_000).map(|i| i as f64 * 0.001).collect();
    let nodes = geosync_accel::prefetch::pack_into_cache_lines(&data);

    c.bench_function("prefetch_traverse_100k", |b| {
        b.iter(|| geosync_accel::prefetch::prefetch_traverse(black_box(&nodes), 4))
    });
}

fn bench_euclidean_distance(c: &mut Criterion) {
    let n = 100_000;
    let ax: Vec<f64> = (0..n).map(|i| (i as f64 * 0.01).sin()).collect();
    let ay: Vec<f64> = (0..n).map(|i| (i as f64 * 0.01).cos()).collect();

    c.bench_function("euclidean_distance_100k", |b| {
        b.iter(|| {
            geosync_accel::gamma_kernel::euclidean_distance(
                black_box(&ax),
                black_box(&ay),
                black_box(0.5),
                black_box(0.5),
            )
        })
    });
}

criterion_group!(
    benches,
    bench_gamma_computation,
    bench_hilbert_curve,
    bench_prefetch_traverse,
    bench_euclidean_distance,
);
criterion_main!(benches);
