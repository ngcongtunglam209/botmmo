import pytest
from telegram.error import BadRequest

from app.core.runtime_loader import load_modules


def _load():
    modules = load_modules()
    return modules["app.utils.ui_and_email"], modules["app.utils.telegram_io"]


ACTION_FIELDS = (
    "callback_data", "url", "copy_text", "web_app", "login_url", "pay",
    "callback_game", "switch_inline_query", "switch_inline_query_current_chat",
    "switch_inline_query_chosen_chat",
)


def _has_action(button) -> bool:
    """Telegram rejects the whole keyboard if any button carries no action."""
    payload = button.to_dict()
    return any(payload.get(name) not in (None, "") for name in ACTION_FIELDS)


def test_an_empty_url_never_reaches_telegram():
    ui, _ = _load()

    # SUPPORT_GROUP_LINK unset means url="", which PTB happily serialises as
    # {"text": ..., "url": ""}. Telegram reads that as a text-only button and
    # rejects the entire keyboard, not just this button.
    button = ui._btn("Cong dong", url="")

    assert button.to_dict().get("url") is None
    assert button.callback_data == "ignore"
    assert _has_action(button)


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_blank_actions_of_any_shape_are_dropped(blank):
    ui, _ = _load()

    assert _has_action(ui._btn("x", url=blank))
    assert _has_action(ui._btn("x", callback_data=blank))


def test_a_real_action_is_left_alone():
    ui, _ = _load()

    button = ui._btn("Mua hang", icon_id="123", callback_data="store_main", style="success")

    assert button.callback_data == "store_main"
    assert button.api_kwargs["icon_custom_emoji_id"] == "123"
    assert button.api_kwargs["style"] == "success"

    linked = ui._btn("Nhom", url="https://t.me/lamshop")
    assert linked.url == "https://t.me/lamshop"
    assert linked.callback_data is None


def test_a_web_app_with_a_blank_url_is_dropped():
    ui, _ = _load()
    from telegram import WebAppInfo

    button = ui._btn("Admin", web_app=WebAppInfo(url=""))

    assert button.web_app is None
    assert _has_action(button)


def test_main_menu_stays_sendable_without_a_support_link(monkeypatch):
    ui, _ = _load()
    monkeypatch.setattr(ui, "SUPPORT_GROUP_LINK", "", raising=False)

    markup = ui.create_main_menu(user_id=1000000001)

    for row in markup.inline_keyboard:
        for button in row:
            assert _has_action(button), f"nut khong co action: {button.text}"
    # The community button links nowhere, so it is left out rather than shown dead.
    assert all("t.me" not in (b.url or "") for row in markup.inline_keyboard for b in row)


def test_main_menu_shows_the_community_button_when_configured(monkeypatch):
    ui, _ = _load()
    monkeypatch.setattr(ui, "SUPPORT_GROUP_LINK", "https://t.me/lamshop", raising=False)

    markup = ui.create_main_menu(user_id=1000000001)

    urls = [b.url for row in markup.inline_keyboard for b in row if b.url]
    assert "https://t.me/lamshop" in urls


def test_admin_menu_omits_the_web_app_button_without_https(monkeypatch):
    ui, _ = _load()
    monkeypatch.setattr(ui, "SUPPORT_GROUP_LINK", "https://t.me/lamshop", raising=False)
    monkeypatch.setattr(ui, "ADMIN_USER_ID", 1000000001, raising=False)
    # PUBLIC_API_URL unset -> get_public_api_base_url() returns the
    # http://YOUR_VPS_IP placeholder, and Telegram only opens web apps over HTTPS.
    monkeypatch.setattr(ui, "get_public_api_base_url", lambda: "http://YOUR_VPS_IP:8080", raising=False)

    markup = ui.create_main_menu(user_id=1000000001)

    assert all(b.web_app is None for row in markup.inline_keyboard for b in row)
    for row in markup.inline_keyboard:
        for button in row:
            assert _has_action(button)


def test_admin_menu_keeps_the_web_app_button_over_https(monkeypatch):
    ui, _ = _load()
    monkeypatch.setattr(ui, "SUPPORT_GROUP_LINK", "https://t.me/lamshop", raising=False)
    monkeypatch.setattr(ui, "ADMIN_USER_ID", 1000000001, raising=False)
    monkeypatch.setattr(ui, "get_public_api_base_url", lambda: "https://lamtung.dev", raising=False)

    markup = ui.create_main_menu(user_id=1000000001)

    web_apps = [b.web_app.url for row in markup.inline_keyboard for b in row if b.web_app]
    assert web_apps == ["https://lamtung.dev/admin"]


def test_keyboard_errors_are_not_mistaken_for_tg_emoji_errors():
    _, io = _load()

    keyboard_error = BadRequest(
        "Can't parse inlinekeyboardbutton: text buttons are unallowed in the inline keyboard"
    )
    # It contains "parse", but retrying with plain text resends the same broken
    # keyboard and the log then blames tg-emoji for a keyboard fault.
    assert io._is_tg_emoji_parse_error(keyboard_error) is False

    assert io._is_tg_emoji_parse_error(BadRequest("Can't parse entities: unsupported start tag")) is True
    assert io._is_tg_emoji_parse_error(BadRequest("Document_invalid")) is True


async def test_a_keyboard_error_propagates_instead_of_being_retried():
    _, io = _load()
    attempts = []

    class Message:
        async def reply_html(self, text, **kwargs):
            attempts.append(text)
            raise BadRequest(
                "Can't parse inlinekeyboardbutton: text buttons are unallowed in the inline keyboard"
            )

    with pytest.raises(BadRequest):
        await io.safe_reply_html(Message(), "<b>xin chao</b>")

    # One attempt, not two: the second was always going to fail identically.
    assert len(attempts) == 1
