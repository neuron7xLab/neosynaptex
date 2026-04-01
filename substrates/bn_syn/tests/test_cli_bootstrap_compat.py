from __future__ import annotations

from types import SimpleNamespace

import pytest

from bnsyn import cli


def test_cmd_run_experiment_compat_without_optional_attrs(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str | None]] = []

    def fake_run_from_yaml(config: str, output: str | None) -> None:
        calls.append((config, output))

    monkeypatch.setitem(
        __import__("sys").modules,
        "bnsyn.experiments.declarative",
        SimpleNamespace(run_from_yaml=fake_run_from_yaml, run_canonical_live_bundle=lambda *_, **__: {}),
    )

    args = SimpleNamespace(config="examples/configs/quickstart.yaml", output=None)
    rc = cli._cmd_run_experiment(args)

    assert rc == 0
    assert calls == [("examples/configs/quickstart.yaml", None)]


def test_cmd_run_experiment_routes_profile_canonical(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str | object] = []

    def fake_live_bundle(config: str | object, output: str | None, **__: object) -> dict[str, str]:
        seen.append(config)
        return {"artifact_dir": str(output)}

    monkeypatch.setitem(
        __import__("sys").modules,
        "bnsyn.experiments.declarative",
        SimpleNamespace(run_from_yaml=lambda *_, **__: None, run_canonical_live_bundle=fake_live_bundle),
    )

    args = SimpleNamespace(config=None, profile="canonical", output=None, plot=False, export_proof=False)
    rc = cli._cmd_run_experiment(args)

    assert rc == 0
    assert len(seen) == 1
    assert str(seen[0]).endswith("configs/canonical_profile.yaml")


def test_cmd_run_experiment_missing_config_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace()
    rc = cli._cmd_run_experiment(args)
    captured = capsys.readouterr()

    assert rc == 2
    assert "provide CONFIG or --profile canonical" in captured.err


def test_cmd_run_experiment_prints_reserved_flag_notices(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_run_from_yaml(config: str, output: str | None) -> None:
        del config, output

    monkeypatch.setitem(
        __import__("sys").modules,
        "bnsyn.experiments.declarative",
        SimpleNamespace(run_from_yaml=fake_run_from_yaml, run_canonical_live_bundle=lambda *_, **__: {}),
    )

    args = SimpleNamespace(config="examples/configs/quickstart.yaml", output=None, plot=True, export_proof=True, profile=None)
    rc = cli._cmd_run_experiment(args)
    captured = capsys.readouterr()

    assert rc == 0
    assert "--plot only applies to --profile canonical" in captured.err
    assert "--export-proof only applies to --profile canonical" in captured.err


def test_cmd_run_experiment_canonical_prints_plot_notice(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setitem(
        __import__("sys").modules,
        "bnsyn.experiments.declarative",
        SimpleNamespace(run_from_yaml=lambda *_, **__: None, run_canonical_live_bundle=lambda *_, **__: {"artifact_dir": "x"}),
    )
    args = SimpleNamespace(config=None, profile="canonical", output=None, plot=True, export_proof=False)
    rc = cli._cmd_run_experiment(args)
    captured = capsys.readouterr()

    assert rc == 0
    assert "--plot acknowledged; canonical live-run plots are emitted by default" in captured.err


def test_cmd_run_experiment_canonical_emits_proof_with_export_flag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setitem(
        __import__("sys").modules,
        "bnsyn.experiments.declarative",
        SimpleNamespace(run_from_yaml=lambda *_, **__: None, run_canonical_live_bundle=lambda *_, **__: {"artifact_dir": "x"}),
    )
    args = SimpleNamespace(config=None, profile="canonical", output=None, plot=False, export_proof=True)
    rc = cli._cmd_run_experiment(args)
    captured = capsys.readouterr()

    assert rc == 0
    assert "--export-proof remains reserved; canonical run currently emits a live-run bundle" not in captured.err


def test_cmd_run_experiment_canonical_uses_default_output_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str | None] = []

    def fake_bundle(_: str, out: str | None, **__: object) -> dict[str, str]:
        seen.append(out)
        return {"artifact_dir": str(out)}

    monkeypatch.setitem(
        __import__("sys").modules,
        "bnsyn.experiments.declarative",
        SimpleNamespace(run_from_yaml=lambda *_, **__: None, run_canonical_live_bundle=fake_bundle),
    )

    args = SimpleNamespace(config=None, profile="canonical", output=None, plot=False, export_proof=False)
    rc = cli._cmd_run_experiment(args)

    assert rc == 0
    assert seen == ["artifacts/canonical_run"]


def test_cmd_run_experiment_canonical_returns_1_on_bundle_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def raise_bundle(_: str, __: str | None, **___: object) -> dict[str, str]:
        raise RuntimeError("bundle failed")

    monkeypatch.setitem(
        __import__("sys").modules,
        "bnsyn.experiments.declarative",
        SimpleNamespace(run_from_yaml=lambda *_, **__: None, run_canonical_live_bundle=raise_bundle),
    )

    args = SimpleNamespace(config=None, profile="canonical", output=None, plot=False, export_proof=False)
    rc = cli._cmd_run_experiment(args)
    captured = capsys.readouterr()

    assert rc == 1
    assert "Error running experiment: bundle failed" in captured.out
