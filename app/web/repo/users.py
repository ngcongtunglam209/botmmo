"""Đọc/ghi user, ví và lịch sử số dư."""

from __future__ import annotations

import time
from typing import Any

from . import collections
from .base import as_int, lookup, resolve_key


def all_users() -> dict[str, dict]:
    return {
        str(uid): data
        for uid, data in collections.users.read().items()
        if isinstance(data, dict)
    }


def get_user(user_id: str) -> dict | None:
    profile = lookup(collections.users.read(), str(user_id or "").strip())
    return profile if isinstance(profile, dict) else None


def count_users() -> int:
    return len(collections.users.read())


def banned_ids() -> set[str]:
    return {str(uid) for uid in collections.banned_users.read()}


def is_banned(user_id: Any) -> bool:
    return str(user_id) in banned_ids()


def set_banned(user_id: Any, banned: bool) -> None:
    current = collections.banned_users.read()
    target = str(user_id)
    remaining = [uid for uid in current if str(uid) != target]
    if banned:
        try:
            remaining.append(int(target))
        except ValueError:
            remaining.append(target)
    collections.banned_users.write(remaining)


def balance_of(user_id: Any) -> int:
    profile = get_user(user_id)
    return as_int(profile.get("balance"), 0) if profile else 0


def upsert_profile(user_id: str, changes: dict[str, Any]) -> dict:
    """Ghi các trường vào hồ sơ user, tạo mới nếu chưa có."""
    with collections.users.mutate() as data:
        key = resolve_key(data, str(user_id))
        profile = data.get(key)
        if not isinstance(profile, dict):
            profile = {"user_id": int(user_id), "balance": 0}
            data[str(user_id)] = profile
            key = str(user_id)
        profile.update(changes)
        data[key] = profile
    return profile


def set_balance(user_id: str, new_balance: int, reason: str) -> int:
    """Đặt số dư mới và ghi một dòng vào lịch sử giao dịch."""
    previous = balance_of(user_id)
    upsert_profile(user_id, {"balance": int(new_balance)})
    _append_transaction(user_id, previous, int(new_balance), reason)
    return previous


def _append_transaction(user_id: str, before: int, after: int, reason: str) -> None:
    with collections.transaction_history.mutate() as history:
        key = resolve_key(history, str(user_id))
        entries = history.get(key)
        if not isinstance(entries, list):
            entries = []
            key = str(user_id)
        entries.append(
            {
                "timestamp": int(time.time()),
                "amount": after - before,
                "balance_before": before,
                "balance_after": after,
                "reason": reason,
                "source": "admin_web",
            }
        )
        history[key] = entries


def transactions_for(user_id: str, limit: int = 30) -> list[dict]:
    entries = lookup(collections.transaction_history.read(), str(user_id))
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries[-limit:] if isinstance(entry, dict)][::-1]


def top_by_balance(limit: int) -> list[tuple[str, dict]]:
    rows = list(all_users().items())
    rows.sort(key=lambda row: as_int(row[1].get("balance"), 0), reverse=True)
    return rows[:limit]
