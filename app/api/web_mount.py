"""Gan toan bo tang HTTP vao app FastAPI dung chung.

File nay nam trong SECTION_FILES nen runtime_loader nap no, nhung no khong dung
bien global nao cua loader ngoai `app` va `logger`. Day la toan bo cho ha tang
cu cham vao package app/web.

Truoc day cho nay la admin_web.py (4519 dong), routes_core.py, routes_v2.py va
developer_docs.py, tat ca khai bao route bang decorator ben trong file duoc exec.
"""

from app.web import register as _register_admin_web
from app.web.api import register as _register_partner_api

_register_admin_web(app)  # noqa: F821 — `app` do runtime_loader cung cap
_register_partner_api(app)  # noqa: F821

logger.info(  # noqa: F821
    "HTTP layer da gan: /admin (Jinja2 + SQLite repo), /api/v1, /api/v2, /docs"
)
