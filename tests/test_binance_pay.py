from decimal import Decimal

from app.core.runtime_loader import load_modules


def _load():
    modules = load_modules()
    return modules["app.integrations.binancepay_api"], modules["app.jobs.payment_monitor"]


def _configure(monkeypatch, binance, *, decimals=4, display_decimals=2):
    monkeypatch.setattr(binance, "ENABLE_PAYMENT_BINANCE_PAY", True, raising=False)
    monkeypatch.setattr(binance, "BINANCE_PAY_ID", "964569042", raising=False)
    monkeypatch.setattr(
        binance, "BINANCE_PAY_HISTORY_URL", "https://sieuthicode.example/historyapibinancev3/TOKEN", raising=False
    )
    monkeypatch.setattr(binance, "BINANCE_PAY_AMOUNT_DECIMALS", decimals, raising=False)
    monkeypatch.setattr(binance, "USDT_DISPLAY_DECIMALS", display_decimals, raising=False)


def _pending(amount_text: str, *, amount_vnd: int = 39900, created_ts: float = 1_800_000_000.0):
    return {
        "provider": "binance_pay",
        "status": "pending_payment",
        "amount": amount_vnd,
        "binance_pay_amount": amount_text,
        "timestamp": created_ts,
        "time": created_ts,
    }


def _feed_row(transaction_id: str, amount: str, timestamp_ms: int, *, tx_type: str = "IN"):
    return {
        "transactionID": transaction_id,
        "amount": amount,
        "description": "",
        "transactionDate": "2026-08-08",
        "timestamp": timestamp_ms,
        "type": tx_type,
        "currency": "USDT",
    }


def test_disabled_until_both_pay_id_and_feed_url_are_set(monkeypatch):
    binance, _ = _load()
    _configure(monkeypatch, binance)

    assert binance.is_binance_pay_enabled() is True

    monkeypatch.setattr(binance, "BINANCE_PAY_HISTORY_URL", "", raising=False)
    assert binance.is_binance_pay_enabled() is False


def test_each_order_gets_an_amount_no_other_pending_order_holds(monkeypatch):
    binance, _ = _load()
    _configure(monkeypatch, binance)
    monkeypatch.setattr(binance, "pending_orders", {}, raising=False)

    first_amount, first_text = binance.allocate_binance_pay_amount(Decimal("1.54"))
    assert first_text == "1.5400"

    binance.pending_orders["ICLD000001"] = _pending(first_text)
    second_amount, second_text = binance.allocate_binance_pay_amount(Decimal("1.54"))

    # Same price, different order: the amount is the only thing the feed lets us
    # match on, so it must not collide.
    assert second_text == "1.5401"
    assert second_amount > first_amount


def test_allocation_only_ever_rounds_up(monkeypatch):
    binance, _ = _load()
    _configure(monkeypatch, binance)
    monkeypatch.setattr(binance, "pending_orders", {}, raising=False)

    for taken in range(5):
        binance.pending_orders[f"ICLD00000{taken}"] = _pending(f"1.540{taken}")

    amount, text = binance.allocate_binance_pay_amount(Decimal("1.54"))

    assert text == "1.5405"
    # The customer is never asked for less than the quoted price.
    assert amount >= Decimal("1.54")


def test_allocation_refuses_rather_than_reusing_an_amount(monkeypatch):
    binance, _ = _load()
    # 3 decimals with 2 displayed leaves only 10 slots per price level.
    _configure(monkeypatch, binance, decimals=3)
    monkeypatch.setattr(binance, "pending_orders", {}, raising=False)

    for slot in range(10):
        binance.pending_orders[f"ICLD0000{slot}"] = _pending(f"1.54{slot}")

    try:
        binance.allocate_binance_pay_amount(Decimal("1.54"))
    except RuntimeError as exc:
        assert "Khong con so tien" in str(exc)
    else:
        raise AssertionError("expected RuntimeError instead of a duplicate amount")


