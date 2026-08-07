def init_db():
    """Khởi tạo database SQLite với WAL mode và PRAGMA tối ưu."""
    from contextlib import closing
    import sqlite3 as _sqlite3
    with closing(_sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        # WAL mode: cho phép đọc song song khi đang ghi, giảm lock contention
        cursor.execute("PRAGMA journal_mode=WAL")
        # synchronous=NORMAL: an toàn với WAL, nhanh hơn FULL ~2-3x
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Giới hạn WAL file tối đa 32MB để tránh phình quá lớn
        cursor.execute("PRAGMA journal_size_limit=33554432")
        # Tăng cache lên 16MB (mặc định 2MB) cho hiệu suất đọc
        cursor.execute("PRAGMA cache_size=-16000")
        # Bật foreign keys (best practice)
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS processed_transactions (tx_id TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'completed', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL DEFAULT 0)")
        tx_columns = {row[1] for row in cursor.execute("PRAGMA table_info(processed_transactions)")}
        if "status" not in tx_columns:
            cursor.execute("ALTER TABLE processed_transactions ADD COLUMN status TEXT NOT NULL DEFAULT 'completed'")
        if "updated_at" not in tx_columns:
            cursor.execute("ALTER TABLE processed_transactions ADD COLUMN updated_at INTEGER NOT NULL DEFAULT 0")
        cursor.execute("UPDATE processed_transactions SET updated_at=created_at WHERE updated_at=0")
        cursor.execute("CREATE TABLE IF NOT EXISTS partner_order_refs (actor_scope TEXT NOT NULL, partner_ref TEXT NOT NULL, status TEXT NOT NULL, order_code TEXT, updated_at INTEGER NOT NULL, PRIMARY KEY(actor_scope, partner_ref))")
        cursor.execute("CREATE TABLE IF NOT EXISTS admin_sessions (token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS admin_login_attempts (ip TEXT NOT NULL, attempted_at INTEGER NOT NULL)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_login_attempts_ip_time ON admin_login_attempts(ip, attempted_at)")
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS api_request_logs ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, requested_at REAL NOT NULL, "
            "key_fingerprint TEXT NOT NULL DEFAULT '', partner_name TEXT NOT NULL DEFAULT '', "
            "client_ip TEXT NOT NULL DEFAULT '', method TEXT NOT NULL, endpoint TEXT NOT NULL, "
            "status_code INTEGER NOT NULL, response_ms REAL NOT NULL DEFAULT 0)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_logs_key_time ON api_request_logs(key_fingerprint, requested_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_logs_status_time ON api_request_logs(status_code, requested_at DESC)")
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS api_partner_ledger ("
            "entry_id TEXT PRIMARY KEY, created_at REAL NOT NULL, key_fingerprint TEXT NOT NULL, "
            "partner_name TEXT NOT NULL DEFAULT '', entry_type TEXT NOT NULL, amount INTEGER NOT NULL, "
            "balance_before INTEGER NOT NULL, balance_after INTEGER NOT NULL, reference TEXT NOT NULL DEFAULT '', "
            "reason TEXT NOT NULL DEFAULT '', admin_actor TEXT NOT NULL DEFAULT '', idempotency_key TEXT NOT NULL UNIQUE)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_ledger_key_time ON api_partner_ledger(key_fingerprint, created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_ledger_type_time ON api_partner_ledger(entry_type, created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_ledger_reference ON api_partner_ledger(reference)")
        conn.commit()
        logger.info("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> SQLite initialized: WAL mode, NORMAL sync, 16MB cache")


def _backfill_durable_registries():
    """One-time compatible migration from legacy JSON blobs into unique tables."""
    from contextlib import closing
    now = int(time.time())
    with closing(_db_connect()) as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO processed_transactions(tx_id, status, created_at, updated_at) VALUES (?, 'completed', ?, ?)",
            [(str(tx_id), now, now) for tx_id in processed_transaction_ids if str(tx_id).strip()],
        )
        refs = []
        for order in order_history:
            ref = str(order.get("api_partner_ref_key") or order.get("api_partner_ref") or "").strip().upper()
            if not ref:
                continue
            scope = "admin-master" if not order.get("api_partner_key_hash") else str(order.get("api_partner_key_hash"))
            refs.append((scope, ref, "completed", str(order.get("order_code") or ""), now))
        conn.executemany(
            "INSERT OR IGNORE INTO partner_order_refs(actor_scope, partner_ref, status, order_code, updated_at) VALUES (?, ?, ?, ?, ?)",
            refs,
        )
        conn.commit()


