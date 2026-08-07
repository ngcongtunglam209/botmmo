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
                    text=f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>SYSTEM LOG: {record.levelname}</b>\n<pre>{safe_log}</pre>",
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
    """Hook cháº¡y sau khi bot khá»Ÿi táº¡o"""
    global bot_instance, http_client

    if http_client and not http_client.is_closed:
        await http_client.aclose()
        http_client = None
        bot_instance = None
        _sync_runtime_resources()
    bot_instance = application.bot
    
    # FIX: Khá»Ÿi táº¡o HTTP client properly
    http_client = httpx.AsyncClient(timeout=15.0)
    _sync_runtime_resources()
    logger.info("<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> HTTP client initialized")

    # Bridge globals into centralized AppState for new-style imports
    try:
        from app.state import app_state
        app_state.bridge_from_globals(globals())
        logger.debug("AppState bridge synced from runtime globals")
    except (ImportError, AttributeError, TypeError) as _state_err:
        logger.debug(f"AppState bridge skipped: {_state_err}")

    # XÃ³a webhook Ä‘á»ƒ trÃ¡nh xung Ä‘á»™t vá»›i cháº¿ Ä‘á»™ polling
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> Webhook Ä‘Ã£ Ä‘Æ°á»£c xÃ³a - bot sáºµn sÃ ng polling")
    except (httpx.HTTPError, ValueError, KeyError) as _wh_err:
        logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> KhÃ´ng thá»ƒ xÃ³a webhook: {_wh_err}")
    
    # Initialize Gemini Assistant
    if gemini_assistant.initialize():
        logger.info(f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> Gemini AI ready: {AI_MODEL}")
    else:
        logger.warning("<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Gemini AI not available - using fallback mode")

    if not _normalize_public_api_url(PUBLIC_API_URL):
        await auto_detect_public_api_url()

    if FASTAPI_ENABLED and uvicorn:
        create_background_task(run_api_server(), fatal=True)
        logger.info(f"<tg-emoji emoji-id=\"5231489647946768652\">ðŸŒ</tg-emoji> API Server Ä‘ang cháº¡y táº¡i port {API_SERVER_PORT}")
    else:
        detail = f" | detail: {FASTAPI_IMPORT_ERROR}" if FASTAPI_IMPORT_ERROR else ""
        logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> API server disabled do thiáº¿u/há»ng FastAPI stack.{detail}")
    
    # ÄÄƒng kÃ½ Telegram Log Handler
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
            logger.warning("<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Webhook Ä‘ang active, tá»± Ä‘á»™ng xÃ³a Ä‘á»ƒ cháº¡y polling á»•n Ä‘á»‹nh.")
            await application.bot.delete_webhook(drop_pending_updates=True)
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> KhÃ´ng thá»ƒ kiá»ƒm tra/xÃ³a webhook trÆ°á»›c khi polling: {e}")

    # FIX: Set command menu on startup (Moved from duplicate post_init)
    await application.bot.set_my_commands([
        ("start", "ðŸ  Menu chÃ­nh"),
        ("lichsu", "ðŸ“œ Lá»‹ch sá»­ Ä‘Æ¡n hÃ ng"),
        ("ask", "ðŸ¤– Há»i AI"),
        ("dkyapi", "ðŸ§© ÄÄƒng kÃ½ API Partner"),
        ("napapi", "ðŸ’³ Náº¡p vÃ­ chung"),
        ("mystats", "ðŸ“Š Thá»‘ng kÃª cÃ¡ nhÃ¢n"),
        ("myref", "ðŸŽ Giá»›i thiá»‡u báº¡n bÃ¨"),
    ])
    
    # Send startup notification
    try:
        await application.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=(
                f"{E_SUCCESS} <b>Há»† THá»NG ÄÃƒ KHá»žI Äá»˜NG VÃ€ GIÃM SÃT Lá»–I</b>\n"
                f"<tg-emoji emoji-id=\"5303290914041505430\">âš¡ï¸</tg-emoji> <b>Bot Ä‘Ã£ khá»Ÿi Ä‘á»™ng láº¡i thÃ nh cÃ´ng!</b>"
            ),
            parse_mode=ParseMode.HTML
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"Cannot send startup admin notification: {e}")

