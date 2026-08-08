"""Catalog lệnh admin: trang HTML và endpoint JSON cho tooling."""

from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from .. import commands, deps
from ..templating import render
from .common import flash_from

router = APIRouter(tags=["Admin"])


@router.get("/admin/commands", dependencies=[Depends(deps.require_admin)])
async def commands_page(request: Request):
    groups = commands.grouped_commands()
    return render(
        request,
        "commands.html",
        {
            "groups": groups,
            "total": len(commands.flat_commands()),
            "flash": flash_from(request),
        },
    )


@router.get("/api/admin/commands")
async def commands_api(
    x_api_key: str = Header(None),
    authorization: str = Header(None),
):
    """Yêu cầu master admin key giống endpoint cũ."""
    secret = str(os.getenv("API_SECRET_KEY", "") or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="API secret not configured")

    supplied = str(x_api_key or "").strip()
    if not supplied and authorization:
        parts = str(authorization).split(" ", 1)
        supplied = parts[1].strip() if len(parts) == 2 else parts[0].strip()
    if not supplied:
        raise HTTPException(status_code=401, detail="Missing API Key")
    if not hmac.compare_digest(supplied, secret):
        raise HTTPException(status_code=403, detail="Admin API key required")

    flat = commands.flat_commands()
    return {
        "ok": True,
        "data": {
            "groups": commands.COMMAND_GROUPS,
            "commands": flat,
            "total": len(flat),
        },
    }