def _db_connect():
    import sqlite3 as _sqlite3
    conn = _sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def db_claim_transaction(tx_id: str) -> bool:
    """Atomically claim a provider transaction ID across processes."""
    from contextlib import closing
    import sqlite3 as _sqlite3
    normalized = str(tx_id or "").strip()
    if not normalized:
        return False
    now = int(time.time())
    stale_before = now - 600
    try:
        with closing(_db_connect()) as conn:
            cursor = conn.execute(
                "INSERT INTO processed_transactions(tx_id, status, created_at, updated_at) "
                "VALUES (?, 'processing', ?, ?) "
                "ON CONFLICT(tx_id) DO UPDATE SET status='processing', updated_at=excluded.updated_at "
                "WHERE processed_transactions.status='processing' AND processed_transactions.updated_at < ?",
                (normalized, now, now, stale_before),
            )
            conn.commit()
            return cursor.rowcount == 1
    except _sqlite3.Error as exc:
        logger.error(f"Cannot claim transaction {normalized}: {exc}")
        return False


def db_transaction_exists(tx_id: str) -> bool:
    from contextlib import closing
    normalized = str(tx_id or "").strip()
    if not normalized:
        return False
    if normalized in processed_transaction_ids:
        return True
    with closing(_db_connect()) as conn:
        row = conn.execute("SELECT 1 FROM processed_transactions WHERE tx_id=?", (normalized,)).fetchone()
    if row:
        processed_transaction_ids.add(normalized)
    return bool(row)


def db_complete_transaction(tx_id: str) -> bool:
    from contextlib import closing
    normalized = str(tx_id or "").strip()
    if not normalized:
        return False
    now = int(time.time())
    with closing(_db_connect()) as conn:
        conn.execute(
            "INSERT INTO processed_transactions(tx_id, status, created_at, updated_at) VALUES (?, 'completed', ?, ?) ON CONFLICT(tx_id) DO UPDATE SET status='completed', updated_at=excluded.updated_at",
            (normalized, now, now),
        )
        conn.commit()
    processed_transaction_ids.add(normalized)
    return True


def db_release_transaction(tx_id: str) -> bool:
    """Release only an unfinished claim so a later scan can retry it."""
    from contextlib import closing
    normalized = str(tx_id or "").strip()
    if not normalized:
        return False
    with closing(_db_connect()) as conn:
        cursor = conn.execute(
            "DELETE FROM processed_transactions WHERE tx_id=? AND status='processing'",
            (normalized,),
        )
        conn.commit()
    processed_transaction_ids.discard(normalized)
    return cursor.rowcount == 1


def db_reserve_partner_ref(actor_scope: str, partner_ref: str) -> bool:
    from contextlib import closing
    with closing(_db_connect()) as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO partner_order_refs(actor_scope, partner_ref, status, updated_at) VALUES (?, ?, 'processing', ?)",
            (str(actor_scope), str(partner_ref).upper(), int(time.time())),
        )
        conn.commit()
        return cursor.rowcount == 1


def db_complete_partner_ref(actor_scope: str, partner_ref: str, order_code: str):
    from contextlib import closing
    with closing(_db_connect()) as conn:
        conn.execute(
            "UPDATE partner_order_refs SET status='completed', order_code=?, updated_at=? WHERE actor_scope=? AND partner_ref=?",
            (str(order_code), int(time.time()), str(actor_scope), str(partner_ref).upper()),
        )
        conn.commit()


def db_mark_partner_ref_review(actor_scope: str, partner_ref: str):
    from contextlib import closing
    with closing(_db_connect()) as conn:
        conn.execute(
            "UPDATE partner_order_refs SET status='manual_review', updated_at=? WHERE actor_scope=? AND partner_ref=? AND status='processing'",
            (int(time.time()), str(actor_scope), str(partner_ref).upper()),
        )
        conn.commit()


def db_release_partner_ref(actor_scope: str, partner_ref: str):
    from contextlib import closing
    with closing(_db_connect()) as conn:
        conn.execute(
            "DELETE FROM partner_order_refs WHERE actor_scope=? AND partner_ref=? AND status='processing'",
            (str(actor_scope), str(partner_ref).upper()),
        )
        conn.commit()


def _admin_token_hash(token: str) -> str:
    return hashlib.sha256(str(token).encode()).hexdigest()


