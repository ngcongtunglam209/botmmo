"""Partner API v2."""

from __future__ import annotations

import re
import time

from fastapi import APIRouter, Depends, Header, HTTPException

from .. import engine
from ..deps import MAX_HISTORY_LIMIT, V2_VERSION, ActorHeaders, require_admin_actor, v2_ok
from ..schemas import CreateOrderRequest

router = APIRouter()


@router.get(
    "/api/v2/catalog",
    tags=["Partner"],
    summary="Lấy catalog sản phẩm",
    description="Trả danh sách sản phẩm đang bán kèm giá, tồn kho và pricing của partner.",
)
async def catalog(
    headers: ActorHeaders = Depends(),
    limit: int | None = None,
    offset: int = 0,
    search: str | None = None,
    available_only: bool = False,
):
    actor = headers.actor()
    products, total, filtered, safe_limit, safe_offset = engine.catalog_payload(
        actor,
        limit=limit,
        offset=offset,
        search=search,
        available_only=available_only,
    )
    returned = len(products)
    return v2_ok(
        {
            "version": V2_VERSION,
            "products": products,
            "total_products": total,
            "filtered_products": filtered,
            "returned_products": returned,
            "pagination": {
                "limit": safe_limit,
                "offset": safe_offset,
                "returned": returned,
                "total": filtered,
                "has_more": bool(safe_limit and (safe_offset + returned) < filtered),
            },
            "maintenance_mode": engine.maintenance_mode(),
            "partner_name": actor.get("partner_name"),
        }
    )


@router.get(
    "/api/v2/me",
    tags=["Partner"],
    summary="Kiểm tra API key và số dư ví chung",
    description=(
        "Dùng endpoint này trước khi tạo đơn để xác nhận key hợp lệ, số dư hiện tại "
        "và hạng chiết khấu."
    ),
)
async def me(headers: ActorHeaders = Depends()):
    actor = headers.actor()
    owner_user_id = engine.actor_owner_user_id(actor)
    rank_info = engine.user_rank(owner_user_id) if owner_user_id else None
    return v2_ok(
        {
            "version": V2_VERSION,
            "partner_name": actor.get("partner_name"),
            "is_admin": bool(actor.get("is_admin")),
            "balance": engine.remaining_balance(actor),
            "maintenance_mode": engine.maintenance_mode(),
            "rank_name": _rank_name(rank_info),
            "rank_discount_percent": 0,
        }
    )


def _rank_name(rank_info) -> str:
    if not rank_info:
        return ""
    raw = str((rank_info.get("rank") or {}).get("name") or "")
    return re.sub(r"<[^>]+>", "", raw).strip()


@router.post(
    "/api/v2/orders",
    tags=["Partner"],
    summary="Tạo đơn hàng",
    description=(
        "Tạo đơn bằng `partner_ref` duy nhất. Nên gửi cùng giá trị trong header "
        "`x-idempotency-key` để retry không tạo trùng."
    ),
)
async def create_order(
    req: CreateOrderRequest,
    headers: ActorHeaders = Depends(),
    x_idempotency_key: str = Header(None),
):
    actor = headers.actor()
    partner_ref = _resolve_ref(req.partner_ref, x_idempotency_key)

    order_data, remaining_balance, idempotent_replay = await engine.create_order(
        actor=actor,
        partner_ref=partner_ref,
        customer_email=req.customer_email or req.email,
        customer_id=req.customer_id,
        note=req.note,
        product_id=req.product_id,
        quantity=req.quantity,
    )
    message = (
        "Existing order returned (idempotent replay)."
        if idempotent_replay
        else "Order created successfully."
    )
    return v2_ok(
        engine.order_payload(
            order_data,
            remaining_balance=remaining_balance,
            idempotent_replay=idempotent_replay,
        ),
        message=message,
    )


def _resolve_ref(partner_ref: str | None, idempotency_key: str | None) -> str:
    body_ref = (partner_ref or "").strip()
    header_ref = (idempotency_key or "").strip()
    if not body_ref and header_ref:
        return header_ref
    if body_ref and header_ref and body_ref != header_ref:
        raise HTTPException(
            status_code=400, detail="partner_ref and x-idempotency-key must match"
        )
    if not body_ref:
        raise HTTPException(status_code=400, detail="partner_ref is required")
    return body_ref


@router.get(
    "/api/v2/orders",
    tags=["Partner"],
    summary="Lấy lịch sử đơn API",
    description=(
        "Trả danh sách đơn của API key hiện tại, có phân trang và filter. Endpoint list "
        "chỉ trả trạng thái đã lưu; trả về theo thứ tự mới nhất trước."
    ),
)
async def list_orders(
    headers: ActorHeaders = Depends(),
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
    search: str | None = None,
):
    actor = headers.actor()
    safe_limit = max(1, min(MAX_HISTORY_LIMIT, int(limit or 20)))
    safe_offset = max(0, int(offset or 0))
    orders_page, total = engine.orders_for_actor(
        actor,
        limit=safe_limit,
        offset=safe_offset,
        status_filter=status,
        search=search,
    )
    return v2_ok(
        {
            "orders": [engine.order_payload(order) for order in orders_page],
            "pagination": {
                "limit": safe_limit,
                "offset": safe_offset,
                "returned": len(orders_page),
                "total": total,
                "has_more": (safe_offset + len(orders_page)) < total,
            },
            "filters": {"status": str(status or ""), "search": str(search or "")},
            "partner_name": actor.get("partner_name"),
            "remaining_balance": engine.remaining_balance(actor),
        }
    )


@router.get(
    "/api/v2/orders/by-ref/{partner_ref}",
    tags=["Partner"],
    summary="Xem chi tiết đơn theo partner_ref",
    description="Dùng khi hệ thống partner lưu mã nội bộ của mình.",
)
async def get_order_by_ref(partner_ref: str, headers: ActorHeaders = Depends()):
    actor = headers.actor()
    order_data = engine.find_order_by_ref(actor, partner_ref)
    if not order_data:
        raise HTTPException(status_code=404, detail="Order not found")
    return v2_ok(
        engine.order_payload(
            order_data,
            remaining_balance=engine.remaining_balance(actor),
            idempotent_replay=True,
        )
    )


@router.get(
    "/api/v2/admin/local-stock-integrity",
    tags=["Admin"],
    summary="Admin: kiểm tra trùng kho local",
    description="Chỉ admin API key dùng được. Endpoint readonly xem báo cáo integrity kho local.",
)
async def local_stock_integrity(headers: ActorHeaders = Depends(), refresh: bool = False):
    require_admin_actor(headers)
    report = engine.last_stock_integrity_report()
    if refresh or not isinstance(report, dict):
        report = await engine.audit_stock_integrity(source="api_readonly")
    return v2_ok(
        report
        or {
            "generated_at": time.time(),
            "products_scanned": 0,
            "products_with_duplicates": 0,
            "duplicate_item_count": 0,
            "products": [],
            "duplicate_items": [],
        }
    )


@router.get(
    "/api/v2/orders/{order_code}",
    tags=["Partner"],
    summary="Xem chi tiết đơn theo mã đơn",
    description="Trả chi tiết đơn theo `order_code`.",
)
async def get_order(order_code: str, headers: ActorHeaders = Depends()):
    actor = headers.actor()
    normalized = str(order_code or "").strip().upper()
    order_data = engine.find_order_by_code(normalized)
    if not order_data or not engine.order_belongs_to_actor(order_data, actor):
        raise HTTPException(status_code=404, detail="Order not found")
    return v2_ok(
        engine.order_payload(order_data, remaining_balance=engine.remaining_balance(actor))
    )
