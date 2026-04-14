"""Declarative adoption gate for the T2 telemetry spine.

Every production call site of
``tools.telemetry.emit.emit_event`` or
``tools.telemetry.emit.span`` outside the test tree MUST be listed
in ``tools/telemetry/adoption_manifest.yaml``. This tool scans the
repo via the Python AST, collects the actual call sites, and
compares the set against the manifest.

Why AST (not grep)?
-------------------

Grep cannot distinguish a real call site from:

* An import line that mentions the symbol.
* A docstring or comment that names the symbol.
* A test fixture or mock.

AST-based discovery eliminates all three false-positive classes by
checking that the name is:

* Bound by an ``import ... emit_event / span`` from
  ``tools.telemetry.emit``.
* Used as the callable of an ``ast.Call`` node.

Contract
--------

* **Input.** None (walks the repo).
* **Success.** Exit 0 when the AST-discovered set of call sites
  equals the manifest set — same paths, same symbols, same count.
* **Failure.** Exit 2 in any of:

  - A call site is present in the code but absent from the
    manifest (code added, manifest not updated).
  - A call site is present in the manifest but absent from the
    code (manifest rotted; code removed or renamed).
  - ``adoption_manifest.yaml`` is malformed.

* **Scope.** Structural. Does NOT verify that the call passes a
  valid ``event_type`` or that the emit actually fires at runtime.
  Does NOT follow indirection through wrappers. Call site is
  defined as a direct textual ``emit_event(...)`` or ``span(...)``
  call in a module that imports those names from
  ``tools.telemetry.emit``.

Excluded paths
--------------

* ``tests/`` — exercisers, not producers.
* ``build/``, ``dist/``, ``.venv/``, ``venv/``, ``__pycache__/``,
  ``node_modules/`` — build / environment noise.
* ``tools/telemetry/emit.py`` — the primitives themselves;
  self-references are not adoption.
"""

from __future__ import annotations

import ast
import pathlib
import sys

__all__ = [
    "EMIT_MODULE",
    "TRACKED_SYMBOLS",
    "IntegrityError",
    "discover_call_sites",
    "load_manifest",
    "main",
    "run_check",
]

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_MANIFEST_PATH = _REPO_ROOT / "tools" / "telemetry" / "adoption_manifest.yaml"

EMIT_MODULE: str = "tools.telemetry.emit"
TRACKED_SYMBOLS: frozenset[str] = frozenset({"emit_event", "span"})

_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        "tests",
        "build",
        "dist",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".git",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".hypothesis",
        ".benchmarks",
        ".playwright-mcp",
    }
)
_EXCLUDED_FILES: frozenset[str] = frozenset(
    {
        # The primitive module itself; self-references are not
        # adoption. If a future refactor moves the primitives, bump
        # this list in the same PR.
        "tools/telemetry/emit.py",
    }
)


class IntegrityError(ValueError):
    """Raised when the manifest cannot be parsed into the expected shape."""


# ---------------------------------------------------------------------------
# AST discovery
# ---------------------------------------------------------------------------


def _imports_from_emit_module(tree: ast.AST) -> set[str]:
    """Return the set of TRACKED_SYMBOLS this module imports from emit."""

    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module != EMIT_MODULE:
                continue
            for alias in node.names:
                name = alias.asname or alias.name
                if alias.name in TRACKED_SYMBOLS:
                    bound.add(name)
    return bound


def _collect_calls(tree: ast.AST, bound: set[str]) -> list[tuple[int, str]]:
    """Return (line, symbol) pairs for each bound-name call site."""

    calls: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in bound:
            calls.append((node.lineno, func.id))
    return calls


def _iter_python_files(repo_root: pathlib.Path) -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for path in repo_root.rglob("*.py"):
        parts = set(path.relative_to(repo_root).parts)
        if parts & _EXCLUDED_DIRS:
            continue
        rel = str(path.relative_to(repo_root))
        if rel in _EXCLUDED_FILES:
            continue
        files.append(path)
    return sorted(files)


def discover_call_sites(repo_root: pathlib.Path = _REPO_ROOT) -> list[dict]:
    """Walk the repo and return ordered call-site records.

    Each record: ``{"path": <rel>, "line": <int>, "symbol": <str>}``.
    Records are sorted by (path, line, symbol) for stable diff output.
    """

    sites: list[dict] = []
    for path in _iter_python_files(repo_root):
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        bound = _imports_from_emit_module(tree)
        if not bound:
            continue
        rel = str(path.relative_to(repo_root))
        for line, symbol in _collect_calls(tree, bound):
            sites.append({"path": rel, "line": line, "symbol": symbol})
    sites.sort(key=lambda r: (r["path"], r["line"], r["symbol"]))
    return sites