def test_feed_amounts_are_truncated_not_rounded(monkeypatch):
    binance, _ = _load()
    _configure(monkeypatch, binance)

    # Rounding 1.54005 up to "1.5401" would match the order that asked for
    # 1.5401 even though this customer meant to pay 1.5400 — wrong buyer gets
    # the goods. Truncating sends it to manual reconciliation instead.
    assert binance.binance_pay_amount_text(Decimal("1.54005")) == "1.5400"
    assert binance.binance_pay_amount_text(Decimal("91.4817877")) == "91.4817"
    # Exact 4-decimal values are untouched.
    assert binance.binance_pay_amount_text(Decimal("1.5401")) == "1.5401"
    assert binance.binance_pay_amount_text(Decimal("1.54")) == "1.5400"


def test_feed_rows_that_are_not_incoming_usdt_are_dropped(monkeypatch):
    binance, _ = _load()
    _configure(monkeypatch, binance)

    assert binance.normalize_binance_pay_transaction(_feed_row("P_1", "1.5400", 1_800_000_000_000))["amount_text"] == "1.5400"
    assert binance.normalize_binance_pay_transaction(_feed_row("P_1", "1.54", 1, tx_type="OUT")) is None
    assert binance.normalize_binance_pay_transaction({**_feed_row("P_1", "1.54", 1), "currency": "BNB"}) is None
    assert binance.normalize_binance_pay_transaction(_feed_row("", "1.54", 1)) is None
    assert binance.normalize_binance_pay_transaction(_feed_row("P_1", "0", 1)) is None


async def test_scan_matches_a_pending_order_on_the_exact_amount(monkeypatch):
    binance, monitor = _load()
    _configure(monkeypatch, binance)
    created_ts = 1_800_000_000.0

    async def fake_snapshot():
        return [("ICLD123456", _pending("1.5401", created_ts=created_ts))]

    async def fake_fetch():
        return [
            binance.normalize_binance_pay_transaction(
                _feed_row("P_A23MQU1EGW971114", "1.5401", int(created_ts * 1000) + 30_000)
            ),
            # Someone else's transfer at a different amount, same window.
            binance.normalize_binance_pay_transaction(
                _feed_row("P_OTHER", "220.0000", int(created_ts * 1000) + 31_000)
            ),
        ]

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda _tx_id: False)
    monkeypatch.setattr(binance, "fetch_binance_pay_transactions", fake_fetch, raising=False)

    synthetic_transactions = []
    status = await monitor._scan_binance_pay_payments(synthetic_transactions)

    assert synthetic_transactions == [{
        "transactionID": "BINPAYP_A23MQU1EGW971114",
        "description": "ICLD123456",
        # VND figure comes from our pending order, never from the feed.
        "amount": 39900,
    }]
    assert status["count"] == 1


async def test_scan_ignores_a_transfer_that_is_off_by_one_ten_thousandth(monkeypatch):
    binance, monitor = _load()
    _configure(monkeypatch, binance)
    created_ts = 1_800_000_000.0

    async def fake_snapshot():
        return [("ICLD123456", _pending("1.5401", created_ts=created_ts))]

    async def fake_fetch():
        return [binance.normalize_binance_pay_transaction(
            _feed_row("P_1", "1.5402", int(created_ts * 1000) + 30_000)
        )]

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda _tx_id: False)
    monkeypatch.setattr(binance, "fetch_binance_pay_transactions", fake_fetch, raising=False)

    synthetic_transactions = []
    await monitor._scan_binance_pay_payments(synthetic_transactions)

    # 1.5402 belongs to some other order (or nobody). Crediting ICLD123456 for
    # it would hand the goods to the wrong customer.
    assert synthetic_transactions == []


