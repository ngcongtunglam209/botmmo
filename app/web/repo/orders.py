"""Đọc/ghi đơn hàng: lịch sử, pending thanh toán, pending manual."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from typing import Any

from .. import domain
from . import collections
from .base import as_int, lookup


def history() -> list[dict]:
    return [order for order in collections.order_history.read() if isinstance(order, dict)]


def count_history() -> int:
    return len(collections.order_history.read())


def recent(limit: int) -> list[dict]:
    """Đơn mới nhất trước."""
    return history()[-limit:][::-1]


def find(order_code: str) -> dict | None:
    target = str(order_code or "").strip().upper()
    if not target:
        return None
    for order in reversed(history()):
        if domain.order_code(order).upper() == target:
            return order
    for source in (pending(), pending_manual()):
        record = lookup(source, target)
        if isinstance(record, dict):
            return record
    return None


def update_records(order_code: str, changes: dict[str, Any]) -> int:
    """Áp thay đổi lên mọi bản ghi của mã đơn. Trả số bản ghi đã sửa."""
    target = str(order_code or "").strip().upper()
    touched = 0

    with collections.order_history.mutate() as orders:
        for order in orders:
            if isinstance(order, dict) and domain.order_code(order).upper() == target:
                order.update(changes)
                touched += 1

    for source in (collections.pending_orders, collections.pending_manual_orders):
        data = source.read()
        record = lookup(data, target)
        if isinstance(record, dict):
            with source.mutate() as mutable:
                key = target if target in mutable else str(target)
                if key in mutable and isinstance(mutable[key], dict):
                    mutable[key].update(changes)
                    touched += 1
    return touched


def user_orders(user_id: Any, limit: int = 30) -> list[dict]:
    target = str(user_id)
    matched = [
        order
        for order in history()
        if str(order.get("user_id") or order.get("buyer_id") or "") == target
    ]
    return matched[-limit:][::-1]


def pending() -> dict:
    return collections.pending_orders.read()


def pending_manual() -> dict:
    return collections.pending_manual_orders.read()


def completed(source: list[dict] | None = None) -> Iterator[dict]:
    for order in history() if source is None else source:
        if domain.is_completed_order(order) and not order.get("refunded_at"):
            yield order


def financial_summary() -> dict[str, int]:
    """Doanh thu/lãi tổng và trong ngày, cùng độ phủ giá vốn."""
    return summarize(history())


def summarize(source: list[dict]) -> dict[str, int]:
    """Bản thuần của financial_summary — tính trên list truyền vào."""
    today = date.today()
    summary = {
        "revenue": 0,
        "today_revenue": 0,
        "profit": 0,
        "today_profit": 0,
        "costed": 0,
        "today_costed": 0,
        "completed": 0,
    }
    for order in completed(source):
        summary["completed"] += 1
        amount = as_int(order.get("amount"), 0)
        summary["revenue"] += amount
        is_today = _is_today(order, today)
        if is_today:
            summary["today_revenue"] += amount
        if order.get("cost_total") is None:
            continue
        profit = amount - as_int(order.get("cost_total"), 0)
        summary["costed"] += 1
        summary["profit"] += profit
        if is_today:
            summary["today_costed"] += 1
            summary["today_profit"] += profit
    return summary


def _is_today(order: dict, today: date) -> bool:
    try:
        return datetime.fromtimestamp(domain.order_timestamp(order)).date() == today
    except (TypeError, ValueError, OSError, OverflowError):
        return False


def revenue_by_day(days: int = 30) -> list[tuple[str, int]]:
    """Doanh thu từng ngày, cũ đến mới, dùng cho biểu đồ tổng quan."""
    buckets: dict[str, int] = {}
    for order in completed(None):
        try:
            day = datetime.fromtimestamp(domain.order_timestamp(order)).date()
        except (TypeError, ValueError, OSError, OverflowError):
            continue
        buckets[day.isoformat()] = buckets.get(day.isoformat(), 0) + as_int(
            order.get("amount"), 0
        )
    return sorted(buckets.items())[-days:]
