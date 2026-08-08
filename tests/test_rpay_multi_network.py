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
