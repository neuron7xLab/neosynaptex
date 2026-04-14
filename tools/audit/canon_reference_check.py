"""Canonical documents must not reference paths that do not exist.

Signal contract
---------------

The measurement framework depends on canonical documents pointing at
real code, tests, and ledgers. A reference to
``tools/audit/claim_status_applied.py::git_head_sha`` that names a
function which never existed (precisely the spec drift fixed by the
``git_head_sha`` consolidation PR) is a silent lie: the doc claims a
contract the code does not implement.

This tool walks a fixed list of canonical documents and verifies
that every **backticked path-like reference** inside them points at
a file or directory that exists on disk today.

Scope
-----

* **In-scope canonical documents:**
    - ``CANONICAL_POSITION.md``
    - ``docs/SYSTEM_PROTOCOL.md``
    - ``docs/ADVERSARIAL_CONTROLS.md``
    - ``docs/REPLICATION_PROTOCOL.md``
    - ``docs/EXTERNAL_PRECEDENTS.md``
    - ``docs/protocols/*.md``
* **In-scope references:** strings inside single backticks that look
  like relative paths (contain a ``/`` AND end in a known extension
  OR are a known directory). The ``::symbol`` suffix after a path is
  tolerated but not checked — symbol resolution requires a language
  server, not file existence.
* **Deliberately skipped** (false-positive reduction):
    - URLs (``http://``, ``https://``).
    - Glob patterns (contain ``*`` or ``?``).
    - Template placeholders (contain ``<`` or ``>``).
    - Python-style dotted paths without a slash (``foo.bar.baz``).
    - Single-word identifiers (no slash).
    - Paths ending in ``.git`` (submodule refs).
    - Bare repo-root file mentions like ``README.md`` unless they
      contain a slash (avoid snagging inline prose).

Contract
--------

* **Input.** None.
* **Success.** Exit 0 when every in-scope reference resolves to an
  existing path relative to repo root.
* **Failure.** Exit 2 with a per-document list of broken references.
* **Scope.** Structural. Does not check that the pointed-at file has
  the claimed semantics or the claimed symbol.
"""

from __future__ import annotations

import pathlib
import re
import sys

__all__ = [
    "CANON_DOCUMENTS",
    "PATH_EXTENSIONS",
    "extract_references",
    "load_allowlist",
    "main",
    "run_check",
]

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_ALLOWLIST_PATH = _REPO_ROOT / "tools" / "audit" / "canon_reference_allowlist.yaml"

# The fixed canon set. Adding a new canonical document requires both
# landing the doc and listing it here in the same PR; otherwise the
# gate cannot protect it.
CANON_DOCUMENTS: tuple[str, ...] = (
    "CANONICAL_POSITION.md",
    "docs/SYSTEM_PROTOCOL.md",
    "docs/ADVERSARIAL_CONTROLS.md",
    "docs/REPLICATION_PROTOCOL.md",
    "docs/EXTERNAL_PRECEDENTS.md",
    "docs/protocols/levin_bridge_protocol.md",
    "docs/protocols/telemetry_spine_spec.md",
    "docs/protocols/mfn_plus_productivity_prereg.md",
)

# File extensions that mark a reference as path-like (when the string
# also contains a ``/``). Anything else is treated as prose and
# skipped.
PATH_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".md",
        ".yaml",
        ".yml",
        ".json",
        ".csv",
        ".ipynb",
        ".txt",
        ".toml",
        ".sh",
    }
)

# Trailing punctuation that a Markdown author might put after an
# inline-code reference; strip before checking existence.
_TRAIL_PUNCT = ",.;:!?)"

# Pattern: any run of characters inside single backticks. Markdown
# code fences use triple backticks; those are deliberately excluded
# by the non-greedy single-backtick anchor.
_BACKTICK = re.compile(r"(?<!`)`([^`\n]+?)`(?!`)")


