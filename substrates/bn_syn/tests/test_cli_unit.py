"""Unit tests for CLI commands to improve coverage.

Parameters
----------
None

Returns
-------
None

Notes
-----
Direct unit tests for CLI command functions.

References
----------
docs/sleep_stack.md
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from bnsyn.cli import _cmd_demo, _cmd_dtcheck, _cmd_sleep_stack


def test_cmd_demo_direct() -> None:
    """Test _cmd_demo function directly."""
    args = argparse.Namespace(
        steps=50,
        dt_ms=0.1,
        seed=42,
        N=40,
    )
    result = _cmd_demo(args)
    assert result == 0


def test_cmd_dtcheck_direct() -> None:
    """Test _cmd_dtcheck function directly."""
    args = argparse.Namespace(
        steps=50,
        dt_ms=0.1,
        dt2_ms=0.05,
        seed=42,
        N=40,
    )
    result = _cmd_dtcheck(args)
    assert result == 0


def test_cmd_sleep_stack_direct() -> None:
    """Test _cmd_sleep_stack function directly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "test_output"

        args = argparse.Namespace(
            seed=123,
            N=64,
            backend="reference",
            steps_wake=50,
            steps_sleep=50,
            out=str(out_dir),
        )

        result = _cmd_sleep_stack(args)
        assert result == 0

        # Verify outputs
        manifest_path = out_dir / "manifest.json"
        metrics_path = out_dir / "metrics.json"

        assert manifest_path.exists()
        assert metrics_path.exists()

        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest["seed"] == 123
        assert manifest["steps_wake"] == 50

        with open(metrics_path) as f:
            metrics = json.load(f)
        assert "wake" in metrics
        assert "sleep" in metrics
        assert "transitions" in metrics
        assert "attractors" in metrics
        assert "consolidation" in metrics


def test_cmd_sleep_stack_with_custom_sleep_duration() -> None:
    """Test _cmd_sleep_stack with non-default sleep duration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "test_output2"

        args = argparse.Namespace(
            seed=456,
            N=64,
            backend="reference",
            steps_wake=30,
            steps_sleep=300,  # Different from default 600
            out=str(out_dir),
        )

        result = _cmd_sleep_stack(args)
        assert result == 0

        # Verify that manifest records the correct steps
        manifest_path = out_dir / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest["steps_sleep"] == 300
