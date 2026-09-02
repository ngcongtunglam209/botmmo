import time

import pytest
from telegram.error import BadRequest, NetworkError

from app.core.runtime_loader import load_modules


def _load():
    return load_modules()["app.integrations.payments_core"]


class FakeUser:
    def __init__(self, user_id=7943906246):
        self.id = user_id
        self.full_name = "Test User"
        self.username = "testuser"


class FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeBot:
    def __init__(self, error=None, status="member"):
        self.error = error
        self.status = status
        self.admin_messages = []

    async def get_chat_member(self, chat_id, user_id):
        if self.error is not None:
            raise self.error

        class Member:
            status = self.status
            is_member = True

        return Member()


class FakeUpdate:
    def __init__(self, bot, user_id=7943906246):
        self._bot = bot
        self.effective_user = FakeUser(user_id)
        self.message = FakeMessage()
        self.callback_query = None

    def get_bot(self):
        return self._bot


@pytest.fixture
def gate(monkeypatch):
    payments = _load()
    payments._required_group_membership_cache.clear()
    monkeypatch.setattr(payments, "REQUIRED_GROUP_ID", -1004396644933, raising=False)
    monkeypatch.setattr(payments, "SUPPORT_GROUP_LINK", "https://t.me/lamshop", raising=False)
    monkeypatch.setattr(payments, "ADMIN_USER_ID", 1, raising=False)
    monkeypatch.setattr(payments, "banned_users", set(), raising=False)
    # Khong dat 0.0: `_alert_required_group_broken` so sanh voi time.monotonic(),
    # ma tren runner CI vua khoi dong thi monotonic() chi vai giay - nho hon
    # REQUIRED_GROUP_ALERT_INTERVAL_SECONDS (900), nen alert bi throttle va test
    # do. Tren may dev monotonic() la uptime nhieu ngay nen khong ai thay.
    monkeypatch.setattr(
        payments,
        "_required_group_alert_at",
        time.monotonic() - payments.REQUIRED_GROUP_ALERT_INTERVAL_SECONDS - 1,
        raising=False,
    )
    return payments


async def test_a_misconfigured_group_does_not_lock_everyone_out(gate, monkeypatch):
    alerts = []

    async def fake_alert(bot, text, **kwargs):
        alerts.append(text)

    monkeypatch.setattr(gate, "safe_send_admin", fake_alert, raising=False)
    update = FakeUpdate(FakeBot(error=BadRequest("Chat not found")))

    blocked = await gate.check_if_banned(update)

    # REQUIRED_GROUP_ID pointing at a chat that does not exist (a topic id, say)
    # must not take the whole shop offline.
    assert blocked is False
    assert update.message.replies == []
    assert len(alerts) == 1
    assert "-1004396644933" in alerts[0]


async def test_a_network_blip_also_lets_the_customer_through(gate, monkeypatch):
    monkeypatch.setattr(gate, "safe_send_admin", lambda *a, **k: _noop(), raising=False)
    update = FakeUpdate(FakeBot(error=NetworkError("timed out")))

    assert await gate.check_if_banned(update) is False


async def _noop():
    return None


async def test_a_definite_non_member_is_still_blocked(gate, monkeypatch):
    update = FakeUpdate(FakeBot(status="left"))

    blocked = await gate.check_if_banned(update)

    # The gate still works when Telegram actually answers.
    assert blocked is True
    assert update.message.replies
    assert "nhóm" in update.message.replies[0].lower()


async def test_a_member_passes(gate):
    update = FakeUpdate(FakeBot(status="member"))

    assert await gate.check_if_banned(update) is False


async def test_the_admin_alert_is_throttled(gate, monkeypatch):
    alerts = []

    async def fake_alert(bot, text, **kwargs):
        alerts.append(text)

    monkeypatch.setattr(gate, "safe_send_admin", fake_alert, raising=False)

    for user_id in range(7943906246, 7943906256):
        await gate.check_if_banned(FakeUpdate(FakeBot(error=BadRequest("Chat not found")), user_id))

    # Ten customers hitting a broken gate must not mean ten identical DMs.
    assert len(alerts) == 1


async def test_a_banned_user_is_blocked_before_the_group_check(gate, monkeypatch):
    monkeypatch.setattr(gate, "banned_users", {7943906246}, raising=False)
    update = FakeUpdate(FakeBot(error=BadRequest("Chat not found")))

    assert await gate.check_if_banned(update) is True


async def test_no_required_group_means_no_check_at_all(gate, monkeypatch):
    monkeypatch.setattr(gate, "REQUIRED_GROUP_ID", 0, raising=False)

    def explode(*args, **kwargs):
        raise AssertionError("khong duoc goi Telegram khi chua bat cong ep vao nhom")

    update = FakeUpdate(FakeBot())
    update._bot.get_chat_member = explode

    assert await gate.check_if_banned(update) is False
