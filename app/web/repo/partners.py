"""API partner: key, ví, sổ cái và log request."""

from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from typing import Any

from ..db import query, transaction
from . import collections
from .base import as_int

DEFAULT_RATE_LIMIT = 60
DEFAULT_LOW_BALANCE = 100_000
KEY_PREFIX = "LAMSHOP"


def all_keys() -> dict[str, dict]:
    """Chuẩn hóa: bản ghi cũ có thể là chuỗi tên thay vì dict."""
    result: dict[str, dict] = {}
    for key, data in collections.api_keys.read().items():
        if isinstance(data, dict):
            result[str(key)] = data
        else:
            result[str(key)] = {"name": str(data), "balance": 0}
    return result


def get_key(api_key: str) -> dict | None:
    return all_keys().get(str(api_key or "").strip())


def find_key(target: str) -> str | None:
    """Tìm theo key đầy đủ, public id hoặc tên partner."""
    needle = str(target or "").strip()
    if not needle:
        return None
    keys = all_keys()
    if needle in keys:
        return needle
    lowered = needle.casefold()
    for api_key, data in keys.items():
        if public_id(api_key).casefold() == lowered:
            return api_key
        if str(data.get("name") or "").strip().casefold() == lowered:
            return api_key
    return None


def public_id(api_key: str) -> str:
    """ID công khai an toàn để hiển thị thay cho key thật."""
    digest = hashlib.sha256(str(api_key or "").encode()).hexdigest()
    return f"pk_{digest[:12]}"


def fingerprint(api_key: str) -> str:
    return hashlib.sha256(str(api_key or "").encode()).hexdigest()[:16]


def masked(api_key: str, visible: int = 5) -> str:
    text = str(api_key or "")
    if len(text) <= visible:
        return "*" * len(text)
    return f"{text[:visible]}{'*' * (len(text) - visible)}"


def generate_key() -> str:
    return f"{KEY_PREFIX}-{secrets.token_urlsafe(24)}"


def create_key(name: str, balance: int = 0) -> tuple[str, dict]:
    api_key = generate_key()
    record = {
        "name": name,
        "balance": max(0, int(balance or 0)),
        "enabled": True,
        "rate_limit_per_minute": DEFAULT_RATE_LIMIT,
        "allowed_ips": [],
        "low_balance_threshold": DEFAULT_LOW_BALANCE,
        "low_balance_alert_enabled": True,
        "created_at": int(time.time()),
    }
    with collections.api_keys.mutate() as keys:
        keys[api_key] = record
    return api_key, record


def update_key(api_key: str, changes: dict[str, Any]) -> dict | None:
    with collections.api_keys.mutate() as keys:
        record = keys.get(api_key)
        if not isinstance(record, dict):
            if record is None:
                return None
            record = {"name": str(record), "balance": 0}
        record.update(changes)
        keys[api_key] = record
    return record


def rotate_key(api_key: str) -> tuple[str, dict] | None:
    """Cấp key mới giữ nguyên số dư, khóa key cũ và trỏ sang key mới."""
    current = get_key(api_key)
    if current is None:
        return None
    new_key = generate_key()
    new_record = dict(current)
    new_record.update({"enabled": True, "rotated_from": public_id(api_key), "updated_at": int(time.time())})
    new_record.pop("rotated_to", None)
    with collections.api_keys.mutate() as keys:
        old = keys.get(api_key)
        if isinstance(old, dict):
            old["enabled"] = False
            old["rotated_to"] = public_id(new_key)
            old["revoked_at"] = int(time.time())
            old["balance"] = 0
        keys[new_key] = new_record
    return new_key, new_record


def adjust_balance(
    api_key: str,
    delta: int,
    reason: str,
    entry_type: str,
    admin_actor: str = "admin_web",
) -> tuple[bool, int]:
    """Cộng/trừ ví partner và ghi sổ cái. Trả (thành công, số dư mới)."""
    record = get_key(api_key)
    if record is None:
        return False, 0
    before = as_int(record.get("balance"), 0)
    after = before + int(delta)
    if after < 0:
        return False, before
    update_key(api_key, {"balance": after, "updated_at": int(time.time())})
    _write_ledger(api_key, record, entry_type, int(delta), before, after, reason, admin_actor)
    return True, after


