"""Sản phẩm, danh mục và ảnh."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, Response

from .. import actions, deps, domain
from ..repo import catalog, orders
from ..repo.base import as_int
from ..settings import get_settings
from ..templating import render
from .common import flash_from, handle_action, run_async_action

router = APIRouter(tags=["Admin"], dependencies=[Depends(deps.require_admin)])

PRODUCTS_PATH = "/admin/products"
CATEGORIES_PATH = "/admin/categories"


def _product_rows(search: str, kind: str, limit: int) -> list[dict]:
    pending_manual = orders.pending_manual()
    pending_by_product: dict[str, int] = {}
    for record in pending_manual.values():
        if isinstance(record, dict):
            pid = str(record.get("product_id") or "")
            pending_by_product[pid] = pending_by_product.get(pid, 0) + 1

    rows = []
    needle = search.casefold()
    for pid, product in catalog.all_products().items():
        product_kind = domain.product_type(product)
        if kind and product_kind != kind:
            continue
        haystack = f"{pid} {product.get('name') or ''} {domain.product_category(product)}"
        if needle and needle not in haystack.casefold():
            continue
        rows.append(
            {
                "id": pid,
                "name": str(product.get("name") or pid),
                "kind": product_kind,
                "price": as_int(product.get("price"), 0),
                "cost_price": as_int(product.get("cost_price"), 0),
                "category": domain.product_category(product),
                "stock": domain.stock_count(product),
                "pending": pending_by_product.get(pid, 0),
                "has_image": catalog.product_image_path(pid) is not None,
            }
        )
    rows.sort(key=lambda row: row["name"].casefold())
    return rows[:limit]


@router.get(PRODUCTS_PATH)
async def products_page(request: Request):
    search = str(request.query_params.get("q") or "").strip()
    kind = str(request.query_params.get("kind") or "").strip()
    limit = get_settings().product_table_limit
    rows = _product_rows(search, kind, limit)
    return render(
        request,
        "products/list.html",
        {
            "rows": rows,
            "total": catalog.count_products(),
            "search": search,
            "kind": kind,
            "categories": catalog.category_names(),
            "flash": flash_from(request),
        },
    )


@router.get("/admin/products/new")
async def product_new(request: Request):
    return render(
        request,
        "products/new.html",
        {"categories": catalog.category_names(), "flash": flash_from(request)},
    )


@router.get("/admin/products/{product_id}")
async def product_detail(request: Request, product_id: str):
    product = catalog.get_product(product_id)
    if product is None:
        return render(
            request,
            "not_found.html",
            {"entity": "Sản phẩm", "item_id": product_id},
            status_code=404,
        )
    stock_items = product.get("stock") if isinstance(product.get("stock"), list) else []
    return render(
        request,
        "products/detail.html",
        {
            "product_id": product_id,
            "product": product,
            "category": domain.product_category(product),
            "categories": catalog.category_names(),
            "kind": domain.product_type(product),
            "stock_items": stock_items[:200],
            "stock_total": len(stock_items),
            "image_url": f"/admin/product-image/{product_id}?t={int(time.time())}",
            "has_image": catalog.product_image_path(product_id) is not None,
            "flash": flash_from(request),
        },
    )


@router.post("/admin/products/create")
async def product_create(request: Request):
    return await handle_action(
        request, "product_create", actions.create_product, PRODUCTS_PATH, "product_id"
    )


@router.post("/admin/products/{product_id}/update")
async def product_update(request: Request, product_id: str):
    return await handle_action(
        request,
        "product_update",
        actions.update_product,
        f"{PRODUCTS_PATH}/{product_id}",
        "product_id",
    )


@router.post("/admin/products/{product_id}/clear-stock")
async def product_clear_stock(request: Request, product_id: str):
    return await handle_action(
        request,
        "product_stock",
        actions.clear_product_stock,
        f"{PRODUCTS_PATH}/{product_id}",
        "product_id",
    )


@router.post("/admin/products/{product_id}/delete")
async def product_delete(request: Request, product_id: str):
    return await handle_action(
        request, "product_delete", actions.delete_product, PRODUCTS_PATH, "product_id"
    )


@router.post("/admin/products/{product_id}/image")
async def product_image_upload(request: Request, product_id: str):
    async def handler(form):
        return await _store_upload(
            form.get("image"), get_settings().product_image_dir, product_id, "sản phẩm"
        )

    return await run_async_action(
        request, "product_image_upload", handler, f"{PRODUCTS_PATH}/{product_id}"
    )


@router.post("/admin/products/{product_id}/image/delete")
async def product_image_delete(request: Request, product_id: str):
    return await handle_action(
        request,
        "product_image_delete",
        actions.delete_product_image,
        f"{PRODUCTS_PATH}/{product_id}",
        "product_id",
    )


# --- Danh mục ---------------------------------------------------------------

@router.get(CATEGORIES_PATH)
async def categories_page(request: Request):
    rows = []
    for name, config in catalog.sorted_categories():
        rows.append(
            {
                "name": name,
                "config": config,
                "hidden": bool(config.get("hidden")),
                "sort_order": as_int(config.get("sort_order"), 9999),
                "product_count": len(catalog.products_in_category(name)),
                "has_image": catalog.category_image_path(name) is not None,
                "slug": domain.category_slug(name),
            }
        )
    return render(
        request,
        "categories.html",
        {
            "rows": rows,
            "fallback": domain.FALLBACK_CATEGORY,
            "flash": flash_from(request),
        },
    )


@router.post("/admin/categories/create")
async def category_create(request: Request):
    return await handle_action(
        request, "category_create", actions.create_category, CATEGORIES_PATH, "category_name"
    )


@router.post("/admin/categories/update")
async def category_update(request: Request):
    return await handle_action(
        request, "category_update", actions.update_category, CATEGORIES_PATH, "category_name"
    )


@router.post("/admin/categories/visibility")
async def category_visibility(request: Request):
    return await handle_action(
        request,
        "category_visibility",
        actions.set_category_visibility,
        CATEGORIES_PATH,
        "category_name",
    )


@router.post("/admin/categories/delete")
async def category_delete(request: Request):
    return await handle_action(
        request, "category_delete", actions.delete_category, CATEGORIES_PATH, "category_name"
    )


@router.post("/admin/categories/image")
async def category_image_upload(request: Request):
    async def handler(form):
        name = str(form.get("category_name") or "").strip()
        if not catalog.category_exists(name):
            return actions.fail("Không tìm thấy danh mục.")
        return await _store_upload(
            form.get("image"),
            get_settings().category_image_dir,
            domain.category_slug(name),
            "danh mục",
        )

    return await run_async_action(
        request, "category_image_upload", handler, CATEGORIES_PATH, "category_name"
    )


@router.post("/admin/categories/image/delete")
async def category_image_delete(request: Request):
    return await handle_action(
        request,
        "category_image_delete",
        actions.delete_category_image,
        CATEGORIES_PATH,
        "category_name",
    )


# --- Phục vụ ảnh ------------------------------------------------------------

@router.get("/admin/product-image/{product_id}", include_in_schema=False)
async def product_image(product_id: str):
    path = catalog.product_image_path(product_id)
    if path is None:
        return Response(status_code=404)
    return FileResponse(path, headers={"Cache-Control": "no-store"})


@router.get("/admin/category-image/{slug}", include_in_schema=False)
async def category_image(slug: str):
    directory = get_settings().category_image_dir
    for ext in sorted(get_settings().image_extensions):
        candidate = directory / f"{slug}.{ext}"
        if candidate.is_file():
            return FileResponse(candidate, headers={"Cache-Control": "no-store"})
    return Response(status_code=404)


async def _store_upload(upload, directory, stem: str, label: str) -> actions.Result:
    """Lưu ảnh tải lên sau khi kiểm tra đuôi file và dung lượng."""
    settings = get_settings()
    filename = str(getattr(upload, "filename", "") or "")
    if not filename:
        return actions.fail("Chưa chọn file ảnh.")
    extension = filename.rsplit(".", 1)[-1].lower()
    if extension not in settings.image_extensions:
        allowed = ", ".join(sorted(settings.image_extensions))
        return actions.fail(f"Chỉ nhận ảnh {allowed}.")

    payload = await upload.read()
    if len(payload) > settings.image_max_bytes:
        limit_mb = settings.image_max_bytes // (1024 * 1024)
        return actions.fail(f"Ảnh vượt quá {limit_mb}MB.")
    if not payload:
        return actions.fail("File ảnh rỗng.")

    catalog.clear_images(directory, stem)
    (directory / f"{stem}.{extension}").write_bytes(payload)
    return actions.ok(f"Đã cập nhật ảnh {label}.")
