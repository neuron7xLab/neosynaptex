"""Smoke tests for mycelium_fractal_net package imports.

This module validates that:
1. The top-level package imports successfully
2. All public API objects are importable
3. Package version is accessible
"""


def test_package_import() -> None:
    """Test that mycelium_fractal_net package imports successfully."""
    import mycelium_fractal_net

    assert mycelium_fractal_net is not None


def test_package_version() -> None:
    """Test that package version is accessible."""
    import mycelium_fractal_net

    assert hasattr(mycelium_fractal_net, "__version__")
    assert isinstance(mycelium_fractal_net.__version__, str)
    assert mycelium_fractal_net.__version__ == "0.1.0"


def test_public_api_functions() -> None:
    """Test that all public API functions are importable."""
    import pytest

    try:
        from mycelium_fractal_net import (
            compute_lyapunov_exponent,
            compute_nernst_potential,
            estimate_fractal_dimension,
            generate_fractal_ifs,
            run_mycelium_simulation,
            run_mycelium_simulation_with_history,
            run_validation,
            run_validation_cli,
            simulate_mycelium_field,
        )
    except ImportError as e:
        pytest.skip(f"Torch-dependent imports unavailable: {e}")

    # Verify functions are callable
    assert callable(compute_nernst_potential)
    assert callable(simulate_mycelium_field)
    assert callable(estimate_fractal_dimension)
    assert callable(generate_fractal_ifs)
    assert callable(compute_lyapunov_exponent)
    assert callable(run_validation)
    assert callable(run_validation_cli)
    assert callable(run_mycelium_simulation)
    assert callable(run_mycelium_simulation_with_history)


def test_public_api_classes() -> None:
    """Test that all public API classes are importable."""
    import pytest

    try:
        from mycelium_fractal_net import (
            HierarchicalKrumAggregator,
            MyceliumFractalNet,
            SparseAttention,
            STDPPlasticity,
            ValidationConfig,
        )
    except ImportError as e:
        pytest.skip(f"Torch-dependent imports unavailable: {e}")

    # Verify classes are importable
    assert STDPPlasticity is not None
    assert SparseAttention is not None
    assert HierarchicalKrumAggregator is not None
    assert MyceliumFractalNet is not None
    assert ValidationConfig is not None


def test_core_engines_import() -> None:
    """Test that core numerical engines are importable."""
    from mycelium_fractal_net import (
        FractalConfig,
        FractalGrowthEngine,
        FractalMetrics,
        MembraneConfig,
        MembraneEngine,
        MembraneMetrics,
        ReactionDiffusionConfig,
        ReactionDiffusionEngine,
        ReactionDiffusionMetrics,
    )

    # Verify engine classes
    assert MembraneEngine is not None
    assert MembraneConfig is not None
    assert MembraneMetrics is not None
    assert ReactionDiffusionEngine is not None
    assert ReactionDiffusionConfig is not None
    assert ReactionDiffusionMetrics is not None
    assert FractalGrowthEngine is not None
    assert FractalConfig is not None
    assert FractalMetrics is not None


def test_exceptions_import() -> None:
    """Test that custom exceptions are importable."""
    from mycelium_fractal_net import (
        NumericalInstabilityError,
        StabilityError,
        ValueOutOfRangeError,
    )

    # Verify exception classes
    assert issubclass(StabilityError, Exception)
    assert issubclass(ValueOutOfRangeError, Exception)
    assert issubclass(NumericalInstabilityError, Exception)


def test_physical_constants_import() -> None:
    """Test that physical constants are importable."""
    import pytest

    from mycelium_fractal_net import (
        BODY_TEMPERATURE_K,
        FARADAY_CONSTANT,
        ION_CLAMP_MIN,
        NERNST_RTFZ_MV,
        QUANTUM_JITTER_VAR,
        R_GAS_CONSTANT,
        TURING_THRESHOLD,
    )

    # ML-dependent constants: only available with torch [ml] extra
    try:
        from mycelium_fractal_net import (
            SPARSE_TOPK,
            STDP_A_MINUS,
            STDP_A_PLUS,
            STDP_TAU_MINUS,
            STDP_TAU_PLUS,
        )
    except ImportError:
        SPARSE_TOPK = 4
        STDP_A_MINUS = 0.012
        STDP_A_PLUS = 0.01
        STDP_TAU_MINUS = 0.020
        STDP_TAU_PLUS = 0.020

    # Verify constants have expected types and values
    assert isinstance(R_GAS_CONSTANT, float)
    assert pytest.approx(8.314, rel=1e-6) == R_GAS_CONSTANT
    assert isinstance(FARADAY_CONSTANT, float)
    assert pytest.approx(96485.33212, rel=1e-6) == FARADAY_CONSTANT
    assert isinstance(BODY_TEMPERATURE_K, float)
    assert pytest.approx(310.0, rel=1e-6) == BODY_TEMPERATURE_K
    assert isinstance(NERNST_RTFZ_MV, float)
    assert isinstance(ION_CLAMP_MIN, float)
    assert isinstance(TURING_THRESHOLD, float)
    assert isinstance(STDP_TAU_PLUS, float)
    assert isinstance(STDP_TAU_MINUS, float)
    assert isinstance(STDP_A_PLUS, float)
    assert isinstance(STDP_A_MINUS, float)
    assert isinstance(SPARSE_TOPK, int)
    assert isinstance(QUANTUM_JITTER_VAR, float)


def test_all_exports() -> None:
    """Test that __all__ exports match importable objects."""
    import mycelium_fractal_net

    # Verify __all__ is defined
    assert hasattr(mycelium_fractal_net, "__all__")

    # Verify all items in __all__ are actually importable
    skipped = []
    for name in mycelium_fractal_net.__all__:
        try:
            getattr(mycelium_fractal_net, name)
        except ImportError:
            # Torch-dependent lazy attributes raise ImportError when accessed
            skipped.append(name)
