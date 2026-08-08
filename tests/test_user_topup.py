"""Wallet top-up: code matching, crediting, and the no-withdraw invariant."""

import asyncio
import time

import pytest

from app.core.runtime_loader import load_modules


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text=None, **kwargs):
        self.messages.append((chat_id, text))
        return None


class FakeContext:
    def __init__(self):
        self.bot = FakeBot()
        self.user_data = {}


@pytest.fixture
def topup_env():
    modules = load_modules()
    topup = modules["app.handlers.user_topup"]
    db = modules["app.services.games_withdrawals_db"]

    users = {}
    pending = {}
    history = {}

    async def fake_save_data(*args, **kwargs):
        return None

    def fake_background_task(coro):
        coro.close()
        return None

    async def fake_send_admin(*args, **kwargs):
        return None

    for module in modules.values():
        namespace = module.__dict__
        if "user_data_db" in namespace:
            namespace["user_data_db"] = users
        if "pending_user_topups" in namespace:
            namespace["pending_user_topups"] = pending
        if "transaction_history" in namespace:
            namespace["transaction_history"] = history
        if "save_data" in namespace:
            namespace["save_data"] = fake_save_data
        if "create_background_task" in namespace:
            namespace["create_background_task"] = fake_background_task
        if "safe_send_admin" in namespace:
            namespace["safe_send_admin"] = fake_send_admin

    return topup, db, users, pending


def test_reference_is_found_in_transfer_description(topup_env):
    topup, _db, _users, _pending = topup_env
    assert topup.find_pending_user_topup_reference("CT DEN:123 NAPU9998877 GD") == "NAPU9998877"
    # Bank statements often strip spaces or lowercase the note.
    assert topup.find_pending_user_topup_reference("napu9998877") == "NAPU9998877"
    assert topup.find_pending_user_topup_reference("ICLD123456") is None


def test_credit_adds_balance_and_marks_it_non_withdrawable(topup_env):
    topup, _db, users, pending = topup_env
    code = "NAPU5551234"
    pending[code] = {"code": code, "user_id": 555, "amount": 100000, "time": time.time()}

    assert asyncio.run(topup.credit_user_topup(FakeContext(), code, 100000)) is True

    assert users["555"]["balance"] == 100000
    assert topup.get_user_topup_balance(555) == 100000
    assert topup.get_withdrawable_balance(555) == 0
    assert code not in pending


def test_spending_consumes_topup_before_reward_money(topup_env):
    topup, db, users, pending = topup_env
    code = "NAPU7770001"
    pending[code] = {"code": code, "user_id": 777, "amount": 50000, "time": time.time()}
    asyncio.run(topup.credit_user_topup(FakeContext(), code, 50000))
    # Reward money is withdrawable, top-up money is not.
    db.db_update_balance(777, 80000, reason="Lucky Wheel: +30000")
    assert topup.get_withdrawable_balance(777) == 30000

    db.db_update_balance(777, 50000, reason="Purchase: ChatGPT Plus x1")
    assert users["777"]["balance"] == 50000
    assert topup.get_user_topup_balance(777) == 20000
    assert topup.get_withdrawable_balance(777) == 30000


def test_underpaid_transfer_is_not_credited(topup_env):
    topup, _db, users, pending = topup_env
    code = "NAPU8880002"
    pending[code] = {"code": code, "user_id": 888, "amount": 100000, "time": time.time()}

    assert asyncio.run(topup.credit_user_topup(FakeContext(), code, 40000)) is True

    assert "888" not in users
    assert code not in pending


def test_unknown_code_is_reported_as_unhandled(topup_env):
    topup, _db, _users, _pending = topup_env
    assert asyncio.run(topup.credit_user_topup(FakeContext(), "NAPU404", 10000)) is False


def test_expired_requests_are_dropped(topup_env):
    topup, _db, _users, pending = topup_env
    now = time.time()
    pending["NAPU1110003"] = {"user_id": 111, "amount": 10000, "time": now}
    pending["NAPU1110004"] = {"user_id": 111, "amount": 10000, "time": now - 99999}

    assert topup.cleanup_expired_user_topups(now) is True
    assert "NAPU1110003" in pending
    assert "NAPU1110004" not in pending


def _payments():
    return load_modules()["app.integrations.payments_core"]


def test_topup_qr_uses_the_same_builder_as_checkout(topup_env, monkeypatch):
    topup, _db, _users, _pending = topup_env
    modules = load_modules()
    ui = modules["app.utils.ui_and_email"]

    # The two QR images used to come from different providers (img.vietqr.io for
    # top-ups, qr.sepay.vn for purchases), so the frame and logo did not match.
    assert topup.build_user_topup_qr_url("NAPU5551234", 100000) == ui.create_vietqr_link(100000, "NAPU5551234")
    assert "qr.sepay.vn" in topup.build_user_topup_qr_url("NAPU5551234", 100000)


def _set_display_rates(monkeypatch, *, vnd_per_usdt="26000", cny_per_usdt="7.2"):
    from decimal import Decimal

    payments = _payments()
    monkeypatch.setattr(payments, "_cached_live_usdt_rate", Decimal(vnd_per_usdt) if vnd_per_usdt else None, raising=False)
    monkeypatch.setattr(payments, "_cached_live_cny_rate", Decimal(cny_per_usdt) if cny_per_usdt else None, raising=False)
    return payments


