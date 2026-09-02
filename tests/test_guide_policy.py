import pytest

from app.core.runtime_loader import load_modules

LANGS = ("vi", "en", "zh")


@pytest.fixture(scope="module")
def ui():
    return load_modules()["app.utils.ui_and_email"]


@pytest.mark.parametrize("lang", LANGS)
def test_guide_and_policy_are_distinct_and_fit_telegram(ui, lang):
    guide = getattr(ui, f"HUONGDAN_TEXT_{lang.upper()}")
    policy = getattr(ui, f"CHINHSACH_TEXT_{lang.upper()}")

    assert guide != policy
    # Telegram rejects a message body over 4096 characters.
    assert len(guide) < 4096
    assert len(policy) < 4096


def test_vietnamese_guide_and_policy_keep_their_sections(ui):
    for required_text in ("Báo lỗi và bảo hành", "An toàn tài khoản"):
        assert required_text in ui.HUONGDAN_TEXT_VI

    for required_text in (
        "Hủy đơn và hoàn tiền",
        "Dữ liệu và quyền riêng tư",
        "Hành vi bị cấm",
        "Khiếu nại và hỗ trợ",
    ):
        assert required_text in ui.CHINHSACH_TEXT_VI


def test_every_language_covers_the_same_sections(ui):
    expected_sections = {
        "en": {
            "guide": ("Reporting a problem and warranty", "Account safety"),
            "policy": ("Cancellation and refunds", "Data and privacy", "Prohibited use", "Complaints and support"),
        },
        "zh": {
            "guide": ("报错与保修", "账号安全"),
            "policy": ("取消与退款", "数据与隐私", "禁止行为", "投诉与支持"),
        },
    }
    for lang, sections in expected_sections.items():
        guide = getattr(ui, f"HUONGDAN_TEXT_{lang.upper()}")
        policy = getattr(ui, f"CHINHSACH_TEXT_{lang.upper()}")
        for text in sections["guide"]:
            assert text in guide, f"{lang} guide is missing {text!r}"
        for text in sections["policy"]:
            assert text in policy, f"{lang} policy is missing {text!r}"


def test_guide_policy_menu_switches_between_both_pages(ui):
    menu = ui.create_guide_policy_menu("policy")
    callbacks = [button.callback_data for row in menu.inline_keyboard for button in row]

    assert callbacks == ["huongdan", "chinhsach", "back_to_main"]