async def test_scan_skips_both_orders_when_two_share_an_amount(monkeypatch):
    binance, monitor = _load()
    _configure(monkeypatch, binance)
    created_ts = 1_800_000_000.0

    async def fake_snapshot():
        return [
            ("ICLD111111", _pending("1.5401", created_ts=created_ts)),
            ("ICLD222222", _pending("1.5401", amount_vnd=41000, created_ts=created_ts)),
        ]

    async def fake_fetch():
        return [binance.normalize_binance_pay_transaction(
            _feed_row("P_1", "1.5401", int(created_ts * 1000) + 30_000)
        )]

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda _tx_id: False)
    monkeypatch.setattr(binance, "fetch_binance_pay_transactions", fake_fetch, raising=False)

    synthetic_transactions = []
    await monitor._scan_binance_pay_payments(synthetic_transactions)

    # Ambiguous: guessing has a 50% chance of delivering to the wrong buyer.
    assert synthetic_transactions == []


async def test_scan_ignores_transfers_outside_the_order_window(monkeypatch):
    binance, monitor = _load()
    _configure(monkeypatch, binance)
    monkeypatch.setattr(monitor, "BINANCE_PAY_MATCH_LEEWAY_SECONDS", 120, raising=False)
    monkeypatch.setattr(monitor, "ORDER_EXPIRATION_SECONDS", 600, raising=False)
    created_ts = 1_800_000_000.0
    created_ms = int(created_ts * 1000)

    async def fake_snapshot():
        return [("ICLD123456", _pending("1.5401", created_ts=created_ts))]

    async def fake_fetch():
        return [
            # An hour before the order existed - a coincidental old transfer.
            binance.normalize_binance_pay_transaction(_feed_row("P_OLD", "1.5401", created_ms - 3_600_000)),
            # Long after expiry.
            binance.normalize_binance_pay_transaction(_feed_row("P_LATE", "1.5401", created_ms + 3_600_000)),
        ]

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda _tx_id: False)
    monkeypatch.setattr(binance, "fetch_binance_pay_transactions", fake_fetch, raising=False)

    synthetic_transactions = []
    await monitor._scan_binance_pay_payments(synthetic_transactions)

    assert synthetic_transactions == []


async def test_scan_does_not_replay_an_already_credited_transfer(monkeypatch):
    binance, monitor = _load()
    _configure(monkeypatch, binance)
    created_ts = 1_800_000_000.0

    async def fake_snapshot():
        return [("ICLD123456", _pending("1.5401", created_ts=created_ts))]

    async def fake_fetch():
        return [binance.normalize_binance_pay_transaction(
            _feed_row("P_1", "1.5401", int(created_ts * 1000) + 30_000)
        )]

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda tx_id: tx_id == "BINPAYP_1")
    monkeypatch.setattr(binance, "fetch_binance_pay_transactions", fake_fetch, raising=False)

    synthetic_transactions = []
    await monitor._scan_binance_pay_payments(synthetic_transactions)

    # The feed keeps returning the last 40 transactions on every poll.
    assert synthetic_transactions == []


async def test_feed_failure_reports_unhealthy_without_leaking_the_token(monkeypatch):
    binance, monitor = _load()
    _configure(monkeypatch, binance)

    async def fake_snapshot():
        return [("ICLD123456", _pending("1.5401"))]

    async def fake_fetch():
        raise RuntimeError("HTTP 503")

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(binance, "fetch_binance_pay_transactions", fake_fetch, raising=False)

    synthetic_transactions = []
    status = await monitor._scan_binance_pay_payments(synthetic_transactions)

    assert status["ok"] is False
    assert synthetic_transactions == []
    assert "TOKEN" not in status["error"]


def _pending_topup(amount_text: str, *, amount_vnd: int = 100000, created_ts: float = 1_800_000_000.0):
    return {
        "provider": "binance_pay",
        "user_id": 555,
        "amount": amount_vnd,
        "binance_pay_amount": amount_text,
        "time": created_ts,
        "timestamp": created_ts,
    }


