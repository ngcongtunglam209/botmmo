"""Toan tien hoan khi giao thieu hang, va cho giu so tien Binance Pay."""

import asyncio
from decimal import Decimal

import pytest

from app.core.runtime_loader import load_modules


@pytest.fixture
def modules():
    return load_modules()


# --- consume_local_stock_items: list rong khong duoc gia lam "co hang" ------

def _stock_product(rows):
    return {"name": "P", "price": 100_000, "stock": list(rows)}


def _consume(guard, monkeypatch, product, qty, order_state=None):
    monkeypatch.setattr(guard, "products", {"p1": product}, raising=False)
    monkeypatch.setattr(guard, "order_history", [], raising=False)

    async def no_save(*args, **kwargs):
        return None

    monkeypatch.setattr(guard, "save_critical_tables", no_save, raising=False)
    return asyncio.run(
        guard.consume_local_stock_items("p1", qty, order_state=order_state, source="test")
    )


def test_blank_stock_rows_report_out_of_stock_instead_of_empty_items(modules, monkeypatch):
    """stock=['',''] dem la 2 dong nhung khong chon duoc dong nao.

    Truoc day tra items=[] ; caller chi kiem tra `is None` nen tru du tien roi
    giao 0 san pham.
    """
    guard = modules["app.services.local_stock_guard"]
    result = _consume(guard, monkeypatch, _stock_product(["", "   "]), 2)
    assert result["items"] is None
    assert result["actual_delivered"] == 0


def test_stock_is_not_consumed_when_nothing_can_be_reserved(modules, monkeypatch):
    guard = modules["app.services.local_stock_guard"]
    product = _stock_product(["", "   "])
    _consume(guard, monkeypatch, product, 2)
    # Khong dong nao bi lay ra khoi kho.
    assert len(product["stock"]) == 2


def test_partial_reservation_reports_the_true_shortfall(modules, monkeypatch):
    """stock=[A, A] qty=2 -> giao duoc 1, thieu 1; con so thieu phai bao dung."""
    guard = modules["app.services.local_stock_guard"]
    result = _consume(guard, monkeypatch, _stock_product(["acc-A", "acc-A"]), 2)
    assert result["items"] == ["acc-A"]
    assert result["actual_delivered"] == 1
    assert result["refunded_qty"] == 1


def test_a_full_reservation_is_unchanged(modules, monkeypatch):
    guard = modules["app.services.local_stock_guard"]
    product = _stock_product(["acc-A", "acc-B"])
    result = _consume(guard, monkeypatch, product, 2)
    assert result["items"] == ["acc-A", "acc-B"]
    assert result["refunded_qty"] == 0
    assert product["stock"] == []


# --- M1: hoan tien theo gia da giam, khong theo gia niem yet ---------------

class _FakeUser:
    def __init__(self, user_id):
        self.id = user_id
        self.full_name = "Test"
        self.username = "test"


class _FakeMessage:
    chat_id = 1

    async def reply_text(self, *args, **kwargs):
        return None

    async def delete(self):
        return None


class _FakeQuery:
    def __init__(self, data, user_id):
        self.data = data
        self.from_user = _FakeUser(user_id)
        self.message = _FakeMessage()

    async def edit_message_text(self, *args, **kwargs):
        return _FakeMessage()

    async def answer(self, *args, **kwargs):
        return None


class _FakeUpdate:
    def __init__(self, query):
        self.callback_query = query
        self.effective_user = query.from_user


class _FakeContext:
    def __init__(self):
        self.user_data = {}
        self.bot = None


