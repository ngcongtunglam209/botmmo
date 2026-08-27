"""Cac cho khach tu khai thac duoc: coupon, phan thuong dice, huy don nguoi khac."""

import asyncio

import pytest

from app.core.runtime_loader import load_modules


@pytest.fixture
def modules():
    return load_modules()


# --- Coupon: soat lai luc tieu ma, khong chi luc ap ma ----------------------

def test_one_use_coupon_cannot_be_redeemed_twice(modules):
    store_menu = modules["app.services.store_menu"]
    saved = dict(store_menu.coupons)
    store_menu.coupons.clear()
    store_menu.coupons["ONE"] = {"discount": 10, "quantity": 1, "used": 0}
    try:
        assert store_menu.redeem_coupon("ONE") is True
        assert store_menu.coupons["ONE"]["used"] == 1
        # Lan hai phai bi tu choi va KHONG duoc tang tiep.
        assert store_menu.redeem_coupon("ONE") is False
        assert store_menu.coupons["ONE"]["used"] == 1
    finally:
        store_menu.coupons.clear()
        store_menu.coupons.update(saved)


def test_unlimited_and_expired_coupons(modules):
    store_menu = modules["app.services.store_menu"]
    saved = dict(store_menu.coupons)
    store_menu.coupons.clear()
    store_menu.coupons.update({
        "INF": {"discount": 10, "quantity": "∞", "used": 999},
        "OLD": {"discount": 10, "quantity": 5, "used": 0, "expires": "01-01-2020"},
        "BADDATE": {"discount": 10, "quantity": 5, "used": 0, "expires": "khong-phai-ngay"},
    })
    try:
        assert store_menu.redeem_coupon("INF") is True          # vo han van chay
        assert store_menu.redeem_coupon("OLD") is False         # het han
        assert store_menu.coupons["OLD"]["used"] == 0
        assert store_menu.redeem_coupon("BADDATE") is True      # ngay hong -> khong chan
        assert store_menu.redeem_coupon("KHONGTONTAI") is False
        assert store_menu.redeem_coupon("") is False
        assert store_menu.redeem_coupon(None) is False
    finally:
        store_menu.coupons.clear()
        store_menu.coupons.update(saved)


def test_coupon_lookup_is_case_insensitive(modules):
    store_menu = modules["app.services.store_menu"]
    saved = dict(store_menu.coupons)
    store_menu.coupons.clear()
    store_menu.coupons["SALE20"] = {"discount": 20, "quantity": 2, "used": 0}
    try:
        assert store_menu.redeem_coupon("  sale20  ") is True
        assert store_menu.coupons["SALE20"]["used"] == 1
    finally:
        store_menu.coupons.clear()
        store_menu.coupons.update(saved)


# --- Dice: callback_data khong duoc quyet dinh phan thuong ------------------

def test_dice_prize_must_be_one_of_the_offered_ids(modules):
    games = modules["app.handlers.callback_games"]
    saved_dice = dict(games.dice_game_data)
    saved_products = dict(games.products)
    games.dice_game_data.clear()
    games.products.clear()
    games.products.update({
        "cheap": {"name": "Cheap", "price": 10_000, "stock": ["a"]},
        "expensive": {"name": "Expensive", "price": 500_000, "stock": ["b"]},
    })
    try:
        games.dice_game_data["prizes_7"] = ["cheap"]
        assert games._dice_prize_is_offered(7, "cheap") is True
        # Doi callback_data sang hang dat tien -> phai bi chan.
        assert games._dice_prize_is_offered(7, "expensive") is False
        assert games._dice_prize_is_offered(7, "khongtontai") is False
    finally:
        games.dice_game_data.clear()
        games.dice_game_data.update(saved_dice)
        games.products.clear()
        games.products.update(saved_products)


def test_dice_prize_without_offer_record_falls_back_to_the_offer_filter(modules):
    """Nguoi thang tu truoc ban va: van phai ap lai bo loc gia + requires_gmail."""
    games = modules["app.handlers.callback_games"]
    saved_dice = dict(games.dice_game_data)
    saved_products = dict(games.products)
    games.dice_game_data.clear()
    games.products.clear()
    cap = games.DICE_PRIZE_MAX_PRICE
    games.products.update({
        "ok": {"name": "Ok", "price": cap, "stock": ["a"]},
        "toopricey": {"name": "Pricey", "price": cap + 1, "stock": ["b"]},
        "manual": {"name": "Manual", "price": 1, "stock": ["c"], "requires_gmail": True},
        "nostock": {"name": "Empty", "price": 1, "stock": []},
    })
    try:
        assert games._dice_prize_is_offered(7, "ok") is True
        assert games._dice_prize_is_offered(7, "toopricey") is False
        assert games._dice_prize_is_offered(7, "manual") is False
        assert games._dice_prize_is_offered(7, "nostock") is False
    finally:
        games.dice_game_data.clear()
        games.dice_game_data.update(saved_dice)
        games.products.clear()
        games.products.update(saved_products)


def test_clearing_dice_winner_also_clears_the_offer_record(modules):
    games = modules["app.handlers.callback_games"]
    saved = dict(games.dice_game_data)
    games.dice_game_data.clear()
    try:
        games.dice_game_data["winner_7"] = 123.0
        games.dice_game_data["prizes_7"] = ["cheap"]
        games._clear_dice_winner(7)
        assert "winner_7" not in games.dice_game_data
        assert "prizes_7" not in games.dice_game_data
    finally:
        games.dice_game_data.clear()
        games.dice_game_data.update(saved)


# --- cancel_order: chi chu don (hoac admin) moi huy duoc --------------------

class _FakeUser:
    def __init__(self, user_id):
        self.id = user_id


class _FakeQuery:
    def __init__(self, user_id):
        self.from_user = _FakeUser(user_id)
        self.answers = []
        self.message = None


def test_cancel_order_rejects_a_stranger(modules, monkeypatch):
    svc = modules["app.services.admin_orders"]
    saved = dict(svc.pending_orders)
    svc.pending_orders.clear()
    svc.pending_orders["ICLD111111"] = {"user_id": 111, "amount": 50_000, "balance_used": 20_000}

    popped = []

    async def fake_pop(code):
        popped.append(code)
        return svc.pending_orders.pop(code, None)

    async def fake_answer(query, text=None, show_alert=False):
        query.answers.append(text)

    monkeypatch.setattr(svc, "pending_pop", fake_pop)
    monkeypatch.setattr(svc, "safe_answer", fake_answer)
    try:
        query = _FakeQuery(999)  # khong phai chu don
        asyncio.run(svc.handle_cancel_order_payment(query, None, "cancel_order:ICLD111111"))
        # Don van con nguyen, chua he goi pending_pop.
        assert "ICLD111111" in svc.pending_orders
        assert popped == []
        assert query.answers and "không còn ở trạng thái chờ" in query.answers[0]
    finally:
        svc.pending_orders.clear()
        svc.pending_orders.update(saved)