def test_a_wallet_topup_cannot_take_an_amount_an_order_already_holds(monkeypatch):
    binance, _ = _load()
    _configure(monkeypatch, binance)
    monkeypatch.setattr(binance, "pending_orders", {"ICLD000001": _pending("1.5400")}, raising=False)
    monkeypatch.setattr(binance, "pending_user_topups", {}, raising=False)

    # Orders and top-ups live in two different dictionaries but are reconciled
    # by the same amount lookup, so a shared amount would cross-credit them.
    _amount, text = binance.allocate_binance_pay_amount(Decimal("1.54"))
    assert text == "1.5401"

    binance.pending_user_topups["NAPU5551234"] = _pending_topup(text)
    _amount, next_text = binance.allocate_binance_pay_amount(Decimal("1.54"))
    assert next_text == "1.5402"


async def test_scan_matches_a_pending_wallet_topup(monkeypatch):
    binance, monitor = _load()
    _configure(monkeypatch, binance)
    created_ts = 1_800_000_000.0

    async def fake_snapshot():
        return []

    async def fake_fetch():
        return [binance.normalize_binance_pay_transaction(
            _feed_row("P_TOPUP1", "1.5401", int(created_ts * 1000) + 30_000)
        )]

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda _tx_id: False)
    monkeypatch.setattr(monitor, "pending_user_topups", {"NAPU5551234": _pending_topup("1.5401", created_ts=created_ts)}, raising=False)
    monkeypatch.setattr(binance, "fetch_binance_pay_transactions", fake_fetch, raising=False)

    synthetic_transactions = []
    await monitor._scan_binance_pay_payments(synthetic_transactions)

    # The description carries the NAPU code so check_payment_job routes it to
    # credit_user_topup, and the VND figure comes from our own record.
    assert synthetic_transactions == [{
        "transactionID": "BINPAYP_TOPUP1",
        "description": "NAPU5551234",
        "amount": 100000,
    }]


async def test_scan_skips_an_order_and_a_topup_that_share_an_amount(monkeypatch):
    binance, monitor = _load()
    _configure(monkeypatch, binance)
    created_ts = 1_800_000_000.0

    async def fake_snapshot():
        return [("ICLD123456", _pending("1.5401", created_ts=created_ts))]

    async def fake_fetch():
        return [binance.normalize_binance_pay_transaction(
            _feed_row("P_1", "1.5401", int(created_ts * 1000) + 30_000)
        )]

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda _tx_id: False)
    monkeypatch.setattr(monitor, "pending_user_topups", {"NAPU5551234": _pending_topup("1.5401", created_ts=created_ts)}, raising=False)
    monkeypatch.setattr(binance, "fetch_binance_pay_transactions", fake_fetch, raising=False)

    synthetic_transactions = []
    await monitor._scan_binance_pay_payments(synthetic_transactions)

    # Guessing between an order and a top-up means either shipping goods nobody
    # paid for or eating a wallet credit. Neither is worth the guess.
    assert synthetic_transactions == []


async def test_a_topup_outside_its_own_expiry_window_is_not_matched(monkeypatch):
    binance, monitor = _load()
    _configure(monkeypatch, binance)
    created_ts = 1_800_000_000.0

    async def fake_snapshot():
        return []

    async def fake_fetch():
        return [binance.normalize_binance_pay_transaction(
            _feed_row("P_LATE", "1.5401", int(created_ts * 1000) + 86_400_000)
        )]

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda _tx_id: False)
    monkeypatch.setattr(monitor, "pending_user_topups", {"NAPU5551234": _pending_topup("1.5401", created_ts=created_ts)}, raising=False)
    monkeypatch.setattr(binance, "fetch_binance_pay_transactions", fake_fetch, raising=False)

    synthetic_transactions = []
    await monitor._scan_binance_pay_payments(synthetic_transactions)

    assert synthetic_transactions == []
