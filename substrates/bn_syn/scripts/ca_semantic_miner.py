from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_DIR = REPO_ROOT / "artifacts" / "ca_dccg" / "01_ontology"


def mine_semantic_artifacts() -> None:
    ONTOLOGY_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    mine_semantic_artifacts()
