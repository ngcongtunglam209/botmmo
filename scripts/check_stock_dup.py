"""Kiểm tra stock bị up trùng của một sản phẩm local stock.

Trả lời hai câu hỏi:
  1. Kho hiện tại của sản phẩm có dòng nào lặp lại, hoặc dòng nào đã từng bán rồi không?
  2. (Nếu truyền file) trong các file .txt đã up, dòng nào đã bán rồi / đang nằm
     trong kho / lặp trong chính file đó / lặp giữa các file?

CHỈ ĐỌC. Mở database ở chế độ read-only nên chạy được trong lúc bot đang chạy.
Chỉ dùng thư viện chuẩn, cùng lý do với scripts/vip_spend_report.py.

Mặc định so khớp theo TÀI KHOẢN: trường đầu tiên trước dấu `|` (email), không
phân biệt hoa thường. Cùng một acc xuất file lần sau có thể mang token khác, so
nguyên dòng sẽ lọt. `--exact` để so nguyên dòng như local_stock_guard. Chỉ in
ra email, không in mật khẩu/token.

    python3 scripts/check_stock_dup.py                          # sản phẩm "2", chỉ soát kho
    python3 scripts/check_stock_dup.py --product 2 up1.txt up2.txt
    python3 scripts/check_stock_dup.py --db /duong/dan.sqlite --product 2 up.txt
    python3 scripts/check_stock_dup.py --no-db up1.txt up2.txt  # chỉ so các file với nhau
    python3 scripts/check_stock_dup.py --selftest
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=7))  # giờ VN, không có DST; tránh phụ thuộc tzdata
KV_ORDERS = "data_order_history.json"
KV_PRODUCTS = "data_products.json"


EXACT = False  # --exact: so nguyên dòng thay vì theo tài khoản


def norm(item) -> str:
    text = str(item or "").strip()
    return text if EXACT else text.split("|", 1)[0].strip().casefold()


def load_kv(conn: sqlite3.Connection, key: str, default):
    row = conn.execute("SELECT value FROM kv_store WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default


def fmt_time(ts) -> str:
    try:
        return datetime.fromtimestamp(float(ts), TZ).strftime("%d/%m %H:%M")
    except (TypeError, ValueError, OSError):
        return str(ts or "?")


def sold_index(orders: list, product_id: str) -> dict[str, list[dict]]:
    """dòng hàng -> các đơn đã giao dòng đó (chỉ đơn của product_id)."""
    index: dict[str, list[dict]] = {}
    for order in orders:
        if not isinstance(order, dict) or str(order.get("product_id") or "") != product_id:
            continue
        items = order.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            key = norm(item)
            if key:
                index.setdefault(key, []).append(order)
    return index


def describe_orders(orders: list[dict]) -> str:
    text = ", ".join(
        f"{o.get('order_code', '?')} (user {o.get('user_id', '?')}, "
        f"{fmt_time(o.get('timestamp') or o.get('created_at'))}, {o.get('status', '?')})"
        for o in orders[:3]
    )
    return text + (f" +{len(orders) - 3} đơn nữa" if len(orders) > 3 else "")


def check(stock: list, sold: dict[str, list[dict]], files: dict[str, list[str]]) -> dict:
    stock_counts = Counter(k for k in map(norm, stock) if k)
    result = {
        "stock_repeated": {k: c for k, c in stock_counts.items() if c > 1},
        "stock_sold": {k: sold[k] for k in stock_counts if k in sold},
        "files": {},
    }
    seen_in: dict[str, list[str]] = {}
    for name, lines in files.items():
        counts = Counter(k for k in map(norm, lines) if k)
        for k in counts:
            seen_in.setdefault(k, []).append(name)
        result["files"][name] = {
            "total": sum(counts.values()),
            "sold": {k: sold[k] for k in counts if k in sold},
            "in_stock": {k: stock_counts[k] for k in counts if k in stock_counts},
            "repeated": {k: c for k, c in counts.items() if c > 1},
        }
    result["cross_file"] = {k: names for k, names in seen_in.items() if len(names) > 1}
    return result


def print_report(product_id: str, product: dict, stock: list, sold: dict, result: dict) -> None:
    print(f"Sản phẩm {product_id}: {product.get('name', '?')}")
    print(f"Tồn kho: {len(stock)} dòng | Số acc khác nhau đã bán: {len(sold)}\n")

    print(f"== KHO HIỆN TẠI: {len(result['stock_repeated'])} dòng bị lặp ==")
    for k, c in result["stock_repeated"].items():
        print(f"  x{c}  {k}")
    print(f"\n== KHO HIỆN TẠI: {len(result['stock_sold'])} dòng ĐÃ BÁN RỒI mà vẫn còn trong kho ==")
    for k, orders in result["stock_sold"].items():
        print(f"  {k}\n      -> {describe_orders(orders)}")

    for name, info in result["files"].items():
        print(f"\n== FILE {name}: {info['total']} dòng ==")
        print(f"  Đã bán rồi: {len(info['sold'])}")
        for k, orders in info["sold"].items():
            print(f"    {k}\n        -> {describe_orders(orders)}")
        print(f"  Đang nằm trong kho: {len(info['in_stock'])} (chỉ liệt kê dòng có >1 bản trong kho)")
        for k, c in info["in_stock"].items():
            if c > 1:
                print(f"    x{c}  {k}")
        print(f"  Lặp trong chính file: {len(info['repeated'])}")
        for k, c in info["repeated"].items():
            print(f"    x{c}  {k}")

    if result["cross_file"]:
        print(f"\n== {len(result['cross_file'])} dòng xuất hiện ở nhiều file ==")
        for k, names in result["cross_file"].items():
            print(f"  {k}  <- {', '.join(names)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default="data/database.sqlite", help="đường dẫn database.sqlite")
    parser.add_argument("--product", default="2", help="product_id cần kiểm tra (mặc định 2)")
    parser.add_argument("files", nargs="*", help="các file .txt đã up (tuỳ chọn)")
    parser.add_argument("--exact", action="store_true", help="so nguyên dòng thay vì theo email")
    parser.add_argument("--no-db", action="store_true", help="không đọc database, chỉ so các file với nhau")
    args = parser.parse_args()
    global EXACT
    EXACT = args.exact

    if args.no_db:
        products, orders = {args.product: {"name": "(không dùng DB, chỉ so file)", "stock": []}}, []
    else:
        with contextlib.closing(sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)) as conn:
            products = load_kv(conn, KV_PRODUCTS, {})
            orders = load_kv(conn, KV_ORDERS, [])

    product = products.get(args.product)
    if not isinstance(product, dict):
        print(f"Không tìm thấy sản phẩm '{args.product}'. Có: {', '.join(list(products)[:30])}", file=sys.stderr)
        return 1

    files = {}
    for path in args.files:
        with open(path, encoding="utf-8-sig") as f:
            files[path] = f.read().splitlines()

    stock = product.get("stock") if isinstance(product.get("stock"), list) else []
    sold = sold_index(orders, args.product)
    print_report(args.product, product, stock, sold, check(stock, sold, files))
    return 0


def _selftest() -> None:
    sold = sold_index(
        [{"product_id": "2", "order_code": "A1", "items": ["acc1|pw", " Acc2|pw|tok1 "]},
         {"product_id": "3", "order_code": "B1", "items": ["acc9|pw"]}],
        "2",
    )
    assert set(sold) == {"acc1", "acc2"}
    r = check(["acc1|pw", "acc3|pw", "ACC3|pw2 ", "acc9|pw"], sold,
              {"a.txt": ["acc2|pw|tok2", "acc3|pw", "acc4|pw", "acc4|x", ""], "b.txt": ["acc4|pw"]})
    assert r["stock_repeated"] == {"acc3": 2}
    assert set(r["stock_sold"]) == {"acc1"}  # acc9 bán ở sản phẩm khác, không tính
    fa = r["files"]["a.txt"]
    assert set(fa["sold"]) == {"acc2"} and fa["in_stock"] == {"acc3": 2} and fa["repeated"] == {"acc4": 2}
    assert r["cross_file"] == {"acc4": ["a.txt", "b.txt"]}


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        _selftest()
        print("ok")
        sys.exit(0)
    sys.exit(main())
