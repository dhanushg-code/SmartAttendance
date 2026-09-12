"""Supabase client factory and a demo-mode in-memory backend.

Demo mode lets the whole app run with no scanner and no Supabase credentials.
The public API (one `Database` object exposing `table(name)`) is identical for
both backends, so swapping backends never touches business logic.
"""
from __future__ import annotations

import threading
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from config import settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return date.today().isoformat()


class _Query:
    """Chained query builder over a list of dict rows (demo backend)."""

    def __init__(self, table: "_MemTable") -> None:
        self._table = table
        self._eq: dict[str, Any] = {}
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None
        self._single = False
        self._pending: tuple[str, Any] | None = None  # deferred mutation

    # --- filters ------------------------------------------------------------
    def select(self, *_columns: str) -> "_Query":
        return self

    def eq(self, column: str, value: Any) -> "_Query":
        self._eq[column] = value
        return self

    def gte(self, column: str, value: Any) -> "_Query":
        self._eq.setdefault("__gte__", {})[column] = value
        return self

    def lte(self, column: str, value: Any) -> "_Query":
        self._eq.setdefault("__lte__", {}).setdefault(column, value)
        return self

    def order(self, column: str, desc: bool = False) -> "_Query":
        self._order = (column, desc)
        return self

    def limit(self, n: int) -> "_Query":
        self._limit = n
        return self

    def single(self) -> "_Query":
        self._single = True
        return self

    # --- execution ------------------------------------------------------------
    def _match(self, row: dict[str, Any]) -> bool:
        for col, val in self._eq.items():
            if row.get(col) != val:
                return False
        for col, val in self._eq.get("__gte__", {}).items():
            if row.get(col) is None or row[col] < val:
                return False
        for col, val in self._eq.get("__lte__", {}).items():
            if row.get(col) is None or row[col] > val:
                return False
        return True

    def _filtered(self) -> list[dict[str, Any]]:
        rows = [dict(r) for r in self._table.rows if self._match(r)]
        if self._order:
            col, desc = self._order
            rows.sort(key=lambda r: r.get(col) or "", reverse=desc)
        if self._limit is not None:
            rows = rows[: self._limit]
        return rows

    def execute(self) -> "_Result":
        if self._pending is not None:
            kind, payload = self._pending
            if kind == "insert":
                return self._do_insert(payload)
            if kind == "update":
                return self._do_update(payload)
            return self._do_delete()
        rows = self._filtered()
        if self._single:
            if not rows:
                raise IndexError("No rows found for single() query")
            return _Result(rows[0])
        return _Result(rows)

    # --- mutations (deferred until .execute(), like supabase-py) ----------------
    def insert(self, payload: dict[str, Any] | list[dict[str, Any]]) -> "_Query":
        self._pending = ("insert", payload)
        return self

    def update(self, payload: dict[str, Any]) -> "_Query":
        self._pending = ("update", payload)
        return self

    def delete(self) -> "_Query":
        self._pending = ("delete", None)
        return self

    def _do_insert(self, payload: dict[str, Any] | list[dict[str, Any]]) -> "_Result":
        items = payload if isinstance(payload, list) else [payload]
        created: list[dict[str, Any]] = []
        for item in items:
            row = dict(item)
            row.setdefault("id", str(uuid.uuid4()))
            row.setdefault("created_at", _now_iso())
            self._table.rows.append(row)
            created.append(dict(row))
        return _Result(created)

    def _do_update(self, payload: dict[str, Any]) -> "_Result":
        updated: list[dict[str, Any]] = []
        for row in self._table.rows:
            if self._match(row):
                row.update(payload)
                updated.append(dict(row))
        return _Result(updated)

    def _do_delete(self) -> "_Result":
        keep = [r for r in self._table.rows if not self._match(r)]
        removed = len(self._table.rows) - len(keep)
        self._table.rows[:] = keep
        return _Result([{"deleted": removed}])

    # conveniences ------------------------------------------------------------
    def upsert(self, payload: dict[str, Any], on_conflict: str = "id") -> "_Result":
        key_cols = [c.strip() for c in on_conflict.split(",")]
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            q = _Query(self._table)
            for c in key_cols:
                q.eq(c, item[c])
            existing = q.execute().data
            if existing:
                q.update(item).execute()
            else:
                self.insert(item).execute()
        return _Result([])


class _Result:
    def __init__(self, data: Any) -> None:
        self.data = data


class _MemTable:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def __call__(self) -> _Query:
        return _Query(self)


class _AdminsTable(_MemTable):
    """In-memory admin store; checks the plain default password in demo mode."""

    def __call__(self) -> "_AdminsQuery":
        return _AdminsQuery(self)


class _AdminsQuery(_Query):
    def verify(self, username: str, password: str) -> _Result:
        ok = username == "admin" and password == "admin123"
        if ok:
            return _Result({"id": "demo-admin", "username": username})
        raise IndexError("Invalid credentials")


class _MemoryClient:
    """Thread-safe in-memory Supabase stand-in."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tables: dict[str, Any] = {}

    def table(self, name: str) -> Any:
        with self._lock:
            if name not in self._tables:
                self._tables[name] = _AdminsTable() if name == "admins" else _MemTable()
            return self._tables[name]()


class _SupabaseClient:
    """Thin wrapper over the real supabase-py client (live mode)."""

    def __init__(self) -> None:
        from supabase import create_client  # imported lazily

        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL / SUPABASE_KEY missing. Set them in .env or set DEMO_MODE=true."
            )
        self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    def table(self, name: str) -> Any:
        return self._client.table(name)


class Database:
    """Single entry point used by the whole app."""

    def __init__(self) -> None:
        self.demo = settings.DEMO_MODE
        self._client: Any
        if self.demo:
            self._client = _MemoryClient()
        else:
            self._client = _SupabaseClient()

    def table(self, name: str) -> Any:
        return self._client.table(name)


# Shared instance ---------------------------------------------------------------
db = Database()
