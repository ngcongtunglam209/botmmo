import pytest

from app.core.runtime_loader import load_modules


class _FakeMessage:
    def __init__(self, text=None):
        self.text = text
        self.document = None
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class _FakeUpdate:
    def __init__(self, message):
        self.message = message


class _FakeContext:
    def __init__(self):
        self.user_data = {}
        self.bot = None


@pytest.fixture
def catalog(monkeypatch):
    module = load_modules()["app.handlers.product_catalog"]

    async def fake_save(*args, **kwargs):
        return None

    monkeypatch.setattr(module, "save_data", fake_save, raising=False)
    return module


async def _add_stock(module, products, prod_id, text):
    calls = []
    scheduled = []

    async def fake_notify(context, product_name, added_count, total_count, price=0):
        calls.append((product_name, added_count, total_count, price))

    async def fake_back_in_stock(*args, **kwargs):
        return None

    module.__dict__["notify_stock_added"] = fake_notify
    module.__dict__["broadcast_back_in_stock"] = fake_back_in_stock
    module.__dict__["create_background_task"] = scheduled.append
    module.__dict__["products"] = products

    context = _FakeContext()
    context.user_data["stock_prod_id"] = prod_id
    message = _FakeMessage(text)
    await module.receive_stock_input(_FakeUpdate(message), context)
    for coro in scheduled:
        await coro
    return calls, message


async def test_addstock_posts_added_and_total_counts(catalog):
    products = {"p1": {"name": "Netflix", "price": 59000, "stock": ["old"]}}

    calls, _ = await _add_stock(catalog, products, "p1", "a\nb\nc")

    assert calls == [("Netflix", 3, 4, 59000)]
    assert products["p1"]["stock"] == ["old", "a", "b", "c"]


async def test_addstock_posts_even_when_product_was_already_in_stock(catalog):
    """Khác broadcast_back_in_stock: bài lên kênh chạy cho mọi lần nhập kho."""
    products = {"p1": {"name": "Netflix", "price": 1000, "stock": ["x", "y"]}}

    calls, _ = await _add_stock(catalog, products, "p1", "z")

    assert calls == [("Netflix", 1, 3, 1000)]


async def test_empty_input_posts_nothing(catalog):
    products = {"p1": {"name": "Netflix", "price": 1000, "stock": []}}

    calls, message = await _add_stock(catalog, products, "p1", "   \n  ")

    assert calls == []
    assert products["p1"]["stock"] == []
    assert message.replies
