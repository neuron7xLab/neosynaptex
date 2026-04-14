"""Deterministic tests for the canon-reference drift detector."""

from __future__ import annotations

import pathlib
import textwrap

from tools.audit.canon_reference_check import (
    CANON_DOCUMENTS,
    PATH_EXTENSIONS,
    extract_references,
    load_allowlist,
    run_check,
)

# ---------------------------------------------------------------------------
# extract_references
# ---------------------------------------------------------------------------


def test_extract_picks_up_backticked_python_paths():
    text = "See `tools/audit/foo.py` for the verdict."
    assert extract_references(text) == ["tools/audit/foo.py"]


def test_extract_tolerates_symbol_suffix():
    text = "Function `tools/audit/git_sha.py::git_head_sha` canonicalises."
    assert extract_references(text) == ["tools/audit/git_sha.py"]


def test_extract_strips_trailing_punct():
    text = "Load `docs/SYSTEM_PROTOCOL.md`, which defines it."
    assert extract_references(text) == ["docs/SYSTEM_PROTOCOL.md"]


def test_extract_skips_urls():
    text = "See `https://github.com/x/y` for context."
    assert extract_references(text) == []


def test_extract_skips_globs():
    text = "Matches `evidence/*/*.csv` pattern."
    assert extract_references(text) == []


def test_extract_skips_template_placeholders():
    text = "Produces `evidence/replications/<slug>/prereg.yaml`."
    assert extract_references(text) == []


def test_extract_skips_single_word_identifiers():
    text = "The `emit_event` primitive is the API."
    assert extract_references(text) == []


def test_extract_skips_dotted_python_modules_without_slash():
    text = "Module `tools.telemetry.emit` exposes it."
    assert extract_references(text) == []


def test_extract_handles_directory_with_trailing_slash():
    text = "Contents of `evidence/levin_bridge/` are canonical."
    assert extract_references(text) == ["evidence/levin_bridge/"]


def test_extract_deduplicates():
    text = "`tools/x.py` and later `tools/x.py` again."
    assert extract_references(text) == ["tools/x.py"]


def test_extract_ignores_code_fences():
    # Triple backticks are NOT single-backtick refs.
    text = textwrap.dedent(
        """\
        Some prose.

        ```python
        path = "tools/audit/foo.py"
        ```
        """
    )
    assert extract_references(text) == []


def test_path_extensions_has_known_set():
    # Guards against accidental removal of core extensions.
    assert {".py", ".md", ".yaml", ".json", ".csv"} <= PATH_EXTENSIONS


# ---------------------------------------------------------------------------
# load_allowlist
# ---------------------------------------------------------------------------


def test_load_allowlist_empty_when_file_missing(tmp_path):
    assert load_allowlist(tmp_path / "not_there.yaml") == frozenset()


def test_load_allowlist_reads_paths(tmp_path):
    body = textwrap.dedent(
        """\
        schema_version: 1
        allowed_missing:
          - path: evidence/future_artefact.md
            rationale: not required at scaffold commit
          - path: notebooks/future.ipynb
            rationale: generated at run time
        """
    )
    path = tmp_path / "allow.yaml"
    path.write_text(body, encoding="utf-8")
    entries = load_allowlist(path)
    assert entries == frozenset({"evidence/future_artefact.md", "notebooks/future.ipynb"})


def test_load_allowlist_malformed_returns_empty(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("not: valid: yaml: ::::", encoding="utf-8")
    # Malformed → empty (strict fallback). The check then proceeds
    # as if no paths are allowlisted — so a real drift is NOT masked
    # by a broken allowlist.
    assert load_allowlist(path) == frozenset()


# ---------------------------------------------------------------------------
# run_check
# ---------------------------------------------------------------------------


def test_run_check_flags_broken_reference(tmp_path):
    doc = tmp_path / "docs" / "CANONICAL_POSITION.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("See `tools/audit/missing.py` for details.\n", encoding="utf-8")

    code, msg = run_check(
        repo_root=tmp_path,
        documents=("docs/CANONICAL_POSITION.md",),
        allowlist_path=tmp_path / "no_allowlist.yaml",
    )
    assert code == 2
    assert "tools/audit/missing.py" in msg
    assert "CANONICAL_POSITION.md" in msg


def test_run_check_passes_when_reference_resolves(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "real.py").write_text("# exists\n")
    doc = tmp_path / "docs" / "CANONICAL_POSITION.md"
    doc.write_text("See `tools/real.py`.\n", encoding="utf-8")

    code, msg = run_check(
        repo_root=tmp_path,
        documents=("docs/CANONICAL_POSITION.md",),
        allowlist_path=tmp_path / "no_allowlist.yaml",
    )
    assert code == 0, msg


def test_run_check_allowlist_exempts_missing_path(tmp_path):
    (tmp_path / "docs").mkdir()
    doc = tmp_path / "docs" / "CANONICAL_POSITION.md"
    doc.write_text("See `evidence/future.md` (later).\n", encoding="utf-8")
    allow = tmp_path / "allow.yaml"
    allow.write_text(
        textwrap.dedent(
            """\
            schema_version: 1
            allowed_missing:
              - path: evidence/future.md
                rationale: not required at scaffold commit
            """
        ),
        encoding="utf-8",
    )

    code, msg = run_check(
        repo_root=tmp_path,
        documents=("docs/CANONICAL_POSITION.md",),
        allowlist_path=allow,
    )
    assert code == 0, msg


def test_run_check_missing_document_itself_flagged(tmp_path):
    code, msg = run_check(
        repo_root=tmp_path,
        documents=("docs/nonexistent.md",),
        allowlist_path=tmp_path / "no_allowlist.yaml",
    )
    assert code == 2
    assert "doc itself missing" in msg


# ---------------------------------------------------------------------------
# Live repo invariant
# ---------------------------------------------------------------------------


def test_repo_canonical_state_passes_canon_reference_check():
    code, msg = run_check()
    assert code == 0, msg


def test_canon_documents_list_points_at_real_files():
    """Every entry in CANON_DOCUMENTS MUST exist on disk.

    Guards against adding a canon doc to the list without committing
    the doc itself.
    """

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    for rel in CANON_DOCUMENTS:
        assert (repo_root / rel).is_file(), f"CANON_DOCUMENTS lists {rel} but file does not exist"
