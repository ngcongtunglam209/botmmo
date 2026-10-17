import hashlib
import hmac
import json
from decimal import Decimal

from app.core.runtime_loader import load_modules

IPN_SECRET = "ipn_secret_value"


def _load():
    modules = load_modules()
    return modules["app.integrations.nowpayments_api"], modules["app.jobs.payment_monitor"]


def _configure(monkeypatch, np, *, tolerance="0.01"):
    monkeypatch.setattr(np, "ENABLE_PAYMENT_NOWPAYMENTS", True, raising=False)
    monkeypatch.setattr(np, "NOWPAYMENTS_API_KEY", "KEY123", raising=False)
    monkeypatch.setattr(np, "NOWPAYMENTS_IPN_SECRET", IPN_SECRET, raising=False)
    monkeypatch.setattr(np, "NOWPAYMENTS_CURRENCIES", ["usdtbsc", "usdtmatic"], raising=False)
    monkeypatch.setattr(np, "NOWPAYMENTS_BASE_URL", "https://api.nowpayments.io/v1", raising=False)
    monkeypatch.setattr(np, "NOWPAYMENTS_UNDERPAY_TOLERANCE", Decimal(tolerance), raising=False)


def _ipn(order_id="ICLD123456", **overrides):
    """A payload shaped like a real NOWPayments IPN."""
    body = {
        "payment_id": 5745459419,
        "parent_payment_id": None,
        "invoice_id": None,
        "payment_status": "finished",
        "pay_address": "0xabc",
        "payin_extra_id": None,
        "price_amount": 1.54,
        "price_currency": "usdtbsc",
        "pay_amount": 1.54,
        "actually_paid": 1.54,
        "pay_currency": "usdtbsc",
        "order_id": order_id,
        "order_description": f"Order {order_id}",
        "purchase_id": "6094705802",
        "outcome_amount": 1.53,
        "outcome_currency": "usdtbsc",
        "fee": {"currency": "usdtbsc", "depositFee": 0.01, "withdrawalFee": 0, "serviceFee": 0},
    }
    body.update(overrides)
    return body


def _sign(np, body, secret=IPN_SECRET):
    return hmac.new(
        secret.encode(),
        np.nowpayments_canonical_payload(body).encode(),
        hashlib.sha512,
    ).hexdigest()


def _pending(amount_vnd=39900, payment_id="5745459419"):
    return {
        "provider": "nowpayments",
        "status": "pending_payment",
        "amount": amount_vnd,
        "nowpayments_payment_id": payment_id,
    }


def test_disabled_until_key_secret_and_currencies_are_all_set(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)

    assert np.is_nowpayments_enabled() is True

    # No IPN secret means every callback gets rejected while the button stays
    # live — customers pay into orders that can never be credited.
    monkeypatch.setattr(np, "NOWPAYMENTS_IPN_SECRET", "", raising=False)
    assert np.is_nowpayments_enabled() is False

    monkeypatch.setattr(np, "NOWPAYMENTS_IPN_SECRET", IPN_SECRET, raising=False)
    monkeypatch.setattr(np, "NOWPAYMENTS_CURRENCIES", [], raising=False)
    assert np.is_nowpayments_enabled() is False


def test_canonical_payload_has_no_spaces_and_sorts_nested_keys(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)

    payload = np.nowpayments_canonical_payload({"b": 1, "a": {"z": 2, "y": 3}})

    # json.dumps defaults to ", " and ": " separators, which produces a totally
    # different string from the one NOWPayments signed.
    assert payload == '{"a":{"y":3,"z":2},"b":1}'
    assert " " not in payload


def test_a_valid_signature_is_accepted_and_a_tampered_body_is_not(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)
    body = _ipn()
    signature = _sign(np, body)

    assert np.nowpayments_verify_signature(body, signature) is True

    # Raising the amount after signing is the whole attack.
    tampered = {**body, "actually_paid": 999.0}
    assert np.nowpayments_verify_signature(tampered, signature) is False
    assert np.nowpayments_verify_signature(body, None) is False
    assert np.nowpayments_verify_signature(body, "deadbeef") is False


def test_a_signature_from_a_different_secret_is_rejected(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)
    body = _ipn()

    assert np.nowpayments_verify_signature(body, _sign(np, body, "wrong_secret")) is False


def test_no_secret_configured_rejects_every_callback(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)
    monkeypatch.setattr(np, "NOWPAYMENTS_IPN_SECRET", "", raising=False)
    body = _ipn()

    # Fail closed: an unauthenticated credit endpoint is worse than a missed one.
    assert np.nowpayments_verify_signature(body, _sign(np, body)) is False


