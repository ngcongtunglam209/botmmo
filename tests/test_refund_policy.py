from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.core.runtime_loader import load_modules


def test_bank_info_validation():
    withdrawals = load_modules()["app.services.games_withdrawals_db"]

    normalized, error = withdrawals.normalize_bank_info("MB Bank - 0123456789 - NGUYEN VAN A")
    assert error is None
    assert normalized == "MB Bank - 0123456789 - NGUYEN VAN A"

    for invalid in (
        "MB Bank - abc123 - NGUYEN VAN A",
        "MB Bank - 12345 - NGUYEN VAN A",
        "<b>MB</b> - 0123456789 - NGUYEN VAN A",
        "MB Bank - 0123456789 - <b>NGUYEN</b>",
    ):
        normalized, error = withdrawals.normalize_bank_info(invalid)
        assert normalized is None
        assert error


def test_prorated_refund_uses_whole_unused_days(monkeypatch):
    refund = load_modules()["app.services.admin_refund"]
    monkeypatch.setattr(refund, "_resolve_order_duration_days", lambda _order: 30)
    now_ts = 30 * 86400
    order = {"amount": 300_000, "timestamp": now_ts - (5 * 86400 + 1)}

    quote = refund._calculate_order_refund(order, prorated=True, now_ts=now_ts)

    assert quote == {
        "amount": 240_000,
        "reason": "Còn 24/30 ngày chưa sử dụng",
        "duration_days": 30,
        "used_days": 6,
        "unused_days": 24,
    }


def test_full_refund_is_not_prorated():
    refund = load_modules()["app.services.admin_refund"]

    quote = refund._calculate_order_refund({"amount": 199_999}, prorated=False)

    assert quote["amount"] == 199_999
    assert quote["reason"] == "100%"


@pytest.mark.asyncio
async def test_eligible_refund_creates_manual_bank_request(monkeypatch):
    refund = load_modules()["app.services.admin_refund"]
    order = {
        "order_code": "PROD123",
        "user_id": 42,
        "refunded_at": 1,
        "refund_amount": 250_000,
        "refund_target": "Ví Bot",
    }
    users = {"42": {"balance": 300_000}}
    requests = {}
    replies = []
    notified = []

    class Message:
        text = "MB Bank - 0123456789 - NGUYEN VAN A"

        async def reply_text(self, text, **kwargs):
            replies.append((text, kwargs))

    async def fake_save(*_args, **_kwargs):
        return None

    async def fake_notify(_context, request_id):
        notified.append(request_id)

    async def fake_refund_lock(_code):
        return asyncio.Lock()

    def fake_balance_update(user_id, new_balance, **_kwargs):
        users[str(user_id)]["balance"] = new_balance

    monkeypatch.setattr(refund, "order_index", {"PROD123": order})
    monkeypatch.setattr(refund, "user_data_db", users)
    monkeypatch.setattr(refund, "withdrawal_requests", requests)
    monkeypatch.setattr(refund, "BANK_REFUND_MIN_AMOUNT", 200_000)
    monkeypatch.setattr(refund, "get_refund_lock", fake_refund_lock)
    monkeypatch.setattr(refund, "db_update_balance", fake_balance_update)
    monkeypatch.setattr(refund, "save_data", fake_save)
    monkeypatch.setattr(refund, "notify_admin_withdrawal", fake_notify)

    context = SimpleNamespace(
        user_data={"state": "awaiting_refund_bank_info", "refund_bank_order_code": "PROD123"}
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=42, full_name="Customer", username="customer"),
        message=Message(),
    )

    await refund.handle_refund_bank_info_input(update, context)

    assert users["42"]["balance"] == 50_000
    assert len(requests) == 1
    request_id, request = next(iter(requests.items()))
    assert request["source"] == "order_refund"
    assert request["order_code"] == "PROD123"
    assert request["amount"] == 250_000
    assert order["bank_refund_request_id"] == request_id
    assert order["bank_refund_status"] == "pending"
    assert notified == [request_id]
    assert context.user_data == {}
    assert "250,000 VNĐ" in replies[-1][0]


@pytest.mark.asyncio
async def test_withdrawal_decision_is_processed_exactly_once(monkeypatch):
    withdrawals = load_modules()["app.services.admin_withdrawals"]
    request_id = "RF_RACE_TEST"
    requests = {
        request_id: {
            "user_id": 42,
            "amount": 250_000,
            "bank_info": "MB Bank - 0123456789 - NGUYEN VAN A",
            "status": "pending",
        }
    }
    users = {"42": {"balance": 0}}

    async def fake_save(*_args, **_kwargs):
        await asyncio.sleep(0)

    async def fake_edit(*_args, **_kwargs):
        return None

    def fake_balance_update(user_id, new_balance, **_kwargs):
        users[str(user_id)]["balance"] = new_balance

    class Bot:
        async def send_message(self, *_args, **_kwargs):
            return None

    query = SimpleNamespace(message=SimpleNamespace(text_html="request", text="request"))
    context = SimpleNamespace(bot=Bot())
    monkeypatch.setattr(withdrawals, "withdrawal_requests", requests)
    monkeypatch.setattr(withdrawals, "user_data_db", users)
    monkeypatch.setattr(withdrawals, "order_index", {})
    monkeypatch.setattr(withdrawals, "save_data", fake_save)
    monkeypatch.setattr(withdrawals, "safe_edit_message", fake_edit)
    monkeypatch.setattr(withdrawals, "db_update_balance", fake_balance_update)

    await asyncio.gather(
        withdrawals.handle_withdrawal_action(
            query, context, f"approve_withdraw:{request_id}", 1
        ),
        withdrawals.handle_withdrawal_action(
            query, context, f"reject_withdraw:{request_id}", 1
        ),
    )

    final_status = requests[request_id]["status"]
    assert final_status in {"approved", "rejected"}
    assert users["42"]["balance"] == (250_000 if final_status == "rejected" else 0)


@pytest.mark.asyncio
async def test_large_error_refund_is_audited_and_offers_bank_option(monkeypatch):
    notifications = load_modules()["app.services.notifications_async"]
    orders = []
    index = {}
    saved = []
    sent = []

    def fake_add_order(order, schedule_save=True):
        orders.append(order)
        index[order["order_code"]] = order

    async def fake_save(*_args, **_kwargs):
        saved.append(True)

    class Bot:
        async def send_message(self, **kwargs):
            sent.append(kwargs)

    monkeypatch.setattr(notifications, "order_index", index)
    monkeypatch.setattr(notifications, "db_add_order", fake_add_order)
    monkeypatch.setattr(notifications, "save_data", fake_save)
    monkeypatch.setattr(notifications, "BANK_REFUND_MIN_AMOUNT", 200_000)

    record = await notifications.record_wallet_refund(
        SimpleNamespace(bot=Bot()),
        order_code="prod123",
        user_id=42,
        amount=250_000,
        product_name="Capcut",
        reason="Supplier failed",
    )

    assert record["refund_amount"] == 250_000
    assert record["refund_target"] == "Ví Bot"
    assert sent[0]["reply_markup"].inline_keyboard[0][0].callback_data == "refund_bank:PROD123"
    assert saved
