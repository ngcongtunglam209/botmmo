"""Script nhập số dư khách hàng cũ.

Script này cộng tiền thật vào ví khách. Hai thứ phải đúng tuyệt đối: cộng đúng
số, và chạy lại không được cộng lần nữa.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import import_customers as importer  # noqa: E402

ROWS = [
    # chatId, balance, username, firstName, lastName
    ("111", 50_000, "khach_a", "An", "Nguyen"),
    ("222", 0, "khach_b", "Binh", ""),
    ("333", 3542.4, "khach_c", "Cuong", "Le"),
    ("444", 10**32, "admin_row", "Admin", ""),
    ("555", -1000, "khach_am", "Am", ""),
    ("khong-phai-so", 9000, "khach_hong", "Hong", ""),
]


@pytest.fixture()
def workbook(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    path = tmp_path / "customers.xlsx"
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(["chatId", "balance", "username", "firstName", "lastName"])
    for row in ROWS:
        sheet.append(list(row))
    book.save(path)
    return path


@pytest.fixture()
def database(tmp_path, monkeypatch):
    """Database rỗng, đã có bảng kv_store."""
    from app.web import db, settings

    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.sqlite"))
    settings.get_settings.cache_clear()
    db.close_connection()
    db.ensure_schema()
    yield tmp_path / "test.sqlite"
    db.close_connection()
    settings.get_settings.cache_clear()


def read_kv(path, key):
    with sqlite3.connect(path) as conn:
        row = conn.execute("SELECT value FROM kv_store WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def seed_users(path, users):
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)",
            (importer.USERS_KEY, json.dumps(users)),
        )


def _invoke(workbook, *extra):
    """Gọi script như chạy từ dòng lệnh, trả về exit code."""
    argv = ["import_customers.py", str(workbook), *extra]
    original = sys.argv
    sys.argv = argv
    try:
        return importer.main()
    finally:
        sys.argv = original


# --- Chọn dòng nào để cộng ---------------------------------------------------

def test_plan_keeps_only_sane_positive_balances(workbook):
    rows = importer.read_rows(workbook)
    credits, skipped = importer.plan(rows, include_absurd=False)

    assert {credit["id"] for credit in credits} == {"111", "333"}
    reasons = {item["label"]: item["reason"] for item in skipped}
    assert "số dư bất thường" in reasons["admin_row"]
    assert "số dư âm" in reasons["khach_am"]
    assert "chatId không phải số" in reasons["khach_hong"]


def test_zero_balance_is_skipped_silently(workbook):
    rows = importer.read_rows(workbook)
    credits, skipped = importer.plan(rows, include_absurd=False)

    assert all(credit["id"] != "222" for credit in credits)
    assert all(item["label"] != "khach_b" for item in skipped)


def test_fractional_balance_is_rounded(workbook):
    rows = importer.read_rows(workbook)
    credits, _ = importer.plan(rows, include_absurd=False)

    assert next(c["amount"] for c in credits if c["id"] == "333") == 3542


def test_absurd_balance_can_be_forced_in(workbook):
    rows = importer.read_rows(workbook)
    credits, _ = importer.plan(rows, include_absurd=True)

    assert any(credit["id"] == "444" for credit in credits)


# --- Ghi dữ liệu -------------------------------------------------------------

def test_dry_run_writes_nothing(workbook, database):
    _invoke(workbook)

    assert read_kv(database, importer.USERS_KEY) is None


def test_apply_creates_missing_users(workbook, database):
    _invoke(workbook, "--apply")

    users = read_kv(database, importer.USERS_KEY)
    assert users["111"]["balance"] == 50_000
    assert users["111"]["username"] == "khach_a"
    assert users["111"]["first_name"] == "An Nguyen"


def test_apply_adds_to_an_existing_balance(workbook, database):
    seed_users(database, {"111": {"user_id": 111, "balance": 20_000, "username": "cu"}})

    _invoke(workbook, "--apply")

    assert read_kv(database, importer.USERS_KEY)["111"]["balance"] == 70_000


def test_existing_username_is_not_overwritten(workbook, database):
    seed_users(database, {"111": {"user_id": 111, "balance": 0, "username": "ten_dang_dung"}})

    _invoke(workbook, "--apply")

    assert read_kv(database, importer.USERS_KEY)["111"]["username"] == "ten_dang_dung"


def test_apply_records_a_transaction_line(workbook, database):
    _invoke(workbook, "--apply")

    entry = read_kv(database, importer.TRANSACTIONS_KEY)["111"][-1]
    assert entry["amount"] == 50_000
    assert entry["balance_before"] == 0
    assert entry["balance_after"] == 50_000
    assert entry["source"] == "import_customers"


# --- Chống cộng đôi ----------------------------------------------------------

def test_second_run_refuses_and_changes_nothing(workbook, database):
    _invoke(workbook, "--apply")
    before = read_kv(database, importer.USERS_KEY)

    assert _invoke(workbook, "--apply") == 1
    assert read_kv(database, importer.USERS_KEY) == before


def test_force_overrides_the_receipt(workbook, database):
    _invoke(workbook, "--apply")

    _invoke(workbook, "--apply", "--force")

    assert read_kv(database, importer.USERS_KEY)["111"]["balance"] == 100_000


def test_a_different_file_is_not_blocked(workbook, database, tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    _invoke(workbook, "--apply")

    other = tmp_path / "khac.xlsx"
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(["chatId", "balance", "username", "firstName", "lastName"])
    sheet.append(["999", 7_000, "khach_moi", "Moi", ""])
    book.save(other)

    _invoke(other, "--apply")

    assert read_kv(database, importer.USERS_KEY)["999"]["balance"] == 7_000


def test_receipt_totals_are_recorded(workbook, database):
    _invoke(workbook, "--apply")

    receipts = read_kv(database, importer.RECEIPTS_KEY)
    receipt = next(iter(receipts.values()))
    assert receipt["customers"] == 2
    assert receipt["total_credited"] == 53_542


# --- Đọc file ----------------------------------------------------------------

def test_missing_column_is_rejected(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    path = tmp_path / "thieu_cot.xlsx"
    book = openpyxl.Workbook()
    book.active.append(["chatId", "username"])
    book.save(path)

    with pytest.raises(SystemExit, match="thiếu cột"):
        importer.read_rows(path)
