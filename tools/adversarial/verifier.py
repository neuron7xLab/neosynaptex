"""Verifier — §IV.B role. Enforces §VII measurement-contract completeness.

Input
-----

Every kill-signal or metric contract in the repo that claims
``measurement_status: instrumented``. Today that surface is the
``kill_criteria`` list in the frontmatter of
``docs/SYSTEM_PROTOCOL.md``. Future instrumented metrics that land
in other canonical docs MUST be registered in
``CONTRACT_SOURCES`` so the Verifier finds them.

Verdict
-------

For each instrumented contract, the Verifier returns one of:

* ``ok`` — all eight fields per
  ``docs/protocols/MEASUREMENT_CONTRACT.md §1`` are present and
  non-empty.
* ``incomplete`` — one or more fields missing or empty. The claim
  cannot rise above ``hypothesized``.
* ``malformed`` — a field is present but the value fails its
  shape check (e.g., ``method:`` without an identifiable
  module/function reference).

The run returns a ``VerifierReport`` aggregating per-contract
verdicts. Exit 0 iff every instrumented contract verifies ``ok``;
exit 2 on any non-ok.

Design
------

* **No semantic judgment.** The Verifier checks field presence and
  shape, not whether the specified controls actually control the
  right thing. Adversarial review of semantic correctness remains
  human.
* **No silent skips.** A contract that lacks ``signal_contract:``
  entirely is treated as ``incomplete`` (with all eight fields
  reported missing), not as "not applicable". Implicit skips
  mask drift.
* **Priority: Verifier > Auditor.** A Verifier failure gates
  merge; the other audit detectors run in parallel but their
  passes do not override a Verifier failure.
"""

from __future__ import annotations

import dataclasses
import pathlib
import re
import sys

__all__ = [
    "CONTRACT_SOURCES",
    "REQUIRED_FIELDS",
    "VerdictKind",
    "VerifierReport",
    "ContractVerdict",
    "load_instrumented_contracts",
    "main",
    "run_check",
    "verify_contract",
]

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# Sources that contain ``signal_contract:`` blocks the Verifier scans.
# New sources MUST be added here in the same PR that adds an
# instrumented contract.
CONTRACT_SOURCES: tuple[str, ...] = ("docs/SYSTEM_PROTOCOL.md",)

# Per ``docs/protocols/MEASUREMENT_CONTRACT.md §1``. The 8th field
# (``interpretation_boundary``) is the one this runtime newly
# enforces. The ``fake_alternative_guard`` key is an accepted alias
# for ``fake_alternative`` to honour the existing repo taxonomy.
REQUIRED_FIELDS: tuple[str, ...] = (
    "substrate",
    "signal",
    "method",
    "window",
    "controls",
    "fake_alternative",
    "falsifier",
    "interpretation_boundary",
)

_FAKE_ALIAS: str = "fake_alternative_guard"

# A method reference that looks plausible: ``module.function`` with
# at least one dot, or ``module.Class.method``. Rejects ``"todo"``,
# ``"see below"``, and single-word values.
_METHOD_SHAPE = re.compile(r"[a-zA-Z_][a-zA-Z_0-9]*(?:\.[a-zA-Z_][a-zA-Z_0-9]*){1,}")


class VerdictKind(str):
    """Sentinel-strings for the three verdict kinds."""

    OK = "ok"
    INCOMPLETE = "incomplete"
    MALFORMED = "malformed"


@dataclasses.dataclass(frozen=True)
class ContractVerdict:
    """Verdict for one signal_contract."""

    signal_id: str
    source: str
    kind: str  # one of VerdictKind.*
    missing: tuple[str, ...]
    malformed: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.kind == VerdictKind.OK

    def as_str(self) -> str:
        if self.ok:
            return f"{self.signal_id} ({self.source}): ok"
        issues: list[str] = []
        if self.missing:
            issues.append(f"missing: {', '.join(self.missing)}")
        if self.malformed:
            issues.append(f"malformed: {', '.join(self.malformed)}")
        return f"{self.signal_id} ({self.source}): {self.kind} — " + "; ".join(issues)


@dataclasses.dataclass(frozen=True)
class VerifierReport:
    """Aggregate Verifier verdict over all instrumented contracts."""

    verdicts: tuple[ContractVerdict, ...]

    @property
    def ok(self) -> bool:
        return all(v.ok for v in self.verdicts)

    @property
    def n_ok(self) -> int:
        return sum(1 for v in self.verdicts if v.ok)

    @property
    def n_incomplete(self) -> int:
        return sum(1 for v in self.verdicts if v.kind == VerdictKind.INCOMPLETE)

    @property
    def n_malformed(self) -> int:
        return sum(1 for v in self.verdicts if v.kind == VerdictKind.MALFORMED)


