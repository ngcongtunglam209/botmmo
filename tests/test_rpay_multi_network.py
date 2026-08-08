from decimal import Decimal

import pytest

from app.core.runtime_loader import load_modules


def _load():
    modules = load_modules()
    return modules["app.integrations.rpay_api"], modules["app.integrations.payments_core"]


def _configure(monkeypatch, rpay, networks, addresses=None):
    monkeypatch.setattr(rpay, "RPAY_MERCHANT_ID", "M1", raising=False)
    monkeypatch.setattr(rpay, "RPAY_API_KEY", "K1", raising=False)
    monkeypatch.setattr(rpay, "ENABLE_PAYMENT_RPAY", True, raising=False)
    monkeypatch.setattr(rpay, "RPAY_NETWORKS", list(networks), raising=False)
    monkeypatch.setattr(rpay, "RPAY_WALLET_ADDRESS_BY_NETWORK", dict(addresses or {}), raising=False)


def test_networks_are_listed_for_the_customer(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay, ["bsc", "tron", "polygon"])

    assert rpay.rpay_available_networks() == ["bsc", "tron", "polygon"]


def test_a_single_network_needs_no_picker(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay, ["bsc"])

    # One wallet: creating the invoice straight away is the whole point.
    assert len(rpay.rpay_available_networks()) == 1


def test_network_names_are_the_ones_wallets_actually_show():
    rpay, _ = _load()

    # "bsc" on a button tells a customer nothing; BEP20 is what their wallet says.
    assert rpay.rpay_network_label("bsc") == "BNB Smart Chain (BEP20)"
    assert rpay.rpay_network_label("tron") == "TRON (TRC20)"
    assert rpay.rpay_network_label("polygon") == "Polygon"
    # An unknown key is shown as-is rather than guessed at.
    assert rpay.rpay_network_label("newchain") == "NEWCHAIN"


def test_a_shared_address_is_never_reused_across_networks(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay, ["bsc", "tron", "polygon"])
    monkeypatch.setattr(rpay, "RPAY_WALLET_ADDRESS", "0xshared", raising=False)

    # A BSC address is not a TRON address. Sending one for all three would tell
    # customers to pay into an address that cannot exist on that chain, so with
    # several networks configured the shared value is dropped and RPay picks.
    assert rpay.rpay_wallet_address_for("bsc") == ""
    assert rpay.rpay_wallet_address_for("tron") == ""


def test_a_shared_address_still_applies_to_a_lone_network(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay, ["bsc"])
    monkeypatch.setattr(rpay, "RPAY_WALLET_ADDRESS", "0xshared", raising=False)

    assert rpay.rpay_wallet_address_for("bsc") == "0xshared"


def test_per_network_addresses_win(monkeypatch):
    rpay, _ = _load()
    _configure(
        monkeypatch, rpay, ["bsc", "tron"], {"bsc": "0xbsc", "tron": "Ttron"}
    )
    monkeypatch.setattr(rpay, "RPAY_WALLET_ADDRESS", "0xshared", raising=False)

    assert rpay.rpay_wallet_address_for("bsc") == "0xbsc"
    assert rpay.rpay_wallet_address_for("tron") == "Ttron"
    # Configured but with no address of its own: let RPay choose.
    assert rpay.rpay_wallet_address_for("polygon") == ""


async def test_the_chosen_network_reaches_rpay(monkeypatch):
    rpay, payments = _load()
    _configure(monkeypatch, rpay, ["bsc", "tron", "polygon"], {"tron": "Ttron"})
    monkeypatch.setattr(rpay, "RPAY_NETWORK", "bsc", raising=False)
    sent = {}

    async def fake_request(path, payload):
        sent.update(payload)
        return {"trans_id": "TX1", "address": "Ttron", "network": "tron"}

    monkeypatch.setattr(rpay, "_rpay_request", fake_request, raising=False)
    monkeypatch.setattr(rpay, "rpay_callback_url", lambda: "https://shop.example/webhook/rpay", raising=False)

    await rpay.rpay_create_invoice(
        order_code="ICLD123456",
        request_id="ICLD123456:abc",
        amount_usdt=Decimal("1.54"),
        name="ChatGPT Plus",
        network="tron",
    )

    assert sent["network"] == "tron"
    assert sent["address"] == "Ttron"


