"""demo_real.py must be honest: mode=real + zero non-admissible adapters.

The earlier CNS-AI boundary test pins that CNS-AI is excluded. This
battery adds the stronger invariant the T1 cleanup introduced:

* ``demo_real.py`` constructs ``Neosynaptex(mode="real")`` (the registration
  gate rejects any inadmissible adapter before the pipeline starts).
* Its only registered adapter is the Zebrafish (REAL + ADMISSIBLE).
* No other substrate module is imported (AST-level check).
* ``demo_multi.py`` carries the synthetic-admissible demo path.

Together these invariants mean a reader can trust the ``demo_real``
label: whatever runs there really is the REAL-mode evidentiary path.
"""

from __future__ import annotations

import ast
import pathlib
import runpy

import pytest

from contracts.provenance import (
    ClaimStatus,
    ProvenanceClass,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _parse(name: str) -> ast.Module:
    return ast.parse((REPO_ROOT / name).read_text(encoding="utf-8"))


def _imports(tree: ast.Module) -> tuple[set[str], set[str]]:
    names: set[str] = set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module)
            for a in node.names:
                names.add(a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                modules.add(a.name)
    return names, modules


# --------------------------------------------------------------------------
# demo_real.py -- real-only pipeline
# --------------------------------------------------------------------------


def test_demo_real_uses_mode_real() -> None:
    """AST-level: ``Neosynaptex(...)`` call must include ``mode="real"``."""
    tree = _parse("demo_real.py")
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Neosynaptex":
            for kw in node.keywords:
                if (
                    kw.arg == "mode"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value == "real"
                ):
                    found = True
    assert found, "demo_real.py must construct Neosynaptex(mode='real')"


def test_demo_real_only_imports_real_adapter() -> None:
    """demo_real must not import any synthetic / mock / downgraded adapter.

    The allowlist is tight: only the Zebrafish substrate module is permitted.
    """
    tree = _parse("demo_real.py")
    _, modules = _imports(tree)
    substrate_modules = {m for m in modules if m.startswith("substrates.")}
    allowed = {"substrates.zebrafish.adapter"}
    assert substrate_modules == allowed, (
        f"demo_real.py substrate imports must equal {allowed}; got {substrate_modules}"
    )


def test_demo_real_registered_adapters_are_all_real_admissible() -> None:
    """Live check: instantiate each adapter that demo_real imports and
    confirm every provenance is REAL+ADMISSIBLE."""
    tree = _parse("demo_real.py")
    _, modules = _imports(tree)
    substrate_modules = {m for m in modules if m.startswith("substrates.")}
    assert substrate_modules, "demo_real.py imports no substrate module"

    for mod_path in substrate_modules:
        mod = __import__(mod_path, fromlist=["*"])
        found_adapter = False
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if isinstance(obj, type) and attr.endswith("Adapter"):
                prov = getattr(obj, "provenance", None)
                if prov is None:
                    continue
                assert prov.provenance_class == ProvenanceClass.REAL, (
                    f"{attr} provenance_class={prov.provenance_class.value!r} "
                    f"-- demo_real permits REAL only"
                )
                assert prov.claim_status == ClaimStatus.ADMISSIBLE, (
                    f"{attr} claim_status={prov.claim_status.value!r} "
                    f"-- demo_real permits ADMISSIBLE only"
                )
                found_adapter = True
        assert found_adapter, f"{mod_path} exposes no *Adapter class with provenance"


# --------------------------------------------------------------------------
# demo_multi.py -- multi-substrate demo path
# --------------------------------------------------------------------------


def test_demo_multi_uses_mode_demo() -> None:
    tree = _parse("demo_multi.py")
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Neosynaptex":
            for kw in node.keywords:
                if (
                    kw.arg == "mode"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value == "demo"
                ):
                    found = True
    assert found, "demo_multi.py must construct Neosynaptex(mode='demo')"


def test_demo_multi_does_not_import_cns_ai() -> None:
    """Even the permissive demo excludes the downgraded CNS-AI substrate."""
    tree = _parse("demo_multi.py")
    names, modules = _imports(tree)
    forbidden_modules = {"substrates.cns_ai_loop", "substrates.cns_ai_loop.adapter"}
    forbidden_names = {"CnsAiLoopAdapter", "SyntheticCnsAiLoopAdapter"}
    assert not (modules & forbidden_modules)
    assert not (names & forbidden_names)


# --------------------------------------------------------------------------
# Both demos execute cleanly as scripts (no ProvenanceViolation, no crash)
# --------------------------------------------------------------------------


def _zebrafish_data_available() -> bool:
    """Zebrafish .mat corpus is required to actually run either demo.

    CI runners ship without the corpus; tests skip cleanly there. Local
    dev machines with the corpus staged exercise the full pipeline.
    """
    from substrates.zebrafish.adapter import _find_data_dir

    return _find_data_dir() is not None


@pytest.mark.parametrize("script", ["demo_real.py", "demo_multi.py"])
def test_demo_scripts_run_clean(script: str, capsys: pytest.CaptureFixture[str]) -> None:
    if not _zebrafish_data_available():
        pytest.skip("zebrafish .mat corpus not staged (CI runner / bare checkout)")
    runpy.run_path(str(REPO_ROOT / script), run_name="__main__")
    captured = capsys.readouterr()
    # Script must have produced the canonical banner; absence means early exit.
    assert "NEOSYNAPTEX" in captured.out, f"{script} produced no banner output"
