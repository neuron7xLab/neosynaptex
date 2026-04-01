from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from bnsyn import cli
from bnsyn.experiments.emergence import run_emergence_to_disk
from bnsyn.numerics import compute_steps_exact
from bnsyn.viz.emergence_plot import plot_emergence_npz


def test_compute_steps_exact_rejects_fractional_steps() -> None:
    with pytest.raises(ValueError, match="integer multiple"):
        compute_steps_exact(1.25, 0.1)


def test_run_emergence_to_disk_writes_npz_contract(tmp_path: Path) -> None:
    metrics, artifact = run_emergence_to_disk(
        N=20,
        dt_ms=0.1,
        duration_ms=10.0,
        seed=7,
        external_current_pA=410.0,
        output_dir=tmp_path,
    )
    assert set(metrics) == {"sigma_mean", "rate_mean_hz", "sigma_std", "rate_std"}

    artifact_path = Path(artifact)
    assert artifact_path.exists()
    with np.load(artifact_path) as data:
        assert str(data["format_version"].item()) == "1.1.0"
        for key in [
            "spike_steps",
            "spike_neurons",
            "sigma_trace",
            "rate_trace_hz",
            "coherence_trace",
            "dt_ms",
            "steps",
            "N",
            "seed",
            "external_current_pA",
        ]:
            assert key in data.files


def _write_npz(path: Path, *, version: str = "1.1.0") -> None:
    np.savez(
        path,
        format_version=np.asarray(version),
        spike_steps=np.asarray([0, 1, 2], dtype=np.int64),
        spike_neurons=np.asarray([1, 2, 3], dtype=np.int64),
        sigma_trace=np.asarray([1.0, 1.1, 0.9], dtype=np.float64),
        rate_trace_hz=np.asarray([5.0, 6.0, 7.0], dtype=np.float64),
        coherence_trace=np.asarray([0.2, 0.3, 0.4], dtype=np.float64),
        dt_ms=np.asarray(0.1),
        steps=np.asarray(3, dtype=np.int64),
        N=np.asarray(10, dtype=np.int64),
        seed=np.asarray(42, dtype=np.int64),
        external_current_pA=np.asarray(410.0),
    )


