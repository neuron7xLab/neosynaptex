from __future__ import annotations
import json
from pathlib import Path
root=Path('evidence'); out=Path('artifacts/package/evidence_manifest.json'); out.parent.mkdir(parents=True,exist_ok=True)
files=[]
if root.exists():
    for p in root.rglob('*'):
        if p.is_file(): files.append({'path':str(p),'size':p.stat().st_size})
out.write_text(json.dumps({'count':len(files),'files':files},indent=2),encoding='utf-8')
print(f'manifest: {len(files)} files')
