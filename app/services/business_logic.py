"""
Business logic services that were previously embedded in config_env.py.

This module extracts revenue tracking, promo budget management, and rate
limiting into proper functions with explicit dependencies instead of relying
on implicit globals from the shared namespace.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any


# ── Revenue Tracking ──────────────────────────────────────────────────

def get_today_revenue(
    order_history: list[dict[str, Any]],
    status_text_fn: Any = None,
) -> int:
    """Calculate today's completed order revenue.

    Args:
        order_history: List of order dicts.
        status_text_fn: Legacy status_text() callable. If None, does basic
                        string matching on the raw status field.
    """
    today = datetime.now().date()
    revenue = 0
    for order in order_history:
        status = order.get("status", "")
        if status_text_fn is not None:
            status = status_text_fn(status)
        if "Hoàn thành" in str(status):
            ts = order.get("timestamp")
            if ts is not None:
                try:
                    if datetime.fromtimestamp(ts).date() == today:
                        revenue += order.get("amount", 0)
                except (ValueError, TypeError, OSError):
                    pass
    return revenue


# ── Promo Budget Management ──────────────────────────────────────────

def get_daily_promo_budget(
    revenue: int,
    budget_percent: int = 15,
    min_budget: int = 20_000,
) -> int:
    """Get today's promo budget = max(min_budget, percent% of revenue)."""
    calculated = int(revenue * budget_percent / 100)
    return max(min_budget, calculated)


def get_daily_promo_spent(tracker: dict[str, Any]) -> int:
    """Get total promo cost spent today."""
    today = datetime.now().strftime("%Y-%m-%d")
    return tracker.get(today, {}).get("total", 0)


def can_spend_promo(
    amount: int,
    tracker: dict[str, Any],
    revenue: int,
    budget_percent: int = 15,
    min_budget: int = 20_000,
) -> bool:
    """Check if we can afford this promo cost within today's budget."""
    budget = get_daily_promo_budget(revenue, budget_percent, min_budget)
    spent = get_daily_promo_spent(tracker)
    return (spent + amount) <= budget


def record_promo_cost(
    tracker: dict[str, Any],
    amount: int,
    promo_type: str = "other",
) -> None:
    """Record a promo cost for today, mutating the tracker dict."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Clean old days
    old_keys = [k for k in tracker if k != today]
    for k in old_keys:
        tracker.pop(k, None)

    if today not in tracker:
        tracker[today] = {"total": 0, "details": []}

    tracker[today]["total"] += amount
    tracker[today]["details"].append({
        "amount": amount,
        "type": promo_type,
        "time": time.time(),
    })

    # Cap detail history
    if len(tracker[today]["details"]) > 200:
        tracker[today]["details"] = tracker[today]["details"][-100:]


def get_promo_budget_status(
    tracker: dict[str, Any],
    order_history: list[dict[str, Any]],
    status_text_fn: Any = None,
    budget_percent: int = 15,
    min_budget: int = 20_000,
) -> dict[str, int]:
    """Get budget status summary for admin display."""
    revenue = get_today_revenue(order_history, status_text_fn)
    budget = get_daily_promo_budget(revenue, budget_percent, min_budget)
    spent = get_daily_promo_spent(tracker)
    remaining = max(0, budget - spent)
    return {
        "revenue": revenue,
        "budget": budget,
        "spent": spent,
        "remaining": remaining,
        "percent_used": int(spent / budget * 100) if budget > 0 else 0,
    }


# ── Rate Limiting ────────────────────────────────────────────────────

class RateLimiter:
    """Per-user rate limiter with configurable cooldown.

    Replaces the global `user_last_action` dict + `check_rate_limit()` function
    from config_env.py.
    """

    def __init__(self, cooldown: float = 1.0):
        self.cooldown = cooldown
        self._timestamps: dict[int, float] = {}

    async def check(self, user_id: int) -> bool:
        """Return True if the action is allowed, False if rate-limited."""
        now = time.time()
        last = self._timestamps.get(user_id, 0)
        if now - last < self.cooldown:
            return False
        self._timestamps[user_id] = now
        return True

    def reset(self, user_id: int) -> None:
        """Clear rate limit for a specific user."""
        self._timestamps.pop(user_id, None)

    def cleanup(self, max_age: float = 3600) -> int:
        """Remove entries older than max_age. Returns count removed."""
        now = time.time()
        expired = [uid for uid, ts in self._timestamps.items() if now - ts > max_age]
        for uid in expired:
            del self._timestamps[uid]
        return len(expired)
