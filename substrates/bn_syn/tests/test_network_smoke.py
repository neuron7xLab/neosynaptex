from bnsyn.sim.network import run_simulation, Network, NetworkParams
from bnsyn.config import AdExParams, CriticalityParams, SynapseParams
from bnsyn.rng import seed_all


def test_network_runs() -> None:
    m = run_simulation(steps=200, dt_ms=0.1, seed=7, N=100)
    assert "sigma_mean" in m and "rate_mean_hz" in m


def test_network_step_adaptive() -> None:
    """Test that Network.step_adaptive() works correctly."""
    pack = seed_all(42)
    net = Network(
        NetworkParams(N=50),
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.1,
        rng=pack.np_rng,
    )

    # Run a few steps with adaptive integration
    for _ in range(10):
        metrics = net.step_adaptive(atol=1e-8, rtol=1e-6)
        assert "sigma" in metrics
        assert "gain" in metrics
        assert "A_t" in metrics

    # Verify network state is reasonable
    assert net.state.V_mV.shape == (50,)
    assert net.state.w_pA.shape == (50,)


def test_network_backend_parameter() -> None:
    """Test that backend parameter works for both reference and accelerated."""
    pack = seed_all(42)

    # Test reference backend
    net_ref = Network(
        NetworkParams(N=30),
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.1,
        rng=pack.np_rng,
        backend="reference",
    )
    m_ref = net_ref.step()
    assert "sigma" in m_ref

    # Test accelerated backend
    pack2 = seed_all(42)  # Same seed for comparison
    net_acc = Network(
        NetworkParams(N=30),
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=0.1,
        rng=pack2.np_rng,
        backend="accelerated",
    )
    m_acc = net_acc.step()
    assert "sigma" in m_acc

    # Both should produce valid results
    assert m_ref["sigma"] == m_acc["sigma"]  # Deterministic with same seed
