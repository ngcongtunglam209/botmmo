# ==============================================================================
#  BOT UPTIME TRACKING
# ==============================================================================
BOT_START_TIME = datetime.now()

# ==============================================================================
#  COMMAND DECORATORS (DRY Patterns)
# ==============================================================================

def admin_only(func):
    """Decorator: chỉ cho phép ADMIN_USER_ID chạy command này."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id != ADMIN_USER_ID:
            logger.warning(f"Unauthorized admin access attempt by user {update.effective_user.id} on {func.__name__}")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def maintenance_guard(func):
    """Decorator: chặn command khi MAINTENANCE_MODE = True (trừ admin)."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if MAINTENANCE_MODE and update.effective_user.id != ADMIN_USER_ID:
            await update.message.reply_text(
                f"{E_ERROR} <b>Bot đang bảo trì</b>\n"
                f"Vui lòng quay lại sau ít phút.",
                parse_mode=ParseMode.HTML
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def rate_limit_command(cooldown: float = 2.0):
    """Decorator: rate limit per-user per-command với cooldown (giây)."""
    _command_timestamps: dict[tuple[int, str], float] = {}
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            # Admin không bị rate limit
            if user_id == ADMIN_USER_ID:
                return await func(update, context, *args, **kwargs)
            key = (user_id, func.__name__)
            now = time.time()
            last = _command_timestamps.get(key, 0)
            if now - last < cooldown:
                remaining = round(cooldown - (now - last), 1)
                await update.message.reply_text(
                    f"<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Vui lòng chờ {remaining}s trước khi dùng lại lệnh này.",
                    parse_mode=ParseMode.HTML
                )
                return
            _command_timestamps[key] = now
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

class LamShopFormatter(logging.Formatter):
    """
    <tg-emoji emoji-id=\"5303145396254563405\">🦕</tg-emoji> Lâm Shop Custom Formatter - Siêu Đẹp & Gọn Gàng
    """
    ANSI_REGEX = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
    HTML_TAG_REGEX = re.compile(r"</?(?:b|i|u|s|code|pre|a|blockquote)\b[^>]*>", re.IGNORECASE)

    # ANSI Colors
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    GREY = "\033[90m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    FORMATS = {
        logging.DEBUG:    f"{GREY}   <tg-emoji emoji-id=\"5215392879320505675\">🛠️</tg-emoji>  DEBUG   {RESET}| %(message)s",
        logging.INFO:     f"{GREEN}   <tg-emoji emoji-id=\"5303145396254563405\">🦖</tg-emoji>  INFO    {RESET}| %(message)s",
        logging.WARNING:  f"{YELLOW}   <tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>  WARN    {RESET}| %(message)s",
        logging.ERROR:    f"{RED}   ❌  ERROR   {RESET}| %(message)s",
        logging.CRITICAL: f"{MAGENTA}   <tg-emoji emoji-id=\"5303290914041505430\">🔥</tg-emoji>  CRITICAL{RESET}| %(message)s",
    }

    PLAIN_LEVELS = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARN",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
    }

    def __init__(self):
        super().__init__()
        self.use_color = bool(getattr(sys.stdout, "isatty", lambda: False)()) and os.name != "nt"

    def _sanitize_console_text(self, value) -> str:
        text = str(value or "")
        text = self.ANSI_REGEX.sub("", text)
        text = strip_tg_emoji(text)
        text = self.HTML_TAG_REGEX.sub("", text)
        return html.unescape(text)

    def format(self, record):
        current_time = self.formatTime(record, "%H:%M:%S")
        message = self._sanitize_console_text(record.getMessage())

        if self.use_color:
            log_fmt = self.FORMATS.get(record.levelno, self.FORMATS[logging.INFO])
            prefix = f"{self.CYAN}[{current_time}]{self.RESET}"
            if "LAM SHOP" in message:
                prefix = f"{self.MAGENTA}[{current_time}]{self.RESET}"
            line = self._sanitize_console_text(f"{prefix} {log_fmt}".replace("%(message)s", message))
        else:
            level = self.PLAIN_LEVELS.get(record.levelno, "INFO")
            line = f"[{current_time}] {level:<8}| {message}"

        if record.exc_info:
            line += "\n" + self._sanitize_console_text(self.formatException(record.exc_info))
        if record.stack_info:
            line += "\n" + self._sanitize_console_text(self.formatStack(record.stack_info))
        return line

