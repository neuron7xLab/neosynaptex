"""Unit tests for CLI main entrypoint (src/mlsdm/cli/main.py).

These tests cover:
- JSONFormatter logging behavior (pure unit)
- main() execution path with mocked dependencies

All tests are hermetic with no runtime side effects.
No network, no filesystem writes beyond tmp.
"""

from __future__ import annotations

import json
import logging
from unittest import mock

import pytest


class TestJSONFormatter:
    """Unit tests for JSONFormatter class."""

    def test_json_formatter_basic_format(self):
        """Test that JSONFormatter produces valid JSON output."""
        from mlsdm.cli.main import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"

        result = formatter.format(record)

        # Verify it's valid JSON
        parsed = json.loads(result)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert parsed["module"] == "test_module"
        assert "timestamp" in parsed

    def test_json_formatter_with_args(self):
        """Test JSONFormatter with message arguments."""
        from mlsdm.cli.main import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="/test/path.py",
            lineno=20,
            msg="Value is %d",
            args=(42,),
            exc_info=None,
        )
        record.module = "test_module"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "WARNING"
        assert parsed["message"] == "Value is 42"

    def test_json_formatter_error_level(self):
        """Test JSONFormatter with ERROR level."""
        from mlsdm.cli.main import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=30,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )
        record.module = "error_module"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "ERROR"
        assert parsed["message"] == "Error occurred"
        assert parsed["module"] == "error_module"

    def test_json_formatter_debug_level(self):
        """Test JSONFormatter with DEBUG level."""
        from mlsdm.cli.main import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="/test/path.py",
            lineno=5,
            msg="Debug info",
            args=(),
            exc_info=None,
        )
        record.module = "debug_module"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "DEBUG"
        assert parsed["message"] == "Debug info"

    def test_json_formatter_timestamp_present(self):
        """Test that JSONFormatter includes timestamp."""
        from mlsdm.cli.main import JSONFormatter

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=1,
            msg="Message",
            args=(),
            exc_info=None,
        )
        record.module = "module"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert "timestamp" in parsed
        assert parsed["timestamp"] is not None


class TestMainFunction:
    """Tests for main() function with mocked dependencies."""

    def test_main_executes_with_mocked_dependencies(self):
        """Test that main() can execute with fully mocked dependencies."""
        from mlsdm.cli import main as cli_main_module

        # Create mock objects
        mock_config = mock.MagicMock()
        mock_manager = mock.MagicMock()

        with (
            mock.patch.object(
                cli_main_module, "ConfigLoader", autospec=True
            ) as mock_config_loader,
            mock.patch.object(
                cli_main_module, "MemoryManager", autospec=True
            ) as mock_memory_manager,
            mock.patch("sys.argv", ["mlsdm", "--config", "test.yaml", "--steps", "10"]),
        ):
            mock_config_loader.load_config.return_value = mock_config
            mock_memory_manager.return_value = mock_manager

            # Should execute without error
            cli_main_module.main()

            # Verify calls were made
            mock_config_loader.load_config.assert_called_once_with("test.yaml")
            mock_memory_manager.assert_called_once_with(mock_config)
            mock_manager.run_simulation.assert_called_once_with(10)

    def test_main_default_config_path(self):
        """Test main() uses default config path when not specified."""
        from mlsdm.cli import main as cli_main_module

        mock_config = mock.MagicMock()
        mock_manager = mock.MagicMock()

        with (
            mock.patch.object(
                cli_main_module, "ConfigLoader", autospec=True
            ) as mock_config_loader,
            mock.patch.object(
                cli_main_module, "MemoryManager", autospec=True
            ) as mock_memory_manager,
            mock.patch("sys.argv", ["mlsdm"]),
        ):
            mock_config_loader.load_config.return_value = mock_config
            mock_memory_manager.return_value = mock_manager

            cli_main_module.main()

            # Default config path should be used
            mock_config_loader.load_config.assert_called_once_with(
                "config/default_config.yaml"
            )

    def test_main_default_steps(self):
        """Test main() uses default steps when not specified."""
        from mlsdm.cli import main as cli_main_module

        mock_config = mock.MagicMock()
        mock_manager = mock.MagicMock()

        with (
            mock.patch.object(
                cli_main_module, "ConfigLoader", autospec=True
            ) as mock_config_loader,
            mock.patch.object(
                cli_main_module, "MemoryManager", autospec=True
            ) as mock_memory_manager,
            mock.patch("sys.argv", ["mlsdm"]),
        ):
            mock_config_loader.load_config.return_value = mock_config
            mock_memory_manager.return_value = mock_manager

            cli_main_module.main()

            # Default steps (100) should be used
            mock_manager.run_simulation.assert_called_once_with(100)

    def test_main_custom_steps(self):
        """Test main() accepts custom steps value."""
        from mlsdm.cli import main as cli_main_module

        mock_config = mock.MagicMock()
        mock_manager = mock.MagicMock()

        with (
            mock.patch.object(
                cli_main_module, "ConfigLoader", autospec=True
            ) as mock_config_loader,
            mock.patch.object(
                cli_main_module, "MemoryManager", autospec=True
            ) as mock_memory_manager,
            mock.patch("sys.argv", ["mlsdm", "--steps", "500"]),
        ):
            mock_config_loader.load_config.return_value = mock_config
            mock_memory_manager.return_value = mock_manager

            cli_main_module.main()

            mock_manager.run_simulation.assert_called_once_with(500)

    def test_main_logs_messages(self):
        """Test main() logs appropriate messages."""
        from mlsdm.cli import main as cli_main_module

        mock_config = mock.MagicMock()
        mock_manager = mock.MagicMock()

        with (
            mock.patch.object(
                cli_main_module, "ConfigLoader", autospec=True
            ) as mock_config_loader,
            mock.patch.object(
                cli_main_module, "MemoryManager", autospec=True
            ) as mock_memory_manager,
            mock.patch.object(cli_main_module, "logger") as mock_logger,
            mock.patch("sys.argv", ["mlsdm"]),
        ):
            mock_config_loader.load_config.return_value = mock_config
            mock_memory_manager.return_value = mock_manager

            cli_main_module.main()

            # Verify logging calls
            mock_logger.info.assert_any_call("Running simulation...")
            mock_logger.info.assert_any_call("Done.")


class TestModuleLevelSetup:
    """Tests for module-level setup (handler, formatter)."""

    def test_module_has_handler_configured(self):
        """Test that the module sets up a StreamHandler."""
        from mlsdm.cli.main import handler

        assert isinstance(handler, logging.StreamHandler)

    def test_module_has_json_formatter(self):
        """Test that the handler uses JSONFormatter."""
        from mlsdm.cli.main import JSONFormatter, handler

        assert isinstance(handler.formatter, JSONFormatter)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