def test_short_delivery_refunds_at_the_discounted_price(modules, monkeypatch):
    """Gia niem yet 100k, giam con 50k, mua 2, chi giao duoc 1.

    Da thu 100k (50k x 2), thieu 1 -> hoan 50k -> thu thuc te 50k.
    Truoc day hoan theo gia niem yet 100k, thanh ra thu -0k va CONG them tien
    vao vi khach.
    """
    store = modules["app.handlers.store_callback"]
    charged = {}

    monkeypatch.setattr(store, "products", {"p1": {"name": "P", "price": 100_000, "stock": ["a", "a"]}}, raising=False)
    monkeypatch.setattr(store, "get_best_discount", lambda *a, **k: (50_000, "flash_sale", None), raising=False)
    monkeypatch.setattr(store, "get_active_store_coupon_context", lambda *a, **k: ("", 0), raising=False)
    monkeypatch.setattr(store, "db_get_user", lambda uid: {"balance": 500_000}, raising=False)
    monkeypatch.setattr(store, "get_local_stock_available_count", lambda p: 2, raising=False)

    async def fake_consume(*args, **kwargs):
        return {"items": ["acc-A"], "actual_delivered": 1, "refunded_qty": 1, "available": 1, "reused": False}

    def fake_update_balance(user_id, new_balance, reason=""):
        charged["new_balance"] = new_balance
        charged["reason"] = reason

    async def fake_code(*args, **kwargs):
        return "PROD1234"

    async def fake_deliver(*args, **kwargs):
        return {"delivered": True, "method": "txt", "sent_items": 1, "errors": []}

    async def no_save(*args, **kwargs):
        return None

    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(store, "consume_local_stock_items", fake_consume, raising=False)
    monkeypatch.setattr(store, "db_update_balance", fake_update_balance, raising=False)
    monkeypatch.setattr(store, "generate_unique_order_code", fake_code, raising=False)
    monkeypatch.setattr(store, "deliver_items_as_txt", fake_deliver, raising=False)
    monkeypatch.setattr(store, "db_add_order", lambda order: charged.setdefault("order", order), raising=False)
    monkeypatch.setattr(store, "save_data", no_save, raising=False)
    monkeypatch.setattr(store, "safe_answer", noop, raising=False)
    monkeypatch.setattr(store, "safe_edit_message", noop, raising=False)
    monkeypatch.setattr(store, "safe_send_message", noop, raising=False)
    monkeypatch.setattr(store, "safe_send_admin", noop, raising=False)
    monkeypatch.setattr(store, "record_promo_cost", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(store, "clear_store_coupon_context", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(store, "process_referral_commission", noop, raising=False)
    monkeypatch.setattr(store, "send_live_order_notification", noop, raising=False)
    monkeypatch.setattr(store, "broadcast_out_of_stock", noop, raising=False)
    monkeypatch.setattr(store, "create_success_menu", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(store, "calculate_warranty_expiry", lambda *a, **k: 0, raising=False)

    query = _FakeQuery("pay_prod_bal_p1_2", 42)
    asyncio.run(store.handle_store_callback(_FakeUpdate(query), _FakeContext()))

    # 500_000 - 50_000 (chi thu phan thuc giao), KHONG phai 500_000 + 100_000.
    assert charged["new_balance"] == 450_000


# --- Binance Pay: so tien cua don het han khong duoc cap lai ngay -----------

def test_expired_order_amount_stays_reserved(modules, monkeypatch):
    binance = modules["app.integrations.binancepay_api"]
    monkeypatch.setattr(binance, "BINANCE_PAY_AMOUNT_DECIMALS", 4, raising=False)
    monkeypatch.setattr(binance, "USDT_DISPLAY_DECIMALS", 2, raising=False)
    monkeypatch.setattr(binance, "ORDER_EXPIRATION_SECONDS", 600, raising=False)
    monkeypatch.setattr(binance, "BINANCE_PAY_MATCH_LEEWAY_SECONDS", 120, raising=False)
    monkeypatch.setattr(binance, "_binance_pay_amount_cooldown", {}, raising=False)
    monkeypatch.setattr(binance, "pending_orders", {}, raising=False)
    monkeypatch.setattr(binance, "pending_user_topups", {}, raising=False)

    _amount, first = binance.allocate_binance_pay_amount(Decimal("1.54"))
    # Don het han bi pop khoi pending_orders -> nguon "dang cho" rong tro lai.
    assert binance.pending_orders == {}
    _amount, second = binance.allocate_binance_pay_amount(Decimal("1.54"))
    assert second != first, "so tien cua don vua het han khong duoc cap lai ngay"


def test_reserved_amount_is_released_after_the_cooldown(modules, monkeypatch):
    binance = modules["app.integrations.binancepay_api"]
    monkeypatch.setattr(binance, "BINANCE_PAY_AMOUNT_DECIMALS", 4, raising=False)
    monkeypatch.setattr(binance, "USDT_DISPLAY_DECIMALS", 2, raising=False)
    monkeypatch.setattr(binance, "ORDER_EXPIRATION_SECONDS", 600, raising=False)
    monkeypatch.setattr(binance, "BINANCE_PAY_MATCH_LEEWAY_SECONDS", 120, raising=False)
    monkeypatch.setattr(binance, "_binance_pay_amount_cooldown", {}, raising=False)
    monkeypatch.setattr(binance, "pending_orders", {}, raising=False)
    monkeypatch.setattr(binance, "pending_user_topups", {}, raising=False)

    _amount, first = binance.allocate_binance_pay_amount(Decimal("1.54"))
    assert binance.binance_pay_cooldown_seconds() == 600 + 2 * 120
    # Het thoi gian giu cho -> duoc cap lai.
    binance._binance_pay_amount_cooldown[first] = 0.0
    _amount, again = binance.allocate_binance_pay_amount(Decimal("1.54"))
    assert again == first
