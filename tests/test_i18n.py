from app.utils import i18n


def test_supported_language_aliases():
    aliases = {
        "vi": "vi",
        "VN": "vi",
        "english": "en",
        "zh-CN": "zh",
        "中文": "zh",
    }
    for value, expected in aliases.items():
        assert i18n.normalize_lang(value) == expected


def test_ietf_language_tags_resolve_to_base_language():
    tags = {
        "en-US": "en",
        "zh-Hans": "zh",
        "zh_TW": "zh",
        "vi-VN": "vi",
    }
    for value, expected in tags.items():
        assert i18n.normalize_lang(value) == expected


def test_unknown_language_falls_back_to_vietnamese():
    assert i18n.normalize_lang("unknown") == i18n.DEFAULT_LANG
    assert i18n.t("btn_shop", lang="unknown") == i18n.STRINGS["vi"]["btn_shop"]


def test_all_languages_have_the_same_translation_keys():
    expected = set(i18n.STRINGS[i18n.DEFAULT_LANG])
    for lang in i18n.SUPPORTED_LANGS:
        assert set(i18n.STRINGS[lang]) == expected


def test_translation_formats_values():
    assert i18n.t("hello", lang="en", name="V") == "Hello V!"
    assert i18n.t("hello", lang="zh", name="V") == "你好 V!"


def test_user_language_is_stored_in_existing_profile(monkeypatch):
    users = {"42": {"balance": 1000}}
    monkeypatch.setattr(i18n, "user_data_db", users, raising=False)

    assert i18n.set_user_lang(42, "english") == "en"
    assert users["42"]["lang"] == "en"
    assert i18n.get_user_lang(42) == "en"


def test_user_language_creates_missing_profile(monkeypatch):
    users = {}
    monkeypatch.setattr(i18n, "user_data_db", users, raising=False)

    i18n.set_user_lang(7, "zh-CN")

    assert users["7"] == {"lang": "zh", "balance": 0}


class _FakeTelegramUser:
    def __init__(self, user_id, language_code=None):
        self.id = user_id
        self.language_code = language_code


def test_resolve_lang_uses_telegram_client_language_for_new_user(monkeypatch):
    monkeypatch.setattr(i18n, "user_data_db", {}, raising=False)

    assert i18n.resolve_lang(_FakeTelegramUser(5, "en-US")) == "en"
    assert i18n.resolve_lang(_FakeTelegramUser(5, "zh-Hans")) == "zh"
    assert i18n.resolve_lang(_FakeTelegramUser(5, None)) == i18n.DEFAULT_LANG
    assert i18n.resolve_lang(_FakeTelegramUser(5, "ru")) == i18n.DEFAULT_LANG


def test_resolve_lang_prefers_stored_profile_language(monkeypatch):
    users = {"5": {"lang": "zh", "balance": 0}}
    monkeypatch.setattr(i18n, "user_data_db", users, raising=False)

    assert i18n.resolve_lang(_FakeTelegramUser(5, "en-US")) == "zh"
