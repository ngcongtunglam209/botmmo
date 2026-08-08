"""Nền tảng repository: mỗi blob kv_store là một collection có transaction."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

from .. import bridge
from ..db import kv_read, kv_write, transaction

T = TypeVar("T")


class KvCollection:
    """Bọc một key trong kv_store.

    `read()` luôn lấy bản mới nhất từ SQLite. `mutate()` đọc, cho callback sửa,
    ghi lại trong một transaction rồi đẩy sang runtime bot qua bridge.
    """

    def __init__(self, key: str, factory: Callable[[], Any]):
        self.key = key
        self.factory = factory

    def read(self) -> Any:
        value = kv_read(self.key, None)
        if value is None:
            return self.factory()
        return value

    def write(self, value: Any) -> None:
        with transaction() as conn:
            kv_write(self.key, value, conn=conn)
        bridge.publish(self.key, value)

    @contextmanager
    def mutate(self) -> Iterator[Any]:
        """Sửa collection rồi tự động lưu khi thoát khối `with`."""
        value = self.read()
        yield value
        self.write(value)


class DictCollection(KvCollection):
    def __init__(self, key: str):
        super().__init__(key, dict)

    def read(self) -> dict:
        value = super().read()
        return value if isinstance(value, dict) else {}

    def get(self, item_id: str) -> Any:
        return lookup(self.read(), item_id)


class ListCollection(KvCollection):
    def __init__(self, key: str):
        super().__init__(key, list)

    def read(self) -> list:
        value = super().read()
        return value if isinstance(value, list) else []


def lookup(mapping: dict, key: Any) -> Any:
    """Tra cứu chấp nhận cả key số lẫn key chuỗi (dữ liệu cũ trộn cả hai)."""
    if not isinstance(mapping, dict):
        return None
    if key in mapping:
        return mapping[key]
    text_key = str(key)
    if text_key in mapping:
        return mapping[text_key]
    if text_key.isdigit():
        int_key = int(text_key)
        if int_key in mapping:
            return mapping[int_key]
    return None


def resolve_key(mapping: dict, key: Any) -> Any:
    """Trả về key thật sự nằm trong mapping, hoặc `key` nếu không tìm thấy."""
    if not isinstance(mapping, dict):
        return key
    if key in mapping:
        return key
    text_key = str(key)
    if text_key in mapping:
        return text_key
    if text_key.isdigit() and int(text_key) in mapping:
        return int(text_key)
    return key


def as_int(value: Any, default: int = 0) -> int:
    """Ép về int, chấp nhận '1.000.000' và '1,000,000' như web cũ."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        text = str(value or "").replace(",", "").replace(".", "").strip()
        return int(text) if text else default
    except (TypeError, ValueError):
        return default
