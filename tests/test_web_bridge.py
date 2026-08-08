"""Bridge giữa web mới và runtime bot đang chạy.

Đây là chỗ dễ hỏng nhất: nếu bridge gán lại object thay vì sửa tại chỗ, các
module cũ giữ alias sẽ nhìn thấy dữ liệu lỗi thời và `save_data()` của bot sẽ
ghi đè thay đổi của web.
"""

from __future__ import annotations

import sys
import types

import pytest

from app.web import bridge


@pytest.fixture()
def fake_state(monkeypatch):
    """Giả lập app.state.app_state mà không cần khởi động bot."""
    state = types.SimpleNamespace(
        products={"p1": {"name": "cũ"}},
        order_history=[{"order_code": "A1"}],
        banned_users={1},
        maintenance_mode=False,
        ai_auto_reply=True,
        bot_instance=None,
    )
    module = types.ModuleType("app.state")
    module.app_state = state
    monkeypatch.setitem(sys.modules, "app.state", module)
    return state


def test_publish_is_noop_without_bot(monkeypatch):
    monkeypatch.delitem(sys.modules, "app.state", raising=False)
    assert bridge.publish("data_products.json", {"p1": {}}) is False


def test_publish_updates_dict_in_place(fake_state):
    alias = fake_state.products

    assert bridge.publish("data_products.json", {"p2": {"name": "mới"}}) is True

    # Cùng object: module cũ giữ alias vẫn thấy dữ liệu mới.
    assert alias is fake_state.products
    assert alias == {"p2": {"name": "mới"}}


def test_publish_updates_list_in_place(fake_state):
    alias = fake_state.order_history

    assert bridge.publish("data_order_history.json", [{"order_code": "B2"}]) is True

    assert alias is fake_state.order_history
    assert alias == [{"order_code": "B2"}]


def test_publish_updates_set_in_place(fake_state):
    alias = fake_state.banned_users

    assert bridge.publish("data_banned_users.json", [7, 8]) is True

    assert alias is fake_state.banned_users
    assert alias == {7, 8}


def test_publish_ignores_unknown_key(fake_state):
    assert bridge.publish("data_khong_ton_tai.json", {}) is False


def test_order_publish_rebuilds_indexes(fake_state, monkeypatch):
    """order_index giữ tham chiếu tới dict đơn — phải dựng lại sau khi thay list."""
    calls = []
    module = types.ModuleType("app.services.games_withdrawals_db")
    module._rebuild_order_indexes = lambda: calls.append(True)
    monkeypatch.setitem(sys.modules, "app.services.games_withdrawals_db", module)

    bridge.publish("data_order_history.json", [{"order_code": "C3"}])

    assert calls == [True]


def test_non_order_publish_does_not_rebuild_indexes(fake_state, monkeypatch):
    calls = []
    module = types.ModuleType("app.services.games_withdrawals_db")
    module._rebuild_order_indexes = lambda: calls.append(True)
    monkeypatch.setitem(sys.modules, "app.services.games_withdrawals_db", module)

    bridge.publish("data_products.json", {"p9": {}})

    assert calls == []


def test_flags_read_and_write(fake_state):
    assert bridge.read_flag("maintenance_mode", True) is False

    bridge.set_flag("maintenance_mode", True)

    assert fake_state.maintenance_mode is True
    assert bridge.read_flag("maintenance_mode", False) is True


def test_read_flag_falls_back_without_bot(monkeypatch):
    monkeypatch.delitem(sys.modules, "app.state", raising=False)
    assert bridge.read_flag("maintenance_mode", True) is True


@pytest.mark.asyncio
async def test_notify_admin_is_noop_without_bot(monkeypatch):
    monkeypatch.delitem(sys.modules, "app.state", raising=False)
    assert await bridge.notify_admin("xin chào") is False


def test_every_mapped_field_exists_on_app_state():
    """Sai tên field sẽ khiến bridge im lặng bỏ qua — bắt lỗi đó ngay ở test."""
    from app.state import AppState

    known = set(AppState.PERSISTED_FIELDS) | set(AppState.RUNTIME_FIELDS)
    unknown = {field for field in bridge.KV_TO_STATE.values() if field not in known}

    assert unknown == set()
