"""Storage layer for the knowledge base.

SQLite for development and tests, PostgreSQL for production — the DDL in
schema.sql is written to run on both. Set DATABASE_URL to a postgres:// URL to
use PostgreSQL; otherwise a local SQLite file is used.

Only the connection and parameter style differ; every query in this package is
written in portable SQL with ``?`` placeholders, translated for Postgres here.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "schema.sql"
DEFAULT_SQLITE = ROOT / "data" / "knowledge.db"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    """Thin portable wrapper. Not an ORM — the queries are the interface."""

    def __init__(self, url: Optional[str] = None):
        self.url = url or os.environ.get("DATABASE_URL") or ""
        self.is_postgres = self.url.startswith(("postgres://", "postgresql://"))
        if self.is_postgres:
            import psycopg  # imported lazily so SQLite dev needs no driver
            self.conn = psycopg.connect(self.url)
        else:
            path = Path(self.url or DEFAULT_SQLITE)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(path))
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")

    # ------------------------------------------------------------- helpers
    def _sql(self, sql: str) -> str:
        return re.sub(r"\?", "%s", sql) if self.is_postgres else sql

    def execute(self, sql: str, params: Iterable[Any] = ()) -> Any:
        cur = self.conn.cursor()
        cur.execute(self._sql(sql), tuple(params))
        return cur

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        cur = self.execute(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def one(self, sql: str, params: Iterable[Any] = ()) -> Optional[dict]:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def insert(self, sql: str, params: Iterable[Any] = ()) -> Optional[int]:
        """Insert and return the new row id."""
        if self.is_postgres:
            cur = self.execute(sql.rstrip().rstrip(";") + " RETURNING id", params)
            row = cur.fetchone()
            return row[0] if row else None
        cur = self.execute(sql, params)
        return cur.lastrowid

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------- schema
    def migrate(self) -> None:
        ddl = SCHEMA_PATH.read_text(encoding="utf-8")
        if self.is_postgres:
            # SQLite spells autoincrement PKs differently.
            ddl = ddl.replace("INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY")
            self.conn.cursor().execute(ddl)
        else:
            self.conn.executescript(ddl)
        self.commit()

    # --------------------------------------------------------- provenance
    def record_source(
        self, source_id: int, *, original_entity_id: str = "", source_url: str = "",
        published_at: str = "", dataset_version: str = "", license: str = "",
        raw: Any = None, import_id: Optional[int] = None,
    ) -> int:
        """Store one source record and return its id. Every fact must cite one."""
        payload = json.dumps(raw, ensure_ascii=False) if raw is not None else None
        content_hash = str(abs(hash(payload or original_entity_id)))
        return self.insert(
            """INSERT INTO source_record
               (source_id, import_id, original_entity_id, source_url, retrieved_at,
                published_at, dataset_version, license, content_hash, raw_payload)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (source_id, import_id, original_entity_id, source_url, utcnow(),
             published_at or None, dataset_version or None, license or None,
             content_hash, payload),
        )

    def start_import(self, source_id: int, dataset_version: str = "") -> int:
        return self.insert(
            """INSERT INTO source_import (source_id, dataset_version, started_at, status)
               VALUES (?,?,?,'running')""",
            (source_id, dataset_version or None, utcnow()),
        )

    def finish_import(self, import_id: int, status: str, records: int = 0,
                      changed: int = 0, error: str = "") -> None:
        self.execute(
            """UPDATE source_import
               SET finished_at=?, status=?, record_count=?, changed_count=?, error_log=?
               WHERE id=?""",
            (utcnow(), status, records, changed, error or None, import_id),
        )
        self.commit()


def connect(url: Optional[str] = None, *, migrate: bool = False) -> Database:
    db = Database(url)
    if migrate:
        db.migrate()
    return db
