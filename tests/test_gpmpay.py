import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.core.runtime_loader import load_modules

SECRET = "whsec_test_value"


def _gpm(monkeypatch):
    gpm = load_modules()["app.integrations.gpmpay_api"]
    monkeypatch.setattr(gpm, "GPMPAY_WEBHOOK_SECRET", SECRET, raising=False)
    return gpm


def _sign(raw: bytes, t: int | None = None, secret: str = SECRET) -> str:
    t = int(time.time()) if t is None else t
    v1 = hmac.new(secret.encode(), f"{t}.".encode() + raw, hashlib.sha256).hexdigest()
    return f"t={t},v1={v1}"


def _payload(**overrides):
    """Payload webhook mau trong docs.gpmpay.com/webhook."""
    body = {
        "id": "f68120ba-c60a-433a-a7af-3746a4eec807",
        "gateway": "VCB",
        "transactionDate": "2026-04-22T03:35:50.306Z",
        "accountNumber": "0123456789",
        "subAccount": None,
        "content": "Thanh toan ICLD123456",
        "description": "Thanh toan ICLD123456",
        "transferType": "in",
        "transferAmount": 100000,
        "accumulated": None,
        "referenceCode": "FT24xxxxxxx",
        "source": "REAL",
    }
    body.update(overrides)
    return body


def test_signature_accepts_valid_and_rejects_tampered_stale_or_unconfigured(monkeypatch):
    gpm = _gpm(monkeypatch)
    raw = json.dumps(_payload()).encode()

    assert gpm.gpmpay_verify_signature(raw, _sign(raw))
    assert not gpm.gpmpay_verify_signature(raw + b" ", _sign(raw))
    assert not gpm.gpmpay_verify_signature(raw, _sign(raw, secret="other"))
    assert not gpm.gpmpay_verify_signature(raw, _sign(raw, t=int(time.time()) - 301))
    assert not gpm.gpmpay_verify_signature(raw, None)
    assert not gpm.gpmpay_verify_signature(raw, "t=abc,v1=00")

    monkeypatch.setattr(gpm, "GPMPAY_WEBHOOK_SECRET", "", raising=False)
    assert not gpm.gpmpay_verify_signature(raw, _sign(raw))


def test_normalize_only_keeps_real_incoming_transfers(monkeypatch):
    gpm = _gpm(monkeypatch)

    assert gpm.gpmpay_normalize_webhook_payload(_payload()) == {
        "transactionID": "GPMf68120ba-c60a-433a-a7af-3746a4eec807",
        "description": "Thanh toan ICLD123456",
        "amount": 100000,
    }
    # Goi tin xac minh khi tao/sua webhook: 1 VND, SIMULATED, test=true.
    assert gpm.gpmpay_normalize_webhook_payload(_payload(test=True)) is None
    assert gpm.gpmpay_normalize_webhook_payload(_payload(transferType="out")) is None
    assert gpm.gpmpay_normalize_webhook_payload(_payload(source="SIMULATED")) is None
    assert gpm.gpmpay_normalize_webhook_payload(_payload(transferAmount=0)) is None


def test_poll_page_parses_string_amounts_and_skips_simulated(monkeypatch):
    gpm = _gpm(monkeypatch)
    tx = {
        "id": "abc", "type": "IN", "source": "REAL", "amount": "100000",
        "transferContent": "Thanh toan ICLD123456",
    }
    payload = {"statusCode": 200, "data": {
        "data": [tx, {**tx, "id": "sim", "source": "SIMULATED"}, {**tx, "id": "out", "type": "OUT"}],
        "meta": {"page": 1, "limit": 50, "totalItems": 3, "totalPages": 2},
    }}

    items, total_pages = gpm.gpmpay_parse_transactions_page(payload)
    assert items == [{"transactionID": "GPMabc", "description": "Thanh toan ICLD123456", "amount": 100000}]
    assert total_pages == 2
    assert gpm.gpmpay_parse_transactions_page(None) == ([], 0)


@pytest.fixture()
def client(monkeypatch):
    modules = load_modules()
    modules["app.database.storage"].init_db()
    gpm = _gpm(monkeypatch)
    monkeypatch.setattr(modules["app.core.config_env"], "ENABLE_PAYMENT_GPMPAY", True, raising=False)
    gpm.gpmpay_webhook_inbox.clear()
    try:
        yield TestClient(modules["app.models.api_models"].app), gpm.gpmpay_webhook_inbox
    finally:
        gpm.gpmpay_webhook_inbox.clear()


def _post(api, body: dict, signature: str | None = None):
    raw = json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "X-GPMPay-Signature": signature or _sign(raw)}
    return api.post("/webhook/gpmpay", content=raw, headers=headers)


def test_webhook_queues_signed_payment(client):
    api, inbox = client
    response = _post(api, _payload())
    assert response.status_code == 200
    assert [tx["transactionID"] for tx in inbox] == ["GPMf68120ba-c60a-433a-a7af-3746a4eec807"]


def test_webhook_rejects_bad_signature(client):
    api, inbox = client
    assert _post(api, _payload(), signature="t=1,v1=deadbeef").status_code == 401
    assert inbox == []


def test_webhook_verification_ping_gets_2xx_without_queueing(client):
    # GPM Pay chi luu cau hinh webhook khi ping nay nhan 2xx trong 5 giay.
    api, inbox = client
    response = _post(api, _payload(id="00000000-0000-0000-0000-000000000000", transferAmount=1,
                                   source="SIMULATED", test=True))
    assert response.status_code == 200
    assert inbox == []
