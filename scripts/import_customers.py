"""Nhập khách hàng từ bản export MongoDB của bot cũ.

Nhập hai thứ:

  * id của mọi khách, để /broadcast gửi thông báo tới được. /broadcast duyệt
    toàn bộ user_data_db, nên chỉ cần có mặt trong đó là nhận được tin.
  * số dư ví, cho những dòng có số tiền đọc được và hợp lý.

Người đã chặn bot cũ được đánh dấu broadcast_disabled để khỏi phí lượt gửi.

Chỉ dùng thư viện chuẩn: bot chạy trong Docker nên host không có fastapi hay
openpyxl, và Debian mới chặn `pip install` ngoài venv.

Chạy khi bot ĐANG DỪNG. Bot giữ dữ liệu trong RAM và save_data() ghi đè kv_store
từ đó, nên mọi thay đổi script này ghi trong lúc bot chạy sẽ bị xóa.

    docker compose down
    python3 scripts/import_customers.py customers.xlsx           # thử, không ghi
    python3 scripts/import_customers.py customers.xlsx --apply   # ghi thật
    docker compose up -d

Cộng dồn: số dư cũ được CỘNG vào số dư hiện có. Để chạy hai lần không cộng đôi
tiền, mỗi lần ghi thật đều lưu một biên lai theo mã băm nội dung file. Chạy lại
cùng file sẽ bị từ chối.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from contextlib import closing, suppress
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Console Windows mặc định cp1252 và sẽ ném UnicodeEncodeError khi in tiếng Việt.
for _stream in (sys.stdout, sys.stderr):
    with suppress(AttributeError, ValueError):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import xlsx_reader  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RECEIPTS_KEY = "data_import_receipts.json"
USERS_KEY = "data_users.json"
TRANSACTIONS_KEY = "data_transaction_history.json"

#: Trên ngưỡng này coi là dữ liệu hỏng chứ không phải tiền thật.
SANE_BALANCE_CEILING = 1_000_000_000

REQUIRED_COLUMNS = ("chatId", "balance")
#: Thiếu cột nào ở đây thì coi như rỗng, không chặn cả lần nhập.
OPTIONAL_COLUMNS = ("username", "firstName", "lastName", "isBlocked")


def default_database() -> Path:
    """Ưu tiên data/database.sqlite (bản mount trong Docker), rồi mới goc project."""
    candidate = PROJECT_ROOT / "data" / "database.sqlite"
    return candidate if candidate.is_file() else PROJECT_ROOT / "database.sqlite"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path, help="File .xlsx export từ MongoDB")
    parser.add_argument(
        "--db", type=Path, default=None, help=f"Database SQLite (mặc định {default_database()})"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Ghi thật. Không có cờ này thì chỉ in ra."
    )
    parser.add_argument(
        "--include-absurd",
        action="store_true",
        help=f"Nhập cả số dư >= {SANE_BALANCE_CEILING:,} VND (mặc định bỏ qua).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bỏ qua biên lai và cộng dồn lần nữa. Chỉ dùng khi biết chắc.",
    )
    return parser.parse_args()


# --- kv_store ---------------------------------------------------------------

def kv_read(database: Path, key: str, default):
    with closing(sqlite3.connect(database)) as conn:
        row = conn.execute("SELECT value FROM kv_store WHERE key=?", (key,)).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return default


def kv_write_many(database: Path, pairs: dict) -> None:
    """Ghi nhiều khóa trong một transaction: không được để nửa vời khi có tiền."""
    with closing(sqlite3.connect(database, timeout=10)) as conn:
        conn.execute("PRAGMA busy_timeout=10000")
        with conn:
            for key, value in pairs.items():
                conn.execute(
                    "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)",
                    (key, json.dumps(value, ensure_ascii=False)),
                )


# --- Đọc và lọc -------------------------------------------------------------

def read_rows(path: Path) -> list[dict]:
    """Sheet đầu tiên thành list dict, chỉ gồm cột script dùng."""
    try:
        raw_rows = xlsx_reader.read_rows(path)
    except Exception as error:
        sys.exit(f"Không đọc được {path}: {error}")
    if not raw_rows:
        sys.exit(f"{path} không có dữ liệu.")

    header = [str(cell or "") for cell in raw_rows[0]]
    missing = [name for name in REQUIRED_COLUMNS if name not in header]
    if missing:
        sys.exit(f"{path} thiếu cột: {', '.join(missing)}")

    index = {
        name: header.index(name)
        for name in REQUIRED_COLUMNS + OPTIONAL_COLUMNS
        if name in header
    }

    def cell(row, position):
        return row[position] if position < len(row) else None

    return [
        {name: cell(row, position) for name, position in index.items()}
        for row in raw_rows[1:]
        if row and cell(row, index["chatId"]) is not None
    ]


def to_amount(value) -> int | None:
    """Số dư về int VND. Trả None nếu không đọc được thành số."""
    try:
        return int(round(float(value or 0)))
    except (TypeError, ValueError):
        return None


def as_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def workbook_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def plan(rows: list[dict], include_absurd: bool) -> tuple[list[dict], list[dict]]:
    """Chia thành (hồ sơ sẽ nhập, dòng bị bỏ kèm lý do).

    Mỗi hồ sơ có `amount` là số tiền sẽ cộng — bằng 0 nghĩa là chỉ nhập id để
    /broadcast gửi tới được, không đụng ví.
    """
    profiles: list[dict] = []
    skipped: list[dict] = []

    for row in rows:
        chat_id = str(row.get("chatId") or "").strip()
        label = str(row.get("username") or "").strip() or chat_id

        if not chat_id.isdigit():
            skipped.append({"id": chat_id, "label": label, "reason": "chatId không phải số"})
            continue

        amount = to_amount(row.get("balance"))
        note = ""
        if amount is None:
            amount, note = 0, "số dư không đọc được, chỉ nhập id"
        elif amount < 0:
            amount, note = 0, f"số dư âm ({amount:,}), chỉ nhập id"
        elif amount >= SANE_BALANCE_CEILING and not include_absurd:
            note = f"số dư bất thường ({amount:,}), chỉ nhập id"
            amount = 0
        if note:
            skipped.append({"id": chat_id, "label": label, "reason": note})

        profiles.append(
            {
                "id": chat_id,
                "amount": amount,
                "username": str(row.get("username") or "").strip(),
                "name": " ".join(
                    part for part in (row.get("firstName"), row.get("lastName")) if part
                ).strip(),
                # Người đã chặn bot cũ: đánh dấu để /broadcast khỏi phí lượt gửi,
                # giống hệt cách _cleanup_blocked_users đánh dấu người chặn bot mới.
                "blocked": bool(row.get("isBlocked")),
            }
        )
    return profiles, skipped


# --- Ghi --------------------------------------------------------------------

def apply_profiles(database: Path, profiles: list[dict], fingerprint: str) -> dict:
    """Tạo/cập nhật hồ sơ, cộng số dư và ghi lịch sử giao dịch khi có tiền."""
    users = kv_read(database, USERS_KEY, {})
    history = kv_read(database, TRANSACTIONS_KEY, {})
    now = int(time.time())
    counts = {"created": 0, "updated": 0, "credited": 0, "blocked": 0}

    for entry in profiles:
        user_id = entry["id"]
        profile = users.get(user_id)
        if not isinstance(profile, dict):
            profile = {"user_id": int(user_id), "balance": 0}
            counts["created"] += 1
        else:
            counts["updated"] += 1

        # Tên và username chỉ để nhận ra ai trong trang admin; không ghi đè bản mới.
        if entry["username"] and not profile.get("username"):
            profile["username"] = entry["username"]
        if entry["name"] and not profile.get("first_name"):
            profile["first_name"] = entry["name"]
        if entry["blocked"]:
            profile["broadcast_disabled"] = True
            counts["blocked"] += 1
        profile["imported_from"] = f"customers_xlsx:{fingerprint}"

        if entry["amount"] > 0:
            before = as_int(profile.get("balance"), 0)
            after = before + entry["amount"]
            profile["balance"] = after
            counts["credited"] += 1

            entries = history.get(user_id)
            if not isinstance(entries, list):
                entries = []
            entries.append(
                {
                    "timestamp": now,
                    "amount": entry["amount"],
                    "balance_before": before,
                    "balance_after": after,
                    "reason": f"Nhập số dư từ bot cũ (file {fingerprint})",
                    "source": "import_customers",
                }
            )
            history[user_id] = entries

        users[user_id] = profile

    receipts = kv_read(database, RECEIPTS_KEY, {})
    receipts[fingerprint] = {
        "applied_at": now,
        "customers": len(profiles),
        "total_credited": sum(entry["amount"] for entry in profiles),
        "created": counts["created"],
        "updated": counts["updated"],
        "credited": counts["credited"],
    }

    # Một transaction cho cả ba: đứt giữa chừng không được để tiền vào ví mà
    # thiếu biên lai, lần chạy sau sẽ cộng đôi.
    kv_write_many(
        database,
        {USERS_KEY: users, TRANSACTIONS_KEY: history, RECEIPTS_KEY: receipts},
    )
    return counts


def main() -> int:
    args = parse_args()
    if not args.workbook.is_file():
        sys.exit(f"Không tìm thấy {args.workbook}")

    database = args.db or default_database()
    if not database.is_file():
        sys.exit(
            f"Không tìm thấy database {database}.\n"
            "Chạy script ở thư mục gốc project, hoặc chỉ đường bằng --db."
        )

    fingerprint = workbook_fingerprint(args.workbook)
    receipt = kv_read(database, RECEIPTS_KEY, {}).get(fingerprint)
    if receipt and not args.force:
        stamp = time.strftime("%d/%m/%Y %H:%M", time.localtime(receipt["applied_at"]))
        print(f"File này đã được nhập lúc {stamp}:")
        print(f"  {receipt['customers']} khách, {receipt['total_credited']:,} VND")
        print("Cộng dồn lần nữa sẽ nhân đôi số tiền. Dùng --force nếu thực sự muốn.")
        return 1

    rows = read_rows(args.workbook)
    profiles, skipped = plan(rows, args.include_absurd)
    with_money = [entry for entry in profiles if entry["amount"] > 0]
    blocked = sum(1 for entry in profiles if entry["blocked"])
    total = sum(entry["amount"] for entry in profiles)

    print(f"Database: {database}")
    print(f"Đọc {len(rows)} dòng từ {args.workbook.name} (mã {fingerprint})")
    print(f"Nhập id cho {len(profiles)} khách để /broadcast gửi tới được")
    print(f"Cộng tiền cho {len(with_money)} khách, tổng {total:,} VND")
    if blocked:
        print(f"Đánh dấu {blocked} người đã chặn bot cũ, bỏ khỏi broadcast")

    if skipped:
        print(f"\n{len(skipped)} dòng không nhập số dư:")
        for item in skipped:
            print(f"  {item['label']:<24} {item['reason']}")

    if with_money:
        top = sorted(with_money, key=lambda e: e["amount"], reverse=True)[:10]
        print("\nSố dư lớn nhất:")
        for entry in top:
            print(f"  {entry['username'] or entry['id']:<24} {entry['amount']:>12,} VND")

    if not args.apply:
        print("\nMới chỉ thử. Thêm --apply để ghi thật.")
        return 0

    if not profiles:
        print("\nKhông có gì để ghi.")
        return 0

    counts = apply_profiles(database, profiles, fingerprint)
    print(
        f"\nĐã ghi: {counts['created']} khách mới, {counts['updated']} khách đã có. "
        f"Cộng tiền cho {counts['credited']} người, tổng {total:,} VND."
    )
    print("Khởi động lại bot: docker compose up -d")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
