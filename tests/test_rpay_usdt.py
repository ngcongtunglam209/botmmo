from decimal import Decimal

from app.core.runtime_loader import load_modules


def _load(force_reload: bool = False):
    modules = load_modules(force_reload=force_reload)
    return modules["app.integrations.rpay_api"], modules["app.integrations.payments_core"]


def _configure(monkeypatch, rpay, *, merchant="M123", api_key="secret-key"):
    monkeypatch.setattr(rpay, "RPAY_MERCHANT_ID", merchant, raising=False)
    monkeypatch.setattr(rpay, "RPAY_API_KEY", api_key, raising=False)
    monkeypatch.setattr(rpay, "ENABLE_PAYMENT_RPAY", True, raising=False)


def _pending(request_id: str, trans_id: str = "TX1", amount_vnd: int = 39900, amount_usdt: str = "1.52"):
    return {
        "provider": "rpay",
        "status": "pending_payment",
        "amount": amount_vnd,
        "rpay_request_id": request_id,
        "rpay_trans_id": trans_id,
        "rpay_amount": amount_usdt,
    }


def _callback(request_id: str, trans_id: str = "TX1", received: str = "1.52", status: str = "completed"):
    return {
        "merchant_id": "M123",
        "api_key": "secret-key",
        "request_id": request_id,
        "trans_id": trans_id,
        "status": status,
        "amount": "1.52",
        "received": received,
    }


def test_request_id_carries_order_code_and_a_secret():
    rpay, _ = _load()

    request_id = rpay.rpay_build_request_id("ICLD123456")

    assert request_id.startswith("ICLD123456:")
    assert rpay.rpay_order_code_from_request_id(request_id) == "ICLD123456"
    # The secret half is what actually authenticates the callback, so a second
    # invoice for the same order must not reuse it.
    assert request_id != rpay.rpay_build_request_id("ICLD123456")


def test_credentials_reject_wrong_key_and_missing_config(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay)

    assert rpay.rpay_verify_credentials(_callback("ICLD123456:abc")) is True
    assert rpay.rpay_verify_credentials({"merchant_id": "M123", "api_key": "wrong"}) is False
    assert rpay.rpay_verify_credentials({"merchant_id": "other", "api_key": "secret-key"}) is False

    monkeypatch.setattr(rpay, "RPAY_API_KEY", "", raising=False)
    assert rpay.rpay_verify_credentials(_callback("ICLD123456:abc")) is False


def test_completed_callback_credits_the_stored_vnd_amount(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay)
    request_id = "ICLD123456:deadbeef"
    monkeypatch.setattr(rpay, "pending_orders", {"ICLD123456": _pending(request_id)}, raising=False)
    monkeypatch.setattr(rpay, "RPAY_UNDERPAY_TOLERANCE", Decimal("0.01"), raising=False)

    normalized = rpay.rpay_normalize_completed_invoice(_callback(request_id))

    assert normalized == {
        "transactionID": "RPAYTX1",
        "description": "ICLD123456",
        # Taken from our own pending order, never from the callback body.
        "amount": 39900,
    }


def test_callback_with_a_forged_request_id_is_rejected(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay)
    monkeypatch.setattr(
        rpay, "pending_orders", {"ICLD123456": _pending("ICLD123456:deadbeef")}, raising=False
    )

    # Order codes are guessable (ICLD######); only the secret half is not.
    assert rpay.rpay_normalize_completed_invoice(_callback("ICLD123456:guessed")) is None
    # Right request_id but a trans_id that is not the one we created.
    assert rpay.rpay_normalize_completed_invoice(
        _callback("ICLD123456:deadbeef", trans_id="TX-OTHER")
    ) is None


def test_waiting_and_underpaid_invoices_are_not_credited(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay)
    request_id = "ICLD123456:deadbeef"
    monkeypatch.setattr(rpay, "pending_orders", {"ICLD123456": _pending(request_id)}, raising=False)
    monkeypatch.setattr(rpay, "RPAY_UNDERPAY_TOLERANCE", Decimal("0.01"), raising=False)

    assert rpay.rpay_normalize_completed_invoice(_callback(request_id, status="waiting")) is None
    assert rpay.rpay_normalize_completed_invoice(_callback(request_id, received="1.00")) is None
    # Within the network-fee tolerance the payment still counts.
    assert rpay.rpay_normalize_completed_invoice(_callback(request_id, received="1.51"))["amount"] == 39900


async def test_poll_falls_back_to_get_invoice_status(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay)
    request_id = "ICLD123456:deadbeef"
    monkeypatch.setattr(rpay, "pending_orders", {"ICLD123456": _pending(request_id)}, raising=False)
    monkeypatch.setattr(rpay, "db_check_tx_exists", lambda _tx_id: False, raising=False)
    monkeypatch.setattr(rpay, "RPAY_UNDERPAY_TOLERANCE", Decimal("0.01"), raising=False)

    async def fake_status(trans_id):
        assert trans_id == "TX1"
        return _callback(request_id)

    monkeypatch.setattr(rpay, "rpay_get_invoice_status", fake_status, raising=False)

    assert await rpay.rpay_poll_pending_invoices() == [{
        "transactionID": "RPAYTX1",
        "description": "ICLD123456",
        "amount": 39900,
    }]