def db_create_admin_session(token: str, expires_at: int):
    from contextlib import closing
    now = int(time.time())
    with closing(_db_connect()) as conn:
        conn.execute("DELETE FROM admin_sessions WHERE expires_at < ?", (now,))
        conn.execute(
            "INSERT OR REPLACE INTO admin_sessions(token_hash, expires_at, created_at) VALUES (?, ?, ?)",
            (_admin_token_hash(token), int(expires_at), now),
        )
        conn.commit()


def db_admin_session_exists(token: str) -> bool:
    from contextlib import closing
    if not token:
        return False
    now = int(time.time())
    with closing(_db_connect()) as conn:
        row = conn.execute(
            "SELECT 1 FROM admin_sessions WHERE token_hash=? AND expires_at>=?",
            (_admin_token_hash(token), now),
        ).fetchone()
    return bool(row)


def db_revoke_admin_session(token: str):
    from contextlib import closing
    if not token:
        return
    with closing(_db_connect()) as conn:
        conn.execute("DELETE FROM admin_sessions WHERE token_hash=?", (_admin_token_hash(token),))
        conn.commit()


def db_admin_login_attempt_count(ip: str, since: int) -> int:
    from contextlib import closing
    with closing(_db_connect()) as conn:
        conn.execute("DELETE FROM admin_login_attempts WHERE attempted_at < ?", (int(since),))
        row = conn.execute(
            "SELECT COUNT(*) FROM admin_login_attempts WHERE ip=? AND attempted_at>=?",
            (str(ip), int(since)),
        ).fetchone()
        conn.commit()
    return int(row[0] if row else 0)


def db_record_admin_login_attempt(ip: str, attempted_at: int):
    from contextlib import closing
    with closing(_db_connect()) as conn:
        conn.execute(
            "INSERT INTO admin_login_attempts(ip, attempted_at) VALUES (?, ?)",
            (str(ip), int(attempted_at)),
        )
        conn.commit()


def db_clear_admin_login_attempts(ip: str):
    from contextlib import closing
    if not ip:
        return
    with closing(_db_connect()) as conn:
        conn.execute("DELETE FROM admin_login_attempts WHERE ip=?", (str(ip),))
        conn.commit()


def db_record_api_request(
    key_fingerprint: str,
    partner_name: str,
    client_ip: str,
    method: str,
    endpoint: str,
    status_code: int,
    response_ms: float,
):
    """Persist one sanitized API access event; never stores keys, bodies, or query strings."""
    now = time.time()
    with closing(_db_connect()) as conn:
        conn.execute(
            "INSERT INTO api_request_logs(requested_at,key_fingerprint,partner_name,client_ip,method,endpoint,status_code,response_ms) VALUES (?,?,?,?,?,?,?,?)",
            (now, str(key_fingerprint or ""), str(partner_name or ""), str(client_ip or ""), str(method or "")[:12], str(endpoint or "")[:240], int(status_code), max(0.0, float(response_ms or 0))),
        )
        # ponytail: opportunistic hourly-sized cleanup; add a scheduled vacuum only above millions of rows.
        if int(now) % 200 == 0:
            conn.execute("DELETE FROM api_request_logs WHERE requested_at < ?", (now - 30 * 86400,))
        conn.commit()


def db_api_request_count_since(key_fingerprint: str, since: float) -> int:
    with closing(_db_connect()) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM api_request_logs WHERE key_fingerprint=? AND requested_at>=?",
            (str(key_fingerprint or ""), float(since)),
        ).fetchone()
    return int(row[0] if row else 0)


