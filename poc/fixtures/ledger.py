from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from typing import Any

from .workspace import DisposableWorkspace


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class LedgerRecord:
    operation_id: str
    result: Any


@dataclass(frozen=True)
class LedgerAppendResult:
    operation_id: str
    result: Any
    inserted: bool
    duplicate_suppressed: bool
    value_conflict: bool


class LedgerFixture:
    """SQLite-backed controlled ledger; this does not claim generic exactly-once behavior."""

    def __init__(self, workspace: DisposableWorkspace) -> None:
        database_path = workspace.resolve_path("state/ledger.sqlite")
        self._connection = sqlite3.connect(
            str(database_path),
            timeout=10.0,
            check_same_thread=False,
            isolation_level=None,
        )
        self._connection.execute("PRAGMA busy_timeout = 10000")
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS ledger ("
            "operation_id TEXT PRIMARY KEY, result_json TEXT NOT NULL)"
        )
        self._lock = threading.RLock()
        self._closed = False

    def append_ledger(self, operation_id: str, value: Any) -> LedgerAppendResult:
        if not operation_id:
            raise ValueError("operation_id must be non-empty")
        proposed_json = _canonical_json(value)
        with self._lock:
            self._ensure_open()
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                cursor = self._connection.execute(
                    "INSERT INTO ledger(operation_id, result_json) VALUES (?, ?) "
                    "ON CONFLICT(operation_id) DO NOTHING",
                    (operation_id, proposed_json),
                )
                inserted = cursor.rowcount == 1
                row = self._connection.execute(
                    "SELECT result_json FROM ledger WHERE operation_id = ?",
                    (operation_id,),
                ).fetchone()
                if row is None:
                    raise RuntimeError("ledger insert did not produce a readable record")
                result_json = row[0]
                self._connection.execute("COMMIT")
            except BaseException:
                self._connection.execute("ROLLBACK")
                raise
        return LedgerAppendResult(
            operation_id=operation_id,
            result=json.loads(result_json),
            inserted=inserted,
            duplicate_suppressed=not inserted,
            value_conflict=(not inserted and result_json != proposed_json),
        )

    def lookup(self, operation_id: str) -> LedgerRecord | None:
        with self._lock:
            self._ensure_open()
            row = self._connection.execute(
                "SELECT result_json FROM ledger WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        if row is None:
            return None
        return LedgerRecord(operation_id=operation_id, result=json.loads(row[0]))

    def count(self, operation_id: str | None = None) -> int:
        with self._lock:
            self._ensure_open()
            if operation_id is None:
                row = self._connection.execute("SELECT COUNT(*) FROM ledger").fetchone()
            else:
                row = self._connection.execute(
                    "SELECT COUNT(*) FROM ledger WHERE operation_id = ?",
                    (operation_id,),
                ).fetchone()
        return int(row[0])

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._connection.close()
                self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("ledger connection is closed")

    def __enter__(self) -> LedgerFixture:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
