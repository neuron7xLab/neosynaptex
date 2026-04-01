"""
Unit Tests for System State Integrity.

Tests cover:
- Schema validation (valid and invalid records)
- Read-after-write consistency
- Migration from legacy format
- Recovery procedures
- Idempotent save operations
- Corruption detection
"""

import json
import os
import tempfile
from datetime import datetime, timezone

import pytest

from mlsdm.state import (
    MemoryStateRecord,
    QILMStateRecord,
    SystemStateRecord,
    delete_system_state,
    load_system_state,
    recover_system_state,
    save_system_state,
)
from mlsdm.state.system_state_migrations import migrate_state
from mlsdm.state.system_state_schema import (
    CURRENT_SCHEMA_VERSION,
    create_system_state_from_dict,
    validate_state_integrity,
)
from mlsdm.state.system_state_store import (
    StateCorruptionError,
    StateLoadError,
    StateRecoveryError,
    create_empty_system_state,
)


class TestMemoryStateRecord:
    """Tests for MemoryStateRecord schema validation."""

    def test_valid_memory_state_record(self):
        """Test creating a valid MemoryStateRecord."""
        record = MemoryStateRecord(
            dimension=3,
            lambda_l1=0.5,
            lambda_l2=0.1,
            lambda_l3=0.01,
            theta_l1=1.0,
            theta_l2=2.0,
            gating12=0.5,
            gating23=0.3,
            state_L1=[0.0, 0.0, 0.0],
            state_L2=[0.0, 0.0, 0.0],
            state_L3=[0.0, 0.0, 0.0],
        )
        assert record.dimension == 3
        assert len(record.state_l1) == 3

    def test_invalid_dimension_zero(self):
        """Test that dimension=0 raises validation error."""
        with pytest.raises(ValueError, match="greater than 0"):
            MemoryStateRecord(
                dimension=0,
                lambda_l1=0.5,
                lambda_l2=0.1,
                lambda_l3=0.01,
                theta_l1=1.0,
                theta_l2=2.0,
                gating12=0.5,
                gating23=0.3,
                state_L1=[],
                state_L2=[],
                state_L3=[],
            )

    def test_invalid_lambda_out_of_range(self):
        """Test that lambda values out of (0, 1] raise validation error."""
        with pytest.raises(ValueError):
            MemoryStateRecord(
                dimension=3,
                lambda_l1=0.0,  # Invalid: must be > 0
                lambda_l2=0.1,
                lambda_l3=0.01,
                theta_l1=1.0,
                theta_l2=2.0,
                gating12=0.5,
                gating23=0.3,
                state_L1=[0.0, 0.0, 0.0],
                state_L2=[0.0, 0.0, 0.0],
                state_L3=[0.0, 0.0, 0.0],
            )

        with pytest.raises(ValueError):
            MemoryStateRecord(
                dimension=3,
                lambda_l1=1.5,  # Invalid: must be <= 1
                lambda_l2=0.1,
                lambda_l3=0.01,
                theta_l1=1.0,
                theta_l2=2.0,
                gating12=0.5,
                gating23=0.3,
                state_L1=[0.0, 0.0, 0.0],
                state_L2=[0.0, 0.0, 0.0],
                state_L3=[0.0, 0.0, 0.0],
            )

    def test_state_dimension_mismatch(self):
        """Test that state arrays must match dimension."""
        with pytest.raises(ValueError, match="state_L1 length"):
            MemoryStateRecord(
                dimension=3,
                lambda_l1=0.5,
                lambda_l2=0.1,
                lambda_l3=0.01,
                theta_l1=1.0,
                theta_l2=2.0,
                gating12=0.5,
                gating23=0.3,
                state_L1=[0.0, 0.0],  # Wrong length!
                state_L2=[0.0, 0.0, 0.0],
                state_L3=[0.0, 0.0, 0.0],
            )


