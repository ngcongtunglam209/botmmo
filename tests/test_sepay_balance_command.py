from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.runtime_loader import load_modules


def test_extracts_configured_sepay_account_and_masks_number():
    admin_api = load_modules()["app.handlers.admin_api"]
    sepay_api = load_modules()["app.integrations.sepay_api"]
    payload = {
        "status": 200,
        "bankaccounts": [
            {
                "id": "1",
                "account_number": "0123456789",
                "account_holder_name": "DINO STORE",
                "bank_short_name": "MBBank",
                "accumulated": "1234567",
            }
        ],
    }

    result = sepay_api.sepay_extract_account_balance(payload, "0123456789")

    assert result["current_balance"] == 1_234_567
    assert result["account_name"] == "DINO STORE"
    assert admin_api._mask_bank_account("0123456789") == "******6789"


def test_extractor_skips_accounts_that_do_not_match():
    sepay_api = load_modules()["app.integrations.sepay_api"]
    payload = {"bankaccounts": [{"account_number": "9999999999", "accumulated": "1000"}]}

    assert sepay_api.sepay_extract_account_balance(payload, "0123456789") is None


@pytest.mark.asyncio
async def test_sepay_balance_command_is_admin_only(monkeypatch):
    admin_api = load_modules()["app.handlers.admin_api"]
    sepay_api = load_modules()["app.integrations.sepay_api"]

    async def unexpected_fetch(*_args, **_kwargs):
        raise AssertionError("Non-admin must not call the bank API")

    monkeypatch.setattr(sepay_api, "sepay_fetch_account_balance", unexpected_fetch)
    update = SimpleNamespace(effective_user=SimpleNamespace(id=admin_api.ADMIN_USER_ID + 1))

    await admin_api.sodumb_command(update, SimpleNamespace())


@pytest.mark.asyncio
async def test_admin_sepay_balance_command_shows_masked_balance(monkeypatch):
    admin_api = load_modules()["app.handlers.admin_api"]
    sepay_api = load_modules()["app.integrations.sepay_api"]
    edits = []

    class StatusMessage:
        async def edit_text(self, text, **kwargs):
            edits.append((text, kwargs))

    class AdminMessage:
        async def reply_text(self, *_args, **_kwargs):
            return StatusMessage()

    monkeypatch.setattr(admin_api, "SEPAY_ACCOUNT_NUMBER", "0123456789")
    monkeypatch.setattr(admin_api, "SEPAY_API_TOKEN", "test-token")
    monkeypatch.setattr(admin_api, "BANK_API_TIMEOUT_SECONDS", 6.0)

    async def fake_fetch(account_no=None):
        assert account_no == "0123456789"
        return {
            "account_no": "0123456789",
            "account_name": "DINO STORE",
            "bank": "MBBank",
            "currency": "VND",
            "current_balance": 1_234_567,
        }

    monkeypatch.setattr(sepay_api, "sepay_fetch_account_balance", fake_fetch)
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


@pytest.mark.asyncio
async def test_sepay_balance_command_without_token_reports_config_error(monkeypatch):
    admin_api = load_modules()["app.handlers.admin_api"]
    replies = []

    class AdminMessage:
        async def reply_text(self, text, *_args, **_kwargs):
            replies.append(text)

    monkeypatch.setattr(admin_api, "SEPAY_API_TOKEN", "")
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=admin_api.ADMIN_USER_ID),
        message=AdminMessage(),
    )

    await admin_api.sodumb_command(update, SimpleNamespace())

    assert replies == ["❌ Chưa cấu hình SEPAY_API_TOKEN."]
