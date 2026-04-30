"""Phase 4a — Horizon Trace Contract lint.

Fail-closed audit on a substrate-side ``horizon_trace_contract.yaml``.
Used by tests, future Phase 4 PRs, and CI to enforce that no
substrate contract slips a hidden-core claim, an auto-promotion path,
a ledger-mutation allowance, or an observable that omits its
expected null behaviour.

CLI usage::

    python -m tools.audit.horizon_trace_lint <path-to-contract.yaml>

Exit codes:
    0 — contract is admissible.
    2 — contract has at least one fail-closed violation.

Programmatic usage::

    from tools.audit.horizon_trace_lint import lint_contract, LintViolation
    violations = lint_contract(yaml_dict)
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml as _yaml

    _HAVE_YAML = True
except ImportError:  # pragma: no cover
    _HAVE_YAML = False

__all__ = [
    "REQUIRED_OBSERVABLE_FIELDS",
    "LintViolation",
    "lint_contract",
    "lint_contract_path",
    "main",
]


REQUIRED_OBSERVABLE_FIELDS: tuple[str, ...] = (
    "status",
    "source_path",
    "code_symbol",
    "definition",
    "units_or_scale",
    "boundary_meaning",
    "expected_null_behavior",
    "failure_modes",
    "falsifiers",
)


@dataclass(frozen=True, slots=True)
class LintViolation:
    """A single fail-closed contract violation.

    ``path`` is a JSON-pointer-style location in the parsed YAML.
    ``rule`` is a stable identifier for the failing rule.
    ``message`` is a human-readable description.
    """

    path: str
    rule: str
    message: str

    def __str__(self) -> str:
        return f"[{self.rule}] {self.path}: {self.message}"


def _is_truthy(value: Any) -> bool:
    """``None``-safe truthiness for contract values.

    A list-valued field is treated as 'present' iff it is a non-empty
    sequence; a string-valued field iff it is non-empty after strip.
    Anything else is checked via plain truthiness.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return bool(value)


def _check_claim_boundary(contract: dict[str, Any]) -> list[LintViolation]:
    out: list[LintViolation] = []
    cb = contract.get("claim_boundary")
    if not isinstance(cb, dict):
        out.append(
            LintViolation(
                path="claim_boundary",
                rule="missing_claim_boundary",
                message=(
                    "claim_boundary block is missing or not a mapping; every "
                    "horizon trace contract must declare it explicitly"
                ),
            )
        )
        return out
    if cb.get("hidden_core_is_evidence") is not False:
        out.append(
            LintViolation(
                path="claim_boundary.hidden_core_is_evidence",
                rule="hidden_core_claimed_as_evidence",
                message=(
                    "must be exactly False; a hidden simulation core is "
                    "structurally not admissible evidence"
                ),
            )
        )
    if cb.get("boundary_trace_required") is not True:
        out.append(
            LintViolation(
                path="claim_boundary.boundary_trace_required",
                rule="boundary_trace_not_required",
                message=(
                    "must be exactly True; the contract is meaningless if "
                    "boundary traces are not required"
                ),
            )
        )
    if cb.get("ledger_mutation_allowed") is not False:
        out.append(
            LintViolation(
                path="claim_boundary.ledger_mutation_allowed",
                rule="ledger_mutation_allowed",
                message=(
                    "must be exactly False; ledger mutations are proposal-only "
                    "and require a separate human-reviewed PR"
                ),
            )
        )
    if cb.get("gamma_promotion_allowed") is not False:
        out.append(
            LintViolation(
                path="claim_boundary.gamma_promotion_allowed",
                rule="gamma_promotion_allowed",
                message=(
                    "must be exactly False; γ promotion is forbidden under "
                    "CANON_VALIDATED_FROZEN globally"
                ),
            )
        )
    return out


