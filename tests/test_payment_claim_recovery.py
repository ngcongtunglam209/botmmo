"""Giao dich da claim nhung chua hoan tat phai quet lai duoc.

Truoc day db_transaction_exists() dem ca dong status='processing', nen mot lan
xu ly bi bo do (bot chet, Telegram nem Forbidden giua chung) lam giao dich do bi
bo qua vinh vien: vong quet sau thay "da co dong" nen continue truoc khi kip goi
db_claim_transaction(), tuc la co che gia han 600s khong bao gio chay toi.
"""

import sqlite3
import time

from app.core.runtime_loader import load_modules


def _isolated_db(tmp_path, name):
    """Tra (modules, storage, games, restore) da tro DB_PATH vao file tam."""
    modules = load_modules()
    storage = modules["app.database.storage"]
    games = modules["app.services.games_withdrawals_db"]
    saved = (storage.DB_PATH, games.DB_PATH, storage.processed_transaction_ids)
    storage.DB_PATH = games.DB_PATH = str(tmp_path / name)
    storage.processed_transaction_ids = games.processed_transaction_ids = set()
    storage.init_db()

    def restore():
        storage.DB_PATH, games.DB_PATH, ids = saved
        storage.processed_transaction_ids = ids
        games.processed_transaction_ids = ids

    return storage, games, restore


def test_in_flight_claim_is_not_reported_as_processed(tmp_path):
    storage, games, restore = _isolated_db(tmp_path, "claim_status.sqlite")
    try:
        assert storage.db_claim_transaction("TXA") is True
        # Dong 'processing' KHONG duoc tinh la da xu ly xong.
        assert storage.db_transaction_exists("TXA") is False
        assert games.db_check_tx_exists("TXA") is False
        # Chi khi hoan tat moi tinh.
        storage.db_complete_transaction("TXA")
        assert storage.db_transaction_exists("TXA") is True
        assert games.db_check_tx_exists("TXA") is True
    finally:
        restore()


def test_abandoned_claim_is_retried_after_lease_expires(tmp_path):
    """Vong doi day du cua mot lan xu ly bi bo do."""
    storage, games, restore = _isolated_db(tmp_path, "claim_lease.sqlite")
    try:
        # Vong quet 1: nhan giao dich, claim, roi chet giua chung.
        assert games.db_check_tx_exists("TXB") is False
        assert storage.db_claim_transaction("TXB") is True

        # Vong quet 2 (15s sau): khong bi coi la da xong, nhung claim phai that
        # bai vi lease con hieu luc - khong duoc xu ly hai lan.
        assert games.db_check_tx_exists("TXB") is False
        assert storage.db_claim_transaction("TXB") is False

        # Sau 600s lease het han -> duoc claim lai va cong tien.
        with sqlite3.connect(storage.DB_PATH) as conn:
            conn.execute(
                "UPDATE processed_transactions SET updated_at=? WHERE tx_id='TXB'",
                (int(time.time()) - 601,),
            )
            conn.commit()
        assert games.db_check_tx_exists("TXB") is False
        assert storage.db_claim_transaction("TXB") is True

        storage.db_complete_transaction("TXB")
        assert games.db_check_tx_exists("TXB") is True
        assert storage.db_claim_transaction("TXB") is False
    finally:
        restore()


def test_released_claim_is_retried_immediately(tmp_path):
    """check_payment_job tra claim ve khi than vong lap nem exception."""
    storage, games, restore = _isolated_db(tmp_path, "claim_release.sqlite")
    try:
        assert storage.db_claim_transaction("TXC") is True
        assert storage.db_release_transaction("TXC") is True
        # Khong phai doi het 600s.
        assert games.db_check_tx_exists("TXC") is False
        assert storage.db_claim_transaction("TXC") is True

        # Da hoan tat thi release khong duoc dung toi.
        storage.db_complete_transaction("TXC")
        assert storage.db_release_transaction("TXC") is False
        assert games.db_check_tx_exists("TXC") is True
    finally:
        restore()
