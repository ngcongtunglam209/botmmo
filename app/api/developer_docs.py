from pathlib import Path

try:
    from fastapi.openapi.docs import get_swagger_ui_html
except ImportError:
    get_swagger_ui_html = None


_API_DOCS_DIR = Path(__file__).resolve().parent
_API_DOCS_TEMPLATE = _API_DOCS_DIR / "templates" / "api_docs.html"
_API_DOCS_STATIC = _API_DOCS_DIR / "static"


def _read_api_docs_asset(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@app.get("/docs", include_in_schema=False)
async def api_developer_docs():
    return HTMLResponse(
        _read_api_docs_asset(_API_DOCS_TEMPLATE),
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/docs/assets/api-docs.css", include_in_schema=False)
async def api_developer_docs_css():
    return Response(
        _read_api_docs_asset(_API_DOCS_STATIC / "api-docs.css"),
        media_type="text/css; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/docs/assets/api-docs.js", include_in_schema=False)
async def api_developer_docs_js():
    return Response(
        _read_api_docs_asset(_API_DOCS_STATIC / "api-docs.js"),
        media_type="application/javascript; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/reference", include_in_schema=False)
async def api_swagger_reference():
    if get_swagger_ui_html is None:
        return HTMLResponse(
            "<h1>API Reference is unavailable</h1><p>FastAPI is not installed.</p>",
            status_code=503,
        )
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Dino Store API Reference",
        swagger_favicon_url="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22><text y=%22.9em%22 font-size=%2290%22>🦖</text></svg>",
        swagger_ui_parameters={
            "deepLinking": True,
            "displayRequestDuration": True,
            "filter": True,
            "persistAuthorization": True,
        },
    )
