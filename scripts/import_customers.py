"""Nhập khách hàng từ bản export MongoDB của bot cũ.

Nhập hai thứ:

  * id của mọi khách, để /broadcast gửi thông báo tới được. /broadcast duyệt
    toàn bộ user_data_db, nên chỉ cần có mặt trong đó là nhận được tin.
  * số dư ví, cho những dòng có số tiền đọc được và hợp lý.

Người đã chặn bot cũ được đánh dấu broadcast_disabled để khỏi phí lượt gửi.

Chạy khi bot ĐANG DỪNG. Bot giữ dữ liệu trong RAM và save_data() ghi đè kv_store
từ đó, nên mọi thay đổi script này ghi trong lúc bot chạy sẽ bị xóa.

    docker compose down
    python scripts/import_customers.py customers.xlsx           # thử, không ghi
    python scripts/import_customers.py customers.xlsx --apply   # ghi thật
    docker compose up -d

Cộng dồn: số dư cũ được CỘNG vào số dư hiện có. Để chạy hai lần không cộng đôi
tiền, mỗi lần ghi thật đều lưu một biên lai theo mã băm nội dung file. Chạy lại
cùng file sẽ bị từ chối.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from contextlib import suppress
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Console Windows mặc định cp1252 và sẽ ném UnicodeEncodeError khi in tiếng Việt.
for _stream in (sys.stdout, sys.stderr):
    with suppress(AttributeError, ValueError):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from app.web.db import kv_read, kv_write  # noqa: E402
from app.web.repo.base import as_int  # noqa: E402

RECEIPTS_KEY = "data_import_receipts.json"
USERS_KEY = "data_users.json"
TRANSACTIONS_KEY = "data_transaction_history.json"

#: Trên ngưỡng này coi là dữ liệu hỏng chứ không phải tiền thật.
SANE_BALANCE_CEILING = 1_000_000_000

REQUIRED_COLUMNS = ("chatId", "balance")
#: Thiếu cột nào ở đây thì coi như rỗng, không chặn cả lần nhập.
OPTIONAL_COLUMNS = ("username", "firstName", "lastName", "isBlocked")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path, help="File .xlsx export từ MongoDB")
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


def read_rows(path: Path) -> list[dict]:
    """Đọc sheet đầu tiên, trả về list dict chỉ gồm cột cần dùng."""
    try:
        import openpyxl
    except ImportError:
        sys.exit("Thiếu openpyxl. Cài bằng: pip install openpyxl")

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    try:
        header = [str(cell or "") for cell in next(rows)]
    except StopIteration:
        sys.exit(f"{path} không có dữ liệu.")

    missing = [name for name in REQUIRED_COLUMNS if name not in header]
    if missing:
        sys.exit(f"{path} thiếu cột: {', '.join(missing)}")

    index = {
        name: header.index(name)
        for name in REQUIRED_COLUMNS + OPTIONAL_COLUMNS
        if name in header
    }
    chat_id_at = index["chatId"]
    return [
        {name: row[position] for name, position in index.items()}
        for row in rows
        if row and row[chat_id_at] is not None
    ]


def to_amount(value) -> int | None:
    """Số dư về int VND. Trả None nếu không đọc được thành số."""
    try:
        return int(round(float(value or 0)))
    except (TypeError, ValueError):
        return None


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
            note = f"số dư bất thường ({amount:,.0f}), chỉ nhập id"
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


def apply_profiles(profiles: list[dict], fingerprint: str) -> dict:
    """Tạo/cập nhật hồ sơ, cộng số dư và ghi lịch sử giao dịch khi có tiền."""
    users = kv_read(USERS_KEY, {})
    history = kv_read(TRANSACTIONS_KEY, {})
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

    kv_write(USERS_KEY, users)
    kv_write(TRANSACTIONS_KEY, history)
    return counts


def save_receipt(fingerprint: str, profiles: list[dict], counts: dict) -> None:
    receipts = kv_read(RECEIPTS_KEY, {})
    receipts[fingerprint] = {
        "applied_at": int(time.time()),
        "customers": len(profiles),
        "total_credited": sum(entry["amount"] for entry in profiles),
        "created": counts["created"],
        "updated": counts["updated"],
        "credited": counts["credited"],
    }
    kv_write(RECEIPTS_KEY, receipts)


def main() -> int:
    args = parse_args()
    if not args.workbook.is_file():
        sys.exit(f"Không tìm thấy {args.workbook}")

    fingerprint = workbook_fingerprint(args.workbook)
    receipt = kv_read(RECEIPTS_KEY, {}).get(fingerprint)
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

    counts = apply_profiles(profiles, fingerprint)
    save_receipt(fingerprint, profiles, counts)
    print(
        f"\nĐã ghi: {counts['created']} khách mới, {counts['updated']} khách đã có. "
        f"Cộng tiền cho {counts['credited']} người, tổng {total:,} VND."
    )
    print("Khởi động lại bot: docker compose up -d")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
