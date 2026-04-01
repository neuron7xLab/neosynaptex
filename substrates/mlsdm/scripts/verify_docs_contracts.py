#!/usr/bin/env python3
"""Verify documentation contract blocks against code defaults."""

from __future__ import annotations

import json
import os
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "CONTRACTS_CRITICAL_SUBSYSTEMS.md"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

CONTRACT_PATTERN = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


@dataclass(frozen=True)
class DocContract:
    name: str
    source: str
    value: Any


def _fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


@contextmanager
def _temporary_env(var: str) -> Any:
    original = os.environ.get(var)
    if var in os.environ:
        del os.environ[var]
    try:
        yield
    finally:
        if original is None:
            os.environ.pop(var, None)
        else:
            os.environ[var] = original


def _load_contracts(doc_text: str) -> list[DocContract]:
    contracts: list[DocContract] = []
    for match in CONTRACT_PATTERN.finditer(doc_text):
        payload = json.loads(match.group(1))
        contracts.append(
            DocContract(
                name=payload["doc_contract"],
                source=payload["source"],
                value=payload["value"],
            )
        )
    return contracts


def _resolve_symbol(path: str) -> Any:
    module_path, _, attr_path = path.rpartition(".")
    module = import_module(module_path)
    value: Any = module
    for attr in attr_path.split("."):
        value = getattr(value, attr)
    return value


def _normalize_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    return value


def _verify_default_public_paths(contract: DocContract) -> None:
    actual = _normalize_value(_resolve_symbol(contract.source))
    if actual != contract.value:
        _fail(
            "security.default_public_paths mismatch: "
            f"expected {contract.value}, got {actual}"
        )


def _verify_runtime_default_mode(contract: DocContract) -> None:
    get_runtime_mode = _resolve_symbol(contract.source)
    with _temporary_env("MLSDM_RUNTIME_MODE"):
        actual = get_runtime_mode()
    if actual.value != contract.value:
        _fail(
            "runtime.default_mode mismatch: "
            f"expected {contract.value}, got {actual.value}"
        )


def _extract_subset(source: dict[str, Any], subset: dict[str, Any]) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    for key, value in subset.items():
        if isinstance(value, dict):
            extracted[key] = _extract_subset(source.get(key, {}), value)
        else:
            extracted[key] = source.get(key)
    return extracted


def _verify_runtime_mode_defaults_subset(contract: DocContract) -> None:
    get_defaults = _resolve_symbol(contract.source)
    expected_modes: dict[str, Any] = contract.value
    from mlsdm.config.runtime import RuntimeMode

    for mode_name, subset in expected_modes.items():
        mode = RuntimeMode(mode_name)
        actual = get_defaults(mode)
        actual_subset = _extract_subset(actual, subset)
        if actual_subset != subset:
            _fail(
                f"runtime.mode_defaults_subset mismatch for {mode_name}: "
                f"expected {subset}, got {actual_subset}"
            )


def main() -> int:
    if not DOC_PATH.exists():
        _fail(f"Doc not found: {DOC_PATH}")

    doc_text = DOC_PATH.read_text(encoding="utf-8")
    contracts = _load_contracts(doc_text)
    if not contracts:
        _fail("No doc_contract JSON blocks found.")

    dispatch = {
        "security.default_public_paths": _verify_default_public_paths,
        "runtime.default_mode": _verify_runtime_default_mode,
        "runtime.mode_defaults_subset": _verify_runtime_mode_defaults_subset,
    }

    for contract in contracts:
        verifier = dispatch.get(contract.name)
        if not verifier:
            _fail(f"No verifier registered for doc_contract '{contract.name}'")
        verifier(contract)

    print("Documentation contracts verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
