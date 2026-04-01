"""
Unit tests for async utilities module.
"""

import asyncio
import os
from unittest.mock import patch

import pytest
from async_utils import (
    calculate_timeout,
    get_timeout_multiplier,
    graceful_cancel_tasks,
    is_ci_environment,
)


class TestCIDetection:
    """Tests for CI environment detection."""

    def test_github_actions_detection(self):
        """Test detection of GitHub Actions environment."""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            assert is_ci_environment() is True

    def test_gitlab_ci_detection(self):
        """Test detection of GitLab CI environment."""
        with patch.dict(os.environ, {"GITLAB_CI": "true"}):
            assert is_ci_environment() is True

    def test_jenkins_url_detection(self):
        """Test detection of Jenkins CI environment with URL."""
        with patch.dict(os.environ, {"JENKINS_URL": "http://jenkins.example.com"}):
            assert is_ci_environment() is True

    def test_ci_generic_detection(self):
        """Test detection with generic CI variable."""
        with patch.dict(os.environ, {"CI": "1"}):
            assert is_ci_environment() is True

    def test_no_ci_environment(self):
        """Test no CI environment detected."""
        # Clear all CI env vars using patch.dict for safety
        with patch.dict(
            os.environ,
            {},
            clear=False,
        ):
            # Remove CI vars explicitly
            for key in ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI", "TRAVIS", "JENKINS_URL"]:
                os.environ.pop(key, None)
            assert is_ci_environment() is False

    def test_false_ci_environment(self):
        """Test CI variable set to false is not detected."""
        # Use patch.dict for safe environment isolation
        with patch.dict(
            os.environ,
            {"CI": "false"},
            clear=False,
        ):
            # Remove other CI vars
            for key in ["GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI", "TRAVIS", "JENKINS_URL"]:
                os.environ.pop(key, None)
            assert is_ci_environment() is False

    def test_zero_ci_environment(self):
        """Test CI variable set to 0 is not detected."""
        # Use patch.dict for safe environment isolation
        with patch.dict(
            os.environ,
            {"CI": "0"},
            clear=False,
        ):
            # Remove other CI vars
            for key in ["GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI", "TRAVIS", "JENKINS_URL"]:
                os.environ.pop(key, None)
            assert is_ci_environment() is False


class TestTimeoutCalculation:
    """Tests for timeout calculation."""

    def test_get_timeout_multiplier_ci(self):
        """Test timeout multiplier in CI environment."""
        with patch.dict(os.environ, {"CI": "true"}):
            assert get_timeout_multiplier() == 1.5

    def test_get_timeout_multiplier_local(self):
        """Test timeout multiplier in local environment."""
        # Use patch.dict for safe environment isolation
        with patch.dict(os.environ, {}, clear=False):
            # Remove CI vars explicitly
            for key in ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI", "TRAVIS", "JENKINS_URL"]:
                os.environ.pop(key, None)
            assert get_timeout_multiplier() == 1.0

    def test_calculate_timeout_local(self):
        """Test timeout calculation in local environment."""
        # Use patch.dict for safe environment isolation
        with patch.dict(os.environ, {}, clear=False):
            # Remove CI vars explicitly
            for key in ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI", "TRAVIS", "JENKINS_URL"]:
                os.environ.pop(key, None)
            assert calculate_timeout(10.0) == 10.0

    def test_calculate_timeout_ci_detected(self):
        """Test timeout calculation with CI environment detected."""
        with patch.dict(os.environ, {"CI": "true"}):
            assert calculate_timeout(10.0) == 15.0

    def test_calculate_timeout_ci_mode_explicit(self):
        """Test timeout calculation with explicit CI mode."""
        # Use patch.dict for safe environment isolation
        with patch.dict(os.environ, {}, clear=False):
            # Remove CI vars explicitly
            for key in ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI", "TRAVIS", "JENKINS_URL"]:
                os.environ.pop(key, None)
            assert calculate_timeout(10.0, ci_mode=True) == 15.0


@pytest.mark.asyncio
async def test_graceful_cancel_tasks():
    """Test graceful task cancellation."""

    async def sample_task():
        """Sample async task."""
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(0.1)  # Simulate cleanup
            raise

    # Create tasks
    tasks = [asyncio.create_task(sample_task()) for _ in range(3)]

    # Give tasks a moment to start
    await asyncio.sleep(0.1)

    # Cancel them gracefully
    await graceful_cancel_tasks(tasks, timeout=2.0)

    # All tasks should be cancelled
    for task in tasks:
        assert task.done()
        assert task.cancelled()


@pytest.mark.asyncio
async def test_graceful_cancel_tasks_timeout():
    """Test graceful task cancellation with timeout."""

    async def slow_task():
        """Task that takes too long to cancel."""
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(10)  # Simulate slow cleanup
            raise

    # Create tasks
    tasks = [asyncio.create_task(slow_task()) for _ in range(2)]

    # Give tasks a moment to start
    await asyncio.sleep(0.1)

    # Cancel them gracefully with short timeout
    # This should log a warning but not raise
    await graceful_cancel_tasks(tasks, timeout=0.5)

    # Tasks should be cancelled but may not be done
    for task in tasks:
        if not task.done():
            task.cancel()  # Force cancel for cleanup
