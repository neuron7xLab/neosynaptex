"""Data-only package — ships the canonical γ-ledger and proof-chain
artifacts alongside :mod:`core.gamma_registry` so that wheel installs
carry the evidence required at import time.

This package is intentionally empty of Python code. Its sole purpose is
to make the top-level ``evidence/`` directory discoverable by
``setuptools.packages.find`` so that the JSON / text / JSONL artifacts
under it are installed as package data and are reachable via
``Path(__file__).parent.parent / "evidence" / ...``.
"""