class TestQILMStateRecord:
    """Tests for QILMStateRecord schema validation."""

    def test_valid_qilm_state_record(self):
        """Test creating a valid QILMStateRecord."""
        record = QILMStateRecord(
            memory=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
            phases=[0.1, 0.5],
        )
        assert len(record.memory) == 2
        assert len(record.phases) == 2

    def test_empty_qilm_valid(self):
        """Test that empty QILM state is valid."""
        record = QILMStateRecord(memory=[], phases=[])
        assert len(record.memory) == 0
        assert len(record.phases) == 0

    def test_length_mismatch_invalid(self):
        """Test that mismatched memory/phases lengths are invalid."""
        with pytest.raises(ValueError, match="memory length"):
            QILMStateRecord(
                memory=[[1.0, 2.0, 3.0]],
                phases=[0.1, 0.5],  # Wrong length!
            )


class TestSystemStateRecord:
    """Tests for SystemStateRecord schema validation."""

    def test_valid_system_state_record(self):
        """Test creating a valid SystemStateRecord."""
        memory = MemoryStateRecord(
            dimension=3,
            lambda_l1=0.5,
            lambda_l2=0.1,
            lambda_l3=0.01,
            theta_l1=1.0,
            theta_l2=2.0,
            gating12=0.5,
            gating23=0.3,
            state_L1=[0.0, 0.0, 0.0],
            state_L2=[0.0, 0.0, 0.0],
            state_L3=[0.0, 0.0, 0.0],
        )
        qilm = QILMStateRecord(memory=[], phases=[])

        record = SystemStateRecord(
            version=1,
            memory_state=memory,
            qilm=qilm,
        )
        assert record.version == 1
        assert record.memory_state.dimension == 3

    def test_invalid_empty_id(self):
        """Test that empty string id is invalid."""
        memory = MemoryStateRecord(
            dimension=3,
            lambda_l1=0.5,
            lambda_l2=0.1,
            lambda_l3=0.01,
            theta_l1=1.0,
            theta_l2=2.0,
            gating12=0.5,
            gating23=0.3,
            state_L1=[0.0, 0.0, 0.0],
            state_L2=[0.0, 0.0, 0.0],
            state_L3=[0.0, 0.0, 0.0],
        )
        qilm = QILMStateRecord(memory=[], phases=[])

        with pytest.raises(ValueError, match="empty string"):
            SystemStateRecord(
                version=1,
                id="   ",  # Empty/whitespace id
                memory_state=memory,
                qilm=qilm,
            )

    def test_timestamps_must_be_ordered(self):
        """Test that created_at <= updated_at."""
        memory = MemoryStateRecord(
            dimension=3,
            lambda_l1=0.5,
            lambda_l2=0.1,
            lambda_l3=0.01,
            theta_l1=1.0,
            theta_l2=2.0,
            gating12=0.5,
            gating23=0.3,
            state_L1=[0.0, 0.0, 0.0],
            state_L2=[0.0, 0.0, 0.0],
            state_L3=[0.0, 0.0, 0.0],
        )
        qilm = QILMStateRecord(memory=[], phases=[])

        created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        updated = datetime(2023, 1, 1, tzinfo=timezone.utc)  # Before created!

        with pytest.raises(ValueError, match="created_at.*updated_at"):
            SystemStateRecord(
                version=1,
                created_at=created,
                updated_at=updated,
                memory_state=memory,
                qilm=qilm,
            )


