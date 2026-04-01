import numpy as np
import pytest

from bnsyn.emergence.crystallizer import Attractor, AttractorCrystallizer


def test_crystallizer_invalid_params() -> None:
    with pytest.raises(ValueError, match="state_dim must be positive"):
        AttractorCrystallizer(state_dim=0)
    with pytest.raises(ValueError, match="max_buffer_size must be positive"):
        AttractorCrystallizer(state_dim=2, max_buffer_size=0)
    with pytest.raises(ValueError, match="snapshot_dim must be in"):
        AttractorCrystallizer(state_dim=2, snapshot_dim=3)
    with pytest.raises(ValueError, match="pca_update_interval must be positive"):
        AttractorCrystallizer(state_dim=2, snapshot_dim=2, pca_update_interval=0)
    with pytest.raises(ValueError, match="cluster_eps must be positive"):
        AttractorCrystallizer(state_dim=2, snapshot_dim=2, cluster_eps=0.0)
    with pytest.raises(ValueError, match="cluster_min_samples must be positive"):
        AttractorCrystallizer(state_dim=2, snapshot_dim=2, cluster_min_samples=0)


def test_crystallizer_subsample_shape_validation() -> None:
    crystallizer = AttractorCrystallizer(state_dim=4, snapshot_dim=2)
    with pytest.raises(ValueError, match="Expected state shape"):
        crystallizer._subsample_state(np.zeros(3))


def test_crystallizer_transform_default_passthrough() -> None:
    crystallizer = AttractorCrystallizer(state_dim=2, snapshot_dim=2)
    state = np.array([0.1, 0.2], dtype=np.float64)
    transformed = crystallizer._transform_to_pca(state)
    assert np.allclose(transformed, state)


