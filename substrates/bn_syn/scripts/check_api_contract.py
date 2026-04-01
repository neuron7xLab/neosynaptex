"""Semver-aware API contract gate for BN-Syn public modules."""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import re
import sys
from pathlib import Path
from typing import Any

CONTRACT_SYMBOLS: dict[str, tuple[str, ...]] = {
    "bnsyn.config": (),
    "bnsyn.rng": (),
    "bnsyn.cli": (),
    "bnsyn.neurons": (
        "AdExState",
        "IntegrationMetrics",
        "adex_step",
        "adex_step_adaptive",
        "adex_step_with_error_tracking",
    ),
    "bnsyn.synapses": ("ConductanceState", "ConductanceSynapses", "nmda_mg_block"),
    "bnsyn.control": (
        "BranchingEstimator",
        "SigmaController",
        "TemperatureSchedule",
        "gate_sigmoid",
        "energy_cost",
        "total_reward",
    ),
    "bnsyn.simulation": ("Network", "NetworkParams", "run_simulation"),
    "bnsyn.sim.network": ("Network", "NetworkParams", "run_simulation"),
    "bnsyn.neuron.adex": (
        "AdExState",
        "IntegrationMetrics",
        "adex_step",
        "adex_step_adaptive",
        "adex_step_with_error_tracking",
    ),
    "bnsyn.synapse.conductance": ("ConductanceState", "ConductanceSynapses", "nmda_mg_block"),
    "bnsyn.plasticity.three_factor": ("three_factor_update",),
    "bnsyn.criticality.branching": ("BranchingEstimator", "SigmaController"),
    "bnsyn.temperature.schedule": ("TemperatureSchedule", "gate_sigmoid"),
    "bnsyn.connectivity.sparse": ("SparseConnectivity", "build_random_connectivity"),
}
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def _ensure_repo_src_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"
    if src_path.is_dir():
        src_text = str(src_path)
        if src_text not in sys.path:
            sys.path.insert(0, src_text)


def _normalize_signature_text(signature_text: str) -> str:
    normalized = signature_text
    normalized = normalized.replace("typing.", "")
    normalized = normalized.replace("collections.abc.", "")
    return normalized


def _safe_signature(obj: Any) -> str:
    try:
        return _normalize_signature_text(str(inspect.signature(obj)))
    except (TypeError, ValueError):
        return "<signature-unavailable>"


def collect_public_api() -> dict[str, dict[str, str]]:
    snapshot: dict[str, dict[str, str]] = {}
    path_bootstrapped = False
    for module_name, contract_symbols in CONTRACT_SYMBOLS.items():
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            missing_name = getattr(exc, "name", "")
            missing_bnsyn_root = missing_name in {"bnsyn", "bnsyn.__init__"}
            if path_bootstrapped or not module_name.startswith("bnsyn") or not missing_bnsyn_root:
                raise
            _ensure_repo_src_on_path()
            path_bootstrapped = True
            module = importlib.import_module(module_name)
        module_snapshot: dict[str, str] = {}
        for symbol_name in sorted(set(contract_symbols)):
            if not hasattr(module, symbol_name):
                module_snapshot[symbol_name] = "<missing-symbol>"
                continue
            obj = getattr(module, symbol_name)
            module_snapshot[symbol_name] = _safe_signature(obj)
        snapshot[module_name] = module_snapshot
    return snapshot


def _read_pyproject_version() -> str:
    pyproject = Path("pyproject.toml")
    payload = pyproject.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"', payload, flags=re.MULTILINE)
    if not match:
        raise ValueError("Could not parse project version from pyproject.toml")
    return match.group(1)


def _parse_semver(version: str) -> tuple[int, int, int]:
    match = SEMVER_RE.match(version)
    if not match:
        raise ValueError(f"Invalid semver version: {version!r}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def check_api_changes(
    baseline: dict[str, dict[str, str]],
    current: dict[str, dict[str, str]],
) -> tuple[bool, list[str]]:
    breaking: list[str] = []
    for module_name, baseline_symbols in baseline.items():
        current_symbols = current.get(module_name)
        if current_symbols is None:
            breaking.append(f"Module removed from API: {module_name}")
            continue
        for symbol_name, baseline_signature in baseline_symbols.items():
            if symbol_name not in current_symbols:
                breaking.append(f"Symbol removed: {module_name}.{symbol_name}")
                continue
            current_signature = _normalize_signature_text(current_symbols[symbol_name])
            baseline_signature_normalized = _normalize_signature_text(baseline_signature)
            if baseline_signature_normalized != current_signature:
                breaking.append(
                    f"Signature changed: {module_name}.{symbol_name} "
                    f"{baseline_signature_normalized} -> {current_signature}"
                )
    return len(breaking) == 0, breaking


def semver_allows_breaking_change(previous: str, current: str) -> bool:
    prev_major, _, _ = _parse_semver(previous)
    cur_major, _, _ = _parse_semver(current)
    return cur_major > prev_major


def main() -> int:
    parser = argparse.ArgumentParser(description="Semver-aware API contract checker")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--current-version", default=None)
    parser.add_argument("--baseline-version", default=None)
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args()

    current_version = args.current_version or _read_pyproject_version()
    current_snapshot = collect_public_api()

    if args.write_baseline:
        payload = {
            "version": current_version,
            "modules": current_snapshot,
        }
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"Wrote baseline: {args.baseline}")
        return 0

    if not args.baseline.exists():
        print(f"ERROR: Baseline not found: {args.baseline}")
        return 1

    baseline_payload = json.loads(args.baseline.read_text(encoding="utf-8"))
    baseline_modules = baseline_payload.get("modules")
    if not isinstance(baseline_modules, dict):
        print("ERROR: Baseline payload missing 'modules' mapping")
        return 1

    baseline_version = args.baseline_version or str(baseline_payload.get("version", "0.0.0"))
    try:
        ok, breaking = check_api_changes(baseline_modules, current_snapshot)
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: Failed to compare API snapshots: {exc}")
        return 1

    if ok:
        print("API contract check passed")
        return 0

    for item in breaking:
        print(f"BREAKING: {item}")

    if semver_allows_breaking_change(baseline_version, current_version):
        print(
            "Detected breaking API changes, but semver major version bump allows this: "
            f"{baseline_version} -> {current_version}"
        )
        return 0

    print(
        "ERROR: Breaking API changes detected without major semver bump: "
        f"{baseline_version} -> {current_version}"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