# Setup logging
console_handler = logging.StreamHandler()
console_handler.setFormatter(LamShopFormatter())
console_handler.addFilter(SensitiveDataFilter())

# File handler (Giữ nguyên để debug)
file_handler = None
if "unittest" not in sys.modules:
    # Rotation tao them bot.log.1/.2/.3 ben canh, nen duong dan phai nam trong
    # thu muc duoc mount ra host chu khong phai mot file don le.
    _log_path = os.getenv("LOG_FILE", "").strip() or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "bot.log",
    )
    os.makedirs(os.path.dirname(_log_path) or ".", exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        _log_path, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    file_handler.addFilter(SensitiveDataFilter())

# Root logger cleanup
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [] # Clear default handlers
if "unittest" in sys.modules:
    console_handler.setLevel(logging.ERROR)
    root_logger.addHandler(console_handler)
else:
    root_logger.addHandler(console_handler)
    if file_handler is not None:
        root_logger.addHandler(file_handler)

# <tg-emoji emoji-id=\"5447644880824181073\">🔇</tg-emoji> TẮT LOG RÁC (Gọn gàng)
for lib in ["httpx", "apscheduler", "telegram", "uvicorn", "asyncio", "httpcore"]:
    logging.getLogger(lib).setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


def is_premium_telegram_user(user=None, user_info=None) -> bool:
    if user is not None:
        return bool(getattr(user, "is_premium", False))
    if isinstance(user_info, dict):
        return bool(user_info.get("is_premium"))
    return False


def get_vip_badge_html(user=None, user_info=None) -> str:
    if not is_premium_telegram_user(user=user, user_info=user_info):
        return ""
    return f'<tg-emoji emoji-id="{VIP_PREMIUM_ICON_ID}">💎</tg-emoji>'


def format_user_name_html(name=None, *, user=None, user_info=None, fallback="N/A") -> str:
    resolved_name = name
    if resolved_name is None and user is not None:
        resolved_name = getattr(user, "full_name", None)
    if resolved_name is None and isinstance(user_info, dict):
        resolved_name = user_info.get("full_name") or user_info.get("first_name")
    safe_name = html.escape(str(resolved_name or fallback))
    vip_badge = get_vip_badge_html(user=user, user_info=user_info)
    return f"{vip_badge} {safe_name}" if vip_badge else safe_name


def format_user_mention_html(user, fallback="N/A") -> str:
    if not user:
        return html.escape(fallback)
    try:
        mention = user.mention_html()
    except AttributeError:
        mention = html.escape(str(getattr(user, "full_name", fallback) or fallback))
    vip_badge = get_vip_badge_html(user=user)
    return f"{vip_badge} {mention}" if vip_badge else mention


def sync_user_premium_flag(user, profile=None) -> bool:
    if not user:
        return False
    target_profile = profile if profile is not None else user_data_db.setdefault(str(user.id), {})
    premium_flag = bool(getattr(user, "is_premium", False))
    if target_profile.get("is_premium") == premium_flag and "is_premium" in target_profile:
        return False
    target_profile["is_premium"] = premium_flag
    return True

def _should_print_start_banner() -> bool:
    if os.getenv("DINO_SUPPRESS_START_BANNER", "").strip().lower() in {"1", "true", "yes", "on"}:
        return False
    return "unittest" not in sys.modules


# Start Banner
if _should_print_start_banner():
    print("\n" + "="*60)
    if os.name != "nt" and bool(getattr(sys.stdout, "isatty", lambda: False)()):
        print("\033[96m  [LAM SHOP]  L A M   S H O P   B O T   S T A R T I N G . . .  \033[0m")
    else:
        print("  [LAM SHOP]  L A M   S H O P   B O T   S T A R T I N G . . .  ")
    print("="*60 + "\n")


# Biến toàn cục (Sẽ dần thay thế bằng DB)
pending_orders, processed_transaction_ids = {}, set()
pending_user_topups = {}
order_history, user_data_db, banned_users, coupons, api_keys, pending_api_deposits = [], {}, set(), {}, {}, {}
products = {} # Store for other products
pending_api_registrations = set() # Set lưu user_id đang chờ duyệt API
file_lock = asyncio.Lock()
# URL public cho API (ưu tiên ENV; để trống sẽ tự detect IP public nếu được bật)
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "").strip().rstrip("/")
bot_instance = None # Biến global lưu instance bot để dùng trong API

# FIX: Thêm index để tìm kiếm nhanh O(1) thay vì O(n)
order_index = {} # {order_code: order_data} - Fast lookup
user_order_index = {} # {user_id_str: [order_data, ...]} - Fast user lookup
api_partner_ref_index = {} # {ref_key_upper: [order_data, ...]}

