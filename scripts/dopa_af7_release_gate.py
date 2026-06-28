from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.eai.dopa_af7_gate import evaluate_current_dopa_validity, result_to_jsonable


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the DOPA-AF7 fail-closed release gate."
    )
    parser.add_argument(
        "--input",
        default="evidence/dopa_closure/dopa_validity_001_result.json",
        help="Path to dopa_validity_001_result.json",
    )
    parser.add_argument(
        "--out",
        default="evidence/dopa_af7_release/FINAL_VERDICT.json",
        help="Output verdict path",
    )
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Exit non-zero unless AF7_READY. Intended for release CI only.",
    )
    args = parser.parse_args()

    result = evaluate_current_dopa_validity(args.input)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = result_to_jsonable(result)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_ready and not result.academy_fellow_ready:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
