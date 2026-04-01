import hashlib, json, pathlib, subprocess, sys

ROOT = pathlib.Path(".")

def run(*cmd):
    r = subprocess.run(cmd)
    if r.returncode:
        sys.exit(r.returncode)

run(sys.executable, "benchmark/benchmark_runner.py")
run(sys.executable, "tools/render_governance_checklist.py")

manifest = {}
for p in sorted(ROOT.rglob("*")):
    if not p.is_file():
        continue
    if ".git" in p.parts or ".ci-artifacts" in p.parts:
        continue
    manifest[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()

(ROOT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print("CI PREP OK")
