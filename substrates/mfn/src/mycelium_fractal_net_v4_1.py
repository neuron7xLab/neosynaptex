"""Backward-compatible module wrapper for legacy CLI imports."""

from mycelium_fractal_net.cli import main as cli_main
from mycelium_fractal_net.model import run_validation_cli

__all__ = ["cli_main", "run_validation_cli"]

if __name__ == "__main__":
    cli_main()