def _check_observables(contract: dict[str, Any]) -> list[LintViolation]:
    out: list[LintViolation] = []
    obs = contract.get("observables")
    if not isinstance(obs, dict) or not obs:
        out.append(
            LintViolation(
                path="observables",
                rule="missing_observables",
                message=(
                    "must declare at least one observable; an empty boundary "
                    "trace is not a contract"
                ),
            )
        )
        return out

    for name, entry in obs.items():
        location = f"observables.{name}"
        if not isinstance(entry, dict):
            out.append(
                LintViolation(
                    path=location,
                    rule="observable_not_mapping",
                    message="must be a mapping",
                )
            )
            continue
        for field in REQUIRED_OBSERVABLE_FIELDS:
            if field not in entry:
                out.append(
                    LintViolation(
                        path=f"{location}.{field}",
                        rule="observable_field_missing",
                        message=(
                            f"required field {field!r} is absent — every "
                            "observable must declare its full ninefold contract"
                        ),
                    )
                )
                continue
            # The TODO_OR_FOUND sentinel is admissible only for these
            # *interpretive* fields; the structural fields must carry
            # a concrete value.
            interpretive = {"boundary_meaning", "expected_null_behavior"}
            structural = {"status", "source_path", "code_symbol", "definition", "units_or_scale"}
            if field in structural and not _is_truthy(entry[field]):
                out.append(
                    LintViolation(
                        path=f"{location}.{field}",
                        rule="observable_field_empty",
                        message=(
                            f"structural field {field!r} must carry a concrete "
                            "value; TODO_OR_FOUND is not allowed here"
                        ),
                    )
                )
            if field in interpretive and entry[field] is None:
                out.append(
                    LintViolation(
                        path=f"{location}.{field}",
                        rule="observable_interpretive_null",
                        message=(
                            f"{field!r} must not be null; declare TODO_OR_FOUND "
                            "if the value is not yet known"
                        ),
                    )
                )
            if field in {"failure_modes", "falsifiers"}:
                # These are *required* lists — empty is allowed but the
                # caller must explicitly write `[]`. A null value is
                # rejected because it conflates 'no entries' with
                # 'forgotten field'.
                if entry[field] is None:
                    out.append(
                        LintViolation(
                            path=f"{location}.{field}",
                            rule="observable_list_field_null",
                            message=(
                                f"{field!r} must be a list (possibly empty); null "
                                "conflates 'no entries' with 'forgotten field'"
                            ),
                        )
                    )
                elif not isinstance(entry[field], (list, tuple)):
                    out.append(
                        LintViolation(
                            path=f"{location}.{field}",
                            rule="observable_list_field_wrong_type",
                            message=f"{field!r} must be a list, got {type(entry[field]).__name__}",
                        )
                    )

    return out


def _check_coordinates(contract: dict[str, Any]) -> list[LintViolation]:
    out: list[LintViolation] = []
    coords = contract.get("coordinates")
    if not isinstance(coords, dict) or not coords:
        out.append(
            LintViolation(
                path="coordinates",
                rule="missing_coordinates",
                message=(
                    "must declare at least one candidate coordinate; "
                    "regression-target ambiguity is itself an admissibility risk"
                ),
            )
        )
    return out


def _check_forbidden_claims_listed(contract: dict[str, Any]) -> list[LintViolation]:
    out: list[LintViolation] = []
    fc = contract.get("forbidden_claims")
    if fc is None:
        out.append(
            LintViolation(
                path="forbidden_claims",
                rule="missing_forbidden_claims",
                message=(
                    "must declare a forbidden_claims list; the contract is "
                    "incomplete without an explicit anti-pattern catalogue"
                ),
            )
        )
        return out
    if not isinstance(fc, (list, tuple)):
        out.append(
            LintViolation(
                path="forbidden_claims",
                rule="forbidden_claims_wrong_type",
                message=f"must be a list, got {type(fc).__name__}",
            )
        )
        return out
    if not fc:
        out.append(
            LintViolation(
                path="forbidden_claims",
                rule="forbidden_claims_empty",
                message="must list at least one forbidden claim",
            )
        )
    return out


def lint_contract(contract: dict[str, Any]) -> list[LintViolation]:
    """Run every fail-closed check on a parsed YAML contract.

    Returns the flat list of violations. An admissible contract returns
    the empty list.
    """
    violations: list[LintViolation] = []
    violations.extend(_check_claim_boundary(contract))
    violations.extend(_check_observables(contract))
    violations.extend(_check_coordinates(contract))
    violations.extend(_check_forbidden_claims_listed(contract))
    return violations


def lint_contract_path(path: Path) -> list[LintViolation]:
    """Read and lint a contract YAML at ``path``."""
    if not _HAVE_YAML:  # pragma: no cover - PyYAML missing
        return [
            LintViolation(
                path=str(path),
                rule="pyyaml_missing",
                message=("PyYAML is not installed; install it to lint contracts"),
            )
        ]
    with path.open(encoding="utf-8") as fh:
        loaded = _yaml.safe_load(fh)
    if not isinstance(loaded, dict):
        return [
            LintViolation(
                path=str(path),
                rule="contract_not_mapping",
                message=(f"top-level YAML must be a mapping; got {type(loaded).__name__}"),
            )
        ]
    return lint_contract(loaded)


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - CLI
    parser = argparse.ArgumentParser(
        prog="horizon_trace_lint",
        description=(
            "Phase 4a horizon-trace-contract lint. Fails closed if a contract "
            "claims a hidden core as evidence, allows γ promotion, allows "
            "ledger mutation, or omits any required observable field."
        ),
    )
    parser.add_argument(
        "contract_path",
        type=Path,
        help="Path to a substrate horizon_trace_contract.yaml file",
    )
    args = parser.parse_args(argv)
    violations = lint_contract_path(args.contract_path.resolve())
    if violations:
        print(
            f"HORIZON_TRACE_LINT FAILED ({len(violations)} violation(s)) at {args.contract_path}:",
            file=sys.stderr,
        )
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 2
    print(f"HORIZON_TRACE_LINT OK at {args.contract_path}: contract admissible at Phase 4a.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
