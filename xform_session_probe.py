"""X-Form Session Gamma Probe — measure gamma-scaling on human-AI session data.

Extracts session metrics from ChatGPT conversations.json export,
classifies productive vs non-productive sessions, and runs
gamma_probe to test hypothesis: productive CNS-AI loop has gamma ~ 1.0.

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import theilslopes

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_BOOTSTRAP_N = 500
_MIN_PAIRS = 8
_LOG_RANGE_GATE = 0.5
_R2_GATE = 0.3  # relaxed for noisy human data


# ---------------------------------------------------------------------------
# Session record
# ---------------------------------------------------------------------------
@dataclass
class SessionRecord:
    """One human-AI conversation session."""
    session_id: str
    title: str
    create_time: float
    update_time: float
    n_turns: int  # total message count
    n_human: int  # human messages
    n_ai: int  # AI messages
    human_chars: int  # total chars in human messages
    ai_chars: int  # total chars in AI messages
    human_tokens_approx: int  # approx token count (chars / 4)
    ai_tokens_approx: int
    has_code: bool  # AI produced code blocks
    has_artifact: bool  # session produced a tangible artifact
    complexity: float  # topo-like metric: information complexity
    cost: float  # thermo-like metric: effort per unit complexity
    duration_min: float  # session duration in minutes
    model: str  # model used


# ---------------------------------------------------------------------------
# Extract sessions from ChatGPT conversations.json
# ---------------------------------------------------------------------------
def extract_chatgpt_sessions(path: str) -> List[SessionRecord]:
    """Parse ChatGPT export conversations.json into SessionRecord list."""
    with open(path, encoding="utf-8") as f:
        conversations = json.load(f)

    records: List[SessionRecord] = []

    for conv in conversations:
        cid = conv.get("conversation_id", "unknown")
        title = conv.get("title", "untitled")
        create_time = conv.get("create_time", 0) or 0
        update_time = conv.get("update_time", 0) or 0
        model = conv.get("default_model_slug", "unknown") or "unknown"
        mapping = conv.get("mapping", {})

        n_human = 0
        n_ai = 0
        human_chars = 0
        ai_chars = 0
        has_code = False

        for node_id, node in mapping.items():
            msg = node.get("message")
            if msg is None:
                continue
            role = msg.get("author", {}).get("role", "")
            content = msg.get("content", {})

            # Extract text from content parts
            text = ""
            parts = content.get("parts", [])
            for part in parts:
                if isinstance(part, str):
                    text += part
                elif isinstance(part, dict):
                    text += part.get("text", "")

            if not text.strip():
                continue

            if role == "user":
                n_human += 1
                human_chars += len(text)
            elif role == "assistant":
                n_ai += 1
                ai_chars += len(text)
                if "```" in text:
                    has_code = True

        n_turns = n_human + n_ai
        if n_turns < 2:
            continue

        # Approximate tokens
        human_tok = max(1, human_chars // 4)
        ai_tok = max(1, ai_chars // 4)

        # Duration
        duration_min = max(0.1, (update_time - create_time) / 60.0) if update_time > create_time else 1.0

        # --- Artifact detection ---
        # Productive session: has code blocks OR title suggests protocol/code/system
        artifact_keywords = [
            "code", "script", "model", "system", "protocol", "engine",
            "module", "api", "pipeline", "architecture", "framework",
            "implementation", "deploy", "build", "config", "setup",
            "test", "benchmark", "analysis", "experiment",
            "neuron", "mycelium", "fractal", "synapse", "plasticity",
            "kuramoto", "gamma", "nfi", "neosynaptex",
        ]
        title_lower = title.lower() if title else ""
        title_has_keyword = any(kw in title_lower for kw in artifact_keywords)
        has_artifact = has_code or title_has_keyword

        # --- Complexity metric (topo-like) ---
        # Information density: unique concepts per message
        # Higher = more complex conversation
        all_text = ""
        for node_id, node in mapping.items():
            msg = node.get("message")
            if msg is None:
                continue
            parts = msg.get("content", {}).get("parts", [])
            for part in parts:
                if isinstance(part, str):
                    all_text += part + " "

        # Vocabulary richness as complexity proxy
        words = re.findall(r'\b\w{3,}\b', all_text.lower())
        unique_words = len(set(words))
        total_words = max(1, len(words))
        vocab_ratio = unique_words / total_words  # type-token ratio
        complexity = math.log1p(unique_words) * vocab_ratio * math.log1p(n_turns)

        # --- Cost metric (thermo-like) ---
        # Effort: total chars produced per unit of complexity
        total_chars = max(1, human_chars + ai_chars)
        if complexity > 0.01:
            cost = total_chars / (complexity * n_turns)
        else:
            cost = total_chars

        records.append(SessionRecord(
            session_id=cid,
            title=title,
            create_time=create_time,
            update_time=update_time,
            n_turns=n_turns,
            n_human=n_human,
            n_ai=n_ai,
            human_chars=human_chars,
            ai_chars=ai_chars,
            human_tokens_approx=human_tok,
            ai_tokens_approx=ai_tok,
            has_code=has_code,
            has_artifact=has_artifact,
            complexity=complexity,
            cost=cost,
            duration_min=duration_min,
            model=model,
        ))

    return records


# ---------------------------------------------------------------------------
# Gamma probe
# ---------------------------------------------------------------------------
def gamma_probe(
    complexities: np.ndarray,
    costs: np.ndarray,
    seed: int = 42,
) -> Dict:
    """Run gamma scaling analysis: cost ~ complexity^(-gamma).

    Delegates to canonical core.gamma.compute_gamma() (Hole 4/11 fix).
    Adds session-specific verdict logic on top.

    Returns dict with gamma, r2, ci_low, ci_high, n_valid, verdict.
    """
    from core.gamma import compute_gamma as _canonical_gamma

    r = _canonical_gamma(
        complexities,
        costs,
        min_pairs=_MIN_PAIRS,
        log_range_gate=_LOG_RANGE_GATE,
        r2_gate=_R2_GATE,
        bootstrap_n=_BOOTSTRAP_N,
        seed=seed,
    )

    result: Dict = {
        "gamma": round(r.gamma, 4) if np.isfinite(r.gamma) else float("nan"),
        "r2": round(r.r2, 4) if np.isfinite(r.r2) else float("nan"),
        "ci_low": round(r.ci_low, 4) if np.isfinite(r.ci_low) else float("nan"),
        "ci_high": round(r.ci_high, 4) if np.isfinite(r.ci_high) else float("nan"),
        "n_valid": r.n_valid,
        "verdict": r.verdict,
    }

    # Session-specific verdict refinement for human-AI data
    if r.verdict not in ("INSUFFICIENT_DATA", "INSUFFICIENT_RANGE", "LOW_R2"):
        if r.ci_low <= 1.0 <= r.ci_high:
            result["verdict"] = "GAMMA_CONTAINS_UNITY"
        elif abs(r.gamma - 1.0) < 0.3:
            result["verdict"] = "GAMMA_NEAR_UNITY"
        else:
            result["verdict"] = "GAMMA_DIVERGENT"

    return result


# ---------------------------------------------------------------------------
# Full analysis pipeline
# ---------------------------------------------------------------------------
def run_analysis(conversations_path: str) -> Dict:
    """Full X-Form session analysis pipeline.

    Steps:
        1. Extract sessions
        2. Classify productive vs non-productive
        3. Run gamma_probe on each group
        4. Compare gammas
        5. Return structured report
    """
    sessions = extract_chatgpt_sessions(conversations_path)

    if not sessions:
        return {"error": "No sessions found"}

    # Split by productivity
    productive = [s for s in sessions if s.has_artifact]
    nonproductive = [s for s in sessions if not s.has_artifact]

    report: Dict = {
        "total_sessions": len(sessions),
        "productive_sessions": len(productive),
        "nonproductive_sessions": len(nonproductive),
        "date_range": {
            "start": min(s.create_time for s in sessions),
            "end": max(s.create_time for s in sessions),
        },
        "models_used": list(set(s.model for s in sessions)),
    }

    # Session-level stats
    report["productive_stats"] = _group_stats(productive)
    report["nonproductive_stats"] = _group_stats(nonproductive)

    # Gamma probe: ALL sessions
    all_complexities = np.array([s.complexity for s in sessions])
    all_costs = np.array([s.cost for s in sessions])
    report["gamma_all"] = gamma_probe(all_complexities, all_costs, seed=42)

    # Gamma probe: PRODUCTIVE only
    if len(productive) >= _MIN_PAIRS:
        prod_c = np.array([s.complexity for s in productive])
        prod_k = np.array([s.cost for s in productive])
        report["gamma_productive"] = gamma_probe(prod_c, prod_k, seed=43)
    else:
        report["gamma_productive"] = {"verdict": "INSUFFICIENT_DATA", "n_valid": len(productive)}

    # Gamma probe: NON-PRODUCTIVE only
    if len(nonproductive) >= _MIN_PAIRS:
        np_c = np.array([s.complexity for s in nonproductive])
        np_k = np.array([s.cost for s in nonproductive])
        report["gamma_nonproductive"] = gamma_probe(np_c, np_k, seed=44)
    else:
        report["gamma_nonproductive"] = {"verdict": "INSUFFICIENT_DATA", "n_valid": len(nonproductive)}

    # Delta gamma
    g_prod = report["gamma_productive"].get("gamma", float("nan"))
    g_nonprod = report["gamma_nonproductive"].get("gamma", float("nan"))
    if np.isfinite(g_prod) and np.isfinite(g_nonprod):
        report["delta_gamma"] = round(abs(g_prod - g_nonprod), 4)
        report["productive_closer_to_unity"] = abs(g_prod - 1.0) < abs(g_nonprod - 1.0)
    else:
        report["delta_gamma"] = float("nan")
        report["productive_closer_to_unity"] = None

    # Top 10 most productive sessions (by complexity)
    top10 = sorted(productive, key=lambda s: s.complexity, reverse=True)[:10]
    report["top10_productive"] = [
        {
            "title": s.title,
            "turns": s.n_turns,
            "complexity": round(s.complexity, 2),
            "cost": round(s.cost, 2),
            "has_code": s.has_code,
            "model": s.model,
        }
        for s in top10
    ]

    # Per-session detail for export
    report["sessions"] = [
        {
            "id": s.session_id,
            "title": s.title,
            "turns": s.n_turns,
            "human_chars": s.human_chars,
            "ai_chars": s.ai_chars,
            "complexity": round(s.complexity, 4),
            "cost": round(s.cost, 4),
            "has_artifact": s.has_artifact,
            "has_code": s.has_code,
            "model": s.model,
            "duration_min": round(s.duration_min, 1),
        }
        for s in sessions
    ]

    return report


def _group_stats(sessions: List[SessionRecord]) -> Dict:
    """Compute summary stats for a group of sessions."""
    if not sessions:
        return {"count": 0}
    turns = [s.n_turns for s in sessions]
    complexities = [s.complexity for s in sessions]
    costs = [s.cost for s in sessions]
    durations = [s.duration_min for s in sessions]
    return {
        "count": len(sessions),
        "turns_mean": round(float(np.mean(turns)), 1),
        "turns_median": round(float(np.median(turns)), 1),
        "complexity_mean": round(float(np.mean(complexities)), 2),
        "complexity_std": round(float(np.std(complexities)), 2),
        "cost_mean": round(float(np.mean(costs)), 2),
        "cost_std": round(float(np.std(costs)), 2),
        "duration_mean_min": round(float(np.mean(durations)), 1),
        "code_fraction": round(sum(1 for s in sessions if s.has_code) / len(sessions), 3),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    conv_path = "/home/neuro7/Downloads/DATA/01_RESEARCH/agi-architecture/neuron7x-academic/452ae4af57bcadcce016a66600fd9f44a2adbe0e63289d775e388d346c107c73-2025-03-10-14-02-22-2b06f10965494b3c867b79583baed5ca/conversations.json"

    if len(sys.argv) > 1:
        conv_path = sys.argv[1]

    print(f"Loading: {conv_path}")
    report = run_analysis(conv_path)

    # Save full report
    out_path = Path(__file__).parent / "xform_gamma_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    # Print summary
    print(f"\n{'='*60}")
    print(f"X-FORM SESSION GAMMA PROBE REPORT")
    print(f"{'='*60}")
    print(f"Total sessions:       {report['total_sessions']}")
    print(f"Productive:           {report['productive_sessions']}")
    print(f"Non-productive:       {report['nonproductive_sessions']}")
    print(f"Models used:          {', '.join(report['models_used'])}")
    print()

    for label, key in [("ALL", "gamma_all"), ("PRODUCTIVE", "gamma_productive"), ("NON-PRODUCTIVE", "gamma_nonproductive")]:
        g = report[key]
        gamma = g.get("gamma", "N/A")
        r2 = g.get("r2", "N/A")
        ci = f"[{g.get('ci_low', '?')}, {g.get('ci_high', '?')}]"
        verdict = g.get("verdict", "?")
        n = g.get("n_valid", 0)
        print(f"{label:20s}  gamma={gamma}  R2={r2}  CI={ci}  n={n}  {verdict}")

    print()
    dg = report.get("delta_gamma", "N/A")
    closer = report.get("productive_closer_to_unity")
    print(f"Delta(gamma):         {dg}")
    print(f"Productive closer to 1.0: {closer}")

    print(f"\nTop 10 productive sessions:")
    for i, s in enumerate(report.get("top10_productive", []), 1):
        print(f"  {i:2d}. [{s['model']:12s}] {s['turns']:3d} turns  C={s['complexity']:6.1f}  K={s['cost']:6.1f}  code={s['has_code']}  {s['title'][:50]}")

    print(f"\nFull report saved to: {out_path}")


if __name__ == "__main__":
    main()
