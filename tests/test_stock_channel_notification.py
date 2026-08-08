import pytest

from app.core.runtime_loader import load_modules


class _FakeBot:
    username = "lamshopbot"

    def __init__(self, fail_with=None):
        self.sent = []
        self.fail_with = fail_with

    async def send_message(self, **kwargs):
        if self.fail_with is not None:
            raise self.fail_with
        self.sent.append(kwargs)


class _FakeContext:
    def __init__(self, bot):
        self.bot = bot


@pytest.fixture
def notifications(monkeypatch):
    module = load_modules()["app.services.notifications_async"]
    monkeypatch.setattr(module, "bot_settings", {}, raising=False)
    monkeypatch.setattr(module, "STOCK_CHANNEL_ID", 0, raising=False)
    return module


def test_channel_falls_back_to_env_when_no_override(notifications, monkeypatch):
    monkeypatch.setattr(notifications, "STOCK_CHANNEL_ID", -100777, raising=False)
    assert notifications.get_stock_channel_id() == -100777


def test_runtime_override_beats_env(notifications, monkeypatch):
    monkeypatch.setattr(notifications, "STOCK_CHANNEL_ID", -100777, raising=False)
    monkeypatch.setattr(notifications, "bot_settings", {"stock_channel_id": -100999}, raising=False)
    assert notifications.get_stock_channel_id() == -100999


def test_override_of_zero_disables_the_env_channel(notifications, monkeypatch):
    """`/setstockchannel off` must win over a channel configured in .env."""
    monkeypatch.setattr(notifications, "STOCK_CHANNEL_ID", -100777, raising=False)
    monkeypatch.setattr(notifications, "bot_settings", {"stock_channel_id": 0}, raising=False)
    assert notifications.get_stock_channel_id() == 0


def test_garbage_override_falls_back_to_env(notifications, monkeypatch):
    monkeypatch.setattr(notifications, "STOCK_CHANNEL_ID", -100777, raising=False)
    monkeypatch.setattr(notifications, "bot_settings", {"stock_channel_id": "abc"}, raising=False)
    assert notifications.get_stock_channel_id() == -100777


async def test_no_post_when_channel_is_not_configured(notifications):
    bot = _FakeBot()
    await notifications.notify_stock_added(_FakeContext(bot), "Netflix", 10, 10)
    assert bot.sent == []


async def test_post_carries_product_counts_and_price(notifications, monkeypatch):
    monkeypatch.setattr(notifications, "bot_settings", {"stock_channel_id": -100123}, raising=False)
    bot = _FakeBot()

    await notifications.notify_stock_added(_FakeContext(bot), "Netflix 1 tháng", 25, 130, price=59000)

    assert len(bot.sent) == 1
    sent = bot.sent[0]
    assert sent["chat_id"] == -100123
    text = sent["text"]
    assert "HÀNG MỚI VỀ" in text
    assert "Netflix 1 tháng" in text
    assert "25" in text
    assert "130" in text
    assert "59,000" in text
    assert "@lamshopbot" in text


async def test_product_name_is_html_escaped(notifications, monkeypatch):
    monkeypatch.setattr(notifications, "bot_settings", {"stock_channel_id": -100123}, raising=False)
    bot = _FakeBot()

    await notifications.notify_stock_added(_FakeContext(bot), "<b>Hack</b> & co", 1, 1)

    text = bot.sent[0]["text"]
    assert "&lt;b&gt;Hack&lt;/b&gt; &amp; co" in text


async def test_send_failure_does_not_propagate(notifications, monkeypatch):
    """Nhập kho không được hỏng chỉ vì bot chưa vào kênh."""
    monkeypatch.setattr(notifications, "bot_settings", {"stock_channel_id": -100123}, raising=False)
    bot = _FakeBot(fail_with=notifications.BadRequest("Chat not found"))

    await notifications.notify_stock_added(_FakeContext(bot), "Netflix", 5, 5)


async def test_set_stock_channel_persists_only_its_own_table(notifications, monkeypatch):
    settings = {}
    saved = []
    monkeypatch.setattr(notifications, "bot_settings", settings, raising=False)

    async def fake_save(force=False, tables=None):
        saved.append((force, tables))

    monkeypatch.setattr(notifications, "save_data", fake_save, raising=False)

    assert await notifications.set_stock_channel_id(-100456) == -100456
    assert settings == {"stock_channel_id": -100456, "stock_channel_topic_id": 0}
    assert saved == [(True, ["data_bot_settings.json"])]


async def test_set_stock_channel_clears_a_stale_topic(notifications, monkeypatch):
    settings = {"stock_channel_id": -100123, "stock_channel_topic_id": 580}
    monkeypatch.setattr(notifications, "bot_settings", settings, raising=False)

    async def fake_save(force=False, tables=None):
        return None

    monkeypatch.setattr(notifications, "save_data", fake_save, raising=False)

    await notifications.set_stock_channel_id(-100456)
    # Topic 580 belongs to the old group. Carrying it over would post into
    # whatever topic happens to have that id in the new one.
    assert settings["stock_channel_topic_id"] == 0

    await notifications.set_stock_channel_id(-100456, 42)
    assert settings["stock_channel_topic_id"] == 42

    # Turning notifications off drops the topic with the channel.
    await notifications.set_stock_channel_id(0, 42)
    assert settings == {"stock_channel_id": 0, "stock_channel_topic_id": 0}
