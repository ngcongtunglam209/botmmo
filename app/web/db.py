"""Truy cập SQLite cho web admin.

Web cũ dùng dict global trong RAM rồi dump ngược vào kv_store. Ở đây SQLite là
nguồn sự thật: mỗi request đọc lại, mỗi ghi đi qua một transaction.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .settings import get_settings

_local = threading.local()


def _configure(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA foreign_keys=ON")


def _connect() -> sqlite3.Connection:
    path = Path(get_settings().db_path)
    if path.is_dir():
        # docker-compose bind-mount `./database.sqlite:/app/database.sqlite`: nếu
        # file trên host chưa tồn tại, Docker tạo một *thư mục* trùng tên và
        # sqlite chỉ báo "unable to open database file".
        raise RuntimeError(
            f"{path} là thư mục chứ không phải file SQLite. "
            "Tạo file rỗng trên host (`touch database.sqlite`) rồi dựng lại container."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10, check_same_thread=False)
    _configure(conn)
    _create_tables(conn)
    return conn


def get_connection() -> sqlite3.Connection:
    """Một connection cho mỗi thread (FastAPI chạy sync handler trong threadpool).

    Database chỉ được mở ở lần dùng thật đầu tiên, không phải lúc import: web
    chạy chung process với bot và không được chạm đĩa trước khi bot init_db.

    Schema dựng theo từng connection chứ không theo cờ toàn cục — cờ toàn cục
    sẽ bỏ qua việc tạo bảng khi database bị thay (mỗi test một file tạm).
    """
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = _connect()
        _local.conn = conn
    return conn


def close_connection() -> None:
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """Ghi có commit/rollback. Lồng nhau không được — giữ mỗi action một transaction."""
    conn = get_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    conn.commit()


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    return list(get_connection().execute(sql, params).fetchall())


def query_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    return get_connection().execute(sql, params).fetchone()


# --- kv_store ---------------------------------------------------------------

def kv_read(key: str, default: Any) -> Any:
    """Đọc một blob JSON trong kv_store. Trả default nếu thiếu hoặc hỏng."""
    row = query_one("SELECT value FROM kv_store WHERE key=?", (key,))
    if row is None:
        return default
    try:
        return json.loads(row["value"])
    except (json.JSONDecodeError, TypeError):
        return default


def kv_write(key: str, value: Any, conn: sqlite3.Connection | None = None) -> None:
    payload = json.dumps(value, ensure_ascii=False)
    if conn is not None:
        conn.execute(
            "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)", (key, payload)
        )
        return
    with transaction() as own:
        own.execute(
            "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)", (key, payload)
        )


def ensure_schema() -> None:
    """Tạo bảng ngay lập tức. Đường chạy bình thường dùng bản lười trong
    `get_connection()`; hàm này để test dựng sẵn database."""
    _create_tables(get_connection())


def _create_tables(conn: sqlite3.Connection) -> None:
    """Bảng web cần, nếu bot chưa chạy init_db (test, hoặc web chạy riêng).

    Chỉ CREATE IF NOT EXISTS — không đụng gì tới bảng bot đã tạo.
    """
    with conn:
        conn.execute("CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS admin_sessions ("
            "token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL, "
            "created_at INTEGER NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS admin_login_attempts ("
            "ip TEXT NOT NULL, attempted_at INTEGER NOT NULL)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_admin_login_attempts_ip_time "
            "ON admin_login_attempts(ip, attempted_at)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS api_request_logs ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, requested_at REAL NOT NULL, "
            "key_fingerprint TEXT NOT NULL DEFAULT '', partner_name TEXT NOT NULL DEFAULT '', "
            "client_ip TEXT NOT NULL DEFAULT '', method TEXT NOT NULL, endpoint TEXT NOT NULL, "
            "status_code INTEGER NOT NULL, response_ms REAL NOT NULL DEFAULT 0)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS api_partner_ledger ("
            "entry_id TEXT PRIMARY KEY, created_at REAL NOT NULL, key_fingerprint TEXT NOT NULL, "
            "partner_name TEXT NOT NULL DEFAULT '', entry_type TEXT NOT NULL, amount INTEGER NOT NULL, "
            "balance_before INTEGER NOT NULL, balance_after INTEGER NOT NULL, "
            "reference TEXT NOT NULL DEFAULT '', reason TEXT NOT NULL DEFAULT '', "
            "admin_actor TEXT NOT NULL DEFAULT '', idempotency_key TEXT NOT NULL UNIQUE)"
        )
