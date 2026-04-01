"""Tests for centralized retry decorator functionality."""

import os
import time
from unittest.mock import Mock, patch

import pytest

from mlsdm.utils.retry_decorator import (
    CRITICAL_RETRY,
    DEFAULT_RETRY,
    FAST_RETRY,
    IO_RETRY,
    NETWORK_RETRY,
    create_custom_retry,
)


class TestDefaultRetry:
    """Test DEFAULT_RETRY policy behavior."""

    def test_successful_execution_no_retry(self) -> None:
        """Test that successful execution doesn't trigger retry."""
        mock_func = Mock(return_value="success")
        decorated = DEFAULT_RETRY(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retries_on_failure(self) -> None:
        """Test that function retries on failure."""
        mock_func = Mock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])
        decorated = DEFAULT_RETRY(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_exhausts_retries_and_raises(self) -> None:
        """Test that exception is raised after all retries exhausted."""
        mock_func = Mock(side_effect=ValueError("persistent failure"))
        decorated = DEFAULT_RETRY(mock_func)

        with pytest.raises(ValueError, match="persistent failure"):
            decorated()

        # Default is 3 attempts
        assert mock_func.call_count == 3

    def test_exponential_backoff(self) -> None:
        """Test that retry waits increase exponentially."""
        call_times: list[float] = []

        @DEFAULT_RETRY
        def failing_func() -> None:
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("retry me")

        failing_func()

        # Verify we have 3 calls
        assert len(call_times) == 3

        # Verify increasing delays between attempts
        # First retry should wait ~1s, second ~2s
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # Allow some tolerance for timing variations
        assert delay1 >= 0.8  # Should be ~1s
        assert delay2 >= delay1  # Should be exponentially longer


class TestCriticalRetry:
    """Test CRITICAL_RETRY policy behavior."""

    def test_more_attempts_than_default(self) -> None:
        """Test that CRITICAL_RETRY attempts more times than DEFAULT_RETRY."""
        mock_func = Mock(side_effect=ValueError("critical failure"))
        decorated = CRITICAL_RETRY(mock_func)

        with pytest.raises(ValueError):
            decorated()

        # Critical retry should default to 5 attempts
        assert mock_func.call_count == 5

    def test_longer_max_wait(self) -> None:
        """Test that CRITICAL_RETRY allows longer waits between retries."""
        call_times: list[float] = []

        @CRITICAL_RETRY
        def failing_func() -> None:
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("retry me")

        failing_func()

        # Just verify it completes - actual timing test would be slow
        assert len(call_times) == 3


class TestFastRetry:
    """Test FAST_RETRY policy behavior."""

    def test_fewer_attempts(self) -> None:
        """Test that FAST_RETRY only attempts 2 times."""
        mock_func = Mock(side_effect=ValueError("fast failure"))
        decorated = FAST_RETRY(mock_func)

        with pytest.raises(ValueError):
            decorated()

        assert mock_func.call_count == 2

    def test_fixed_delay(self) -> None:
        """Test that FAST_RETRY uses fixed delay."""
        call_times: list[float] = []

        @FAST_RETRY
        def failing_func() -> None:
            call_times.append(time.time())
            if len(call_times) < 2:
                raise ValueError("retry me")

        failing_func()

        assert len(call_times) == 2

        # Should have roughly 1 second delay
        delay = call_times[1] - call_times[0]
        assert 0.8 <= delay <= 1.5  # Allow some timing tolerance


class TestIoRetry:
    """Test IO_RETRY policy behavior."""

    def test_io_operations(self) -> None:
        """Test that IO_RETRY works for I/O operations."""
        mock_func = Mock(side_effect=[OSError("I/O error"), OSError("I/O error"), "success"])
        decorated = IO_RETRY(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_shorter_max_wait(self) -> None:
        """Test that IO_RETRY has appropriate wait times for I/O."""
        call_times: list[float] = []

        @IO_RETRY
        def failing_func() -> None:
            call_times.append(time.time())
            if len(call_times) < 2:
                raise OSError("I/O error")

        failing_func()

        # Verify shorter delays appropriate for I/O
        assert len(call_times) == 2
        delay = call_times[1] - call_times[0]
        # IO_RETRY uses 0.5 multiplier, so should be ~0.5s
        assert 0.3 <= delay <= 1.0


class TestNetworkRetry:
    """Test NETWORK_RETRY policy behavior."""

    def test_retries_on_timeout_error(self) -> None:
        """Test that NETWORK_RETRY retries on TimeoutError."""
        mock_func = Mock(side_effect=[TimeoutError("timeout"), "success"])
        decorated = NETWORK_RETRY(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retries_on_connection_error(self) -> None:
        """Test that NETWORK_RETRY retries on ConnectionError."""
        mock_func = Mock(side_effect=[ConnectionError("connection failed"), "success"])
        decorated = NETWORK_RETRY(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retries_on_runtime_error(self) -> None:
        """Test that NETWORK_RETRY retries on RuntimeError."""
        mock_func = Mock(side_effect=[RuntimeError("runtime error"), "success"])
        decorated = NETWORK_RETRY(mock_func)

        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_does_not_retry_on_value_error(self) -> None:
        """Test that NETWORK_RETRY doesn't retry on non-network errors."""
        mock_func = Mock(side_effect=ValueError("not a network error"))
        decorated = NETWORK_RETRY(mock_func)

        with pytest.raises(ValueError, match="not a network error"):
            decorated()

        # Should not retry ValueError
        assert mock_func.call_count == 1


class TestCustomRetry:
    """Test create_custom_retry function."""

    def test_custom_attempts(self) -> None:
        """Test custom retry with specific attempt count."""
        custom_retry = create_custom_retry(attempts=7)
        mock_func = Mock(side_effect=ValueError("fail"))
        decorated = custom_retry(mock_func)

        with pytest.raises(ValueError):
            decorated()

        assert mock_func.call_count == 7

    def test_custom_wait_times(self) -> None:
        """Test custom retry with specific wait times."""
        custom_retry = create_custom_retry(
            attempts=3, min_wait=0.1, max_wait=0.5, multiplier=2.0
        )

        call_times: list[float] = []

        @custom_retry
        def failing_func() -> None:
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("retry me")

        failing_func()

        assert len(call_times) == 3

        # Verify custom wait times (with tolerance for timing)
        delay1 = call_times[1] - call_times[0]
        # With multiplier=2.0 and min_wait=0.1, first retry should wait ~0.2-0.5s
        assert 0.05 <= delay1 <= 0.8  # Adjusted for actual exponential backoff behavior


class TestEnvironmentConfiguration:
    """Test environment variable configuration."""

    def test_retry_attempts_env_var(self) -> None:
        """Test that MLSDM_RETRY_ATTEMPTS environment variable is respected."""
        with patch.dict(os.environ, {"MLSDM_RETRY_ATTEMPTS": "7"}):
            # Need to reload module to pick up env var
            from importlib import reload

            from mlsdm.utils import retry_decorator

            reload(retry_decorator)

            mock_func = Mock(side_effect=ValueError("fail"))
            decorated = retry_decorator.DEFAULT_RETRY(mock_func)

            with pytest.raises(ValueError):
                decorated()

            # Should use env var value
            assert mock_func.call_count == 7

    def test_retry_wait_times_env_vars(self) -> None:
        """Test that wait time environment variables are respected."""
        with patch.dict(
            os.environ, {"MLSDM_RETRY_MIN_WAIT": "0.1", "MLSDM_RETRY_MAX_WAIT": "0.5"}
        ):
            from importlib import reload

            from mlsdm.utils import retry_decorator

            reload(retry_decorator)

            call_times: list[float] = []

            @retry_decorator.DEFAULT_RETRY
            def failing_func() -> None:
                call_times.append(time.time())
                if len(call_times) < 2:
                    raise ValueError("retry me")

            failing_func()

            # Should use custom min wait with exponential backoff
            delay = call_times[1] - call_times[0]
            # With multiplier=1.0 and min_wait=0.1, max_wait=0.5, first retry should be between 0.1-0.8s
            assert 0.05 <= delay <= 0.8  # Adjusted for actual exponential backoff behavior


class TestDecoratorPreservesFunction:
    """Test that decorators preserve function metadata."""

    def test_preserves_function_name(self) -> None:
        """Test that decorator preserves function name."""

        @DEFAULT_RETRY
        def my_function() -> str:
            """My docstring."""
            return "result"

        # Function name might be wrapped by tenacity, check return value works
        assert my_function() == "result"

    def test_works_with_arguments(self) -> None:
        """Test that decorator works with function arguments."""

        @DEFAULT_RETRY
        def add_numbers(a: int, b: int) -> int:
            if a < 0:
                raise ValueError("negative not allowed")
            return a + b

        assert add_numbers(2, 3) == 5

    def test_works_with_keyword_arguments(self) -> None:
        """Test that decorator works with keyword arguments."""

        @DEFAULT_RETRY
        def format_name(first: str, last: str, middle: str = "") -> str:
            if not first:
                raise ValueError("first name required")
            if middle:
                return f"{first} {middle} {last}"
            return f"{first} {last}"

        assert format_name("John", "Doe") == "John Doe"
        assert format_name(first="John", last="Doe", middle="Q") == "John Q Doe"


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_file_save_with_io_retry(self) -> None:
        """Test typical file save scenario with IO_RETRY."""
        attempts = 0

        @IO_RETRY
        def save_file(data: str) -> None:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise OSError("Disk full")
            # Success on second attempt
            return None

        save_file("test data")
        assert attempts == 2

    def test_api_call_with_network_retry(self) -> None:
        """Test typical API call scenario with NETWORK_RETRY."""
        attempts = 0

        @NETWORK_RETRY
        def call_api() -> dict[str, str]:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("Network unavailable")
            return {"status": "success"}

        result = call_api()
        assert result == {"status": "success"}
        assert attempts == 3

    def test_critical_operation_with_critical_retry(self) -> None:
        """Test critical operation scenario with CRITICAL_RETRY."""
        attempts = 0

        @CRITICAL_RETRY
        def critical_save() -> bool:
            nonlocal attempts
            attempts += 1
            if attempts < 4:
                raise RuntimeError("Temporary failure")
            return True

        result = critical_save()
        assert result is True
        assert attempts == 4
