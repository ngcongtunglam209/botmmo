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

HEADER = ["chatId", "balance", "username", "firstName", "lastName", "isBlocked"]

ROWS = [
    ("111", 50_000, "khach_a", "An", "Nguyen", False),
    ("222", 0, "khach_b", "Binh", "", False),
    ("333", 3542.4, "khach_c", "Cuong", "Le", False),
    ("444", 10**32, "admin_row", "Admin", "", False),
    ("555", -1000, "khach_am", "Am", "", False),
    ("666", 0, "khach_chan", "Chan", "", True),
    ("khong-phai-so", 9000, "khach_hong", "Hong", "", False),
]


def write_workbook(path, rows):
    openpyxl = pytest.importorskip("openpyxl")
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(HEADER)
    for row in rows:
        sheet.append(list(row))
    book.save(path)
    return path


@pytest.fixture()
def workbook(tmp_path):
    return write_workbook(tmp_path / "customers.xlsx", ROWS)


@pytest.fixture()
def database(tmp_path):
    """Database rỗng, đã có bảng kv_store."""
    path = tmp_path / "test.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE kv_store (key TEXT PRIMARY KEY, value TEXT)")
    return path


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


def _invoke(workbook, database, *extra):
    """Gọi script như chạy từ dòng lệnh, trả về exit code."""
    original = sys.argv
    sys.argv = ["import_customers.py", str(workbook), "--db", str(database), *extra]
    try:
        return importer.main()
    finally:
        sys.argv = original


# --- Chọn ai vào, ai được cộng tiền ------------------------------------------

def test_every_numeric_id_is_imported_for_broadcast(workbook):
    """Ai cũng phải có id trong user_data_db thì /broadcast mới gửi tới được."""
    rows = importer.read_rows(workbook)
    profiles, _ = importer.plan(rows, include_absurd=False)

    assert {entry["id"] for entry in profiles} == {"111", "222", "333", "444", "555", "666"}


def test_only_sane_positive_balances_are_credited(workbook):
    rows = importer.read_rows(workbook)
    profiles, skipped = importer.plan(rows, include_absurd=False)

    credited = {entry["id"] for entry in profiles if entry["amount"] > 0}
    assert credited == {"111", "333"}

    reasons = {item["label"]: item["reason"] for item in skipped}
    assert "số dư bất thường" in reasons["admin_row"]
    assert "số dư âm" in reasons["khach_am"]
    assert "chatId không phải số" in reasons["khach_hong"]


def test_non_numeric_id_is_dropped_entirely(workbook):
    rows = importer.read_rows(workbook)
    profiles, _ = importer.plan(rows, include_absurd=False)

    assert all(entry["id"] != "khong-phai-so" for entry in profiles)


def test_zero_balance_is_imported_without_a_warning(workbook):
    rows = importer.read_rows(workbook)
    profiles, skipped = importer.plan(rows, include_absurd=False)

    entry = next(entry for entry in profiles if entry["id"] == "222")
    assert entry["amount"] == 0
    assert all(item["label"] != "khach_b" for item in skipped)


def test_fractional_balance_is_rounded(workbook):
    rows = importer.read_rows(workbook)
    profiles, _ = importer.plan(rows, include_absurd=False)

    assert next(e["amount"] for e in profiles if e["id"] == "333") == 3542


def test_absurd_balance_can_be_forced_in(workbook):
    rows = importer.read_rows(workbook)
    profiles, _ = importer.plan(rows, include_absurd=True)

    # Excel lưu số này dưới dạng float nên giá trị đọc lại không khớp tuyệt đối.
    assert next(e["amount"] for e in profiles if e["id"] == "444") > 10**31


def test_optional_columns_may_be_absent(tmp_path):
    """Export khác có thể không có username/isBlocked — vẫn phải nhập được id."""
    openpyxl = pytest.importorskip("openpyxl")
    path = tmp_path / "toi_gian.xlsx"
    book = openpyxl.Workbook()
    book.active.append(["chatId", "balance"])
    book.active.append(["777", 1234])
    book.save(path)

    profiles, _ = importer.plan(importer.read_rows(path), include_absurd=False)

    assert profiles == [
        {"id": "777", "amount": 1234, "username": "", "name": "", "blocked": False}
    ]


