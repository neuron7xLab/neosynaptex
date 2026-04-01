#!/usr/bin/env python3
"""
Production-grade offline bibliography validator for MLSDM repository.

Validates:
- CITATION.cff exists and has required fields
- docs/bibliography/REFERENCES.bib parses successfully
- BibTeX keys are unique
- Each entry has title + year + author + at least one of (doi, url, eprint, isbn)
- Year is 4 digits within range [1850..2026]
- DOI format is valid (basic regex)
- URLs use HTTPS protocol
- No forbidden content (TODO, example.com, placeholder text)
- BibTeX and APA files have 1:1 key mapping
- identifiers.json covers all keys with canonical identifiers
- VERIFICATION.md aligns with identifiers.json
- Frozen metadata (title/year/first author/venue) matches identifiers.json

No network requests are made.
Exit code 0 on success, non-zero on failure.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# Forbidden patterns (applied to CITATION.cff and REFERENCES.bib only, not APA)
FORBIDDEN_PATTERNS_STRICT = [
    r"\bTODO\b",
    r"\bTBD\b",
    r"\bFIXME\b",
    r"example\.com",
    r"\bplaceholder\b",
]

# Patterns that apply to CITATION.cff only (not bibliography files)
FORBIDDEN_PATTERNS_CFF = FORBIDDEN_PATTERNS_STRICT + [
    r"\.\.\.",  # Ellipsis placeholders (but allowed in APA author lists)
]

# DOI format regex (basic validation - must have prefix and suffix)
DOI_PATTERN = re.compile(r"^10\.\d{4,}/.+")

# Year range for validation
MIN_YEAR = 1850
MAX_YEAR = 2026  # current_year + 1

# Year regex (4 digits)
YEAR_PATTERN = re.compile(r"^\d{4}$")

ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_CANONICAL_ID_TYPES = {"doi", "arxiv", "isbn", "url"}
META_KEY_PREFIX = "_"
REQUIRED_IDENTIFIER_FIELDS = ("doi", "url", "eprint", "isbn")
PLACEHOLDER_DOMAINS = {"example.com", "example.org"}


def is_placeholder_domain(host: str) -> bool:
    """Return True if host matches placeholder domains or their subdomains."""
    return host in PLACEHOLDER_DOMAINS or any(
        host.endswith(f".{domain}") for domain in PLACEHOLDER_DOMAINS
    )


def is_meta_key(key: str) -> bool:
    """Return True if the identifiers.json key is reserved for metadata."""
    return key.startswith(META_KEY_PREFIX)


def normalize_string(value: str) -> str:
    """Lowercase and strip non-alphanumeric characters for robust comparisons."""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def normalize_title(value: str) -> str:
    """Remove braces and normalize title for duplicate detection."""
    return normalize_string(value.replace("{", "").replace("}", ""))


def extract_first_author(author_field: str) -> str:
    """Extract and normalize the first author from a BibTeX author field."""
    cleaned = author_field.replace("{", "").replace("}", "")
    first = re.split(r"\s+and\s+", cleaned, flags=re.IGNORECASE)[0].strip()
    return normalize_string(first)


def extract_first_author_family(author_field: str) -> str:
    """
    Extract first author family name without normalization for frozen metadata.

    Supports both "Last, First" and "First Last" formats; when no comma is present,
    the last token is treated as the family name.
    """
    cleaned = author_field.replace("{", "").replace("}", "").strip()
    if not cleaned:
        return ""
    first = re.split(r"\s+and\s+", cleaned, flags=re.IGNORECASE)[0].strip()
    if "," in first:
        return first.split(",", 1)[0].strip()
    parts = first.split()
    return parts[-1] if parts else ""


def extract_venue_field(fields: dict[str, str]) -> str:
    """Derive venue/publisher string from BibTeX fields."""
    for field_name in ("journal", "booktitle", "institution", "publisher"):
        if fields.get(field_name):
            return fields[field_name]
    if fields.get("eprint"):
        return "arXiv"
    author_value = fields.get("author", "")
    if author_value and " and " not in author_value.lower():
        # Standards/software entries sometimes omit journal/booktitle but list a single
        # issuing organization (or author) in the author field. When no venue fields
        # are available, treat that single issuer as the venue/publisher fallback.
        return author_value.replace("{", "").replace("}", "")
    return ""


def find_repo_root() -> Path:
    """Find repository root by looking for CITATION.cff or pyproject.toml."""
    current = Path(__file__).resolve().parent
    for _ in range(10):  # Max 10 levels up
        if (current / "pyproject.toml").exists():
            return current
        if (current / "CITATION.cff").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    # Fallback: assume script is in scripts/ directory
    return Path(__file__).resolve().parent.parent


def check_citation_cff(repo_root: Path) -> list[str]:
    """Check that CITATION.cff exists and has required fields."""
    errors: list[str] = []
    cff_path = repo_root / "CITATION.cff"

    if not cff_path.exists():
        errors.append(f"CITATION.cff not found at {cff_path}")
        return errors

    content = cff_path.read_text(encoding="utf-8")

    # Basic checks for required fields
    required_fields = ["cff-version", "title", "version", "authors", "license"]
    for field in required_fields:
        if field + ":" not in content:
            errors.append(f"CITATION.cff missing required field: {field}")

    # Check for forbidden patterns
    for pattern in FORBIDDEN_PATTERNS_CFF:
        if re.search(pattern, content, re.IGNORECASE):
            errors.append(f"CITATION.cff contains forbidden pattern: {pattern}")

    return errors


def _has_odd_trailing_backslashes(buffer: list[str]) -> bool:
    """Return True if buffer ends with an odd number of backslashes."""
    count = 0
    idx = len(buffer) - 1
    while idx >= 0 and buffer[idx] == "\\":
        count += 1
        idx -= 1
    return count % 2 == 1


def _split_fields(fields_str: str) -> list[str]:
    """Split a BibTeX fields block into individual field strings."""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    in_quotes = False

    for ch in fields_str:
        if ch == '"' and not _has_odd_trailing_backslashes(current):
            in_quotes = not in_quotes
        if ch == "{":
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
        if ch == "," and depth == 0 and not in_quotes:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(ch)

    if current and "".join(current).strip():
        parts.append("".join(current).strip())
    return parts


def parse_bibtex_entries(content: str) -> tuple[list[dict], list[str]]:
    """
    Robust, dependency-free BibTeX parser that handles:
    - nested braces (e.g., author={{OpenAI}})
    - commas inside braced values
    - last field without trailing comma
    """
    entries: list[dict] = []
    errors: list[str] = []
    idx = 0

    while True:
        at_idx = content.find("@", idx)
        if at_idx == -1:
            break

        match = re.match(r"@(\w+)\s*\{", content[at_idx:])
        if not match:
            idx = at_idx + 1
            continue

        entry_type = match.group(1).lower()
        cursor = at_idx + match.end()

        while cursor < len(content) and content[cursor].isspace():
            cursor += 1

        key_start = cursor
        while cursor < len(content) and content[cursor] not in {",", "\n", " "}:
            cursor += 1
        entry_key = content[key_start:cursor].strip()

        # Move to start of fields (after first comma)
        while cursor < len(content) and content[cursor] != ",":
            cursor += 1
        if cursor >= len(content):
            errors.append(f"Malformed BibTeX entry near index {at_idx}: missing field list")
            break
        cursor += 1  # skip comma
        body_start = cursor
        brace_depth = 1
        while cursor < len(content) and brace_depth > 0:
            ch = content[cursor]
            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
            cursor += 1

        if brace_depth != 0:
            errors.append(f"Unbalanced braces while parsing entry '{entry_key or 'unknown'}'")
            break

        fields_block = content[body_start : cursor - 1]
        fields: dict[str, str] = {}
        for field_str in _split_fields(fields_block):
            if "=" not in field_str:
                errors.append(f"Entry '{entry_key}': could not parse field '{field_str}'")
                continue
            name_raw, value_raw = field_str.split("=", 1)
            field_name = name_raw.strip().lower()
            value = value_raw.strip().rstrip(",")
            if (value.startswith("{") and value.endswith("}")) or (value.startswith('"') and value.endswith('"')):
                value = value[1:-1]
            fields[field_name] = value.strip()

        entries.append({"type": entry_type, "key": entry_key, "fields": fields})
        idx = cursor

    return entries, errors


def run_parser_self_checks() -> list[str]:
    """Internal self-checks to ensure parser robustness."""
    errors: list[str] = []
    sample = """
