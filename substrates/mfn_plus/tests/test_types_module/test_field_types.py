"""
Tests for FieldState and FieldHistory types.

Validates field type invariants, conversions, and properties.
"""

import numpy as np
import pytest

from mycelium_fractal_net.types.field import (
    BoundaryCondition,
    FieldHistory,
    FieldState,
    GridShape,
)


class TestGridShape:
    """Tests for GridShape type."""

    def test_create_square_grid(self) -> None:
        """Test creating a square grid shape."""
        shape = GridShape.square(64)
        assert shape.rows == 64
        assert shape.cols == 64
        assert shape.is_square
        assert shape.size == 64
        assert shape.total_cells == 4096

    def test_create_rectangular_grid(self) -> None:
        """Test creating a rectangular grid shape."""
        shape = GridShape(rows=32, cols=64)
        assert shape.rows == 32
        assert shape.cols == 64
        assert not shape.is_square
        assert shape.total_cells == 2048

    def test_rectangular_size_raises(self) -> None:
        """Test that size property raises for non-square grids."""
        shape = GridShape(rows=32, cols=64)
        with pytest.raises(ValueError, match="only defined for square grids"):
            _ = shape.size

    def test_to_tuple(self) -> None:
        """Test conversion to tuple."""
        shape = GridShape(rows=32, cols=64)
        assert shape.to_tuple() == (32, 64)

    def test_invalid_dimensions(self) -> None:
        """Test validation of grid dimensions."""
        with pytest.raises(ValueError, match="rows must be >= 2"):
            GridShape(rows=1, cols=32)
        with pytest.raises(ValueError, match="cols must be >= 2"):
            GridShape(rows=32, cols=1)

    def test_frozen(self) -> None:
        """Test that GridShape is immutable."""
        shape = GridShape.square(32)
        with pytest.raises(Exception):  # FrozenInstanceError
            shape.rows = 64  # type: ignore


class TestFieldState:
    """Tests for FieldState type."""

    def test_create_valid_field(self) -> None:
        """Test creating a valid field state."""
        data = np.random.randn(32, 32) * 0.01 - 0.070
        field = FieldState(data=data)
        assert field.grid_size == 32
        assert field.shape.is_square

    def test_field_statistics(self) -> None:
        """Test field statistics properties."""
        data = np.full((32, 32), -0.070)  # -70 mV uniform field
        field = FieldState(data=data)
        assert abs(field.mean_mV - (-70.0)) < 0.01
        assert abs(field.min_mV - (-70.0)) < 0.01
        assert abs(field.max_mV - (-70.0)) < 0.01
        assert field.std_mV < 0.01

    def test_to_binary(self) -> None:
        """Test binary conversion."""
        data = np.array([[-0.080, -0.050], [-0.060, -0.040]])
        field = FieldState(data=data)
        binary = field.to_binary(threshold_v=-0.060)
        expected = np.array([[False, True], [False, True]])
        np.testing.assert_array_equal(binary, expected)

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        data = np.random.randn(32, 32) * 0.01 - 0.070
        field = FieldState(data=data)
        d = field.to_dict()
        assert "shape" in d
        assert "boundary" in d
        assert "min_mV" in d
        assert "max_mV" in d
        assert "mean_mV" in d
        assert "std_mV" in d

    def test_boundary_condition(self) -> None:
        """Test boundary condition attribute."""
        data = np.random.randn(32, 32) * 0.01 - 0.070
        field_periodic = FieldState(data=data, boundary=BoundaryCondition.PERIODIC)
        field_neumann = FieldState(data=data, boundary=BoundaryCondition.NEUMANN)
        assert field_periodic.boundary == BoundaryCondition.PERIODIC
        assert field_neumann.boundary == BoundaryCondition.NEUMANN

    def test_invalid_dimensions(self) -> None:
        """Test validation of field dimensions."""
        with pytest.raises(ValueError, match="must be 2D"):
            FieldState(data=np.array([1, 2, 3]))
        with pytest.raises(ValueError, match="must be >= 2"):
            FieldState(data=np.array([[1]]))

    def test_nan_rejected(self) -> None:
        """Test that NaN values are rejected."""
        data = np.array([[1.0, np.nan], [3.0, 4.0]])
        with pytest.raises(ValueError, match="NaN or Inf"):
            FieldState(data=data)

    def test_inf_rejected(self) -> None:
        """Test that Inf values are rejected."""
        data = np.array([[1.0, np.inf], [3.0, 4.0]])
        with pytest.raises(ValueError, match="NaN or Inf"):
            FieldState(data=data)


class TestFieldHistory:
    """Tests for FieldHistory type."""

    def test_create_valid_history(self) -> None:
        """Test creating valid field history."""
        data = np.random.randn(10, 32, 32) * 0.01 - 0.070
        history = FieldHistory(data=data)
        assert history.num_steps == 10
        assert history.grid_size == 32

    def test_get_frame(self) -> None:
        """Test getting individual frames."""
        data = np.random.randn(5, 32, 32) * 0.01 - 0.070
        history = FieldHistory(data=data)
        frame = history.get_frame(2)
        assert isinstance(frame, FieldState)
        assert frame.grid_size == 32

    def test_initial_and_final_state(self) -> None:
        """Test initial and final state properties."""
        data = np.random.randn(10, 32, 32) * 0.01 - 0.070
        history = FieldHistory(data=data)
        initial = history.initial_state
        final = history.final_state
        assert isinstance(initial, FieldState)
        assert isinstance(final, FieldState)
        np.testing.assert_array_equal(initial.data, data[0])
        np.testing.assert_array_equal(final.data, data[-1])

    def test_frame_index_bounds(self) -> None:
        """Test frame index validation."""
        data = np.random.randn(5, 32, 32) * 0.01 - 0.070
        history = FieldHistory(data=data)
        with pytest.raises(IndexError):
            history.get_frame(-1)
        with pytest.raises(IndexError):
            history.get_frame(5)

    def test_invalid_dimensions(self) -> None:
        """Test validation of history dimensions."""
        with pytest.raises(ValueError, match="must be 3D"):
            FieldHistory(data=np.random.randn(32, 32))
        with pytest.raises(ValueError, match="time steps must be >= 1"):
            FieldHistory(data=np.random.randn(0, 32, 32))
        with pytest.raises(ValueError, match="spatial dimensions must be >= 2"):
            FieldHistory(data=np.random.randn(5, 1, 32))

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        data = np.random.randn(10, 32, 32) * 0.01 - 0.070
        history = FieldHistory(data=data)
        d = history.to_dict()
        assert d["num_steps"] == 10
        assert d["spatial_shape"] == (32, 32)
        assert "initial_min_mV" in d
        assert "final_max_mV" in d


class TestBoundaryCondition:
    """Tests for BoundaryCondition enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert BoundaryCondition.PERIODIC.value == "periodic"
        assert BoundaryCondition.NEUMANN.value == "neumann"
        assert BoundaryCondition.DIRICHLET.value == "dirichlet"

    def test_string_conversion(self) -> None:
        """Test that enum inherits from str."""
        bc = BoundaryCondition.PERIODIC
        assert bc == "periodic"
        assert bc.value == "periodic"
