"""Deterministic tests for the declarative telemetry adoption gate."""

from __future__ import annotations

import json
import pathlib
import textwrap

import pytest

from tools.audit.telemetry_adoption import (
    EMIT_MODULE,
    TRACKED_SYMBOLS,
    IntegrityError,
    discover_call_sites,
    load_manifest,
    run_check,
)


def _write_manifest(tmp_path: pathlib.Path, body: str) -> pathlib.Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(body, encoding="utf-8")
    return path


_EMPTY_MANIFEST = textwrap.dedent(
    """\
    schema_version: 1
    spec: docs/protocols/telemetry_spine_spec.md
    checker: tools/audit/telemetry_adoption.py
    emit_sites: []
    """
)


def _mk_module(root: pathlib.Path, rel: str, source: str) -> pathlib.Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_tracked_symbols_match_spec():
    assert {"emit_event", "span"} == TRACKED_SYMBOLS
    assert EMIT_MODULE == "tools.telemetry.emit"


# ---------------------------------------------------------------------------
# discover_call_sites — AST correctness
# ---------------------------------------------------------------------------


def test_discovers_direct_emit_event_call(tmp_path):
    _mk_module(
        tmp_path,
        "producer/worker.py",
        """
        from tools.telemetry.emit import emit_event


        def work():
            emit_event("substrate.x.run.start", "x")
        """,
    )
    sites = discover_call_sites(tmp_path)
    assert sites == [{"path": "producer/worker.py", "line": 6, "symbol": "emit_event"}]


def test_discovers_span_context_manager(tmp_path):
    _mk_module(
        tmp_path,
        "producer/worker.py",
        """
        from tools.telemetry.emit import span


        def work():
            with span("substrate.x.run", "x"):
                pass
        """,
    )
    sites = discover_call_sites(tmp_path)
    assert sites == [{"path": "producer/worker.py", "line": 6, "symbol": "span"}]


def test_ignores_modules_that_do_not_import_from_emit(tmp_path):
    # Uses names that LOOK like telemetry calls but come from a
    # different module. Must not be flagged.
    _mk_module(
        tmp_path,
        "unrelated/worker.py",
        """
        def emit_event(*_args, **_kwargs):
            return None


        def span(*_args, **_kwargs):
            return None


        def work():
            emit_event("x", "y")
            span("a", "b")
        """,
    )
    sites = discover_call_sites(tmp_path)
    assert sites == []


def test_ignores_docstring_and_comment_mentions(tmp_path):
    # Mentions the primitives in docstrings and comments but never
    # imports them. Grep would false-positive; AST correctly ignores.
    _mk_module(
        tmp_path,
        "docs/worker.py",
        '''
        """This module discusses emit_event and span.

        >>> # emit_event("foo", "bar")
        """


        def work():
            # we would emit_event here but don't
            pass
        ''',
    )
    sites = discover_call_sites(tmp_path)
    assert sites == []


def test_handles_alias_import(tmp_path):
    _mk_module(
        tmp_path,
        "producer/aliased.py",
        """
        from tools.telemetry.emit import emit_event as telemetry_emit


        def work():
            telemetry_emit("substrate.x.run.start", "x")
        """,
    )
    sites = discover_call_sites(tmp_path)
    assert sites == [{"path": "producer/aliased.py", "line": 6, "symbol": "telemetry_emit"}]


def test_excludes_tests_tree(tmp_path):
    _mk_module(
        tmp_path,
        "tests/telemetry/test_x.py",
        """
        from tools.telemetry.emit import emit_event


        def test_x():
            emit_event("a.b.c.start", "x")
        """,
    )
    sites = discover_call_sites(tmp_path)
    assert sites == []


def test_skips_files_with_syntax_errors(tmp_path):
    (tmp_path / "broken.py").write_text("def oops(:\n    pass\n", encoding="utf-8")
    _mk_module(
        tmp_path,
        "producer/worker.py",
        """
        from tools.telemetry.emit import emit_event


        def work():
            emit_event("substrate.x.run.start", "x")
        """,
    )
    sites = discover_call_sites(tmp_path)
    # Broken file is skipped; valid file is found.
    assert sites == [{"path": "producer/worker.py", "line": 6, "symbol": "emit_event"}]


# ---------------------------------------------------------------------------
# Manifest parse
# ---------------------------------------------------------------------------


def test_load_manifest_empty(tmp_path):
    path = _write_manifest(tmp_path, _EMPTY_MANIFEST)
    assert load_manifest(path) == []