# --- Ghi dữ liệu -------------------------------------------------------------

def test_dry_run_writes_nothing(workbook, database):
    _invoke(workbook, database)

    assert read_kv(database, importer.USERS_KEY) is None


def test_apply_creates_missing_users(workbook, database):
    _invoke(workbook, database, "--apply")

    users = read_kv(database, importer.USERS_KEY)
    assert users["111"]["balance"] == 50_000
    assert users["111"]["username"] == "khach_a"
    assert users["111"]["first_name"] == "An Nguyen"


def test_apply_imports_zero_balance_users_too(workbook, database):
    _invoke(workbook, database, "--apply")

    users = read_kv(database, importer.USERS_KEY)
    assert users["222"]["balance"] == 0
    assert users["222"]["username"] == "khach_b"


def test_users_who_blocked_the_old_bot_are_left_out_of_broadcasts(workbook, database):
    _invoke(workbook, database, "--apply")

    users = read_kv(database, importer.USERS_KEY)
    assert users["666"]["broadcast_disabled"] is True
    assert "broadcast_disabled" not in users["111"]


def test_absurd_balance_row_still_gets_an_id(workbook, database):
    """Bỏ số dư rác nhưng vẫn phải nhận được thông báo."""
    _invoke(workbook, database, "--apply")

    users = read_kv(database, importer.USERS_KEY)
    assert users["444"]["balance"] == 0
    assert "444" in users


def test_apply_adds_to_an_existing_balance(workbook, database):
    seed_users(database, {"111": {"user_id": 111, "balance": 20_000, "username": "cu"}})

    _invoke(workbook, database, "--apply")

    assert read_kv(database, importer.USERS_KEY)["111"]["balance"] == 70_000


def test_existing_username_is_not_overwritten(workbook, database):
    seed_users(database, {"111": {"user_id": 111, "balance": 0, "username": "ten_dang_dung"}})

    _invoke(workbook, database, "--apply")

    assert read_kv(database, importer.USERS_KEY)["111"]["username"] == "ten_dang_dung"


def test_apply_records_a_transaction_line(workbook, database):
    _invoke(workbook, database, "--apply")

    entry = read_kv(database, importer.TRANSACTIONS_KEY)["111"][-1]
    assert entry["amount"] == 50_000
    assert entry["balance_before"] == 0
    assert entry["balance_after"] == 50_000
    assert entry["source"] == "import_customers"


# --- Chống cộng đôi ----------------------------------------------------------

def test_second_run_refuses_and_changes_nothing(workbook, database):
    _invoke(workbook, database, "--apply")
    before = read_kv(database, importer.USERS_KEY)

    assert _invoke(workbook, database, "--apply") == 1
    assert read_kv(database, importer.USERS_KEY) == before


def test_force_overrides_the_receipt(workbook, database):
    _invoke(workbook, database, "--apply")

    _invoke(workbook, database, "--apply", "--force")

    assert read_kv(database, importer.USERS_KEY)["111"]["balance"] == 100_000


def test_a_different_file_is_not_blocked(workbook, database, tmp_path):
    _invoke(workbook, database, "--apply")

    other = write_workbook(
        tmp_path / "khac.xlsx", [("999", 7_000, "khach_moi", "Moi", "", False)]
    )
    _invoke(other, database, "--apply")

    assert read_kv(database, importer.USERS_KEY)["999"]["balance"] == 7_000


def test_receipt_totals_are_recorded(workbook, database):
    _invoke(workbook, database, "--apply")

    receipts = read_kv(database, importer.RECEIPTS_KEY)
    receipt = next(iter(receipts.values()))
    assert receipt["customers"] == 6  # moi id, ke ca nguoi khong co tien
    assert receipt["credited"] == 2
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
