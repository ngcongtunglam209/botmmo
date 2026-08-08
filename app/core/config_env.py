# ==============================================================================
#  CẤU HÌNH BOT
# ==============================================================================
import os, sys, time, re, logging, json
from decimal import Decimal, InvalidOperation
from datetime import datetime
def get_env_int(name: str, default: int, minimum: int | None = 1) -> int:
    """minimum=None cho phép giá trị âm — chat_id của group/kênh luôn âm."""
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        parsed_value = int(raw_value)
    except ValueError:
        return default
    if minimum is None:
        return parsed_value
    return max(minimum, parsed_value)

def get_env_float(name: str, default: float, minimum: float = 0.0) -> float:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        parsed_value = float(raw_value)
    except ValueError:
        return default
    return max(minimum, parsed_value)


# ==============================================================================
#  LOAD .ENV FILE — Tất cả secrets phải nằm trong file .env
# ==============================================================================
from dotenv import load_dotenv
import secrets as _secrets
load_dotenv(override=True)  # Load .env từ thư mục hiện tại (override system env)

def _require_env(name: str) -> str:
    """Yêu cầu biến môi trường bắt buộc. Thoát ngay nếu thiếu."""
    value = os.getenv(name, "").strip()
    if not value:
        print(f"\n❌ THIẾU BIẾN MÔI TRƯỜNG BẮT BUỘC: {name}")
        print(f"   Hãy thêm {name}=... vào file .env")
        print("   Xem .env.example để biết cấu hình mẫu.\n")
        sys.exit(1)
    return value

# --- Secrets (BẮT BUỘC — không có default) ---
TELEGRAM_TOKEN = _require_env("TELEGRAM_TOKEN")
API_SECRET_KEY = _require_env("API_SECRET_KEY")
ADMIN_WEB_USERNAME = os.getenv("ADMIN_WEB_USERNAME", "").strip() or "telegram-admin"
# Khoa ky cookie phien admin. Phai co dinh: sinh moi moi lan khoi dong nghia la
# da het admin dang dang nhap ra ngoai sau mot lan restart.
ADMIN_WEB_SESSION_SECRET = os.getenv("ADMIN_WEB_SESSION_SECRET", "").strip()
if not ADMIN_WEB_SESSION_SECRET:
    ADMIN_WEB_SESSION_SECRET = _secrets.token_hex(32)
    os.environ["ADMIN_WEB_SESSION_SECRET"] = ADMIN_WEB_SESSION_SECRET
    print(
        "\n⚠️  ADMIN_WEB_SESSION_SECRET chưa được đặt — đang dùng khóa ngẫu nhiên tạm.\n"
        "   Mọi phiên đăng nhập admin sẽ mất sau mỗi lần restart.\n"
        "   Sinh khóa cố định rồi thêm vào .env:  openssl rand -hex 32\n"
    )
ADMIN_WEB_SESSION_HOURS = get_env_int("ADMIN_WEB_SESSION_HOURS", 8, minimum=1)
TELEGRAM_LOGIN_CLIENT_ID = os.getenv("TELEGRAM_LOGIN_CLIENT_ID", "").strip() or TELEGRAM_TOKEN.split(":", 1)[0]
TELEGRAM_LOGIN_CLIENT_SECRET = os.getenv("TELEGRAM_LOGIN_CLIENT_SECRET", "").strip()
TELEGRAM_LOGIN_REDIRECT_URI = os.getenv("TELEGRAM_LOGIN_REDIRECT_URI", "").strip()
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD", "").strip()

# --- Config (có default an toàn) ---
BANK_ID = os.getenv("BANK_ID", "MB").strip()
BANK_ACCOUNT_NUMBER = os.getenv("BANK_ACCOUNT_NUMBER", "").strip()
ACCOUNT_NAME = os.getenv("ACCOUNT_NAME", "").strip()

