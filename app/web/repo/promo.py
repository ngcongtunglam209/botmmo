"""Coupon, flash sale, combo, giveaway và ngân sách khuyến mãi."""

from __future__ import annotations

import time
from typing import Any

from . import collections
from .base import as_int


def all_coupons() -> dict[str, dict]:
    return {
        str(code): (data if isinstance(data, dict) else {})
        for code, data in collections.coupons.read().items()
    }


def get_coupon(code: str) -> dict | None:
    coupon = all_coupons().get(str(code or "").strip().upper())
    return coupon


def save_coupon(code: str, payload: dict[str, Any]) -> None:
    with collections.coupons.mutate() as data:
        data[str(code).upper()] = payload


def delete_coupon(code: str) -> bool:
    target = str(code or "").strip().upper()
    with collections.coupons.mutate() as data:
        if target not in data:
            return False
        data.pop(target, None)
    return True


def promo_spent_today() -> int:
    """Số tiền khuyến mãi đã chi trong ngày hôm nay."""
    tracker = collections.promo_budget.read()
    today = time.strftime("%Y-%m-%d")
    entry = tracker.get(today) or tracker.get("today")
    if isinstance(entry, dict):
        return as_int(entry.get("spent"), 0)
    return as_int(entry, 0)


def snapshot() -> dict[str, int]:
    return {
        "coupons": len(collections.coupons.read()),
        "flash_sales": len(collections.flash_sales.read()),
        "combo_deals": len(collections.combo_deals.read()),
        "giveaways": len(collections.giveaways.read()),
        "spent_today": promo_spent_today(),
    }