# ---------------------------------------------------------------------------
# YAML-frontmatter extraction
# ---------------------------------------------------------------------------


_FRONTMATTER = re.compile(r"\A---\n(.*?\n)---\n", re.DOTALL)


def _load_yaml(body: str) -> dict:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - fallback
        raise RuntimeError(
            "pyyaml is required for tools.adversarial.verifier; install via `pip install pyyaml`"
        ) from exc
    data = yaml.safe_load(body)
    return {} if data is None else data


def load_instrumented_contracts(
    sources: tuple[str, ...] = CONTRACT_SOURCES,
    repo_root: pathlib.Path = _REPO_ROOT,
) -> list[dict]:
    """Return the list of instrumented ``signal_contract`` blocks.

    Each returned dict carries the normalised contract plus a
    ``_signal_id`` and ``_source`` key the Verifier uses for
    reporting.
    """

    contracts: list[dict] = []
    for rel in sources:
        path = repo_root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        m = _FRONTMATTER.match(text)
        if m is None:
            continue
        data = _load_yaml(m.group(1))
        criteria = data.get("kill_criteria")
        if not isinstance(criteria, list):
            continue
        for entry in criteria:
            if not isinstance(entry, dict):
                continue
            if entry.get("measurement_status") != "instrumented":
                continue
            contract = entry.get("signal_contract") or {}
            if not isinstance(contract, dict):
                contract = {}
            annotated = dict(contract)
            annotated["_signal_id"] = entry.get("id", "<no id>")
            annotated["_source"] = rel
            contracts.append(annotated)
    return contracts


# ---------------------------------------------------------------------------
# Per-contract verification
# ---------------------------------------------------------------------------


def verify_contract(contract: dict) -> ContractVerdict:
    """Return the verdict for one signal_contract dict."""

    signal_id = str(contract.get("_signal_id", "<no id>"))
    source = str(contract.get("_source", "<no source>"))

    # Resolve aliases before presence check.
    normalised = dict(contract)
    if "fake_alternative" not in normalised and _FAKE_ALIAS in normalised:
        normalised["fake_alternative"] = normalised[_FAKE_ALIAS]

    missing: list[str] = []
    malformed: list[str] = []

    for field in REQUIRED_FIELDS:
        value = normalised.get(field)
        if value is None:
            missing.append(field)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(field)
            continue
        if not isinstance(value, (str, dict, list)):
            malformed.append(f"{field}={value!r} must be string or structured")
            continue

    # Method shape: must name a module/function path if it is a string.
    method_value = normalised.get("method")
    if (
        isinstance(method_value, str)
        and method_value.strip()
        and not _METHOD_SHAPE.search(method_value)
    ):
        malformed.append(
            f"method={method_value!r} must reference a module/function (e.g. 'pkg.mod.fn')"
        )

    if missing and not malformed:
        kind = VerdictKind.INCOMPLETE
    elif malformed:
        kind = VerdictKind.MALFORMED
    else:
        kind = VerdictKind.OK

    return ContractVerdict(
        signal_id=signal_id,
        source=source,
        kind=kind,
        missing=tuple(missing),
        malformed=tuple(malformed),
    )


def run_check(
    sources: tuple[str, ...] = CONTRACT_SOURCES,
    repo_root: pathlib.Path = _REPO_ROOT,
) -> tuple[int, VerifierReport, str]:
    """Execute the Verifier. Returns (exit_code, report, human_summary)."""

    contracts = load_instrumented_contracts(sources, repo_root)
    verdicts = tuple(verify_contract(c) for c in contracts)
    report = VerifierReport(verdicts=verdicts)

    if report.ok:
        summary = (
            f"OK: {report.n_ok}/{len(verdicts)} instrumented contract(s) "
            "satisfy MEASUREMENT_CONTRACT.md §1. All eight fields present."
        )
        return 0, report, summary

    lines = [f"FAIL: {len(verdicts) - report.n_ok}/{len(verdicts)} contract(s) failed."]
    for v in verdicts:
        if not v.ok:
            lines.append("  - " + v.as_str())
    return 2, report, "\n".join(lines)


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - CLI
    _ = argv
    code, _report, message = run_check()
    stream = sys.stdout if code == 0 else sys.stderr
    print(message, file=stream)
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
