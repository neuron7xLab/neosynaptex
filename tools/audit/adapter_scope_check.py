"""Detect drift between canonical in-scope substrate list and runtime adapters.

Signal contract
---------------

Neosynaptex's Levin-bridge canon has two authoritative declarations of
the in-scope substrate set:

* Prose — ``evidence/levin_bridge/horizon_knobs.md`` opening line:
  "Substrates in scope after audit. Three — ..." and the
  ``§Pre-registration block`` table at the bottom of the same file.
* Code — ``substrates.bridge.levin_runner.ADAPTERS``.

When these disagree, any cross-substrate claim built on top of the
bridge is reviewably wrong (either the claim over-counts or the
runner under-counts). PR #80 fixed one such drift found manually;
this tool prevents the next one by failing CI on any future
divergence.

Contract
--------

* **Input.** None (the tool reads the canonical files directly).
* **Success.** Exit 0 when the count declared in ``horizon_knobs.md``
  ("Substrates in scope after audit. <word> —") equals
  ``len(ADAPTERS)``, AND every non-scoped-out row in the
  pre-registration table points at an on-disk adapter code location.
* **Failure.** Exit 2 in any of:

  1. The "Substrates in scope after audit" sentence is missing or
     unparseable.
  2. The declared count ≠ ``len(ADAPTERS)``.
  3. A row in the pre-registration table references an
     ``Adapter code location`` path that does not exist.

* **Scope.** Structural only. The tool does NOT verify that each
  adapter's ``name`` attribute matches the table's display name
  (those are deliberately different: e.g. ``Kuramoto (TradePulse
  proxy)`` in the table vs ``kuramoto_tradepulse_proxy`` in
  ``ADAPTERS``). Semantic alignment stays the reviewer's job; the
  machine enforces only the count-and-existence invariant that was
  the class of drift previously missed.
"""

from __future__ import annotations

import pathlib
import re
import sys

__all__ = [
    "SCOPE_DECLARATION_REGEX",
    "WORD_TO_COUNT",
    "count_declared_scope",
    "extract_prereg_paths",
    "main",
    "run_check",
]

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_HORIZON_KNOBS = _REPO_ROOT / "evidence" / "levin_bridge" / "horizon_knobs.md"

SCOPE_DECLARATION_REGEX = re.compile(
    # Tolerates Markdown emphasis around the phrase
    # (e.g. ``**Substrates in scope after audit.**``) and either an
    # em-dash or a double-hyphen separator.
    r"Substrates in scope after audit\.[*_\s]*"
    r"(?P<word>Two|Three|Four|Five|Six)\s*(?:—|--)",
    re.IGNORECASE,
)

WORD_TO_COUNT: dict[str, int] = {
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
}

# Match table rows of the form ``| name | knobs | path | sha |``.
# The path column may also be literal ``scoped out`` (for rows that
# declare an explicit non-inclusion). Those are ignored by the
# path-existence check; only numeric scope comes from the
# ``Substrates in scope after audit`` sentence.
_TABLE_ROW_REGEX = re.compile(
    r"^\|\s*(?P<name>[^|]+?)\s*\|"
    r"\s*(?P<knobs>[^|]+?)\s*\|"
    r"\s*(?P<path>[^|]+?)\s*\|"
    r"\s*(?P<sha>[^|]+?)\s*\|\s*$"
)


def count_declared_scope(text: str) -> int:
    """Return the scope count declared in ``horizon_knobs.md`` prose."""

    match = SCOPE_DECLARATION_REGEX.search(text)
    if match is None:
        raise ValueError(
            "horizon_knobs.md: missing the canonical "
            "'Substrates in scope after audit. <word> —' sentence; "
            "cannot determine declared scope."
        )
    word = match.group("word").lower()
    return WORD_TO_COUNT[word]


_PREREG_HEADING_REGEX = re.compile(r"^#{1,6}\s+Pre-registration block\s*$", re.IGNORECASE)
_ANY_HEADING_REGEX = re.compile(r"^#{1,6}\s+\S")


def extract_prereg_paths(text: str) -> list[str]:
    """Return paths from the ``Pre-registration block`` table only.

    Other 4-column tables in ``horizon_knobs.md`` (e.g. per-substrate
    regime tables) share the row shape but carry different semantics;
    parsing them as code paths is a false-positive. We locate the
    ``## Pre-registration block`` heading explicitly and parse rows
    only until the next heading or EOF.

    Rows whose third column is ``scoped out`` (or contains that
    phrase) are excluded — they document deliberate non-inclusion
    and carry no path to verify.

    Returns an empty list when the pre-registration block is absent;
    callers treat "no block" as "nothing to verify", not as a drift,
    because the block's presence is a separate invariant (not
    currently gated).
    """

    lines = text.splitlines()
    start: int | None = None
    for i, line in enumerate(lines):
        if _PREREG_HEADING_REGEX.match(line):
            start = i + 1
            break
    if start is None:
        return []

    paths: list[str] = []
    for line in lines[start:]:
        if _ANY_HEADING_REGEX.match(line):
            break
        m = _TABLE_ROW_REGEX.match(line)
        if m is None:
            continue
        name = m.group("name").strip().lower()
        path = m.group("path").strip()
        if name in {"substrate", ":---", "---"} or set(name) <= {"-", ":"}:
            continue
        if set(path) <= {"-", ":"}:
            continue
        if "scoped out" in path.lower():
            continue
        paths.append(path)
    return paths


def run_check(
    knobs_path: pathlib.Path = _HORIZON_KNOBS,
    repo_root: pathlib.Path = _REPO_ROOT,
) -> tuple[int, str]:
    """Execute the drift check. Return (exit_code, human_message)."""

    if not knobs_path.is_file():
        return (
            2,
            f"horizon_knobs.md not found at {knobs_path}; cannot run adapter-scope drift check.",
        )

    text = knobs_path.read_text(encoding="utf-8")

    try:
        declared = count_declared_scope(text)
    except ValueError as exc:
        return 2, str(exc)

    try:
        from substrates.bridge.levin_runner import ADAPTERS
    except ImportError as exc:  # pragma: no cover - import-time failure
        return (
            2,
            f"cannot import substrates.bridge.levin_runner.ADAPTERS: {exc}",
        )
    runtime = len(ADAPTERS)

    if declared != runtime:
        return (
            2,
            "DRIFT: horizon_knobs.md declares "
            f"{declared} in-scope substrate(s); "
            f"levin_runner.ADAPTERS has {runtime}. "
            "Reconcile horizon_knobs.md §opening sentence with "
            "substrates/bridge/levin_runner.py::ADAPTERS before merging.",
        )

    missing: list[str] = []
    for rel in extract_prereg_paths(text):
        # Code-location cells may include backticks.
        cleaned = rel.strip().strip("`").strip()
        if not cleaned:
            continue
        if not (repo_root / cleaned).exists():
            missing.append(cleaned)
    if missing:
        return (
            2,
            "DRIFT: pre-registration table references "
            f"non-existent paths: {missing}. Update horizon_knobs.md "
            "or land the missing adapter code.",
        )

    return (
        0,
        f"OK: {declared} in-scope substrate(s), "
        f"len(ADAPTERS)={runtime}, all pre-registration paths exist.",
    )


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - CLI
    _ = argv  # no arguments; kept for test symmetry.
    code, message = run_check()
    stream = sys.stdout if code == 0 else sys.stderr
    print(message, file=stream)
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