def test_plotter_with_matplotlib_shim(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    npz_path = tmp_path / "in.npz"
    png_path = tmp_path / "out.png"
    _write_npz(npz_path)

    class _Ax:
        def scatter(self, *args: object, **kwargs: object) -> None:
            return None

        def plot(self, *args: object, **kwargs: object) -> None:
            return None

        def set_ylabel(self, *args: object, **kwargs: object) -> None:
            return None

        def set_xlabel(self, *args: object, **kwargs: object) -> None:
            return None

        def set_title(self, *args: object, **kwargs: object) -> None:
            return None

    class _PLT:
        def subplots(self, *args: object, **kwargs: object) -> tuple[object, list[_Ax]]:
            return object(), [_Ax(), _Ax(), _Ax()]

        def tight_layout(self) -> None:
            return None

        def savefig(self, path: str | Path, **kwargs: object) -> None:
            Path(path).write_bytes(b"png")

        def close(self, fig: object) -> None:
            _ = fig

    plt_shim = _PLT()
    monkeypatch.setitem(sys.modules, "matplotlib", SimpleNamespace(pyplot=plt_shim))
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", plt_shim)

    plot_emergence_npz(npz_path, png_path)
    assert png_path.exists()


def test_plotter_rejects_wrong_format_version(tmp_path: Path) -> None:
    npz_path = tmp_path / "bad.npz"
    _write_npz(npz_path, version="1.0.0")
    with pytest.raises(ValueError, match="Unsupported format_version"):
        plot_emergence_npz(npz_path, tmp_path / "x.png")


def test_plotter_reports_missing_matplotlib(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    npz_path = tmp_path / "in.npz"
    _write_npz(npz_path)
    monkeypatch.setitem(sys.modules, "matplotlib", None)
    monkeypatch.delitem(sys.modules, "matplotlib.pyplot", raising=False)

    with pytest.raises(RuntimeError, match="Visualization requires matplotlib"):
        plot_emergence_npz(npz_path, tmp_path / "x.png")


def test_cli_emergence_run_via_main(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_args = [
        "bnsyn",
        "emergence-run",
        "--N",
        "24",
        "--dt-ms",
        "0.1",
        "--duration-ms",
        "10.0",
        "--seed",
        "42",
        "--external-current-pA",
        "410.0",
        "--out",
        str(tmp_path),
    ]
    monkeypatch.setattr("sys.argv", test_args)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    report = json.loads((tmp_path / "emergence_run_report.json").read_text(encoding="utf-8"))
    assert Path(report["artifact_npz"]).exists()


def test_cli_emergence_sweep_via_main(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_args = [
        "bnsyn",
        "emergence-sweep",
        "--N",
        "24",
        "--dt-ms",
        "0.1",
        "--duration-ms",
        "10.0",
        "--seed",
        "42",
        "--out",
        str(tmp_path),
    ]
    monkeypatch.setattr("sys.argv", test_args)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    report = json.loads((tmp_path / "emergence_sweep_report.json").read_text(encoding="utf-8"))
    artifacts = [run["artifact_npz"] for run in report["runs"]]
    assert len(artifacts) == len(cli.EMERGENCE_SWEEP_CURRENTS_PA)
    assert len(set(artifacts)) == len(artifacts)
    assert all(Path(path).exists() for path in artifacts)


def test_compute_steps_exact_rejects_nonpositive_dt() -> None:
    with pytest.raises(ValueError, match="dt_ms must be greater than 0"):
        compute_steps_exact(1.0, 0.0)


def test_run_emergence_to_disk_rejects_invalid_inputs(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="seed must be a positive integer"):
        run_emergence_to_disk(
            N=20,
            dt_ms=0.1,
            duration_ms=10.0,
            seed=0,
            external_current_pA=410.0,
            output_dir=tmp_path,
        )
    with pytest.raises(ValueError, match="external_current_pA must be a finite real number"):
        run_emergence_to_disk(
            N=20,
            dt_ms=0.1,
            duration_ms=10.0,
            seed=1,
            external_current_pA=float("nan"),
            output_dir=tmp_path,
        )


def test_plotter_rejects_missing_required_fields(tmp_path: Path) -> None:
    npz_path = tmp_path / "missing.npz"
    np.savez(npz_path, format_version=np.asarray("1.1.0"))
    with pytest.raises(ValueError, match="Missing required NPZ fields"):
        plot_emergence_npz(npz_path, tmp_path / "x.png")


def test_plotter_rejects_shape_invariant_violation(tmp_path: Path) -> None:
    npz_path = tmp_path / "shape_bad.npz"
    np.savez(
        npz_path,
        format_version=np.asarray("1.1.0"),
        spike_steps=np.asarray([0, 1], dtype=np.int64),
        spike_neurons=np.asarray([1], dtype=np.int64),
        sigma_trace=np.asarray([1.0, 1.1, 0.9], dtype=np.float64),
        rate_trace_hz=np.asarray([5.0, 6.0, 7.0], dtype=np.float64),
        coherence_trace=np.asarray([0.2, 0.3, 0.4], dtype=np.float64),
        dt_ms=np.asarray(0.1),
        steps=np.asarray(3, dtype=np.int64),
        N=np.asarray(10, dtype=np.int64),
        seed=np.asarray(42, dtype=np.int64),
        external_current_pA=np.asarray(410.0),
    )
    with pytest.raises(ValueError, match="identical shapes"):
        plot_emergence_npz(npz_path, tmp_path / "x.png")


def test_plotter_rejects_invalid_trace_dimensions(tmp_path: Path) -> None:
    npz_path = tmp_path / "bad_dims.npz"
    np.savez(
        npz_path,
        format_version=np.asarray("1.1.0"),
        spike_steps=np.asarray([0]),
        spike_neurons=np.asarray([0]),
        sigma_trace=np.asarray([[1.0]]),
        rate_trace_hz=np.asarray([5.0]),
        dt_ms=np.asarray(0.1),
        steps=np.asarray(1),
        N=np.asarray(10),
        seed=np.asarray(42),
        external_current_pA=np.asarray(410.0),
    )
    with pytest.raises(ValueError, match="1-D arrays"):
        plot_emergence_npz(npz_path, tmp_path / "out.png")


def test_plotter_rejects_trace_length_mismatch(tmp_path: Path) -> None:
    npz_path = tmp_path / "bad_len.npz"
    np.savez(
        npz_path,
        format_version=np.asarray("1.1.0"),
        spike_steps=np.asarray([]),
        spike_neurons=np.asarray([]),
        sigma_trace=np.asarray([1.0, 2.0]),
        rate_trace_hz=np.asarray([5.0, 6.0]),
        dt_ms=np.asarray(0.1),
        steps=np.asarray(1),
        N=np.asarray(10),
        seed=np.asarray(42),
        external_current_pA=np.asarray(410.0),
    )
    with pytest.raises(ValueError, match="Trace lengths must equal steps"):
        plot_emergence_npz(npz_path, tmp_path / "out.png")


def test_plotter_rejects_out_of_bounds_spikes(tmp_path: Path) -> None:
    npz_path = tmp_path / "bad_spikes.npz"
    np.savez(
        npz_path,
        format_version=np.asarray("1.1.0"),
        spike_steps=np.asarray([5]),
        spike_neurons=np.asarray([0]),
        sigma_trace=np.asarray([1.0]),
        rate_trace_hz=np.asarray([5.0]),
        dt_ms=np.asarray(0.1),
        steps=np.asarray(1),
        N=np.asarray(10),
        seed=np.asarray(42),
        external_current_pA=np.asarray(410.0),
    )
    with pytest.raises(ValueError, match=r"spike_steps values must be in \[0, steps\)"):
        plot_emergence_npz(npz_path, tmp_path / "out.png")


def test_cli_emergence_plot_via_main(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "plot_emergence_npz", lambda i, o: None)
    test_args = [
        "bnsyn",
        "emergence-plot",
        "--input",
        "in.npz",
        "--output",
        str(tmp_path / "out.png"),
    ]
    monkeypatch.setattr("sys.argv", test_args)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0


def test_compute_steps_exact_rejects_tolerance_mismatch() -> None:
    with pytest.raises(ValueError, match="within tolerance"):
        compute_steps_exact(duration_ms=10.0, dt_ms=0.3)


def test_run_emergence_to_disk_rejects_non_real_current(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="finite real number"):
        run_emergence_to_disk(
            N=20,
            dt_ms=0.1,
            duration_ms=10.0,
            seed=1,
            external_current_pA="invalid_type",  # type: ignore[arg-type]
            output_dir=tmp_path,
        )


def test_plotter_rejects_out_of_bounds_neurons(tmp_path: Path) -> None:
    npz_path = tmp_path / "bad_neurons.npz"
    np.savez(
        npz_path,
        format_version=np.asarray("1.1.0"),
        spike_steps=np.asarray([0]),
        spike_neurons=np.asarray([999]),
        sigma_trace=np.asarray([1.0]),
        rate_trace_hz=np.asarray([5.0]),
        dt_ms=np.asarray(0.1),
        steps=np.asarray(1),
        N=np.asarray(10),
        seed=np.asarray(42),
        external_current_pA=np.asarray(410.0),
    )
    with pytest.raises(ValueError, match=r"spike_neurons values must be in \[0, N\)"):
        plot_emergence_npz(npz_path, tmp_path / "out.png")
