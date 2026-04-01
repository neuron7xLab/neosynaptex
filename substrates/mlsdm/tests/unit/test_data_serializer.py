"""
Unit Tests for Data Serializer

Tests data serialization to JSON and NPZ formats.
"""

import json
import os
import tempfile

import numpy as np
import pytest

from mlsdm.utils.data_serializer import DataSerializer


class TestDataSerializerJSON:
    """Test JSON serialization."""

    def test_save_json(self):
        """Test saving data to JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            data = {"key": "value", "number": 42, "list": [1, 2, 3]}
            DataSerializer.save(data, filepath)

            assert os.path.exists(filepath)

            # Verify content
            with open(filepath) as f:
                loaded = json.load(f)

            assert loaded == data
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_load_json(self):
        """Test loading data from JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name
            data = {"test": "data", "value": 123}
            json.dump(data, f)

        try:
            loaded = DataSerializer.load(filepath)
            assert loaded == data
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_save_load_roundtrip_json(self):
        """Test save and load roundtrip for JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            data = {
                "string": "hello",
                "integer": 42,
                "float": 3.14,
                "list": [1, 2, 3],
                "nested": {"a": 1, "b": 2},
            }

            DataSerializer.save(data, filepath)
            loaded = DataSerializer.load(filepath)

            assert loaded == data
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_save_json_creates_parent_dirs(self, tmp_path):
        """Saving should create missing parent directories for JSON."""
        filepath = tmp_path / "nested" / "state" / "snapshot.json"
        data = {"status": "ok"}

        DataSerializer.save(data, str(filepath))

        assert filepath.exists()
        assert json.loads(filepath.read_text()) == data


class TestDataSerializerNPZ:
    """Test NPZ (NumPy) serialization."""

    def test_save_npz(self):
        """Test saving data to NPZ file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".npz", delete=False) as f:
            filepath = f.name

        try:
            data = {"array1": [1, 2, 3], "array2": [[4, 5], [6, 7]]}

            DataSerializer.save(data, filepath)

            assert os.path.exists(filepath)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_load_npz(self):
        """Test loading data from NPZ file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".npz", delete=False) as f:
            filepath = f.name

        try:
            data = {"arr1": np.array([1, 2, 3]), "arr2": np.array([4, 5, 6])}
            np.savez(filepath, **data)

            loaded = DataSerializer.load(filepath)

            assert "arr1" in loaded
            assert "arr2" in loaded
            assert loaded["arr1"] == [1, 2, 3]
            assert loaded["arr2"] == [4, 5, 6]
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_save_load_roundtrip_npz(self):
        """Test save and load roundtrip for NPZ."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".npz", delete=False) as f:
            filepath = f.name

        try:
            data = {"vector": [1.0, 2.0, 3.0], "matrix": [[1, 2], [3, 4]]}

            DataSerializer.save(data, filepath)
            loaded = DataSerializer.load(filepath)

            assert "vector" in loaded
            assert "matrix" in loaded
            # Compare as lists since NPZ converts to numpy
            assert loaded["vector"] == [1.0, 2.0, 3.0]
            assert loaded["matrix"] == [[1, 2], [3, 4]]
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_save_npz_creates_parent_dirs(self, tmp_path):
        """Saving NPZ should create missing parent directories."""
        filepath = tmp_path / "nested" / "state" / "snapshot.npz"
        data = {"array": np.array([1, 2, 3])}

        DataSerializer.save(data, str(filepath))
        loaded = DataSerializer.load(str(filepath))

        assert filepath.exists()
        assert loaded["array"] == [1, 2, 3]


class TestDataSerializerErrors:
    """Test error handling."""

    def test_save_unsupported_format(self):
        """Test saving to unsupported format raises error."""
        from tenacity import RetryError

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            filepath = f.name

        try:
            data = {"key": "value"}

            # tenacity wraps the error in RetryError
            with pytest.raises((ValueError, RetryError)):
                DataSerializer.save(data, filepath)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_load_unsupported_format(self):
        """Test loading from unsupported format raises error."""
        from tenacity import RetryError

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            filepath = f.name
            f.write("test content")

        try:
            # tenacity wraps the error in RetryError
            with pytest.raises((ValueError, RetryError)):
                DataSerializer.load(filepath)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_save_invalid_filepath_type(self):
        """Test saving with invalid filepath type."""
        data = {"key": "value"}

        with pytest.raises(TypeError, match="Filepath must be a string"):
            DataSerializer.save(data, 123)

    def test_load_invalid_filepath_type(self):
        """Test loading with invalid filepath type."""
        with pytest.raises(TypeError, match="Filepath must be a string"):
            DataSerializer.load(123)

    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises error."""
        from tenacity import RetryError

        filepath = "/tmp/nonexistent_file_12345.json"

        # tenacity wraps the error in RetryError
        with pytest.raises((FileNotFoundError, RetryError)):
            DataSerializer.load(filepath)


class TestDataSerializerEdgeCases:
    """Test edge cases."""

    def test_save_empty_dict(self):
        """Test saving empty dictionary."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            data = {}
            DataSerializer.save(data, filepath)
            loaded = DataSerializer.load(filepath)

            assert loaded == data
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_save_nested_structure(self):
        """Test saving deeply nested structure."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            data = {"level1": {"level2": {"level3": {"value": 42}}}}

            DataSerializer.save(data, filepath)
            loaded = DataSerializer.load(filepath)

            assert loaded == data
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_save_large_array_npz(self):
        """Test saving large array to NPZ."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".npz", delete=False) as f:
            filepath = f.name

        try:
            large_array = list(range(10000))
            data = {"large": large_array}

            DataSerializer.save(data, filepath)
            loaded = DataSerializer.load(filepath)

            assert loaded["large"] == large_array
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
