"""Rank name and balance follow the reader's language, not the shop's."""

from decimal import Decimal

import pytest

from app.core.runtime_loader import load_modules


@pytest.fixture
def rank_env(monkeypatch):
    modules = load_modules()
    payments = modules["app.integrations.payments_core"]
    stats = modules["app.services.referrals_stats"]
    ui = modules["app.utils.ui_and_email"]

    monkeypatch.setattr(payments, "_cached_live_usdt_rate", Decimal("26000"), raising=False)
    monkeypatch.setattr(payments, "_cached_live_cny_rate", Decimal("7.2"), raising=False)

    # The runtime loader copies symbols into every module's own globals, so the
    # language has to be forced module by module — and put back afterwards, or
    # the next test in the session reads its strings in the wrong language.
    originals = {
        module: module.__dict__["get_user_lang"]
        for module in modules.values()
        if "get_user_lang" in module.__dict__
    }

    def use_lang(lang):
        for module in originals:
            module.__dict__["get_user_lang"] = lambda _user_id=None, _lang=lang: _lang

    yield payments, stats, ui, use_lang

    for module, original in originals.items():
        module.__dict__["get_user_lang"] = original


def test_rank_names_are_translated(rank_env):
    _payments, stats, _ui, use_lang = rank_env
    diamond = {"name": "💎 Kim Cương", "min_spent": 5000000, "discount": 0}

    use_lang("vi")
    assert stats.format_rank_entry_premium(diamond, user_id=1).endswith("Kim Cương")

    # An English or Chinese customer used to be told their rank in Vietnamese.
    use_lang("en")
    assert stats.format_rank_entry_premium(diamond, user_id=1).endswith("Diamond")

    use_lang("zh")
    assert stats.format_rank_entry_premium(diamond, user_id=1).endswith("钻石")


def test_rank_tiers_are_read_from_the_spend_threshold(rank_env):
    _payments, stats, _ui, use_lang = rank_env
    use_lang("en")

    assert stats.rank_tier_key({"name": "⭐️ Đồng", "min_spent": 0}) == "bronze"
    assert stats.rank_tier_key({"name": "⭐️ Bạc", "min_spent": 500000}) == "silver"
    assert stats.rank_tier_key({"name": "⭐️ Vàng", "min_spent": 1000000}) == "gold"
    assert stats.rank_tier_key({"name": "⭐️ Cao Thủ", "min_spent": 10000000}) == "master"
    # Renaming a rank in VIP_RANKS must not drop anyone back to bronze.
    assert stats.rank_tier_key({"name": "Elite Tier", "min_spent": 5000000}) == "diamond"
    assert stats.rank_tier_key(None) == "bronze"


def test_the_main_menu_summary_uses_the_readers_currency(rank_env, monkeypatch):
    _payments, _stats, ui, use_lang = rank_env
    modules = load_modules()
    db = modules["app.services.games_withdrawals_db"]
    monkeypatch.setattr(db, "db_get_user", lambda _uid: {"balance": 260000}, raising=False)

    use_lang("vi")
    assert "260,000 VNĐ" in ui.build_main_menu_account_summary(555)

    use_lang("en")
    summary = ui.build_main_menu_account_summary(555)
    assert "$10.00" in summary
    assert "VNĐ" not in summary

    use_lang("zh")
    assert "¥72.00 ($10.00)" in ui.build_main_menu_account_summary(555)


def test_the_status_button_stays_plain_text(rank_env, monkeypatch):
    _payments, _stats, ui, use_lang = rank_env
    modules = load_modules()
    db = modules["app.services.games_withdrawals_db"]
    monkeypatch.setattr(db, "db_get_user", lambda _uid: {"balance": 260000}, raising=False)

    use_lang("en")
    text = ui.build_main_menu_status_button_text(555)

    # Button labels render literally, so a tg-emoji tag would show as markup.
    assert "<" not in text
    assert "$10.00" in text
