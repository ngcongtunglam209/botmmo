import time

from app.core.runtime_loader import load_modules


def test_cost_snapshots_and_profit_summary():
    modules = load_modules()
    db = modules["app.services.games_withdrawals_db"]
    original_products = db.products
    original_history = db.order_history
    history = []
    products = {
        "local": {"name": "Local", "cost_price": 4000},
        "dat": {"name": "Dat", "cost_price": 7000},
    }
    db.products = products
    db.order_history = history
    try:
        local = {"order_code": "L1", "product_id": "local", "quantity": 2, "amount": 12000, "status": "Hoàn thành", "timestamp": time.time()}
        dat = {"order_code": "D1", "product_id": "dat", "quantity": 3, "amount": 30000, "status": "Hoàn thành", "timestamp": time.time()}
        missing = {"order_code": "M1", "product_id": "missing", "amount": 9000, "status": "Hoàn thành", "timestamp": time.time()}
        for order in (local, dat, missing):
            db.db_add_order(order, schedule_save=False)

        assert local["cost_total"] == 8000 and local["cost_source"] == "cost_price"
        assert dat["cost_total"] == 21000 and dat["cost_source"] == "cost_price"
        assert missing.get("cost_snapshot_missing") is True and "cost_total" not in missing

        products["local"]["cost_price"] = 9999
        replacement = dict(local, amount=13000)
        for snapshot_field in ("cost_total", "cost_unit", "cost_source", "cost_snapshot_at"):
            replacement.pop(snapshot_field)
        db.db_add_order(replacement, schedule_save=False)
        assert replacement["cost_total"] == 8000

        from app.web.repo import orders as orders_repo

        summary = orders_repo.summarize(history)
        assert summary["revenue"] == 52000
        assert summary["profit"] == 14000
        assert summary["costed"] == 2
        assert summary["completed"] == 3
    finally:
        db.products = original_products
        db.order_history = original_history

