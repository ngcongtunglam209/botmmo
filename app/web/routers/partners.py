"""API partner: danh sách, chi tiết ví/quota, export CSV."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from .. import actions, deps
from ..repo import partners
from ..repo.base import as_int
from ..templating import render
from .common import flash_from, handle_action

router = APIRouter(tags=["Admin"], dependencies=[Depends(deps.require_admin)])

PARTNERS_PATH = "/admin/partners"


def _row(api_key: str, record: dict) -> dict:
    return {
        "api_key": api_key,
        "public_id": partners.public_id(api_key),
        "masked": partners.masked(api_key),
        "name": str(record.get("name") or "—"),
        "balance": as_int(record.get("balance"), 0),
        "active": partners.is_active(record),
        "low_balance": partners.is_low_balance(record),
        "rate_limit": partners.rate_limit(record),
        "threshold": partners.low_balance_threshold(record),
        "allowed_ips": partners.normalize_allowed_ips(record.get("allowed_ips")),
        "alert_enabled": record.get("low_balance_alert_enabled") is not False,
        "admin_note": str(record.get("admin_note") or ""),
        "rotated_to": str(record.get("rotated_to") or ""),
    }


def _find_by_public_id(public_id: str) -> tuple[str, dict] | None:
    for api_key, record in partners.all_keys().items():
        if partners.public_id(api_key) == public_id:
            return api_key, record
    return None


@router.get(PARTNERS_PATH)
async def partners_page(request: Request):
    status = str(request.query_params.get("status") or "").strip()
    search = str(request.query_params.get("q") or "").strip().casefold()

    rows = []
    for api_key, record in partners.all_keys().items():
        row = _row(api_key, record)
        if status == "active" and not row["active"]:
            continue
        if status == "disabled" and row["active"]:
            continue
        if status == "low" and not row["low_balance"]:
            continue
        if search and search not in f"{row['name']} {row['public_id']}".casefold():
            continue
        rows.append(row)
    rows.sort(key=lambda row: (not row["active"], -row["balance"]))

    return render(
        request,
        "partners/list.html",
        {
            "rows": rows,
            "total": len(partners.all_keys()),
            "active_count": sum(1 for row in rows if row["active"]),
            "analytics": partners.analytics("", 14),
            "status": status,
            "search": request.query_params.get("q") or "",
            "flash": flash_from(request),
        },
    )


@router.get("/admin/partners/{public_id}")
async def partner_detail(request: Request, public_id: str):
    found = _find_by_public_id(public_id)
    if found is None:
        return render(
            request, "not_found.html", {"entity": "API partner", "item_id": public_id},
            status_code=404,
        )
    api_key, record = found
    return render(
        request,
        "partners/detail.html",
        {
            "row": _row(api_key, record),
            "analytics": partners.analytics(api_key, 14),
            "traffic": partners.daily_traffic(api_key, 14),
            "ledger": partners.ledger(api_key, 40),
            "logs": partners.request_logs(api_key, 40),
            "flash": flash_from(request),
        },
    )


@router.post("/admin/partners/manage")
async def partner_manage(request: Request):
    return await handle_action(
        request, "api_partner", actions.manage_partner, PARTNERS_PATH, "target"
    )


@router.post("/admin/partners/{public_id}/manage")
async def partner_manage_one(request: Request, public_id: str):
    return await handle_action(
        request,
        "api_partner",
        actions.manage_partner,
        f"{PARTNERS_PATH}/{public_id}",
        "target",
    )


@router.get("/admin/partners.csv", include_in_schema=False)
async def partners_export(request: Request):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "public_id", "partner", "balance_vnd", "status", "allowed_ips",
            "rate_limit_per_minute", "low_balance_threshold", "alert_enabled", "admin_note",
        ]
    )
    for api_key, record in partners.all_keys().items():
        row = _row(api_key, record)
        writer.writerow(
            [
                row["public_id"], row["name"], row["balance"],
                "active" if row["active"] else "revoked",
                ";".join(row["allowed_ips"]), row["rate_limit"], row["threshold"],
                "yes" if row["alert_enabled"] else "no", row["admin_note"],
            ]
        )
    return Response(
        content="﻿" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="lamshop-api-partners.csv"',
            "Cache-Control": "no-store",
        },
    )
