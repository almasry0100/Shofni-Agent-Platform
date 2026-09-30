from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from poc.evidence.redactor import REDACTED_PATH, redact_string


PRIVATE_PATH = re.compile(r"(?i)(?:[A-Z]:[\\/]Users[\\/]|/Users/|/home/|/root/)")
TARGETS = (
    "tests/poc/evidence/phase-4/phase4-remediation-20260930T190000Z/provenance.json",
    "tests/poc/evidence/phase-4/phase4-remediation-20260930T190500Z/provenance.json",
    "tests/poc/evidence/phase-4/phase4-remediation-20260930T191000Z/provenance.json",
    "tests/poc/evidence/phase-4/phase4-remediation-20260930T191500Z/provenance.json",
    "tests/poc/evidence/phase-4/phase4-remediation-20260930T192000Z/provenance.json",
)


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _semantic_view(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _semantic_view(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_semantic_view(item) for item in value]
    if isinstance(value, str) and (PRIVATE_PATH.search(value) or value == REDACTED_PATH):
        return "<PRIVATE_PATH>"
    return value


def _path_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        values: list[str] = []
        for item in value.values():
            values.extend(_path_values(item))
        return values
    if isinstance(value, list):
        values = []
        for item in value:
            values.extend(_path_values(item))
        return values
    if isinstance(value, str) and PRIVATE_PATH.search(value):
        return [value]
    return []


def sanitize(root: Path) -> dict[str, Any]:
    root = root.resolve()
    raw_root = (root / "poc/.runtime/raw-evidence/historical-sanitization").resolve()
    runtime_root = (root / "poc/.runtime").resolve()
    if runtime_root not in raw_root.parents:
        raise ValueError("raw staging path escaped poc/.runtime")
    raw_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    files: list[dict[str, Any]] = []
    try:
        for relative in TARGETS:
            source = root / relative
            if not source.is_file():
                raise FileNotFoundError(relative)
            original_bytes = source.read_bytes()
            original_text = original_bytes.decode("utf-8")
            original_value = json.loads(original_text)
            raw_copy = raw_root / f"{source.parent.name}-provenance.json"
            shutil.copy2(source, raw_copy)
            raw_hash = _sha256(raw_copy.read_bytes())
            path_values = sorted(set(_path_values(original_value)))
            sanitized_text = original_text
            replacement_count = 0
            for path_value in path_values:
                # Use the redactor's stable placeholder while replacing the exact JSON value.
                _ = redact_string(path_value)
                literal = json.dumps(path_value, ensure_ascii=True)
                replacement = json.dumps(REDACTED_PATH, ensure_ascii=True)
                occurrences = sanitized_text.count(literal)
                sanitized_text = sanitized_text.replace(literal, replacement)
                replacement_count += occurrences
            sanitized_value = json.loads(sanitized_text)
            if _semantic_view(original_value) != _semantic_view(sanitized_value):
                raise ValueError(f"semantic content changed: {relative}")
            if PRIVATE_PATH.search(sanitized_text):
                raise ValueError(f"private path remains: {relative}")
            source.write_text(sanitized_text, encoding="utf-8", newline="\n")
            sanitized_hash = _sha256(source.read_bytes())
            files.append(
                {
                    "path": relative,
                    "raw_temp_path": raw_copy.relative_to(root).as_posix(),
                    "original_sha256": raw_hash,
                    "sanitized_sha256": sanitized_hash,
                    "private_path_replacements": replacement_count,
                    "semantic_fields_unchanged": True,
                }
            )
        shutil.rmtree(raw_root)
        raw_deleted = not raw_root.exists()
    except Exception:
        raise
    lineage = {
        "schema_version": "1.0",
        "sanitization_run": "historical-liteLLM-private-paths-" + timestamp.replace("-", "").replace(":", "").replace(".", ""),
        "sanitized_at_utc": timestamp,
        "redactor_placeholder": REDACTED_PATH,
        "raw_staging_root": "poc/.runtime/raw-evidence/historical-sanitization/",
        "raw_deleted": raw_deleted,
        "raw_files_persisted": False,
        "files": files,
    }
    destination = root / "tests/poc/evidence/phase-4/historical-sanitization-lineage.json"
    destination.write_text(json.dumps(lineage, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return lineage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    result = sanitize(args.root)
    print(json.dumps({"files": len(result["files"]), "raw_deleted": result["raw_deleted"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
