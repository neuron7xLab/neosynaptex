from __future__ import annotations

from pathlib import Path


def test_makefile_bootstrap_surface_is_canonical() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "BOOTSTRAP_SCRIPT := scripts/bootstrap.sh" in makefile
    assert "bash $(BOOTSTRAP_SCRIPT) --venv .venv --ready-file $(ENV_READY) --extras dev,test" in makefile
    assert "quickstart-smoke:" in makefile


def test_dockerfile_uses_bootstrap_fail_safe_entrypoint() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "bash scripts/bootstrap.sh --venv .venv --ready-file .venv/.ready-dev --extras dev,test" in dockerfile
    assert 'ENTRYPOINT ["make"]' in dockerfile
    assert 'CMD ["quickstart-smoke"]' in dockerfile


def test_bootstrap_script_has_deterministic_contract() -> None:
    script = Path("scripts/bootstrap.sh").read_text(encoding="utf-8")

    assert script.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in script
    assert '"${VENV_PATH}/bin/python" -m pip check' in script
