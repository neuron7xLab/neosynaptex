# Unicode Security Policy

We block Trojan Source and hidden control characters that can disguise malicious changes.

**Blocked codepoints**
- Bidirectional controls: U+061C, U+200E, U+200F, U+202A–U+202E, U+2066–U+2069
- Zero-width/invisible: U+200B, U+200C, U+200D, U+2060, U+FEFF
- Any other Unicode **Cf** characters (no allowlist)

**How to run locally**
```bash
python scripts/unicode_scan.py
```

The scanner reports `file:line:col U+XXXX NAME snippet` for every violation and fails CI on findings.
