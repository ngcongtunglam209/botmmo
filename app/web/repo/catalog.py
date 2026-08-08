"""Đọc/ghi sản phẩm và danh mục."""

from __future__ import annotations

import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .. import domain
from ..settings import get_settings
from . import collections
from .base import as_int

# --- Sản phẩm ---------------------------------------------------------------

def all_products() -> dict[str, dict]:
    return {
        str(pid): data
        for pid, data in collections.products.read().items()
        if isinstance(data, dict)
    }


def get_product(product_id: str) -> dict | None:
    product = collections.products.get(str(product_id or "").strip())
    return product if isinstance(product, dict) else None


def product_exists(product_id: str) -> bool:
    return get_product(product_id) is not None


def count_products() -> int:
    return len(all_products())


def low_stock_products(threshold: int = 3) -> list[str]:
    """product_id của sản phẩm local còn <= threshold item."""
    result = []
    for pid, product in all_products().items():
        if domain.product_type(product) != "local":
            continue
        count = domain.stock_count(product)
        if isinstance(count, int) and count <= threshold:
            result.append(pid)
    return result


def products_in_category(name: str) -> list[str]:
    target = str(name or "").strip()
    return [
        pid
        for pid, product in all_products().items()
        if domain.product_category(product) == target
    ]


# --- Danh mục ---------------------------------------------------------------

def all_categories() -> dict[str, dict]:
    raw = collections.store_categories.read()
    return {str(k): (v if isinstance(v, dict) else {}) for k, v in raw.items()}


def category_config(name: str) -> dict:
    return all_categories().get(str(name or "").strip(), {})


def category_names() -> list[str]:
    """Mọi danh mục: đã khai báo trong store_categories + suy ra từ sản phẩm."""
    names = set(all_categories())
    for product in all_products().values():
        category = domain.product_category(product)
        if category:
            names.add(category)
    return sorted(names)


def category_exists(name: str) -> bool:
    target = str(name or "").strip()
    if not target:
        return False
    if target in all_categories():
        return True
    return any(
        domain.product_category(product) == target
        for product in all_products().values()
    )


def sorted_categories() -> list[tuple[str, dict]]:
    """Danh mục theo sort_order rồi tên, kèm config đã chuẩn hóa."""
    configs = all_categories()
    rows = []
    for name in category_names():
        config = dict(configs.get(name, {}))
        config.setdefault("sort_order", 9999)
        config.setdefault("hidden", False)
        rows.append((name, config))
    rows.sort(key=lambda row: (as_int(row[1].get("sort_order"), 9999), row[0].lower()))
    return rows


# --- Ảnh --------------------------------------------------------------------

def _find_image(directory: Path, stem: str) -> Path | None:
    if not stem:
        return None
    for ext in sorted(get_settings().image_extensions):
        candidate = directory / f"{stem}.{ext}"
        if candidate.is_file():
            return candidate
    return None


def product_image_path(product_id: str) -> Path | None:
    return _find_image(get_settings().product_image_dir, str(product_id or "").strip())


def category_image_path(name: str) -> Path | None:
    return _find_image(get_settings().category_image_dir, domain.category_slug(name))


def clear_images(directory: Path, stem: str) -> int:
    """Xóa mọi phần mở rộng của một ảnh; trả số file đã xóa."""
    removed = 0
    for ext in get_settings().image_extensions:
        candidate = directory / f"{stem}.{ext}"
        if candidate.is_file():
            candidate.unlink()
            removed += 1
    return removed


def categories_with_image(names: Iterable[str]) -> int:
    return sum(1 for name in names if name and category_image_path(name) is not None)


def touch_config(config: dict[str, Any]) -> dict[str, Any]:
    config["updated_at"] = int(time.time())
    return config
