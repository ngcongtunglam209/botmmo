"""Product catalog and stock data models."""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StockItem(BaseModel):
    """A single stock unit (link, account, code) ready for delivery."""

    content: str = Field(..., description="The deliverable content (link, account info, code)")
    added_at: float = Field(default_factory=time.time, description="When this item was added to stock")
    reserved_by: str = Field("", description="Order code that reserved this item")

    model_config = ConfigDict(extra="allow")


class Product(BaseModel):
    """A product in the store catalog."""

    product_id: str = Field("", description="Unique product identifier")
    name: str = Field(..., description="Display name")
    price: int = Field(..., ge=0, description="Price per unit in VND")
    description: str = Field("", description="Product description")
    duration: str = Field("", description="Duration text (e.g. '1 tháng', 'Vĩnh viễn')")
    stock: list[str] = Field(default_factory=list, description="Available stock items")
    stock_count: int = Field(0, ge=0, description="Cached stock count")

    # Delivery
    requires_gmail: bool = Field(False, description="Needs customer email for manual fulfillment")
    auto_delivery: bool = Field(True, description="Auto-deliver from stock on payment")

    # SupplierSource resell
    is_supplier_source_resell: bool = Field(False, description="Product sourced from SupplierSource API")
    supplier_source_product_id: str = Field("", description="SupplierSource external product ID")
    supplier_source_variant_id: str = Field("", description="SupplierSource variant ID")

    # SocialSource social service
    is_social_source_service: bool = Field(False, description="Social service product from SOCIAL_SOURCE")
    ctt_service_id: str = Field("", description="SOCIAL_SOURCE service ID")
    ctt_min_quantity: int = Field(0, ge=0)
    ctt_max_quantity: int = Field(0, ge=0)
    ctt_rate_per_unit: float = Field(0.0, ge=0)

    # Product metadata
    warranty_days: int = Field(0, ge=0, description="Warranty period in days")
    daily_limit: int = Field(0, ge=0, description="Max purchases per user per day (0=unlimited)")
    category: str = Field("", description="Product category for grouping")
    sort_order: int = Field(0, description="Display sort order")
    is_active: bool = Field(True, description="Whether product is visible in store")
    created_at: float = Field(default_factory=time.time)

    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_dict(cls, product_id: str, data: dict[str, Any]) -> "Product":
        """Create from legacy dict format."""
        merged = {"product_id": product_id, **data}
        return cls.model_validate(merged)

    def available_stock_count(self) -> int:
        """Count of available (unreserved) stock items."""
        return len(self.stock)

    def is_in_stock(self, quantity: int = 1) -> bool:
        """Check if enough stock is available."""
        if self.is_supplier_source_resell or self.is_social_source_service:
            return True  # External source, always "in stock"
        return self.available_stock_count() >= quantity


class FlashSale(BaseModel):
    """A time-limited flash sale on a product."""

    product_id: str = Field(...)
    discount_percent: int = Field(..., ge=1, le=100)
    start_time: float = Field(default_factory=time.time)
    end_time: float = Field(...)
    max_quantity: int = Field(0, ge=0, description="Max units at sale price (0=unlimited)")
    sold_count: int = Field(0, ge=0)

    model_config = ConfigDict(extra="allow")

    def is_active(self) -> bool:
        now = time.time()
        return self.start_time <= now <= self.end_time

    def is_sold_out(self) -> bool:
        return self.max_quantity > 0 and self.sold_count >= self.max_quantity


class ComboD(BaseModel):
    """A combo deal combining multiple products at a discount."""

    combo_id: str = Field("")
    name: str = Field("")
    product_ids: list[str] = Field(default_factory=list)
    discount_percent: int = Field(0, ge=0, le=100)
    is_active: bool = Field(True)
    created_at: float = Field(default_factory=time.time)

    model_config = ConfigDict(extra="allow")