def test_crystallizer_pca_failure_retains_previous(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    crystallizer = AttractorCrystallizer(state_dim=2, snapshot_dim=2, max_buffer_size=5)
    crystallizer._buffer[:2] = np.array([[0.0, 0.0], [1.0, 1.0]], dtype=np.float64)
    crystallizer._buffer_idx = 2
    crystallizer._update_pca()

    previous_components = crystallizer._pca_components.copy()
    previous_mean = crystallizer._pca_mean.copy()

    def _raise_svd(*_args: object, **_kwargs: object) -> None:
        raise np.linalg.LinAlgError("svd failure")

    monkeypatch.setattr(np.linalg, "svd", _raise_svd)
    with caplog.at_level("WARNING"):
        crystallizer._update_pca()

    assert np.array_equal(crystallizer._pca_components, previous_components)
    assert np.array_equal(crystallizer._pca_mean, previous_mean)
    assert "Retaining previous components" in caplog.text


def test_crystallizer_dbscan_detects_cluster() -> None:
    crystallizer = AttractorCrystallizer(
        state_dim=2, snapshot_dim=2, cluster_eps=0.2, cluster_min_samples=2
    )
    data = np.array([[0.0, 0.0], [0.05, 0.05], [1.0, 1.0]], dtype=np.float64)
    clusters = crystallizer._dbscan_lite(data)
    assert any(len(cluster) >= 2 for cluster in clusters)


def test_crystallizer_refresh_updates_existing_attractor_metrics() -> None:
    crystallizer = AttractorCrystallizer(state_dim=2, snapshot_dim=2, cluster_eps=0.25)
    crystallizer._attractors = [
        Attractor(
            center=np.array([0.0, 0.0], dtype=np.float64),
            basin_radius=0.1,
            stability=0.2,
            formation_step=7,
            crystallization=0.4,
        )
    ]

    crystallizer._refresh_attractors(
        [
            Attractor(
                center=np.array([0.1, 0.1], dtype=np.float64),
                basin_radius=0.3,
                stability=0.9,
                formation_step=99,
                crystallization=1.0,
            )
        ]
    )

    attractors = crystallizer.get_attractors()
    assert len(attractors) == 1
    assert np.allclose(attractors[0].center, np.array([0.1, 0.1], dtype=np.float64))
    assert attractors[0].basin_radius == pytest.approx(0.3)
    assert attractors[0].stability == pytest.approx(0.9)
    assert attractors[0].formation_step == 7
    assert attractors[0].crystallization == pytest.approx(1.0)


def test_crystallizer_refresh_drops_inactive_attractors_and_notifies_new() -> None:
    crystallizer = AttractorCrystallizer(state_dim=2, snapshot_dim=2, cluster_eps=0.25)
    crystallizer._attractors = [
        Attractor(
            center=np.array([0.0, 0.0], dtype=np.float64),
            basin_radius=0.1,
            stability=0.5,
            formation_step=1,
            crystallization=1.0,
        )
    ]
    formed: list[Attractor] = []
    crystallizer.on_attractor_formed(formed.append)

    new_attractor = Attractor(
        center=np.array([1.0, 1.0], dtype=np.float64),
        basin_radius=0.2,
        stability=0.8,
        formation_step=5,
        crystallization=1.0,
    )

    crystallizer._refresh_attractors([new_attractor])

    attractors = crystallizer.get_attractors()
    assert attractors == [new_attractor]
    assert formed == [new_attractor]


def test_crystallizer_refresh_does_not_refire_callback_for_matched_attractor() -> None:
    crystallizer = AttractorCrystallizer(state_dim=2, snapshot_dim=2, cluster_eps=0.25)
    crystallizer._attractors = [
        Attractor(
            center=np.array([0.0, 0.0], dtype=np.float64),
            basin_radius=0.1,
            stability=0.4,
            formation_step=3,
            crystallization=0.8,
        )
    ]
    formed: list[Attractor] = []
    crystallizer.on_attractor_formed(formed.append)

    crystallizer._refresh_attractors(
        [
            Attractor(
                center=np.array([0.1, 0.1], dtype=np.float64),
                basin_radius=0.2,
                stability=0.6,
                formation_step=12,
                crystallization=1.0,
            )
        ]
    )

    attractors = crystallizer.get_attractors()
    assert len(attractors) == 1
    assert attractors[0].formation_step == 3
    assert formed == []


def test_crystallizer_refresh_prefers_nearest_unmatched_existing_attractor() -> None:
    crystallizer = AttractorCrystallizer(state_dim=2, snapshot_dim=2, cluster_eps=0.5)
    crystallizer._attractors = [
        Attractor(
            center=np.array([0.0, 0.0], dtype=np.float64),
            basin_radius=0.1,
            stability=0.2,
            formation_step=11,
            crystallization=0.4,
        ),
        Attractor(
            center=np.array([0.3, 0.3], dtype=np.float64),
            basin_radius=0.1,
            stability=0.7,
            formation_step=29,
            crystallization=1.0,
        ),
    ]

    crystallizer._refresh_attractors(
        [
            Attractor(
                center=np.array([0.26, 0.26], dtype=np.float64),
                basin_radius=0.2,
                stability=0.9,
                formation_step=100,
                crystallization=1.0,
            )
        ]
    )

    attractors = crystallizer.get_attractors()
    assert len(attractors) == 1
    assert attractors[0].formation_step == 29
    assert np.allclose(attractors[0].center, np.array([0.26, 0.26], dtype=np.float64))


def test_crystallizer_observe_replaces_stale_attractor_after_buffer_turnover() -> None:
    crystallizer = AttractorCrystallizer(
        state_dim=2,
        snapshot_dim=2,
        max_buffer_size=4,
        pca_update_interval=1,
        cluster_eps=0.25,
        cluster_min_samples=2,
    )

    for _ in range(4):
        crystallizer.observe(np.array([0.0, 0.0], dtype=np.float64), temperature=1.0)

    initial_attractors = crystallizer.get_attractors()
    assert len(initial_attractors) == 1
    assert np.allclose(initial_attractors[0].center, np.array([0.0, 0.0], dtype=np.float64))
    initial_formation_step = initial_attractors[0].formation_step

    for _ in range(4):
        crystallizer.observe(np.array([1.0, 1.0], dtype=np.float64), temperature=1.0)

    refreshed_attractors = crystallizer.get_attractors()
    assert len(refreshed_attractors) == 1
    assert np.allclose(refreshed_attractors[0].center, np.array([1.0, 1.0], dtype=np.float64))
    assert refreshed_attractors[0].formation_step > initial_formation_step


def test_crystallizer_observe_emits_callback_only_for_new_active_basin() -> None:
    crystallizer = AttractorCrystallizer(
        state_dim=2,
        snapshot_dim=2,
        max_buffer_size=4,
        pca_update_interval=1,
        cluster_eps=0.25,
        cluster_min_samples=2,
    )
    formed: list[Attractor] = []
    crystallizer.on_attractor_formed(formed.append)

    for _ in range(4):
        crystallizer.observe(np.array([0.0, 0.0], dtype=np.float64), temperature=1.0)

    assert len(formed) == 1
    assert np.allclose(formed[0].center, np.array([0.0, 0.0], dtype=np.float64))

    for _ in range(4):
        crystallizer.observe(np.array([0.0, 0.0], dtype=np.float64), temperature=1.0)

    assert len(formed) == 1

    for _ in range(4):
        crystallizer.observe(np.array([1.0, 1.0], dtype=np.float64), temperature=1.0)

    assert len(formed) == 2
    assert np.allclose(formed[1].center, np.array([1.0, 1.0], dtype=np.float64))
