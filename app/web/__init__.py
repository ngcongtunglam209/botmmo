"""Web admin mới.

Không đi qua runtime_loader: import bình thường, khởi tạo bằng create_app().
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .db import ensure_schema
from .deps import LoginRequired
from .settings import WEB_ROOT, get_settings

logger = logging.getLogger(__name__)


def create_app(mount_static: bool = True) -> FastAPI:
    """Tạo app admin độc lập, dùng được cả khi mount vào app chính."""
    app = FastAPI(
        title="Lâm Shop Admin",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    register(app, mount_static=mount_static)
    return app


def register(app: FastAPI, mount_static: bool = True) -> None:
    """Gắn router, static và exception handler của web admin vào một app FastAPI."""
    from .routers import admin, auth, catalog, commands, partners

    ensure_schema()
    get_settings()

    for router in (
        auth.router,
        admin.router,
        catalog.router,
        partners.router,
        commands.router,
    ):
        # /reference là trang công khai cho đối tác; không liệt kê đường quản trị
        # ở đó. Endpoint admin nào cần lộ schema thì tự bật include_in_schema.
        app.include_router(router, include_in_schema=False)

    if mount_static:
        app.mount(
            "/admin/static",
            StaticFiles(directory=str(WEB_ROOT / "static")),
            name="admin_static",
        )

    @app.exception_handler(LoginRequired)
    async def _login_required(request: Request, exc: LoginRequired):
        del exc
        target = request.url.path
        suffix = f"?next={target}" if target.startswith("/admin") else ""
        return RedirectResponse(f"/admin/login{suffix}", status_code=303)

    @app.exception_handler(HTTPException)
    async def _http_error(request: Request, exc: HTTPException):
        """Lỗi trong khu /admin trả HTML để admin đọc được, còn lại giữ JSON.

        Handler này thay handler mặc định của toàn app, nên đường không phải
        /admin phải được chuyển tiếp *tường minh* sang handler mặc định. Nếu chỉ
        `raise exc` thì lỗi bay thẳng ra ngoài và Partner API trả 500 thay vì
        401/404.
        """
        if not request.url.path.startswith("/admin"):
            from fastapi.exception_handlers import http_exception_handler

            return await http_exception_handler(request, exc)
        from .templating import render

        return render(
            request,
            "error.html",
            {"status_code": exc.status_code, "detail": exc.detail},
            status_code=exc.status_code,
        )

    @app.get("/admin/health", include_in_schema=False)
    async def health() -> HTMLResponse:
        return HTMLResponse("ok")
