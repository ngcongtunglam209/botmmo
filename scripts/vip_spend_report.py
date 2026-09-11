"""Thống kê phân bố chi tiêu của khách để chốt ngưỡng và % giảm giá cho hạng VIP.

Trả lời đúng một câu hỏi: nếu bật giảm giá theo hạng thì mỗi tháng mất bao nhiêu
tiền, và đặt ngưỡng bậc cuối ở 10 triệu hay 20 triệu thì hợp lý hơn.

CHỈ ĐỌC. Không ghi gì vào kv_store nên chạy được trong lúc bot đang chạy.

Chỉ dùng thư viện chuẩn: bot chạy trong Docker nên host không có fastapi, và
Debian mới chặn `pip install` ngoài venv. Vì vậy logic "đơn đã hoàn thành" và
"chủ đơn thật sự" được chép lại ở đây thay vì import từ app/ — xem
`app/services/games_withdrawals_db.py::is_completed_order` và
`app/api/helpers.py::_api_get_effective_order_user_id` để đối chiếu.

    python3 scripts/vip_spend_report.py                        # dùng data/database.sqlite
    python3 scripts/vip_spend_report.py --db /duong/dan.sqlite
    python3 scripts/vip_spend_report.py --ladder 0:0,500000:2,2000000:5,7000000:8,20000000:10

Hạng xếp theo chi tiêu trong cửa sổ trượt 90 ngày, đúng như get_user_vip_rank().

Chi phí ước tính là CẬN TRÊN: đơn nào đang dính flash sale thì khách ăn giá flash
chứ không cộng dồn VIP, nên số thật sẽ thấp hơn một chút.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sqlite3
import sys
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
KV_ORDERS = "data_order_history.json"

# Giữ khớp với VIP_RANK_WINDOW_DAYS trong app/core/config_env.py. Hạng tính
# theo chi tiêu trong cửa sổ trượt này, không phải lifetime cộng dồn.
RANK_WINDOW_DAYS = 90

# (ngưỡng chi tiêu lifetime, phần trăm giảm). Phải xếp tăng dần theo ngưỡng.
LADDERS: dict[str, list[tuple[int, int]]] = {
    "hien-tai": [(0, 0), (500_000, 2), (2_000_000, 5), (7_000_000, 8), (20_000_000, 10)],
    "cu-10tr": [(0, 0), (500_000, 2), (1_000_000, 5), (5_000_000, 8), (10_000_000, 10)],
}
RANK_LABELS = ["Đồng", "Bạc", "Vàng", "Kim Cương", "Cao Thủ"]


def strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn")


def is_completed(order: dict) -> bool:
    """Đơn có tính vào doanh thu không. Chép từ games_withdrawals_db.is_completed_order."""
    if not isinstance(order, dict):
        return False
    raw = order.get("status")
    status = strip_accents(str(raw or "")).strip().lower()
    if not status:
        return False
    if "hoan thanh" in status or status == "completed":
        return True
    is_api = bool(order.get("api_partner_key_hash") or order.get("api_owner_user_id"))
    return is_api and "api sold" in status


def effective_user_id(order: dict) -> int:
    """Chủ đơn thật sự: đơn qua partner API tính cho chủ API key, không tính cho khách lẻ."""
    for key in ("api_owner_user_id", "user_id"):
        try:
            uid = int(order.get(key, 0) or 0)
        except (ValueError, TypeError):
            uid = 0
        if uid > 0:
            return uid
    return 0


def load_orders(db_path: str) -> list[dict]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM kv_store WHERE key=?", (KV_ORDERS,)).fetchone()
    finally:
        conn.close()
    if not row:
        return []
    data = json.loads(row[0])
    return [o for o in data if isinstance(o, dict)] if isinstance(data, list) else []


def cutoffs(now: datetime) -> tuple[float, float]:
    """Trả (mốc đầu cửa sổ xét hạng, mốc 30 ngày trước) dạng timestamp."""
    return (now - timedelta(days=RANK_WINDOW_DAYS)).timestamp(), (now - timedelta(days=30)).timestamp()


def collect(orders: list[dict], now: datetime) -> dict[int, dict]:
    window_start, last30 = cutoffs(now)
    users: dict[int, dict] = {}
    for order in orders:
        if not is_completed(order):
            continue
        uid = effective_user_id(order)
        if not uid:
            continue
        try:
            amount = max(0, int(order.get("amount", 0) or 0))
            ts = float(order.get("timestamp", 0) or 0)
        except (ValueError, TypeError):
            continue
        u = users.setdefault(uid, {"lifetime": 0, "window": 0, "last30": 0, "orders": 0})
        u["lifetime"] += amount
        u["orders"] += 1
        if ts >= window_start:
            u["window"] += amount
        if ts >= last30:
            u["last30"] += amount
    return users


def rank_index(lifetime: int, ladder: list[tuple[int, int]]) -> int:
    idx = 0
    for i, (threshold, _pct) in enumerate(ladder):
        if lifetime >= threshold:
            idx = i
    return idx


def simulate(users: dict[int, dict], ladder: list[tuple[int, int]]) -> list[dict]:
    rows = [
        {
            "rank": RANK_LABELS[i] if i < len(RANK_LABELS) else f"Bậc {i}",
            "threshold": ladder[i][0],
            "percent": ladder[i][1],
            "users": 0,
            "revenue30": 0,
            "cost30": 0,
        }
        for i in range(len(ladder))
    ]
    for u in users.values():
        # Hạng theo chi tiêu trong cửa sổ trượt, giống get_user_vip_rank().
        idx = rank_index(u["window"], ladder)
        row = rows[idx]
        row["users"] += 1
        row["revenue30"] += u["last30"]
        row["cost30"] += u["last30"] * ladder[idx][1] // 100
    return rows


def render(name: str, rows: list[dict]) -> None:
    total_users = sum(r["users"] for r in rows)
    total_revenue = sum(r["revenue30"] for r in rows)
    total_cost = sum(r["cost30"] for r in rows)

    print(f"\n=== Ladder: {name} ===")
    print(f"{'Bậc':<12}{'Ngưỡng':>12}{'Giảm':>6}{'Khách':>8}{'% khách':>9}{'DThu 30n':>14}{'% DThu':>8}{'Chi phí':>13}")
    for r in rows:
        share_u = r["users"] / total_users * 100 if total_users else 0.0
        share_r = r["revenue30"] / total_revenue * 100 if total_revenue else 0.0
        print(
            f"{r['rank']:<12}{r['threshold']:>12,}{r['percent']:>5}%{r['users']:>8}"
            f"{share_u:>8.1f}%{r['revenue30']:>14,}{share_r:>7.1f}%{r['cost30']:>13,}"
        )
    blended = total_cost / total_revenue * 100 if total_revenue else 0.0
    print(f"{'TỔNG':<12}{'':>12}{'':>6}{total_users:>8}{'':>9}{total_revenue:>14,}{'':>8}{total_cost:>13,}")
    print(f"Chi phí gộp: {blended:.2f}% doanh thu 30 ngày (cận trên, chưa trừ đơn dính flash sale)")


def parse_ladder(raw: str) -> list[tuple[int, int]]:
    pairs = []
    for chunk in raw.split(","):
        threshold, percent = chunk.split(":")
        pairs.append((int(threshold), int(percent)))
    pairs.sort()
    return pairs


def main() -> None:
    # Console Windows mac dinh cp1252, khong in duoc tieng Viet co dau.
    with contextlib.suppress(AttributeError, OSError):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default="data/database.sqlite", help="đường dẫn database.sqlite")
    parser.add_argument("--ladder", help="ngưỡng:phần_trăm phân tách bằng dấu phẩy, thay cho các ladder mẫu")
    args = parser.parse_args()

    orders = load_orders(args.db)
    if not orders:
        print(f"Không đọc được đơn nào từ {args.db} (key {KV_ORDERS}).")
        return

    now = datetime.now(TZ)
    users = collect(orders, now)
    completed = sum(u["orders"] for u in users.values())
    lifetime_total = sum(u["lifetime"] for u in users.values())
    print(f"Đơn hoàn thành: {completed:,} | Khách có đơn: {len(users):,} | Doanh thu lifetime: {lifetime_total:,}đ")

    over10 = sum(1 for u in users.values() if u["window"] >= 10_000_000)
    over20 = sum(1 for u in users.values() if u["window"] >= 20_000_000)
    print(f"Khách chi trên 10 triệu trong {RANK_WINDOW_DAYS} ngày: {over10:,} | trên 20 triệu: {over20:,}")

    ladders = {"tuy-chon": parse_ladder(args.ladder)} if args.ladder else LADDERS
    for name, ladder in ladders.items():
        render(name, simulate(users, ladder))


if __name__ == "__main__":
    main()
