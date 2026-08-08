"""Partner API v1 (legacy).

Khác v2 ở chỗ lỗi trả HTTP 200 kèm `success: false` — giữ nguyên vì client đối
tác cũ phụ thuộc vào định dạng đó.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Header, HTTPException

from .. import engine
from ..deps import (
    ActorHeaders,
    parse_quantity,
    resolve_partner_ref,
    v1_error_from,
    v1_success,
    validate_variant,
)

router = APIRouter(tags=["Legacy"])


@router.get("/api/v1/users/profile", summary="Legacy: kiểm tra profile partner")
async def users_profile(headers: ActorHeaders = Depends()):
    try:
        actor = headers.actor(allow_admin=False)
    except HTTPException as exc:
        return v1_error_from(exc)

    return v1_success(
        {
            "username": str(actor.get("partner_name") or ""),
            "email": engine.actor_contact_email(actor),
            "walletBalance": int(engine.remaining_balance(actor) or 0),
        }
    )


@router.get("/api/v1/products/info/{product_id}", summary="Legacy: lấy thông tin sản phẩm")
async def product_info(product_id: str, headers: ActorHeaders = Depends()):
    try:
        actor = headers.actor(allow_admin=False)
        product_data = engine.product(product_id)
        if not isinstance(product_data, dict):
            raise HTTPException(status_code=404, detail="product_not_found")
    except HTTPException as exc:
        return v1_error_from(exc)

    return v1_success(engine.v1_product_payload(product_id, product_data, actor))


@router.get("/api/v1/products/variant/{variant_id}", summary="Legacy: lấy thông tin variant")
async def variant_info(variant_id: str, headers: ActorHeaders = Depends()):
    try:
        actor = headers.actor(allow_admin=False)
        product_id, product_data = engine.product_from_variant(variant_id)
        if not product_id or not isinstance(product_data, dict):
            raise HTTPException(status_code=404, detail="Variant not found")
    except HTTPException as exc:
        return v1_error_from(exc)

    return v1_success(engine.v1_product_payload(product_id, product_data, actor))


@router.get("/api/v1/orders/buy", summary="Legacy: tạo đơn bằng query string")
async def buy_order(
    productId: str | None = None,  # noqa: N803 — tên tham số công khai của API cũ
    quantity: str | None = None,
    variantId: str | None = None,  # noqa: N803
    orderId: str | None = None,  # noqa: N803
    order_id: str | None = None,
    headers: ActorHeaders = Depends(),
    x_idempotency_key: str = Header(None),
):
    try:
        actor = headers.actor(allow_admin=False)
        order_data = await _create_v1_order(
            actor,
            product_id=productId,
            variant_id=variantId,
            order_id=orderId,
            order_id_alt=order_id,
            idempotency_key=x_idempotency_key,
            quantity=quantity,
        )
    except HTTPException as exc:
        return v1_error_from(exc)

    return v1_success(
        [engine.v1_order_summary(order_data)], message="Order processing complete"
    )


@router.post("/api/v1/orders", summary="Legacy: tạo đơn")
async def create_order(
    payload: dict | None = Body(default=None),
    headers: ActorHeaders = Depends(),
    x_idempotency_key: str = Header(None),
):
    raw = payload if isinstance(payload, dict) else {}
    try:
        actor = headers.actor(allow_admin=False)
        order_data = await _create_v1_order(
            actor,
            product_id=raw.get("productId"),
            variant_id=raw.get("variantId"),
            order_id=raw.get("orderId"),
            order_id_alt=raw.get("order_id"),
            idempotency_key=x_idempotency_key,
            quantity=raw.get("quantity"),
        )
    except HTTPException as exc:
        return v1_error_from(exc)

    return v1_success(
        [engine.v1_order_summary(order_data)], message="Order processing complete"
    )


async def _create_v1_order(
    actor: dict,
    product_id,
    variant_id,
    order_id,
    order_id_alt,
    idempotency_key,
    quantity,
) -> dict:
    normalized_product_id = str(product_id or "").strip()
    if not normalized_product_id:
        raise HTTPException(status_code=400, detail="productId is required")
    if not isinstance(engine.product(normalized_product_id), dict):
        raise HTTPException(status_code=404, detail="product_not_found")

    validate_variant(normalized_product_id, variant_id)
    partner_ref = resolve_partner_ref(order_id, order_id_alt, idempotency_key)
    order_data, _balance, _replay = await engine.create_order(
        actor=actor,
        partner_ref=partner_ref,
        product_id=normalized_product_id,
        quantity=parse_quantity(quantity),
    )
    return order_data


@router.get("/api/v1/orders/{order_id}", summary="Legacy: xem chi tiết đơn")
async def order_detail(order_id: str, headers: ActorHeaders = Depends()):
    try:
        actor = headers.actor(allow_admin=False)
        order_data = engine.order_by_index(str(order_id or "").strip().upper())
        if not order_data or not engine.order_belongs_to_actor(order_data, actor):
            raise HTTPException(status_code=404, detail="Order not found")
    except HTTPException as exc:
        return v1_error_from(exc)

    return v1_success(engine.v1_order_detail(order_data))