async def test_no_choice_falls_back_to_the_configured_default(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay, ["bsc"])
    monkeypatch.setattr(rpay, "RPAY_NETWORK", "bsc", raising=False)
    sent = {}

    async def fake_request(path, payload):
        sent.update(payload)
        return {"trans_id": "TX1"}

    monkeypatch.setattr(rpay, "_rpay_request", fake_request, raising=False)
    monkeypatch.setattr(rpay, "rpay_callback_url", lambda: "https://shop.example/webhook/rpay", raising=False)

    await rpay.rpay_create_invoice(
        order_code="ICLD123456",
        request_id="ICLD123456:abc",
        amount_usdt=Decimal("1.54"),
        name="ChatGPT Plus",
    )

    assert sent["network"] == "bsc"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("bsc,tron,polygon", ["bsc", "tron", "polygon"]),
        ("BSC, TRON , Polygon", ["bsc", "tron", "polygon"]),
        ("bsc tron;polygon", ["bsc", "tron", "polygon"]),
        ("", []),
    ],
)
def test_the_network_list_parses_however_it_is_typed(monkeypatch, raw, expected):
    import re

    config = load_modules()["app.core.config_env"]
    monkeypatch.setenv("RPAY_NETWORKS", raw)

    parsed = [n for n in re.split(r"[,\s;]+", config.get_env_str("RPAY_NETWORKS", "").lower()) if n]

    assert parsed == expected


def _reset_verified(monkeypatch, rpay, value=None):
    monkeypatch.setattr(rpay, "_rpay_verified_networks", value, raising=False)


async def test_invalid_network_keys_are_dropped_from_the_picker(monkeypatch):
    rpay, _ = _load()
    # "trc" and "pol" are what a human writes; RPay calls them tron and polygon.
    _configure(monkeypatch, rpay, ["bsc", "trc", "pol"])
    _reset_verified(monkeypatch, rpay)

    async def fake_networks():
        return [
            {"key": "bsc", "status": "active"},
            {"key": "tron", "status": "active"},
            {"key": "polygon", "status": "active"},
        ]

    monkeypatch.setattr(rpay, "rpay_get_networks", fake_networks, raising=False)

    remaining = await rpay.rpay_verify_networks()

    # Otherwise the bad keys only surface as HTTP 400 after a customer has
    # already chosen one and the order is dead.
    assert remaining == ["bsc"]
    assert rpay.rpay_available_networks() == ["bsc"]


async def test_valid_keys_all_survive(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay, ["bsc", "tron", "polygon"])
    _reset_verified(monkeypatch, rpay)

    async def fake_networks():
        return [
            {"key": "bsc", "status": "active"},
            {"key": "tron", "status": "active"},
            {"key": "polygon", "status": "active"},
            {"key": "base", "status": "active"},
        ]

    monkeypatch.setattr(rpay, "rpay_get_networks", fake_networks, raising=False)

    assert await rpay.rpay_verify_networks() == ["bsc", "tron", "polygon"]


async def test_an_inactive_network_is_not_offered(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay, ["bsc", "kava"])
    _reset_verified(monkeypatch, rpay)

    async def fake_networks():
        return [
            {"key": "bsc", "status": "active"},
            {"key": "kava", "status": "disabled"},
        ]

    monkeypatch.setattr(rpay, "rpay_get_networks", fake_networks, raising=False)

    assert await rpay.rpay_verify_networks() == ["bsc"]


async def test_a_failed_check_leaves_the_configuration_alone(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay, ["bsc", "tron"])
    _reset_verified(monkeypatch, rpay)

    async def boom():
        raise RuntimeError("network down")

    monkeypatch.setattr(rpay, "rpay_get_networks", boom, raising=False)

    # A blip reaching RPay at startup must not silently disable USDT checkout.
    assert await rpay.rpay_verify_networks() == ["bsc", "tron"]
    assert rpay.rpay_available_networks() == ["bsc", "tron"]


@pytest.mark.parametrize(
    "network, networks, expected",
    [
        # The singular name with a list in it. One missing "S" between the two
        # variable names used to send "bsc,tron,polygon" as a single network
        # name, and RPay answered HTTP 400 the moment a customer tried to pay.
        ("bsc,tron,polygon", "", ["bsc", "tron", "polygon"]),
        ("BSC, TRON ; Polygon", "", ["bsc", "tron", "polygon"]),
        # The plural name, as documented.
        ("", "bsc,tron,polygon", ["bsc", "tron", "polygon"]),
        # A genuine single network.
        ("bsc", "", ["bsc"]),
        # Plural wins when both are set.
        ("tron", "bsc,polygon", ["bsc", "polygon"]),
        ("", "", []),
    ],
)
def test_either_variable_name_accepts_a_list(monkeypatch, network, networks, expected):
    config = load_modules()["app.core.config_env"]
    monkeypatch.setenv("RPAY_NETWORK", network)
    monkeypatch.setenv("RPAY_NETWORKS", networks)

    resolved = config._split_rpay_networks(
        config.get_env_str("RPAY_NETWORKS", "")
    ) or config._split_rpay_networks(config.get_env_str("RPAY_NETWORK", ""))

    assert resolved == expected
    # The single-network default is the first entry, never the raw string.
    assert (resolved[0] if resolved else "") == (expected[0] if expected else "")
