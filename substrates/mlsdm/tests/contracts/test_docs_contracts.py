"""Contract tests ensuring documentation matches code defaults."""

from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from mlsdm.adapters.llm_provider import LocalStubProvider
from mlsdm.adapters.provider_factory import build_provider_from_env
from mlsdm.config.runtime import RuntimeMode, get_runtime_config, get_runtime_mode
from mlsdm.security.path_utils import DEFAULT_PUBLIC_PATHS

DOC_PATH = Path(__file__).resolve().parents[2] / "docs" / "CONTRACTS_CRITICAL_SUBSYSTEMS.md"
CONTRACT_PATTERN = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


@contextmanager
def _temporary_env(var: str, value: str | None = None) -> Any:
    original = os.environ.get(var)
    if value is None:
        os.environ.pop(var, None)
    else:
        os.environ[var] = value
    try:
        yield
    finally:
        if original is None:
            os.environ.pop(var, None)
        else:
            os.environ[var] = original


@contextmanager
def _clear_runtime_env() -> Any:
    keys = [
        "HOST",
        "PORT",
        "MLSDM_WORKERS",
        "MLSDM_RELOAD",
        "MLSDM_LOG_LEVEL",
        "MLSDM_TIMEOUT_KEEP_ALIVE",
        "DISABLE_RATE_LIMIT",
        "RATE_LIMIT_REQUESTS",
        "RATE_LIMIT_WINDOW",
        "MLSDM_SECURE_MODE",
        "LOG_LEVEL",
        "JSON_LOGGING",
        "ENABLE_METRICS",
        "OTEL_TRACING_ENABLED",
        "OTEL_SDK_DISABLED",
        "OTEL_EXPORTER_TYPE",
        "OTEL_SERVICE_NAME",
        "LLM_BACKEND",
        "EMBEDDING_DIM",
        "ENABLE_FSLGS",
        "MLSDM_ENGINE_ENABLE_METRICS",
        "CONFIG_PATH",
        "MLSDM_DEBUG",
    ]
    originals = {key: os.environ.get(key) for key in keys}
    for key in keys:
        os.environ.pop(key, None)
    try:
        yield
    finally:
        for key, value in originals.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _load_doc_contract(name: str) -> dict[str, Any]:
    text = DOC_PATH.read_text(encoding="utf-8")
    for match in CONTRACT_PATTERN.finditer(text):
        payload = json.loads(match.group(1))
        if payload.get("doc_contract") == name:
            return payload
    raise AssertionError(f"doc_contract not found: {name}")


def _extract_subset(source: dict[str, Any], subset: dict[str, Any]) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    for key, value in subset.items():
        if isinstance(value, dict):
            extracted[key] = _extract_subset(source.get(key, {}), value)
        else:
            extracted[key] = source.get(key)
    return extracted


def test_security_default_public_paths_doc_parity() -> None:
    contract = _load_doc_contract("security.default_public_paths")
    assert contract["value"] == list(DEFAULT_PUBLIC_PATHS)


def test_runtime_default_mode() -> None:
    with _temporary_env("MLSDM_RUNTIME_MODE", None):
        assert get_runtime_mode() == RuntimeMode.DEV


def test_runtime_mode_defaults_subset() -> None:
    contract = _load_doc_contract("runtime.mode_defaults_subset")
    expected = contract["value"]

    with _clear_runtime_env():
        for mode_name, subset in expected.items():
            defaults = RuntimeMode(mode_name)
            actual = get_runtime_config(mode=defaults)
            actual_dict = {
                "server": {
                    "workers": actual.server.workers,
                    "log_level": actual.server.log_level,
                },
                "security": {
                    "rate_limit_enabled": actual.security.rate_limit_enabled,
                    "secure_mode": actual.security.secure_mode,
                },
                "observability": {
                    "json_logging": actual.observability.json_logging,
                    "tracing_enabled": actual.observability.tracing_enabled,
                },
                "engine": {"config_path": actual.engine.config_path},
            }
            actual_subset = _extract_subset(actual_dict, subset)
            assert actual_subset == subset


def test_disable_rate_limit_inversion() -> None:
    with _temporary_env("DISABLE_RATE_LIMIT", "1"):
        config = get_runtime_config(mode=RuntimeMode.DEV)
        assert config.security.rate_limit_enabled is False

    with _temporary_env("DISABLE_RATE_LIMIT", "0"):
        config = get_runtime_config(mode=RuntimeMode.DEV)
        assert config.security.rate_limit_enabled is True


def test_runtime_config_path_default() -> None:
    with _clear_runtime_env():
        config = get_runtime_config(mode=RuntimeMode.DEV)
        assert config.engine.config_path == "config/default_config.yaml"


def test_llm_backend_default() -> None:
    with _temporary_env("LLM_BACKEND", None):
        provider = build_provider_from_env()
    assert isinstance(provider, LocalStubProvider)
