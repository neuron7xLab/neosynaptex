"""Tests for CLI entry point."""

from __future__ import annotations

from neuron7x_agents.cli import main


class TestCLI:
    def test_main_runs(self, capsys: object) -> None:
        main()
        # CLI should print version and module list without error