# ---------------------------------------------------------------------------
# Manifest IO
# ---------------------------------------------------------------------------


def _load_yaml(text: str) -> dict:
    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(text)
        return {} if data is None else data
    except ImportError:  # pragma: no cover - fallback path
        return _parse_manifest_fallback(text)


def _parse_manifest_fallback(text: str) -> dict:
    """Narrow fallback recognising only the manifest's actual shape."""

    out: dict[str, object] = {}
    emit_sites: list[dict] = []
    in_sites = False
    current: dict[str, object] | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("emit_sites:"):
            in_sites = True
            rest = line.partition(":")[2].strip()
            if rest == "[]":
                out["emit_sites"] = []
                in_sites = False
            continue
        if not in_sites:
            if ":" in line:
                k, _, v = line.partition(":")
                out[k.strip()] = v.strip()
            continue
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        if stripped.startswith("- ") and indent == 2:
            current = {}
            emit_sites.append(current)
            rest = stripped[2:].strip()
            if rest and ":" in rest:
                k, _, v = rest.partition(":")
                current[k.strip()] = v.strip()
            continue
        if current is None:
            continue
        if indent >= 4 and ":" in stripped:
            k, _, v = stripped.partition(":")
            val = v.strip()
            if val.isdigit():
                current[k.strip()] = int(val)
            else:
                current[k.strip()] = val.strip().strip('"').strip("'")
    if "emit_sites" not in out:
        out["emit_sites"] = emit_sites
    return out


def load_manifest(path: pathlib.Path = _MANIFEST_PATH) -> list[dict]:
    if not path.is_file():
        raise IntegrityError(f"manifest not found at {path}")
    data = _load_yaml(path.read_text(encoding="utf-8"))
    emit_sites = data.get("emit_sites")
    if emit_sites is None:
        raise IntegrityError("manifest: missing 'emit_sites' key")
    if not isinstance(emit_sites, list):
        raise IntegrityError("manifest: 'emit_sites' must be a list")
    normalised: list[dict] = []
    for i, entry in enumerate(emit_sites):
        if not isinstance(entry, dict):
            raise IntegrityError(f"manifest entry[{i}] is not a mapping")
        required = {"path", "line", "symbol"}
        if required - entry.keys():
            raise IntegrityError(
                f"manifest entry[{i}] missing keys {sorted(required - entry.keys())}"
            )
        if entry["symbol"] not in TRACKED_SYMBOLS:
            raise IntegrityError(
                f"manifest entry[{i}] symbol {entry['symbol']!r} not in {sorted(TRACKED_SYMBOLS)}"
            )
        try:
            line_int = int(entry["line"])
        except (TypeError, ValueError) as exc:
            raise IntegrityError(
                f"manifest entry[{i}] line must be an int, got {entry['line']!r}"
            ) from exc
        normalised.append(
            {
                "path": str(entry["path"]),
                "line": line_int,
                "symbol": str(entry["symbol"]),
            }
        )
    normalised.sort(key=lambda r: (r["path"], r["line"], r["symbol"]))
    return normalised


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


def run_check(
    repo_root: pathlib.Path = _REPO_ROOT,
    manifest_path: pathlib.Path = _MANIFEST_PATH,
) -> tuple[int, str]:
    try:
        manifest = load_manifest(manifest_path)
    except IntegrityError as exc:
        return 2, f"DRIFT: {exc}"

    discovered = discover_call_sites(repo_root)

    def _as_set(records: list[dict]) -> set[tuple[str, int, str]]:
        return {(r["path"], r["line"], r["symbol"]) for r in records}

    m = _as_set(manifest)
    d = _as_set(discovered)

    unlisted = sorted(d - m)
    missing = sorted(m - d)
    messages: list[str] = []
    if unlisted:
        messages.append(
            "call sites present in code but absent from manifest: "
            + ", ".join(f"{p}:{ln}:{s}" for (p, ln, s) in unlisted)
        )
    if missing:
        messages.append(
            "manifest entries with no matching call site in code: "
            + ", ".join(f"{p}:{ln}:{s}" for (p, ln, s) in missing)
        )

    if messages:
        return 2, "DRIFT: " + "; ".join(messages)

    return 0, f"OK: {len(discovered)} telemetry emit site(s) adopted and manifested."


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - CLI
    _ = argv
    code, message = run_check()
    stream = sys.stdout if code == 0 else sys.stderr
    print(message, file=stream)
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
