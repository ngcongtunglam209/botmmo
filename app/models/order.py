"""Order data models for tracking purchases, fulfillment, and refunds."""

from __future__ import annotations

import enum
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OrderStatus(str, enum.Enum):
    """All possible order lifecycle states."""

    PENDING_PAYMENT = "pending_payment"
    AWAITING_EMAIL = "awaiting_email"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"
    FAILED = "failed"

    @classmethod
    def from_legacy(cls, raw_status: str) -> OrderStatus:
        """Convert legacy Vietnamese status strings to enum values."""
        normalized = str(raw_status or "").strip().lower()
        # Strip tg-emoji tags for comparison
        import re
        normalized = re.sub(r"<tg-emoji[^>]*>[^<]*</tg-emoji>", "", normalized).strip().lower()

        mapping = {
            "hoàn thành": cls.COMPLETED,
            "hoan thanh": cls.COMPLETED,
            "completed": cls.COMPLETED,
            "đã hoàn tiền": cls.REFUNDED,
            "refunded": cls.REFUNDED,
            "pending_payment": cls.PENDING_PAYMENT,
            "awaiting_email": cls.AWAITING_EMAIL,
            "processing": cls.PROCESSING,
            "cancelled": cls.CANCELLED,
            "failed": cls.FAILED,
        }
        for key, status in mapping.items():
            if key in normalized:
                return status
        return cls.PROCESSING


class Order(BaseModel):
    """Represents a completed or in-progress order."""

    order_code: str = Field(..., description="Unique order identifier (e.g. ICLD123456, PROD...)")
    user_id: int | str = Field(..., description="Telegram user ID or PARTNER_ prefixed ID")
    amount: int = Field(0, ge=0, description="Total amount in VND")
    status: str = Field("Hoàn thành", description="Order status (legacy string or OrderStatus)")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp of creation")

    # Product info
    product_id: str = Field("", description="Product ID from catalog")
    product_name: str = Field("", description="Human-readable product name")
    product_duration: str = Field("", description="Duration text (e.g. '1 tháng', 'Vĩnh viễn')")
    quantity: int = Field(1, ge=1, description="Number of units purchased")

    # Delivery
    items: list[str] = Field(default_factory=list, description="Delivered items (links, accounts)")
    link: str = Field("", description="Legacy single link field")
    email: str = Field("", description="Customer email for delivery")
    # Written by several unrelated paths, so the value set is wider than it looks:
    # order_pipeline writes instant_items/stock_items/manual_pending, admin_orders
    # writes manual_completed, store_callback writes pending, and anything taking
    # delivery_result["method"] writes document/text/failed. Older rows may also
    # carry pending_source. Kept as a free string on purpose.
    delivery_method: str = Field("", description="instant_items | stock_items | manual_pending | manual_completed | pending | document | text | failed")

    # Payment
    payment_method: str = Field("bank_transfer", description="bank_transfer | usdt_rpay | binance_pay | balance")
    balance_used: int = Field(0, ge=0, description="Wallet balance portion used")
    qr_amount: int = Field(0, ge=0, description="Amount paid via QR/transfer")
    coupon_used: str = Field("", description="Applied coupon code")

    # User info snapshot
    full_name: str | None = Field(None, description="User's display name at order time")
    username: str | None = Field(None, description="User's @username at order time")

    # Completion / Refund
    completed_at: float | None = Field(None, description="Unix timestamp when completed")
    refunded_at: float | None = Field(None, description="Unix timestamp when refunded")
    refund_amount: int = Field(0, ge=0, description="Amount refunded")
    refund_reason: str = Field("", description="Refund reason description")
    refund_target: str = Field("", description="Where refund went (Ví Bot / Ví chung)")

    # API Partner fields
    type: str = Field("store_product", description="store_product | manual_order")
    api_partner_key_hash: str = Field("", description="SHA256 hash of partner API key")
    api_customer_email: str | None = Field(None)
    api_partner_ref: str = Field("", description="Partner's external reference code")
    manual_fulfillment: bool = Field(False, description="Whether order requires manual processing")

    model_config = ConfigDict(extra="allow")  # Allow legacy fields we haven't modeled yet

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Order:
        """Create Order from a raw dict, handling missing/extra fields gracefully."""
        return cls.model_validate(data)

    def to_legacy_dict(self) -> dict[str, Any]:
        """Convert back to the legacy dict format used by existing code."""
        return self.model_dump(exclude_none=False, exclude_defaults=False)


class PendingOrder(BaseModel):
    """An order that is waiting for payment confirmation."""

    order_code: str = Field("", description="Generated unique order code")
    user_id: int = Field(..., description="Telegram user ID")
    amount: int = Field(..., ge=0, description="Expected payment amount in VND")
    time: float = Field(default_factory=time.time, description="When the order was created")
    status: str = Field("pending_payment")

    # Product
    product_id: str = Field("")
    product_name: str = Field("")
    quantity: int = Field(1, ge=1)
    type: str = Field("store_product")

    # Payment
    transfer_content: str = Field("", description="Expected bank transfer description")
    secret_transfer_code: str = Field("", description="Secret code to match in transfer description")
    payment_method: str = Field("bank_transfer")
    provider: str = Field("", description="Payment provider: bank_transfer | rpay | binance_pay")
    balance_used: int = Field(0, ge=0)
    coupon_code: str = Field("")
    original_price: int = Field(0, ge=0)
    total_amount: int = Field(0, ge=0)

    # Message tracking
    message_id: int | None = Field(None, description="Telegram message ID of the payment QR")
    message_kind: str = Field("", description="text | photo")

    # User info
    full_name: str | None = None
    username: str | None = None
    email: str | None = None

    # RPay USDT
    rpay_trans_id: str = Field("")
    rpay_request_id: str = Field("")
    rpay_amount: str = Field("", description="Invoice amount in USDT, as sent to RPay")

    # Binance Pay. Reconciliation matches on this exact string, so it must stay
    # byte-identical to what the customer was shown.
    binance_pay_amount: str = Field("", description="Unique USDT amount the customer must send")
    binance_pay_id: str = Field("")

    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PendingOrder:
        return cls.model_validate(data)

