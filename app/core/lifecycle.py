class TelegramLogHandler(logging.Handler):
    """Custom Logging Handler to send error logs to Telegram Admin"""
    def __init__(self, bot, admin_id):
        super().__init__()
        self.bot = bot
        self.admin_id = admin_id

    def emit(self, record):
        # Ignore non-error logs or if connection is not ready
        if record.levelno < logging.ERROR:
            return

        log_entry = self.format(record)

        # Prevent infinite loops if error comes from sending message itself
        if "TelegramLogHandler" in log_entry or "httpx" in log_entry:
            return

        # Ignore getUpdates conflict spam (caused by multiple bot instances)
        conflict_markers = (
            "telegram.error.Conflict",
            "terminated by other getUpdates request",
            "Conflict: terminated by other getUpdates request",
            "can't use getUpdates method while webhook is active",
        )
        if any(marker in log_entry for marker in conflict_markers):
            return

        async def send_log():
            try:
                # Escape html to prevent parse mode errors
                safe_log = html.escape(log_entry)[:4000] # Limit length
                await self.bot.send_message(
                    chat_id=self.admin_id,
                    text=f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>SYSTEM LOG: {record.levelname}</b>\n<pre>{safe_log}</pre>",
                    parse_mode=ParseMode.HTML
                )
            except (httpx.HTTPError, TelegramError, OSError, ValueError, KeyError):
                pass  # Silent fail to avoid infinite loop

        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(send_log(), loop)
        except RuntimeError:
            pass


def _sync_runtime_resources() -> None:
    """Keep late-bound runtime globals in sync across section modules."""
    try:
        from app.core.runtime_loader import sync_runtime_bindings

        sync_runtime_bindings(globals(), ["bot_instance", "http_client"])
    except (ValueError, TypeError, KeyError, AttributeError, ImportError) as sync_error:
        logger.debug(f"Runtime resource sync skipped: {sync_error}")

async def post_init(application: Application):
    """Hook chạy sau khi bot khởi tạo"""
    global bot_instance, http_client

    if http_client and not http_client.is_closed:
        await http_client.aclose()
        http_client = None
        bot_instance = None
        _sync_runtime_resources()
    bot_instance = application.bot

    # FIX: Khởi tạo HTTP client properly
    http_client = httpx.AsyncClient(timeout=15.0)
    _sync_runtime_resources()
    logger.info("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> HTTP client initialized")

    # Bridge globals into centralized AppState for new-style imports
    try:
        from app.state import app_state
        app_state.bridge_from_globals(globals())
        logger.debug("AppState bridge synced from runtime globals")
    except (ImportError, AttributeError, TypeError) as _state_err:
        logger.debug(f"AppState bridge skipped: {_state_err}")

    # Xóa webhook để tránh xung đột với chế độ polling
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Webhook đã được xóa - bot sẵn sàng polling")
    except (httpx.HTTPError, ValueError, KeyError) as _wh_err:
        logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Không thể xóa webhook: {_wh_err}")

    # Initialize Gemini Assistant
    if gemini_assistant.initialize():
        logger.info(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Gemini AI ready: {AI_MODEL}")
    else:
        logger.warning("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Gemini AI not available - using fallback mode")

    if not _normalize_public_api_url(PUBLIC_API_URL):
        await auto_detect_public_api_url()

    if FASTAPI_ENABLED and uvicorn:
        create_background_task(run_api_server(), fatal=True)
        logger.info(f"<tg-emoji emoji-id=\"5231489647946768652\">🌐</tg-emoji> API Server đang chạy tại port {API_SERVER_PORT}")
    else:
        detail = f" | detail: {FASTAPI_IMPORT_ERROR}" if FASTAPI_IMPORT_ERROR else ""
        logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> API server disabled do thiếu/hỏng FastAPI stack.{detail}")

    # Đăng ký Telegram Log Handler
    telegram_handler = TelegramLogHandler(application.bot, ADMIN_USER_ID)
    telegram_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    telegram_handler.setFormatter(formatter)
    telegram_handler.addFilter(SensitiveDataFilter())

    # Add to root logger to catch all errors
    logging.getLogger().addHandler(telegram_handler)

    # Polling mode safety: if webhook is still active, remove it to prevent Conflict.
    try:
        webhook_info = await application.bot.get_webhook_info()
        if webhook_info and getattr(webhook_info, "url", ""):
            logger.warning("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Webhook đang active, tự động xóa để chạy polling ổn định.")
            await application.bot.delete_webhook(drop_pending_updates=True)
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Không thể kiểm tra/xóa webhook trước khi polling: {e}")

    # FIX: Set command menu on startup (Moved from duplicate post_init)
    await application.bot.set_my_commands([
        ("start", "🏠 Menu chính"),
        ("lichsu", "📜 Lịch sử đơn hàng"),
        ("ask", "🤖 Hỏi AI"),
        ("dkyapi", "🧩 Đăng ký API Partner"),
        ("napapi", "💳 Nạp ví chung"),
        ("mystats", "📊 Thống kê cá nhân"),
        ("myref", "🎁 Giới thiệu bạn bè"),
    ])

    # Send startup notification
    try:
        await application.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=(
                f"{E_SUCCESS} <b>HỆ THỐNG ĐÃ KHỞI ĐỘNG VÀ GIÁM SÁT LỖI</b>\n"
                f"<tg-emoji emoji-id=\"5303290914041505430\">⚡️</tg-emoji> <b>Bot đã khởi động lại thành công!</b>"
            ),
            parse_mode=ParseMode.HTML
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"Cannot send startup admin notification: {e}")

