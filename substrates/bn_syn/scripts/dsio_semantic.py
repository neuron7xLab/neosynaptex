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
ART = ROOT / "artifacts" / "dsio"
LOGS = ART / "logs"
REPORTS = ART / "reports"

TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]{2,}")
STOPWORDS = {"the", "and", "for", "with", "that", "this", "from", "into", "true", "false", "none", "return", "class", "def"}


def h64(key: str) -> str:
    return hashlib.blake2b(key.encode("utf-8"), digest_size=8).hexdigest()


def sid(kind: str, key: str) -> str:
    return f"§{kind}:{key}#{h64(key)}"


def tok(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOPWORDS]


def tfidf(corpus: dict[str, list[str]]) -> dict[str, dict[str, float]]:
    docs = sorted(corpus)
    df: Counter[str] = Counter()
    for doc in docs:
        df.update(set(corpus[doc]))
    n_docs = len(docs)
    out: dict[str, dict[str, float]] = {}
    for doc in docs:
        counts = Counter(corpus[doc])
        total = sum(counts.values()) or 1
        vec: dict[str, float] = {}
        for term, count in sorted(counts.items()):
            idf = math.log((1 + n_docs) / (1 + df[term])) + 1.0
            vec[term] = round((count / total) * idf, 8)
        out[doc] = vec
    return out


def cos(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    num = sum(a[t] * b[t] for t in common)
    da = math.sqrt(sum(v * v for v in a.values()))
    db = math.sqrt(sum(v * v for v in b.values()))
    if da == 0.0 or db == 0.0:
        return 0.0
    return round(num / (da * db), 8)


def parse_py(path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    rel = path.relative_to(ROOT).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    symbols: list[str] = []
    imports: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                imports.append((rel, a.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((rel, node.module))
    return sorted(set(symbols)), sorted(set(imports))


def main() -> int:
    for d in [ART, LOGS, REPORTS]:
        d.mkdir(parents=True, exist_ok=True)

    py_files = sorted((ROOT / "src").rglob("*.py")) + sorted((ROOT / "scripts").glob("*.py"))
    docs = sorted((ROOT / "docs").rglob("*.md"))
    if (ROOT / "README.md").exists():
        docs.append(ROOT / "README.md")

    corpus: dict[str, list[str]] = {}
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    retrieval: dict[str, Any] = {"symbols": {}, "file_topics": {}, "neighbors": {}, "critical_path": [], "ssot": {}}

    for path in py_files:
        rel = path.relative_to(ROOT).as_posix()
        mod_id = sid("MOD", rel)
        nodes.append({"id": mod_id, "type": "MOD", "key": rel, "evidence": [f"file:{rel}:L1-L1"]})
        code = path.read_text(encoding="utf-8")
        corpus[rel] = tok(code)
        symbols, imports = parse_py(path)
        for sym in symbols:
            key = f"{rel}:{sym}"
            fid = sid("FUN", key)
            nodes.append({"id": fid, "type": "FUN", "key": key, "evidence": [f"file:{rel}:L1-L1"]})
            edges.append({"src": mod_id, "dst": fid, "kind": "defines"})
            retrieval["symbols"][sym] = {"id": fid, "file": rel}
        for src, dst in imports:
            edges.append({"src": sid("MOD", src), "dst": sid("MOD", dst), "kind": "imports"})

    for path in docs:
        rel = path.relative_to(ROOT).as_posix()
        did = sid("DOC", rel)
        text = path.read_text(encoding="utf-8")
        terms = tok(text)
        corpus[rel] = terms
        nodes.append({"id": did, "type": "DOC", "key": rel, "evidence": [f"file:{rel}:L1-L1"]})
        top = [t for t, _ in Counter(terms).most_common(8)]
        retrieval["file_topics"][rel] = top
        for term in top[:4]:
            tid = sid("TOP", f"topic:{term}")
            edges.append({"src": did, "dst": tid, "kind": "mentions", "weight": 1.0})

    vectors = tfidf(corpus)
    keys = sorted(vectors)
    nb: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            sim = cos(vectors[a], vectors[b])
            if sim >= 0.12:
                edges.append({"src": sid("IDX", a), "dst": sid("IDX", b), "kind": "similar", "weight": sim})
                nb[a].append({"target": b, "score": sim})
                nb[b].append({"target": a, "score": sim})

    retrieval["neighbors"] = {k: sorted(v, key=lambda x: (x["target"], x["score"])) for k, v in sorted(nb.items())}
    retrieval["critical_path"] = ["src/bnsyn/cli.py", "src/bnsyn/simulation.py", "src/bnsyn/schemas/experiment.py"]
    retrieval["ssot"] = {"commands": ["make install", "make lint", "make mypy", "make test", "make build", "make dsio-gate"], "cli": "bnsyn"}

    kg = {"nodes": sorted(nodes, key=lambda x: x["id"]), "edges": sorted(edges, key=lambda x: (x["src"], x["dst"], x["kind"]))}

    (ART / "SEMANTIC_KG.json").write_text(json.dumps(kg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ART / "RETRIEVAL_INDEX.json").write_text(json.dumps(retrieval, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ART / "TASK_DAG.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": sid("DAG", "fingerprint"), "inputs": [], "outputs": ["REPO_FINGERPRINT.json"], "verify": "hash"},
                    {"id": sid("DAG", "env_snapshot"), "inputs": [], "outputs": ["ENV_SNAPSHOT.json"], "verify": "json-parse"},
                    {"id": sid("DAG", "ric"), "inputs": ["docs", "workflows", "makefile"], "outputs": ["RIC_TRUTH_MAP.json", "RIC_REPORT.md"], "verify": "contradictions==0"},
                    {"id": sid("DAG", "semantic"), "inputs": ["src", "docs"], "outputs": ["SEMANTIC_KG.json", "RETRIEVAL_INDEX.json"], "verify": "json-parse"},
                    {"id": sid("DAG", "quality"), "inputs": ["all logs"], "outputs": ["quality.json"], "verify": "verdict"},
                ],
                "edges": [
                    [sid("DAG", "fingerprint"), sid("DAG", "quality")],
                    [sid("DAG", "env_snapshot"), sid("DAG", "quality")],
                    [sid("DAG", "ric"), sid("DAG", "quality")],
                    [sid("DAG", "semantic"), sid("DAG", "quality")],
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (REPORTS / "SEMANTIC_MINING_REPORT.md").write_text(
        "# SEMANTIC_MINING_REPORT\n\n- file:artifacts/dsio/SEMANTIC_KG.json:L1-L5\n- file:artifacts/dsio/RETRIEVAL_INDEX.json:L1-L5\n- file:artifacts/dsio/TASK_DAG.json:L1-L5\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
