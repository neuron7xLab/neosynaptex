from scripts import benchmark as bm


def test_stress_sparse_small():
    elapsed, nnz, mem_mb = bm.stress_test_sparse(neurons=500, conn_prob=0.01, steps=2, seed=7)
    assert nnz > 0
    assert elapsed >= 0
    assert mem_mb > 0


def test_benchmark_weight_update_smoke():
    elapsed, n_iter = bm.benchmark_weight_update(N=5, n_iter=3)
    assert n_iter == 3
    assert elapsed >= 0
