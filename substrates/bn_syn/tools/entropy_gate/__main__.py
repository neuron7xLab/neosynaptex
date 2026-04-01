from __future__ import annotations

from pathlib import Path
import json
import sys

from tools.entropy_gate.compute_metrics import _repo_root_from_file, compute_metrics


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_command_log(path: Path, command: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(command + "\n")


def main(argv: list[str]) -> int:
    mode = "current"
    if "--mode" in argv:
        mode_index = argv.index("--mode")
        if mode_index + 1 >= len(argv):
            raise SystemExit("NEEDS_EVIDENCE: --mode expects baseline|current")
        mode = argv[mode_index + 1]

    if mode not in {"baseline", "current"}:
        raise SystemExit("NEEDS_EVIDENCE: --mode must be baseline|current")

    repo_root = _repo_root_from_file(Path(__file__))
    metrics = compute_metrics(repo_root)

    entropy_dir = repo_root / "entropy"
    evidence_dir = repo_root / "evidence" / "entropy_gate"

    if mode == "baseline":
        _write_json(entropy_dir / "baseline.json", metrics)
        _write_json(evidence_dir / "baseline_metrics.json", metrics)
    else:
        _write_json(entropy_dir / "current.json", metrics)
        _write_json(evidence_dir / "final_metrics.json", metrics)

    _append_command_log(evidence_dir / "commands.log", f"python -m tools.entropy_gate --mode {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