def set_balance(
    api_key: str, amount: int, reason: str, admin_actor: str = "admin_web"
) -> tuple[bool, int]:
    record = get_key(api_key)
    if record is None:
        return False, 0
    before = as_int(record.get("balance"), 0)
    after = max(0, int(amount))
    update_key(api_key, {"balance": after, "updated_at": int(time.time())})
    _write_ledger(
        api_key, record, "adjustment", after - before, before, after, reason, admin_actor
    )
    return True, after


def _write_ledger(
    api_key: str,
    record: dict,
    entry_type: str,
    amount: int,
    before: int,
    after: int,
    reason: str,
    admin_actor: str,
) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO api_partner_ledger "
            "(entry_id, created_at, key_fingerprint, partner_name, entry_type, amount, "
            "balance_before, balance_after, reference, reason, admin_actor, idempotency_key) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                uuid.uuid4().hex,
                time.time(),
                fingerprint(api_key),
                str(record.get("name") or ""),
                entry_type,
                amount,
                before,
                after,
                "",
                reason,
                admin_actor,
                uuid.uuid4().hex,
            ),
        )


def ledger(api_key: str, limit: int = 50) -> list[dict]:
    rows = query(
        "SELECT * FROM api_partner_ledger WHERE key_fingerprint=? "
        "ORDER BY created_at DESC LIMIT ?",
        (fingerprint(api_key), limit),
    )
    return [dict(row) for row in rows]


def request_logs(api_key: str, limit: int = 50) -> list[dict]:
    rows = query(
        "SELECT * FROM api_request_logs WHERE key_fingerprint=? "
        "ORDER BY requested_at DESC LIMIT ?",
        (fingerprint(api_key), limit),
    )
    return [dict(row) for row in rows]


def analytics(api_key: str = "", days: int = 14) -> dict:
    """Tổng request và tỉ lệ lỗi trong N ngày, cho toàn hệ thống hoặc một key."""
    since = time.time() - days * 86400
    if api_key:
        rows = query(
            "SELECT status_code, COUNT(*) AS total FROM api_request_logs "
            "WHERE key_fingerprint=? AND requested_at>=? GROUP BY status_code",
            (fingerprint(api_key), since),
        )
    else:
        rows = query(
            "SELECT status_code, COUNT(*) AS total FROM api_request_logs "
            "WHERE requested_at>=? GROUP BY status_code",
            (since,),
        )
    total = sum(int(row["total"]) for row in rows)
    errors = sum(int(row["total"]) for row in rows if int(row["status_code"]) >= 400)
    error_rate = round(errors * 100 / total, 2) if total else 0
    return {"total": total, "errors": errors, "error_rate": error_rate}


def daily_traffic(api_key: str, days: int = 14) -> list[tuple[str, int]]:
    since = time.time() - days * 86400
    rows = query(
        "SELECT CAST(requested_at AS INTEGER) / 86400 AS bucket, COUNT(*) AS total "
        "FROM api_request_logs WHERE key_fingerprint=? AND requested_at>=? "
        "GROUP BY bucket ORDER BY bucket",
        (fingerprint(api_key), since),
    )
    return [
        (time.strftime("%d/%m", time.localtime(int(row["bucket"]) * 86400)), int(row["total"]))
        for row in rows
    ]


def normalize_allowed_ips(value: Any) -> list[str]:
    """Nhận chuỗi ngăn cách bởi dấu phẩy/xuống dòng hoặc list, trả list sạch."""
    if isinstance(value, (list, tuple, set)):
        candidates = [str(item) for item in value]
    else:
        candidates = str(value or "").replace("\n", ",").replace(";", ",").split(",")
    return [item.strip() for item in candidates if item.strip()]


def rate_limit(record: dict) -> int:
    return max(1, as_int(record.get("rate_limit_per_minute"), DEFAULT_RATE_LIMIT))


def low_balance_threshold(record: dict) -> int:
    return max(0, as_int(record.get("low_balance_threshold"), DEFAULT_LOW_BALANCE))


def is_low_balance(record: dict) -> bool:
    return as_int(record.get("balance"), 0) <= low_balance_threshold(record)


def is_active(record: dict) -> bool:
    return record.get("enabled") is not False
