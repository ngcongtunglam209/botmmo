import pytest

from app.core.runtime_loader import load_modules


class _FakeBot:
    def __init__(self):
        self.edited_text = []
        self.edited_caption = []

    async def edit_message_text(self, **kwargs):
        self.edited_text.append(kwargs)

    async def edit_message_caption(self, **kwargs):
        self.edited_caption.append(kwargs)


class _FakeContext:
    def __init__(self, bot):
        self.bot = bot


def _install_expired_order(monkeypatch, monitor, details):
    async def fake_snapshot():
        return [("ORD1", details)]

    async def fake_pop(code, default=None):
        return details if code == "ORD1" else default

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot, raising=False)
    monkeypatch.setattr(monitor, "pending_pop", fake_pop, raising=False)
    monkeypatch.setattr(monitor, "ORDER_EXPIRATION_SECONDS", 600, raising=False)


@pytest.mark.parametrize("order_type", ["store_product", "manual_email"])
async def test_expired_order_without_balance_notifies_the_buyer(monkeypatch, order_type):
    """A pending order that used no balance must still get its expiry notice."""
    monitor = load_modules()["app.jobs.payment_monitor"]
    details = {
        "user_id": 4242,
        "time": 0,
        "balance_used": 0,
        "type": order_type,
        "message_id": 77,
        "message_kind": "text",
        "email": "buyer@example.com",
    }
    _install_expired_order(monkeypatch, monitor, details)

    bot = _FakeBot()
    changed = await monitor._cleanup_expired_pending_orders(_FakeContext(bot), 10_000)

    assert changed is True
    assert len(bot.edited_text) == 1
    assert bot.edited_text[0]["chat_id"] == 4242
    assert "HẾT HẠN" in bot.edited_text[0]["text"]


async def test_expired_order_with_balance_is_refunded(monkeypatch):
    monitor = load_modules()["app.jobs.payment_monitor"]
    details = {
        "user_id": 99,
        "time": 0,
        "balance_used": 50_000,
        "type": "store_product",
        "message_id": 5,
        "message_kind": "photo",
    }
    _install_expired_order(monkeypatch, monitor, details)
    monkeypatch.setattr(monitor, "user_data_db", {"99": {"balance": 10_000}}, raising=False)

    refunds = []
    monkeypatch.setattr(
        monitor,
        "db_update_balance",
        lambda user_id, new_balance: refunds.append((user_id, new_balance)),
        raising=False,
    )

    bot = _FakeBot()
    await monitor._cleanup_expired_pending_orders(_FakeContext(bot), 10_000)

    assert refunds == [(99, 60_000)]
    assert len(bot.edited_caption) == 1
    assert bot.edited_caption[0]["chat_id"] == 99
    assert "Đã hoàn lại" in bot.edited_caption[0]["caption"]