@misc{selfcheck_one,
  author={{OpenAI}},
  title={ISO/IEC 42001:2023 — Artificial intelligence management system},
  url={https://example.com/path?with=comma,inside}
}

@article{selfcheck_two,
  author = {Example, Author},
  title = {Nested {brace} sample},
  year = {2024},
  note = {Trailing field without comma}
}
"""
    entries, parse_errors = parse_bibtex_entries(sample)
    errors.extend(parse_errors)
    if len(entries) != 2:
        errors.append(f"Self-check expected 2 entries, found {len(entries)}")
        return errors

    first_fields = entries[0]["fields"]
    if first_fields.get("author") != "{OpenAI}":
        errors.append("Self-check failed: nested braces not preserved in author field")
    if first_fields.get("url") != "https://example.com/path?with=comma,inside":
        errors.append("Self-check failed: URL with comma not parsed correctly")

    second_fields = entries[1]["fields"]
    if second_fields.get("note") != "Trailing field without comma":
        errors.append("Self-check failed: last field without trailing comma was not captured")
    return errors


def validate_doi(doi: str) -> bool:
    """Validate DOI format (basic check)."""
    return bool(DOI_PATTERN.match(doi))


def validate_year(year: str) -> tuple[bool, str]:
    """Validate year is 4 digits in reasonable range [1850..2026].

    Returns (is_valid, error_message).
    """
    # Handle n.d. for "no date" entries
    if year.lower() == "n.d.":
        return True, ""
    if not YEAR_PATTERN.match(year):
        return False, f"year '{year}' is not a 4-digit integer"
    year_int = int(year)
    if year_int < MIN_YEAR or year_int > MAX_YEAR:
        return False, f"year {year_int} outside valid range [{MIN_YEAR}..{MAX_YEAR}]"
    return True, ""


def validate_url(url: str) -> bool:
    """Validate URL uses HTTPS and is not example.com."""
    if not url.startswith("https://"):
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    # Reject placeholder domains exactly or as subdomains (e.g., foo.example.com)
    return not is_placeholder_domain(host)


def check_forbidden_content(content: str, context: str, patterns: list[str] | None = None) -> list[str]:
    """Check for forbidden patterns in content."""
    if patterns is None:
        patterns = FORBIDDEN_PATTERNS_STRICT
    errors = []
    for pattern in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            errors.append(f"{context} contains forbidden pattern: {pattern}")
    return errors


def check_bibtex(repo_root: Path) -> tuple[list[str], set[str], list[dict]]:
    """Check that REFERENCES.bib is valid and entries meet requirements.

    Returns (errors, bib_keys, entries) where bib_keys is the set of all BibTeX keys.
    """
    errors: list[str] = []
    bib_keys: set[str] = set()
    entries: list[dict] = []
    bib_path = repo_root / "docs" / "bibliography" / "REFERENCES.bib"

    if not bib_path.exists():
        errors.append(f"REFERENCES.bib not found at {bib_path}")
        return errors, bib_keys, entries

    content = bib_path.read_text(encoding="utf-8")

    # Check for forbidden patterns
    errors.extend(check_forbidden_content(content, "REFERENCES.bib"))

    parsed_entries, parse_errors = parse_bibtex_entries(content)
    entries.extend(parsed_entries)
    errors.extend(parse_errors)

    if not entries:
        errors.append("No BibTeX entries found in REFERENCES.bib")
        return errors, bib_keys, entries

    # Check for unique keys
    seen_keys: set[str] = set()
    doi_to_key: dict[str, str] = {}
    normalized_work_to_key: dict[tuple[str, str, str], str] = {}
    for entry in entries:
        key = entry["key"]
        if key in seen_keys:
            errors.append(f"Duplicate BibTeX key: {key}")
        seen_keys.add(key)
    bib_keys = seen_keys.copy()

    # Check each entry has required fields
    for entry in entries:
        key = entry["key"]
        fields = entry["fields"]

        # Must have title
        if "title" not in fields or not fields["title"]:
            errors.append(f"Entry '{key}' missing required field: title")

        # Must have author
        if "author" not in fields or not fields["author"]:
            errors.append(f"Entry '{key}' missing required field: author")

        # Must have year
        year = fields.get("year", "")
        if not year:
            errors.append(f"Entry '{key}' missing required field: year")
        else:
            year_valid, year_error = validate_year(year)
            if not year_valid:
                errors.append(f"Entry '{key}' has invalid year: {year_error}")

        # Must have at least one of: doi, url, eprint, isbn
        has_identifier = any(fields.get(f) for f in REQUIRED_IDENTIFIER_FIELDS)
        if not has_identifier:
            required_list = ", ".join(REQUIRED_IDENTIFIER_FIELDS)
            errors.append(f"Entry '{key}' must have at least one of: {required_list}")

        # Validate DOI format if present and enforce uniqueness
        doi = fields.get("doi", "").strip()
        if doi:
            if not validate_doi(doi):
                errors.append(f"Entry '{key}' has invalid DOI format: {doi}")
            doi_key = doi.lower()
            if doi_key in doi_to_key and doi_to_key[doi_key] != key:
                errors.append(
                    f"Duplicate DOI across entries: {doi} used by '{doi_to_key[doi_key]}' and '{key}'"
                )
            doi_to_key[doi_key] = key

        # Validate URL if present
        url = fields.get("url", "")
        if url and not validate_url(url):
            errors.append(f"Entry '{key}' has invalid URL (must be HTTPS, not example.com): {url}")

        # Deduplicate by normalized (title + year + first author)
        title = fields.get("title", "")
        author = fields.get("author", "")
        norm_tuple = (
            normalize_title(title) if title else "",
            year.strip(),
            extract_first_author(author) if author else "",
        )
        if all(norm_tuple):
            existing = normalized_work_to_key.get(norm_tuple)
            if existing and existing != key:
                errors.append(
                    "Duplicate work detected by normalized (title, year, first author): "
                    f"'{existing}' and '{key}'"
                )
            normalized_work_to_key[norm_tuple] = key

    print(f"Validated {len(entries)} BibTeX entries")
    return errors, bib_keys, entries


def extract_apa_keys(repo_root: Path) -> tuple[list[str], set[str]]:
    """Extract BibTeX key comments from APA file.

    Returns (errors, apa_keys) where apa_keys is the set of all keys found.
    """
    errors: list[str] = []
    apa_keys: set[str] = set()
    apa_path = repo_root / "docs" / "bibliography" / "REFERENCES_APA7.md"

    if not apa_path.exists():
        errors.append(f"REFERENCES_APA7.md not found at {apa_path}")
        return errors, apa_keys

    content = apa_path.read_text(encoding="utf-8")

    # Check for forbidden patterns
    errors.extend(check_forbidden_content(content, "REFERENCES_APA7.md"))

    # Extract keys from HTML comments: <!-- key: bibkey -->
    key_pattern = re.compile(r"<!--\s*key:\s*(\S+)\s*-->")
    for match in key_pattern.finditer(content):
        key = match.group(1)
        if key in apa_keys:
            errors.append(f"Duplicate APA key comment: {key}")
        apa_keys.add(key)

    # Enforce that each entry block starts with a key marker
    marker_pending = False
    in_entry = False
    has_seen_marker = False
    for idx, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            if in_entry:
                in_entry = False
            continue
        if stripped.startswith("#"):
            marker_pending = False
            in_entry = False
            continue
        if key_pattern.match(stripped):
            marker_pending = True
            in_entry = False
            has_seen_marker = True
            continue
        if stripped.startswith("<!--"):
            # Ignore other comments
            continue
        if not has_seen_marker:
            continue
        if not marker_pending and not in_entry:
            errors.append(f"Line {idx}: APA entry text not preceded by <!-- key: ... --> marker")
        in_entry = True
        marker_pending = False

    print(f"Found {len(apa_keys)} key comments in APA file")
    return errors, apa_keys


def parse_verification_table(repo_root: Path) -> tuple[list[str], list[dict]]:
    """Parse verification table rows from VERIFICATION.md."""
    errors: list[str] = []
    rows: list[dict] = []
    verification_path = repo_root / "docs" / "bibliography" / "VERIFICATION.md"

    if not verification_path.exists():
        return [f"VERIFICATION.md not found at {verification_path}"], rows

    content = verification_path.read_text(encoding="utf-8")
    table_started = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("| key"):
            table_started = True
            continue
        if not table_started:
            continue
        if stripped.startswith("|---"):
            continue
        if not stripped.startswith("|"):
            if table_started:
                break
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 6:
            continue
        row = {
            "key": cells[0],
            "canonical_id_type": cells[1],
            "canonical_id": cells[2],
            "canonical_url": cells[3],
            "verified_on": cells[4],
            "verification_method": cells[5],
        }
        rows.append(row)

    if not rows:
        errors.append("No rows parsed from VERIFICATION.md table")
    return errors, rows


def check_verification_table(
    repo_root: Path, bib_keys: set[str], identifiers: dict[str, dict] | None = None
) -> list[str]:
    """Ensure verification table covers all BibTeX keys exactly once and is well-formed."""
    errors: list[str] = []
    parse_errors, rows = parse_verification_table(repo_root)
    errors.extend(parse_errors)
    if parse_errors:
        return errors

    table_keys: set[str] = set()
    for row in rows:
        key = row["key"]
        if key in table_keys:
            errors.append(f"Duplicate key in VERIFICATION.md: {key}")
        table_keys.add(key)
        if row["canonical_id_type"] not in ALLOWED_CANONICAL_ID_TYPES:
            errors.append(
                f"Row '{key}' has invalid canonical_id_type '{row['canonical_id_type']}' "
                f"(allowed: {sorted(ALLOWED_CANONICAL_ID_TYPES)})"
            )
        if not row["canonical_id"]:
            errors.append(f"Row '{key}' missing canonical_id")
        if not row["canonical_url"].startswith("https://"):
            errors.append(f"Row '{key}' canonical_url must use https: {row['canonical_url']}")
        if not ISO_DATE_PATTERN.match(row["verified_on"]):
            errors.append(f"Row '{key}' verified_on must be ISO date (YYYY-MM-DD)")
        if identifiers and key in identifiers:
            id_entry = identifiers[key]
            for field in ("canonical_id_type", "canonical_id", "canonical_url", "verification_method"):
                if str(row[field]) != str(id_entry.get(field, "")):
                    errors.append(
                        f"Row '{key}' mismatch for {field}: table='{row[field]}' identifiers='{id_entry.get(field, '')}'"
                    )
            if row["verified_on"] != identifiers[key].get("verified_on"):
                errors.append(
                    f"Row '{key}' mismatch for verified_on: table='{row['verified_on']}' identifiers='{identifiers[key].get('verified_on', '')}'"
                )

    missing = bib_keys - table_keys
    extra = table_keys - bib_keys
    if missing:
        for key in sorted(missing):
            errors.append(f"BibTeX key '{key}' missing from VERIFICATION.md table")
    if extra:
        for key in sorted(extra):
            errors.append(f"VERIFICATION.md contains key not present in BibTeX: {key}")
    if identifiers:
        id_keys = {key for key in identifiers if not is_meta_key(key)}
        missing_from_table = id_keys - table_keys
        extra_in_table = table_keys - id_keys
        for key in sorted(missing_from_table):
            errors.append(f"VERIFICATION.md missing key from identifiers.json: {key}")
        for key in sorted(extra_in_table):
            errors.append(f"VERIFICATION.md includes key not present in identifiers.json: {key}")

    return errors


def load_identifiers_json(repo_root: Path) -> tuple[list[str], dict[str, dict]]:
    """Load identifiers.json and perform basic schema validation."""
    errors: list[str] = []
    path = repo_root / "docs" / "bibliography" / "metadata" / "identifiers.json"
    if not path.exists():
        return [f"identifiers.json not found at {path}"], {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"identifiers.json is not valid JSON: {exc}"], {}

    if not isinstance(data, dict):
        return ["identifiers.json must contain a JSON object keyed by BibTeX key"], {}

    return errors, data


def check_identifiers_against_bib(
    bib_entries: list[dict], identifiers: dict[str, dict]
) -> list[str]:
    """Ensure identifiers.json covers all BibTeX keys and has required fields."""
    errors: list[str] = []
    bib_keys = {entry["key"] for entry in bib_entries}
    seen_canonical: dict[tuple[str, str], str] = {}

    for key, payload in identifiers.items():
        if is_meta_key(key):
            continue
        if key not in bib_keys:
            errors.append(f"identifiers.json contains key not present in BibTeX: {key}")
        canonical_type = payload.get("canonical_id_type")
        canonical_id = str(payload.get("canonical_id", "")).strip()
        canonical_url = str(payload.get("canonical_url", "")).strip()
        verified_on = str(payload.get("verified_on", "")).strip()
        verification_method = str(payload.get("verification_method", "")).strip()
        frozen = payload.get("frozen_metadata") or {}

        if canonical_type not in ALLOWED_CANONICAL_ID_TYPES:
            errors.append(
                f"Key '{key}' has invalid canonical_id_type '{canonical_type}' "
                f"(allowed: {sorted(ALLOWED_CANONICAL_ID_TYPES)})"
            )
        if not canonical_id:
            errors.append(f"Key '{key}' missing canonical_id in identifiers.json")
        if not canonical_url or not canonical_url.startswith("https://"):
            errors.append(f"Key '{key}' canonical_url must use https: {canonical_url}")
        if not verification_method:
            errors.append(f"Key '{key}' missing verification_method in identifiers.json")
        if not verified_on or not ISO_DATE_PATTERN.match(verified_on):
            errors.append(f"Key '{key}' verified_on must be ISO date (YYYY-MM-DD)")

        for frozen_field in ("title", "year", "first_author_family", "venue"):
            if not str(frozen.get(frozen_field, "")).strip():
                errors.append(f"Key '{key}' missing frozen_metadata.{frozen_field}")

        canonical_key = (canonical_type or "", canonical_id.lower())
        if canonical_key[1]:
            if canonical_key in seen_canonical and seen_canonical[canonical_key] != key:
                errors.append(
                    "Duplicate canonical identifier detected: "
                    f"{canonical_key[0]} '{canonical_id}' used by '{seen_canonical[canonical_key]}' and '{key}'"
                )
            seen_canonical[canonical_key] = key

    id_keys = {key for key in identifiers if not is_meta_key(key)}
    missing = bib_keys - id_keys
    for key in sorted(missing):
        errors.append(f"BibTeX key '{key}' missing from identifiers.json")

    return errors


def check_frozen_metadata(bib_entries: list[dict], identifiers: dict[str, dict]) -> list[str]:
    """Ensure BibTeX metadata matches frozen_metadata in identifiers.json."""
    errors: list[str] = []
    bib_by_key = {entry["key"]: entry["fields"] for entry in bib_entries}

    for key, payload in identifiers.items():
        if is_meta_key(key):
            continue
        if key not in bib_by_key:
            continue
        fields = bib_by_key[key]
        frozen = payload.get("frozen_metadata") or {}
        bib_title_raw = fields.get("title", "")
        frozen_title_raw = str(frozen.get("title", ""))
        if normalize_title(bib_title_raw) != normalize_title(frozen_title_raw):
            errors.append(
                f"Title mismatch for '{key}': bib='{bib_title_raw}' vs frozen='{frozen_title_raw}'"
            )

        bib_year = str(fields.get("year", "")).strip()
        frozen_year = str(frozen.get("year", "")).strip()
        if bib_year != frozen_year:
            errors.append(f"Year mismatch for '{key}': bib='{bib_year}' vs frozen='{frozen_year}'")

        bib_first_raw = extract_first_author_family(fields.get("author", ""))
        frozen_first_raw = str(frozen.get("first_author_family", ""))
        if normalize_string(bib_first_raw) != normalize_string(frozen_first_raw):
            errors.append(
                f"First author mismatch for '{key}': bib='{bib_first_raw}' vs frozen='{frozen_first_raw}'"
            )

        bib_venue_raw = extract_venue_field(fields)
        frozen_venue_raw = str(frozen.get("venue", ""))
        if normalize_string(bib_venue_raw) != normalize_string(frozen_venue_raw):
            errors.append(
                f"Venue/publisher mismatch for '{key}': bib='{bib_venue_raw}' vs frozen='{frozen_venue_raw}'"
            )

    return errors


def check_bib_apa_consistency(bib_keys: set[str], apa_keys: set[str]) -> list[str]:
    """Check 1:1 mapping between BibTeX and APA keys."""
    errors: list[str] = []

    # Keys in BibTeX but not in APA
    missing_in_apa = bib_keys - apa_keys
    for key in sorted(missing_in_apa):
        errors.append(f"BibTeX key '{key}' has no corresponding APA entry (add <!-- key: {key} --> comment)")

    # Keys in APA but not in BibTeX
    missing_in_bib = apa_keys - bib_keys
    for key in sorted(missing_in_bib):
        errors.append(f"APA key '{key}' has no corresponding BibTeX entry")

    return errors


def check_extra_bib_files(repo_root: Path) -> list[str]:
    """Fail if unarchived .bib files exist outside docs/bibliography/."""
    errors: list[str] = []
    allowed_files = {
        repo_root / "docs" / "bibliography" / "REFERENCES.bib",
        repo_root / "CITATION.bib",
    }
    allowed_prefixes = [
        repo_root / "docs" / "bibliography",
        repo_root / "docs" / "archive",
    ]

    for path in repo_root.rglob("*.bib"):
        if path in allowed_files:
            continue
        if any(path.is_relative_to(prefix) for prefix in allowed_prefixes):
            # Archived bibliography files are allowed but ignored.
            continue
        errors.append(
            f"Unexpected BibTeX file outside canonical paths: {path.relative_to(repo_root)} "
            "(delete or move to docs/archive/)"
        )
    return errors


def main() -> int:
    """Run all validation checks."""
    repo_root = find_repo_root()
    print(f"Repository root: {repo_root}")

    all_errors: list[str] = []

    print("\n[1/8] Running parser self-checks...")
    parser_errors = run_parser_self_checks()
    all_errors.extend(parser_errors)
    if parser_errors:
        for err in parser_errors:
            print(f"  ERROR: {err}")
    else:
        print("  OK: parser self-checks passed")

    # Check CITATION.cff
    print("\n[2/8] Checking CITATION.cff...")
    cff_errors = check_citation_cff(repo_root)
    all_errors.extend(cff_errors)
    if cff_errors:
        for err in cff_errors:
            print(f"  ERROR: {err}")
    else:
        print("  OK: CITATION.cff is valid")

    # Check for stray .bib files
    print("\n[3/8] Checking for stray .bib files...")
    extra_bib_errors = check_extra_bib_files(repo_root)
    all_errors.extend(extra_bib_errors)
    if extra_bib_errors:
        for err in extra_bib_errors:
            print(f"  ERROR: {err}")
    else:
        print("  OK: no unexpected .bib files found")

    # Check REFERENCES.bib
    print("\n[4/8] Checking REFERENCES.bib...")
    bib_errors, bib_keys, bib_entries = check_bibtex(repo_root)
    all_errors.extend(bib_errors)
    if bib_errors:
        for err in bib_errors:
            print(f"  ERROR: {err}")
    else:
        print("  OK: REFERENCES.bib is valid")

    id_schema_errors: list[str] = []
    frozen_errors: list[str] = []
    # Check identifiers.json and frozen metadata
    print("\n[5/8] Checking identifiers.json...")
    id_load_errors, identifiers = load_identifiers_json(repo_root)
    all_errors.extend(id_load_errors)
    if id_load_errors:
        for err in id_load_errors:
            print(f"  ERROR: {err}")
    else:
        id_schema_errors = check_identifiers_against_bib(bib_entries, identifiers)
        frozen_errors = check_frozen_metadata(bib_entries, identifiers)
        all_errors.extend(id_schema_errors + frozen_errors)
        if id_schema_errors or frozen_errors:
            for err in id_schema_errors + frozen_errors:
                print(f"  ERROR: {err}")
        else:
            print("  OK: identifiers.json coverage and frozen metadata are valid")

    # Check REFERENCES_APA7.md
    print("\n[6/8] Checking REFERENCES_APA7.md...")
    apa_errors, apa_keys = extract_apa_keys(repo_root)
    all_errors.extend(apa_errors)
    if apa_errors:
        for err in apa_errors:
            print(f"  ERROR: {err}")
    else:
        print("  OK: REFERENCES_APA7.md is valid")

    # Check BibTeX-APA consistency
    print("\n[7/8] Checking BibTeX-APA consistency...")
    consistency_errors = check_bib_apa_consistency(bib_keys, apa_keys)
    all_errors.extend(consistency_errors)
    if consistency_errors:
        for err in consistency_errors:
            print(f"  ERROR: {err}")
    else:
        print("  OK: BibTeX and APA files are consistent")

    print("\n[8/8] Checking VERIFICATION.md coverage...")
    verification_errors = check_verification_table(repo_root, bib_keys, identifiers)
    all_errors.extend(verification_errors)
    if verification_errors:
        for err in verification_errors:
            print(f"  ERROR: {err}")
    else:
        print("  OK: VERIFICATION.md covers all BibTeX keys")

    # Summary
    print("\n" + "=" * 50)
    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s) found")
        return 1
    else:
        print("PASSED: All bibliography checks passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
