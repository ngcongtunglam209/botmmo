"""Nhập số dư ví khách hàng từ bản export MongoDB của bot cũ.

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

COLUMNS = ("chatId", "balance", "username", "firstName", "lastName")


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

    missing = [name for name in COLUMNS if name not in header]
    if missing:
        sys.exit(f"{path} thiếu cột: {', '.join(missing)}")

    index = {name: header.index(name) for name in COLUMNS}
    return [
        {name: row[position] for name, position in index.items()}
        for row in rows
        if row and row[index["chatId"]] is not None
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
    """Chia thành (sẽ cộng tiền, bị bỏ qua kèm lý do)."""
    credits: list[dict] = []
    skipped: list[dict] = []

    for row in rows:
        chat_id = str(row["chatId"] or "").strip()
        amount = to_amount(row["balance"])
        label = str(row["username"] or "").strip() or chat_id

        if not chat_id.isdigit():
            skipped.append({"id": chat_id, "label": label, "reason": "chatId không phải số"})
            continue
        if amount is None:
            skipped.append({"id": chat_id, "label": label, "reason": "số dư không đọc được"})
            continue
        if amount == 0:
            continue  # không có gì để cộng, im lặng bỏ qua
        if amount < 0:
            skipped.append({"id": chat_id, "label": label, "reason": f"số dư âm ({amount:,})"})
            continue
        if amount >= SANE_BALANCE_CEILING and not include_absurd:
            skipped.append(
                {"id": chat_id, "label": label, "reason": f"số dư bất thường ({amount:,.0f})"}
            )
            continue

        credits.append(
            {
                "id": chat_id,
                "amount": amount,
                "username": str(row["username"] or "").strip(),
                "name": " ".join(
                    part for part in (row["firstName"], row["lastName"]) if part
                ).strip(),
            }
        )
    return credits, skipped


def apply_credits(credits: list[dict], fingerprint: str) -> dict:
    """Cộng số dư và ghi một dòng lịch sử giao dịch cho mỗi khách."""
    users = kv_read(USERS_KEY, {})
    history = kv_read(TRANSACTIONS_KEY, {})
    now = int(time.time())
    created = 0
    updated = 0

    for credit in credits:
        user_id = credit["id"]
        profile = users.get(user_id)
        if not isinstance(profile, dict):
            profile = {"user_id": int(user_id), "balance": 0}
            created += 1
        else:
            updated += 1

        before = as_int(profile.get("balance"), 0)
        after = before + credit["amount"]
        profile["balance"] = after
        # Tên và username chỉ để nhận ra ai đang giữ số tiền này trong trang admin.
        if credit["username"] and not profile.get("username"):
            profile["username"] = credit["username"]
        if credit["name"] and not profile.get("first_name"):
            profile["first_name"] = credit["name"]
        profile["imported_from"] = f"customers_xlsx:{fingerprint}"
        users[user_id] = profile

        entries = history.get(user_id)
        if not isinstance(entries, list):
            entries = []
        entries.append(
            {
                "timestamp": now,
                "amount": credit["amount"],
                "balance_before": before,
                "balance_after": after,
                "reason": f"Nhập số dư từ bot cũ (file {fingerprint})",
                "source": "import_customers",
            }
        )
        history[user_id] = entries

    kv_write(USERS_KEY, users)
    kv_write(TRANSACTIONS_KEY, history)
    return {"created": created, "updated": updated}


def save_receipt(fingerprint: str, credits: list[dict], counts: dict) -> None:
    receipts = kv_read(RECEIPTS_KEY, {})
    receipts[fingerprint] = {
        "applied_at": int(time.time()),
        "customers": len(credits),
        "total_credited": sum(credit["amount"] for credit in credits),
        "created": counts["created"],
        "updated": counts["updated"],
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
    credits, skipped = plan(rows, args.include_absurd)
    total = sum(credit["amount"] for credit in credits)

    print(f"Đọc {len(rows)} dòng từ {args.workbook.name} (mã {fingerprint})")
    print(f"Sẽ cộng tiền cho {len(credits)} khách, tổng {total:,} VND")

    if skipped:
        print(f"\nBỏ qua {len(skipped)} dòng:")
        for item in skipped:
            print(f"  {item['label']:<24} {item['reason']}")

    if credits:
        top = sorted(credits, key=lambda c: c["amount"], reverse=True)[:10]
        print("\nSố dư lớn nhất:")
        for credit in top:
            label = credit["username"] or credit["id"]
            print(f"  {label:<24} {credit['amount']:>12,} VND")

    if not args.apply:
        print("\nMới chỉ thử. Thêm --apply để ghi thật.")
        return 0

    if not credits:
        print("\nKhông có gì để ghi.")
        return 0

    counts = apply_credits(credits, fingerprint)
    save_receipt(fingerprint, credits, counts)
    print(
        f"\nĐã ghi: {counts['created']} khách mới, {counts['updated']} khách đã có, "
        f"tổng {total:,} VND."
    )
    print("Khởi động lại bot: docker compose up -d")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
