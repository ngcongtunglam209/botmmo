"""Ticket hỗ trợ: live chat, bảo hành, yêu cầu rút tiền."""

from __future__ import annotations

import time
from typing import Any

from . import collections
from .base import lookup, resolve_key

OPEN_STATUSES = {None, "", "pending", "open", "active"}

SOURCES = {
    "live_chat": collections.live_chats,
    "warranty": collections.warranty_claims,
    "withdrawal": collections.withdrawals,
}

LABELS = {
    "live_chat": "Live chat",
    "warranty": "Bảo hành",
    "withdrawal": "Rút tiền",
}


def entity_valid(entity: str) -> bool:
    return entity in SOURCES


def all_items(entity: str) -> dict[str, dict]:
    source = SOURCES.get(entity)
    if source is None:
        return {}
    return {
        str(key): value
        for key, value in source.read().items()
        if isinstance(value, dict)
    }


def get_item(entity: str, item_id: str) -> dict | None:
    source = SOURCES.get(entity)
    if source is None:
        return None
    item = lookup(source.read(), str(item_id or "").strip())
    return item if isinstance(item, dict) else None


def update_item(entity: str, item_id: str, changes: dict[str, Any]) -> bool:
    source = SOURCES.get(entity)
    if source is None:
        return False
    with source.mutate() as data:
        key = resolve_key(data, str(item_id or "").strip())
        item = data.get(key)
        if not isinstance(item, dict):
            return False
        item.update(changes)
        item["updated_at"] = int(time.time())
        item["updated_by"] = "admin_web"
        data[key] = item
    return True


def is_open(item: dict) -> bool:
    return item.get("status") in OPEN_STATUSES


def open_count() -> int:
    return sum(
        1
        for entity in SOURCES
        for item in all_items(entity).values()
        if is_open(item)
    )


def rows(limit: int = 120) -> list[dict]:
    """Gom cả ba loại ticket thành một danh sách để render một bảng."""
    result: list[dict] = []
    for entity, label in LABELS.items():
        for item_id, item in all_items(entity).items():
            result.append(
                {
                    "entity": entity,
                    "label": label,
                    "id": item_id,
                    "user_id": item.get("user_id") or item.get("chat_id") or "",
                    "status": str(item.get("status") or "pending"),
                    "open": is_open(item),
                    "summary": _summary(item),
                    "updated_at": item.get("updated_at") or item.get("created_at") or 0,
                }
            )
    result.sort(key=lambda row: (not row["open"], -int(row["updated_at"] or 0)))
    return result[:limit]


def _summary(item: dict) -> str:
    for field in ("message", "reason", "note", "content", "product_name", "order_code"):
        value = str(item.get(field) or "").strip()
        if value:
            return value
    return ""
