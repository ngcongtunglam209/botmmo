from app.core.runtime_loader import load_modules


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _Client:
    is_closed = False

    def __init__(self):
        self.requests = []

    async def post(self, _url, *, json, headers):
        self.requests.append(json)
        method = json["method"]
        if method == "eth_blockNumber":
            result = "0x2710"
        elif method == "eth_getLogs":
            result = [{
                "transactionHash": "0xabc123",
                "blockNumber": "0x270b",
                "data": hex(1_234_567_000_000_000_000),
            }]
        elif method == "eth_getBlockByNumber":
            result = {"timestamp": hex(1_700_000_000)}
        else:
            raise AssertionError(f"Unexpected RPC method: {method}")
        return _Response({"jsonrpc": "2.0", "id": 1, "result": result})


async def test_bep20_transfer_amount_is_normalized(monkeypatch):
    payments = load_modules()["app.integrations.payments_core"]
    client = _Client()
    monkeypatch.setattr(payments, "http_client", client)

    transfers = await payments.fetch_usdt_bep20_transfers(
        "0xe38e7a58c86543d32ce799ef852d68e71ac924e8",
        max_pages=1,
    )

    assert transfers[0]["amount_display"] == "1.234567"
    logs_request = next(request for request in client.requests if request["method"] == "eth_getLogs")
    assert logs_request["params"][0]["address"].lower() == "0x55d398326f99059ff775485246999027b3197955"
    assert logs_request["params"][0]["topics"][2].endswith("e38e7a58c86543d32ce799ef852d68e71ac924e8")


def test_checkout_keyboard_copies_binance_id_and_bep20_wallet(monkeypatch):
    payments = load_modules()["app.integrations.payments_core"]
    monkeypatch.setattr(payments, "BINANCE_PAY_ID", "964569042")

    keyboard = payments.build_usdt_trc20_checkout_keyboard(
        "ICLD123456",
        "0xe38e7a58c86543d32ce799ef852d68e71ac924e8",
    )

    assert keyboard.inline_keyboard[0][0].copy_text.text == "964569042"
    assert keyboard.inline_keyboard[1][0].copy_text.text == "0xe38e7a58c86543d32ce799ef852d68e71ac924e8"
    assert keyboard.inline_keyboard[2][0].callback_data == "cancel_order:ICLD123456"


async def test_binance_spot_scan_accepts_usdt_multi_provider(monkeypatch):
    modules = load_modules(force_reload=True)
    monitor = modules["app.jobs.payment_monitor"]
    payments = modules["app.integrations.payments_core"]

    async def fake_pending_items_snapshot():
        return [(
            "ICLD038261",
            {
                "provider": "usdt_multi",
                "status": "pending_payment",
                "amount": 39900,
                "timestamp": 1_700_000_000,
                "usdt_trc20_amount": "1.513",
                "usdt_trc20_amount_quant": "1513000000000000000",
            },
        )]

    async def fake_fetch_binance_spot_deposits(start_timestamp_ms=0):
        return [{
            "status": 1,
            "txId": "396264090756",
            "amount": "1.51300000",
            "coin": "USDT",
            "insertTime": 1_700_000_030_000,
        }]

    monkeypatch.setattr(monitor, "pending_items_snapshot", fake_pending_items_snapshot)
    monkeypatch.setattr(monitor, "db_check_tx_exists", lambda _tx_id: False)
    monkeypatch.setattr(payments, "is_binance_spot_enabled", lambda: True)
    monkeypatch.setattr(payments, "fetch_binance_spot_deposits", fake_fetch_binance_spot_deposits)

    synthetic_transactions = []
    await monitor._scan_binance_spot_payments(synthetic_transactions)

    assert synthetic_transactions == [{
        "transactionID": "BINSPOT:396264090756",
        "description": "ICLD038261",
        "amount": 39900,
    }]
