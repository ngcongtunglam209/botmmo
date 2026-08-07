from app.core.runtime_loader import load_modules


def test_payment_legal_notice_is_clear_and_localized(monkeypatch):
    payment = load_modules()["app.handlers.payment_generation"]
    translations = (
        ("vi", "Tuân thủ pháp luật", "rửa tiền"),
        ("en", "Legal compliance", "money laundering"),
        ("zh", "合法合规", "洗钱"),
    )

    for lang, heading, prohibited_action in translations:
        monkeypatch.setattr(
            payment,
            "lt",
            lambda _user_id, vi, en, zh, selected=lang: {
                "vi": vi,
                "en": en,
                "zh": zh,
            }[selected],
        )
        notice = payment._build_payment_legal_notice(123)
        assert notice.startswith("\n\n🛡️")
        assert heading in notice
        assert prohibited_action in notice