def test_a_finished_payment_normalizes(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)

    record = np.nowpayments_normalize_payment(_ipn())

    assert record["transaction_ref"] == "NOWPAY5745459419"
    assert record["order_code"] == "ICLD123456"
    assert record["actually_paid"] == Decimal("1.54")


def test_a_redeposit_is_never_credited_automatically(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)

    # NOWPayments marks re-deposits "finished" too, and their own docs say not
    # to ship goods on that status: the total may be short of what was owed.
    assert np.nowpayments_normalize_payment(_ipn(parent_payment_id=1234567890)) is None
    assert np.nowpayments_normalize_payment(_ipn(parent_payment_id="1234567890")) is None


def test_an_unfinished_payment_is_not_credited(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)

    for status in ("waiting", "confirming", "confirmed", "sending", "partially_paid", "failed", "expired", "refunded"):
        assert np.nowpayments_normalize_payment(_ipn(payment_status=status)) is None


def test_a_short_payment_is_not_credited_even_when_marked_finished(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)

    # A wrong-asset deposit converted at the current rate can land as "finished"
    # while actually_paid falls short. Trusting the status alone ships goods.
    assert np.nowpayments_normalize_payment(_ipn(pay_amount=1.54, actually_paid=1.20)) is None
    # Within tolerance: network fees shaving a cent off is not underpayment.
    assert np.nowpayments_normalize_payment(_ipn(pay_amount=1.54, actually_paid=1.535)) is not None


def test_a_payment_without_an_order_id_is_dropped(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)

    assert np.nowpayments_normalize_payment(_ipn(order_id="")) is None
    assert np.nowpayments_normalize_payment(_ipn(order_id=None)) is None


async def test_scan_credits_the_vnd_from_our_own_pending_order(monkeypatch):
    np, monitor = _load()
    _configure(monkeypatch, np)

    async def fake_snapshot():
        return [("ICLD123456", _pending(amount_vnd=39900))]

    async def fake_poll():
        return []

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda _tx_id: False)
    monkeypatch.setattr(monitor, "pending_user_topups", {}, raising=False)
    monkeypatch.setattr(np, "nowpayments_poll_pending_payments", fake_poll, raising=False)
    np.nowpayments_ipn_inbox[:] = [np.nowpayments_normalize_payment(_ipn())]

    synthetic_transactions = []
    status = await monitor._scan_nowpayments_payments(synthetic_transactions)

    assert synthetic_transactions == [{
        "transactionID": "NOWPAY5745459419",
        "description": "ICLD123456",
        # VND comes from our record; the payload only says "enough USDT arrived".
        "amount": 39900,
    }]
    assert status["count"] == 1
    assert np.nowpayments_ipn_inbox == []


async def test_scan_ignores_a_payment_for_an_order_that_is_no_longer_pending(monkeypatch):
    np, monitor = _load()
    _configure(monkeypatch, np)

    async def fake_snapshot():
        return []

    async def fake_poll():
        return []

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda _tx_id: False)
    monkeypatch.setattr(monitor, "pending_user_topups", {}, raising=False)
    monkeypatch.setattr(np, "nowpayments_poll_pending_payments", fake_poll, raising=False)
    np.nowpayments_ipn_inbox[:] = [np.nowpayments_normalize_payment(_ipn())]

    synthetic_transactions = []
    await monitor._scan_nowpayments_payments(synthetic_transactions)

    # Expired or already-credited. Guessing the VND from the payload is how a
    # cancelled order gets delivered anyway.
    assert synthetic_transactions == []


async def test_scan_does_not_credit_the_same_payment_twice(monkeypatch):
    np, monitor = _load()
    _configure(monkeypatch, np)

    async def fake_snapshot():
        return [("ICLD123456", _pending())]

    async def fake_poll():
        return [np.nowpayments_normalize_payment(_ipn())]

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda tx_id: tx_id == "NOWPAY5745459419")
    monkeypatch.setattr(monitor, "pending_user_topups", {}, raising=False)
    monkeypatch.setattr(np, "nowpayments_poll_pending_payments", fake_poll, raising=False)
    np.nowpayments_ipn_inbox[:] = [np.nowpayments_normalize_payment(_ipn())]

    synthetic_transactions = []
    await monitor._scan_nowpayments_payments(synthetic_transactions)

    # IPN and the fallback poll both surface the same payment every round.
    assert synthetic_transactions == []


async def test_scan_credits_a_wallet_topup(monkeypatch):
    np, monitor = _load()
    _configure(monkeypatch, np)

    async def fake_snapshot():
        return []

    async def fake_poll():
        return []

    topup = {"provider": "nowpayments", "user_id": 555, "amount": 100000, "nowpayments_payment_id": "5745459419"}
    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda _tx_id: False)
    monkeypatch.setattr(monitor, "pending_user_topups", {"NAPU5551234": topup}, raising=False)
    monkeypatch.setattr(np, "nowpayments_poll_pending_payments", fake_poll, raising=False)
    np.nowpayments_ipn_inbox[:] = [np.nowpayments_normalize_payment(_ipn(order_id="NAPU5551234"))]

    synthetic_transactions = []
    await monitor._scan_nowpayments_payments(synthetic_transactions)

    assert synthetic_transactions == [{
        "transactionID": "NOWPAY5745459419",
        "description": "NAPU5551234",
        "amount": 100000,
    }]


