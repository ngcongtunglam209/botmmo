from decimal import Decimal

from app.core.runtime_loader import load_modules


def _config():
    return load_modules()["app.core.config_env"]


def test_a_blank_line_falls_back_to_the_default(monkeypatch):
    config = _config()

    # .env is loaded with override=True, so `KEY=` sets the variable to "" and
    # os.getenv(name, default) hands back "" instead of the default. Shipping
    # `USDT_RATE_SOURCE_URL=` blank in .env.example emptied the rate source URL
    # and broke every crypto invoice.
    monkeypatch.setenv("SOME_URL", "")
    assert config.get_env_str("SOME_URL", "https://default") == "https://default"

    monkeypatch.setenv("SOME_URL", "   ")
    assert config.get_env_str("SOME_URL", "https://default") == "https://default"

    monkeypatch.delenv("SOME_URL", raising=False)
    assert config.get_env_str("SOME_URL", "https://default") == "https://default"


def test_a_real_value_still_wins(monkeypatch):
    config = _config()

    monkeypatch.setenv("SOME_URL", "  https://custom  ")
    assert config.get_env_str("SOME_URL", "https://default") == "https://custom"


def test_a_blank_flag_does_not_silently_mean_off(monkeypatch):
    config = _config()

    # `ENABLE_PAYMENT_SEPAY=` used to evaluate to False and quietly disable the
    # gateway, with nothing in the logs to say why.
    monkeypatch.setenv("SOME_FLAG", "")
    assert config.get_env_bool("SOME_FLAG", True) is True
    assert config.get_env_bool("SOME_FLAG", False) is False

    for truthy in ("1", "true", "TRUE", "yes", "on"):
        monkeypatch.setenv("SOME_FLAG", truthy)
        assert config.get_env_bool("SOME_FLAG", False) is True

    for falsy in ("0", "false", "no", "off", "nonsense"):
        monkeypatch.setenv("SOME_FLAG", falsy)
        assert config.get_env_bool("SOME_FLAG", True) is False


def test_the_rate_source_url_survives_a_blank_line(monkeypatch):
    config = _config()

    monkeypatch.setenv("USDT_RATE_SOURCE_URL", "")
    url = config.get_env_str(
        "USDT_RATE_SOURCE_URL", "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    )

    # An empty URL makes the rate fetch throw, which falls back to
    # USDT_RATE_VND_PER_USDT=0, which makes convert_vnd_to_usdt raise.
    assert url.startswith("https://")


def test_a_blank_port_no_longer_crashes_at_import(monkeypatch):
    config = _config()

    # int(os.getenv("API_SERVER_PORT", "8080")) raised ValueError on `KEY=`,
    # killing the bot during module import rather than at first use.
    monkeypatch.setenv("API_SERVER_PORT", "")
    assert config.get_env_int("API_SERVER_PORT", 8080, minimum=1) == 8080


def test_price_formatting_sees_the_rate_fetched_by_another_module(monkeypatch):
    modules = load_modules()
    payments = modules["app.integrations.payments_core"]
    store_menu = modules["app.services.store_menu"]

    monkeypatch.setattr(payments, "_cached_live_usdt_rate", Decimal("26100"), raising=False)

    # `_cached_live_usdt_rate` is a payments_core module global rebound at
    # runtime. The runtime loader copies symbols between modules once, at load,
    # so store_menu's own globals() keeps the stale None it was built with —
    # reading it there fell through to USDT_RATE_VND_PER_USDT (0) and made every
    # EN/ZH price render in VND. Going through the accessor runs in
    # payments_core's namespace and sees the live value.
    assert store_menu.__dict__.get("_cached_live_usdt_rate") is None
    assert store_menu.get_cached_usdt_rate() == Decimal("26100")


def test_price_formatting_falls_back_to_vnd_when_no_rate_is_known(monkeypatch):
    modules = load_modules()
    payments = modules["app.integrations.payments_core"]
    store_menu = modules["app.services.store_menu"]

    monkeypatch.setattr(payments, "_cached_live_usdt_rate", None, raising=False)
    monkeypatch.setattr(payments, "USDT_RATE_VND_PER_USDT", Decimal("0"), raising=False)

    # Showing "0.00 USDT" would be worse than showing the VND figure.
    assert store_menu.get_cached_usdt_rate() == Decimal("0")
