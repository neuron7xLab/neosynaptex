"""Data-only package — ships the ``manifest.json`` referenced by
:mod:`neosynaptex._load_chain_root` so that wheel installs carry the
proof-chain genesis hash.

This package is intentionally empty of Python code; it exists solely to
make the top-level ``evidence_bundle_v1/`` directory discoverable by
``setuptools.packages.find``.
"""