def _looks_like_path(s: str) -> bool:
    if not s or "\n" in s:
        return False
    if s.startswith(("http://", "https://")):
        return False
    if any(c in s for c in ("*", "?", "<", ">")):
        return False
    if s.endswith(".git"):
        return False
    if "/" not in s:
        return False
    # Strip a ``::symbol`` or Markdown-trailing punctuation.
    candidate = s.split("::", 1)[0]
    while candidate and candidate[-1] in _TRAIL_PUNCT:
        candidate = candidate[:-1]
    if "/" not in candidate:
        return False
    # Must end in a known extension OR name a directory (trailing ``/``).
    if candidate.endswith("/"):
        return True
    _, _, ext = candidate.rpartition(".")
    return f".{ext}" in PATH_EXTENSIONS


def _normalise(s: str) -> str:
    candidate = s.split("::", 1)[0]
    while candidate and candidate[-1] in _TRAIL_PUNCT:
        candidate = candidate[:-1]
    return candidate


def extract_references(text: str) -> list[str]:
    """Return the ordered list of path-like backticked references."""

    refs: list[str] = []
    seen: set[str] = set()
    for m in _BACKTICK.finditer(text):
        raw = m.group(1).strip()
        if not _looks_like_path(raw):
            continue
        canon = _normalise(raw)
        if canon in seen:
            continue
        seen.add(canon)
        refs.append(canon)
    return refs


def _check_document(
    doc_rel: str,
    repo_root: pathlib.Path,
    allowed: frozenset[str],
) -> tuple[list[str], list[str]]:
    """Return (checked_refs, broken_refs) for one canonical document."""

    doc_path = repo_root / doc_rel
    if not doc_path.is_file():
        return ([], [f"(doc itself missing: {doc_rel})"])
    text = doc_path.read_text(encoding="utf-8")
    refs = extract_references(text)
    broken: list[str] = []
    for ref in refs:
        if ref in allowed:
            continue
        if not (repo_root / ref).exists():
            broken.append(ref)
    return (refs, broken)


def load_allowlist(path: pathlib.Path = _ALLOWLIST_PATH) -> frozenset[str]:
    """Return the set of intentionally-missing paths.

    Absent file → empty set (allowlist is optional). Malformed file
    → empty set with a stderr note; the check proceeds strict so
    that a broken allowlist does not mask a real drift.
    """

    if not path.is_file():
        return frozenset()
    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except ImportError:  # pragma: no cover - fallback
        data = _parse_allowlist_fallback(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return frozenset()
    entries = data.get("allowed_missing") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return frozenset()
    out: set[str] = set()
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            out.add(entry["path"])
    return frozenset(out)


def _parse_allowlist_fallback(text: str) -> dict:
    # Narrow fallback: find ``- path: <value>`` under
    # ``allowed_missing:`` and ignore everything else.
    entries: list[dict[str, str]] = []
    in_list = False
    for raw in text.splitlines():
        if raw.startswith("allowed_missing:"):
            in_list = True
            continue
        if not in_list:
            continue
        stripped = raw.strip()
        if stripped.startswith("- path:"):
            _, _, val = stripped.partition(":")
            entries.append({"path": val.strip()})
    return {"allowed_missing": entries}


def run_check(
    repo_root: pathlib.Path = _REPO_ROOT,
    documents: tuple[str, ...] = CANON_DOCUMENTS,
    allowlist_path: pathlib.Path | None = None,
) -> tuple[int, str]:
    path = allowlist_path if allowlist_path is not None else _ALLOWLIST_PATH
    allowed = load_allowlist(path)
    total_refs = 0
    fails: list[str] = []
    for doc in documents:
        refs, broken = _check_document(doc, repo_root, allowed)
        total_refs += len(refs)
        if broken:
            fails.append(f"{doc}: " + ", ".join(sorted(broken)))
    if fails:
        return (
            2,
            "DRIFT: broken canonical references — " + "; ".join(fails),
        )
    return (
        0,
        f"OK: {total_refs} canonical reference(s) across "
        f"{len(documents)} document(s), {len(allowed)} allow-listed, all resolve.",
    )


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - CLI
    _ = argv
    code, message = run_check()
    stream = sys.stdout if code == 0 else sys.stderr
    print(message, file=stream)
    return code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
