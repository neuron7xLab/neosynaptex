from __future__ import annotations

import ast
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts" / "smlrs"
GRAPHS = ART / "graphs"
INDEXES = ART / "indexes"
REPORTS = ART / "reports"

TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]{2,}")
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "json",
    "true",
    "false",
    "none",
    "return",
    "class",
    "def",
}


def h64(value: str) -> str:
    return hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest()


def sid(kind: str, key: str) -> str:
    return f"§{kind}:{key}#{h64(key)}"


def tokens(text: str) -> list[str]:
    values = [t.lower() for t in TOKEN_RE.findall(text)]
    return [t for t in values if t not in STOPWORDS]


def tfidf_vectors(corpus: dict[str, list[str]]) -> dict[str, dict[str, float]]:
    docs = sorted(corpus)
    df: Counter[str] = Counter()
    for name in docs:
        df.update(set(corpus[name]))
    n = len(docs)
    vectors: dict[str, dict[str, float]] = {}
    for name in docs:
        counts = Counter(corpus[name])
        total = sum(counts.values()) or 1
        vec: dict[str, float] = {}
        for term, count in sorted(counts.items()):
            idf = math.log((1 + n) / (1 + df[term])) + 1.0
            vec[term] = round((count / total) * idf, 8)
        vectors[name] = vec
    return vectors


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    num = sum(a[t] * b[t] for t in common)
    da = math.sqrt(sum(v * v for v in a.values()))
    db = math.sqrt(sum(v * v for v in b.values()))
    if da == 0 or db == 0:
        return 0.0
    return round(num / (da * db), 8)


def parse_python(path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    symbols: list[str] = []
    edges: list[tuple[str, str]] = []
    module = path.relative_to(ROOT).as_posix()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append((module, alias.name))
        if isinstance(node, ast.ImportFrom) and node.module:
            edges.append((module, node.module))
    return sorted(set(symbols)), sorted(set(edges))


def main() -> int:
    for d in (GRAPHS, INDEXES, REPORTS):
        d.mkdir(parents=True, exist_ok=True)

    py_files = sorted((ROOT / "src").rglob("*.py")) + sorted((ROOT / "scripts").glob("*.py"))
    doc_files = sorted((ROOT / "docs").rglob("*.md")) + [ROOT / "README.md"]

    nodes: list[dict[str, Any]] = []
    struct_edges: list[dict[str, str]] = []
    sem_edges: list[dict[str, Any]] = []
    index: dict[str, Any] = {
        "symbols": {},
        "file_topics": {},
        "neighbors": defaultdict(list),
        "critical_path": [],
        "ssot": {},
    }

    corpus: dict[str, list[str]] = {}
    for path in py_files:
        rel = path.relative_to(ROOT).as_posix()
        symbols, imports = parse_python(path)
        module_id = sid("MOD", rel)
        nodes.append({"id": module_id, "type": "MOD", "key": rel, "evidence": [f"file:{rel}:L1-L1"]})
        corpus[rel] = tokens(path.read_text(encoding="utf-8"))
        for sym in symbols:
            key = f"{rel}:{sym}"
            sym_id = sid("FUN", key)
            nodes.append({"id": sym_id, "type": "FUN", "key": key, "evidence": [f"file:{rel}:L1-L1"]})
            struct_edges.append({"src": module_id, "dst": sym_id, "kind": "defines"})
            index["symbols"][sym] = {"id": sym_id, "file": rel}
        for src, dst in imports:
            struct_edges.append({"src": sid("MOD", src), "dst": sid("MOD", dst), "kind": "imports"})

    for path in doc_files:
        if not path.exists():
            continue
        rel = path.relative_to(ROOT).as_posix()
        doc_id = sid("DOC", rel)
        text = path.read_text(encoding="utf-8")
        nodes.append({"id": doc_id, "type": "DOC", "key": rel, "evidence": [f"file:{rel}:L1-L1"]})
        tks = tokens(text)
        corpus[rel] = tks
        top = [k for k, _ in Counter(tks).most_common(10)]
        index["file_topics"][rel] = top
        for term in top[:5]:
            top_id = sid("TOP", f"topic:{term}")
            sem_edges.append({"src": doc_id, "dst": top_id, "kind": "mentions", "weight": 1.0})

    vectors = tfidf_vectors(corpus)
    names = sorted(vectors)
    for i, a_name in enumerate(names):
        for b_name in names[i + 1 :]:
            sim = cosine(vectors[a_name], vectors[b_name])
            if sim >= 0.12:
                sem_edges.append({"src": sid("IDX", a_name), "dst": sid("IDX", b_name), "kind": "similar", "weight": sim})
                index["neighbors"][a_name].append({"target": b_name, "score": sim})
                index["neighbors"][b_name].append({"target": a_name, "score": sim})

    index["critical_path"] = ["src/bnsyn/cli.py", "src/bnsyn/simulation.py", "src/bnsyn/schemas/experiment.py"]
    index["ssot"] = {
        "commands": ["make install", "make lint", "make mypy", "make test", "make build", "make launch-gate"],
        "schema": "src/bnsyn/schemas/experiment.py",
        "cli": "bnsyn",
    }
    index["neighbors"] = {k: sorted(v, key=lambda x: (x["target"], x["score"])) for k, v in sorted(index["neighbors"].items())}

    kg = {"nodes": sorted(nodes, key=lambda x: x["id"]), "edges": sorted(struct_edges + [{"src": e["src"], "dst": e["dst"], "kind": e["kind"]} for e in sem_edges if "src" in e and "dst" in e and "kind" in e], key=lambda x: (x["src"], x["dst"], x["kind"]))}
    struct = {"edges": sorted(struct_edges, key=lambda x: (x["src"], x["dst"], x["kind"]))}
    sem = {"edges": sorted(sem_edges, key=lambda x: (x["src"], x["dst"], x["kind"]))}

    (GRAPHS / "KG.json").write_text(json.dumps(kg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (GRAPHS / "STRUCT_GRAPH.json").write_text(json.dumps(struct, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (GRAPHS / "SEM_GRAPH.json").write_text(json.dumps(sem, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (INDEXES / "RETRIEVAL_INDEX.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report_lines = [
        "# SEMANTIC_MINING_REPORT",
        "",
        f"nodes={len(kg['nodes'])}",
        f"struct_edges={len(struct['edges'])}",
        f"sem_edges={len(sem['edges'])}",
        "",
        "- file:artifacts/smlrs/graphs/KG.json:L1-L5",
        "- file:artifacts/smlrs/graphs/STRUCT_GRAPH.json:L1-L5",
        "- file:artifacts/smlrs/graphs/SEM_GRAPH.json:L1-L5",
        "- file:artifacts/smlrs/indexes/RETRIEVAL_INDEX.json:L1-L5",
    ]
    (REPORTS / "SEMANTIC_MINING_REPORT.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
