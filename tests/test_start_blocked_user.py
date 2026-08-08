"""/start from someone who blocked the bot must not raise."""

from telegram.error import Forbidden

from app.core.runtime_loader import load_modules


class BlockedMessage:
    async def reply_html(self, text, **kwargs):
        raise Forbidden("Forbidden: bot was blocked by the user")

    async def reply_video(self, **kwargs):
        raise Forbidden("Forbidden: bot was blocked by the user")


class FakeUser:
    id = 7193749511
    first_name = "Dino"
    last_name = None
    username = "blocked"
    full_name = "Dino"
    is_premium = False
    language_code = "vi"


class FakeUpdate:
    def __init__(self):
        self.message = BlockedMessage()
        self.effective_user = FakeUser()


class FakeContext:
    user_data: dict = {}


async def test_the_text_menu_gives_up_quietly_when_the_bot_is_blocked(monkeypatch):
    telegram_io = load_modules()["app.utils.telegram_io"]
    monkeypatch.setattr(telegram_io, "WELCOME_VIDEO_ENABLED", False, raising=False)

    # A blocked user can still have a queued /start replayed at us. Letting the
    # Forbidden escape printed a full traceback per such update, burying real
    # errors in the log.
    await telegram_io.send_start_welcome_with_video(FakeUpdate(), FakeContext(), FakeUser())


async def test_the_video_path_does_not_retry_as_text_when_the_bot_is_blocked(monkeypatch):
    telegram_io = load_modules()["app.utils.telegram_io"]
    monkeypatch.setattr(telegram_io, "WELCOME_VIDEO_ENABLED", True, raising=False)
    monkeypatch.setattr(telegram_io, "WELCOME_VIDEO_URL", "https://example/welcome.mp4", raising=False)
    monkeypatch.setattr(telegram_io, "WELCOME_VIDEO_FILE_ID", "", raising=False)

    text_attempts = []

    async def spy_reply_html(message, text, **kwargs):
        text_attempts.append(text)
        raise Forbidden("Forbidden: bot was blocked by the user")

    monkeypatch.setattr(telegram_io, "safe_reply_html", spy_reply_html, raising=False)

    await telegram_io.send_start_welcome_with_video(FakeUpdate(), FakeContext(), FakeUser())

    assert text_attempts == []
