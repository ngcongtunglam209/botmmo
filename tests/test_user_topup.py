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
