# ==============================================================================
#  GIVEAWAY SYSTEM HELPER FUNCTIONS
# ==============================================================================

def parse_ga_time(time_str):
    """Parse time string (30, 1h, 24h) to seconds"""
    try:
        time_str = str(time_str).lower().strip()
        if time_str == '0': return 0
        
        if 'h' in time_str:
            hours = float(time_str.replace('h', ''))
            return int(hours * 3600)
        elif 'm' in time_str:
            minutes = float(time_str.replace('m', ''))
            return int(minutes * 60)
        else:
            # Default to minutes if just number
            return int(float(time_str) * 60)
    except (TypeError, ValueError):
        return None


async def auto_end_giveaway_job(context: ContextTypes.DEFAULT_TYPE):
    """Check for expired giveaways"""
    now = time.time()
    expired = []
    
    # Create copy to avoid runtime validation errors during iteration
    for ga_id, ga in list(active_giveaways.items()):
        if ga.get('end_time', 0) > 0 and ga['end_time'] <= now and ga.get('status') == 'active':
            expired.append(ga_id)
            
    for ga_id in expired:
        await draw_ga_winners(context, ga_id)


# ==============================================================================
#  AUTO-BACKUP SYSTEM (NEW)
# ==============================================================================

def _legacy_create_backup_zip_json_export():
    """Create a ZIP file containing all JSON data files exported from SQLite"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"backup_lamshop_{timestamp}.zip"
        
        # Connect to SQLite and dump to JSON files first
        exported_files = []
        try:
            with closing(sqlite3.connect(DB_PATH)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM kv_store")
                for row in cursor.fetchall():
                    key, value = row[0], row[1]
                    try:
                        # Value should be valid JSON text
                        data = json.loads(value)
                        with open(key, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        exported_files.append(key)
                    except (sqlite3.Error, aiosqlite.Error, ValueError) as e:
                        logger.error(f"Error dumping {key}: {e}")
        except (sqlite3.Error, aiosqlite.Error, ValueError) as e:
            logger.error(f"Error reading SQLite for backup: {e}")
            
        # If no files, fallback to old list just in case
        if not exported_files:
            exported_files = [
                USERS_FILE, HISTORY_FILE, PRODUCTS_FILE,
                LINKS_FILE, BANNED_USERS_FILE, PENDING_ORDERS_FILE,
                PENDING_MANUAL_ORDERS_FILE,
                COUPONS_FILE, PROCESSED_TX_FILE, API_KEYS_FILE,
                "data_pending_api_deposits.json",
                WARRANTY_CLAIMS_FILE, PRODUCT_RATINGS_FILE,
                REFERRAL_DATA_FILE, LIVE_CHATS_FILE, "data_giveaways.json",
                DICE_GAME_FILE, WITHDRAWALS_FILE, TRANSACTION_HISTORY_FILE,
                ADMIN_ACTION_LOG_FILE
            ]
        
        # Create ZIP
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in exported_files:
                if os.path.exists(file_path):
                    zipf.write(file_path, os.path.basename(file_path))
                    
        return zip_filename
    except (sqlite3.Error, aiosqlite.Error, ValueError) as e:
        logger.error(f"❌ Failed to create backup ZIP: {e}")
        return None

def get_backup_file_specs():
    """Canonical list of payloads that must be included in backup/restore."""
    return [
        (LINKS_FILE, []),
        (HISTORY_FILE, []),
        (PROCESSED_TX_FILE, []),
        (USERS_FILE, {}),
        (BANNED_USERS_FILE, []),
        (COUPONS_FILE, {}),
        (API_KEYS_FILE, {}),
        (PENDING_ORDERS_FILE, {}),
        ("data_pending_api_deposits.json", {}),
        (PRODUCTS_FILE, {}),
        (PENDING_MANUAL_ORDERS_FILE, {}),
        (WARRANTY_CLAIMS_FILE, {}),
        (PRODUCT_RATINGS_FILE, {}),
        (REFERRAL_DATA_FILE, {}),
        ("data_giveaways.json", {}),
        (LIVE_CHATS_FILE, {}),
        (DICE_GAME_FILE, {}),
        (PROMO_BUDGET_FILE, {}),
        (WITHDRAWALS_FILE, {}),
        (STOCK_WAITLIST_FILE, {}),
        (FLASH_SALES_FILE, {}),
        (COMBO_DEALS_FILE, {}),
        (WHEEL_DATA_FILE, {}),
        (TRANSACTION_HISTORY_FILE, {}),
        (ADMIN_ACTION_LOG_FILE, []),
        (CUSTOM_STORE_ICONS_FILE, {}),
    ]


def get_backup_file_names():
    return [file_name for file_name, _ in get_backup_file_specs()]


def _backup_root_dir():
    return os.path.dirname(os.path.abspath(DB_PATH)) or os.getcwd()


def _load_backup_rows_from_db(keys=None):
    wanted_keys = set(keys or get_backup_file_names())
    rows = {}
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM kv_store")
        for key, value in cursor.fetchall():
            if key in wanted_keys:
                rows[key] = value
    return rows


def _serialize_backup_payload(data, pretty=False):
    kwargs = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    return json.dumps(data, **kwargs)


def _parse_backup_payload(raw_value):
    if isinstance(raw_value, bytes):
        raw_value = raw_value.decode("utf-8-sig")
    return json.loads(raw_value)


_DURABLE_BACKUP_TABLES = {
    "_processed_transactions.json": (
        "processed_transactions",
        ("tx_id", "status", "created_at", "updated_at"),
    ),
    "_partner_order_refs.json": (
        "partner_order_refs",
        ("actor_scope", "partner_ref", "status", "order_code", "updated_at"),
    ),
}


def _load_durable_backup_rows():
    snapshots = {}
    with closing(sqlite3.connect(DB_PATH)) as conn:
        for file_name, (table_name, columns) in _DURABLE_BACKUP_TABLES.items():
            query = f"SELECT {', '.join(columns)} FROM {table_name}"
            snapshots[file_name] = [dict(zip(columns, row)) for row in conn.execute(query).fetchall()]
    return snapshots


def create_backup_zip(prefix="backup_lamshop"):
    """Create ZIP directly from SQLite snapshot without mutating live JSON files."""
    zip_filename = None
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = os.path.join(_backup_root_dir(), f"{prefix}_{timestamp}.zip")
        db_rows = _load_backup_rows_from_db()
        written_files = []

        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_name, default_value in get_backup_file_specs():
                payload = default_value
                raw_value = db_rows.get(file_name)

                if raw_value is not None:
                    try:
                        payload = _parse_backup_payload(raw_value)
                    except (TypeError, ValueError, json.JSONDecodeError) as e:
                        logger.error(f"Backup payload lỗi cho {file_name}: {e}")
                else:
                    fallback_path = os.path.join(_backup_root_dir(), file_name)
                    if os.path.exists(fallback_path):
                        try:
                            with open(fallback_path, 'r', encoding='utf-8') as f:
                                payload = json.load(f)
                        except (OSError, ValueError, json.JSONDecodeError) as e:
                            logger.error(f"Không thể đọc fallback backup {file_name}: {e}")

                zipf.writestr(file_name, _serialize_backup_payload(payload, pretty=True) + "\n")
                written_files.append(file_name)

            durable_snapshots = _load_durable_backup_rows()
            for file_name, rows in durable_snapshots.items():
                zipf.writestr(file_name, _serialize_backup_payload(rows, pretty=True) + "\n")

            zipf.writestr(
                "backup_manifest.json",
                _serialize_backup_payload(
                    {
                        "created_at": datetime.now().isoformat(),
                        "db_path": os.path.basename(DB_PATH),
                        "files": written_files,
                        "durable_tables": sorted(durable_snapshots),
                        "format": "sqlite-json-export-v3",
                    },
                    pretty=True,
                ) + "\n",
            )

        return zip_filename if written_files else None
    except (OSError, sqlite3.Error, aiosqlite.Error, TypeError, ValueError, json.JSONDecodeError) as e:
        logger.error(f"❌ Failed to create backup ZIP: {e}")
        if zip_filename and os.path.exists(zip_filename):
            try:
                os.remove(zip_filename)
            except OSError:
                pass
        return None


def restore_backup_zip_to_db(zip_path):
    """Restore a ZIP backup into SQLite after validating filenames and JSON payloads."""
    if not zip_path or not os.path.exists(zip_path):
        raise ValueError("Không tìm thấy file backup để phục hồi.")

    file_specs = get_backup_file_specs()
    allowed_names = {file_name for file_name, _ in file_specs}
    restored_rows = {}

    with zipfile.ZipFile(zip_path, 'r') as zipf:
        for file_info in zipf.infolist():
            raw_name = str(file_info.filename or "").strip()
            if not raw_name or file_info.is_dir():
                continue

            normalized_name = raw_name.replace("\\", "/")
            while normalized_name.startswith("./"):
                normalized_name = normalized_name[2:]
            basename = os.path.basename(normalized_name)

            if normalized_name.startswith("/") or normalized_name != basename or ".." in normalized_name.split("/"):
                raise ValueError(f"Backup chứa đường dẫn không hợp lệ: {raw_name}")

            if basename == "backup_manifest.json":
                continue
            if basename in _DURABLE_BACKUP_TABLES:
                payload = _parse_backup_payload(zipf.read(file_info))
                if not isinstance(payload, list):
                    raise ValueError(f"Backup table payload không hợp lệ: {basename}")
                restored_rows[basename] = payload
                continue
            if basename not in allowed_names:
                logger.info(f"Bỏ qua file ngoài danh sách backup: {basename}")
                continue
            if basename in restored_rows:
                raise ValueError(f"Backup chứa file trùng lặp: {basename}")

            payload = _parse_backup_payload(zipf.read(file_info))
            restored_rows[basename] = _serialize_backup_payload(payload)

    if not restored_rows:
        raise ValueError("Backup ZIP không chứa file dữ liệu hợp lệ.")

    merged_rows = {}
    reset_files = []

    for file_name, default_value in file_specs:
        raw_value = restored_rows.get(file_name)
        if raw_value is None:
            raw_value = _serialize_backup_payload(default_value)
            reset_files.append(file_name)
        merged_rows[file_name] = raw_value

    durable_rows = {
        name: restored_rows.pop(name)
        for name in list(restored_rows)
        if name in _DURABLE_BACKUP_TABLES
    }

    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        for file_name in merged_rows.keys():
            cursor.execute("DELETE FROM kv_store WHERE key = ?", (file_name,))
        cursor.executemany(
            "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)",
            list(merged_rows.items()),
        )
        for file_name, rows in durable_rows.items():
            table_name, columns = _DURABLE_BACKUP_TABLES[file_name]
            cursor.execute(f"DELETE FROM {table_name}")
            placeholders = ", ".join("?" for _ in columns)
            cursor.executemany(
                f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})",
                [tuple(row.get(column) for column in columns) for row in rows],
            )
        cursor.execute("DELETE FROM admin_sessions")
        conn.commit()

    return {
        "restored_files": sorted(restored_rows.keys()),
        "restored_tables": sorted(durable_rows.keys()),
        "reset_files": reset_files,
    }


def send_email_backup(zip_path, recipient_email):
    """Send backup ZIP via email. Returns: (success: bool, error: Optional[str])."""
    if not ENABLE_EMAIL_SENDING:
        return False, "Email sending is disabled"
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        return False, "Missing SMTP credentials: SENDER_EMAIL/SENDER_APP_PASSWORD"
    if not zip_path or not os.path.exists(zip_path):
        return False, f"Backup file not found: {zip_path}"

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = f"SYSTEM BACKUP - {datetime.now().strftime('%d/%m/%Y')}"

        body = f"""
        <html>
        <body>
            <h2><tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> AUTO-BACKUP SYSTEM REPORT</h2>
            <p><b><tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Thời gian:</b> {datetime.now().strftime('%H:%M %d/%m/%Y')}</p>
            <p><b><tg-emoji emoji-id=\"5854908544712707500\">📂</tg-emoji> File:</b> {os.path.basename(zip_path)}</p>
            <p><b><tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Trạng thái:</b> An toàn</p>
            <br>
            <p><i>Đây là tin nhắn tự động từ Lâm Shop. Vui lòng lưu trữ file này cẩn thận.</i></p>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        with open(zip_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {os.path.basename(zip_path)}",
        )
        msg.attach(part)
    except (OSError, ValueError) as e:
        err = f"Prepare backup email payload failed: {e}"
        logger.error(f"❌ {err}")
        return False, err

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    max_attempts = int(os.getenv("SMTP_RETRY_ATTEMPTS", "3"))
    smtp_timeout = float(os.getenv("SMTP_TIMEOUT_SEC", "20"))
    transports = [("starttls", 587), ("ssl", 465)]
    errors = []

    for attempt in range(1, max_attempts + 1):
        for mode, port in transports:
            try:
                if mode == "starttls":
                    with smtplib.SMTP(smtp_host, port, timeout=smtp_timeout) as server:
                        server.ehlo()
                        server.starttls()
                        server.ehlo()
                        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
                        server.send_message(msg)
                else:
                    with smtplib.SMTP_SSL(smtp_host, port, timeout=smtp_timeout) as server:
                        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
                        server.send_message(msg)
                logger.info(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Backup email sent via {mode.upper()}:{port} (attempt {attempt}/{max_attempts})")
                return True, None
            except (ValueError, TypeError, KeyError, IndexError) as e:
                err = f"{mode.upper()}:{port} attempt {attempt}/{max_attempts} -> {e}"
                errors.append(err)
                logger.warning(f"Backup email send failed: {err}")

        if attempt < max_attempts:
            time.sleep(min(2 ** (attempt - 1), 5))

    final_error = " | ".join(errors[-4:]) if errors else "Unknown SMTP error"
    logger.error(f"❌ Failed to send backup email after retries: {final_error}")
    return False, final_error

async def auto_backup_job(context: ContextTypes.DEFAULT_TYPE):
    """Job: Run backup to Telegram (every 6h) and Email (every 3d)"""
    global last_email_backup_time
    
    # 1. Flush data then create ZIP dưới file lock để tránh race với save_data trên Windows
    await save_data(force=True)
    async with file_lock:
        zip_path = await asyncio.get_running_loop().run_in_executor(None, create_backup_zip)
    if not zip_path: return

    now = time.time()
    
    # 2. Send to Telegram (ALWAYS)
    try:
        caption = (
            f'<tg-emoji emoji-id="5197288647275071607">🛡</tg-emoji> <b>AUTO-BACKUP SYSTEM</b>\n\n'
            f'<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> Thời gian: {datetime.now().strftime("%H:%M %d/%m/%Y")}\n'
            f'<tg-emoji emoji-id="5800835941543186089">#⃣</tg-emoji> File: <code>{os.path.basename(zip_path)}</code>\n'
            f'<tg-emoji emoji-id="6269163801178804220">✅</tg-emoji> Trạng thái: An toàn'
        )
        with open(zip_path, 'rb') as backup_file:
            await context.bot.send_document(
                chat_id=ADMIN_USER_ID,
                document=backup_file,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Failed to send backup to Telegram: {e}")
        
    # 3. Check for Email Backup (Every 3 days)
    if now - last_email_backup_time >= BACKUP_INTERVAL_EMAIL:
        sent, email_error = await asyncio.to_thread(send_email_backup, zip_path, ADMIN_EMAIL_BACKUP)
        if sent:
            try:
                await context.bot.send_message(
                    ADMIN_USER_ID,
                    f"<b><tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> EMAIL BACKUP SENT!</b>\n\nĐã gửi backup về mail: <code>{ADMIN_EMAIL_BACKUP}</code>",
                    parse_mode=ParseMode.HTML
                )
                last_email_backup_time = now
            except (TelegramError, ValueError, KeyError, AttributeError) as e:
                logger.warning(f"Failed to notify admin about email backup: {e}")
        else:
            await safe_send_admin(
                context.bot,
                (
                    f"{E_ERROR} <b>EMAIL BACKUP FAILED</b>\n"
                    f"<b>Target:</b> <code>{html.escape(ADMIN_EMAIL_BACKUP)}</code>\n"
                    f"<b>Reason:</b> <code>{html.escape(str(email_error or 'Unknown error'))}</code>"
                ),
            )
            
    # 4. Cleanup
    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)
    except OSError as e:
        logger.debug(f"Cannot cleanup backup zip '{zip_path}': {e}")

