from __future__ import annotations
import sys
from pathlib import Path
FORBIDDEN={0x202A,0x202B,0x202D,0x202E,0x202C,0x2066,0x2067,0x2068,0x2069,0x200B,0x200C,0x200D,0xFEFF}
ALLOW_SUFFIX={'.png','.jpg','.jpeg','.gif','.pdf','.lock'}

def main()->int:
    bad=[]
    for p in Path('.').rglob('*'):
        if not p.is_file() or '.git/' in str(p):
            continue
        if p.suffix.lower() in ALLOW_SUFFIX:
            continue
        try:text=p.read_text(encoding='utf-8')
        except Exception:continue
        for i,ch in enumerate(text):
            if ord(ch) in FORBIDDEN:
                bad.append((str(p),i,ord(ch)));break
    if bad:
        for f,i,c in bad: print(f'FORBIDDEN_UNICODE {f}:{i} U+{c:04X}')
        return 1
    print('unicode-scan: OK');return 0

if __name__=='__main__': raise SystemExit(main())
