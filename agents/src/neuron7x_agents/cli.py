"""CLI entry point for neuron7x-agents."""

from __future__ import annotations


def main() -> None:
    """Entry point for n7x-agents CLI."""


def _version() -> str:
    from neuron7x_agents import __version__

    return __version__


if __name__ == "__main__":
    main()
