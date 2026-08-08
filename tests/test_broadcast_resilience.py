import pytest
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter

from app.core.runtime_loader import load_modules


def _io():
    return load_modules()["app.utils.telegram_io"]


class Bot:
    def __init__(self, errors=None):
        self.errors = dict(errors or {})
        self.delivered = []
        self.attempts = []

    async def send_message(self, chat_id, text, **kwargs):
        self.attempts.append(chat_id)
        error = self.errors.get(chat_id)
        if error is not None:
            if isinstance(error, list):
                raised = error.pop(0)
                if raised is not None:
                    raise raised
            else:
                raise error
        self.delivered.append(chat_id)


async def test_a_deleted_account_is_reported_not_raised():
    io = _io()
    bot = Bot({1: BadRequest("Chat not found")})

    # This is the exact error that killed the flash-sale task: BadRequest is a
    # TelegramError, which the loop's `except (ValueError, TypeError, ...)`
    # never caught.
    assert await io.broadcast_send_message(bot, 1, "hi") == "invalid"


async def test_a_user_who_blocked_the_bot_is_reported():
    io = _io()
    bot = Bot({1: Forbidden("bot was blocked by the user")})

    assert await io.broadcast_send_message(bot, 1, "hi") == "blocked"


async def test_other_telegram_errors_are_kept_for_a_retry():
    io = _io()
    bot = Bot({1: NetworkError("connection reset")})

    # A network blip is not proof the user is gone, so they keep their place on
    # the list.
    assert await io.broadcast_send_message(bot, 1, "hi") == "failed"


async def test_flood_control_sleeps_and_retries_once(monkeypatch):
    io = _io()
    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(io.asyncio, "sleep", fake_sleep, raising=False)
    bot = Bot({1: [RetryAfter(3), None]})

    assert await io.broadcast_send_message(bot, 1, "hi") == "ok"
    # Treating flood control as a failure would silently drop everyone from the
    # point Telegram starts throttling onwards.
    assert slept and slept[0] >= 3
    assert bot.attempts == [1, 1]


async def test_persistent_flood_control_gives_up_without_raising(monkeypatch):
    io = _io()

    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr(io.asyncio, "sleep", fake_sleep, raising=False)
    bot = Bot({1: [RetryAfter(3), RetryAfter(3)]})

    assert await io.broadcast_send_message(bot, 1, "hi") == "failed"


async def test_a_successful_send_reports_ok():
    io = _io()
    bot = Bot()

    assert await io.broadcast_send_message(bot, 1, "hi") == "ok"
    assert bot.delivered == [1]


async def test_one_bad_recipient_does_not_stop_the_rest():
    io = _io()
    bot = Bot({2: BadRequest("Chat not found"), 3: Forbidden("blocked")})
    results = {}

    for chat_id in (1, 2, 3, 4, 5):
        results[chat_id] = await io.broadcast_send_message(bot, chat_id, "hi")

    # The whole point: users 4 and 5 still get the message.
    assert bot.delivered == [1, 4, 5]
    assert results == {1: "ok", 2: "invalid", 3: "blocked", 4: "ok", 5: "ok"}


@pytest.mark.parametrize(
    "message",
    ["Chat not found", "user is deactivated", "PEER_ID_INVALID", "Bot was blocked by the user"],
)
async def test_every_gone_user_spelling_is_recognised(message):
    io = _io()
    bot = Bot({1: BadRequest(message)})

    # Telegram spells these inconsistently, underscores included.
    assert await io.broadcast_send_message(bot, 1, "hi") == "invalid"


async def test_a_malformed_message_is_not_mistaken_for_a_dead_user():
    io = _io()
    bot = Bot({1: BadRequest("Can't parse entities: unclosed tag")})

    # Marking the user gone would disable their broadcasts forever over a bug
    # in our own HTML.
    assert await io.broadcast_send_message(bot, 1, "hi") == "failed"
