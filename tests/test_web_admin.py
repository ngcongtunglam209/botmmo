"""Test cho web admin mới (app/web).

Dùng database tạm nên không đụng vào database.sqlite thật.
"""

from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def web(tmp_path, monkeypatch):
    """App admin sạch, trỏ vào SQLite tạm, đã đăng nhập sẵn."""
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("ADMIN_WEB_SESSION_SECRET", "test-secret-for-web-admin")
    monkeypatch.setenv("ADMIN_USER_ID", "424242")
    monkeypatch.setenv("PUBLIC_API_URL", "http://testserver")

    from app.web import create_app, db, security, settings
    from app.web.repo import sessions

    settings.get_settings.cache_clear()
    db.close_connection()

    app = create_app()
    client = TestClient(app)

    token, expires_at = security.new_session_token()
    sessions.create(token, expires_at)
    client.cookies.set(settings.get_settings().session_cookie, token)

    yield client, token, db_path

    db.close_connection()
    settings.get_settings.cache_clear()


def seed(db_path, key: str, value) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)",
            (key, json.dumps(value, ensure_ascii=False)),
        )


def read_kv(db_path, key: str):
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT value FROM kv_store WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def csrf_of(token: str) -> str:
    from app.web import security

    return security.csrf_token_for(token)


# --- Xác thực ---------------------------------------------------------------

def test_guest_is_redirected_to_login(web):
    client, _token, _db = web
    client.cookies.clear()
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin/login")


def test_login_page_renders_for_guest(web):
    client, _token, _db = web
    client.cookies.clear()
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert "Đăng nhập" in response.text


def test_dashboard_renders_when_logged_in(web):
    client, _token, _db = web
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Tổng quan" in response.text


def test_post_without_csrf_is_rejected(web):
    client, _token, _db = web
    response = client.post("/admin/coupons/save", data={"code": "NOPE", "mode": "add"})
    assert response.status_code == 403


def test_post_from_foreign_origin_is_rejected(web):
    client, token, _db = web
    response = client.post(
        "/admin/coupons/save",
        data={"code": "EVIL", "mode": "add", "csrf_token": csrf_of(token)},
        headers={"origin": "https://attacker.example"},
    )
    assert response.status_code == 403


def test_logout_revokes_session(web):
    client, token, _db = web
    response = client.post(
        "/admin/logout", data={"csrf_token": csrf_of(token)}, follow_redirects=False
    )
    assert response.status_code == 303

    from app.web.repo import sessions

    assert not sessions.exists(token)


# --- Sản phẩm ---------------------------------------------------------------