async def test_a_poll_failure_reports_unhealthy_without_losing_the_inbox_credit(monkeypatch):
    np, monitor = _load()
    _configure(monkeypatch, np)

    async def fake_snapshot():
        return [("ICLD123456", _pending())]

    async def fake_poll():
        raise RuntimeError("HTTP 503")

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda _tx_id: False)
    monkeypatch.setattr(monitor, "pending_user_topups", {}, raising=False)
    monkeypatch.setattr(np, "nowpayments_poll_pending_payments", fake_poll, raising=False)
    np.nowpayments_ipn_inbox[:] = [np.nowpayments_normalize_payment(_ipn())]

    synthetic_transactions = []
    status = await monitor._scan_nowpayments_payments(synthetic_transactions)

    # The fallback dying must not swallow a payment the webhook already proved.
    assert status["ok"] is False
    assert len(synthetic_transactions) == 1


def test_the_real_ipn_example_from_the_docs_round_trips(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)

    # Verbatim from the NOWPayments docs, including the null fields, so a change
    # to the canonicalisation shows up here rather than in production.
    body = json.loads(
        '{"payment_id":123456789,"parent_payment_id":null,"invoice_id":null,'
        '"payment_status":"finished","pay_address":"address","payin_extra_id":null,'
        '"price_amount":1,"price_currency":"usd","pay_amount":15,"actually_paid":15,'
        '"actually_paid_at_fiat":0,"pay_currency":"trx","order_id":"ICLD999999",'
        '"order_description":null,"purchase_id":"123456789","outcome_amount":14.8106,'
        '"outcome_currency":"trx","payment_extra_ids":null,'
        '"fee":{"currency":"btc","depositFee":0.098,"withdrawalFee":0,"serviceFee":0}}'
    )

    assert np.nowpayments_verify_signature(body, _sign(np, body)) is True
    assert np.nowpayments_normalize_payment(body)["transaction_ref"] == "NOWPAY123456789"


def _install_min_amounts(monkeypatch, np, table, calls=None):
    """Fake the /min-amount endpoint; `table` maps currency -> min USDT string."""
    monkeypatch.setattr(np, "NOWPAYMENTS_CURRENCIES", ["usdtbsc", "usdtmatic", "usdttrc20"], raising=False)
    monkeypatch.setattr(np, "NOWPAYMENTS_PAYOUT_CURRENCY", "", raising=False)

    async def fake_request(method, path, payload=None):
        currency = path.split("currency_from=")[1].split("&")[0]
        if calls is not None:
            calls.append(currency)
        if currency not in table:
            raise RuntimeError("HTTP 400")
        return {"min_amount": table[currency]}

    monkeypatch.setattr(np, "_nowpayments_request", fake_request, raising=False)
    np._nowpayments_min_amount_cache.clear()


async def test_a_network_whose_floor_is_above_the_order_is_hidden(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)
    _install_min_amounts(monkeypatch, np, {
        "usdtbsc": "0.0569726",
        "usdtmatic": "0.140639",
        "usdttrc20": "11.40939",
    })

    # A 1.54 USDT order cannot be paid over TRON: NOWPayments rejects anything
    # under its floor, so offering the button guarantees a dead invoice.
    assert await np.nowpayments_currencies_for_amount(Decimal("1.54")) == ["usdtbsc", "usdtmatic"]
    # A big order can use all three.
    assert await np.nowpayments_currencies_for_amount(Decimal("50")) == ["usdtbsc", "usdtmatic", "usdttrc20"]
    # Exactly on the floor is allowed.
    assert "usdttrc20" in await np.nowpayments_currencies_for_amount(Decimal("11.40939"))


async def test_a_min_amount_lookup_failure_keeps_the_network_visible(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)
    _install_min_amounts(monkeypatch, np, {"usdtbsc": "0.05"})

    # usdtmatic/usdttrc20 raise here. Silently dropping payment methods over a
    # transient network blip is worse than letting NOWPayments reject later.
    assert await np.nowpayments_currencies_for_amount(Decimal("1.54")) == ["usdtbsc", "usdtmatic", "usdttrc20"]


