#!/usr/bin/env python3
"""Canonical PR intake heading contract shared by compiler, validator, and tests."""

from __future__ import annotations

REQUIRED_HEADINGS = [
    "## Problem",
    "## Scope",
    "## Invariants touched",
    "## Evidence",
    "## Risks",
    "## Non-goals",
    "## Manifest refresh justification",
    "## Human review required",
    "## Policy-drift review (mandatory for governance-critical surfaces)",
]
