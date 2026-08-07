from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.runtime_loader import load_modules


def test_extracts_configured_mbbank_account_and_masks_number():
    admin_api = load_modules()["app.handlers.admin_api"]
    response = {
        "acct_list": [
            {
                "acctNo": "0123456789",
                "acctNm": "DINO STORE",
                "ccyCd": "VND",
                "currentBalance": "1234567.00",
            }
        ]
    }

    result = admin_api._extract_mbbank_account_balance(response, "0123456789")

    assert result["current_balance"] == 1_234_567
    assert result["account_name"] == "DINO STORE"
    assert admin_api._mask_bank_account("0123456789") == "******6789"


@pytest.mark.asyncio
async def test_mbbank_balance_command_is_admin_only(monkeypatch):
    admin_api = load_modules()["app.handlers.admin_api"]

    def unexpected_fetch(*_args, **_kwargs):
        raise AssertionError("Non-admin must not call the bank API")

    monkeypatch.setattr(admin_api, "_fetch_mbbank_account_balance", unexpected_fetch)
    update = SimpleNamespace(effective_user=SimpleNamespace(id=admin_api.ADMIN_USER_ID + 1))

    await admin_api.sodumb_command(update, SimpleNamespace())


@pytest.mark.asyncio
async def test_admin_mbbank_balance_command_shows_masked_balance(monkeypatch):
    admin_api = load_modules()["app.handlers.admin_api"]
    edits = []

    class StatusMessage:
        async def edit_text(self, text, **kwargs):
            edits.append((text, kwargs))

    class AdminMessage:
        async def reply_text(self, *_args, **_kwargs):
            return StatusMessage()

    monkeypatch.setattr(admin_api, "BANK_ACCOUNT_NUMBER", "0123456789")
    monkeypatch.setattr(admin_api, "API_PASSWORD", "test-password")
    monkeypatch.setattr(admin_api, "BANK_API_TIMEOUT_SECONDS", 6.0)
    monkeypatch.setattr(
        admin_api,
        "_fetch_mbbank_account_balance",
        lambda *_args: {
            "account_no": "0123456789",
            "account_name": "DINO STORE",
            "currency": "VND",
            "current_balance": 1_234_567,
        },
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=admin_api.ADMIN_USER_ID),
        message=AdminMessage(),
    )

    await admin_api.sodumb_command(update, SimpleNamespace())

    assert len(edits) == 1
    assert "1,234,567 VND" in edits[0][0]
    assert "******6789" in edits[0][0]
    assert "0123456789" not in edits[0][0]
    assert edits[0][1]["parse_mode"] == admin_api.ParseMode.HTML
