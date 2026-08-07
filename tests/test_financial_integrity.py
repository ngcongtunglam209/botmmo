import asyncio
import sqlite3
import time

from app.core.runtime_loader import load_modules


def test_blocked_user_cleanup_retains_financial_data():
    modules = load_modules()
    notifications = modules["app.services.notifications_async"]
    original_users = notifications.user_data_db
    original_history = notifications.transaction_history
    original_referrals = notifications.referral_data
    original_save = notifications.save_data
    notifications.user_data_db = {"42": {"balance": 125_000}}
    notifications.transaction_history = {"42": [{"amount": 125_000}]}
    notifications.referral_data = {"42": {"total_commission": 5_000}}

    async def no_save(*args, **kwargs):
        return None

    notifications.save_data = no_save
    try:
        assert asyncio.run(notifications._cleanup_blocked_users(["42"])) == 1
        assert notifications.user_data_db["42"]["balance"] == 125_000
        assert notifications.user_data_db["42"]["broadcast_disabled"] is True
        assert notifications.transaction_history["42"] == [{"amount": 125_000}]
        assert notifications.referral_data["42"]["total_commission"] == 5_000
    finally:
        notifications.user_data_db = original_users
        notifications.transaction_history = original_history
        notifications.referral_data = original_referrals
        notifications.save_data = original_save


def test_transaction_claim_lease_and_completion(tmp_path):
    modules = load_modules()
    storage = modules["app.database.storage"]
    games = modules["app.services.games_withdrawals_db"]
    original_storage_path = storage.DB_PATH
    original_games_path = games.DB_PATH
    original_ids = storage.processed_transaction_ids
    db_path = str(tmp_path / "claims.sqlite")
    storage.DB_PATH = games.DB_PATH = db_path
    storage.processed_transaction_ids = games.processed_transaction_ids = set()
    try:
        storage.init_db()
        assert storage.db_claim_transaction("TX1") is True
        assert storage.db_claim_transaction("TX1") is False
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE processed_transactions SET updated_at=? WHERE tx_id='TX1'", (int(time.time()) - 601,))
            conn.commit()
        assert storage.db_claim_transaction("TX1") is True
        assert storage.db_release_transaction("TX1") is True
        assert storage.db_claim_transaction("TX1") is True
        assert storage.db_complete_transaction("TX1") is True
        assert storage.db_release_transaction("TX1") is False
        assert storage.db_claim_transaction("TX1") is False
    finally:
        storage.DB_PATH = original_storage_path
        games.DB_PATH = original_games_path
        storage.processed_transaction_ids = original_ids
        games.processed_transaction_ids = original_ids


def test_backup_restore_round_trip_includes_durable_tables(tmp_path):
    modules = load_modules()
    storage = modules["app.database.storage"]
    backup = modules["app.jobs.backup_and_rewards"]
    original_storage_path = storage.DB_PATH
    original_backup_path = backup.DB_PATH
    db_path = str(tmp_path / "backup.sqlite")
    storage.DB_PATH = backup.DB_PATH = db_path
    try:
        storage.init_db()
        with sqlite3.connect(db_path) as conn:
            conn.execute("INSERT INTO kv_store(key,value) VALUES (?,?)", (backup.CUSTOM_STORE_ICONS_FILE, '{"shop":"123"}'))
            conn.execute("INSERT INTO processed_transactions VALUES ('TX-BACKUP','completed',1,1)")
            conn.execute("INSERT INTO partner_order_refs VALUES ('scope','REF','completed','ORDER',1)")
            conn.commit()
        zip_path = backup.create_backup_zip("integrity_test")
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM kv_store")
            conn.execute("DELETE FROM processed_transactions")
            conn.execute("DELETE FROM partner_order_refs")
            conn.commit()
        report = backup.restore_backup_zip_to_db(zip_path)
        with sqlite3.connect(db_path) as conn:
            assert __import__("json").loads(conn.execute("SELECT value FROM kv_store WHERE key=?", (backup.CUSTOM_STORE_ICONS_FILE,)).fetchone()[0]) == {"shop": "123"}
            assert conn.execute("SELECT status FROM processed_transactions WHERE tx_id='TX-BACKUP'").fetchone()[0] == "completed"
            assert conn.execute("SELECT order_code FROM partner_order_refs WHERE partner_ref='REF'").fetchone()[0] == "ORDER"
        assert len(report["restored_tables"]) == 2
    finally:
        storage.DB_PATH = original_storage_path
        backup.DB_PATH = original_backup_path
