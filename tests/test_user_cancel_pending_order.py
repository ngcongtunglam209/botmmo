"""Khách tự tra và hủy đơn chưa hoàn thành từ /lichsu."""

import pytest

from app.core.runtime_loader import load_modules


class _FakeUser:
    def __init__(self, user_id):
        self.id = user_id


class _FakeQuery:
    def __init__(self, user_id):
        self.from_user = _FakeUser(user_id)
        self.data = ""


class _FakeBot:
    def __init__(self):
        self.deleted = []

    async def delete_message(self, chat_id, message_id):
        self.deleted.append((chat_id, message_id))


class _FakeContext:
    def __init__(self):
        self.bot = _FakeBot()


@pytest.fixture()
def cancel_service(monkeypatch):
    """admin_orders với pending store, ví và I/O Telegram giả."""
    modules = load_modules()
    module = modules["app.services.admin_orders"]
    lookup = modules["app.services.games_withdrawals_db"]
    store = {}
    manual_store = {}
    balances = {}
    edits = []
    alerts = []

    async def fake_pop(code, default=None):
        return store.pop(code, default)

    async def fake_set(code, data):
        store[code] = data

    async def fake_edit(_query, **kwargs):
        edits.append(kwargs)

    async def fake_answer(_query, text=None, **_kwargs):
        alerts.append(text)

    async def fake_save(*_args, **_kwargs):
        return None

    def fake_db_get_user(user_id):
        return {"balance": balances.get(user_id, 0)}

    def fake_db_update_balance(user_id, new_balance, reason=None):
        balances[user_id] = new_balance

    # find_pending_order_by_code đọc globals của games_withdrawals_db, nên hai
    # kho pending phải là chính dict mà pending_pop/pending_set sửa.
    monkeypatch.setattr(lookup, "pending_orders", store, raising=False)
    monkeypatch.setattr(lookup, "pending_manual_orders", manual_store, raising=False)
    monkeypatch.setattr(module, "pending_pop", fake_pop, raising=False)
    monkeypatch.setattr(module, "pending_set", fake_set, raising=False)
    monkeypatch.setattr(module, "safe_edit_message", fake_edit, raising=False)
    monkeypatch.setattr(module, "safe_answer", fake_answer, raising=False)
    monkeypatch.setattr(module, "save_data", fake_save, raising=False)
    monkeypatch.setattr(module, "db_get_user", fake_db_get_user, raising=False)
    monkeypatch.setattr(module, "db_update_balance", fake_db_update_balance, raising=False)
    monkeypatch.setattr(module, "products", {}, raising=False)

    return module, store, manual_store, balances, edits, alerts


def _pending_order(user_id=4242, balance_used=0):
    return {
        "user_id": user_id,
        "type": "store_product",
        "product_id": "netflix",
        "product_name": "Netflix 1 tháng",
        "amount": 50_000,
        "balance_used": balance_used,
        "quantity": 1,
        "timestamp": 1_700_000_000,
        "status": "pending_payment",
        "message_id": 77,
    }


async def test_first_press_only_asks_for_confirmation(cancel_service):
    module, store, _manual, _balances, edits, _alerts = cancel_service
    store["ICLD111111"] = _pending_order()

    await module.handle_user_cancel_pending_order(
        _FakeQuery(4242), _FakeContext(), "user_cancel_order:ICLD111111:0"
    )

    assert "ICLD111111" in store, "Đơn không được xóa ở bước hỏi xác nhận"
    assert len(edits) == 1
    assert "ICLD111111" in edits[0]["text"]
    assert "user_cancel_confirm:ICLD111111:0" in str(edits[0]["reply_markup"])


async def test_confirmation_removes_the_order_and_deletes_the_qr(cancel_service):
    module, store, _manual, _balances, edits, _alerts = cancel_service
    store["ICLD111111"] = _pending_order()
    context = _FakeContext()

    await module.handle_user_cancel_pending_order(
        _FakeQuery(4242), context, "user_cancel_confirm:ICLD111111:0"
    )

    assert store == {}
    assert context.bot.deleted == [(4242, 77)]
    assert "ĐÃ HỦY ĐƠN" in edits[-1]["text"]


async def test_confirmation_refunds_the_balance_that_was_already_deducted(cancel_service):
    module, store, _manual, balances, edits, _alerts = cancel_service
    store["ICLD111111"] = _pending_order(balance_used=30_000)
    balances[4242] = 10_000

    await module.handle_user_cancel_pending_order(
        _FakeQuery(4242), _FakeContext(), "user_cancel_confirm:ICLD111111:0"
    )

    assert balances[4242] == 40_000
    assert "30,000" in edits[-1]["text"]


