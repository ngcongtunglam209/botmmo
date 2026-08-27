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

    chart = _chart_bars(orders.revenue_by_day(30))
    pending_payment = len(orders.pending())
    pending_manual = len(orders.pending_manual())
    low_stock = len(catalog.low_stock_products())
    banned = len(users.banned_ids())
    open_tickets = support.open_count()
    api_balance = sum(as_int(record.get("balance"), 0) for record in keys.values())

    # Bốn con số dẫn dắt trang; phần còn lại xuống lưới chỉ số phụ.
    figures = [
        {
            "label": "Doanh thu hôm nay",
            "value": f"{finance['today_revenue']:,}",
            "unit": "VND",
            "note": f"Lãi gộp {finance['today_profit']:,} VND",
        },
        {
            "label": "Doanh thu 30 ngày",
            "value": f"{chart['total']:,}",
            "unit": "VND",
            "note": f"Ngày cao nhất {chart['max']:,} VND",
        },
        {
            "label": "Tổng doanh thu",
            "value": f"{finance['revenue']:,}",
            "unit": "VND",
            "note": f"{finance['completed']:,} đơn thành công",
        },
        {
            "label": "Cần xử lý",
            "value": f"{pending_payment + pending_manual:,}",
            "unit": "đơn",
            "note": f"{pending_payment:,} chờ thanh toán · {pending_manual:,} chờ làm tay",
        },
    ]

    stat_groups = [
        {
            "label": "Đơn hàng",
            "items": [
                ("Đơn thành công", f"{finance['completed']:,}", "", "/admin/orders?status=completed"),
                ("Chờ thanh toán", f"{pending_payment:,}", "", "/admin/orders?status=payment"),
                ("Chờ làm tay", f"{pending_manual:,}", "", "/admin/orders?status=manual"),
                ("Độ phủ giá vốn", f"{finance['costed']}/{finance['completed']}", "đơn", "/admin/orders"),
            ],
        },
        {
            "label": "Kho & danh mục",
            "items": [
                ("Sản phẩm", f"{catalog.count_products():,}", "", "/admin/products"),
                ("Sắp hết hàng", f"{low_stock:,}", "", "/admin/products?kind=local"),
                ("Danh mục", f"{len(category_names):,}", "", "/admin/categories"),
                (
                    "Danh mục có ảnh",
                    f"{catalog.categories_with_image(category_names)}/{len(category_names)}",
                    "",
                    "/admin/categories",
                ),
            ],
        },
        {
            "label": "Khách & đối tác",
            "items": [
                ("Users", f"{users.count_users():,}", "", "/admin/users"),
                ("Đang bị ban", f"{banned:,}", "", "/admin/users?status=banned"),
                ("API partner bật", f"{active_keys}/{len(keys)}", "", "/admin/partners"),
                ("Số dư API", f"{api_balance:,}", "VND", "/admin/partners"),
            ],
        },
        {
            "label": "Khuyến mãi & vận hành",
            "items": [
                ("Coupon", f"{len(promo.all_coupons()):,}", "", "/admin/coupons"),
                ("Promo hôm nay", f"{promo.promo_spent_today():,}", "VND", "/admin/coupons"),
                ("Ticket đang mở", f"{open_tickets:,}", "", "/admin/support"),
                ("Bot uptime", _uptime_text(), "", "/admin/ops"),
            ],
        },
    ]

    return render(
        request,
        "dashboard.html",
        {
            "figures": figures,
            "stat_groups": stat_groups,
            "chart": chart,
            "recent_orders": orders.recent(8),
            "open_tickets": [row for row in support.rows(6) if row["open"]],
            "recent_audit": audit.recent(6),
            "nav_counts": {
                "/admin/orders": pending_payment + pending_manual or "",
                "/admin/support": open_tickets or "",
            },
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


def _chart_bars(series: list[tuple[str, int]]) -> dict:
    """Dữ liệu biểu đồ cột — template vẽ bằng div, không cần thư viện ngoài."""
    if not series:
        return {"bars": [], "max": 0, "total": 0, "first": "", "last": ""}
    peak = max(value for _, value in series) or 1
    bars = [
        {
            "day": day,
            "value": value,
            # Cột 0 đồng vẫn giữ 2% chiều cao để nhìn ra là có ngày đó.
            "pct": round(max(value * 100 / peak, 2), 2),
            "zero": value <= 0,
        }
        for day, value in series
    ]
    return {
        "bars": bars,
        "max": peak,
        "total": sum(value for _, value in series),
        "first": series[0][0],
        "last": series[-1][0],
    }


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

ORDER_STATUS_FILTERS = ("pending", "payment", "manual", "completed")

PENDING_KIND_LABEL = {"payment": "Chờ thanh toán", "manual": "Chờ xử lý tay"}


def _order_row(order: dict, *, kind: str, code: str = "", status: str = "") -> dict:
    return {
        "code": code or domain.order_code(order),
        "kind": kind,
        "product": str(order.get("product_name") or order.get("product_id") or "—"),
        "user_id": order.get("user_id") or order.get("buyer_id") or "",
        "status": status or domain.status_text(order.get("status")) or "—",
        "amount": as_int(order.get("amount"), 0),
        "quantity": as_int(order.get("quantity"), 1),
        "timestamp": domain.order_timestamp(order),
        "completed": domain.is_completed_order(order),
    }


def _order_matches(row: dict, needle: str) -> bool:
    if not needle:
        return True
    haystack = f"{row['code']} {row['product']} {row['user_id']} {row['status']}"
    return needle in haystack.casefold()


@router.get("/admin/orders")
async def orders_page(request: Request):
    search = str(request.query_params.get("q") or "").strip()
    status_filter = str(request.query_params.get("status") or "").strip().lower()
    if status_filter not in ORDER_STATUS_FILTERS:
        status_filter = ""
    needle = search.casefold()

    pending_rows = []
    if status_filter != "completed":
        for entry in orders.pending_all():
            if status_filter in ("payment", "manual") and entry["kind"] != status_filter:
                continue
            pending_rows.append(
                _order_row(
                    entry["record"],
                    kind=entry["kind"],
                    code=entry["code"],
                    status=PENDING_KIND_LABEL[entry["kind"]],
                )
            )

    # Đơn manual còn treo có thể đã có bản ghi trong order_history — bản pending
    # mới là bản đang chờ xử lý nên nó thắng.
    pending_codes = {row["code"].upper() for row in pending_rows}
    history_rows = []
    if status_filter in ("", "completed"):
        for order in orders.recent(get_settings().order_table_limit):
            row = _order_row(order, kind="history")
            if row["code"].upper() in pending_codes:
                continue
            if status_filter == "completed" and not row["completed"]:
                continue
            history_rows.append(row)

    rows = [row for row in pending_rows + history_rows if _order_matches(row, needle)]
    rows.sort(key=lambda row: row["timestamp"], reverse=True)

    return render(
        request,
        "orders/list.html",
        {
            "rows": rows,
            "total": orders.count_history(),
            "search": search,
            "status_filter": status_filter,
            "pending_count": len(orders.pending()),
            "pending_manual_count": len(orders.pending_manual()),
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
    normalized_code = order_code.strip().upper()
    pending_kind = next(
        (row["kind"] for row in orders.pending_all() if row["code"] == normalized_code), ""
    )

    return render(
        request,
        "orders/detail.html",
        {
            "order_code": domain.order_code(order) or normalized_code,
            "order": order,
            "pending_kind": pending_kind,
            "pending_label": PENDING_KIND_LABEL.get(pending_kind, ""),
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
    path = get_settings().log_file
    if not path.is_file():
        return []
    try:
        lines = path.read_text("utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [domain.plain_text(line) for line in lines[-max_lines:]]


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
