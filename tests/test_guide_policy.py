from app.core.runtime_loader import load_modules


def test_guide_and_policy_are_complete_and_fit_telegram():
    ui = load_modules()["app.utils.ui_and_email"]

    assert ui.HUONGDAN_TEXT != ui.CHINHSACH_TEXT
    assert len(ui.HUONGDAN_TEXT) < 4096
    assert len(ui.CHINHSACH_TEXT) < 4096

    for required_text in (
        "Làm mới giá &amp; tồn kho",
        "Dịch vụ Social Media",
        "Báo lỗi và bảo hành",
        "An toàn tài khoản",
    ):
        assert required_text in ui.HUONGDAN_TEXT

    for required_text in (
        "Hủy đơn và hoàn tiền",
        "Dữ liệu và quyền riêng tư",
        "Hành vi bị cấm",
        "Khiếu nại và hỗ trợ",
    ):
        assert required_text in ui.CHINHSACH_TEXT


def test_guide_policy_menu_switches_between_both_pages():
    ui = load_modules()["app.utils.ui_and_email"]
    menu = ui.create_guide_policy_menu("policy")
    callbacks = [button.callback_data for row in menu.inline_keyboard for button in row]

    assert callbacks == ["huongdan", "chinhsach", "back_to_main"]

