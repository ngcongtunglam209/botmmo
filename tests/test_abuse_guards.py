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


# --- Coupon: don cho giu suat, tra lai khi huy ------------------------------

def _one_use(store_menu, code="ONE"):
    store_menu.coupons.clear()
    store_menu.coupons[code] = {"discount": 10, "quantity": 1, "used": 0}
    return store_menu.coupons[code]


def test_two_pending_orders_cannot_share_a_one_use_coupon(modules):
    """Lo hong goc: `used` chi tang luc doi soat xong, nen N don QR cung dung
    chung mot ma quantity=1 va deu duoc giam gia."""
    store_menu = modules["app.services.store_menu"]
    saved = dict(store_menu.coupons)
    details = _one_use(store_menu)
    try:
        assert store_menu.reserve_coupon("ONE", "ICLD000001") is True
        assert store_menu.reserve_coupon("ONE", "ICLD000002") is False
        # `used` chua tang - moi chi giu cho.
        assert details["used"] == 0
        assert store_menu.coupon_effective_used(details) == 1
    finally:
        store_menu.coupons.clear()
        store_menu.coupons.update(saved)


def test_cancelling_a_pending_order_returns_the_coupon_slot(modules):
    store_menu = modules["app.services.store_menu"]
    saved = dict(store_menu.coupons)
    details = _one_use(store_menu)
    try:
        store_menu.reserve_coupon("ONE", "ICLD000001")
        assert store_menu.release_coupon("ONE", "ICLD000001") is True
        assert store_menu.coupon_effective_used(details) == 0
        # Tra lai hai lan la no-op, khong am.
        assert store_menu.release_coupon("ONE", "ICLD000001") is False
        assert store_menu.coupon_effective_used(details) == 0
        # Don khac gio dung duoc.
        assert store_menu.reserve_coupon("ONE", "ICLD000002") is True
    finally:
        store_menu.coupons.clear()
        store_menu.coupons.update(saved)


def test_paying_converts_the_reservation_into_a_real_use(modules):
    store_menu = modules["app.services.store_menu"]
    saved = dict(store_menu.coupons)
    details = _one_use(store_menu)
    try:
        store_menu.reserve_coupon("ONE", "ICLD000001")
        assert store_menu.redeem_coupon("ONE", "ICLD000001") is True
        assert details["used"] == 1
        assert details["reserved_by"] == []
        assert store_menu.coupon_effective_used(details) == 1
        # Da tieu het suat: don khac khong giu duoc nua.
        assert store_menu.reserve_coupon("ONE", "ICLD000002") is False
    finally:
        store_menu.coupons.clear()
        store_menu.coupons.update(saved)


def test_reserving_the_same_order_twice_takes_one_slot(modules):
    store_menu = modules["app.services.store_menu"]
    saved = dict(store_menu.coupons)
    store_menu.coupons.clear()
    store_menu.coupons["TWO"] = {"discount": 10, "quantity": 2, "used": 0}
    try:
        assert store_menu.reserve_coupon("TWO", "ICLD000001") is True
        assert store_menu.reserve_coupon("TWO", "ICLD000001") is True
        assert store_menu.coupon_effective_used(store_menu.coupons["TWO"]) == 1
    finally:
        store_menu.coupons.clear()
        store_menu.coupons.update(saved)


def test_pending_lifecycle_reserves_and_releases_without_per_site_patching(modules):
    """pending_set/pending_pop la choke point - moi duong huy deu di qua day."""
    notif = modules["app.services.notifications_async"]
    store_menu = modules["app.services.store_menu"]
    saved_coupons = dict(store_menu.coupons)
    saved_pending = dict(notif.pending_orders)
    details = _one_use(store_menu)
    notif.pending_orders.clear()
    try:
        order = {"user_id": 1, "coupon_code": "ONE", "status": "pending_payment"}
        asyncio.run(notif.pending_set("ICLD000001", order))
        assert store_menu.coupon_effective_used(details) == 1
        assert store_menu.reserve_coupon("ONE", "ICLD000002") is False

        # Huy / het han -> tra suat.
        asyncio.run(notif.pending_pop("ICLD000001"))
        assert store_menu.coupon_effective_used(details) == 0
        assert store_menu.reserve_coupon("ONE", "ICLD000002") is True
    finally:
        store_menu.coupons.clear()
        store_menu.coupons.update(saved_coupons)
        notif.pending_orders.clear()
        notif.pending_orders.update(saved_pending)


