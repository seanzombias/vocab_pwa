import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

from config import (
    DATA_DIR,
    LOCAL_DB_PATH,
    TURSO_AUTH_TOKEN,
    TURSO_DATABASE_URL,
    normalize_turso_url,
    use_turso,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vocab (
    id TEXT PRIMARY KEY,
    word TEXT NOT NULL,
    phrase TEXT NOT NULL DEFAULT '',
    meaning TEXT NOT NULL,
    sentence TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vocab_created_at ON vocab(created_at);
"""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _row_to_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(row)
    tags = item.get("tags") or "[]"
    try:
        item["tags"] = json.loads(tags) if isinstance(tags, str) else tags
    except json.JSONDecodeError:
        item["tags"] = []
    return item


class Database:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._turso_client = None
        self.backend = "sqlite"
        if use_turso():
            import libsql_client

            self.backend = "turso"
            self._turso_client = libsql_client.create_client_sync(
                normalize_turso_url(TURSO_DATABASE_URL),
                auth_token=TURSO_AUTH_TOKEN,
            )
        self.init_schema()

    def init_schema(self) -> None:
        for statement in SCHEMA_SQL.strip().split(";"):
            sql = statement.strip()
            if sql:
                self.execute(sql)

    def ping(self) -> bool:
        row = self.fetchone("SELECT 1 AS ok")
        return bool(row and row.get("ok") == 1)

    @contextmanager
    def _sqlite_conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def execute(self, sql: str, params: tuple = ()) -> None:
        if self._turso_client:
            self._turso_client.execute(sql, params)
            return
        with self._sqlite_conn() as conn:
            conn.execute(sql, params)

    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        if self._turso_client:
            result = self._turso_client.execute(sql, params)
            return [dict(zip(result.columns, row)) for row in result.rows]
        with self._sqlite_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        rows = self.fetchall(sql, params)
        return rows[0] if rows else None

    def list_vocab(
        self,
        *,
        date: Optional[str] = None,
        tag: Optional[str] = None,
        today: bool = False,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM vocab WHERE 1=1"
        params: List[Any] = []

        if today:
            today_prefix = datetime.now(timezone.utc).date().isoformat()
            sql += " AND created_at LIKE ?"
            params.append(f"{today_prefix}%")
        elif date:
            sql += " AND created_at LIKE ?"
            params.append(f"{date}%")

        if query:
            sql += " AND (word LIKE ? OR phrase LIKE ? OR meaning LIKE ? OR sentence LIKE ?)"
            like = f"%{query}%"
            params.extend([like, like, like, like])

        sql += " ORDER BY created_at DESC, word ASC"
        rows = self.fetchall(sql, tuple(params))

        if tag:
            rows = [row for row in rows if tag in (_row_to_dict(row).get("tags") or [])]

        return [_row_to_dict(row) for row in rows]

    def get_tags(self) -> List[Dict[str, Any]]:
        rows = self.fetchall("SELECT tags FROM vocab")
        counts: Dict[str, int] = {}
        for row in rows:
            item = _row_to_dict(row)
            for tag in item.get("tags") or []:
                counts[tag] = counts.get(tag, 0) + 1
        return [{"tag": tag, "count": count} for tag, count in sorted(counts.items())]

    def get_dates(self) -> List[str]:
        rows = self.fetchall("SELECT created_at FROM vocab ORDER BY created_at DESC")
        dates = set()
        for row in rows:
            created_at = row.get("created_at") or ""
            if len(created_at) >= 10:
                dates.add(created_at[:10])
        return sorted(dates, reverse=True)

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        entry = self._normalize_payload(payload)
        self.execute(
            """
            INSERT INTO vocab (id, word, phrase, meaning, sentence, source, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry["id"],
                entry["word"],
                entry["phrase"],
                entry["meaning"],
                entry["sentence"],
                entry["source"],
                json.dumps(entry["tags"], ensure_ascii=False),
                entry["created_at"],
            ),
        )
        return entry

    def create_many(self, payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.create(payload) for payload in payloads]

    def delete(self, entry_id: str) -> bool:
        existing = self.fetchone("SELECT id FROM vocab WHERE id = ?", (entry_id,))
        if not existing:
            return False
        self.execute("DELETE FROM vocab WHERE id = ?", (entry_id,))
        return True

    def _normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        word = (payload.get("word") or "").strip()
        meaning = (payload.get("meaning") or "").strip()
        sentence = (payload.get("sentence") or "").strip()
        if not word or not meaning or not sentence:
            raise ValueError("word, meaning, and sentence are required")

        tags = payload.get("tags") or []
        if isinstance(tags, str):
            tags = [part.strip() for part in tags.split(",") if part.strip()]

        created_at = payload.get("created_at") or _utc_now_iso()
        return {
            "id": payload.get("id") or str(uuid.uuid4()),
            "word": word,
            "phrase": (payload.get("phrase") or "").strip(),
            "meaning": meaning,
            "sentence": sentence,
            "source": (payload.get("source") or "").strip(),
            "tags": tags,
            "created_at": created_at,
        }


_db: Optional[Database] = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db
