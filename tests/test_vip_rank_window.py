"""Hạng VIP tính theo cửa sổ trượt, và giảm giá theo hạng thật sự vào giá bán."""

import time

import pytest

from app.core.runtime_loader import load_modules

DAY = 86400


@pytest.fixture
def rank_env():
    modules = load_modules()
    stats = modules["app.services.referrals_stats"]
    jobs = modules["app.jobs.admin_background"]

    # Loader chép symbol vào globals của mọi module, nên user_order_index phải
    # được vá theo từng module và trả lại sau, kẻo test sau đọc nhầm dữ liệu.
    indexes = [
        module.__dict__["user_order_index"]
        for module in modules.values()
        if "user_order_index" in module.__dict__
    ]
    saved = [dict(index) for index in indexes]

    def seed(user_id, orders):
        """orders: danh sách (số tiền, số ngày trước)."""
        rows = [
            {
                "order_code": f"{user_id}-{i}",
                "user_id": user_id,
                "amount": amount,
                "status": "completed",
                "timestamp": time.time() - age_days * DAY,
            }
            for i, (amount, age_days) in enumerate(orders)
        ]
        for index in indexes:
            index[str(user_id)] = rows

    yield stats, jobs, seed

    for index, original in zip(indexes, saved):
        index.clear()
        index.update(original)


def test_orders_older_than_the_window_do_not_count(rank_env):
    stats, jobs, seed = rank_env
    window_days = stats.VIP_RANK_WINDOW_DAYS
    seed(9001, [(9_000_000, window_days + 10), (9_000_000, window_days + 60)])

    rank = jobs.get_user_vip_rank(9001)

    # Lifetime vẫn 18 triệu nhưng không đơn nào nằm trong cửa sổ xét hạng.
    assert rank["lifetime_spent"] == 18_000_000
    assert rank["total_spent"] == 0
    assert rank["discount_percent"] == 0
    assert stats.rank_tier_key(rank["rank"]) == "bronze"


def test_rank_and_discount_follow_spending_inside_the_window(rank_env):
    stats, jobs, seed = rank_env
    seed(9002, [(9_000_000, 5), (9_000_000, 40)])

    rank = jobs.get_user_vip_rank(9002)

    assert rank["total_spent"] == 18_000_000
    assert stats.rank_tier_key(rank["rank"]) == "diamond"
    assert rank["discount_percent"] == 8
    assert stats.get_rank_discount(9002) == 8


def test_drop_timestamp_points_at_the_order_leaving_the_window(rank_env):
    stats, jobs, seed = rank_env
    window_days = stats.VIP_RANK_WINDOW_DAYS
    oldest_age = window_days - 10
    seed(9003, [(4_000_000, oldest_age), (4_000_000, 1)])

    rank = jobs.get_user_vip_rank(9003)

    # Bỏ đơn cũ đi thì còn 4 triệu, dưới ngưỡng Kim Cương, nên hạng tụt đúng
    # lúc đơn đó rời cửa sổ — khoảng 10 ngày nữa.
    assert stats.rank_tier_key(rank["rank"]) == "diamond"
    days_left = (rank["drop_timestamp"] - time.time()) / DAY
    assert 9 < days_left < 11


def test_lowest_rank_never_reports_a_drop_date(rank_env):
    _stats, jobs, seed = rank_env
    seed(9004, [])

    rank = jobs.get_user_vip_rank(9004)

    assert rank["total_spent"] == 0
    assert rank["drop_timestamp"] == 0


def test_vip_discount_reaches_the_price_and_never_stacks(rank_env):
    stats, _jobs, seed = rank_env
    seed(9005, [(25_000_000, 2)])

    price, kind, info = stats.get_best_discount(9005, "khong-co-san-pham", 100_000)

    assert kind == "vip"
    assert info["discount_percent"] == 10
    assert price == 90_000
