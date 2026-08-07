"""Helpers for preserving original delivery data and warranty replacements."""

from __future__ import annotations

import time
from typing import Any

WARRANTY_REPLACEMENT_HISTORY_LIMIT = 50
_NON_DELIVERY_LINK_MARKERS = {
    "",
    "store product",
    "sản phẩm khác",
}


def _clean_items(items: Any) -> list[str]:
    if items is None:
        return []
    source = items if isinstance(items, (list, tuple, set)) else [items]
    cleaned = [str(item).strip() for item in source if str(item or "").strip()]
    return list(dict.fromkeys(cleaned))


def _clean_link(value: Any) -> str:
    link = str(value or "").strip()
    return "" if link.casefold() in _NON_DELIVERY_LINK_MARKERS else link


def ensure_warranty_original_delivery(order: dict) -> dict:
    """Snapshot the original delivery before the first replacement mutates it."""

    if not isinstance(order, dict):
        return {}
    if "warranty_original_items" not in order:
        order["warranty_original_items"] = _clean_items(order.get("items"))
    if "warranty_original_link" not in order:
        order["warranty_original_link"] = _clean_link(order.get("link"))
    return order


def record_warranty_replacement(
    order: dict,
    items: Any,
    *,
    source: str,
    admin_user_id: Any = None,
    created_at: float | None = None,
    note: str = "",
) -> dict:
    """Append one immutable warranty replacement event to an order."""

    if not isinstance(order, dict):
        raise TypeError("order must be a dict")
    clean_items = _clean_items(items)
    if not clean_items:
        raise ValueError("replacement must contain at least one item")

    ensure_warranty_original_delivery(order)
    history = order.get("warranty_replacements")
    if not isinstance(history, list):
        history = []

    event = {
        "items": clean_items,
        "source": str(source or "manual").strip() or "manual",
        "created_at": float(created_at if created_at is not None else time.time()),
    }
    if admin_user_id is not None and str(admin_user_id).strip():
        event["admin_user_id"] = admin_user_id
    clean_note = str(note or "").strip()
    if clean_note:
        event["note"] = clean_note[:500]

    history.append(event)
    order["warranty_replacements"] = history[-WARRANTY_REPLACEMENT_HISTORY_LIMIT:]
    order["support_status"] = "warranty_replaced"
    order["support_resolved_at"] = event["created_at"]
    if admin_user_id is not None:
        order["support_resolved_by"] = admin_user_id
    return event


def get_original_delivery_items(order: dict | None) -> list[str]:
    if not isinstance(order, dict):
        return []
    if "warranty_original_items" in order:
        return _clean_items(order.get("warranty_original_items"))
    return _clean_items(order.get("items"))


def get_original_delivery_link(order: dict | None) -> str:
    if not isinstance(order, dict):
        return ""
    if "warranty_original_link" in order:
        return _clean_link(order.get("warranty_original_link"))
    return _clean_link(order.get("link"))


def get_latest_warranty_replacement(order: dict | None) -> dict | None:
    if not isinstance(order, dict):
        return None
    history = order.get("warranty_replacements")
    if not isinstance(history, list):
        return None
    valid = [entry for entry in history if isinstance(entry, dict) and _clean_items(entry.get("items"))]
    if not valid:
        return None
    latest = max(valid, key=lambda entry: float(entry.get("created_at", 0) or 0))
    return {**latest, "items": _clean_items(latest.get("items"))}