def db_api_recent_logs(key_fingerprint: str = "", limit: int = 80) -> list[dict]:
    safe_limit = max(1, min(500, int(limit or 80)))
    where = "WHERE key_fingerprint=?" if key_fingerprint else ""
    params = [str(key_fingerprint)] if key_fingerprint else []
    params.append(safe_limit)
    with closing(_db_connect()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT requested_at,key_fingerprint,partner_name,client_ip,method,endpoint,status_code,response_ms FROM api_request_logs {where} ORDER BY requested_at DESC LIMIT ?",
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def db_api_analytics(key_fingerprint: str = "", days: int = 14) -> dict:
    safe_days = max(1, min(90, int(days or 14)))
    since = time.time() - safe_days * 86400
    where = "requested_at>=?" + (" AND key_fingerprint=?" if key_fingerprint else "")
    params = [since] + ([str(key_fingerprint)] if key_fingerprint else [])
    with closing(_db_connect()) as conn:
        summary = conn.execute(
            f"SELECT COUNT(*), SUM(CASE WHEN status_code>=400 THEN 1 ELSE 0 END), AVG(response_ms) FROM api_request_logs WHERE {where}",
            params,
        ).fetchone()
        daily = conn.execute(
            f"SELECT date(requested_at, 'unixepoch', '+7 hours') AS day, COUNT(*) AS requests, SUM(CASE WHEN status_code>=400 THEN 1 ELSE 0 END) AS errors FROM api_request_logs WHERE {where} GROUP BY day ORDER BY day",
            params,
        ).fetchall()
    total = int(summary[0] or 0) if summary else 0
    errors = int(summary[1] or 0) if summary else 0
    return {
        "total": total,
        "errors": errors,
        "error_rate": round(errors * 100 / total, 1) if total else 0.0,
        "avg_ms": round(float(summary[2] or 0), 1) if summary else 0.0,
        "daily": [{"day": row[0], "requests": int(row[1]), "errors": int(row[2] or 0)} for row in daily],
    }


def db_record_api_partner_ledger(
    key_fingerprint: str,
    partner_name: str,
    entry_type: str,
    amount: int,
    balance_before: int,
    balance_after: int,
    *,
    reference: str = "",
    reason: str = "",
    admin_actor: str = "",
    idempotency_key: str = "",
) -> bool:
    """Append an idempotent balance event. Raw API keys must never be passed here."""
    normalized_type = str(entry_type or "adjustment").lower()
    if normalized_type not in {"deposit", "usage", "refund", "adjustment"}:
        raise ValueError("invalid ledger entry type")
    fingerprint = str(key_fingerprint or "").strip()
    if not fingerprint:
        raise ValueError("key fingerprint is required")
    created_at = time.time()
    dedupe = str(idempotency_key or f"manual:{fingerprint}:{time.time_ns()}")[:180]
    entry_id = hashlib.sha256(dedupe.encode()).hexdigest()[:24]
    with closing(_db_connect()) as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO api_partner_ledger(entry_id,created_at,key_fingerprint,partner_name,entry_type,amount,balance_before,balance_after,reference,reason,admin_actor,idempotency_key) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (entry_id, created_at, fingerprint, str(partner_name or "")[:160], normalized_type, int(amount), int(balance_before), int(balance_after), str(reference or "")[:160], str(reason or "")[:500], str(admin_actor or "")[:160], dedupe),
        )
        conn.commit()
        return cursor.rowcount == 1