async def test_min_amounts_are_cached_per_currency(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)
    calls = []
    _install_min_amounts(monkeypatch, np, {"usdtbsc": "0.05", "usdtmatic": "0.14", "usdttrc20": "11.4"}, calls)

    await np.nowpayments_currencies_for_amount(Decimal("50"))
    await np.nowpayments_currencies_for_amount(Decimal("50"))

    # The floor moves with network fees, not per order — one lookup per currency
    # per cache window, not one per checkout.
    assert sorted(calls) == ["usdtbsc", "usdtmatic", "usdttrc20"]


# --- "Other coin": hosted NOWPayments invoice -------------------------------


def test_the_invoice_choice_needs_a_reachable_ipn_url(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)

    # Without IPN the invoice's payment_id is never learned, so polling would be
    # blind and the order could only be credited by hand. Hide the button.
    monkeypatch.setattr(np, "PUBLIC_API_URL", "", raising=False)
    assert np.nowpayments_invoice_available() is False

    monkeypatch.setattr(np, "PUBLIC_API_URL", "https://shop.example", raising=False)
    assert np.nowpayments_invoice_available() is True


async def test_the_invoice_choice_creates_a_hosted_invoice_priced_in_usdt(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)
    monkeypatch.setattr(np, "PUBLIC_API_URL", "https://shop.example/", raising=False)
    monkeypatch.setattr(np, "NOWPAYMENTS_PAYOUT_CURRENCY", "", raising=False)

    import sys
    core = sys.modules["app.integrations.payments_core"]

    async def fake_rate():
        return Decimal("26000")

    monkeypatch.setattr(core, "get_live_usdt_vnd_rate", fake_rate)

    calls = []

    async def fake_request(method, path, payload=None):
        calls.append((method, path, payload))
        return {"id": 4522625843, "invoice_url": "https://nowpayments.io/payment/?iid=4522625843"}

    monkeypatch.setattr(np, "_nowpayments_request", fake_request)

    payment = await np.create_nowpayments_payment("ICLD123456", 39900, np.NOWPAYMENTS_INVOICE_CHOICE)

    method, path, payload = calls[0]
    assert (method, path) == ("POST", "/invoice")
    # Priced in the same USDT ticker the fixed-network buttons use, so the
    # number the customer saw in the bot is the number on the invoice page.
    assert payload["price_currency"] == "usdtbsc"
    assert payload["order_id"] == "ICLD123456"
    assert payload["ipn_callback_url"] == "https://shop.example/webhook/nowpayments"
    assert Decimal(str(payload["price_amount"])) >= Decimal("39900") / Decimal("26000")

    assert payment["invoice_url"] == "https://nowpayments.io/payment/?iid=4522625843"
    assert payment["invoice_id"] == "4522625843"
    assert payment["pay_currency"] == "any"
    # No address and no payment_id yet: both only exist once the customer picks
    # a coin on the hosted page.
    assert payment["pay_address"] == ""
    assert payment["payment_id"] == ""


def test_the_first_ipn_of_an_invoice_order_fills_in_the_payment_id_for_polling(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np)
    record = {"provider": "nowpayments", "status": "pending_payment", "amount": 39900, "nowpayments_payment_id": ""}
    monkeypatch.setattr(np, "pending_orders", {"ICLD123456": record}, raising=False)
    monkeypatch.setattr(np, "pending_user_topups", {}, raising=False)

    # The very first callback is usually "waiting" — not creditable, but it is
    # the only moment we learn which payment belongs to this invoice.
    waiting = _ipn(payment_status="waiting", pay_currency="ltc", actually_paid=0)
    assert np.nowpayments_remember_payment_id(waiting) is True
    assert record["nowpayments_payment_id"] == "5745459419"
    assert record["nowpayments_currency"] == "ltc"

    # A later payment for the same order (e.g. a re-deposit) must not hijack it.
    assert np.nowpayments_remember_payment_id(_ipn(payment_id=999, pay_currency="btc")) is False
    assert record["nowpayments_payment_id"] == "5745459419"

    # Orders that already carry a payment_id (fixed-network flow) are untouched.
    assert np.nowpayments_remember_payment_id(_ipn(order_id="OTHER")) is False


def test_the_underpay_tolerance_only_applies_to_stablecoins(monkeypatch):
    np, _ = _load()
    _configure(monkeypatch, np, tolerance="0.01")

    # 0.01 USDT is a network-fee rounding. 0.01 BTC is a car. Any coin the
    # customer can pick on the invoice page must be paid in full.
    assert np.nowpayments_normalize_payment(_ipn(pay_currency="usdtbsc", pay_amount=1.54, actually_paid=1.535)) is not None
    assert np.nowpayments_normalize_payment(_ipn(pay_currency="btc", pay_amount=0.0010, actually_paid=0.0009)) is None
    assert np.nowpayments_normalize_payment(_ipn(pay_currency="btc", pay_amount=0.0010, actually_paid=0.0010)) is not None
