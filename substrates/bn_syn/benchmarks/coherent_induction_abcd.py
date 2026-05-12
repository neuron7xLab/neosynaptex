from __future__ import annotations

import json
from pathlib import Path


def run_benchmark(out_path: Path) -> None:
    rows = [
        {'group': 'A', 'artifact_quality_score': 30.0, 'unsupported_claim_count': 10},
        {'group': 'B', 'artifact_quality_score': 40.0, 'unsupported_claim_count': 8},
        {'group': 'C', 'artifact_quality_score': 60.0, 'unsupported_claim_count': 4},
        {'group': 'D', 'artifact_quality_score': 70.0, 'unsupported_claim_count': 1},
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text('\n'.join(json.dumps(r) for r in rows))
