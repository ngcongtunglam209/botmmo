"""Bot chỉ phục vụ trong chat riêng.

Trong group, câu trả lời của bot lộ số dư/đơn hàng cho cả nhóm và ai cũng gõ
được lệnh. Chỉ giveaway và guard tiếng Trung được phép sống ở group.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from telegram.ext import CommandHandler, MessageHandler

from app.core.runtime_loader import load_modules


class _FakeMessage:
    def __init__(self, text):
        self.text = text
        self.html_replies = []

    async def reply_html(self, text, **kwargs):
        self.html_replies.append((text, kwargs.get("reply_markup")))


def _update(chat_type, text="/start@example_bot", user_id=7):
    message = _FakeMessage(text)
    return SimpleNamespace(
        effective_chat=SimpleNamespace(type=chat_type),
        effective_message=message,
        effective_user=SimpleNamespace(id=user_id, language_code="vi"),
        message=message,
    )


@pytest.fixture
def user_entry(monkeypatch):
    module = load_modules()["app.handlers.user_entry"]
    monkeypatch.setattr(module, "BOT_USERNAME", "example_bot", raising=False)

    async def not_banned(_update):
        return False

    monkeypatch.setattr(module, "check_if_banned", not_banned, raising=False)
    return module


def _context(args=None):
    return SimpleNamespace(
        bot=SimpleNamespace(username="example_bot"),
        args=args or [],
        user_data={},
    )


async def test_group_start_answers_with_a_private_chat_link(user_entry, monkeypatch):
    async def unexpected_menu(*args, **kwargs):
        raise AssertionError("Menu chính không được hiển thị trong group")

    monkeypatch.setattr(user_entry, "send_start_welcome_with_video", unexpected_menu, raising=False)

    update = _update("supergroup")
    await user_entry.start_command(update, _context())

    assert len(update.message.html_replies) == 1
    text, markup = update.message.html_replies[0]
    assert "chat riêng" in text
    url = markup.inline_keyboard[0][0].url
    assert url == "https://t.me/example_bot"


async def test_group_start_keeps_the_referral_payload(user_entry, monkeypatch):
    monkeypatch.setattr(
        user_entry, "send_start_welcome_with_video", lambda *a, **k: None, raising=False
    )

    update = _update("group")
    await user_entry.start_command(update, _context(args=["ref_12345"]))

    _, markup = update.message.html_replies[0]
    assert markup.inline_keyboard[0][0].url == "https://t.me/example_bot?start=ref_12345"


async def test_group_start_drops_a_malformed_payload(user_entry, monkeypatch):
    """Chỉ nhận payload deep link hợp lệ, không nhồi ký tự lạ vào URL."""
    monkeypatch.setattr(
        user_entry, "send_start_welcome_with_video", lambda *a, **k: None, raising=False
    )

    update = _update("group")
    await user_entry.start_command(update, _context(args=["ref_1 evil?x=1"]))

    _, markup = update.message.html_replies[0]
    assert markup.inline_keyboard[0][0].url == "https://t.me/example_bot"


@pytest.fixture(scope="module")
def bot_application():
    from telegram.ext import Application

    entry = load_modules()["app.legacy_entry"]
    application = Application.builder().token("123456:TEST-TOKEN-NOT-USED").build()
    entry.register_handlers(application)
    return application


def _iter_handlers(application):
    for handlers in application.handlers.values():
        yield from handlers


def test_every_command_except_start_is_private_only(bot_application):
    """/start và /menu tự gác bằng _should_handle_start_command."""
    offenders = []
    for handler in _iter_handlers(bot_application):
        if not isinstance(handler, CommandHandler):
            continue
        commands = set(handler.commands)
        if commands <= {"start", "menu"}:
            continue
        if "private" not in str(handler.filters).lower():
            offenders.append(sorted(commands))
    assert offenders == []


def test_free_text_handlers_do_not_listen_in_groups(bot_application):
    """AI reply và bắt email chỉ chạy ở chat riêng.

    Giveaway comment và guard tiếng Trung là ngoại lệ có chủ đích.
    """
    group_features = {"ga_comment_handler", "ga_edit_handler", "chinese_language_guard_handler"}
    offenders = []
    for handler in _iter_handlers(bot_application):
        if not isinstance(handler, MessageHandler):
            continue
        name = getattr(handler.callback, "__name__", "")
        if name in group_features:
            continue
        if "private" not in str(handler.filters).lower():
            offenders.append(name)
    assert offenders == []
