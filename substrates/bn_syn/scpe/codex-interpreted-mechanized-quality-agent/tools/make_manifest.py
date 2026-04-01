#!/usr/bin/env python3
import argparse
import hashlib
import json
import pathlib
import re
import time

def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def collect_artifacts(root: pathlib.Path):
    artifacts = []
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        artifacts.append({"path": str(p.relative_to(root)), "sha256": sha256_file(p)})
    return artifacts

def upsert_self_hash(artifacts, rel_out: str, out_sha256: str):
    for item in artifacts:
        if item["path"] == rel_out:
            item["sha256"] = out_sha256
            return artifacts
    artifacts.append({"path": rel_out, "sha256": out_sha256})
    artifacts.sort(key=lambda x: x["path"])
    return artifacts

def parse_command_metrics(metrics_path: pathlib.Path):
    items = []
    if not metrics_path.exists():
        return items
    rx = re.compile(r"__CMD_EXIT_CODE__=(\d+)\s+__DURATION_MS__=(\d+)\s+__CMD__=(.*)$")
    for line in metrics_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = rx.match(line.strip())
        if not m:
            continue
        items.append({"cmd": m.group(3), "exit_code": int(m.group(1)), "duration_ms": int(m.group(2))})
    return items

ap = argparse.ArgumentParser()
ap.add_argument("--evidence-root", required=True)
ap.add_argument("--git-sha-before", required=True)
ap.add_argument("--git-sha-after", required=True)
ap.add_argument("--out", required=True)
args = ap.parse_args()

root = pathlib.Path(args.evidence_root).resolve()
outp = pathlib.Path(args.out).resolve()
rel_out = str(outp.relative_to(root))

manifest = {
  "work_id": root.name,
  "utc_started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "utc_finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "git_sha_before": args.git_sha_before,
  "git_sha_after": args.git_sha_after,
  "commands": parse_command_metrics(root / "AFTER" / "command-metrics.log"),
  "artifacts": collect_artifacts(root)
}
outp.parent.mkdir(parents=True, exist_ok=True)

# Two-pass write so MANIFEST.json is included in artifacts with its final sha256.
outp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
manifest["artifacts"] = upsert_self_hash(manifest["artifacts"], rel_out, sha256_file(outp))
outp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("ok")
