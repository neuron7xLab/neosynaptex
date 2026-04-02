"""Multiverse engine tests -- grid size, summary statistics."""

import itertools

from core.multiverse import MULTIVERSE_GRID, MultiverseCell, multiverse_summary


def test_grid_size_432():
    n = len(list(itertools.product(*MULTIVERSE_GRID.values())))
    assert n == 432, f"Expected 432, got {n}"


def test_summary_basic():
    cells = [
        MultiverseCell(
            substrate="test",
            window_ratio=1.0,
            overlap=0.5,
            topo_summary="h0_entropy",
            metric="euclidean",
            estimator="theilslopes",
            block_m=2,
            gamma=1.0 + i * 0.01,
            ci_low=0.9,
            ci_high=1.1,
            n_eff=50,
            p_null=0.01,
            ci_contains_unity=True,
            ci_excludes_zero=True,
            quality_flag="ok",
        )
        for i in range(20)
    ]
    s = multiverse_summary(cells)
    assert s["n_cells_total"] == 20
    assert s["n_cells_valid"] == 20
    assert 0.9 < s["median_gamma"] < 1.3
    assert s["R_plus"] == 1.0
    assert s["R_unity"] == 1.0


def test_summary_filters_invalid():
    cells = [
        MultiverseCell(
            substrate="test",
            window_ratio=1.0,
            overlap=0.0,
            topo_summary="h0_entropy",
            metric="euclidean",
            estimator="theilslopes",
            block_m=1,
            gamma=1.0,
            ci_low=0.9,
            ci_high=1.1,
            n_eff=50,
            p_null=0.01,
            ci_contains_unity=True,
            ci_excludes_zero=True,
            quality_flag="ok",
        ),
        MultiverseCell(
            substrate="test",
            window_ratio=1.0,
            overlap=0.0,
            topo_summary="h0_entropy",
            metric="euclidean",
            estimator="theilslopes",
            block_m=1,
            gamma=float("nan"),
            ci_low=float("nan"),
            ci_high=float("nan"),
            n_eff=0,
            p_null=1.0,
            ci_contains_unity=False,
            ci_excludes_zero=False,
            quality_flag="low_range",
        ),
    ]
    s = multiverse_summary(cells)
    assert s["n_cells_total"] == 2
    assert s["n_cells_valid"] == 1


def test_summary_empty_returns_error():
    s = multiverse_summary([])
    assert "error" in s


def test_r_strong_requires_all_conditions():
    cells = [
        MultiverseCell(
            substrate="test",
            window_ratio=1.0,
            overlap=0.0,
            topo_summary="h0_entropy",
            metric="euclidean",
            estimator="theilslopes",
            block_m=1,
            gamma=1.0,
            ci_low=0.9,
            ci_high=1.1,
            n_eff=50,
            p_null=0.5,  # high p_null -> R_strong should be lower
            ci_contains_unity=True,
            ci_excludes_zero=True,
            quality_flag="ok",
        ),
    ]
    s = multiverse_summary(cells)
    assert s["R_strong"] == 0.0  # p_null=0.5 >= 0.25 -> fails R_strong