def test_create_product_writes_to_sqlite(web):
    client, token, db_path = web
    response = client.post(
        "/admin/products/create",
        data={
            "csrf_token": csrf_of(token),
            "product_id": "netflix_1m",
            "name": "Netflix Premium",
            "price": "35000",
            "cost_price": "20000",
            "stock_items": "acc1\nacc2",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    products = read_kv(db_path, "data_products.json")
    assert products["netflix_1m"]["price"] == 35000
    assert products["netflix_1m"]["stock"] == ["acc1", "acc2"]


def test_create_product_rejects_missing_cost_price(web):
    client, token, db_path = web
    client.post(
        "/admin/products/create",
        data={
            "csrf_token": csrf_of(token),
            "product_id": "broken",
            "name": "Không giá vốn",
            "price": "10000",
        },
        follow_redirects=False,
    )
    assert read_kv(db_path, "data_products.json") in (None, {})


def test_update_product_appends_stock(web):
    client, token, db_path = web
    seed(db_path, "data_products.json", {"p1": {"name": "P1", "price": 1000, "stock": ["a"]}})

    client.post(
        "/admin/products/p1/update",
        data={"csrf_token": csrf_of(token), "product_id": "p1", "stock_items": "b\nc"},
        follow_redirects=False,
    )
    assert read_kv(db_path, "data_products.json")["p1"]["stock"] == ["a", "b", "c"]


def test_manual_product_rejects_local_stock(web):
    client, token, db_path = web
    seed(db_path, "data_products.json", {"m1": {"name": "M1", "requires_gmail": True, "stock": []}})

    client.post(
        "/admin/products/m1/update",
        data={"csrf_token": csrf_of(token), "product_id": "m1", "stock_items": "x"},
        follow_redirects=False,
    )
    assert read_kv(db_path, "data_products.json")["m1"]["stock"] == []


def test_delete_product(web):
    client, token, db_path = web
    seed(db_path, "data_products.json", {"gone": {"name": "Gone", "price": 1}})

    client.post(
        "/admin/products/gone/delete",
        data={"csrf_token": csrf_of(token), "product_id": "gone"},
        follow_redirects=False,
    )
    assert "gone" not in read_kv(db_path, "data_products.json")


def test_product_list_filters_by_kind(web):
    client, _token, db_path = web
    seed(
        db_path,
        "data_products.json",
        {
            "local1": {"name": "Local One", "price": 1000},
            "manual1": {"name": "Manual One", "price": 2000, "requires_gmail": True},
        },
    )
    response = client.get("/admin/products?kind=manual")
    assert "Manual One" in response.text
    assert "Local One" not in response.text


# --- Ví user ----------------------------------------------------------------

def test_add_balance_records_transaction(web):
    client, token, db_path = web
    seed(db_path, "data_users.json", {"777": {"user_id": 777, "balance": 5000}})

    client.post(
        "/admin/users/777/balance",
        data={"csrf_token": csrf_of(token), "user_id": "777", "mode": "add", "amount": "2500"},
        follow_redirects=False,
    )
    assert read_kv(db_path, "data_users.json")["777"]["balance"] == 7500
    history = read_kv(db_path, "data_transaction_history.json")["777"]
    assert history[-1]["amount"] == 2500
    assert history[-1]["balance_after"] == 7500


def test_subtract_balance_never_goes_negative(web):
    client, token, db_path = web
    seed(db_path, "data_users.json", {"777": {"user_id": 777, "balance": 1000}})

    client.post(
        "/admin/users/777/balance",
        data={"csrf_token": csrf_of(token), "user_id": "777", "mode": "sub", "amount": "9999"},
        follow_redirects=False,
    )
    assert read_kv(db_path, "data_users.json")["777"]["balance"] == 0


def test_ban_and_unban_user(web):
    client, token, db_path = web
    seed(db_path, "data_users.json", {"555": {"user_id": 555, "balance": 0}})

    client.post(
        "/admin/users/555/ban",
        data={"csrf_token": csrf_of(token), "user_id": "555", "mode": "ban"},
        follow_redirects=False,
    )
    assert 555 in read_kv(db_path, "data_banned_users.json")

    client.post(
        "/admin/users/555/ban",
        data={"csrf_token": csrf_of(token), "user_id": "555", "mode": "unban"},
        follow_redirects=False,
    )
    assert read_kv(db_path, "data_banned_users.json") == []


# --- Đơn hàng ---------------------------------------------------------------

def test_order_email_update_touches_every_record(web):
    client, token, db_path = web
    seed(db_path, "data_order_history.json", [{"order_code": "ICLD123456", "amount": 1000}])
    seed(db_path, "data_pending_manual_orders.json", {"ICLD123456": {"order_code": "ICLD123456"}})

    client.post(
        "/admin/orders/ICLD123456/update",
        data={
            "csrf_token": csrf_of(token),
            "order_code": "ICLD123456",
            "mode": "set_email",
            "value": "khach@example.com",
        },
        follow_redirects=False,
    )
    assert read_kv(db_path, "data_order_history.json")[0]["email"] == "khach@example.com"
    pending = read_kv(db_path, "data_pending_manual_orders.json")
    assert pending["ICLD123456"]["email"] == "khach@example.com"


def test_order_rejects_bad_email(web):
    client, token, db_path = web
    seed(db_path, "data_order_history.json", [{"order_code": "ICLD999999", "amount": 1}])

    client.post(
        "/admin/orders/ICLD999999/update",
        data={
            "csrf_token": csrf_of(token),
            "order_code": "ICLD999999",
            "mode": "set_email",
            "value": "khong-phai-email",
        },
        follow_redirects=False,
    )
    assert "email" not in read_kv(db_path, "data_order_history.json")[0]


# --- Coupon -----------------------------------------------------------------

def test_coupon_save_keeps_used_count(web):
    client, token, db_path = web
    seed(db_path, "data_coupons.json", {"SALE": {"discount": 1000, "quantity": 5, "used": 3}})

    client.post(
        "/admin/coupons/save",
        data={
            "csrf_token": csrf_of(token),
            "mode": "add",
            "code": "sale",
            "discount": "2000",
            "quantity": "10",
            "days": "7",
        },
        follow_redirects=False,
    )
    coupon = read_kv(db_path, "data_coupons.json")["SALE"]
    assert coupon["discount"] == 2000 and coupon["used"] == 3


def test_coupon_delete(web):
    client, token, db_path = web
    seed(db_path, "data_coupons.json", {"OLD": {"discount": 1}})

    client.post(
        "/admin/coupons/save",
        data={"csrf_token": csrf_of(token), "mode": "delete", "code": "OLD"},
        follow_redirects=False,
    )
    assert read_kv(db_path, "data_coupons.json") == {}


# --- Danh mục ---------------------------------------------------------------

def test_rename_category_moves_products(web):
    client, token, db_path = web
    seed(db_path, "data_store_categories.json", {"Cũ": {"sort_order": 1}})
    seed(db_path, "data_products.json", {"p1": {"name": "P1", "store_category": "Cũ"}})

    client.post(
        "/admin/categories/update",
        data={"csrf_token": csrf_of(token), "category_name": "Cũ", "new_name": "Mới"},
        follow_redirects=False,
    )
    assert read_kv(db_path, "data_products.json")["p1"]["store_category"] == "Mới"
    assert "Cũ" not in read_kv(db_path, "data_store_categories.json")


def test_delete_category_moves_products_to_fallback(web):
    client, token, db_path = web
    seed(db_path, "data_store_categories.json", {"Tạm": {"sort_order": 1}})
    seed(db_path, "data_products.json", {"p1": {"name": "P1", "store_category": "Tạm"}})

    client.post(
        "/admin/categories/delete",
        data={"csrf_token": csrf_of(token), "category_name": "Tạm"},
        follow_redirects=False,
    )
    assert read_kv(db_path, "data_products.json")["p1"]["store_category"] == "Sản Phẩm Khác"


def test_default_category_cannot_be_deleted(web):
    client, token, db_path = web
    seed(db_path, "data_store_categories.json", {"Sản Phẩm Khác": {"sort_order": 1}})

    client.post(
        "/admin/categories/delete",
        data={"csrf_token": csrf_of(token), "category_name": "Sản Phẩm Khác"},
        follow_redirects=False,
    )
    assert "Sản Phẩm Khác" in read_kv(db_path, "data_store_categories.json")


# --- API partner ------------------------------------------------------------

def test_create_partner_and_topup(web):
    client, token, db_path = web
    client.post(
        "/admin/partners/manage",
        data={"csrf_token": csrf_of(token), "mode": "create", "target": "Đối tác A", "amount": "0"},
        follow_redirects=False,
    )
    keys = read_kv(db_path, "data_api_keys.json")
    assert len(keys) == 1
    api_key = next(iter(keys))
    assert keys[api_key]["name"] == "Đối tác A"

    from app.web.repo import partners

    client.post(
        f"/admin/partners/{partners.public_id(api_key)}/manage",
        data={
            "csrf_token": csrf_of(token),
            "mode": "topup",
            "target": partners.public_id(api_key),
            "amount": "500000",
        },
        follow_redirects=False,
    )
    assert read_kv(db_path, "data_api_keys.json")[api_key]["balance"] == 500000


def test_partner_subtract_blocked_when_insufficient(web):
    client, token, db_path = web
    seed(db_path, "data_api_keys.json", {"KEY1": {"name": "B", "balance": 1000, "enabled": True}})

    from app.web.repo import partners

    client.post(
        f"/admin/partners/{partners.public_id('KEY1')}/manage",
        data={
            "csrf_token": csrf_of(token),
            "mode": "subtract",
            "target": partners.public_id("KEY1"),
            "amount": "5000",
        },
        follow_redirects=False,
    )
    assert read_kv(db_path, "data_api_keys.json")["KEY1"]["balance"] == 1000


def test_partner_csv_export(web):
    client, _token, db_path = web
    seed(db_path, "data_api_keys.json", {"KEY1": {"name": "Đối tác CSV", "balance": 7000}})

    response = client.get("/admin/partners.csv")
    assert response.status_code == 200
    assert "Đối tác CSV" in response.text
    assert "KEY1" not in response.text  # key thật không bao giờ lộ ra file export


# --- Hỗ trợ và vận hành -----------------------------------------------------

def test_support_update_sets_status(web):
    client, token, db_path = web
    seed(db_path, "data_warranty_claims.json", {"W1": {"status": "pending", "user_id": 5}})

    client.post(
        "/admin/support/update",
        data={
            "csrf_token": csrf_of(token),
            "entity": "warranty",
            "item_id": "W1",
            "status": "resolved",
            "admin_note": "Đã đổi tài khoản",
        },
        follow_redirects=False,
    )
    claim = read_kv(db_path, "data_warranty_claims.json")["W1"]
    assert claim["status"] == "resolved" and claim["admin_note"] == "Đã đổi tài khoản"


def test_clear_all_pending_manual(web):
    client, token, db_path = web
    seed(db_path, "data_pending_manual_orders.json", {"A": {"amount": 1}, "B": {"amount": 2}})

    client.post(
        "/admin/ops/pending-manual",
        data={"csrf_token": csrf_of(token), "mode": "clear_all"},
        follow_redirects=False,
    )
    assert read_kv(db_path, "data_pending_manual_orders.json") == {}


# --- Audit ------------------------------------------------------------------

def test_actions_are_written_to_audit_log(web):
    client, token, db_path = web
    client.post(
        "/admin/coupons/save",
        data={
            "csrf_token": csrf_of(token),
            "mode": "add",
            "code": "AUDIT1",
            "discount": "1000",
            "quantity": "1",
            "days": "1",
        },
        follow_redirects=False,
    )
    log = read_kv(db_path, "data_admin_action_log.json")
    assert log[-1]["action"] == "coupon" and log[-1]["ok"] is True


def test_audit_log_never_stores_csrf_token(web):
    client, token, db_path = web
    client.post(
        "/admin/coupons/save",
        data={"csrf_token": csrf_of(token), "mode": "add", "code": "SAFE", "discount": "1"},
        follow_redirects=False,
    )
    assert "csrf_token" not in read_kv(db_path, "data_admin_action_log.json")[-1]["details"]


# --- Trang hiển thị ---------------------------------------------------------

@pytest.mark.parametrize(
    "path",
    [
        "/admin",
        "/admin/products",
        "/admin/products/new",
        "/admin/categories",
        "/admin/orders",
        "/admin/users",
        "/admin/partners",
        "/admin/coupons",
        "/admin/support",
        "/admin/ops",
        "/admin/audit",
    ],
)
def test_every_page_renders_on_empty_database(web, path):
    client, _token, _db = web
    response = client.get(path)
    assert response.status_code == 200


def test_missing_product_returns_404_page(web):
    client, _token, _db = web
    response = client.get("/admin/products/khong-ton-tai")
    assert response.status_code == 404
    assert "Không tìm thấy" in response.text
