from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.runtime_loader import load_modules


def _update(chat_type: str, text: str):
    message = SimpleNamespace(text=text)
    return SimpleNamespace(
        effective_chat=SimpleNamespace(type=chat_type),
        effective_message=message,
        message=message,
    )


def test_private_start_does_not_require_bot_mention():
    user_entry = load_modules()["app.handlers.user_entry"]
    context = SimpleNamespace(bot=SimpleNamespace(username="example_bot"))

    assert user_entry._should_handle_start_command(_update("private", "/start"), context) is True


def test_group_start_requires_correct_bot_mention(monkeypatch):
    user_entry = load_modules()["app.handlers.user_entry"]
    monkeypatch.setattr(user_entry, "BOT_USERNAME", "example_bot")
    context = SimpleNamespace(bot=SimpleNamespace(username="example_bot"))

    assert user_entry._should_handle_start_command(_update("group", "/start"), context) is False
    assert user_entry._should_handle_start_command(_update("supergroup", "/start@other_bot"), context) is False
    assert user_entry._should_handle_start_command(_update("group", "/start@example_bot"), context) is True


@pytest.mark.asyncio
async def test_bare_group_start_is_ignored_before_other_checks(monkeypatch):
    user_entry = load_modules()["app.handlers.user_entry"]
    monkeypatch.setattr(user_entry, "BOT_USERNAME", "example_bot")

    async def unexpected_ban_check(_update):
        raise AssertionError("A bare /start in a group must be ignored immediately")

    monkeypatch.setattr(user_entry, "check_if_banned", unexpected_ban_check)
    context = SimpleNamespace(bot=SimpleNamespace(username="example_bot"))

    await user_entry.start_command(_update("group", "/start"), context)