# NEW: Tracking sản phẩm hết hàng để tránh spam thông báo
notified_out_of_stock = set() # {product_id} - Track đã thông báo

# NEW: Tracking đơn hàng Gmail chờ Admin xử lý thủ công
pending_manual_orders = {} # {order_code: {user_id, email, product_id, qty, ...}}

# NEW: Queue gom báo cáo lỗi để gửi Batch (1h/lần)
pending_error_reports = [] # [{user_id, username, order_code, ...}]

stock_waitlist = {}
flash_sales = {}
combo_deals = {}
wheel_data = {}
bot_settings = {}  # Cài đặt admin sửa lúc chạy: {"stock_channel_id": int}

# NEW: Locks for concurrency
product_stock_locks = {}  # {product_id: asyncio.Lock()}
api_key_locks = {}  # {api_key: asyncio.Lock()}
api_key_locks_guard = asyncio.Lock()
refund_locks = {}  # {order_code: asyncio.Lock()}
refund_locks_guard = asyncio.Lock()
withdrawal_locks = {}  # {request_id: asyncio.Lock()}
withdrawal_locks_guard = asyncio.Lock()
pending_orders_lock = asyncio.Lock()  # FIX: Lock for pending_orders mutations
reserved_order_codes = set()
global_stock_lock = asyncio.Lock()  # NEW: Global lock for stock/inventory mutations

# Track background tasks
background_tasks = set()

# Single-instance guard (prevent duplicate local polling with same token)
INSTANCE_LOCK_FILE = "bot.instance.lock"
_instance_lock_handle = None

def acquire_single_instance_lock() -> bool:
    """Acquire a non-blocking process lock so only one local bot instance can run."""
    global _instance_lock_handle
    lock_path = os.path.abspath(INSTANCE_LOCK_FILE)
    lock_handle = open(lock_path, "a+", encoding="utf-8")
    try:
        if os.name == "nt":
            import msvcrt
            lock_handle.seek(0)
            lock_handle.write("0")
            lock_handle.flush()
            lock_handle.seek(0)
            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        lock_handle.seek(0)
        lock_handle.truncate()
        lock_handle.write(str(os.getpid()))
        lock_handle.flush()
        _instance_lock_handle = lock_handle
        return True
    except (OSError, ValueError):
        lock_handle.close()
        return False

def release_single_instance_lock() -> None:
    """Release local process lock."""
    global _instance_lock_handle
    if not _instance_lock_handle:
        return
    try:
        if os.name == "nt":
            import msvcrt
            _instance_lock_handle.seek(0)
            msvcrt.locking(_instance_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(_instance_lock_handle.fileno(), fcntl.LOCK_UN)
    except (OSError, ValueError):
        logger.debug("Suppressed error at L812")
    try:
        _instance_lock_handle.close()
    except (OSError, ValueError):
        logger.debug("Suppressed error at L816")
    _instance_lock_handle = None

atexit.register(release_single_instance_lock)
# ======================== ADVANCED FEATURES DATA ========================
# Warranty System
warranty_claims = {}  # {claim_id: {order_code, user_id, product_id, status, timestamp, admin_notes, photos}}

# Rating & Review System
product_ratings = {}  # {product_id: {user_id: {rating, review, timestamp, order_code, verified}}}

# Referral System
referral_data = {}  # {user_id: {referrer_id, referred_users: [], total_commission, commission_history: []}}

# Live Chat System
live_chats = {}  # {user_id: {messages: [{from, text, timestamp}], status, last_activity, unread_by_admin}}

# Giveaway System
active_giveaways = {} # {message_id: {channel_id, prize, end_time, participants: [], ...}}

# Dice Game System
dice_game_data = {} # {user_id: last_play_timestamp}

# Withdrawal System
withdrawal_requests = {} # {request_id: {user_id, amount, status, timestamp, bank_info, admin_notes}}
transaction_history = {} # {user_id: [{amount, new_balance, reason, timestamp}]}
admin_action_log = [] # [{timestamp, actor, action, target, status, message, ip}]
custom_store_icons = {} # {keyword: custom_emoji_id}
store_categories = {} # {category_name: {hidden, sort_order, emoji_id, icon_url}}
# ========================================================================

# ==============================================================================
#  CORE HELPER FUNCTIONS & DATA MANAGEMENT
# ==============================================================================
