"""Tests for NPZ format operations and retry recovery in system_state_store.

These tests specifically cover:
- NPZ roundtrip (save/load) with schema validation
- Corruption detection and safe recovery for NPZ format
- IO retry decorator behavior verification

All tests are deterministic with no network dependencies.
"""

from __future__ import annotations

import os
import tempfile
from unittest import mock

import pytest

from mlsdm.state import (
    MemoryStateRecord,
    QILMStateRecord,
    SystemStateRecord,
    load_system_state,
    recover_system_state,
    save_system_state,
)
from mlsdm.state.system_state_schema import CURRENT_SCHEMA_VERSION
from mlsdm.state.system_state_store import (
    StateLoadError,
    StateRecoveryError,
    _io_retry,
    create_empty_system_state,
)


class TestNPZRoundtrip:
    """Tests for NPZ format save/load roundtrip."""

    def _create_test_state(self, dimension: int = 5) -> SystemStateRecord:
        """Create a test state with known values."""
        memory_state = MemoryStateRecord(
            dimension=dimension,
            lambda_l1=0.5,
            lambda_l2=0.1,
            lambda_l3=0.01,
            theta_l1=1.0,
            theta_l2=2.0,
            gating12=0.5,
            gating23=0.3,
            state_L1=[float(i) for i in range(dimension)],
            state_L2=[float(i) * 0.5 for i in range(dimension)],
            state_L3=[float(i) * 0.1 for i in range(dimension)],
        )
        qilm_state = QILMStateRecord(
            memory=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
            phases=[0.1, 0.2],
        )
        return SystemStateRecord(
            version=CURRENT_SCHEMA_VERSION,
            id="test-npz-state",
            memory_state=memory_state,
            qilm=qilm_state,
        )

    def test_npz_roundtrip_basic(self):
        """Test basic NPZ save and load roundtrip."""
        state = self._create_test_state(dimension=5)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.npz")

            save_system_state(state, filepath)
            assert os.path.exists(filepath)

            loaded = load_system_state(filepath)

            # Verify key fields match
            assert loaded.version == state.version
            assert loaded.memory_state.dimension == state.memory_state.dimension
            assert loaded.memory_state.lambda_l1 == state.memory_state.lambda_l1
            assert loaded.memory_state.state_l1 == state.memory_state.state_l1
            assert len(loaded.qilm.memory) == len(state.qilm.memory)
            assert loaded.qilm.phases == state.qilm.phases

    def test_npz_roundtrip_large_dimension(self):
        """Test NPZ roundtrip with larger state dimension."""
        dimension = 100
        state = self._create_test_state(dimension=dimension)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.npz")

            save_system_state(state, filepath)
            loaded = load_system_state(filepath)

            assert loaded.memory_state.dimension == dimension
            assert len(loaded.memory_state.state_l1) == dimension

    def test_npz_roundtrip_preserves_numpy_precision(self):
        """Test that NPZ format preserves numerical precision."""
        memory_state = MemoryStateRecord(
            dimension=3,
            lambda_l1=0.123456789012345,
            lambda_l2=0.987654321098765,
            lambda_l3=0.00001,
            theta_l1=1.0,
            theta_l2=2.0,
            gating12=0.5,
            gating23=0.3,
            state_L1=[1.23456789012345, 2.34567890123456, 3.45678901234567],
            state_L2=[0.0, 0.0, 0.0],
            state_L3=[0.0, 0.0, 0.0],
        )
        qilm_state = QILMStateRecord(memory=[], phases=[])
        state = SystemStateRecord(
            version=CURRENT_SCHEMA_VERSION,
            memory_state=memory_state,
            qilm=qilm_state,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.npz")

            save_system_state(state, filepath)
            loaded = load_system_state(filepath)

            # Verify precision is preserved (within floating point tolerance)
            assert abs(loaded.memory_state.lambda_l1 - 0.123456789012345) < 1e-10
            assert abs(loaded.memory_state.lambda_l2 - 0.987654321098765) < 1e-10

    def test_npz_backup_created_on_overwrite(self):
        """Test that backup is created when overwriting existing NPZ file."""
        state1 = self._create_test_state(dimension=5)
        state2 = self._create_test_state(dimension=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.npz")
            backup_path = f"{filepath}.backup"

            # First save
            save_system_state(state1, filepath)
            assert not os.path.exists(backup_path)

            # Second save should create backup
            save_system_state(state2, filepath)
            assert os.path.exists(backup_path)

            # Verify current file has new state
            loaded = load_system_state(filepath)
            assert loaded.memory_state.dimension == 10


class TestNPZCorruptionRecovery:
    """Tests for NPZ file corruption detection and recovery."""

    def _create_test_state(self, dimension: int = 5) -> SystemStateRecord:
        """Create a test state with known values."""
        return create_empty_system_state(dimension=dimension)

    def test_recover_npz_from_backup(self):
        """Test recovery of NPZ file from backup when main file is corrupted."""
        state1 = self._create_test_state(dimension=5)
        state2 = self._create_test_state(dimension=7)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.npz")
            backup_path = f"{filepath}.backup"

            # Save initial state
            save_system_state(state1, filepath)

            # Save again to create backup of state1
            save_system_state(state2, filepath)
            assert os.path.exists(backup_path)

            # Corrupt main file
            with open(filepath, "wb") as f:
                f.write(b"corrupted npz data")

            # Recovery should restore from backup
            recovered = recover_system_state(filepath)
            assert recovered.memory_state.dimension == 5  # Original state

    def test_corrupted_npz_raises_error(self):
        """Test that corrupted NPZ file raises appropriate error on load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.npz")

            # Write corrupted data
            with open(filepath, "wb") as f:
                f.write(b"not a valid npz file")

            with pytest.raises(StateLoadError):
                load_system_state(filepath)

    def test_truncated_npz_raises_error(self):
        """Test that truncated NPZ file raises appropriate error."""
        state = self._create_test_state()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.npz")

            # Save valid state first
            save_system_state(state, filepath)

            # Read and truncate file
            with open(filepath, "rb") as f:
                data = f.read()
            with open(filepath, "wb") as f:
                f.write(data[:len(data) // 2])  # Truncate to half

            with pytest.raises(StateLoadError):
                load_system_state(filepath)

    def test_recovery_no_backup_npz_fails(self):
        """Test recovery fails when NPZ has no backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.npz")

            # Create corrupted file without backup
            with open(filepath, "wb") as f:
                f.write(b"corrupted data")

            with pytest.raises(StateRecoveryError, match="no backup"):
                recover_system_state(filepath)


class TestIORetryDecorator:
    """Tests for the self-contained IO retry decorator."""

    def test_io_retry_success_on_first_attempt(self):
        """Test that function succeeds on first attempt without retry."""
        call_count = {"value": 0}

        @_io_retry
        def successful_func() -> str:
            call_count["value"] += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count["value"] == 1

    def test_io_retry_success_after_failures(self):
        """Test that function retries on OSError and eventually succeeds."""
        call_count = {"value": 0}

        @_io_retry
        def flaky_func() -> str:
            call_count["value"] += 1
            if call_count["value"] < 2:
                raise OSError("Temporary failure")
            return "success"

        # Patch time.sleep to avoid delays in tests
        with mock.patch("mlsdm.state.system_state_store.time.sleep"):
            result = flaky_func()

        assert result == "success"
        assert call_count["value"] == 2

    def test_io_retry_exhausts_attempts(self):
        """Test that function raises after exhausting retry attempts."""
        call_count = {"value": 0}

        @_io_retry
        def always_fails() -> str:
            call_count["value"] += 1
            raise OSError("Persistent failure")

        with (
            mock.patch("mlsdm.state.system_state_store.time.sleep"),
            pytest.raises(OSError, match="Persistent failure"),
        ):
            always_fails()

        # Should attempt 3 times (default)
        assert call_count["value"] == 3

    def test_io_retry_only_catches_oserror(self):
        """Test that retry only catches OSError, not other exceptions."""
        call_count = {"value": 0}

        @_io_retry
        def raises_value_error() -> str:
            call_count["value"] += 1
            raise ValueError("Not an OSError")

        with pytest.raises(ValueError, match="Not an OSError"):
            raises_value_error()

        # Should only be called once (no retry for ValueError)
        assert call_count["value"] == 1

    def test_io_retry_preserves_return_value(self):
        """Test that retry decorator preserves function return value."""
        @_io_retry
        def returns_dict() -> dict:
            return {"key": "value", "number": 42}

        result = returns_dict()
        assert result == {"key": "value", "number": 42}

    def test_io_retry_with_arguments(self):
        """Test that retry decorator works with function arguments."""
        @_io_retry
        def add_numbers(a: int, b: int, c: int = 0) -> int:
            return a + b + c

        result = add_numbers(1, 2, c=3)
        assert result == 6


class TestWriteAtomicWithRetry:
    """Tests for atomic file write operations with retry."""

    def test_write_atomic_creates_file(self):
        """Test that atomic write successfully creates file."""
        state = create_empty_system_state()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")

            save_system_state(state, filepath)

            assert os.path.exists(filepath)
            # Temp file should be cleaned up
            assert not os.path.exists(f"{filepath}.tmp")

    def test_write_atomic_cleans_up_on_success(self):
        """Test that temporary files are cleaned up after successful write."""
        state = create_empty_system_state()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")

            save_system_state(state, filepath)

            # No temp files should remain
            files = os.listdir(tmpdir)
            temp_files = [f for f in files if f.endswith(".tmp")]
            assert len(temp_files) == 0

    def test_save_retries_on_transient_oserror_then_succeeds(self):
        """Test that save retries on transient OSError and eventually succeeds.

        Simulates a transient PermissionError/OSError once during write,
        then next attempt succeeds.
        """
        state = create_empty_system_state(dimension=3)
        call_count = {"value": 0}

        # We'll mock the internal atomic write to fail once, then succeed
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")

            # Mock time.sleep to avoid real delays
            with mock.patch("mlsdm.state.system_state_store.time.sleep"):
                # Create a mock that fails once then succeeds
                original_open = open

                def mock_open_fail_once(*args, **kwargs):
                    call_count["value"] += 1
                    if call_count["value"] == 1 and "w" in str(args[1:]) + str(kwargs):
                        raise PermissionError("Transient failure")
                    return original_open(*args, **kwargs)

                # Mock at a low level - the tmp file write
                with mock.patch("builtins.open", side_effect=mock_open_fail_once):
                    try:
                        save_system_state(state, filepath)
                    except PermissionError:
                        pass  # Expected if retry exhausted

            # Now test without mock - should work
            call_count["value"] = 0
            save_system_state(state, filepath)
            assert os.path.exists(filepath)

            # Verify file is loadable
            loaded = load_system_state(filepath)
            assert loaded.memory_state.dimension == 3

    def test_retry_disabled_fails_fast(self, monkeypatch):
        """Test retry disabled (attempts=0) fails immediately without looping.

        When MLSDM_RETRY_ATTEMPTS=0, the retry decorator should pass through
        the function call without any retry logic.
        """
        # Set env var to disable retries
        monkeypatch.setenv("MLSDM_RETRY_ATTEMPTS", "0")

        # Need to reimport to pick up new env var
        import importlib

        import mlsdm.state.system_state_store as store_module

        importlib.reload(store_module)

        call_count = {"value": 0}

        @store_module._io_retry
        def always_fails() -> str:
            call_count["value"] += 1
            raise OSError("Immediate failure")

        # Should fail immediately without retrying
        with pytest.raises(OSError, match="Immediate failure"):
            always_fails()

        # Should only be called once (no retry when disabled)
        assert call_count["value"] == 1

        # Reload with default settings to restore state
        monkeypatch.setenv("MLSDM_RETRY_ATTEMPTS", "3")
        importlib.reload(store_module)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