def test_load_manifest_with_entries(tmp_path):
    body = textwrap.dedent(
        """\
        schema_version: 1
        spec: docs/protocols/telemetry_spine_spec.md
        checker: tools/audit/telemetry_adoption.py
        emit_sites:
          - path: substrates/bridge/levin_runner.py
            line: 382
            symbol: emit_event
          - path: tools/audit/pr_body_check.py
            line: 141
            symbol: span
        """
    )
    path = _write_manifest(tmp_path, body)
    entries = load_manifest(path)
    assert len(entries) == 2
    assert entries[0]["path"] == "substrates/bridge/levin_runner.py"
    assert entries[0]["line"] == 382
    assert entries[0]["symbol"] == "emit_event"


def test_load_manifest_rejects_bad_symbol(tmp_path):
    body = textwrap.dedent(
        """\
        schema_version: 1
        emit_sites:
          - path: x.py
            line: 1
            symbol: not_tracked
        """
    )
    path = _write_manifest(tmp_path, body)
    with pytest.raises(IntegrityError, match="symbol"):
        load_manifest(path)


def test_load_manifest_rejects_missing_key(tmp_path):
    body = textwrap.dedent(
        """\
        schema_version: 1
        emit_sites:
          - path: x.py
            symbol: emit_event
        """
    )
    path = _write_manifest(tmp_path, body)
    with pytest.raises(IntegrityError, match="missing keys"):
        load_manifest(path)


def test_load_manifest_rejects_non_int_line(tmp_path):
    body = textwrap.dedent(
        """\
        schema_version: 1
        emit_sites:
          - path: x.py
            line: not_a_number
            symbol: emit_event
        """
    )
    path = _write_manifest(tmp_path, body)
    with pytest.raises(IntegrityError, match="line must be an int"):
        load_manifest(path)


# ---------------------------------------------------------------------------
# run_check
# ---------------------------------------------------------------------------


def test_run_check_empty_both_sides_passes(tmp_path):
    manifest = _write_manifest(tmp_path, _EMPTY_MANIFEST)
    # no .py files under tmp_path
    code, msg = run_check(repo_root=tmp_path, manifest_path=manifest)
    assert code == 0, msg
    assert "0 telemetry emit site(s)" in msg


def test_run_check_flags_unlisted_call_site(tmp_path):
    _mk_module(
        tmp_path,
        "producer/w.py",
        """
        from tools.telemetry.emit import emit_event


        def f():
            emit_event("x.y.z", "s")
        """,
    )
    manifest = _write_manifest(tmp_path, _EMPTY_MANIFEST)
    code, msg = run_check(repo_root=tmp_path, manifest_path=manifest)
    assert code == 2
    assert "present in code but absent from manifest" in msg
    assert "producer/w.py" in msg


def test_run_check_flags_missing_call_site_in_code(tmp_path):
    body = textwrap.dedent(
        """\
        schema_version: 1
        emit_sites:
          - path: producer/w.py
            line: 6
            symbol: emit_event
        """
    )
    manifest = _write_manifest(tmp_path, body)
    # No producer/w.py exists; code has no site.
    code, msg = run_check(repo_root=tmp_path, manifest_path=manifest)
    assert code == 2
    assert "manifest entries with no matching call site" in msg


def test_run_check_passes_when_code_matches_manifest(tmp_path):
    _mk_module(
        tmp_path,
        "producer/w.py",
        """
        from tools.telemetry.emit import emit_event


        def f():
            emit_event("x.y.z", "s")
        """,
    )
    body = textwrap.dedent(
        """\
        schema_version: 1
        emit_sites:
          - path: producer/w.py
            line: 6
            symbol: emit_event
        """
    )
    manifest = _write_manifest(tmp_path, body)
    code, msg = run_check(repo_root=tmp_path, manifest_path=manifest)
    assert code == 0, msg


# ---------------------------------------------------------------------------
# Live repo state
# ---------------------------------------------------------------------------


def test_repo_canonical_state_passes_adoption_gate():
    """Main branch has zero emit sites and an empty manifest. Passes.

    As emit sites land (post-#84 stack), manifest entries are added
    in the same PR. This test would start failing on any PR that
    adds one without the other.
    """

    code, msg = run_check()
    assert code == 0, msg


def test_manifest_ends_with_empty_emit_sites_today():
    """Sanity: the committed manifest declares no production producers.

    This test will need to be updated in the same PR that adds the
    first emit site to main. That coupling is intentional — it makes
    the manifest update visible in the same diff as the wiring.
    """

    entries = load_manifest()
    # NOTE: bump this assertion as emit sites land.
    assert entries == []


def _ignored(s):
    return json.dumps(s, default=str)
