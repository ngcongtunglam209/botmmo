"""Pydantic model cho Partner API.

Giữ nguyên tên field và mô tả của bản cũ để OpenAPI và client đối tác không đổi.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LegacyBuyRequest(BaseModel):
    """Body của endpoint legacy `POST /api/buy`."""

    partner_ref: str = Field(
        ...,
        description="Mã đơn duy nhất bên hệ thống đối tác. Dùng để chống tạo trùng khi retry.",
        examples=["ORDER_20260426_0001"],
    )
    email: str | None = Field(
        None,
        description="Email khách nhận link với endpoint legacy `/api/buy`.",
        examples=["customer@example.com"],
    )
    product_id: str | None = Field(None, description="ID sản phẩm cần mua.")
    quantity: int = Field(1, description="Số lượng sản phẩm.", examples=[1])


class CreateOrderRequest(BaseModel):
    """Body của `POST /api/v2/orders`."""

    partner_ref: str | None = Field(
        None, description="Mã đơn duy nhất của partner.", examples=["ORDER_20260426_0001"]
    )
    product_id: str | None = Field(
        None, description="ID từ `GET /api/v2/catalog`.", examples=["netflix_1"]
    )
    quantity: int = Field(1, description="Số lượng sản phẩm.", examples=[1])
    email: str | None = Field(None, description="Alias cũ của `customer_email`.")
    customer_email: str | None = Field(None, description="Email khách cuối nếu cần.")
    customer_id: str | None = Field(None, description="ID khách cuối phía partner.")
    note: str | None = Field(None, description="Ghi chú nội bộ, tối đa 200 ký tự.")
    send_email: bool = Field(True, description="Gửi email khi luồng sản phẩm hỗ trợ.")