async def pre_shutdown(application: Application):
    """Hook cleanup trÆ°á»›c khi táº¯t bot â€” Ä‘áº£m báº£o save data vÃ  Ä‘Ã³ng HTTP client."""
    global bot_instance, http_client

    # 1. Save data trÆ°á»›c khi Ä‘Ã³ng connections
    try:
        try:
            from app.state import app_state
            app_state.export_to_globals(globals())
        except ImportError:
            pass
        await save_data(force=True)
        logger.info("<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> Final data save completed")
    except OSError as save_err:
        logger.error(f"âŒ Final save failed (data may be stale): {save_err}")

    # 2. ÄÃ³ng HTTP client
    if http_client:
        try:
            await http_client.aclose()
        except OSError:
            pass  # Connection already dead
        http_client = None
        bot_instance = None
        _sync_runtime_resources()
        logger.info("<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> HTTP client closed properly")


async def error_handler_callback(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and notify admin/user appropriately."""
    global _last_conflict_report_time
    
    err = context.error
    if err is None:
        return
    err_text = str(err)
    err_text_lower = err_text.lower()

    # â”€â”€ 1. Conflict (duplicate polling / webhook active) â”€â”€
    if isinstance(err, Conflict):
        now = time.time()
        if (now - _last_conflict_report_time) >= _conflict_report_cooldown:
            _last_conflict_report_time = now
            if "terminated by other getupdates request" in err_text_lower:
                logger.warning("<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Conflict: getUpdates bá»‹ tranh cháº¥p â€” cÃ³ process khÃ¡c polling cÃ¹ng token.")
            elif "webhook is active" in err_text_lower:
                logger.warning("<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Conflict: token Ä‘ang á»Ÿ cháº¿ Ä‘á»™ webhook.")
            else:
                logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Conflict: {err_text}")
        return

    # â”€â”€ 2. Forbidden (user chÆ°a má»Ÿ chat riÃªng) â”€â”€
    if isinstance(err, Forbidden) and "can't initiate conversation" in err_text_lower:
        logger.debug(f"Forbidden: user chÆ°a /start bot â€” {err_text}")
        return

    # â”€â”€ 3. BadRequest (harmless callback query noise) â”€â”€
    if isinstance(err, BadRequest):
        harmless = ("message is not modified", "query is too old", "response timeout expired",
                    "query id is invalid", "document_invalid", "message to edit not found",
                    "media_caption_too_long", "caption_too_long", "caption is too long")
        if any(h in err_text_lower for h in harmless):
            return

    # â”€â”€ 4. RetryAfter (flood wait â€” log and move on) â”€â”€
    if isinstance(err, RetryAfter):
        logger.warning(f"<tg-emoji emoji-id=\"5213349767672769194\">â³</tg-emoji> Flood wait: Telegram yÃªu cáº§u chá» {err.retry_after}s")
        return

    # â”€â”€ 5. TimedOut â”€â”€
    if isinstance(err, TimedOut):
        logger.debug(f"<tg-emoji emoji-id=\"5213349767672769194\">â±</tg-emoji> Request timed out: {err_text}")
        return

    # â”€â”€ 6. NetworkError (transient) â”€â”€
    if isinstance(err, NetworkError):
        if any(h in err_text_lower for h in ("media_caption_too_long", "caption_too_long", "caption is too long")):
            logger.debug(f"Suppressed caption overflow after Telegram fallback: {err_text}")
            return
        if any(h in err_text_lower for h in ("entity_text_invalid", "can't parse entities", "unsupported start tag", "entity begins")):
            logger.debug(f"Suppressed Telegram entity parse noise after fallback: {err_text}")
            return
        logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Network issue: {err_text or type(err).__name__}")
        return

    # â”€â”€ 7. Unexpected error â€” log + notify user + alert admin â”€â”€
    logger.error("âŒ Unexpected error:", exc_info=err)

    # Gá»­i tin nháº¯n thÃ¢n thiá»‡n cho user (náº¿u cÃ³ update)
    if isinstance(update, Update):
        try:
            chat_id = None
            if update.effective_chat:
                chat_id = update.effective_chat.id
            if chat_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> ÄÃ£ xáº£y ra lá»—i khi xá»­ lÃ½ yÃªu cáº§u. Vui lÃ²ng thá»­ láº¡i sau.",
                )
        except (TelegramError, ValueError, AttributeError):
            pass  # KhÃ´ng block náº¿u gá»­i user tháº¥t báº¡i

    # Alert admin (rate-limited: max 1 láº§n / 60s)
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
        f"<tg-emoji emoji-id=\"5447644880824181073\">ðŸš¨</tg-emoji> <b>Lá»–I Báº¤T THÆ¯á»œNG</b>\n\n"
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
#  SUPPLIER_SOURCE ADMIN COMMANDS (Nháº­p hÃ ng tá»« API bÃªn ngoÃ i)

