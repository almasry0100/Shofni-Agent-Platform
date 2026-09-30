from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Self


ALPHA_CONTENT = "alpha fixture input\n"
BETA_CONTENT = '{"count":2,"label":"beta"}\n'


class WorkspaceError(ValueError):
    pass


class DisposableWorkspace:
    """A programmatically created workspace that owns only its temporary root."""

    def __init__(self, seed: str = "workspace-fixture-v1") -> None:
        self.seed = seed
        self.workspace_id = "workspace_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
        self._temporary_directory: tempfile.TemporaryDirectory[str] | None = None
        self._root: Path | None = None

    @property
    def root(self) -> Path:
        if self._root is None:
            raise RuntimeError("workspace has not been entered")
        return self._root

    def __enter__(self) -> Self:
        if self._temporary_directory is not None:
            raise RuntimeError("workspace is already active")
        self._temporary_directory = tempfile.TemporaryDirectory(prefix="shofni-poc-workspace-")
        self._root = Path(self._temporary_directory.name).resolve()
        (self._root / "input").mkdir()
        (self._root / "output").mkdir()
        (self._root / "state").mkdir()
        (self._root / "input" / "alpha.txt").write_text(ALPHA_CONTENT, encoding="utf-8")
        (self._root / "input" / "beta.json").write_text(BETA_CONTENT, encoding="utf-8")
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
        self._temporary_directory = None
        self._root = None

    def resolve_path(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path or "\x00" in relative_path:
            raise WorkspaceError("workspace path must be a non-empty relative string")
        normalized = relative_path.replace("\\", "/")
        posix_path = PurePosixPath(normalized)
        windows_path = PureWindowsPath(relative_path)
        parts = normalized.split("/")
        if (
            posix_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or any(part in {"", ".", ".."} or ":" in part for part in parts)
        ):
            raise WorkspaceError("workspace path must stay relative to the fixture root")
        if parts[0] not in {"input", "output", "state"}:
            raise WorkspaceError("workspace path must use input, output, or state")

        root = self.root.resolve()
        target = root.joinpath(*parts).resolve(strict=False)
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise WorkspaceError("workspace path escapes the fixture root") from exc
        return target

    def read_text(self, relative_path: str) -> str:
        path = self.resolve_path(relative_path)
        if not path.is_file():
            raise WorkspaceError("workspace file does not exist")
        return path.read_text(encoding="utf-8")

    def write_text(self, relative_path: str, content: str) -> None:
        parts = relative_path.replace("\\", "/").split("/")
        if not parts or parts[0] not in {"output", "state"}:
            raise WorkspaceError("fixture writes are limited to output and state")
        path = self.resolve_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def read_json(self, relative_path: str) -> object:
        return json.loads(self.read_text(relative_path))
