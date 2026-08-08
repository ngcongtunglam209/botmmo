"""Tests for business logic services extracted from config_env.py."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from app.core.runtime_loader import load_modules
from app.services.business_logic import (
    RateLimiter,
    can_spend_promo,
    get_daily_promo_budget,
    get_daily_promo_spent,
    get_promo_budget_status,
    get_today_revenue,
    record_promo_cost,
)


class TestGetTodayRevenue:
    def test_empty_history(self):
        assert get_today_revenue([]) == 0

    def test_completed_today(self):
        orders = [
            {"status": "Hoàn thành", "timestamp": time.time(), "amount": 35000},
            {"status": "Hoàn thành", "timestamp": time.time(), "amount": 50000},
        ]
        assert get_today_revenue(orders) == 85000

    def test_ignores_non_completed(self):
        orders = [
            {"status": "pending_payment", "timestamp": time.time(), "amount": 35000},
        ]
        assert get_today_revenue(orders) == 0

    def test_ignores_yesterday(self):
        yesterday_ts = time.time() - 86400 * 2
        orders = [
            {"status": "Hoàn thành", "timestamp": yesterday_ts, "amount": 35000},
        ]
        assert get_today_revenue(orders) == 0

    def test_with_status_text_fn(self):
        orders = [
            {"status": "completed", "timestamp": time.time(), "amount": 25000},
        ]
        assert get_today_revenue(orders, status_text_fn=lambda s: "Hoàn thành" if s == "completed" else s) == 25000


class TestPromoBudget:
    def test_min_budget(self):
        assert get_daily_promo_budget(0) == 20_000

    def test_percentage_budget(self):
        # 15% of 1,000,000 = 150,000
        assert get_daily_promo_budget(1_000_000) == 150_000

    def test_custom_percent(self):
        assert get_daily_promo_budget(1_000_000, budget_percent=10) == 100_000

    def test_spent_tracking(self):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        tracker = {today: {"total": 5000, "details": []}}
        assert get_daily_promo_spent(tracker) == 5000

    def test_spent_empty(self):
        assert get_daily_promo_spent({}) == 0

    def test_can_spend_within_budget(self):
        assert can_spend_promo(5000, {}, revenue=1_000_000) is True

    def test_cannot_spend_over_budget(self):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        tracker = {today: {"total": 19000, "details": []}}
        assert can_spend_promo(5000, tracker, revenue=0) is False  # budget=20k, spent=19k+5k > 20k


class TestRecordPromoCost:
    def test_record_creates_entry(self):
        tracker: dict = {}
        record_promo_cost(tracker, 5000, "wheel")
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in tracker
        assert tracker[today]["total"] == 5000
        assert len(tracker[today]["details"]) == 1
        assert tracker[today]["details"][0]["type"] == "wheel"

    def test_record_accumulates(self):
        tracker: dict = {}
        record_promo_cost(tracker, 3000, "coupon")
        record_promo_cost(tracker, 2000, "referral")
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        assert tracker[today]["total"] == 5000
        assert len(tracker[today]["details"]) == 2


class TestPromoBudgetStatus:
    def test_returns_all_fields(self):
        result = get_promo_budget_status({}, [])
        assert "revenue" in result
        assert "budget" in result
        assert "spent" in result
        assert "remaining" in result
        assert "percent_used" in result


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_first_action_allowed(self):
        limiter = RateLimiter(cooldown=1.0)
        assert await limiter.check(123) is True

    @pytest.mark.asyncio
    async def test_rapid_action_blocked(self):
        limiter = RateLimiter(cooldown=10.0)  # Long cooldown
        await limiter.check(456)
        assert await limiter.check(456) is False  # Too fast

    @pytest.mark.asyncio
    async def test_different_users_independent(self):
        limiter = RateLimiter(cooldown=10.0)
        await limiter.check(100)
        assert await limiter.check(200) is True  # Different user

    def test_reset(self):
        limiter = RateLimiter()
        limiter._timestamps[999] = time.time()
        limiter.reset(999)
        assert 999 not in limiter._timestamps

    def test_cleanup_removes_old(self):
        limiter = RateLimiter()
        limiter._timestamps[1] = time.time() - 7200  # 2 hours old
        limiter._timestamps[2] = time.time()  # Fresh
        removed = limiter.cleanup(max_age=3600)
        assert removed == 1
        assert 1 not in limiter._timestamps
        assert 2 in limiter._timestamps


@pytest.mark.asyncio
async def test_navigation_callback_is_acknowledged_before_rendering(monkeypatch):
    callback_router = load_modules()["app.handlers.callback_router"]
    events = []

    class FakeQuery:
        data = "games_menu"

        async def answer(self, text=None, show_alert=False):
            events.append(("answer", text, show_alert))

    async def false_handler(*_args, **_kwargs):
        return False

    async def true_rate_limit(*_args, **_kwargs):
        return True

    async def games_handler(*_args, **_kwargs):
        events.append(("render", None, None))
        return True

    monkeypatch.setattr(callback_router, "check_if_banned", false_handler)
    monkeypatch.setattr(callback_router, "MAINTENANCE_MODE", False)
    monkeypatch.setattr(callback_router, "handle_store_callback", false_handler)
    monkeypatch.setattr(callback_router, "check_rate_limit", true_rate_limit)
    monkeypatch.setattr(callback_router, "handle_admin_callbacks", false_handler)
    monkeypatch.setattr(callback_router, "handle_games_callbacks", games_handler)

    update = SimpleNamespace(
        callback_query=FakeQuery(),
        effective_user=SimpleNamespace(id=123),
    )
    await callback_router.button_handler(update, SimpleNamespace())

    assert [event[0] for event in events] == ["answer", "render"]
    assert callback_router._callback_requires_manual_answer("approve_withdraw:1") is True
    assert callback_router._callback_requires_manual_answer("games_menu") is False


@pytest.mark.asyncio
async def test_membership_check_uses_cache_but_explicit_recheck_is_fresh(monkeypatch):
    payments = load_modules()["app.integrations.payments_core"]
    # _is_required_group_member short-circuits when no group is configured, so the
    # test has to set one instead of inheriting whatever .env this machine has.
    monkeypatch.setattr(payments, "REQUIRED_GROUP_ID", -1001234567890, raising=False)
    payments._required_group_membership_cache.clear()

    class FakeBot:
        def __init__(self):
            self.calls = 0

        async def get_chat_member(self, **_kwargs):
            self.calls += 1
            return SimpleNamespace(status="member", is_member=True)

    bot = FakeBot()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=456),
        get_bot=lambda: bot,
    )

    assert await payments._is_required_group_member(update) is True
    assert await payments._is_required_group_member(update) is True
    assert bot.calls == 1

    assert await payments._is_required_group_member(update, force_refresh=True) is True
    assert bot.calls == 2