def _set_lang(monkeypatch, lang):
    payments = _payments()
    monkeypatch.setattr(payments, "get_user_lang", lambda _user_id=None: lang, raising=False)


def test_each_language_sees_its_own_currency(monkeypatch):
    payments = _set_display_rates(monkeypatch)

    _set_lang(monkeypatch, "vi")
    assert payments.format_money(260000, 1) == "260,000 VNĐ"

    _set_lang(monkeypatch, "en")
    assert payments.format_money(260000, 1) == "$10.00"

    # Chinese shows CNY with the USD figure alongside, because the shop quotes
    # crypto in USDT and customers cross-check against it.
    _set_lang(monkeypatch, "zh")
    assert payments.format_money(260000, 1) == "¥72.00 ($10.00)"


def test_amounts_fall_back_to_vnd_when_no_rate_is_known(monkeypatch):
    from decimal import Decimal

    payments = _set_display_rates(monkeypatch, vnd_per_usdt="", cny_per_usdt="")
    monkeypatch.setattr(payments, "USDT_RATE_VND_PER_USDT", Decimal("0"), raising=False)
    monkeypatch.setattr(payments, "USDT_RATE_CNY_PER_USDT", Decimal("0"), raising=False)

    # "$0.00" would be worse than the honest VND figure.
    _set_lang(monkeypatch, "en")
    assert payments.format_money(260000, 1) == "260,000 VNĐ"
    assert payments.parse_money_to_vnd("260000", 1) == 260000


def test_the_amount_is_read_back_in_the_currency_it_was_shown_in(monkeypatch):
    payments = _set_display_rates(monkeypatch)

    _set_lang(monkeypatch, "vi")
    assert payments.parse_money_to_vnd("100.000", 1) == 100000
    assert payments.parse_money_to_vnd("100,000", 1) == 100000

    _set_lang(monkeypatch, "en")
    # An English customer typing "10" means ten dollars, not ten dong.
    assert payments.parse_money_to_vnd("10", 1) == 260000
    assert payments.parse_money_to_vnd("$12.50", 1) == 325000

    _set_lang(monkeypatch, "zh")
    assert payments.parse_money_to_vnd("72", 1) == 260000

    assert payments.parse_money_to_vnd("abc", 1) is None
    assert payments.parse_money_to_vnd("", 1) is None


def test_binance_is_offered_only_once_it_is_configured(topup_env, monkeypatch):
    topup, _db, _users, _pending = topup_env

    monkeypatch.setattr(topup, "is_bank_transfer_enabled", lambda: True, raising=False)
    monkeypatch.setattr(topup, "is_binance_pay_enabled", lambda: False, raising=False)
    assert topup.available_topup_methods() == ["bank"]

    monkeypatch.setattr(topup, "is_binance_pay_enabled", lambda: True, raising=False)
    assert topup.available_topup_methods() == ["bank", "binance"]

    # No gateway configured at all still leaves the bank QR reachable rather
    # than dead-ending the top-up flow.
    monkeypatch.setattr(topup, "is_bank_transfer_enabled", lambda: False, raising=False)
    monkeypatch.setattr(topup, "is_binance_pay_enabled", lambda: False, raising=False)
    assert topup.available_topup_methods() == ["bank"]


class FakeUser:
    id = 555
    full_name = "Test User"
    username = "tester"


class FakeChat:
    id = 555


class FakeUpdate:
    effective_user = FakeUser()
    effective_chat = FakeChat()
    callback_query = None
    message = None


class PhotoBot(FakeBot):
    def __init__(self):
        super().__init__()
        self.photos = []

    async def send_photo(self, chat_id, photo=None, caption=None, **kwargs):
        self.photos.append({"chat_id": chat_id, "photo": photo, "caption": caption, "kwargs": kwargs})
        return None


class PhotoContext(FakeContext):
    def __init__(self):
        super().__init__()
        self.bot = PhotoBot()


def test_a_binance_topup_stores_what_reconciliation_matches_on(topup_env, monkeypatch):
    topup, _db, _users, pending = topup_env

    async def fake_quote(order_code, amount_vnd):
        return {"binance_pay_id": "964569042", "amount_text": "3.8500", "rate": 26000, "amount": 3.85}

    monkeypatch.setattr(topup, "is_binance_pay_enabled", lambda: True, raising=False)
    monkeypatch.setattr(topup, "create_binance_pay_order", fake_quote, raising=False)
    monkeypatch.setattr(topup, "binance_pay_qr_photo", lambda: "https://qr.example/binance", raising=False)

    context = PhotoContext()
    assert asyncio.run(topup.create_user_topup_request(FakeUpdate(), context, 100000, method="binance")) is True

    code, details = topup.get_user_pending_topup(555)
    assert code in pending
    assert details["provider"] == "binance_pay"
    # The exact string shown to the customer is the only handle the history feed
    # gives us to match this top-up, so it has to be stored verbatim.
    assert details["binance_pay_amount"] == "3.8500"
    assert details["amount"] == 100000
    assert "3.8500" in context.bot.photos[0]["caption"]


def test_a_binance_topup_is_refused_when_the_gateway_is_off(topup_env, monkeypatch):
    topup, _db, _users, pending = topup_env

    monkeypatch.setattr(topup, "is_binance_pay_enabled", lambda: False, raising=False)

    context = PhotoContext()
    assert asyncio.run(topup.create_user_topup_request(FakeUpdate(), context, 100000, method="binance")) is False
    assert pending == {}
