"""Dependency và tiện ích dùng chung cho Partner API."""

from __future__ import annotations

import random
import string
import time
from typing import Any

from fastapi import Header, HTTPException

from . import engine

V2_VERSION = "2.0"
MAX_HISTORY_LIMIT = 100


class ActorHeaders:
    """Gom 3 header xác thực để handler khỏi lặp lại chữ ký dài."""

    def __init__(
        self,
        x_api_key: str = Header(None),
        x_api_token: str = Header(None),
        authorization: str = Header(None),
    ):
        self.x_api_key = x_api_key
        self.x_api_token = x_api_token
        self.authorization = authorization

    def actor(self, allow_admin: bool = True) -> dict:
        return engine.require_actor(
            x_api_key=self.x_api_key,
            x_api_token=self.x_api_token,
            authorization=self.authorization,
            allow_admin=allow_admin,
        )


def require_admin_actor(headers: ActorHeaders) -> dict:
    actor = headers.actor()
    if not actor.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin API key required")
    return actor


# --- Chuẩn hóa tham số v1 ---------------------------------------------------

def clean_scalar(value: Any) -> str:
    if value is None or not isinstance(value, (str, int, float)):
        return ""
    return str(value).strip()


def parse_quantity(raw_quantity: Any) -> int:
    normalized = clean_scalar(raw_quantity)
    if not normalized:
        return 1
    try:
        quantity = int(normalized)
    except (ValueError, TypeError) as error:
        raise HTTPException(
            status_code=400, detail="quantity must be a positive integer"
        ) from error
    if quantity < 1:
        raise HTTPException(status_code=400, detail="quantity must be a positive integer")
    return quantity


def validate_variant(product_id: str, variant_id: Any) -> str | None:
    normalized = clean_scalar(variant_id)
    if not normalized:
        return None
    if normalized != engine.synthetic_variant_id(product_id):
        raise HTTPException(status_code=400, detail="variantId is invalid for this product")
    return normalized


def generate_partner_ref() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"DMV1_{int(time.time() * 1000)}_{suffix}"


def resolve_partner_ref(
    order_id: Any, order_id_alt: Any, idempotency_key: Any
) -> str:
    """orderId trong body và x-idempotency-key phải khớp nếu gửi cả hai."""
    body_ref = clean_scalar(order_id) or clean_scalar(order_id_alt)
    header_ref = clean_scalar(idempotency_key)
    if body_ref and header_ref and body_ref != header_ref:
        raise HTTPException(
            status_code=400, detail="orderId and x-idempotency-key must match"
        )
    return body_ref or header_ref or generate_partner_ref()


# --- Bao response -----------------------------------------------------------

def v1_success(data: Any, message: str | None = None) -> dict:
    payload: dict[str, Any] = {"success": True, "data": data}
    if message is not None:
        payload["message"] = str(message)
    return payload


def v1_error(message: str, status_code: int = 400):
    """Body chỉ có `success` và `message` — đúng như bản cũ, không thêm `data`."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": str(message or "Request failed")},
    )


def v1_error_from(exc: HTTPException):
    return v1_error(engine.humanize_error(exc.detail), exc.status_code)


def v2_ok(data: Any, message: str | None = None) -> dict:
    payload: dict[str, Any] = {"ok": True, "data": data}
    if message is not None:
        payload["message"] = str(message)
    return payload
