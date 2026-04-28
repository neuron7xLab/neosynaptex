"""CLI: emit the locked Mycelium Gate 0 verdict as strict JSON.

This tool is the runtime audit twin of
``contracts/mycelium_pre_admission.py``. It reads no fungal data and
takes no admit-data flags; it only serialises the locked Gate 0 verdict
to a strict-JSON document so external auditors and CI gates can confirm
the gate is still BLOCKED.

The output is strict JSON (RFC 8259): no ``NaN``, ``Infinity``, or
``-Infinity`` tokens are emitted (and there are no float fields anyway).
The exit code is fixed at 0 — the CLI's job is to **report** the
verdict, not to fail the calling process; downstream consumers should
read the JSON ``verdict.gate_status`` field and decide for themselves.

CLI
---
::

    python -m tools.audit.mycelium_gate_status \\
        --out evidence/mycelium_gate_status.json

Without ``--out`` the document is printed to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from contracts.mycelium_pre_admission import gate_zero_verdict  # noqa: E402

__all__ = ["build_gate_status_document", "main"]


def build_gate_status_document() -> dict[str, Any]:
    """Build the strict-JSON-safe Gate 0 status document."""
    v = gate_zero_verdict()
    return {
        "schema_version": "1.0.0",
        "substrate": "mycelium",
        "gate": "GAMMA_GATE_0",
        "verdict": {
            "claim_status": v.claim_status,
            "gate_status": v.gate_status,
            "reasons": list(v.reasons),
        },
        "non_claims": list(v.non_claims),
        "references": {
            "method_gate_doc": "docs/method_gates/MYCELIUM_GAMMA_GATE_0.md",
            "architecture_doc": "docs/architecture/recursive_claim_refinement.md",
            "contract_module": "contracts.mycelium_pre_admission",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Emit the locked Mycelium Gate 0 verdict (BLOCKED_BY_METHOD_DEFINITION) "
            "as strict JSON for audit tooling. Reads no fungal data."
        )
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSON path. If omitted, write to stdout.",
    )
    args = parser.parse_args(argv)

    document = build_gate_status_document()
    payload = json.dumps(document, sort_keys=True, indent=2, allow_nan=False) + "\n"

    out_path: Path | None = args.out
    if out_path is None:
        sys.stdout.write(payload)
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