def test_paid_order_does_not_double_release_on_pop(modules):
    """Duong tra tien: redeem truoc, pop sau - pop khong duoc tra lai suat."""
    notif = modules["app.services.notifications_async"]
    store_menu = modules["app.services.store_menu"]
    saved_coupons = dict(store_menu.coupons)
    saved_pending = dict(notif.pending_orders)
    details = _one_use(store_menu)
    notif.pending_orders.clear()
    try:
        order = {"user_id": 1, "coupon_code": "ONE", "status": "pending_payment"}
        asyncio.run(notif.pending_set("ICLD000001", order))
        assert store_menu.redeem_coupon("ONE", "ICLD000001") is True
        asyncio.run(notif.pending_pop("ICLD000001"))
        # Van la 1 lan tieu that, khong bi pop tra ve 0.
        assert details["used"] == 1
        assert store_menu.coupon_effective_used(details) == 1
    finally:
        store_menu.coupons.clear()
        store_menu.coupons.update(saved_coupons)
        notif.pending_orders.clear()
        notif.pending_orders.update(saved_pending)


# --- Nhac thanh toan phai nam trong vong doi cua don ------------------------

def test_payment_reminder_fires_inside_the_order_lifetime(modules, monkeypatch):
    """Nguong nhac phai < ORDER_EXPIRATION_SECONDS.

    Truoc day nhac o 900s va tu huy o 3600s, trong khi don bi pop o 600s - ca hai
    nhanh khong bao gio chay toi nen job chay moi 3 phut ma khong lam gi.
    """
    bg = modules["app.jobs.admin_background"]
    import inspect
    source = inspect.getsource(bg.payment_reminder_job)
    assert "MAX_PENDING_SECONDS" not in source, "nhanh tu huy 1h trung chuc nang phai bo"
    assert "REMIND_AFTER_SECONDS = 5 * 60" in source
    assert bg.ORDER_EXPIRATION_SECONDS > 5 * 60


def test_payment_reminder_sends_once_then_forgets_dead_orders(modules, monkeypatch):
    bg = modules["app.jobs.admin_background"]
    saved_pending = dict(bg.pending_orders)
    saved_marks = set(bg._payment_reminded)
    sent = []

    class _Bot:
        async def send_message(self, user_id, text, **kwargs):
            sent.append((user_id, text))

    class _Ctx:
        bot = _Bot()

    bg.pending_orders.clear()
    bg._payment_reminded.clear()
    try:
        # Don tao cach day 6 phut -> qua nguong 5 phut, con trong han 10 phut.
        old = bg.time.time() - 6 * 60
        bg.pending_orders["ICLD000001"] = {
            "user_id": 42, "timestamp": old, "time": old,
            "amount": 50_000, "product_name": "P", "status": "pending_payment",
        }
        asyncio.run(bg.payment_reminder_job(_Ctx()))
        assert len(sent) == 1 and sent[0][0] == 42
        assert "NHẮC NHỞ THANH TOÁN" in sent[0][1]

        # Chay lai: khong spam lan hai.
        asyncio.run(bg.payment_reminder_job(_Ctx()))
        assert len(sent) == 1

        # Don roi hang cho -> quen danh dau, khong phinh mai.
        bg.pending_orders.clear()
        asyncio.run(bg.payment_reminder_job(_Ctx()))
        assert bg._payment_reminded == set()
    finally:
        bg.pending_orders.clear()
        bg.pending_orders.update(saved_pending)
        bg._payment_reminded.clear()
        bg._payment_reminded.update(saved_marks)


def test_payment_reminder_stays_quiet_before_the_threshold(modules):
    bg = modules["app.jobs.admin_background"]
    saved_pending = dict(bg.pending_orders)
    saved_marks = set(bg._payment_reminded)
    sent = []

    class _Bot:
        async def send_message(self, user_id, text, **kwargs):
            sent.append(user_id)

    class _Ctx:
        bot = _Bot()

    bg.pending_orders.clear()
    bg._payment_reminded.clear()
    try:
        young = bg.time.time() - 60  # moi 1 phut
        bg.pending_orders["ICLD000002"] = {
            "user_id": 7, "timestamp": young, "time": young, "amount": 1000,
        }
        asyncio.run(bg.payment_reminder_job(_Ctx()))
        assert sent == []
    finally:
        bg.pending_orders.clear()
        bg.pending_orders.update(saved_pending)
        bg._payment_reminded.clear()
        bg._payment_reminded.update(saved_marks)