def test_vnd_converts_up_so_the_shop_never_undercharges(monkeypatch):
    _, payments = _load()
    monkeypatch.setattr(payments, "USDT_DISPLAY_DECIMALS", 2, raising=False)

    # 39,900 / 26,000 = 1.5346... -> rounded up to 1.54, not down to 1.53.
    assert payments.convert_vnd_to_usdt(39_900, rate=Decimal("26000")) == Decimal("1.54")


def test_checkout_keyboard_exposes_payment_page_address_and_amount():
    _, payments = _load()

    keyboard = payments.build_rpay_checkout_keyboard(
        {
            "url_payment": "https://api.rpay.vn/invoice/usdt/TX1",
            "address": "0x83846bb147B4a07B81C99298E76e43416A18DC45",
            "amount_text": "1.54",
        },
        "ICLD123456",
    )

    assert keyboard.inline_keyboard[0][0].url == "https://api.rpay.vn/invoice/usdt/TX1"
    assert keyboard.inline_keyboard[1][0].copy_text.text == "0x83846bb147B4a07B81C99298E76e43416A18DC45"
    assert keyboard.inline_keyboard[2][0].copy_text.text == "1.54"
    assert keyboard.inline_keyboard[3][0].callback_data == "cancel_order:ICLD123456"


def test_qr_photo_decodes_the_base64_data_url():
    _, payments = _load()
    # 1x1 transparent PNG.
    png = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )

    stream = payments.rpay_qr_photo({"qrcode": f"data:image/png;base64,{png}"})

    # Telegram rejects data: URLs, so the base64 must be decoded to bytes.
    assert stream.getvalue().startswith(b"\x89PNG")


def test_qr_photo_falls_back_to_qr_content_when_rpay_omits_the_image():
    _, payments = _load()

    photo = payments.rpay_qr_photo({"qr_content": "0x8384 6bb1"})

    assert photo.startswith("https://api.qrserver.com/")
    assert "0x8384%206bb1" in photo


async def test_monitor_drains_the_callback_inbox(monkeypatch):
    modules = load_modules()
    monitor = modules["app.jobs.payment_monitor"]
    rpay = modules["app.integrations.rpay_api"]
    _configure(monkeypatch, rpay)

    queued = {"transactionID": "RPAYTX1", "description": "ICLD123456", "amount": 39900}
    monkeypatch.setattr(rpay, "rpay_callback_inbox", [queued], raising=False)
    monkeypatch.setattr(rpay, "pending_orders", {}, raising=False)

    synthetic_transactions = []
    status = await monitor._scan_rpay_payments(synthetic_transactions)

    assert synthetic_transactions == [queued]
    assert status == {"enabled": True, "ok": True, "error": "", "count": 1}
    # Drained, so the next cron pass does not replay it.
    assert rpay.rpay_callback_inbox == []


def _pending_topup(request_id: str, trans_id: str = "TXTOPUP", amount_vnd: int = 100000, amount_usdt: str = "3.85"):
    return {
        "provider": "rpay",
        "user_id": 555,
        "amount": amount_vnd,
        "rpay_request_id": request_id,
        "rpay_trans_id": trans_id,
        "rpay_amount": amount_usdt,
    }


def test_a_completed_callback_also_matches_a_wallet_topup(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay)
    request_id = "NAPU5551234:deadbeef"
    monkeypatch.setattr(rpay, "pending_orders", {}, raising=False)
    monkeypatch.setattr(rpay, "pending_user_topups", {"NAPU5551234": _pending_topup(request_id)}, raising=False)
    monkeypatch.setattr(rpay, "RPAY_UNDERPAY_TOLERANCE", Decimal("0.01"), raising=False)

    normalized = rpay.rpay_normalize_completed_invoice(
        _callback(request_id, trans_id="TXTOPUP", received="3.85")
    )

    # The NAPU code in the description is what routes this to credit_user_topup;
    # the VND figure comes from our own record, never from the callback.
    assert normalized == {
        "transactionID": "RPAYTXTOPUP",
        "description": "NAPU5551234",
        "amount": 100000,
    }


def test_a_topup_callback_with_the_wrong_secret_is_refused(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay)
    monkeypatch.setattr(rpay, "pending_orders", {}, raising=False)
    monkeypatch.setattr(
        rpay, "pending_user_topups", {"NAPU5551234": _pending_topup("NAPU5551234:deadbeef")}, raising=False
    )

    # The NAPU code is guessable; the random half is the only real proof.
    assert rpay.rpay_normalize_completed_invoice(_callback("NAPU5551234:guessed")) is None


def test_the_poll_covers_topups_as_well_as_orders(monkeypatch):
    rpay, _ = _load()
    _configure(monkeypatch, rpay)
    monkeypatch.setattr(rpay, "pending_orders", {"ICLD123456": _pending("ICLD123456:aaa", trans_id="TX1")}, raising=False)
    monkeypatch.setattr(
        rpay, "pending_user_topups", {"NAPU5551234": _pending_topup("NAPU5551234:bbb", trans_id="TX2")}, raising=False
    )

    seen = [code for code, _details in rpay.rpay_iter_pending_records()]

    # A top-up left out of the poll means a customer who paid after a missed
    # callback never gets credited.
    assert seen == ["ICLD123456", "NAPU5551234"]
