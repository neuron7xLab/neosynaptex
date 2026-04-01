"""
Integration tests for the MLSDM CLI.

Tests the CLI commands: demo, serve, check
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def _cli_env(repo_root: os.PathLike[str]) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{Path(repo_root) / 'src'}:{env.get('PYTHONPATH', '')}".rstrip(":")
    return env


class TestCLICheck:
    """Test the 'mlsdm check' command."""

    def test_check_command_runs(self):
        """Test that check command runs without error."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "check"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "MLSDM Environment Check" in result.stdout

    def test_check_shows_version(self):
        """Test that check shows mlsdm version."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "check"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=30,
        )
        assert "mlsdm v" in result.stdout

    def test_check_validates_python_version(self):
        """Test that check validates Python version."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "check"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=30,
        )
        assert "Python version" in result.stdout

    def test_check_verbose_flag(self):
        """Test verbose flag outputs more info."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "check", "--verbose"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        # Verbose mode should show full status JSON
        assert "checks" in result.stdout


class TestCLIDemo:
    """Test the 'mlsdm demo' command."""

    def test_demo_with_prompt(self):
        """Test demo with single prompt."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "demo", "-p", "Hello world"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "MLSDM Demo" in result.stdout
        assert "Prompt: Hello world" in result.stdout

    def test_demo_without_prompt_runs_demo(self):
        """Test demo without prompt runs demo prompts."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "demo"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "Running demo prompts" in result.stdout

    def test_demo_verbose_output(self):
        """Test demo verbose mode."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "demo", "-p", "Test", "--verbose"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "Full result" in result.stdout

    def test_demo_custom_moral_value(self):
        """Test demo with custom moral value."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "demo", "-p", "Test", "-m", "0.9"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "Moral Value: 0.9" in result.stdout

    def test_demo_low_moral_rejected(self):
        """Test demo with low moral value gets rejected."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mlsdm.cli",
                "demo",
                "-p",
                "Test",
                "-m",
                "0.1",  # Very low moral value
                "--moral-threshold",
                "0.9",  # High threshold
            ],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "Rejected" in result.stdout


class TestCLIVersion:
    """Test version flag."""

    def test_version_flag(self):
        """Test --version flag."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "--version"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "1.2.0" in result.stdout


class TestCLIHelp:
    """Test help output."""

    def test_help_flag(self):
        """Test --help flag."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "--help"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "demo" in result.stdout
        assert "serve" in result.stdout
        assert "check" in result.stdout

    def test_demo_help(self):
        """Test demo --help."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "demo", "--help"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "--prompt" in result.stdout
        assert "--interactive" in result.stdout

    def test_serve_help(self):
        """Test serve --help."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "serve", "--help"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "--host" in result.stdout
        assert "--port" in result.stdout

    def test_check_help(self):
        """Test check --help."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "check", "--help"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "--verbose" in result.stdout


class TestCLIModule:
    """Test CLI module can be imported and run directly."""

    def test_import_cli_module(self):
        """Test that CLI module can be imported."""
        from mlsdm import cli

        assert hasattr(cli, "main")
        assert callable(cli.main)

    def test_main_with_no_args(self):
        """Test main() with no arguments shows help."""
        from mlsdm.cli import main

        with patch("sys.argv", ["mlsdm"]):
            # Should print help and return 0
            result = main()
            assert result == 0


class TestCLIServe:
    """Test 'mlsdm serve' command (without actually starting server)."""

    def test_serve_help(self):
        """Test serve shows help with correct options."""
        repo_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "mlsdm.cli", "serve", "--help"],
            capture_output=True,
            cwd=repo_root,
            env=_cli_env(repo_root),
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "--host" in result.stdout
        assert "--port" in result.stdout
        assert "--backend" in result.stdout
        assert "--config" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
