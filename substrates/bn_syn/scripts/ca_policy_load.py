from __future__ import annotations

from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "governance" / "ca_dccg.yml"


def load_policy_config() -> dict[str, object]:
    parsed = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        msg = "governance/ca_dccg.yml must parse to a mapping"
        raise ValueError(msg)
    return parsed


def main() -> None:
    _ = load_policy_config()


if __name__ == "__main__":
    main()
