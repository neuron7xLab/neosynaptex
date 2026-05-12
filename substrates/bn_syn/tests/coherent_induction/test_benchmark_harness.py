from pathlib import Path
from benchmarks.coherent_induction_abcd import run_benchmark


def test_benchmark_harness_one_command(tmp_path: Path) -> None:
    out = tmp_path / "bench.jsonl"
    run_benchmark(out)
    assert out.exists()
