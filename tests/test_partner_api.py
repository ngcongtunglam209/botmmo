"""Partner API sau khi chuyển tầng HTTP sang app/web/api.

Nghiệp vụ tạo đơn vẫn ở app/api/order_pipeline.py; ở đây kiểm tra phần mà việc
chuyển nhà có thể làm gãy: định tuyến, xác thực, và hình dạng response mà đối
tác đang phụ thuộc.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.runtime_loader import load_modules

ADMIN_KEY = "admin-secret-key-for-tests"
PARTNER_KEY = "partner-key-for-tests"


@pytest.fixture()
def api(monkeypatch):
    """Client trên app thật, với một admin key và một partner key giả lập."""
    modules = load_modules()
    helpers = modules["app.api.helpers"]

    monkeypatch.setattr(helpers, "API_SECRET_KEY", ADMIN_KEY, raising=False)
    helpers.api_keys[PARTNER_KEY] = {
        "name": "Đối tác Test",
        "balance": 1_000_000,
        "enabled": True,
        "rate_limit_per_minute": 600,
        "allowed_ips": [],
    }
    try:
        yield TestClient(modules["app.models.api_models"].app)
    finally:
        helpers.api_keys.pop(PARTNER_KEY, None)


def partner(headers: dict | None = None) -> dict:
    result = {"x-api-key": PARTNER_KEY}
    result.update(headers or {})
    return result


# --- Định tuyến -------------------------------------------------------------

def test_healthz_is_public(api):
    assert api.get("/healthz").json() == {"status": "ok"}


def test_buy_path_is_not_swallowed_by_order_id_route(api):
    """/api/v1/orders/buy phải khớp route mua hàng, không phải /orders/{order_id}."""
    response = api.get("/api/v1/orders/buy", headers=partner())

    # Thiếu productId -> lỗi validate của route mua, không phải "Order not found".
    assert response.status_code == 400
    assert response.json()["message"] == "productId is required"


def test_by_ref_path_is_not_swallowed_by_order_code_route(api):
    response = api.get("/api/v2/orders/by-ref/KHONG-CO-REF", headers=partner())

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_admin_stock_integrity_requires_admin_key(api):
    denied = api.get("/api/v2/admin/local-stock-integrity", headers=partner())
    assert denied.status_code == 403

    allowed = api.get(
        "/api/v2/admin/local-stock-integrity", headers={"x-api-key": ADMIN_KEY}
    )
    assert allowed.status_code == 200
    assert allowed.json()["ok"] is True


# --- Xác thực ---------------------------------------------------------------

def test_missing_key_is_rejected(api):
    assert api.get("/api/v2/me").status_code == 401


def test_unknown_key_is_rejected(api):
    response = api.get("/api/v2/me", headers={"x-api-key": "khong-ton-tai"})
    assert response.status_code in (401, 403)


def test_bearer_authorization_header_works(api):
    response = api.get("/api/v2/me", headers={"authorization": f"Bearer {PARTNER_KEY}"})
    assert response.status_code == 200
    assert response.json()["data"]["partner_name"] == "Đối tác Test"


def test_v1_rejects_admin_master_key(api):
    """v1 gọi actor với allow_admin=False — key admin không được dùng."""
    response = api.get("/api/v1/users/profile", headers={"x-api-key": ADMIN_KEY})

    assert response.status_code == 403
    assert response.json()["success"] is False


# --- Hình dạng response -----------------------------------------------------

def test_v2_uses_ok_envelope(api):
    body = api.get("/api/v2/me", headers=partner()).json()

    assert body["ok"] is True
    assert set(body["data"]) >= {
        "version", "partner_name", "is_admin", "balance", "maintenance_mode"
    }


def test_legacy_status_endpoint_does_not_500(api):
    """Bản cũ đọc khóa `stock_count` không có trong payload -> 500 với mọi partner."""
    response = api.get("/api/status", headers=partner())

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "status", "maintenance_mode", "stock_count", "pending_orders", "your_balance"
    }
    assert isinstance(body["stock_count"], int)


def test_v2_status_agrees_with_legacy_status(api):
    legacy = api.get("/api/status", headers=partner()).json()
    v2 = api.get("/api/v2/status", headers=partner()).json()["data"]

    assert v2["status"] == legacy["status"]
    assert v2["product_count"] == legacy["stock_count"]
    assert v2["pending_orders"] == legacy["pending_orders"]


def test_v1_error_body_has_only_success_and_message(api):
    """Bản cũ không kèm key `data` trong lỗi v1 — thêm vào là đổi hợp đồng."""
    response = api.get("/api/v1/products/info/khong-ton-tai", headers=partner())

    assert response.status_code == 404
    assert response.json() == {"success": False, "message": "Product not found"}


def test_v1_profile_shape(api):
    body = api.get("/api/v1/users/profile", headers=partner()).json()

    assert body["success"] is True
    assert set(body["data"]) == {"username", "email", "walletBalance"}
    assert body["data"]["username"] == "Đối tác Test"
    assert body["data"]["walletBalance"] == 1_000_000


def test_catalog_pagination_shape(api):
    body = api.get("/api/v2/catalog?limit=5&offset=0", headers=partner()).json()

    assert body["ok"] is True
    pagination = body["data"]["pagination"]
    assert set(pagination) == {"limit", "offset", "returned", "total", "has_more"}
    assert pagination["returned"] == len(body["data"]["products"])


# --- Chống tạo đơn trùng ----------------------------------------------------

def test_v2_requires_partner_ref(api):
    response = api.post("/api/v2/orders", headers=partner(), json={"product_id": "x"})

    assert response.status_code == 400
    assert response.json()["detail"] == "partner_ref is required"


def test_v2_rejects_conflicting_idempotency_key(api):
    response = api.post(
        "/api/v2/orders",
        headers=partner({"x-idempotency-key": "REF-B"}),
        json={"partner_ref": "REF-A", "product_id": "x"},
    )

    assert response.status_code == 400
    assert "must match" in response.json()["detail"]


def test_v2_idempotency_header_can_supply_partner_ref(api):
    """Chỉ gửi header, không gửi body — không được báo thiếu partner_ref."""
    response = api.post(
        "/api/v2/orders",
        headers=partner({"x-idempotency-key": "REF-ONLY-HEADER"}),
        json={"product_id": "khong-ton-tai"},
    )

    assert response.status_code == 404  # sang tới bước tìm sản phẩm


def test_v1_rejects_conflicting_order_id_and_idempotency_key(api):
    modules = load_modules()
    helpers = modules["app.api.helpers"]
    helpers.products["ref_test"] = {"name": "Ref", "price": 1000, "stock": ["a"]}
    try:
        response = api.post(
            "/api/v1/orders",
            headers=partner({"x-idempotency-key": "KEY-B"}),
            json={"productId": "ref_test", "orderId": "KEY-A"},
        )
    finally:
        helpers.products.pop("ref_test", None)

    assert response.status_code == 400
    assert "must match" in response.json()["message"]


@pytest.mark.parametrize("quantity", ["0", "-3", "abc"])
def test_v1_rejects_bad_quantity(api, quantity):
    modules = load_modules()
    helpers = modules["app.api.helpers"]
    helpers.products["qty_test"] = {"name": "Qty", "price": 1000, "stock": ["a"]}
    try:
        response = api.get(
            f"/api/v1/orders/buy?productId=qty_test&quantity={quantity}",
            headers=partner(),
        )
    finally:
        helpers.products.pop("qty_test", None)

    assert response.status_code == 400
    assert response.json()["success"] is False


# --- Trang tài liệu ---------------------------------------------------------

def test_docs_page_and_assets(api):
    page = api.get("/docs")
    css = api.get("/docs/assets/api-docs.css")
    javascript = api.get("/docs/assets/api-docs.js")

    assert page.status_code == 200
    assert css.headers["content-type"].startswith("text/css")
    assert javascript.headers["content-type"].startswith("application/javascript")


def test_swagger_reference_renders(api):
    response = api.get("/reference")

    assert response.status_code == 200
    assert b"SwaggerUIBundle" in response.content


def test_openapi_lists_partner_endpoints(api):
    schema = api.get("/openapi.json").json()

    assert "/api/v2/orders" in schema["paths"]
    assert "/api/v1/users/profile" in schema["paths"]
    # Endpoint nội bộ không được lộ trong tài liệu công khai.
    assert "/webhook/sepay" not in schema["paths"]
    assert "/admin" not in schema["paths"]
