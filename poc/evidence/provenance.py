from __future__ import annotations

import hashlib
import os
import unicodedata
from pathlib import Path


EXCLUDED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".turbo",
        "dist",
        "build",
        "coverage",
        ".next",
        ".cache",
        ".pnpm-store",
    }
)


def _entries(root: Path, relative: str = "") -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    children = sorted(
        os.scandir(root),
        key=lambda item: unicodedata.normalize("NFC", item.name),
    )
    for item in children:
        child_relative = f"{relative}/{item.name}" if relative else item.name
        if item.is_symlink():
            digest = hashlib.sha256(b"SYMLINK\0" + os.readlink(item.path).encode("utf-8")).hexdigest()
            entries.append((unicodedata.normalize("NFC", child_relative).replace("\\", "/"), digest))
        elif item.is_dir(follow_symlinks=False):
            if item.name not in EXCLUDED_DIRECTORY_NAMES:
                entries.extend(_entries(Path(item.path), child_relative))
        elif item.is_file(follow_symlinks=False):
            digest = hashlib.sha256()
            with open(item.path, "rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            entries.append((unicodedata.normalize("NFC", child_relative).replace("\\", "/"), digest.hexdigest()))
    return entries


def candidate_tree_identity(root: Path) -> tuple[str, int]:
    """Return the locked tree digest and included entry count."""

    entries = sorted(_entries(root), key=lambda item: item[0])
    digest = hashlib.sha256()
    for relative, entry_hash in entries:
        digest.update(f"{relative}\0{entry_hash.lower()}\n".encode("utf-8"))
    return "sha256:" + digest.hexdigest(), len(entries)