async def test_another_user_cannot_cancel_someone_elses_order(cancel_service):
    module, store, _manual, _balances, edits, alerts = cancel_service
    store["ICLD111111"] = _pending_order(user_id=4242)

    await module.handle_user_cancel_pending_order(
        _FakeQuery(9999), _FakeContext(), "user_cancel_confirm:ICLD111111:0"
    )

    assert "ICLD111111" in store, "Đơn của người khác phải giữ nguyên"
    assert edits == []
    assert alerts and "chờ thanh toán" in alerts[-1]


async def test_a_paid_manual_order_cannot_be_self_canceled(cancel_service):
    """Đơn manual đã trả tiền phải qua admin, không cho khách tự xóa."""
    module, _store, manual_store, _balances, edits, alerts = cancel_service
    manual_store["MANUALAB1234"] = {"user_id": 4242, "status": "awaiting_email"}

    await module.handle_user_cancel_pending_order(
        _FakeQuery(4242), _FakeContext(), "user_cancel_confirm:MANUALAB1234:0"
    )

    assert "MANUALAB1234" in manual_store
    assert edits == []
    assert alerts and "chờ thanh toán" in alerts[-1]


async def test_cancelling_an_order_that_already_left_pending_is_reported(cancel_service):
    module, _store, _manual, _balances, edits, alerts = cancel_service

    await module.handle_user_cancel_pending_order(
        _FakeQuery(4242), _FakeContext(), "user_cancel_confirm:ICLD111111:0"
    )

    assert edits == []
    assert alerts and "chờ thanh toán" in alerts[-1]


# --- Tra đơn còn treo -------------------------------------------------------

@pytest.fixture()
def pending_lookup(monkeypatch):
    module = load_modules()["app.services.games_withdrawals_db"]
    monkeypatch.setattr(
        module, "pending_orders", {"icld111111": _pending_order()}, raising=False
    )
    monkeypatch.setattr(
        module,
        "pending_manual_orders",
        {"MANUALAB1234": {"user_id": 4242, "product_name": "CapCut", "status": "awaiting_email"}},
        raising=False,
    )
    return module


def test_pending_order_is_found_by_code_regardless_of_key_casing(pending_lookup):
    """Tra không phân biệt hoa/thường, nhưng phải trả key thật để pop được."""
    kind, code, record = pending_lookup.find_pending_order_by_code("ICLD111111")

    assert (kind, code) == ("payment", "icld111111")
    assert record["product_name"] == "Netflix 1 tháng"


def test_manual_pending_order_is_found_and_tagged(pending_lookup):
    kind, code, _record = pending_lookup.find_pending_order_by_code("manualab1234")

    assert (kind, code) == ("manual", "MANUALAB1234")


def test_unknown_code_returns_nothing(pending_lookup):
    assert pending_lookup.find_pending_order_by_code("ICLD000000") == (None, None, None)


def test_user_pending_orders_cover_both_stores_with_a_code(pending_lookup):
    rows = pending_lookup.get_user_pending_orders(4242)

    assert {row["order_code"] for row in rows} == {"ICLD111111", "MANUALAB1234"}
    assert {row["pending_kind"] for row in rows} == {"payment", "manual"}


def test_user_pending_orders_ignore_other_buyers(pending_lookup):
    assert pending_lookup.get_user_pending_orders(9999) == []


def test_history_list_shows_pending_orders_and_prefers_them(monkeypatch):
    """Đơn manual đã trả tiền nằm ở cả hai chỗ — bản đang chờ xử lý phải thắng."""
    module = load_modules()["app.handlers.public_commands"]
    history_record = {"order_code": "MANUALAB1234", "status": "Hoàn thành", "timestamp": 1}
    pending_record = {
        "order_code": "MANUALAB1234",
        "status": "awaiting_email",
        "pending_kind": "manual",
        "timestamp": 2,
    }
    monkeypatch.setattr(module, "user_order_index", {"4242": [history_record]}, raising=False)
    monkeypatch.setattr(module, "_api_get_orders_for_user", lambda _uid: [], raising=False)
    monkeypatch.setattr(
        module, "get_user_pending_orders", lambda _uid: [pending_record], raising=False
    )

    rows = module._get_user_history_orders(4242)

    assert len(rows) == 1
    assert rows[0]["status"] == "awaiting_email"