async def pre_shutdown(application: Application):
    """Hook cleanup trước khi tắt bot — đảm bảo save data và đóng HTTP client."""
    global bot_instance, http_client

    # 1. Save data trước khi đóng connections
    try:
        try:
            from app.state import app_state
            app_state.export_to_globals(globals())
        except ImportError:
            pass
        await save_data(force=True)
        logger.info("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Final data save completed")
    except OSError as save_err:
        logger.error(f"❌ Final save failed (data may be stale): {save_err}")

    # 2. Đóng HTTP client
    if http_client:
        try:
            await http_client.aclose()
        except OSError:
            pass  # Connection already dead
        http_client = None
        bot_instance = None
        _sync_runtime_resources()
        logger.info("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> HTTP client closed properly")


async def error_handler_callback(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and notify admin/user appropriately."""
    global _last_conflict_report_time

    err = context.error
    if err is None:
        return
    err_text = str(err)
    err_text_lower = err_text.lower()

    # ── 1. Conflict (duplicate polling / webhook active) ──
    if isinstance(err, Conflict):
        now = time.time()
        if (now - _last_conflict_report_time) >= _conflict_report_cooldown:
            _last_conflict_report_time = now
            if "terminated by other getupdates request" in err_text_lower:
                logger.warning("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Conflict: getUpdates bị tranh chấp — có process khác polling cùng token.")
            elif "webhook is active" in err_text_lower:
                logger.warning("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Conflict: token đang ở chế độ webhook.")
            else:
                logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Conflict: {err_text}")
        return

    # ── 2. Forbidden (user chưa mở chat riêng) ──
    if isinstance(err, Forbidden) and "can't initiate conversation" in err_text_lower:
        logger.debug(f"Forbidden: user chưa /start bot — {err_text}")
        return

    # ── 3. BadRequest (harmless callback query noise) ──
    if isinstance(err, BadRequest):
        harmless = ("message is not modified", "query is too old", "response timeout expired",
                    "query id is invalid", "document_invalid", "message to edit not found",
                    "media_caption_too_long", "caption_too_long", "caption is too long")
        if any(h in err_text_lower for h in harmless):
            return

    # ── 4. RetryAfter (flood wait — log and move on) ──
    if isinstance(err, RetryAfter):
        logger.warning(f"<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Flood wait: Telegram yêu cầu chờ {err.retry_after}s")
        return

    # ── 5. TimedOut ──
    if isinstance(err, TimedOut):
        logger.debug(f"<tg-emoji emoji-id=\"5213349767672769194\">⏱</tg-emoji> Request timed out: {err_text}")
        return

    # ── 6. NetworkError (transient) ──
    if isinstance(err, NetworkError):
        if any(h in err_text_lower for h in ("media_caption_too_long", "caption_too_long", "caption is too long")):
            logger.debug(f"Suppressed caption overflow after Telegram fallback: {err_text}")
            return
        if any(h in err_text_lower for h in ("entity_text_invalid", "can't parse entities", "unsupported start tag", "entity begins")):
            logger.debug(f"Suppressed Telegram entity parse noise after fallback: {err_text}")
            return
        logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Network issue: {err_text or type(err).__name__}")
        return

    # ── 7. Unexpected error — log + notify user + alert admin ──
    logger.error("❌ Unexpected error:", exc_info=err)

    # Gửi tin nhắn thân thiện cho user (nếu có update)
    if isinstance(update, Update):
        try:
            chat_id = None
            if update.effective_chat:
                chat_id = update.effective_chat.id
            if chat_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=t("sys_unexpected_error", user_id=getattr(update.effective_user, "id", None)),
                )
        except (TelegramError, ValueError, AttributeError):
            pass  # Không block nếu gửi user thất bại

    # Alert admin (rate-limited: max 1 lần / 60s)
    _err_alert_key = "_last_error_alert_time"
    last_alert = getattr(error_handler_callback, _err_alert_key, 0)
    now = time.time()
    if (now - last_alert) < 60:
        return  # Throttle admin alerts
    setattr(error_handler_callback, _err_alert_key, now)

    tb_list = traceback.format_exception(None, err, err.__traceback__)
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"<tg-emoji emoji-id=\"5447644880824181073\">🚨</tg-emoji> <b>LỖI BẤT THƯỜNG</b>\n\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )
    if len(message) > 4096:
        message = message[:4090] + "</pre>"

    try:
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID, text=message, parse_mode=ParseMode.HTML
        )
    except (TelegramError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to send error report to admin: {e}")


# ==============================================================================
#  ADMIN COMMANDS