def db_api_partner_ledger(key_fingerprint: str = "", entry_type: str = "", limit: int = 100, before: float = 0) -> list[dict]:
    clauses, params = [], []
    if key_fingerprint:
        clauses.append("key_fingerprint=?"); params.append(str(key_fingerprint))
    if entry_type:
        clauses.append("entry_type=?"); params.append(str(entry_type).lower())
    if before:
        clauses.append("created_at<?"); params.append(float(before))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(max(1, min(500, int(limit or 100))))
    with closing(_db_connect()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT entry_id,created_at,key_fingerprint,partner_name,entry_type,amount,balance_before,balance_after,reference,reason,admin_actor FROM api_partner_ledger {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def db_api_partner_ledger_summary(key_fingerprint: str = "", since: float = 0) -> dict:
    clauses, params = [], []
    if key_fingerprint:
        clauses.append("key_fingerprint=?"); params.append(str(key_fingerprint))
    if since:
        clauses.append("created_at>=?"); params.append(float(since))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with closing(_db_connect()) as conn:
        rows = conn.execute(
            f"SELECT entry_type,COALESCE(SUM(amount),0),COUNT(*) FROM api_partner_ledger {where} GROUP BY entry_type",
            params,
        ).fetchall()
    result = {"deposit": 0, "usage": 0, "refund": 0, "adjustment": 0, "count": 0, "net": 0}
    for entry_type_value, total, count in rows:
        result[str(entry_type_value)] = int(total or 0)
        result["count"] += int(count or 0)
        result["net"] += int(total or 0)
    return result


def load_from_db(key, default_value, migrate_file=None):
    """Load data từ SQLite KV store (sync cho startup)"""
    from contextlib import closing
    import sqlite3 as _sqlite3
    try:
        with closing(_sqlite3.connect(DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM kv_store WHERE key=?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            
            # Migrate từ JSON cũ nếu tồn tại
            value_to_save = default_value
            if migrate_file and os.path.exists(migrate_file):
                try:
                    with open(migrate_file, 'r', encoding='utf-8') as f: 
                        value_to_save = json.load(f)
                    bak_path = f"{migrate_file}.bak"
                    os.replace(migrate_file, bak_path)
                    logger.info(f"Đã migrate {migrate_file} vào {DB_PATH}")
                    # Xóa file .bak sau khi migrate thành công
                    try:
                        os.remove(bak_path)
                        logger.info(f"Đã xóa file backup: {bak_path}")
                    except OSError:
                        pass
                except (json.JSONDecodeError, OSError) as e:
                    logger.error(f"Lỗi đọc JSON {migrate_file}: {e}")
            
            # Lưu vào DB
            cursor.execute("INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)", (key, json.dumps(value_to_save, ensure_ascii=False)))
            conn.commit()
            return value_to_save
    except (_sqlite3.Error, json.JSONDecodeError) as e:
        logger.error(f"DB Error loading {key}: {e}")
        return default_value

async def _apply_wal_pragmas(db):
    """Áp dụng PRAGMA tối ưu cho mỗi kết nối aiosqlite."""
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute("PRAGMA cache_size=-16000")

async def save_data(force=False, tables=None):
    """Lưu dữ liệu an toàn vào SQLite KV với WAL mode và atomic transaction."""
    current_time = time.time()
    
    if not force and not tables and (current_time - _cache["last_save_time"]) < _cache["save_debounce"]:
        _cache["pending_save"] = True
        return
    
    async with file_lock:
        try:
            def json_dumps_optimized(data):
                return json.dumps(data, separators=(',', ':'), ensure_ascii=False)
                

            
            need_cleanup = (current_time - _cache["last_cleanup_time"]) >= 3600
            if need_cleanup:
                removed_duplicates = _dedupe_order_history_in_place()
                _rebuild_order_indexes()
                if removed_duplicates:
                    logger.warning(f"Da loai bo {removed_duplicates} ban ghi don hang trung ma trong qua trinh cleanup.")
                _cache["last_cleanup_time"] = current_time
            
            should_update_product_stock_flags = (
                tables is None
                or PRODUCTS_FILE in set(tables)
            )
            if should_update_product_stock_flags:
                # Track out-of-stock duration only when product data is being saved.
                for pid, p in products.items():
                    if isinstance(p, dict):
                        has_stock = True
                        if not p.get("requires_gmail"):
                            has_stock = len(p.get("stock", [])) > 0

                        if not has_stock:
                            if "out_of_stock_since" not in p:
                                p["out_of_stock_since"] = current_time
                        else:
                            p.pop("out_of_stock_since", None)
                
            files_to_save = [
                (HISTORY_FILE, order_history), 
                (PROCESSED_TX_FILE, list(processed_transaction_ids)), 
                (USERS_FILE, user_data_db), 
                (BANNED_USERS_FILE, list(banned_users)), 
                (COUPONS_FILE, coupons), 
                (API_KEYS_FILE, api_keys),
                (PENDING_ORDERS_FILE, pending_orders),
                ("data_pending_api_deposits.json", pending_api_deposits),
                (PRODUCTS_FILE, products),
                (CUSTOM_STORE_ICONS_FILE, custom_store_icons),
                (STORE_CATEGORIES_FILE, store_categories),
                (PENDING_MANUAL_ORDERS_FILE, pending_manual_orders),
                (WARRANTY_CLAIMS_FILE, warranty_claims),
                (PRODUCT_RATINGS_FILE, product_ratings),
                (REFERRAL_DATA_FILE, referral_data),
                ("data_giveaways.json", active_giveaways), 
                (LIVE_CHATS_FILE, live_chats),
                (DICE_GAME_FILE, dice_game_data),
                (PROMO_BUDGET_FILE, daily_promo_tracker),  
                (WITHDRAWALS_FILE, withdrawal_requests),  
                (STOCK_WAITLIST_FILE, stock_waitlist),
                (FLASH_SALES_FILE, flash_sales),
                (COMBO_DEALS_FILE, combo_deals),
                (WHEEL_DATA_FILE, wheel_data),
                (TRANSACTION_HISTORY_FILE, transaction_history),
                (ADMIN_ACTION_LOG_FILE, admin_action_log)
            ]
            
            if tables:
                files_to_save = [f for f in files_to_save if f[0] in tables]
            
            serialized_data = []
            for key, data in files_to_save:
                content = await asyncio.to_thread(json_dumps_optimized, data)
                serialized_data.append((key, content))
                
            async with aiosqlite.connect(DB_PATH) as db:
                await _apply_wal_pragmas(db)
                await db.execute('BEGIN TRANSACTION')
                for key, content in serialized_data:
                    await db.execute("INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)", (key, content))
                await db.commit()
                
            _cache["last_save_time"] = current_time
            _cache["pending_save"] = False
            
            logger.debug(
                "Saved %s table(s) to SQLite. orders=%s",
                len(serialized_data),
                len(order_history),
            )
        except (sqlite3.Error, aiosqlite.Error, ValueError) as e:
            logger.error(f"❌ Lỗi nghiêm trọng khi lưu dữ liệu vào SQLite: {e}", exc_info=True)

async def save_critical_tables(*table_keys):
    """Save ngay lập tức các bảng quan trọng (payment, order) không qua debounce.
    
    Dùng cho các luồng nghiệp vụ critical: match payment, tạo đơn hàng, etc.
    """
    if table_keys:
        await save_data(force=True, tables=list(table_keys))
    else:
        await save_data(force=True)

async def save_data_debounced(context: ContextTypes.DEFAULT_TYPE):
    """Background task để save dữ liệu pending"""
    if _cache.get("pending_save"):
        await save_data(force=True)

def load_data():
    global order_history, processed_transaction_ids, user_data_db, banned_users, coupons, pending_orders, api_keys, pending_api_deposits, products, custom_store_icons, store_categories, pending_manual_orders, stock_waitlist, flash_sales, combo_deals, wheel_data
    global warranty_claims, product_ratings, referral_data, live_chats, active_giveaways, dice_game_data, withdrawal_requests, transaction_history, admin_action_log, daily_promo_tracker
    
    init_db()

    order_history = load_from_db(HISTORY_FILE, [], HISTORY_FILE)
    processed_transaction_ids = set(load_from_db(PROCESSED_TX_FILE, [], PROCESSED_TX_FILE))
    _backfill_durable_registries()
    user_data_db = load_from_db(USERS_FILE, {}, USERS_FILE)
    banned_users = set(load_from_db(BANNED_USERS_FILE, [], BANNED_USERS_FILE))
    coupons = load_from_db(COUPONS_FILE, {}, COUPONS_FILE)
    pending_orders = load_from_db(PENDING_ORDERS_FILE, {}, PENDING_ORDERS_FILE)
    api_keys = load_from_db(API_KEYS_FILE, {}, API_KEYS_FILE)
    products = load_from_db(PRODUCTS_FILE, {}, PRODUCTS_FILE)
    custom_store_icons = load_from_db(CUSTOM_STORE_ICONS_FILE, {}, CUSTOM_STORE_ICONS_FILE)
    if not isinstance(custom_store_icons, dict):
        custom_store_icons = {}
    store_categories = load_from_db(STORE_CATEGORIES_FILE, {}, STORE_CATEGORIES_FILE)
    if not isinstance(store_categories, dict):
        store_categories = {}
    pending_api_deposits = load_from_db("data_pending_api_deposits.json", {}, "data_pending_api_deposits.json")
    pending_manual_orders = load_from_db(PENDING_MANUAL_ORDERS_FILE, {}, PENDING_MANUAL_ORDERS_FILE)
    
    # Load Advanced Features Data
    warranty_claims = load_from_db(WARRANTY_CLAIMS_FILE, {}, WARRANTY_CLAIMS_FILE)
    product_ratings = load_from_db(PRODUCT_RATINGS_FILE, {}, PRODUCT_RATINGS_FILE)
    referral_data = load_from_db(REFERRAL_DATA_FILE, {}, REFERRAL_DATA_FILE)
    live_chats = load_from_db(LIVE_CHATS_FILE, {}, LIVE_CHATS_FILE)
    active_giveaways = load_from_db("data_giveaways.json", {}, "data_giveaways.json")
    dice_game_data = load_from_db(DICE_GAME_FILE, {}, DICE_GAME_FILE)
    daily_promo_tracker = load_from_db(PROMO_BUDGET_FILE, {}, PROMO_BUDGET_FILE)
    withdrawal_requests = load_from_db(WITHDRAWALS_FILE, {}, WITHDRAWALS_FILE)
    stock_waitlist = load_from_db(STOCK_WAITLIST_FILE, {}, STOCK_WAITLIST_FILE)
    flash_sales = load_from_db(FLASH_SALES_FILE, {}, FLASH_SALES_FILE)
    combo_deals = load_from_db(COMBO_DEALS_FILE, {}, COMBO_DEALS_FILE)
    wheel_data = load_from_db(WHEEL_DATA_FILE, {}, WHEEL_DATA_FILE)
    transaction_history = load_from_db(TRANSACTION_HISTORY_FILE, {}, TRANSACTION_HISTORY_FILE)
    admin_action_log = load_from_db(ADMIN_ACTION_LOG_FILE, [], ADMIN_ACTION_LOG_FILE)
    if not isinstance(admin_action_log, list):
        admin_action_log = []

    runtime_binding_names = [
        "order_history",
        "processed_transaction_ids",
        "user_data_db",
        "banned_users",
        "coupons",
        "pending_orders",
        "api_keys",
        "pending_api_deposits",
        "products",
        "custom_store_icons",
        "store_categories",
        "pending_manual_orders",
        "stock_waitlist",
        "flash_sales",
        "combo_deals",
        "wheel_data",
        "warranty_claims",
        "product_ratings",
        "referral_data",
        "live_chats",
        "active_giveaways",
        "dice_game_data",
        "withdrawal_requests",
        "transaction_history",
        "admin_action_log",
        "daily_promo_tracker",
        "order_index",
        "user_order_index",
        "api_partner_ref_index",
    ]

    try:
        from app.core.runtime_loader import sync_runtime_bindings
        sync_runtime_bindings(globals(), runtime_binding_names)
    except (ValueError, TypeError, KeyError, AttributeError, ImportError) as sync_error:
        logger.debug(f"Runtime binding pre-sync skipped: {sync_error}")

    legacy_refunds_backfilled = 0
    for legacy_order in order_history:
        if not isinstance(legacy_order, dict) or not legacy_order.get("refunded_at"):
            continue
        changed = False
        if not str(legacy_order.get("refund_target") or "").strip():
            legacy_status = str(legacy_order.get("status") or "").casefold()
            if "ví chung" in legacy_status or "vi chung" in legacy_status:
                legacy_order["refund_target"] = "Ví chung"
            elif "ngân hàng" in legacy_status or "ngan hang" in legacy_status:
                legacy_order["refund_target"] = "Ngân hàng"
            elif "hoàn" in legacy_status or "hoan" in legacy_status or "refund" in legacy_status:
                legacy_order["refund_target"] = "Ví Bot"
            else:
                legacy_order["refund_target"] = "Không rõ (dữ liệu cũ)"
            changed = True
        try:
            known_refund_amount = int(legacy_order.get("refund_amount", 0) or 0)
        except (TypeError, ValueError):
            known_refund_amount = 0
        if known_refund_amount <= 0:
            # The old schema did not persist the exact amount. Do not invent a
            # value from the order total because historical refunds may be partial.
            if not legacy_order.get("refund_amount_legacy_unknown"):
                legacy_order["refund_amount_legacy_unknown"] = True
                changed = True
        if changed:
            legacy_order["refund_metadata_backfilled"] = True
            legacy_refunds_backfilled += 1

    removed_duplicates = _dedupe_order_history_in_place()
    _rebuild_order_indexes()
    if removed_duplicates or legacy_refunds_backfilled:
        _cache["pending_save"] = True
    if legacy_refunds_backfilled:
        logger.info(f"Da bo sung metadata cho {legacy_refunds_backfilled} ban ghi hoan tien cu.")
    if removed_duplicates:
        logger.warning(f"Da loai bo {removed_duplicates} ban ghi don hang trung ma de giu index nhat quan.")
            
    if not isinstance(active_giveaways, dict): active_giveaways = {}

    try:
        from app.core.runtime_loader import sync_runtime_bindings

        sync_runtime_bindings(globals(), runtime_binding_names)
    except (ValueError, TypeError, KeyError, AttributeError, ImportError) as sync_error:
        logger.debug(f"Runtime binding sync skipped: {sync_error}")
             
    try:
        from app.state import app_state
        app_state.bridge_from_globals(globals())
    except ImportError:
        pass
    logger.info(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Dữ liệu đã được tải từ SQLite. Orders: {len(order_history)}, Index: {len(order_index)}")

