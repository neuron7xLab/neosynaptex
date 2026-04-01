import os
import subprocess
from importlib import resources
from pathlib import Path

import pytest

from mlsdm.utils.config_loader import ConfigLoader


def test_default_config_resource_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CONFIG_PATH", raising=False)

    config = ConfigLoader.load_config("config/default_config.yaml")

    assert isinstance(config, dict)
    assert "dimension" in config


def test_api_import_without_repo_files(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("CONFIG_PATH", None)
    repo_root = Path(__file__).resolve().parents[2]
    env["PYTHONPATH"] = f"{repo_root / 'src'}:{env.get('PYTHONPATH', '')}".rstrip(":")

    proc = subprocess.run(
        [
            "python",
            "-c",
            "import os; os.environ.pop('CONFIG_PATH', None); import mlsdm.api.app; print('ok')",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, f"stdout: {proc.stdout}\nstderr: {proc.stderr}"


def test_packaged_default_config_matches_repo() -> None:
    repo_config = Path(__file__).resolve().parents[2] / "config" / "default_config.yaml"
    if not repo_config.is_file():
        pytest.skip("Repository default_config.yaml not present")

    packaged_text = (
        resources.files("mlsdm.config").joinpath("default_config.yaml").read_text(encoding="utf-8")
    )
    repo_text = repo_config.read_text(encoding="utf-8")

    assert packaged_text == repo_text
