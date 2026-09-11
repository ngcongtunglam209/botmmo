"""User profile and VIP system data models."""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VIPRank(BaseModel):
    """A VIP tier definition with spending threshold and discount percentage."""

    name: str = Field(..., description="Display name with emoji (e.g. '⭐️ Đồng')")
    min_spend: int = Field(0, ge=0, description="Minimum total spend to reach this rank (VND)")
    discount: int = Field(0, ge=0, le=100, description="Discount percentage for this rank")

    @staticmethod
    def default_ranks() -> list[VIPRank]:
        """Return the default VIP rank ladder."""
        return [
            VIPRank(name="⭐️ Đồng", min_spend=0, discount=0),
            VIPRank(name="⭐️ Bạc", min_spend=500_000, discount=2),
            VIPRank(name="⭐️ Vàng", min_spend=2_000_000, discount=5),
            VIPRank(name='<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> Kim Cương', min_spend=7_000_000, discount=8),
            VIPRank(name="⭐️ Cao Thủ", min_spend=20_000_000, discount=10),
        ]


class UserProfile(BaseModel):
    """A bot user's profile data, stored keyed by str(user_id)."""

    user_id: int | str = Field(..., description="Telegram user ID")
    full_name: str = Field("", description="User's display name")
    username: str = Field("", description="Telegram @username")
    balance: int = Field(0, ge=0, description="Wallet balance in VND")
    total_spent: int = Field(0, ge=0, description="Lifetime spending in VND")
    order_count: int = Field(0, ge=0, description="Total number of completed orders")
    first_seen: float = Field(default_factory=time.time, description="First interaction timestamp")
    last_seen: float = Field(default_factory=time.time, description="Last interaction timestamp")
    is_premium: bool = Field(False, description="Telegram Premium subscriber flag")

    # Referral
    referrer_id: int | None = Field(None, description="Who referred this user")
    referral_code: str = Field("", description="This user's referral code")

    # Notifications
    notifications_enabled: bool = Field(True)

    model_config = ConfigDict(extra="allow")  # Allow legacy fields

    @classmethod
    def from_dict(cls, user_id: int | str, data: dict[str, Any]) -> UserProfile:
        """Create from the legacy dict format, injecting user_id."""
        merged = {"user_id": user_id, **data}
        return cls.model_validate(merged)

    def get_vip_rank(self, ranks: list[VIPRank] | None = None) -> VIPRank:
        """Determine user's current VIP rank based on total_spent."""
        if ranks is None:
            ranks = VIPRank.default_ranks()
        current = ranks[0]
        for rank in ranks:
            if self.total_spent >= rank.min_spend:
                current = rank
        return current

    def get_discount_percent(self, ranks: list[VIPRank] | None = None) -> int:
        """Get the user's discount percentage based on VIP rank."""
        return self.get_vip_rank(ranks).discount


class TransactionRecord(BaseModel):
    """A single balance change event for audit trail."""

    amount: int = Field(..., description="Change amount (positive=credit, negative=debit)")
    new_balance: int = Field(..., ge=0, description="Balance after this transaction")
    reason: str = Field("", description="Human-readable reason")
    timestamp: float = Field(default_factory=time.time)

    model_config = ConfigDict(extra="allow")
