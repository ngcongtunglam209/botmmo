import pytest

from app.core.runtime_loader import load_modules


class FakeBot:
    username = "lamshopbot"

    def __init__(self, error=None):
        self.calls = []
        self.error = error

    async def send_message(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return None


class FakeContext:
    def __init__(self, bot):
        self.bot = bot


def _load():
    modules = load_modules()
    return modules["app.services.notifications_async"]


def test_topic_kwargs_only_set_when_a_topic_is_configured():
    notif = _load()

    # A plain channel, and a forum group's General topic, both take no thread id.
    # Telegram rejects message_thread_id=0 outright, so it must be absent.
    assert notif.topic_kwargs(0) == {}
    assert notif.topic_kwargs(None) == {}
    assert notif.topic_kwargs("") == {}
    assert notif.topic_kwargs("not a number") == {}
    assert notif.topic_kwargs(-5) == {}

    assert notif.topic_kwargs(580) == {"message_thread_id": 580}
    assert notif.topic_kwargs("580") == {"message_thread_id": 580}


async def test_live_order_posts_into_the_configured_topic(monkeypatch):
    notif = _load()
    monkeypatch.setattr(notif, "LIVE_ORDERS_CHANNEL_ID", -1004396644933, raising=False)
    monkeypatch.setattr(notif, "LIVE_ORDERS_TOPIC_ID", 580, raising=False)
    bot = FakeBot()

    await notif.send_live_order_notification(
        FakeContext(bot), "Nguyen Van An", 39900, product_name="ChatGPT Plus", order_code="ICLD123456"
    )

    assert len(bot.calls) == 1
    assert bot.calls[0]["chat_id"] == -1004396644933
    assert bot.calls[0]["message_thread_id"] == 580


async def test_live_order_without_a_topic_sends_no_thread_id(monkeypatch):
    notif = _load()
    monkeypatch.setattr(notif, "LIVE_ORDERS_CHANNEL_ID", -1002191171631, raising=False)
    monkeypatch.setattr(notif, "LIVE_ORDERS_TOPIC_ID", 0, raising=False)
    bot = FakeBot()

    await notif.send_live_order_notification(FakeContext(bot), "Nguyen Van An", 39900)

    # Non-forum groups reject the parameter, so existing deployments must keep
    # sending the exact same call they always did.
    assert "message_thread_id" not in bot.calls[0]


async def test_live_order_masks_the_customer_name(monkeypatch):
    notif = _load()
    monkeypatch.setattr(notif, "LIVE_ORDERS_CHANNEL_ID", -1004396644933, raising=False)
    monkeypatch.setattr(notif, "LIVE_ORDERS_TOPIC_ID", 580, raising=False)
    bot = FakeBot()

    await notif.send_live_order_notification(FakeContext(bot), "Nguyen Van An", 39900)

    text = bot.calls[0]["text"]
    assert "Nguyen Van A***" in text
    assert "Nguyen Van An" not in text


async def test_disabled_channel_sends_nothing(monkeypatch):
    notif = _load()
    monkeypatch.setattr(notif, "LIVE_ORDERS_CHANNEL_ID", 0, raising=False)
    monkeypatch.setattr(notif, "LIVE_ORDERS_TOPIC_ID", 580, raising=False)
    bot = FakeBot()

    await notif.send_live_order_notification(FakeContext(bot), "Nguyen Van An", 39900)

    # A topic id alone is not a destination - it needs a group chat_id.
    assert bot.calls == []


async def test_a_missing_topic_is_reported_as_a_topic_problem(monkeypatch, caplog):
    notif = _load()
    from telegram.error import BadRequest

    monkeypatch.setattr(notif, "LIVE_ORDERS_CHANNEL_ID", -1004396644933, raising=False)
    monkeypatch.setattr(notif, "LIVE_ORDERS_TOPIC_ID", 580, raising=False)
    bot = FakeBot(error=BadRequest("Message thread not found"))

    with caplog.at_level("WARNING"):
        await notif.send_live_order_notification(FakeContext(bot), "Nguyen Van An", 39900)

    # Wrong chat_id and wrong topic_id both arrive as BadRequest. Saying "check
    # the channel" when the channel is fine sends the admin hunting in the
    # wrong place.
    assert "topic 580" in caplog.text
    assert "chua vao" not in caplog.text


@pytest.mark.parametrize(
    "message, expected",
    [
        # Telegram mixes styles in one API: spaces here, underscores there.
        ("Topic_closed", "DANG DONG"),
        ("TOPIC_CLOSED", "DANG DONG"),
        ("Message thread not found", "khong ton tai"),
        ("TOPIC_DELETED", "khong ton tai"),
    ],
)
async def test_every_spelling_of_a_topic_fault_is_recognised(monkeypatch, caplog, message, expected):
    notif = _load()
    from telegram.error import BadRequest

    monkeypatch.setattr(notif, "LIVE_ORDERS_CHANNEL_ID", -1004396644933, raising=False)
    monkeypatch.setattr(notif, "LIVE_ORDERS_TOPIC_ID", 580, raising=False)
    bot = FakeBot(error=BadRequest(message))

    with caplog.at_level("WARNING"):
        await notif.send_live_order_notification(FakeContext(bot), "Nguyen Van An", 39900)

    # Underscore spellings used to miss every marker and fall through to the
    # generic "Telegram API" line, which names no remedy.
    assert expected in caplog.text
    assert "topic 580" in caplog.text


async def test_a_missing_chat_is_still_reported_as_a_channel_problem(monkeypatch, caplog):
    notif = _load()
    from telegram.error import BadRequest

    monkeypatch.setattr(notif, "LIVE_ORDERS_CHANNEL_ID", -1004396644933, raising=False)
    monkeypatch.setattr(notif, "LIVE_ORDERS_TOPIC_ID", 580, raising=False)
    bot = FakeBot(error=BadRequest("Chat not found"))

    with caplog.at_level("WARNING"):
        await notif.send_live_order_notification(FakeContext(bot), "Nguyen Van An", 39900)

    assert "chua vao" in caplog.text


async def test_a_failed_post_never_breaks_the_sale(monkeypatch):
    notif = _load()
    from telegram.error import BadRequest

    monkeypatch.setattr(notif, "LIVE_ORDERS_CHANNEL_ID", -1004396644933, raising=False)
    monkeypatch.setattr(notif, "LIVE_ORDERS_TOPIC_ID", 580, raising=False)
    bot = FakeBot(error=BadRequest("Message thread not found"))

    # The notification is cosmetic; the customer has already paid by this point.
    await notif.send_live_order_notification(FakeContext(bot), "Nguyen Van An", 39900)


async def test_stock_notification_posts_into_its_topic(monkeypatch):
    notif = _load()
    monkeypatch.setattr(notif, "get_stock_channel_id", lambda: -1004396644933, raising=False)
    monkeypatch.setattr(notif, "get_stock_channel_topic_id", lambda: 42, raising=False)
    bot = FakeBot()

    await notif.notify_stock_added(FakeContext(bot), "ChatGPT Plus", 10, 25, price=39900)

    assert bot.calls[0]["chat_id"] == -1004396644933
    assert bot.calls[0]["message_thread_id"] == 42


def test_stock_topic_follows_whichever_source_set_the_channel(monkeypatch):
    notif = _load()
    monkeypatch.setattr(notif, "STOCK_CHANNEL_TOPIC_ID", 111, raising=False)

    # No runtime override: the .env topic applies to the .env channel.
    monkeypatch.setattr(notif, "bot_settings", {}, raising=False)
    assert notif.get_stock_channel_topic_id() == 111

    # /setstockchannel moved the channel, so the .env topic must not leak onto
    # the new one - a stale thread id would post into an unrelated topic.
    monkeypatch.setattr(notif, "bot_settings", {"stock_channel_id": -100999}, raising=False)
    assert notif.get_stock_channel_topic_id() == 0

    monkeypatch.setattr(
        notif, "bot_settings", {"stock_channel_id": -100999, "stock_channel_topic_id": 7}, raising=False
    )
    assert notif.get_stock_channel_topic_id() == 7


def test_negative_channel_ids_survive_env_parsing(monkeypatch):
    config = load_modules()["app.core.config_env"]

    # Group chat ids are always negative; a `minimum` floor of 1 would clamp
    # -1004396644933 up to 1 and post every sale into a stranger's chat.
    monkeypatch.setenv("SOME_CHANNEL_ID", "-1004396644933")
    assert config.get_env_int("SOME_CHANNEL_ID", 0, minimum=None) == -1004396644933

    # Topic ids stay non-negative.
    monkeypatch.setenv("SOME_TOPIC_ID", "-5")
    assert config.get_env_int("SOME_TOPIC_ID", 0, minimum=0) == 0
