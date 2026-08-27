"""Hong du lieu am tham: giao hang bi bien dang, save tung bang, lich su AI chung."""

import asyncio

import pytest

from app.core.runtime_loader import load_modules


@pytest.fixture
def modules():
    return load_modules()


# --- Thong tin tai khoan giao cho khach phai nguyen van --------------------

@pytest.mark.parametrize(
    "raw",
    [
        "user1@mail.com|Ab<x>cd",       # <x> tung bi cat mat
        "user2@mail.com|P&sect;ssw0rd",  # tung bi doi thanh §
        "user3@mail.com|a&amp;b",        # tung bi doi thanh a&b
        "user4@mail.com|pass<>&word",
        "user5@mail.com|100%&not>ok",    # entity khong dau ; cung bi unescape
    ],
)
def test_delivered_credentials_are_not_html_decoded(modules, raw):
    delivery = modules["app.services.orders_delivery"]
    assert delivery.normalize_delivered_items([raw]) == [raw]


def test_delivery_line_still_strips_index_prefix_and_cr(modules):
    delivery = modules["app.services.orders_delivery"]
    assert delivery.normalize_delivered_items(["[ 12 ] user@mail.com|pw\r"]) == ["user@mail.com|pw"]


def test_delivery_drops_empty_lines(modules):
    delivery = modules["app.services.orders_delivery"]
    assert delivery.normalize_delivered_items(["", "   ", "acc"]) == ["acc"]


# --- save_data(tables=[...]) khong duoc huy lan luu day dang cho -----------

def test_partial_save_keeps_the_pending_full_save_armed(modules, monkeypatch):
    storage = modules["app.database.storage"]
    cache = storage._cache
    saved = dict(cache)

    async def fake_thread(fn, *args, **kwargs):
        return "{}"

    class _FakeDB:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def execute(self, *args, **kwargs):
            return None

        async def commit(self):
            return None

    monkeypatch.setattr(storage.asyncio, "to_thread", fake_thread, raising=False)
    monkeypatch.setattr(storage.aiosqlite, "connect", lambda *a, **k: _FakeDB(), raising=False)

    async def no_pragmas(db):
        return None

    monkeypatch.setattr(storage, "_apply_wal_pragmas", no_pragmas, raising=False)
    try:
        # Mot lan luu day bi debounce -> chi dat co, chua ghi.
        cache["last_save_time"] = 10_000_000.0
        cache["pending_save"] = True

        # Luu tung bang xen vao: KHONG duoc go co.
        asyncio.run(storage.save_data(tables=[storage.HISTORY_FILE]))
        assert cache["pending_save"] is True, "luu tung bang da huy mat lan luu day dang cho"

        # Luu day du thi moi duoc go co.
        asyncio.run(storage.save_data(force=True))
        assert cache["pending_save"] is False
    finally:
        cache.clear()
        cache.update(saved)


# --- Lich su chat AI khong duoc dung chung ---------------------------------

def test_ai_history_is_per_user_and_never_falls_into_bucket_zero(modules):
    ai = modules["app.integrations.ai_core"]
    assistant = ai.GroqAssistant()

    a = assistant.get_chat_history(111)
    a.append({"role": "user", "content": "don hang cua toi la ICLD123"})
    b = assistant.get_chat_history(222)
    assert b == [], "khach khac khong duoc thay hoi thoai cua nguoi truoc"

    # user_id khong hop le -> list dung mot lan, khong luu lai.
    for bad in (0, None, -5, "abc"):
        throwaway = assistant.get_chat_history(bad)
        assert throwaway == []
        throwaway.append({"role": "user", "content": "chi thi cai cam"})
        assert assistant.get_chat_history(bad) == [], "o nho chung van con ton tai"

    # 111 va 222 la id that -> co o nho rieng; 0/None/-5/'abc' thi khong.
    assert set(assistant.chat_sessions) == {111, 222}
