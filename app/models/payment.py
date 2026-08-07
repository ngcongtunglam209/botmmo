"""Payment and withdrawal data models."""

from __future__ import annotations

import enum
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PaymentMethod(str, enum.Enum):
    """Supported payment methods."""

    BANK_TRANSFER = "bank_transfer"
    BINANCE_PAY = "binance_pay"
    USDT_TRC20 = "usdt_trc20"
    USDT_BEP20 = "usdt_bep20"
    BALANCE = "balance"  # Full balance payment, no external transfer


class WithdrawalStatus(str, enum.Enum):
    """Withdrawal request lifecycle states."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class PendingPayment(BaseModel):
    """Tracks a pending API partner deposit waiting for bank confirmation."""

    reference: str = Field("", description="Transfer reference code (e.g. NAPI12345)")
    user_id: int = Field(0, description="Partner's Telegram user ID")
    api_key: str = Field("", description="Partner API key")
    partner_name: str = Field("", description="Partner display name")
    amount: int = Field(0, ge=0, description="Expected deposit amount in VND")
    time: float = Field(default_factory=time.time)
    transfer_content: str = Field("", description="Expected transfer description")
    reference_type: str = Field("", description="How reference was generated (telegram_id, etc.)")

    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PendingPayment":
        return cls.model_validate(data)


class WithdrawalRequest(BaseModel):
    """A user's request to withdraw balance to their bank account."""

    request_id: str = Field("", description="Unique withdrawal ID")
    user_id: int = Field(..., description="Telegram user ID")
    amount: int = Field(..., ge=0, description="Withdrawal amount in VND")
    status: WithdrawalStatus = Field(WithdrawalStatus.PENDING)
    timestamp: float = Field(default_factory=time.time)

    # Bank details
    bank_name: str = Field("", description="Target bank name")
    account_number: str = Field("", description="Target bank account number")
    account_holder: str = Field("", description="Account holder name")

    # Admin processing
    admin_notes: str = Field("")
    processed_at: float | None = Field(None)
    processed_by: int | None = Field(None, description="Admin user ID who processed")

    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WithdrawalRequest":
        return cls.model_validate(data)


class WheelPrize(BaseModel):
    """A prize definition for the lucky wheel game."""

    name: str = Field(..., description="Display name (e.g. '5,000đ')")
    type: str = Field(..., description="balance | coupon | nothing")
    value: int = Field(0, ge=0, description="Prize value (amount for balance, percent for coupon)")
    weight: int = Field(1, ge=1, description="Relative probability weight")
    emoji: str = Field("🎁", description="Display emoji with optional tg-emoji tag")

    @staticmethod
    def default_prizes() -> list["WheelPrize"]:
        """Return the default wheel prize configuration."""
        return [
            WheelPrize(name="5,000đ", type="balance", value=5000, weight=30, emoji='<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji>'),
            WheelPrize(name="Giảm 10%", type="coupon", value=10, weight=40, emoji='<tg-emoji emoji-id="5377624166436445368">🎟</tg-emoji>'),
            WheelPrize(name="Chúc may mắn lần sau!", type="nothing", value=0, weight=850, emoji='<tg-emoji emoji-id="5386856460632201117">😢</tg-emoji>'),
            WheelPrize(name="2,000đ", type="balance", value=2000, weight=35, emoji='<tg-emoji emoji-id="5379773896352355687">🪙</tg-emoji>'),
            WheelPrize(name="Giảm 20%", type="coupon", value=20, weight=20, emoji='<tg-emoji emoji-id="5377624166436445368">🎟</tg-emoji>'),
            WheelPrize(name="20,000đ", type="balance", value=20000, weight=10, emoji='<tg-emoji emoji-id="5215239948420003628">💵</tg-emoji>'),
            WheelPrize(name="Giảm 50%", type="coupon", value=50, weight=10, emoji='<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji>'),
            WheelPrize(name="50,000đ", type="balance", value=50000, weight=5, emoji='<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji>'),
        ]
