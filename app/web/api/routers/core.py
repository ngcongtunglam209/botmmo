"""Endpoint hạ tầng: health check, status, mua link legacy, webhook SePay."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from .. import engine
from ..deps import ActorHeaders, v2_ok
from ..schemas import LegacyBuyRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@router.get("/api/status", tags=["Partner"], summary="Kiểm tra trạng thái bot và kho hàng")
async def get_status(headers: ActorHeaders = Depends()):
    """Bản rút gọn của /api/v2/status, giữ cho client cũ.

    `stock_count` lấy từ `product_count`: bản cũ đọc khóa `stock_count` vốn
    không tồn tại trong payload nên endpoint này luôn ném KeyError thành 500.
    """
    payload = engine.status_payload(headers.actor())
    return {
        "status": payload["status"],
        "maintenance_mode": payload["maintenance_mode"],
        "stock_count": payload["product_count"],
        "pending_orders": payload["pending_orders"],
        "your_balance": payload["your_balance"],
    }


@router.get(
    "/api/v2/status",
    tags=["Partner"],
    summary="Kiểm tra trạng thái hệ thống",
    description=(
        "Trả trạng thái online, maintenance mode, số sản phẩm hiển thị, pending orders "
        "và số dư của partner."
    ),
)
async def api_v2_status(headers: ActorHeaders = Depends()):
    return v2_ok(engine.status_payload(headers.actor()))


@router.post(
    "/api/buy",
    tags=["Legacy"],
    summary="Legacy: mua link trực tiếp",
    description=(
        "Endpoint cũ để mua 1 link trực tiếp. Với API V2, partner nên dùng "
        "`POST /api/v2/orders`; chỉ endpoint legacy này mới xem `link` là nội dung "
        "giao hàng chính."
    ),
)
async def buy_link(req: LegacyBuyRequest, headers: ActorHeaders = Depends()):
    actor = headers.actor()
    if not req.partner_ref or not req.partner_ref.strip():
        raise HTTPException(status_code=400, detail="partner_ref is required")

    order_data, remaining_balance, idempotent_replay = await engine.create_order(
        actor=actor,
        partner_ref=req.partner_ref,
        customer_email=req.email,
        note="legacy_api_buy",
        product_id=req.product_id,
        quantity=req.quantity or 1,
    )
    return {
        "status": "success",
        "order_code": order_data.get("order_code"),
        "link": order_data.get("link"),
        "price": int(order_data.get("amount", 0) or 0),
        "remaining_balance": remaining_balance,
        "idempotent_replay": bool(idempotent_replay),
    }


@router.post("/webhook/sepay", include_in_schema=False)
async def sepay_webhook(request: Request):
    """Nhận giao dịch ngân hàng do SePay push.

    SePay coi mọi response khác 200/201 là thất bại và retry nhiều giờ. Vì vậy
    payload rác / sai key / chưa bật SePay đều trả 200 — retry không giúp gì.
    Chỉ lỗi hạ tầng thật mới để exception bay lên thành 500 cho SePay gửi lại.
    Giao dịch hợp lệ chỉ được đưa vào hàng đợi; payment_monitor khớp đơn ở vòng
    quét kế tiếp.
    """
    from app.integrations.sepay_api import (
        sepay_normalize_webhook_payload,
        sepay_verify_webhook_key,
        sepay_webhook_inbox,
    )

    if not sepay_verify_webhook_key(request.headers.get("Authorization")):
        return JSONResponse(status_code=401, content={"success": False})

    if not engine.value(engine.CONFIG_MODULE, "ENABLE_PAYMENT_SEPAY", False):
        logger.warning("SePay webhook: ENABLE_PAYMENT_SEPAY=false -> bỏ qua payload")
        return {"success": True}

    try:
        body = await request.json()
    except Exception as error:
        logger.warning("SePay webhook: body không phải JSON hợp lệ: %s", error)
        return {"success": True}

    normalized = sepay_normalize_webhook_payload(body)
    if normalized:
        sepay_webhook_inbox.append(normalized)
        logger.info(
            "SePay webhook: nhận giao dịch %s số tiền %s",
            normalized["transactionID"],
            f"{normalized['amount']:,}đ",
        )
    return {"success": True}


@router.post("/webhook/rpay", include_in_schema=False)
@router.get("/webhook/rpay", include_in_schema=False)
async def rpay_callback(request: Request):
    """Nhận kết quả hóa đơn USDT do RPay push.

    RPay không ký HMAC — nó chỉ gửi lại `merchant_id`/`api_key` trong body, nên
    đó là toàn bộ thứ xác thực có được. Sai key trả 401 và không ghi log giá trị
    nhận được. Payload rác / chưa completed / không khớp đơn đều trả 200 vì
    retry cũng không đổi kết quả. Hóa đơn hợp lệ chỉ được đưa vào hàng đợi;
    payment_monitor khớp đơn ở vòng quét kế tiếp.
    """
    from app.integrations.rpay_api import (
        rpay_callback_inbox,
        rpay_normalize_completed_invoice,
        rpay_verify_credentials,
    )

    try:
        body = await request.json()
    except Exception:
        body = None
    if not isinstance(body, dict):
        form = await request.form()
        body = dict(form) if form else dict(request.query_params)

    if not rpay_verify_credentials(body):
        return JSONResponse(status_code=401, content={"success": False})

    if not engine.value(engine.CONFIG_MODULE, "ENABLE_PAYMENT_RPAY", False):
        logger.warning("RPay callback: ENABLE_PAYMENT_RPAY=false -> bỏ qua payload")
        return {"success": True}

    normalized = rpay_normalize_completed_invoice(body)
    if normalized:
        rpay_callback_inbox.append(normalized)
        logger.info(
            "RPay callback: hóa đơn %s cho đơn %s, số tiền %s",
            normalized["transactionID"],
            normalized["description"],
            f"{normalized['amount']:,}đ",
        )
    return {"success": True}
