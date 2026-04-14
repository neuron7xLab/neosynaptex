"""Ratchet: kill-signal instrumentation coverage must never regress.

Signal contract
---------------

``docs/SYSTEM_PROTOCOL.md`` declares a list of ``kill_criteria`` in
machine-readable frontmatter, each tagged with
``measurement_status: instrumented | not_instrumented``. Instrumented
entries carry a ``signal_contract`` with ``tool`` and ``test_suite``
paths.

This tool enforces two invariants:

1. **Integrity** — every instrumented entry MUST point at an existing
   ``signal_contract.tool`` file AND an existing
   ``signal_contract.test_suite`` file. A claim of instrumentation
   whose code has been removed or renamed is a measurement lie.
2. **Ratchet** — the count of instrumented entries MUST be
   ``>= MIN_INSTRUMENTED`` recorded in
   ``tools/audit/kill_signal_baseline.json``. Regression requires an
   explicit diff to the baseline file, visible at review.

Adding instrumentation for a previously prose-only kill-signal is a
two-step commit: (a) land the tool + test + workflow, transition the
frontmatter entry to ``instrumented``, and (b) bump the baseline in
the same PR. The ratchet enforces that bumps never silently reverse.

Contract
--------

* **Input.** None (reads canonical files directly).
* **Success.** Exit 0 when all instrumented entries have existing
  tool + test files AND instrumented count >= baseline.
* **Failure.** Exit 2 on any integrity or ratchet violation.
* **Scope.** Structural. Does NOT import or run the referenced tools;
  does NOT measure whether they currently produce a valid verdict.
  Semantic correctness of the signal contract stays the reviewer's
  job — the machine enforces only existence and non-regression.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

__all__ = [
    "FRONTMATTER_REGEX",
    "IntegrityError",
    "load_baseline",
    "load_kill_criteria",
    "main",
    "run_check",
]

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SYSTEM_PROTOCOL = _REPO_ROOT / "docs" / "SYSTEM_PROTOCOL.md"
_BASELINE_PATH = _REPO_ROOT / "tools" / "audit" / "kill_signal_baseline.json"

FRONTMATTER_REGEX = re.compile(r"\A---\n(.*?\n)---\n", re.DOTALL)


class IntegrityError(ValueError):
    """Raised when the frontmatter cannot be parsed into the expected shape."""


def _parse_yaml_frontmatter(text: str) -> dict:
    """Minimal, dependency-free YAML subset parser for the frontmatter shape.

    Uses ``pyyaml`` when available; falls back to a narrow hand parser
    that recognises only the shape SYSTEM_PROTOCOL.md actually uses
    (top-level scalars, nested dicts under ``kill_criteria``). Keeping
    the fallback keeps the audit tool runnable in minimal CI images
    without pulling a YAML dependency into the audit surface.
    """

    m = FRONTMATTER_REGEX.match(text)
    if m is None:
        raise IntegrityError("SYSTEM_PROTOCOL.md: missing YAML frontmatter block")
    body = m.group(1)
    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(body)
        if not isinstance(data, dict):
            raise IntegrityError("frontmatter did not parse as a mapping")
        return data
    except ImportError:  # pragma: no cover - fallback path
        return _parse_kill_criteria_fallback(body)


def _parse_kill_criteria_fallback(body: str) -> dict:
    """Narrow fallback: extract only ``kill_criteria`` list of dicts.

    Recognises this shape (one level of nesting under each list
    element, strings only) and nothing more. Any other frontmatter
    key is ignored.

    Invariant: returns ``{}`` (NOT ``{"kill_criteria": []}``) when
    the body contains no ``kill_criteria:`` line at all. Returning
    an empty list in that case would mask the absence of the key and
    let ``load_kill_criteria`` silently return ``[]`` instead of
    raising ``IntegrityError``. That was a CI-reproducible bug
    (#82/#83/#93/#94 test_load_kill_criteria_rejects_missing_list).
    """

    criteria: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    current_contract: dict[str, str] | None = None
    in_kill = False
    kill_criteria_seen = False

    for raw in body.splitlines():
        if raw.startswith("kill_criteria:"):
            in_kill = True
            kill_criteria_seen = True
            continue
        if in_kill and raw and not raw.startswith(" ") and not raw.startswith("#"):
            # Next top-level key ends the kill_criteria block.
            break
        if not in_kill:
            continue
        if raw.lstrip().startswith("#") or not raw.strip():
            continue

        stripped = raw.rstrip()
        indent = len(stripped) - len(stripped.lstrip(" "))
        line = stripped.strip()

        if line.startswith("- ") and indent == 2:
            current = {}
            current_contract = None
            criteria.append(current)
            remainder = line[2:].strip()
            if remainder:
                key, _, val = remainder.partition(":")
                current[key.strip()] = val.strip()
            continue

        if current is None:
            continue

        if indent == 4 and line == "signal_contract:":
            current_contract = {}
            current["signal_contract"] = current_contract  # type: ignore[assignment]
            continue
        if indent == 6 and current_contract is not None and ":" in line:
            key, _, val = line.partition(":")
            current_contract[key.strip()] = val.strip()
            continue
        if indent == 4 and ":" in line:
            key, _, val = line.partition(":")
            current[key.strip()] = val.strip()
            current_contract = None
            continue

    if not kill_criteria_seen:
        return {}
    return {"kill_criteria": criteria}


def load_kill_criteria(path: pathlib.Path = _SYSTEM_PROTOCOL) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    data = _parse_yaml_frontmatter(text)
    criteria = data.get("kill_criteria")
    if not isinstance(criteria, list):
        raise IntegrityError(
            "SYSTEM_PROTOCOL.md frontmatter: kill_criteria is missing or not a list"
        )
    return criteria


def load_baseline(path: pathlib.Path = _BASELINE_PATH) -> int:
    if not path.is_file():
        raise IntegrityError(
            f"baseline file not found at {path}; "
            "first-time setup requires committing kill_signal_baseline.json"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data.get("min_instrumented_count")
    if not isinstance(value, int) or value < 0:
        raise IntegrityError(
            "kill_signal_baseline.json: min_instrumented_count must be a non-negative int"
        )
    return value


def _instrumented(criterion: dict) -> bool:
    return criterion.get("measurement_status") == "instrumented"


def run_check(
    system_protocol: pathlib.Path = _SYSTEM_PROTOCOL,
    baseline_path: pathlib.Path = _BASELINE_PATH,
    repo_root: pathlib.Path = _REPO_ROOT,
) -> tuple[int, str]:
    try:
        criteria = load_kill_criteria(system_protocol)
        baseline = load_baseline(baseline_path)
    except (IntegrityError, json.JSONDecodeError, FileNotFoundError) as exc:
        return 2, f"DRIFT: {exc}"

    instrumented = [c for c in criteria if _instrumented(c)]
    integrity_violations: list[str] = []

    for c in instrumented:
        cid = c.get("id", "<no id>")
        contract = c.get("signal_contract") or {}
        if not isinstance(contract, dict):
            integrity_violations.append(f"{cid}: signal_contract is missing or malformed")
            continue
        for key in ("tool", "test_suite"):
            rel = contract.get(key)
            if not isinstance(rel, str) or not rel.strip():
                integrity_violations.append(f"{cid}: signal_contract.{key} is missing")
                continue
            if not (repo_root / rel.strip()).exists():
                integrity_violations.append(
                    f"{cid}: signal_contract.{key} points at missing path {rel!r}"
                )

    if integrity_violations:
        return 2, "DRIFT: " + "; ".join(integrity_violations)

    current = len(instrumented)
    if current < baseline:
        return (
            2,
            "DRIFT: instrumented kill-signal count regressed: "
            f"baseline={baseline}, current={current}. Bump the baseline "
            "only in the same PR that removes instrumentation, with a "
            "written rationale in the PR body.",
        )

    total = len(criteria)
    return (
        0,
        f"OK: {current}/{total} kill-signals instrumented "
        f"(baseline={baseline}). All signal contracts point at existing code.",
    )


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - CLI
    _ = argv
    code, message = run_check()
    stream = sys.stdout if code == 0 else sys.stderr
    print(message, file=stream)
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