class TestSaveAndLoadState:
    """Tests for save/load operations."""

    def test_save_and_load_json(self):
        """Test saving and loading state as JSON."""
        state = create_empty_system_state(dimension=5)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")

            save_system_state(state, filepath)
            loaded = load_system_state(filepath)

            assert loaded.version == state.version
            assert loaded.memory_state.dimension == 5
            assert len(loaded.memory_state.state_l1) == 5

    def test_read_after_write_consistency(self):
        """Test that loaded state is identical to saved state (logically)."""
        state = create_empty_system_state(dimension=10)

        # Modify state
        state = state.model_copy(
            update={
                "id": "test-state-123",
                "memory_state": state.memory_state.model_copy(
                    update={"state_L1": [float(i) for i in range(10)]}
                ),
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")

            save_system_state(state, filepath)
            loaded = load_system_state(filepath)

            # Verify key fields match
            assert loaded.id == state.id
            assert loaded.version == state.version
            assert loaded.memory_state.dimension == state.memory_state.dimension
            assert loaded.memory_state.state_l1 == state.memory_state.state_l1
            assert loaded.memory_state.lambda_l1 == state.memory_state.lambda_l1

    def test_invalid_filepath_type(self):
        """Test that non-string filepath raises TypeError."""
        state = create_empty_system_state()

        with pytest.raises(TypeError, match="must be a string"):
            save_system_state(state, 123)  # type: ignore

    def test_invalid_filepath_empty(self):
        """Test that empty filepath raises ValueError."""
        state = create_empty_system_state()

        with pytest.raises(ValueError, match="cannot be empty"):
            save_system_state(state, "")

    def test_unsupported_format(self):
        """Test that unsupported file format raises ValueError."""
        state = create_empty_system_state()

        with pytest.raises(ValueError, match="Unsupported file format"):
            save_system_state(state, "/tmp/state.txt")

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file raises StateLoadError."""
        with pytest.raises(StateLoadError, match="not found"):
            load_system_state("/nonexistent/path/state.json")


class TestMigration:
    """Tests for state migration."""

    def test_migrate_legacy_to_v1(self):
        """Test migration from legacy format to v1."""
        legacy_data = {
            "memory_state": {
                "dimension": 3,
                "lambda_l1": 0.5,
                "lambda_l2": 0.1,
                "lambda_l3": 0.01,
                "theta_l1": 1.0,
                "theta_l2": 2.0,
                "gating12": 0.5,
                "gating23": 0.3,
                "state_L1": [0.0, 0.0, 0.0],
                "state_L2": [0.0, 0.0, 0.0],
                "state_L3": [0.0, 0.0, 0.0],
            },
            "qilm": {
                "memory": [],
                "phases": [],
            },
        }

        migrated = migrate_state(legacy_data, 0, 1)

        assert migrated["version"] == 1
        assert "created_at" in migrated
        assert "updated_at" in migrated
        assert migrated["memory_state"]["dimension"] == 3

    def test_create_system_state_from_legacy_dict(self):
        """Test creating SystemStateRecord from legacy format dict."""
        legacy_data = {
            "memory_state": {
                "dimension": 3,
                "lambda_l1": 0.5,
                "lambda_l2": 0.1,
                "lambda_l3": 0.01,
                "theta_l1": 1.0,
                "theta_l2": 2.0,
                "gating12": 0.5,
                "gating23": 0.3,
                "state_L1": [0.0, 0.0, 0.0],
                "state_L2": [0.0, 0.0, 0.0],
                "state_L3": [0.0, 0.0, 0.0],
            },
            "qilm": {
                "memory": [],
                "phases": [],
            },
        }

        record = create_system_state_from_dict(legacy_data)
        assert record.version == CURRENT_SCHEMA_VERSION
        assert record.memory_state.dimension == 3


class TestRecovery:
    """Tests for recovery procedures."""

    def test_recover_from_backup(self):
        """Test recovery from backup when main file is corrupted."""
        state = create_empty_system_state(dimension=5)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")
            backup_path = f"{filepath}.backup"

            # Save valid state (creates backup when overwriting)
            save_system_state(state, filepath)

            # Now overwrite again to create backup
            state2 = create_empty_system_state(dimension=7)
            save_system_state(state2, filepath)

            # Verify backup exists
            assert os.path.exists(backup_path)

            # Corrupt main file
            with open(filepath, "w") as f:
                f.write("corrupted data")

            # Also corrupt checksum
            checksum_path = f"{filepath}.checksum"
            if os.path.exists(checksum_path):
                with open(checksum_path, "w") as f:
                    f.write("invalid_checksum")

            # Recovery should work from backup
            recovered = recover_system_state(filepath)
            assert recovered.memory_state.dimension == 5  # Original dimension

    def test_recovery_no_backup_fails(self):
        """Test recovery fails when no backup exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")

            # Create corrupted file with no backup
            with open(filepath, "w") as f:
                f.write("corrupted data")

            with pytest.raises(StateRecoveryError, match="no backup"):
                recover_system_state(filepath)


class TestIdempotency:
    """Tests for idempotent save operations."""

    def test_idempotent_save(self):
        """Test that repeated saves with same state are idempotent."""
        state = create_empty_system_state(dimension=5)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")

            # Save twice with same id
            save_system_state(state, filepath, state_id="test-123")
            save_system_state(state, filepath, state_id="test-123")

            # Load and verify
            loaded = load_system_state(filepath)
            assert loaded.id == "test-123"
            assert loaded.memory_state.dimension == 5

    def test_backup_created_on_overwrite(self):
        """Test that backup is created when overwriting existing file."""
        state = create_empty_system_state(dimension=5)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")
            backup_path = f"{filepath}.backup"

            # First save (no backup yet)
            save_system_state(state, filepath)
            assert not os.path.exists(backup_path)

            # Second save (backup should be created)
            state2 = create_empty_system_state(dimension=7)
            save_system_state(state2, filepath)
            assert os.path.exists(backup_path)

            # Verify backup contains original state
            with open(backup_path) as f:
                backup_data = json.load(f)
            assert backup_data["memory_state"]["dimension"] == 5


class TestValidateStateIntegrity:
    """Tests for integrity validation."""

    def test_valid_state_no_warnings(self):
        """Test that valid state produces no warnings."""
        state = create_empty_system_state(dimension=10)
        warnings = validate_state_integrity(state)
        assert len(warnings) == 0

    def test_large_values_produce_warnings(self):
        """Test that very large state values produce warnings."""
        memory = MemoryStateRecord(
            dimension=3,
            lambda_l1=0.5,
            lambda_l2=0.1,
            lambda_l3=0.01,
            theta_l1=1.0,
            theta_l2=2.0,
            gating12=0.5,
            gating23=0.3,
            state_L1=[1e11, 0.0, 0.0],  # Very large value
            state_L2=[0.0, 0.0, 0.0],
            state_L3=[0.0, 0.0, 0.0],
        )
        qilm = QILMStateRecord(memory=[], phases=[])
        state = SystemStateRecord(
            version=1,
            memory_state=memory,
            qilm=qilm,
        )

        warnings = validate_state_integrity(state)
        assert len(warnings) > 0
        assert any("very large" in w for w in warnings)


class TestDeleteState:
    """Tests for delete operations."""

    def test_delete_state_file(self):
        """Test deleting state file."""
        state = create_empty_system_state()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")

            save_system_state(state, filepath)
            assert os.path.exists(filepath)

            delete_system_state(filepath)
            assert not os.path.exists(filepath)

    def test_delete_with_backup(self):
        """Test deleting state file and backup."""
        state = create_empty_system_state()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")
            backup_path = f"{filepath}.backup"

            # Create backup
            save_system_state(state, filepath)
            save_system_state(state, filepath)  # Creates backup
            assert os.path.exists(backup_path)

            delete_system_state(filepath, delete_backup=True)
            assert not os.path.exists(filepath)
            assert not os.path.exists(backup_path)


class TestChecksumVerification:
    """Tests for checksum-based corruption detection."""

    def test_checksum_created_on_save(self):
        """Test that checksum file is created when saving JSON."""
        state = create_empty_system_state()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")
            checksum_path = f"{filepath}.checksum"

            save_system_state(state, filepath)
            assert os.path.exists(checksum_path)

    def test_corruption_detected_on_load(self):
        """Test that file corruption is detected via checksum."""
        state = create_empty_system_state()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")

            save_system_state(state, filepath)

            # Corrupt the file
            with open(filepath, "a") as f:
                f.write(" extra data")

            with pytest.raises(StateCorruptionError, match="Checksum mismatch"):
                load_system_state(filepath, verify_checksum=True)

    def test_load_without_checksum_verification(self):
        """Test loading without checksum verification."""
        state = create_empty_system_state()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "state.json")

            save_system_state(state, filepath)

            # Corrupt the file
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            data["extra"] = "field"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f)

            # Should load without error when verification disabled
            loaded = load_system_state(filepath, verify_checksum=False)
            assert loaded.version == state.version


class TestCreateEmptyState:
    """Tests for creating empty state."""

    def test_create_empty_state_defaults(self):
        """Test creating empty state with defaults."""
        state = create_empty_system_state()
        assert state.version == CURRENT_SCHEMA_VERSION
        assert state.memory_state.dimension == 10
        assert all(v == 0.0 for v in state.memory_state.state_l1)

    def test_create_empty_state_custom(self):
        """Test creating empty state with custom parameters."""
        state = create_empty_system_state(
            dimension=20,
            lambda_l1=0.3,
            theta_l1=1.5,
        )
        assert state.memory_state.dimension == 20
        assert state.memory_state.lambda_l1 == 0.3
        assert state.memory_state.theta_l1 == 1.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
