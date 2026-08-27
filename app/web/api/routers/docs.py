"""Trang tài liệu cho đối tác: /docs (tự viết) và /reference (Swagger UI)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

router = APIRouter()

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
# Dùng chung bộ font đã self-host với web admin, không nhân đôi file .woff2.
FONTS_DIR = Path(__file__).resolve().parents[2] / "static" / "fonts"

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


@lru_cache(maxsize=1)
def _fonts_css() -> str:
    return (FONTS_DIR / "fonts.css").read_text(encoding="utf-8").replace(
        "/admin/static/fonts/", "/docs/assets/fonts/"
    )


@lru_cache(maxsize=1)
def _font_names() -> frozenset[str]:
    """Danh sách file font được phép phục vụ, quét một lần lúc gọi đầu tiên.

    Trang /docs là trang công khai nên phải chốt allowlist thay vì ghép thẳng
    tên file vào đường dẫn — tránh đọc ngược ra ngoài thư mục font.
    """
    if not FONTS_DIR.is_dir():
        return frozenset()
    return frozenset(path.name for path in FONTS_DIR.glob("*.woff2"))


@router.get("/docs/assets/fonts.css", include_in_schema=False)
async def developer_docs_fonts_css():
    """Cùng một fonts.css với admin, chỉ đổi tiền tố URL sang đường công khai."""
    css = _fonts_css()
    return Response(
        css,
        media_type="text/css; charset=utf-8",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/docs/assets/fonts/{name}", include_in_schema=False)
async def developer_docs_font(name: str):
    if name not in _font_names():
        raise HTTPException(status_code=404, detail="Không có font này")
    return Response(
        (FONTS_DIR / name).read_bytes(),
        media_type="font/woff2",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
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
