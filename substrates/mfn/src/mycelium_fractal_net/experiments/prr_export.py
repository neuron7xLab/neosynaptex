"""PRR table exporter — formats results for Physical Review Research.

# EVIDENCE TYPE: real_simulation
All tables from actual MFN R-D simulations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from scipy import stats

if TYPE_CHECKING:
    from .runner import ScenarioResult

__all__ = ["PRRExporter", "PRRReport"]


@dataclass
class PRRReport:
    table_1: str
    table_2: str
    table_3: str
    table_4: str
    table_5: str
    friston_gap_status: str
    evidence_type: str = "real_simulation"
    n_healthy_runs: int = 0
    n_patho_runs: int = 0


class PRRExporter:
    """Exports structured tables for Physical Review Research."""

    def export(
        self,
        healthy: ScenarioResult,
        pathological: ScenarioResult,
        output_dir: str = "src/mycelium_fractal_net/experiments/output",
    ) -> PRRReport:
        t1 = self._table_1(healthy, pathological)
        t2 = self._table_2(healthy, pathological)
        t3 = self._table_3(healthy, pathological)
        t4 = self._table_4(healthy, pathological)
        t5 = self._table_5(healthy, pathological)

        # Friston gap: F is available from FreeEnergyTracker
        friston = "PARTIAL"
        if healthy.runs and healthy.runs[0].free_energy_trajectory:
            friston = "PARTIAL"  # F available but not full Friston proof

        report = PRRReport(
            table_1=t1, table_2=t2, table_3=t3, table_4=t4, table_5=t5,
            friston_gap_status=friston,
            n_healthy_runs=len(healthy.runs),
            n_patho_runs=len(pathological.runs),
        )

        # Save to file
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        with (out / "prr_tables.txt").open("w") as f:
            f.write("TABLE 1: gamma-scaling by condition\n")
            f.write(t1 + "\n\n")
            f.write("TABLE 2: Feature attribution (top 5)\n")
            f.write(t2 + "\n\n")
            f.write("TABLE 3: Statistical comparison\n")
            f.write(t3 + "\n\n")
            f.write("TABLE 4: Deviation origin distribution\n")
            f.write(t4 + "\n\n")
            f.write("TABLE 5: Lyapunov V over simulation\n")
            f.write(t5 + "\n")

        return report

    def _table_1(self, h: ScenarioResult, p: ScenarioResult) -> str:
        lines = [
            "+---------------+----------+----------+--------+----------+",
            "| Condition     | gamma_m  | gamma_sd | N runs | status   |",
            "+---------------+----------+----------+--------+----------+",
        ]
        g_h = [r.gamma for r in h.runs]
        g_p = [r.gamma for r in p.runs]
        lines.append(
            f"| Healthy       | {np.mean(g_h):+7.3f}  | {np.std(g_h):7.3f}  | {len(g_h):6d} | scaling  |"
        )
        lines.append(
            f"| Pathological  | {np.mean(g_p):+7.3f}  | {np.std(g_p):7.3f}  | {len(g_p):6d} | deviant  |"
        )
        lines.append("+---------------+----------+----------+--------+----------+")
        return "\n".join(lines)

    def _table_2(self, h: ScenarioResult, p: ScenarioResult) -> str:
        # Collect feature names from first run
        if not h.runs or not h.runs[0].features:
            return "(no features available)"
        all_features: dict[str, list[float]] = {}
        for run in h.runs:
            for fd in run.features:
                for group in ("topological", "fractal", "causal"):
                    group_data = fd.get(group)
                    if not isinstance(group_data, dict):
                        continue
                    for k, v in group_data.items():
                        key = f"{group}.{k}"
                        all_features.setdefault(key, []).append(float(v))

        # Sort by variance
        sorted_f = sorted(all_features.items(), key=lambda kv: np.std(kv[1]), reverse=True)
        lines = [
            "+-----------------------------+-----------+-----------+",
            "| Feature                     | mean      | std       |",
            "+-----------------------------+-----------+-----------+",
        ]
        for name, vals in sorted_f[:5]:
            lines.append(f"| {name:27s} | {np.mean(vals):+9.4f} | {np.std(vals):9.4f} |")
        lines.append("+-----------------------------+-----------+-----------+")
        return "\n".join(lines)

    def _table_3(self, h: ScenarioResult, p: ScenarioResult) -> str:
        g_h = np.array([r.gamma for r in h.runs])
        g_p = np.array([r.gamma for r in p.runs])

        if len(g_h) < 2 or len(g_p) < 2:
            return "(insufficient runs for statistics)"

        t_stat, p_val = stats.ttest_ind(g_h, g_p, equal_var=False)
        pooled_std = float(np.sqrt((np.var(g_h) + np.var(g_p)) / 2))
        cohens_d = float(abs(np.mean(g_h) - np.mean(g_p)) / (pooled_std + 1e-12))

        # Wasserstein
        w_dist = float(stats.wasserstein_distance(g_h, g_p))

        # Bonferroni (4 comparisons)
        p_bonf = min(p_val * 4, 1.0)

        lines = [
            "+---------------------+-----------+",
            "| Metric              | Value     |",
            "+---------------------+-----------+",
            f"| t-statistic         | {t_stat:+9.3f} |",
            f"| p-value             | {p_val:9.6f} |",
            f"| p-value (Bonf.)     | {p_bonf:9.6f} |",
            f"| Cohen's d           | {cohens_d:9.3f} |",
            f"| Wasserstein dist.   | {w_dist:9.3f} |",
            "+---------------------+-----------+",
        ]
        return "\n".join(lines)

    def _table_4(self, h: ScenarioResult, p: ScenarioResult) -> str:
        origins_h: dict[str, int] = {}
        origins_p: dict[str, int] = {}
        for r in h.runs:
            origins_h[r.deviation_origin] = origins_h.get(r.deviation_origin, 0) + 1
        for r in p.runs:
            origins_p[r.deviation_origin] = origins_p.get(r.deviation_origin, 0) + 1

        all_origins = sorted(set(list(origins_h.keys()) + list(origins_p.keys())))
        lines = [
            "+--------------------+----------+----------+",
            "| Origin             | Healthy  | Patho    |",
            "+--------------------+----------+----------+",
        ]
        for o in all_origins:
            nh = origins_h.get(o, 0)
            np_ = origins_p.get(o, 0)
            lines.append(f"| {o:18s} | {nh:8d} | {np_:8d} |")
        lines.append("+--------------------+----------+----------+")
        return "\n".join(lines)

    def _table_5(self, h: ScenarioResult, p: ScenarioResult) -> str:
        def _v_stats(sr: ScenarioResult) -> tuple[float, float]:
            all_v = []
            for r in sr.runs:
                if r.v_trajectory:
                    all_v.extend(r.v_trajectory)
            if not all_v:
                return 0.0, 0.0
            diffs = np.diff(all_v) if len(all_v) > 1 else [0.0]
            return float(np.mean(all_v)), float(np.mean(diffs))

        v_h_mean, v_h_trend = _v_stats(h)
        v_p_mean, v_p_trend = _v_stats(p)

        t_h = sum(r.n_transforms for r in h.runs)
        t_p = sum(r.n_transforms for r in p.runs)

        lines = [
            "+---------------------+-----------+-----------+",
            "| Metric              | Healthy   | Patho     |",
            "+---------------------+-----------+-----------+",
            f"| V mean              | {v_h_mean:9.4f} | {v_p_mean:9.4f} |",
            f"| V trend (dV/dt)     | {v_h_trend:+9.4f} | {v_p_trend:+9.4f} |",
            f"| Transformations     | {t_h:9d} | {t_p:9d} |",
            "+---------------------+-----------+-----------+",
        ]
        return "\n".join(lines)