# --- SePay: duong thanh toan ngan hang duy nhat (webhook la chinh, poll chi
# la du phong doi soat lai) ---
ENABLE_PAYMENT_SEPAY = os.getenv("ENABLE_PAYMENT_SEPAY", "true").strip().lower() in {"1", "true", "yes", "on"}
SEPAY_WEBHOOK_API_KEY = os.getenv("SEPAY_WEBHOOK_API_KEY", "").strip()
SEPAY_API_TOKEN = os.getenv("SEPAY_API_TOKEN", "").strip()
SEPAY_API_BASE_URL = os.getenv("SEPAY_API_BASE_URL", "https://my.sepay.vn").strip().rstrip("/")
SEPAY_ACCOUNT_NUMBER = os.getenv("SEPAY_ACCOUNT_NUMBER", "").strip() or BANK_ACCOUNT_NUMBER
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "").strip()
SUPPORT_GROUP_LINK = os.getenv("SUPPORT_GROUP_LINK", "").strip()
REQUIRED_GROUP_ID = int(os.getenv("REQUIRED_GROUP_ID", "0") or "0")
ENABLE_EMAIL_SENDING = os.getenv("ENABLE_EMAIL_SENDING", "true").strip().lower() in {"1", "true", "yes", "on"}
REGISTRATION_CHALLENGE_ENABLED = os.getenv("REGISTRATION_CHALLENGE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "").strip()
if ENABLE_EMAIL_SENDING and not SENDER_APP_PASSWORD:
    SENDER_APP_PASSWORD = _require_env("SENDER_APP_PASSWORD")

# --- FIX Phase 2: Chuyển hardcoded values → .env ---
REPORT_INSTRUCTION_IMAGE_URL = os.getenv(
    "REPORT_INSTRUCTION_IMAGE_URL",
    "https://sf-static.upanhlaylink.com/img/image_2026012951ccd173a4a5883794367070516a2463.jpg"
).strip()
LIVE_ORDERS_CHANNEL_ID = get_env_int("LIVE_ORDERS_CHANNEL_ID", -1002191171631, minimum=None)
# Topic (subchannel) trong group forum. 0 = đăng thẳng vào kênh/topic General.
# Đây là message_thread_id, KHÔNG phải chat_id: nó chỉ có nghĩa khi đi kèm
# CHANNEL_ID của group. Lấy từ link topic: t.me/c/<group>/<topic>.
LIVE_ORDERS_TOPIC_ID = get_env_int("LIVE_ORDERS_TOPIC_ID", 0, minimum=0)
# Kênh nhận thông báo nhập kho. Đây chỉ là mặc định; /setstockchannel ghi đè lúc chạy.
STOCK_CHANNEL_ID = get_env_int("STOCK_CHANNEL_ID", 0, minimum=None)
STOCK_CHANNEL_TOPIC_ID = get_env_int("STOCK_CHANNEL_TOPIC_ID", 0, minimum=0)
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip()

MAINTENANCE_MODE = False
AI_AUTO_REPLY = False
API_SERVER_PORT = int(os.getenv("API_SERVER_PORT", "8080"))
PUBLIC_API_SCHEME = os.getenv("PUBLIC_API_SCHEME", "https").strip().lower()
# Which client IPs may set X-Forwarded-Proto/-For. Caddy reaches the bot over the
# internal Docker network, so its address is not 127.0.0.1 and uvicorn would
# otherwise drop those headers and report every HTTPS request as plain http.
TRUSTED_PROXY_IPS = os.getenv("TRUSTED_PROXY_IPS", "*").strip() or "*"
AUTO_PUBLIC_IP_DETECT = os.getenv("AUTO_PUBLIC_IP_DETECT", "true").strip().lower() in {"1", "true", "yes", "on"}
# --- RPay: cong thanh toan USDT duy nhat (callback la chinh, poll
# GetInvoiceStatus chi la du phong doi soat lai) ---
ENABLE_PAYMENT_RPAY = os.getenv("ENABLE_PAYMENT_RPAY", "true").strip().lower() in {"1", "true", "yes", "on"}
RPAY_MERCHANT_ID = os.getenv("RPAY_MERCHANT_ID", "").strip()
RPAY_API_KEY = os.getenv("RPAY_API_KEY", "").strip()
RPAY_API_BASE_URL = os.getenv("RPAY_API_BASE_URL", "https://api.rpay.vn/api").strip().rstrip("/")
# Token/network/address deu tuy chon: de trong thi RPay dung vi mac dinh cua
# cua hang. Chi bat buoc `address` khi 1 network/token co nhieu vi active.
RPAY_TOKEN = os.getenv("RPAY_TOKEN", "USDT").strip().upper()
RPAY_NETWORK = os.getenv("RPAY_NETWORK", "").strip().lower()
RPAY_WALLET_ADDRESS = os.getenv("RPAY_WALLET_ADDRESS", "").strip()
# De trong -> bam theo PUBLIC_API_URL + /webhook/rpay (xem rpay_callback_url()).
RPAY_CALLBACK_URL = os.getenv("RPAY_CALLBACK_URL", "").strip()
RPAY_TIMEOUT_SECONDS = get_env_float("RPAY_TIMEOUT_SECONDS", 15.0, minimum=3.0)
# Tra thieu bao nhieu USDT thi van chap nhan (phi mang lam hut vai cent).
RPAY_UNDERPAY_TOLERANCE_RAW = os.getenv("RPAY_UNDERPAY_TOLERANCE", "0.01").strip()
# So le USDT hien cho khach va gui len RPay. 2 la du cho moi network.
USDT_DISPLAY_DECIMALS = get_env_int("USDT_DISPLAY_DECIMALS", 2, minimum=1)

# --- Binance Pay: khach chuyen thang vao Binance ID cua shop, doi soat bang
# feed lich su sieuthicode.com (poll, khong co callback) ---
ENABLE_PAYMENT_BINANCE_PAY = os.getenv("ENABLE_PAYMENT_BINANCE_PAY", "false").strip().lower() in {"1", "true", "yes", "on"}
# Binance ID (Pay ID) khach se chuyen toi. Hien trong hoa don va QR.
BINANCE_PAY_ID = os.getenv("BINANCE_PAY_ID", "").strip()
# URL feed lich su day du, ke ca token. Vi du:
#   https://sieuthicode.com/historyapibinancev3/<TOKEN>
# Token nam trong path nen no se lot vao log truy cap cua moi proxy tren duong
# di - coi nhu bi mat yeu, va vi vay no khong bao gio duoc phep quyet dinh so
# tien cong cho khach (xem _scan_binance_pay_payments).
BINANCE_PAY_HISTORY_URL = os.getenv("BINANCE_PAY_HISTORY_URL", "").strip()
BINANCE_PAY_TIMEOUT_SECONDS = get_env_float("BINANCE_PAY_TIMEOUT_SECONDS", 10.0, minimum=3.0)
# Feed KHONG tra ve noi dung chuyen khoan (`description` gan nhu luon rong), nen
# khong the khop don theo ma ICLD. Cach khop duy nhat con lai la so tien chinh
# xac + cua so thoi gian. Vi vay moi don duoc gan mot so le rieng o chu so thu
# BINANCE_PAY_AMOUNT_DECIMALS de khong hai don nao trung so tien.
BINANCE_PAY_AMOUNT_DECIMALS = get_env_int("BINANCE_PAY_AMOUNT_DECIMALS", 4, minimum=3)
# Giao dich duoc coi la cua don neu roi trong [tao don - LEEWAY, het han + LEEWAY].
BINANCE_PAY_MATCH_LEEWAY_SECONDS = get_env_int("BINANCE_PAY_MATCH_LEEWAY_SECONDS", 120, minimum=30)
# Ty gia du phong khi khong lay duoc gia P2P live (0 = bat buoc phai co live).
USDT_RATE_VND_PER_USDT_RAW = os.getenv("USDT_RATE_VND_PER_USDT", "0").strip()
# Nguon gia USDT/VND tham khao. San pham niem yet VND con RPay thu USDT nen
# van phai quy doi; day chi la bang gia cong khai, khong phai cong thanh toan.
USDT_RATE_SOURCE_URL = os.getenv(
    "USDT_RATE_SOURCE_URL",
    "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search",
).strip()
BANK_BUTTON_ICON_ID = os.getenv("BANK_BUTTON_ICON_ID", "6201627300170043826").strip()
CRYPTO_BUTTON_ICON_ID = os.getenv("CRYPTO_BUTTON_ICON_ID", "5280763862113592324").strip()
VIP_PREMIUM_ICON_ID = os.getenv("VIP_PREMIUM_ICON_ID", "5240228673738527951").strip()

# Advanced Features Configuration
REFERRAL_COMMISSION_PERCENT = 10
WARRANTY_REMINDER_DAYS = 3
RATING_PROMPT_DELAY_HOURS = 24
MAX_REVIEWS_DISPLAY = 10
# AUTO-BACKUP CONFIGURATION
ADMIN_EMAIL_BACKUP = os.getenv("ADMIN_EMAIL_BACKUP", "dinikhang@gmail.com").strip()
BACKUP_INTERVAL_TELEGRAM = 21600 # 6 hours (6 * 3600)
BACKUP_INTERVAL_EMAIL = 259200 # 3 days (3 * 24 * 3600)
last_email_backup_time = time.time() # Track last email backup timestamp
VIP_MONTHLY_MAINTENANCE_MIN_SPEND = 200000
VIP_RANKS = [
    {"name": "⭐️ Đồng", "min_spend": 0, "discount": 0},
    {"name": "⭐️ Bạc", "min_spend": 500000, "discount": 0},
    {"name": "⭐️ Vàng", "min_spend": 1000000, "discount": 0},
    {"name": '<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> Kim Cương', "min_spend": 5000000, "discount": 0},
    {"name": '⭐️ Cao Thủ', "min_spend": 10000000, "discount": 0},
]
WHEEL_PRIZES = [
    {"name": "5,000đ", "type": "balance", "value": 5000, "weight": 30, "emoji": '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji>'},
    {"name": "Giảm 10%", "type": "coupon", "value": 10, "weight": 40, "emoji": '<tg-emoji emoji-id="5377624166436445368">🎟</tg-emoji>'},
    {"name": "Chúc may mắn lần sau!", "type": "nothing", "value": 0, "weight": 850, "emoji": '<tg-emoji emoji-id="5386856460632201117">😢</tg-emoji>'},
    {"name": "2,000đ", "type": "balance", "value": 2000, "weight": 35, "emoji": '<tg-emoji emoji-id="5379773896352355687">🪙</tg-emoji>'},
    {"name": "Giảm 20%", "type": "coupon", "value": 20, "weight": 20, "emoji": '<tg-emoji emoji-id="5377624166436445368">🎟</tg-emoji>'},
    {"name": "20,000đ", "type": "balance", "value": 20000, "weight": 10, "emoji": '<tg-emoji emoji-id="5215239948420003628">💵</tg-emoji>'},
    {"name": "Giảm 50%", "type": "coupon", "value": 50, "weight": 10, "emoji": '<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji>'},
    {"name": "50,000đ", "type": "balance", "value": 50000, "weight": 5, "emoji": '<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji>'},
]
DAILY_PROMO_BUDGET_PERCENT = 15
DAILY_PROMO_MIN_BUDGET = 20000
daily_promo_tracker = {}

try:
    USDT_RATE_VND_PER_USDT = Decimal(USDT_RATE_VND_PER_USDT_RAW or "0")
except InvalidOperation:
    USDT_RATE_VND_PER_USDT = Decimal("0")

try:
    RPAY_UNDERPAY_TOLERANCE = Decimal(RPAY_UNDERPAY_TOLERANCE_RAW or "0")
except InvalidOperation:
    RPAY_UNDERPAY_TOLERANCE = Decimal("0.01")
if RPAY_UNDERPAY_TOLERANCE < 0:
    RPAY_UNDERPAY_TOLERANCE = Decimal("0")

def _get_today_key():
    return datetime.now().strftime('%Y-%m-%d')

def get_today_revenue():
    """Calculate today's completed order revenue"""
    today = datetime.now().date()
    revenue = 0
    for o in order_history:
        if 'Hoàn thành' in status_text(o.get('status', '')):
            if 'timestamp' in o:
                try:
                    if datetime.fromtimestamp(o['timestamp']).date() == today:
                        revenue += o.get('amount', 0)
                except (ValueError, TypeError, OSError):
                    pass
    return revenue

def get_daily_promo_budget():
    """Get today's promo budget = max(MIN_BUDGET, PERCENT% of today revenue)"""
    revenue = get_today_revenue()
    calculated = int(revenue * DAILY_PROMO_BUDGET_PERCENT / 100)
    return max(DAILY_PROMO_MIN_BUDGET, calculated)

def get_daily_promo_spent():
    """Get total promo cost spent today"""
    today = _get_today_key()
    tracker = daily_promo_tracker.get(today, {})
    return tracker.get('total', 0)

def record_promo_cost(amount: int, promo_type: str = "other"):
    """Record a promo cost for today"""
    today = _get_today_key()
    if today not in daily_promo_tracker:
        old_keys = [k for k in daily_promo_tracker if k != today]
        for k in old_keys:
            daily_promo_tracker.pop(k, None)
        daily_promo_tracker[today] = {'total': 0, 'details': []}
    daily_promo_tracker[today]['total'] += amount
    daily_promo_tracker[today]['details'].append({
        'amount': amount, 'type': promo_type, 'time': time.time()
    })
    if len(daily_promo_tracker[today]['details']) > 200:
        daily_promo_tracker[today]['details'] = daily_promo_tracker[today]['details'][-100:]

def can_spend_promo(amount: int) -> bool:
    """Check if we can afford this promo cost within today's budget"""
    budget = get_daily_promo_budget()
    spent = get_daily_promo_spent()
    return (spent + amount) <= budget

def get_promo_budget_status():
    """Get budget status string for admin"""
    budget = get_daily_promo_budget()
    spent = get_daily_promo_spent()
    revenue = get_today_revenue()
    remaining = max(0, budget - spent)
    return {
        'revenue': revenue,
        'budget': budget,
        'spent': spent,
        'remaining': remaining,
        'percent_used': int(spent / budget * 100) if budget > 0 else 0
    }

_bank_api_fail_count = 0
_bank_api_last_alert_time = 0
_bank_api_last_check_time = 0.0
_bank_api_last_status = "unknown"
_bank_api_last_error = ""
_bank_api_last_tx_count = 0
_bank_api_total_checks = 0
_bank_api_total_success = 0

## =============================
#  CẤU HÌNH AI (GROQ API)
## =============================
AI_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
AI_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.9"))

def _iter_log_secrets():
    candidates = (
        TELEGRAM_TOKEN,
        API_SECRET_KEY,
        SEPAY_WEBHOOK_API_KEY,
        SEPAY_API_TOKEN,
        RPAY_API_KEY,
        BINANCE_PAY_HISTORY_URL,
        ADMIN_WEB_SESSION_SECRET,
        AI_API_KEY,
        SENDER_APP_PASSWORD,
        BANK_ACCOUNT_NUMBER,
    )
    seen = set()
    for value in candidates:
        secret = str(value or "").strip()
        if len(secret) < 6 or secret in seen:
            continue
        seen.add(secret)
        yield secret

def _redact_sensitive_text(value) -> str:
    text = str(value or "")
    for secret in _iter_log_secrets():
        if secret in text:
            text = text.replace(secret, "[REDACTED]")
    return text

class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        try:
            if isinstance(record.msg, str):
                record.msg = _redact_sensitive_text(record.msg)
            if isinstance(record.args, dict):
                record.args = {
                    key: _redact_sensitive_text(val) if isinstance(val, str) else val
                    for key, val in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    _redact_sensitive_text(val) if isinstance(val, str) else val
                    for val in record.args
                )
        except (ValueError, TypeError, KeyError, AttributeError):
            pass
        return True

# =============================
#  CÁC THIẾT LẬP HỆ THỐNG
# =============================
HISTORY_FILE, PROCESSED_TX_FILE = "data_order_history.json", "data_processed_ids.json"
USERS_FILE, BANNED_USERS_FILE, COUPONS_FILE, API_KEYS_FILE = "data_users.json", "data_banned_users.json", "data_coupons.json", "data_api_keys.json"
PRODUCTS_FILE = "data_products.json"
CUSTOM_STORE_ICONS_FILE = "data_custom_store_icons.json"
STORE_CATEGORIES_FILE = "data_store_categories.json"
PENDING_ORDERS_FILE = "data_pending_orders.json"
PENDING_MANUAL_ORDERS_FILE = "data_pending_manual_orders.json"  # NEW

# Advanced Features Data Files
WARRANTY_CLAIMS_FILE = "data_warranty_claims.json"
PRODUCT_RATINGS_FILE = "data_product_ratings.json"
REFERRAL_DATA_FILE = "data_referral_data.json"
LIVE_CHATS_FILE = "data_live_chats.json"
DICE_GAME_FILE = "data_dice_game.json"  # NEW: Dice Game tracking
PROMO_BUDGET_FILE = 'data_promo_budget.json'
WITHDRAWALS_FILE = "data_withdrawals.json"
USER_TOPUP_FILE = "data_pending_user_topups.json"  # NEW: Pending wallet top-ups
STOCK_WAITLIST_FILE = "data_stock_waitlist.json"
FLASH_SALES_FILE = "data_flash_sales.json"
COMBO_DEALS_FILE = "data_combo_deals.json"
WHEEL_DATA_FILE = "data_wheel_data.json"
BOT_SETTINGS_FILE = "data_bot_settings.json"  # Cài đặt admin đổi lúc chạy, giữ qua restart

# Withdrawal Configuration
TRANSACTION_HISTORY_FILE = "data_transaction_history.json"  # NEW: Balance history
ADMIN_ACTION_LOG_FILE = "data_admin_action_log.json"
MIN_WITHDRAWAL_AMOUNT = 200000  # Minimum 200,000 VNĐ

# Nap tien vao vi (tien nap chi de mua hang, khong rut ra duoc)
MIN_USER_TOPUP_AMOUNT = get_env_int("MIN_USER_TOPUP_AMOUNT", 10000, minimum=1000)
MAX_USER_TOPUP_AMOUNT = get_env_int("MAX_USER_TOPUP_AMOUNT", 20000000, minimum=10000)
USER_TOPUP_EXPIRATION_SECONDS = get_env_int("USER_TOPUP_EXPIRATION_SECONDS", 900, minimum=300)

# Hủy đơn sau 10 phút không thanh toán | Cron duyệt đơn quét bank mặc định mỗi 15 giây
ORDER_EXPIRATION_SECONDS = 600
BANK_CHECK_INTERVAL_SECONDS = get_env_int("BANK_CHECK_INTERVAL_SECONDS", 15, minimum=5)
BANK_API_TIMEOUT_SECONDS = get_env_float("BANK_API_TIMEOUT_SECONDS", 6.0, minimum=2.0)
SEPAY_POLL_LOOKBACK_MINUTES = get_env_int("SEPAY_POLL_LOOKBACK_MINUTES", 180, minimum=15)
BANK_REFUND_MIN_AMOUNT = get_env_int("BANK_REFUND_MIN_AMOUNT", 200000, minimum=200000)

# Tối ưu: Compile regex trước để tăng tốc
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
ORDER_CODE_REGEX = re.compile(r'^ICLD\d{6}$')
MANUAL_EMAIL_ORDER_CODE_REGEX = re.compile(r'^(?:ICLD\d{6}|MANUAL[A-Z0-9]{6,})$')
USER_ORDER_CODE_REGEX = re.compile(r'^(?:ICLD\d{6}|MANUAL[A-Z0-9]{6,}|PROD[A-Z0-9]{6,})$')
ORDER_CODE_SEARCH_REGEX = re.compile(r'ICLD\d{6}')
ICLD_PATTERN = re.compile(r'ICLD\s*(\d{6})', re.IGNORECASE)
NAPI_PATTERN = re.compile(r'(NAPI\d+)', re.IGNORECASE)
NAPU_PATTERN = re.compile(r'(NAPU\d+)', re.IGNORECASE)

# ===============================================

# ===============================================

# Welcome video shown above menu on /start
WELCOME_VIDEO_URL = os.getenv(
    "WELCOME_VIDEO_URL",
    "https://raw.githubusercontent.com/lequockhang978/action-ipadown/master/gemini_generated_video_f54777a3.mp4",
).strip()
WELCOME_VIDEO_ENABLED = os.getenv("WELCOME_VIDEO_ENABLED", "1").strip().lower() in ("1", "true", "yes", "on")
WELCOME_VIDEO_FILE_ID = os.getenv("WELCOME_VIDEO_FILE_ID", "").strip() or None
WELCOME_VIDEO_SEND_TIMEOUT = float(os.getenv("WELCOME_VIDEO_SEND_TIMEOUT", "8.0"))

# Rate Limiting Configuration
RATE_LIMIT_DELAY = 1.0 # Seconds between actions
user_last_action = {}

async def check_rate_limit(user_id: int) -> bool:
    """True if allowed, False if too fast"""
    now = time.time()
    last_time = user_last_action.get(user_id, 0)
    if now - last_time < RATE_LIMIT_DELAY:
        return False
    user_last_action[user_id] = now
    return True

