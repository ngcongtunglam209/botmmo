"""Trang tài liệu cho đối tác: /docs (tự viết) và /reference (Swagger UI)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

router = APIRouter()

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

SWAGGER_FAVICON = (
    "data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22>"
    "<text y=%22.9em%22 font-size=%2290%22>🦖</text></svg>"
)


@lru_cache(maxsize=8)
def _asset(name: str) -> str:
    """Đọc một lần rồi cache: asset tĩnh, không đổi giữa các request."""
    return (STATIC_DIR / name).read_text(encoding="utf-8")


@router.get("/docs", include_in_schema=False)
async def developer_docs():
    return HTMLResponse(_asset("docs.html"), headers={"Cache-Control": "no-cache"})


@router.get("/docs/assets/api-docs.css", include_in_schema=False)
async def developer_docs_css():
    return Response(
        _asset("api-docs.css"),
        media_type="text/css; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/docs/assets/api-docs.js", include_in_schema=False)
async def developer_docs_js():
    return Response(
        _asset("api-docs.js"),
        media_type="application/javascript; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/reference", include_in_schema=False)
async def swagger_reference(request: Request):
    from fastapi.openapi.docs import get_swagger_ui_html

    openapi_url = request.app.openapi_url or "/openapi.json"
    return get_swagger_ui_html(
        openapi_url=openapi_url,
        title="Lâm Shop API Reference",
        swagger_favicon_url=SWAGGER_FAVICON,
        swagger_ui_parameters={
            "deepLinking": True,
            "displayRequestDuration": True,
            "filter": True,
            "persistAuthorization": True,
        },
    )
