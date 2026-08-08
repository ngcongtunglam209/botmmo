"""Tổng quan, user, đơn hàng, coupon, hỗ trợ, vận hành, audit."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request

from .. import actions, bridge, deps, domain
from ..repo import audit, catalog, orders, partners, promo, support, users
from ..repo.base import as_int
from ..settings import get_settings
from ..templating import render
from .common import flash_from, handle_action

router = APIRouter(tags=["Admin"], dependencies=[Depends(deps.require_admin)])


@router.get("/admin")
async def dashboard(request: Request):
    settings = get_settings()
    finance = orders.financial_summary()
    keys = partners.all_keys()
    active_keys = sum(1 for record in keys.values() if partners.is_active(record))
    category_names = catalog.category_names()

    metrics = [
        ("Doanh thu hôm nay", f"{finance['today_revenue']:,} VND", "revenue", "/admin/orders"),
        ("Lãi gộp hôm nay", f"{finance['today_profit']:,} VND", "revenue", "/admin/orders"),
        ("Tổng doanh thu", f"{finance['revenue']:,} VND", "revenue", "/admin/orders"),
        ("Đơn thành công", f"{finance['completed']:,}", "orders", "/admin/orders"),
        ("Độ phủ giá vốn", f"{finance['costed']}/{finance['completed']}", "revenue", "/admin/orders"),
        ("Chờ thanh toán", f"{len(orders.pending()):,}", "orders", "/admin/orders"),
        ("Manual pending", f"{len(orders.pending_manual()):,}", "orders", "/admin/ops"),
        ("Sản phẩm", f"{catalog.count_products():,}", "products", "/admin/products"),
        ("Sắp hết hàng", f"{len(catalog.low_stock_products()):,}", "products", "/admin/products?kind=local"),
        ("Users", f"{users.count_users():,}", "users", "/admin/users"),
        ("Đang bị ban", f"{len(users.banned_ids()):,}", "users", "/admin/users?status=banned"),
        ("API partner bật", f"{active_keys}/{len(keys)}", "api", "/admin/partners"),
        ("Số dư API", f"{sum(as_int(r.get('balance'), 0) for r in keys.values()):,} VND", "api", "/admin/partners"),
        ("Coupon", f"{len(promo.all_coupons()):,}", "promo", "/admin/coupons"),
        ("Promo hôm nay", f"{promo.promo_spent_today():,} VND", "promo", "/admin/coupons"),
        ("Ticket đang mở", f"{support.open_count():,}", "support", "/admin/support"),
        ("Ảnh danh mục", f"{catalog.categories_with_image(category_names)}/{len(category_names)}", "products", "/admin/categories"),
        ("Bot uptime", _uptime_text(), "support", "/admin/ops"),
    ]

    return render(
        request,
        "dashboard.html",
        {
            "metrics": metrics,
            "chart": _chart_points(orders.revenue_by_day(30)),
            "recent_orders": orders.recent(8),
            "open_tickets": [row for row in support.rows(6) if row["open"]],
            "recent_audit": audit.recent(6),
            "maintenance": bridge.read_flag("maintenance_mode", False),
            "ai_auto_reply": bridge.read_flag("ai_auto_reply", True),
            "settings": settings,
            "flash": flash_from(request),
        },
    )


def _uptime_text() -> str:
    started = bridge.bot_start_time(0.0)
    if started <= 0:
        return "—"
    seconds = int(time.time() - started)
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    if days:
        return f"{days}d {hours}h"
    return f"{hours}h {rest // 60}m"


def _chart_points(series: list[tuple[str, int]]) -> dict:
    """Chuẩn bị dữ liệu để template vẽ SVG mà không cần thư viện ngoài."""
    if not series:
        return {"points": "", "labels": [], "max": 0, "series": []}
    peak = max(value for _, value in series) or 1
    step = 100 / max(1, len(series) - 1)
    points = " ".join(
        f"{index * step:.2f},{100 - (value * 100 / peak):.2f}"
        for index, (_, value) in enumerate(series)
    )
    return {"points": points, "max": peak, "series": series}


# --- Users ------------------------------------------------------------------

@router.get("/admin/users")
async def users_page(request: Request):
    search = str(request.query_params.get("q") or "").strip().casefold()
    status = str(request.query_params.get("status") or "").strip()
    banned = users.banned_ids()

    rows = []
    for user_id, profile in users.all_users().items():
        is_banned = user_id in banned
        if status == "banned" and not is_banned:
            continue
        if status == "active" and is_banned:
            continue
        haystack = f"{user_id} {profile.get('username') or ''} {profile.get('full_name') or ''}"
        if search and search not in haystack.casefold():
            continue
        rows.append(
            {
                "id": user_id,
                "name": str(profile.get("full_name") or profile.get("username") or "—"),
                "username": str(profile.get("username") or ""),
                "balance": as_int(profile.get("balance"), 0),
                "orders": len(orders.user_orders(user_id, limit=9999)),
                "banned": is_banned,
            }
        )
    rows.sort(key=lambda row: row["balance"], reverse=True)
    return render(
        request,
        "users/list.html",
        {
            "rows": rows[: get_settings().user_table_limit],
            "total": users.count_users(),
            "search": request.query_params.get("q") or "",
            "status": status,
            "flash": flash_from(request),
        },
    )


@router.get("/admin/users/{user_id}")
async def user_detail(request: Request, user_id: str):
    profile = users.get_user(user_id)
    if profile is None:
        return render(
            request, "not_found.html", {"entity": "User", "item_id": user_id}, status_code=404
        )
    return render(
        request,
        "users/detail.html",
        {
            "user_id": user_id,
            "profile": profile,
            "balance": as_int(profile.get("balance"), 0),
            "banned": users.is_banned(user_id),
            "orders": orders.user_orders(user_id, limit=30),
            "transactions": users.transactions_for(user_id, limit=30),
            "flash": flash_from(request),
        },
    )


@router.post("/admin/users/{user_id}/balance")
async def user_balance(request: Request, user_id: str):
    return await handle_action(
        request, "user_balance", actions.update_user_balance,
        f"/admin/users/{user_id}", "user_id",
    )


@router.post("/admin/users/{user_id}/ban")
async def user_ban(request: Request, user_id: str):
    return await handle_action(
        request, "user_ban", actions.set_user_ban, f"/admin/users/{user_id}", "user_id"
    )


@router.post("/admin/users/{user_id}/profile")
async def user_profile(request: Request, user_id: str):
    return await handle_action(
        request, "user_profile", actions.update_user_profile,
        f"/admin/users/{user_id}", "user_id",
    )


# --- Đơn hàng ---------------------------------------------------------------

@router.get("/admin/orders")
async def orders_page(request: Request):
    search = str(request.query_params.get("q") or "").strip()
    needle = search.casefold()
    rows = []
    for order in orders.recent(get_settings().order_table_limit):
        code = domain.order_code(order)
        haystack = f"{code} {order.get('product_name') or ''} {order.get('user_id') or ''}"
        if needle and needle not in haystack.casefold():
            continue
        rows.append(
            {
                "code": code,
                "product": str(order.get("product_name") or "—"),
                "user_id": order.get("user_id") or order.get("buyer_id") or "",
                "status": domain.status_text(order.get("status")) or "—",
                "amount": as_int(order.get("amount"), 0),
                "quantity": as_int(order.get("quantity"), 1),
                "timestamp": domain.order_timestamp(order),
                "completed": domain.is_completed_order(order),
            }
        )
    return render(
        request,
        "orders/list.html",
        {
            "rows": rows,
            "total": orders.count_history(),
            "search": search,
            "pending_count": len(orders.pending()),
            "flash": flash_from(request),
        },
    )


@router.get("/admin/orders/{order_code}")
async def order_detail(request: Request, order_code: str):
    order = orders.find(order_code)
    if order is None:
        return render(
            request, "not_found.html", {"entity": "Đơn hàng", "item_id": order_code},
            status_code=404,
        )
    return render(
        request,
        "orders/detail.html",
        {
            "order_code": domain.order_code(order) or order_code.upper(),
            "order": order,
            "amount": as_int(order.get("amount"), 0),
            "status": domain.status_text(order.get("status")),
            "completed": domain.is_completed_order(order),
            "timestamp": domain.order_timestamp(order),
            "flash": flash_from(request),
        },
    )


@router.post("/admin/orders/{order_code}/update")
async def order_update(request: Request, order_code: str):
    return await handle_action(
        request, "order_tools", actions.update_order,
        f"/admin/orders/{order_code}", "order_code",
    )


# --- Coupon -----------------------------------------------------------------

@router.get("/admin/coupons")
async def coupons_page(request: Request):
    rows = [
        {
            "code": code,
            "discount": as_int(data.get("discount"), 0),
            "quantity": as_int(data.get("quantity"), 0),
            "used": as_int(data.get("used"), 0),
            "expires": str(data.get("expires") or "—"),
        }
        for code, data in sorted(promo.all_coupons().items())
    ]
    return render(
        request,
        "coupons.html",
        {"rows": rows, "snapshot": promo.snapshot(), "flash": flash_from(request)},
    )


@router.post("/admin/coupons/save")
async def coupon_save(request: Request):
    return await handle_action(
        request, "coupon", actions.manage_coupon, "/admin/coupons", "code"
    )


# --- Hỗ trợ -----------------------------------------------------------------

@router.get("/admin/support")
async def support_page(request: Request):
    return render(
        request,
        "support.html",
        {
            "rows": support.rows(120),
            "labels": support.LABELS,
            "open_count": support.open_count(),
            "flash": flash_from(request),
        },
    )


@router.post("/admin/support/update")
async def support_update(request: Request):
    return await handle_action(
        request, "support_update", actions.update_support, "/admin/support", "item_id"
    )


# --- Vận hành ---------------------------------------------------------------

@router.get("/admin/ops")
async def ops_page(request: Request):
    pending_manual = [
        {
            "code": code,
            "product": str(record.get("product_name") or record.get("product_id") or "—"),
            "user_id": record.get("user_id") or "",
            "amount": as_int(record.get("amount"), 0),
            "timestamp": domain.order_timestamp(record),
        }
        for code, record in orders.pending_manual().items()
        if isinstance(record, dict)
    ]
    pending_manual.sort(key=lambda row: row["timestamp"], reverse=True)
    return render(
        request,
        "ops.html",
        {
            "maintenance": bridge.read_flag("maintenance_mode", False),
            "ai_auto_reply": bridge.read_flag("ai_auto_reply", True),
            "pending_manual": pending_manual,
            "pending_payment": len(orders.pending()),
            "log_lines": _tail_log(),
            "uptime": _uptime_text(),
            "flash": flash_from(request),
        },
    )


def _tail_log(max_lines: int = 60) -> list[str]:
    from ..settings import PROJECT_ROOT

    for candidate in (PROJECT_ROOT / "bot.log", get_settings().log_dir / "bot.log"):
        if candidate.is_file():
            try:
                lines = candidate.read_text("utf-8", errors="replace").splitlines()
            except OSError:
                continue
            return [domain.plain_text(line) for line in lines[-max_lines:]]
    return []


@router.post("/admin/ops/toggle")
async def ops_toggle(request: Request):
    return await handle_action(
        request, "system_toggle", actions.toggle_system, "/admin/ops", "mode"
    )


@router.post("/admin/ops/pending-manual")
async def ops_pending_manual(request: Request):
    return await handle_action(
        request, "pending_manual", actions.clear_pending_manual, "/admin/ops", "order_code"
    )


# --- Audit ------------------------------------------------------------------

@router.get("/admin/audit")
async def audit_page(request: Request):
    return render(
        request,
        "audit.html",
        {"rows": audit.recent(get_settings().audit_limit), "flash": flash_from(request)},
    )
