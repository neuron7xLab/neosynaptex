from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[import-not-found]


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def test_optional_dependency_extras_defined() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    extras = pyproject["project"]["optional-dependencies"]

    assert "http" in extras
    assert "kafka" in extras
    assert "ml" in extras
    assert "accel" in extras
    assert "full" in extras

    assert "aiohttp>=3.9.4" in extras["http"]
    assert "kafka-python>=2.0.0" in extras["kafka"]
    assert "torch>=2.0.0,<3.0.0" in extras["ml"]
    assert "numba>=0.60.0" in extras["accel"]
    # full extra is a meta-extra referencing other extras
    full_set = set(extras["full"])
    # Must contain at least one self-referencing extra
    assert any("mycelium-fractal-net[" in dep for dep in full_set) or len(full_set) > 5


def _run_blocked_torch_script(tmp_path: Path, source: str) -> subprocess.CompletedProcess[str]:
    script = tmp_path / "blocked_torch_case.py"
    script.write_text(source, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )


def test_core_import_works_without_ml_dependency(tmp_path: Path) -> None:
    proc = _run_blocked_torch_script(
        tmp_path,
        """
import builtins
_real_import = builtins.__import__

def _blocked_import(name, *args, **kwargs):
    if name == 'torch' or name.startswith('torch.'):
        raise ModuleNotFoundError('blocked torch import for core-install test')
    return _real_import(name, *args, **kwargs)

builtins.__import__ = _blocked_import
import mycelium_fractal_net as mfn
assert callable(mfn.simulate)
print('ok')
""",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok" in proc.stdout


def test_ml_only_surface_emits_clear_error_without_torch(tmp_path: Path) -> None:
    proc = _run_blocked_torch_script(
        tmp_path,
        """
import builtins
_real_import = builtins.__import__

def _blocked_import(name, *args, **kwargs):
    if name == 'torch' or name.startswith('torch.'):
        raise ModuleNotFoundError('blocked torch import for core-install test')
    return _real_import(name, *args, **kwargs)

builtins.__import__ = _blocked_import
import mycelium_fractal_net as mfn
try:
    _ = mfn.MyceliumFractalNet
except ImportError as exc:
    print(str(exc))
else:
    raise SystemExit('expected ImportError for ML surface')
""",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "optional ML dependency" in proc.stdout
