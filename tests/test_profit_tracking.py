import time

from app.core.runtime_loader import load_modules


def test_cost_snapshots_and_profit_summary():
    modules = load_modules()
    db = modules["app.services.games_withdrawals_db"]
    web = modules["app.api.admin_web"]
    original_products = db.products
    original_history = db.order_history
    original_rate = db.SOCIAL_SOURCE_RATE_VND_PER_USD
    history = []
    products = {
        "local": {"name": "Local", "cost_price": 4000},
        "dat": {"name": "Dat", "is_supplier_source_resell": True, "supplier_source_price": 7000},
    }
    db.products = products
    db.order_history = history
    db.SOCIAL_SOURCE_RATE_VND_PER_USD = 28000
    web.order_history = history
    try:
        local = {"order_code": "L1", "product_id": "local", "quantity": 2, "amount": 12000, "status": "Hoàn thành", "timestamp": time.time()}
        dat = {"order_code": "D1", "product_id": "dat", "quantity": 3, "amount": 30000, "status": "Hoàn thành", "timestamp": time.time()}
        social = {"order_code": "S1", "delivery_method": "social_service", "ctt_supplier_charge": "0.5", "amount": 20000, "status": "Hoan thanh", "timestamp": time.time()}
        missing = {"order_code": "M1", "product_id": "missing", "amount": 9000, "status": "Hoàn thành", "timestamp": time.time()}
        for order in (local, dat, social, missing):
            db.db_add_order(order, schedule_save=False)

        assert local["cost_total"] == 8000 and local["cost_source"] == "cost_price"
        assert dat["cost_total"] == 21000 and dat["cost_source"] == "supplier_source_price"
        assert social["cost_total"] == 14000 and social["cost_source"] == "ctt_supplier_charge"
        assert missing.get("cost_snapshot_missing") is True and "cost_total" not in missing

        products["local"]["cost_price"] = 9999
        replacement = dict(local, amount=13000)
        replacement.pop("cost_total"); replacement.pop("cost_unit"); replacement.pop("cost_source"); replacement.pop("cost_snapshot_at")
        db.db_add_order(replacement, schedule_save=False)
        assert replacement["cost_total"] == 8000

        summary = web._admin_web_financial_summary()
        assert summary["revenue"] == 72000
        assert summary["profit"] == 20000
        assert summary["costed"] == 3
        assert summary["completed"] == 4
    finally:
        db.products = original_products
        db.order_history = original_history
        db.SOCIAL_SOURCE_RATE_VND_PER_USD = original_rate
        web.order_history = original_history

