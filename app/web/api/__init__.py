"""Partner API — tầng HTTP sạch, nghiệp vụ đơn hàng đi qua `engine`."""

from __future__ import annotations

from fastapi import FastAPI


def register(app: FastAPI) -> None:
    """Gắn toàn bộ router Partner API vào app.

    Thứ tự quan trọng: v2 phải vào trước v1 và core, vì `/api/v2/orders/{code}`
    dễ nuốt các đường cụ thể hơn nếu đăng ký sai thứ tự.
    """
    from .routers import core, docs, v1, v2

    for router in (v2.router, v1.router, core.router, docs.router):
        app.include_router(router)
