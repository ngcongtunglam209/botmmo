"""Phiên đăng nhập admin và chống dò mật khẩu — lưu trong bảng SQLite riêng."""

from __future__ import annotations

import hashlib
import time

from ..db import query_one, transaction


def _hash(token: str) -> str:
    return hashlib.sha256(str(token or "").encode()).hexdigest()


def create(token: str, expires_at: int) -> None:
    with transaction() as conn:
        conn.execute("DELETE FROM admin_sessions WHERE expires_at < ?", (int(time.time()),))
        conn.execute(
            "INSERT OR REPLACE INTO admin_sessions (token_hash, expires_at, created_at) "
            "VALUES (?, ?, ?)",
            (_hash(token), int(expires_at), int(time.time())),
        )


def exists(token: str) -> bool:
    if not token:
        return False
    row = query_one(
        "SELECT expires_at FROM admin_sessions WHERE token_hash=?", (_hash(token),)
    )
    return bool(row) and int(row["expires_at"]) > int(time.time())


def revoke(token: str) -> None:
    if not token:
        return
    with transaction() as conn:
        conn.execute("DELETE FROM admin_sessions WHERE token_hash=?", (_hash(token),))


def record_attempt(ip: str) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO admin_login_attempts (ip, attempted_at) VALUES (?, ?)",
            (str(ip or ""), int(time.time())),
        )


def attempts_within(ip: str, window_seconds: int) -> int:
    row = query_one(
        "SELECT COUNT(*) AS total FROM admin_login_attempts "
        "WHERE ip=? AND attempted_at >= ?",
        (str(ip or ""), int(time.time()) - window_seconds),
    )
    return int(row["total"]) if row else 0


def clear_attempts(ip: str) -> None:
    with transaction() as conn:
        conn.execute("DELETE FROM admin_login_attempts WHERE ip=?", (str(ip or ""),))
