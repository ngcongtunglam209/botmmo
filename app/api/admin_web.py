from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import string
import time
from html import escape, unescape
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode

from fastapi.responses import FileResponse, RedirectResponse

from .admin_web_utils import (
    _admin_web_active_count,
    _admin_web_bool_text,
    _admin_web_format_timestamp,
    _admin_web_int,
    _admin_web_json_block,
    _admin_web_mapping_get,
    _admin_web_money,
    _admin_web_order_code,
    _admin_web_order_time,
    _admin_web_plain_display,
    _admin_web_product_type,
    _admin_web_row_search,
    _admin_web_short,
    _admin_web_strip_telegram_emoji_markup,
    _admin_web_text,
)

try:
    from app.state import app_state
    app_state.bridge_from_globals(globals())
except ImportError:
    pass


ADMIN_WEB_AUDIT_LIMIT = 500
ADMIN_WEB_PRODUCT_TABLE_LIMIT = 3000
ADMIN_WEB_ORDER_TABLE_LIMIT = 260
ADMIN_WEB_USER_TABLE_LIMIT = 260
ADMIN_WEB_API_TABLE_LIMIT = 260
ADMIN_WEB_SUSPICIOUS_BALANCE_THRESHOLD = 1_000_000_000_000
ADMIN_WEB_LOGIN_NOTIFY_COOLDOWN_SECONDS = 6 * 60 * 60
ADMIN_WEB_LOGIN_NOTIFY_CACHE_MAX = 256
ADMIN_WEB_SESSION_COOKIE = "dino_admin_session"
ADMIN_WEB_LOGIN_WINDOW_SECONDS = 5 * 60
ADMIN_WEB_LOGIN_MAX_ATTEMPTS = 5
ADMIN_WEB_TELEGRAM_OIDC_COOKIE = "dino_admin_telegram_oidc"
ADMIN_WEB_TELEGRAM_OIDC_TTL_SECONDS = 10 * 60
ADMIN_WEB_TELEGRAM_AUTH_URL = "https://oauth.telegram.org/auth"
ADMIN_WEB_TELEGRAM_TOKEN_URL = "https://oauth.telegram.org/token"
ADMIN_WEB_TELEGRAM_JWKS_URL = "https://oauth.telegram.org/.well-known/jwks.json"
ADMIN_WEB_ASSET_DIR = Path(__file__).resolve().parent / "assets"
ADMIN_WEB_BANNER_PATH = ADMIN_WEB_ASSET_DIR / "admin-banner.png"
ADMIN_WEB_PRODUCT_IMAGE_DIR = Path(__file__).resolve().parent / "static" / "products"
ADMIN_WEB_PRODUCT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
ADMIN_WEB_CATEGORY_IMAGE_DIR = Path(__file__).resolve().parent / "static" / "categories"
ADMIN_WEB_CATEGORY_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
ADMIN_WEB_PRODUCT_IMAGE_EXTS = {"jpg", "jpeg", "png", "webp"}
ADMIN_WEB_PRODUCT_IMAGE_MAX_BYTES = 8 * 1024 * 1024


def _admin_web_category_slug(name: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s or "uncategorized"


def _admin_web_product_image_path(product_id: str):
    pid = str(product_id or "").strip()
    if not pid:
        return None
    for ext in ADMIN_WEB_PRODUCT_IMAGE_EXTS:
        p = ADMIN_WEB_PRODUCT_IMAGE_DIR / f"{pid}.{ext}"
        if p.is_file():
            return p
    return None


def _admin_web_category_image_path(category_name: str):
    slug = _admin_web_category_slug(category_name)
    if not slug:
        return None
    for ext in ADMIN_WEB_PRODUCT_IMAGE_EXTS:
        p = ADMIN_WEB_CATEGORY_IMAGE_DIR / f"{slug}.{ext}"
        if p.is_file():
            return p
    return None


def _admin_web_product_image_url(request, product_id: str) -> str:
    return _admin_web_page_url(
        request,
        "/admin/product_image",
        {"id": str(product_id), "t": str(int(time.time()))},
    )


def _admin_web_category_image_url(request, category_name: str) -> str:
    return _admin_web_page_url(
        request,
        "/admin/category_image",
        {"name": str(category_name), "t": str(int(time.time()))},
    )


def _admin_web_product_category(product) -> str:
    if not isinstance(product, dict):
        return ""
    cat = str(product.get("store_category") or "").strip()
    if cat:
        return cat
    name = str(product.get("name") or "")
    try:
        get_cat = globals().get("get_product_category")
        if callable(get_cat):
            return str(get_cat(name) or "")
    except Exception:
        pass
    return ""

def _admin_web_category_config(category_name: str) -> dict:
    config = store_categories.get(str(category_name or "").strip(), {}) if isinstance(store_categories, dict) else {}
    return config if isinstance(config, dict) else {}


_admin_web_login_notify_cache = {}

ADMIN_WEB_EXPERIENCE_CSS = (Path(__file__).parent / "static" / "experience.css").read_text(encoding="utf-8")

ADMIN_WEB_I18N_SCRIPT = (Path(__file__).parent / "static" / "i18n.js").read_text(encoding="utf-8")

ADMIN_WEB_THREE_SCRIPT = (Path(__file__).parent / "static" / "three.js").read_text(encoding="utf-8")

ADMIN_WEB_PRO_CSS = (Path(__file__).parent / "static" / "pro.css").read_text(encoding="utf-8")

ADMIN_WEB_MMO_CSS = (Path(__file__).parent / "static" / "mmo.css").read_text(encoding="utf-8")

ADMIN_WEB_DARK_CSS = (Path(__file__).parent / "static" / "dark.css").read_text(encoding="utf-8")

ADMIN_WEB_MOTION_CSS = (Path(__file__).parent / "static" / "motion.css").read_text(encoding="utf-8")

ADMIN_WEB_MOTION_SCRIPT = (Path(__file__).parent / "static" / "motion.js").read_text(encoding="utf-8")

ADMIN_WEB_REDESIGN_CSS = (Path(__file__).parent / "static" / "admin_redesign.css").read_text(encoding="utf-8")

ADMIN_WEB_VIP_CSS = (Path(__file__).parent / "static" / "vip_admin.css").read_text(encoding="utf-8")

ADMIN_WEB_OPS_CSS = (Path(__file__).parent / "static" / "admin_ops_2026.css").read_text(encoding="utf-8")

ADMIN_WEB_COMMAND_GROUPS = [
    {
        "group": "Tá»•ng quan há»‡ thá»‘ng",
        "commands": [
            ("admin", "/admin", "Má»Ÿ báº£ng Ä‘iá»u khiá»ƒn admin trÃªn Telegram.", "readonly"),
            ("helpadmin", "/helpadmin", "Alias cá»§a /admin.", "readonly"),
            ("uptime", "/uptime", "Xem uptime, thÃ´ng tin há»‡ thá»‘ng.", "readonly"),
            ("status", "/status", "Alias cá»§a /uptime.", "readonly"),
            ("backup", "/backup", "Táº¡o vÃ  gá»­i backup dá»¯ liá»‡u.", "danger"),
            ("nhapdata", "/nhapdata", "Restore dá»¯ liá»‡u tá»« file backup zip.", "danger"),
            ("testing", "/testing", "Lá»‡nh test ná»™i bá»™.", "danger"),
        ],
    },
    {
        "group": "Kho link legacy",
        "commands": [
            ("kho", "/kho", "Xem kho link legacy.", "readonly"),
            ("addlink", "/addlink <link>", "ThÃªm link vÃ o kho legacy.", "write"),
            ("dellink", "/dellink <link>", "XÃ³a link kho legacy.", "write"),
            ("guilink", "/guilink <user_id> <link>", "Gá»­i link thá»§ cÃ´ng cho user.", "danger"),
        ],
    },
    {
        "group": "Sáº£n pháº©m vÃ  tá»“n kho",
        "commands": [
            ("products", "/products", "Danh sÃ¡ch sáº£n pháº©m store.", "readonly"),
            ("newproduct", "/newproduct", "Conversation táº¡o sáº£n pháº©m má»›i.", "conversation"),
            ("editproduct", "/editproduct", "Conversation sá»­a sáº£n pháº©m.", "conversation"),
            ("delproduct", "/delproduct <product_id>", "XÃ³a sáº£n pháº©m.", "danger"),
            ("addstock", "/addstock", "Conversation thÃªm stock local.", "conversation"),
            ("viewstock", "/viewstock", "Xem stock local.", "readonly"),
            ("delstock", "/delstock", "Conversation xÃ³a stock local.", "conversation"),
            ("setlimit", "/setlimit <product_id> <so_luong>", "Äáº·t giá»›i háº¡n pending/manual.", "write"),
        ],
    },
    {
        "group": "ÄÆ¡n hÃ ng vÃ  thanh toÃ¡n",
        "commands": [
            ("duyet", "/duyet <ma_don>", "Duyá»‡t Ä‘Æ¡n thá»§ cÃ´ng/manual.", "write"),
            ("pending", "/pending", "Xem Ä‘Æ¡n manual Ä‘ang chá».", "readonly"),
            ("clearpending", "/clearpending", "XÃ³a pending manual.", "danger"),
            ("refund", "/refund <ma_don>", "HoÃ n tiá»n Ä‘Æ¡n hÃ ng user/API partner.", "danger"),
            ("find", "/find <ma_don|user_id>", "TÃ¬m Ä‘Æ¡n hÃ ng.", "readonly"),
            ("doanhthu", "/doanhthu", "Thá»‘ng kÃª doanh thu.", "readonly"),
            ("setemail", "/setemail <ma_don> <email>", "Gáº¯n email nháº­n hÃ ng cho Ä‘Æ¡n.", "write"),
            ("transactions", "/transactions", "Xem lá»‹ch sá»­ giao dá»‹ch vÃ­.", "readonly"),
            ("lichsugiaodich", "/lichsugiaodich", "Alias cá»§a /transactions.", "readonly"),
        ],
    },
    {
        "group": "User vÃ  vÃ­",
        "commands": [
            ("users", "/users", "Danh sÃ¡ch user.", "readonly"),
            ("info", "/info <user_id>", "Xem thÃ´ng tin user.", "readonly"),
            ("ban", "/ban <user_id>", "Cáº¥m user.", "danger"),
            ("unban", "/unban <user_id>", "Gá»¡ cáº¥m user.", "write"),
            ("bc", "/bc <noi_dung>", "Broadcast tin nháº¯n.", "danger"),
            ("addmoney", "/addmoney <user_id> <so_tien>", "Cá»™ng tiá»n vÃ o vÃ­ user/API.", "danger"),
            ("submoney", "/submoney <user_id> <so_tien>", "Trá»« tiá»n vÃ­ user/API.", "danger"),
            ("pending_withdrawals", "/pending_withdrawals", "Xem yÃªu cáº§u rÃºt tiá»n.", "readonly"),
        ],
    },
    {
        "group": "Coupon, khuyáº¿n mÃ£i, game",
        "commands": [
            ("sale", "/sale <noi_dung>", "Gá»­i thÃ´ng bÃ¡o sale.", "danger"),
            ("addcoupon", "/addcoupon ...", "ThÃªm coupon.", "write"),
            ("delcoupon", "/delcoupon <code>", "XÃ³a coupon.", "write"),
            ("listcoupons", "/listcoupons", "Danh sÃ¡ch coupon.", "readonly"),
            ("rewardtop", "/rewardtop", "ThÆ°á»Ÿng top buyer/referral.", "danger"),
            ("promobudget", "/promobudget", "Xem ngÃ¢n sÃ¡ch khuyáº¿n mÃ£i.", "readonly"),
            ("ngansachkm", "/ngansachkm", "Alias cá»§a /promobudget.", "readonly"),
            ("flashsale", "/flashsale ...", "Quáº£n lÃ½ flash sale.", "write"),
            ("combo", "/combo ...", "Quáº£n lÃ½ combo deal.", "write"),
            ("create_ga", "/create_ga", "Conversation táº¡o giveaway.", "conversation"),
            ("list_ga", "/list_ga", "Danh sÃ¡ch giveaway.", "readonly"),
            ("listga", "/listga", "Alias cá»§a /list_ga.", "readonly"),
            ("endga", "/endga <ga_id>", "Káº¿t thÃºc giveaway.", "write"),
            ("end_ga", "/end_ga <ga_id>", "Alias cá»§a /endga.", "write"),
        ],
    },
    {
        "group": "API partner",
        "commands": [
            ("api", "/api", "Danh sÃ¡ch API key partner.", "readonly"),
            ("addapi", "/addapi <ten> <so_du>", "Táº¡o API key partner.", "danger"),
            ("delapi", "/delapi <key>", "XÃ³a/vÃ´ hiá»‡u API key.", "danger"),
            ("napi", "/napi ...", "Náº¡p vÃ­ API partner.", "write"),
            ("helpapi", "/helpapi", "HÆ°á»›ng dáº«n API.", "readonly"),
            ("dkyapi", "/dkyapi", "User Ä‘Äƒng kÃ½ API partner.", "user"),
            ("dkapi", "/dkapi", "Alias Ä‘Äƒng kÃ½ API.", "user"),
            ("dangkyapi", "/dangkyapi", "Alias Ä‘Äƒng kÃ½ API.", "user"),
            ("regapi", "/regapi", "Alias Ä‘Äƒng kÃ½ API.", "user"),
            ("napapi", "/napapi", "User náº¡p vÃ­ API.", "user"),
            ("topupapi", "/topupapi", "Alias náº¡p vÃ­ API.", "user"),
        ],
    },
    {
        "group": "Supplier SupplierSource vÃ  SocialSource",
        "commands": [
            ("add_resell", "/add_resell ...", "ThÃªm sáº£n pháº©m resell SupplierSource.", "write"),
            ("supplier_catalog_web", "/admin/supplier_catalog", "Web chá»n sáº£n pháº©m SupplierCatalog, tick lÃ  hiá»‡n bot.", "write"),
            ("list_supplier_catalog_products", "/list_supplier_catalog_products [keyword]", "Xem ID sáº£n pháº©m SupplierCatalog.", "readonly"),
            ("add_supplier_catalog_resell", "/add_supplier_catalog_resell ...", "ThÃªm resell SupplierCatalog báº±ng ID.", "write"),
            ("list_resell", "/list_resell", "Danh sÃ¡ch resell SupplierSource.", "readonly"),
            ("edit_markup", "/edit_markup ...", "Sá»­a markup resell.", "write"),
            ("del_resell", "/del_resell <product_id>", "XÃ³a resell.", "danger"),
            ("sync_resell", "/sync_resell", "Äá»“ng bá»™ SupplierSource.", "write"),
            ("add_ctt", "/add_ctt ...", "ThÃªm dá»‹ch vá»¥ SocialSource.", "write"),
            ("list_ctt", "/list_ctt", "Danh sÃ¡ch dá»‹ch vá»¥ SocialSource.", "readonly"),
            ("del_ctt", "/del_ctt <product_id>", "XÃ³a dá»‹ch vá»¥ SocialSource.", "danger"),
            ("sync_ctt", "/sync_ctt", "Äá»“ng bá»™ SocialSource.", "write"),
            ("ctt_balance", "/ctt_balance", "Xem sá»‘ dÆ° SocialSource.", "readonly"),
        ],
    },
    {
        "group": "Há»— trá»£, thÃ´ng bÃ¡o, váº­n hÃ nh",
        "commands": [
            ("notify", "/notify <product_id> <out|back>", "ThÃ´ng bÃ¡o háº¿t/cÃ³ hÃ ng.", "write"),
            ("resetnotify", "/resetnotify", "Reset cá» thÃ´ng bÃ¡o stock.", "write"),
            ("analytics", "/analytics", "Thá»‘ng kÃª nÃ¢ng cao.", "readonly"),
            ("chats", "/chats", "Danh sÃ¡ch live chat.", "readonly"),
            ("chat", "/chat <user_id>", "Má»Ÿ chat admin vá»›i user.", "conversation"),
            ("closechat", "/closechat", "ÄÃ³ng chat admin.", "write"),
            ("baotri", "/baotri", "Báº­t/táº¯t maintenance mode.", "danger"),
            ("aimode", "/aimode", "Báº­t/táº¯t AI auto reply.", "write"),
        ],
    },
]


_LAYOUT_CSS = (Path(__file__).parent / "static" / "layout.css").read_text(encoding="utf-8")

def _admin_web_flat_commands():
    rows = []
    for group in ADMIN_WEB_COMMAND_GROUPS:
        for name, syntax, description, risk in group["commands"]:
            rows.append(
                {
                    "group": group["group"],
                    "name": name,
                    "syntax": syntax,
                    "description": description,
                    "risk": risk,
                }
            )
    return rows


def _admin_web_session_token() -> str:
    expires_at = int(time.time()) + int(ADMIN_WEB_SESSION_HOURS) * 3600
    nonce = secrets.token_hex(16)
    payload = f"{expires_at}.{nonce}"
    signature = hmac.new(ADMIN_WEB_SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _admin_web_session_valid(token: str) -> bool:
    try:
        expires_at, nonce, signature = str(token or "").split(".", 2)
        if int(expires_at) < int(time.time()) or len(nonce) != 32:
            return False
        payload = f"{expires_at}.{nonce}"
        expected = hmac.new(ADMIN_WEB_SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    except (TypeError, ValueError):
        return False


def _admin_web_b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _admin_web_b64url_decode(value: str) -> bytes:
    text = str(value or "")
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _admin_web_telegram_login_enabled() -> bool:
    return bool(TELEGRAM_LOGIN_CLIENT_ID and TELEGRAM_LOGIN_CLIENT_SECRET and ADMIN_USER_ID)


def _admin_web_telegram_redirect_uri(request) -> str:
    configured = str(TELEGRAM_LOGIN_REDIRECT_URI or "").strip()
    if configured:
        return configured
    return str(request.url_for("admin_web_telegram_callback"))


def _admin_web_telegram_oidc_cookie(payload: dict) -> str:
    encoded = _admin_web_b64url_encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    )
    signature = hmac.new(
        ADMIN_WEB_SESSION_SECRET.encode("utf-8"),
        f"telegram_oidc.{encoded}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded}.{signature}"


def _admin_web_telegram_oidc_cookie_data(value: str) -> dict:
    try:
        encoded, signature = str(value or "").split(".", 1)
        expected = hmac.new(
            ADMIN_WEB_SESSION_SECRET.encode("utf-8"),
            f"telegram_oidc.{encoded}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return {}
        payload = json.loads(_admin_web_b64url_decode(encoded).decode("utf-8"))
        issued_at = int(payload.get("issued_at") or 0)
        if issued_at <= 0 or abs(int(time.time()) - issued_at) > ADMIN_WEB_TELEGRAM_OIDC_TTL_SECONDS:
            return {}
        return payload if isinstance(payload, dict) else {}
    except (ValueError, TypeError, json.JSONDecodeError):
        return {}


def _admin_web_verify_telegram_id_token(id_token: str, jwks: dict, expected_nonce: str) -> dict:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    try:
        header_part, payload_part, signature_part = str(id_token or "").split(".", 2)
        header = json.loads(_admin_web_b64url_decode(header_part).decode("utf-8"))
        claims = json.loads(_admin_web_b64url_decode(payload_part).decode("utf-8"))
        if header.get("alg") != "RS256":
            return {}
        key_id = str(header.get("kid") or "")
        key = next(
            (
                item for item in (jwks.get("keys") or [])
                if isinstance(item, dict)
                and item.get("kty") == "RSA"
                and str(item.get("kid") or "") == key_id
            ),
            None,
        )
        if not key:
            return {}
        modulus = int.from_bytes(_admin_web_b64url_decode(key["n"]), "big")
        exponent = int.from_bytes(_admin_web_b64url_decode(key["e"]), "big")
        public_key = rsa.RSAPublicNumbers(exponent, modulus).public_key()
        public_key.verify(
            _admin_web_b64url_decode(signature_part),
            f"{header_part}.{payload_part}".encode("ascii"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        now = int(time.time())
        audience = claims.get("aud")
        audience_valid = (
            hmac.compare_digest(str(audience), str(TELEGRAM_LOGIN_CLIENT_ID))
            if not isinstance(audience, list)
            else str(TELEGRAM_LOGIN_CLIENT_ID) in {str(item) for item in audience}
        )
        if claims.get("iss") != "https://oauth.telegram.org" or not audience_valid:
            return {}
        if int(claims.get("exp") or 0) < now - 30:
            return {}
        if int(claims.get("iat") or 0) > now + 60:
            return {}
        token_nonce = claims.get("nonce")
        if token_nonce is not None and (
            not expected_nonce
            or not hmac.compare_digest(str(token_nonce), str(expected_nonce))
        ):
            return {}
        return claims
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, InvalidSignature):
        return {}


def _admin_web_auth_token_from_request(request):
    return str(request.cookies.get(ADMIN_WEB_SESSION_COOKIE) or "").strip()


def _admin_web_authorized(request) -> bool:
    token = _admin_web_auth_token_from_request(request)
    return _admin_web_session_valid(token) and db_admin_session_exists(token)


def _admin_web_csrf_token(request) -> str:
    session = _admin_web_auth_token_from_request(request)
    if not _admin_web_session_valid(session):
        return ""
    return hmac.new(ADMIN_WEB_SESSION_SECRET.encode(), f"csrf.{session}".encode(), hashlib.sha256).hexdigest()


def _admin_web_password_valid(password: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = ADMIN_WEB_PASSWORD_HASH.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)).hex()
        return hmac.compare_digest(actual, digest_hex)
    except (TypeError, ValueError):
        return False


def _admin_web_require_csrf(request, form):
    supplied = _admin_web_form_text(form, "csrf_token")
    expected = _admin_web_csrf_token(request)
    if not supplied or not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def _admin_web_require(request):
    if not _admin_web_authorized(request):
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})


def _admin_web_require_same_origin(request):
    origin = str(request.headers.get("origin") or "").strip()
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(status_code=403, detail="Invalid request origin")


def _admin_web_key_query(request) -> str:
    return ""


def _admin_web_action_url(request) -> str:
    return "/admin/action"


def _admin_web_page_url(request, path: str, params: dict | None = None) -> str:
    query_parts = []
    for key, value in (params or {}).items():
        query_parts.append(f"{quote(str(key))}={quote(str(value))}")
    return f"{path}?{'&'.join(query_parts)}" if query_parts else path


def _admin_web_item_url(request, entity: str, item_id: str) -> str:
    return _admin_web_page_url(request, "/admin/item", {"entity": entity, "id": item_id})


def _admin_web_row_link(request, entity: str, item_id: str, label: str = "Má»Ÿ") -> str:
    return f'<a class="row-link" href="{escape(_admin_web_item_url(request, entity, item_id), quote=True)}">{escape(label)}</a>'


def _admin_web_completed_orders():
    completed = []
    for order in order_history:
        try:
            if is_completed_order(order) and not order.get("refunded_at"):
                completed.append(order)
        except Exception:
            continue
    return completed


def _admin_web_financial_summary() -> dict:
    today = datetime.now().date()
    completed = _admin_web_completed_orders()
    summary = {"revenue": 0, "today_revenue": 0, "profit": 0, "today_profit": 0, "costed": 0, "today_costed": 0, "completed": len(completed)}
    for order in completed:
        amount = _admin_web_int(order.get("amount"), 0)
        summary["revenue"] += amount
        is_today = False
        try:
            is_today = datetime.fromtimestamp(float(order.get("timestamp", 0) or 0)).date() == today
        except (TypeError, ValueError, OSError, OverflowError):
            pass
        if is_today:
            summary["today_revenue"] += amount
        if order.get("cost_total") is None:
            continue
        cost = _admin_web_int(order.get("cost_total"), 0)
        summary["costed"] += 1
        summary["profit"] += amount - cost
        if is_today:
            summary["today_costed"] += 1
            summary["today_profit"] += amount - cost
    return summary


def _admin_web_total_revenue() -> int:
    return _admin_web_financial_summary()["revenue"]


def _admin_web_low_stock_count(threshold: int = 3) -> int:
    count = 0
    for product in products.values():
        if not isinstance(product, dict):
            continue
        if _admin_web_product_type(product) != "local":
            continue
        stock_count = _admin_web_stock_count(product)
        if isinstance(stock_count, int) and stock_count <= threshold:
            count += 1
    return count


def _admin_web_recent_orders(limit=10):
    rows = []
    for order in reversed(order_history[-limit * 4:]):
        if not isinstance(order, dict):
            continue
        rows.append(order)
        if len(rows) >= limit:
            break
    return rows


def _admin_web_stock_count(product_data):
    if not isinstance(product_data, dict):
        return 0
    if product_data.get("is_social_source_service"):
        return "SOCIAL_SOURCE"
    if product_data.get("is_supplier_source_resell"):
        return product_data.get("supplier_source_stock", "API")
    if product_data.get("requires_gmail"):
        return "manual"
    try:
        return int(get_local_stock_available_count(product_data) or 0)
    except Exception:
        stock = product_data.get("stock", [])
        return len(stock) if isinstance(stock, list) else 0


def _admin_web_render_products(limit=12):
    rows = []
    for product_id, product in list(products.items())[:limit]:
        if not isinstance(product, dict):
            continue
        rows.append(
            "<tr>"
            f"<td><code>{escape(str(product_id))}</code></td>"
            f"<td>{escape(str(product.get('name') or product_id))}</td>"
            f"<td>{escape(str(product.get('price', 0)))} VND</td>"
            f"<td>{escape(str(_admin_web_stock_count(product)))}</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='4' class='muted'>ChÆ°a cÃ³ sáº£n pháº©m.</td></tr>"


def _admin_web_render_users(limit=12):
    def sort_key(item):
        profile = item[1] if isinstance(item[1], dict) else {}
        return _admin_web_int(profile.get("balance"), 0)

    rows = []
    for user_id, profile in sorted(user_data_db.items(), key=sort_key, reverse=True)[:limit]:
        if not isinstance(profile, dict):
            continue
        name = profile.get("full_name") or profile.get("first_name") or profile.get("username") or ""
        banned = int(user_id) in banned_users if str(user_id).isdigit() else False
        rows.append(
            "<tr>"
            f"<td><code>{escape(str(user_id))}</code></td>"
            f"<td>{escape(str(name))}</td>"
            f"<td>{_admin_web_int(profile.get('balance'), 0):,} VND</td>"
            f"<td><span class='tag {'danger' if banned else 'readonly'}'>{'ban' if banned else 'active'}</span></td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='4' class='muted'>ChÆ°a cÃ³ user.</td></tr>"


def _admin_web_render_api_keys(limit=12):
    rows = []
    for api_key, data in list(api_keys.items())[:limit]:
        normalized = data if isinstance(data, dict) else {"name": str(data), "balance": 0}
        enabled = normalized.get("enabled") is not False
        rows.append(
            "<tr>"
            f"<td><code>{escape(str(api_key)[:18])}...</code></td>"
            f"<td>{escape(str(normalized.get('name') or 'N/A'))}</td>"
            f"<td>{_admin_web_int(normalized.get('balance'), 0):,} VND</td>"
            f"<td><span class='tag {'readonly' if enabled else 'danger'}'>{'on' if enabled else 'off'}</span></td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='4' class='muted'>ChÆ°a cÃ³ API key.</td></tr>"


def _admin_web_render_orders(limit=10):
    rows = []
    for order in _admin_web_recent_orders(limit):
        order_code = order.get("order_code") or order.get("code") or ""
        status = _admin_web_plain_display(order.get("status") or "N/A") or "N/A"
        rows.append(
            "<tr>"
            f"<td><code>{escape(str(order_code))}</code></td>"
            f"<td>{escape(str(order.get('product_name') or order.get('product_id') or 'N/A'))}</td>"
            f"<td>{escape(status)}</td>"
            f"<td>{_admin_web_int(order.get('amount'), 0):,} VND</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='4' class='muted'>ChÆ°a cÃ³ Ä‘Æ¡n hÃ ng.</td></tr>"


def _admin_web_render_audit_log(limit=12):
    rows = []
    events = admin_action_log if isinstance(admin_action_log, list) else []
    for event in reversed(events[-limit:]):
        if not isinstance(event, dict):
            continue
        status = str(event.get("status") or "unknown")
        status_class = "readonly" if status == "ok" else "danger"
        rows.append(
            "<tr>"
            f"<td>{escape(_admin_web_format_timestamp(event.get('timestamp')))}</td>"
            f"<td><code>{escape(str(event.get('action') or 'unknown'))}</code></td>"
            f"<td>{escape(str(event.get('target') or ''))}</td>"
            f"<td><span class='tag {status_class}'>{escape(status)}</span></td>"
            f"<td>{escape(str(event.get('message') or ''))}</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='5' class='muted'>ChÆ°a cÃ³ audit log.</td></tr>"


def _admin_web_render_product_rows(request=None, limit=None):
    rows = []
    items = list(products.items())[:limit] if limit else list(products.items())
    # Pre-compute sold & pending counts for performance
    _sold_map: dict = {}
    for order in (order_history if isinstance(order_history, list) else order_history.values() if isinstance(order_history, dict) else []):
        if isinstance(order, dict):
            pid = str(order.get("product_id") or "")
            _sold_map[pid] = _sold_map.get(pid, 0) + 1
    _pending_map: dict = {}
    for order in (pending_manual_orders.values() if isinstance(pending_manual_orders, dict) else []):
        if isinstance(order, dict):
            pid = str(order.get("product_id") or "")
            _pending_map[pid] = _pending_map.get(pid, 0) + 1
    for product_id, product in items:
        if not isinstance(product, dict):
            continue
        product_type = _admin_web_product_type(product)
        pending_count = _pending_map.get(str(product_id), 0)
        sold_count = _sold_map.get(str(product_id), 0)
        stock_count = _admin_web_stock_count(product)
        sync_state = str(product.get("ctt_sync_state") or "active")
        status_class = "readonly"
        if product_type == "local" and isinstance(stock_count, int) and stock_count <= 0:
            status_class = "danger"
        elif product_type == "manual" and pending_count >= _admin_web_int(product.get("max_pending_orders"), 10):
            status_class = "write"
        if sync_state == "inactive":
            status_class = "danger"
        search = _admin_web_row_search(product_id, product.get("name"), product_type, product.get("price"), sync_state)
        rows.append(
            f'<tr class="data-row" data-search="{search}" data-kind="{escape(product_type)}">'
            f"<td><code>{escape(str(product_id))}</code></td>"
            f"<td><b>{escape(_admin_web_short(product.get('name') or product_id, 90))}</b><small>{escape(_admin_web_short(product.get('duration') or product.get('store_category') or '', 90))}</small></td>"
            f"<td><span class='tag {escape(product_type)}'>{escape(product_type)}</span></td>"
            f"<td>{_admin_web_money(product.get('price'))}</td>"
            f"<td><span class='tag {status_class}'>{escape(str(stock_count))}</span></td>"
            f"<td>{pending_count}</td>"
            f"<td>{sold_count}</td>"
            f"<td>{escape(sync_state)}</td>"
            f"<td>{_admin_web_row_link(request, 'product', str(product_id))}</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='9' class='muted'>ChÆ°a cÃ³ sáº£n pháº©m.</td></tr>"


def _admin_web_render_user_rows(request=None, limit=240):
    def sort_key(item):
        profile = item[1] if isinstance(item[1], dict) else {}
        return _admin_web_int(profile.get("balance"), 0)

    rows = []
    for user_id, profile in sorted(user_data_db.items(), key=sort_key, reverse=True)[:limit]:
        if not isinstance(profile, dict):
            continue
        name = profile.get("full_name") or profile.get("first_name") or profile.get("username") or ""
        user_id_text = str(user_id)
        banned = int(user_id_text) in banned_users if user_id_text.isdigit() else False
        orders_count = sum(
            1
            for order in order_history
            if isinstance(order, dict) and str(order.get("user_id") or "") == user_id_text
        )
        search = _admin_web_row_search(user_id, name, profile.get("username"), profile.get("email"), profile.get("balance"))
        rows.append(
            f'<tr class="data-row" data-search="{search}" data-kind="{"banned" if banned else "active"}">'
            f"<td><code>{escape(user_id_text)}</code></td>"
            f"<td><b>{escape(_admin_web_short(name or 'N/A', 90))}</b><small>{escape(_admin_web_short(profile.get('username') or profile.get('email') or '', 90))}</small></td>"
            f"<td>{_admin_web_money(profile.get('balance'))}</td>"
            f"<td>{orders_count}</td>"
            f"<td>{_admin_web_money(profile.get('total_spent') or profile.get('spent') or 0)}</td>"
            f"<td><span class='tag {'danger' if banned else 'readonly'}'>{'ban' if banned else 'active'}</span></td>"
            f"<td>{_admin_web_row_link(request, 'user', user_id_text)}</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='7' class='muted'>ChÆ°a cÃ³ user.</td></tr>"


def _admin_web_render_order_rows(request=None, limit=240):
    rows = []
    for order in _admin_web_recent_orders(limit):
        if not isinstance(order, dict):
            continue
        order_code = _admin_web_order_code(order)
        raw_status = str(order.get("status") or "N/A")
        status = _admin_web_plain_display(raw_status) or raw_status
        status_text_value = status
        try:
            status_text_value = status_text(status)
        except Exception:
            pass
        status_text_value = _admin_web_plain_display(status_text_value) or status
        status_class = "readonly" if "hoan" in status_text_value.casefold() or "complete" in status.casefold() else "write"
        if any(word in status.casefold() for word in ("cancel", "refund", "fail", "huy")):
            status_class = "danger"
        search = _admin_web_row_search(order_code, order.get("product_name"), order.get("product_id"), order.get("user_id"), status)
        rows.append(
            f'<tr class="data-row" data-search="{search}" data-kind="{escape(status.casefold())}">'
            f"<td><code>{escape(order_code)}</code></td>"
            f"<td><b>{escape(_admin_web_short(order.get('product_name') or order.get('product_id') or 'N/A', 90))}</b><small>{escape(str(order.get('product_id') or ''))}</small></td>"
            f"<td>{escape(str(order.get('user_id') or ''))}</td>"
            f"<td><span class='tag {status_class}'>{escape(_admin_web_short(status_text_value, 36))}</span></td>"
            f"<td>{_admin_web_money(order.get('amount'))}</td>"
            f"<td>{escape(str(order.get('quantity') or 1))}</td>"
            f"<td>{escape(_admin_web_order_time(order))}</td>"
            f"<td>{_admin_web_row_link(request, 'order', order_code)}</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='8' class='muted'>ChÆ°a cÃ³ Ä‘Æ¡n hÃ ng.</td></tr>"


def _admin_web_render_api_partner_rows(request=None, limit=240):
    rows = []
    action_url = _admin_web_action_url(request) if request is not None else "/admin/action"
    for api_key, data in list(api_keys.items()):
        normalized = data if isinstance(data, dict) else {"name": str(data), "balance": 0}
        enabled = normalized.get("enabled") is not False
        balance = _admin_web_int(normalized.get("balance"), 0)
        key_label = _admin_web_api_display_key(str(api_key))
        api_public_id = _admin_web_api_public_id(str(api_key))
        is_admin_key = str(normalized.get("user_id") or "").strip() == str(ADMIN_USER_ID).strip()
        balance_class = "money-alert" if (abs(balance) >= ADMIN_WEB_SUSPICIOUS_BALANCE_THRESHOLD and not is_admin_key) else ""
        role_badge = "<span class='tag danger'>ADMIN</span>" if is_admin_key else "<span class='tag readonly'>USER</span>"
        row_kind = "admin" if is_admin_key else ("active" if enabled else "disabled")
        threshold = max(0, _admin_web_int(normalized.get("low_balance_threshold"), 100000))
        is_low = balance <= threshold
        ip_count = len(_api_normalize_allowed_ips(normalized.get("allowed_ips") or []))
        quota = _api_partner_rate_limit(normalized)
        note = str(normalized.get("admin_note") or _admin_web_api_wallet_note(normalized, balance))
        search = _admin_web_row_search(api_key, api_public_id, normalized.get("name"), balance, normalized.get("user_id"), note, row_kind)
        rows.append(
            f'<tr class="data-row" data-search="{search}" data-kind="{row_kind}" data-balance="{balance}" data-low="{"1" if is_low else "0"}">'
            f"<td><code>{escape(key_label)}</code><small>{escape(api_public_id)}</small></td>"
            f"<td><b>{escape(_admin_web_short(normalized.get('name') or 'N/A', 60))}</b><div class='api-row-badges'>{role_badge}<span class='tag api'>{ip_count} IP</span></div><small>Owner {escape(str(normalized.get('user_id') or 'none'))}</small></td>"
            f'<td class="{balance_class}"><b>{_admin_web_money(balance)}</b><small class="{"low-balance" if is_low else ""}">NgÆ°á»¡ng {_admin_web_money(threshold)}</small></td>'
            f"<td><span class='api-status-dot {'is-on' if enabled else 'is-off'}'></span>{'Äang hoáº¡t Ä‘á»™ng' if enabled else 'ÄÃ£ thu há»“i'}</td>"
            f"<td><b>{quota}/phÃºt</b><small>{'Telegram ON' if normalized.get('low_balance_alert_enabled') is not False else 'Alert OFF'}</small></td>"
            f"<td>{escape(_admin_web_short(note, 80))}</td>"
            f'<td><form method="post" action="{action_url}" class="api-quick-wallet"><input type="hidden" name="action" value="api_partner"><input type="hidden" name="mode" value="topup"><input type="hidden" name="target" value="{escape(api_public_id, quote=True)}"><input name="amount" type="number" min="1" placeholder="Sá»‘ tiá»n" aria-label="Sá»‘ tiá»n cá»™ng nhanh"><button type="submit" title="Cá»™ng sá»‘ dÆ°">+</button></form>{_admin_web_row_link(request, "api", api_public_id)}</td>'
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='7' class='muted'>ChÆ°a cÃ³ API partner.</td></tr>"


def _admin_web_render_coupon_rows(request=None, limit=180):
    rows = []
    source = coupons if isinstance(coupons, dict) else {}
    for code, details in list(source.items())[:limit]:
        item = details if isinstance(details, dict) else {}
        quantity = item.get("quantity", "inf")
        used = item.get("used", 0)
        search = _admin_web_row_search(code, item.get("discount"), item.get("expires"))
        rows.append(
            f'<tr class="data-row" data-search="{search}" data-kind="coupon">'
            f"<td><code>{escape(str(code))}</code></td>"
            f"<td>{_admin_web_money(item.get('discount'))}</td>"
            f"<td>{escape(str(used))} / {escape(str(quantity))}</td>"
            f"<td>{escape(str(item.get('expires') or 'N/A'))}</td>"
            f"<td>{_admin_web_row_link(request, 'coupon', str(code))}</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='5' class='muted'>ChÆ°a cÃ³ coupon.</td></tr>"


def _admin_web_render_pending_manual_rows(limit=120):
    rows = []
    for order_code, info in list(pending_manual_orders.items())[:limit]:
        item = info if isinstance(info, dict) else {}
        search = _admin_web_row_search(order_code, item.get("product_name"), item.get("product_id"), item.get("user_id"))
        rows.append(
            f'<tr class="data-row" data-search="{search}" data-kind="pending">'
            f"<td><code>{escape(str(order_code))}</code></td>"
            f"<td><b>{escape(_admin_web_short(item.get('product_name') or item.get('product_id') or 'N/A', 90))}</b><small>{escape(str(item.get('product_id') or ''))}</small></td>"
            f"<td>{escape(str(item.get('user_id') or ''))}</td>"
            f"<td>{_admin_web_money(item.get('amount'))}</td>"
            f"<td>{escape(_admin_web_format_timestamp(item.get('timestamp')))}</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='5' class='muted'>KhÃ´ng cÃ³ Ä‘Æ¡n manual pending.</td></tr>"


def _admin_web_log_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _admin_web_tail_text(path: Path, max_lines: int = 80) -> str:
    try:
        if not path.is_file():
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()[-max_lines:]
        return "\n".join(lines)
    except (OSError, UnicodeError, ValueError):
        return ""


def _admin_web_render_ops_status_rows(request=None) -> str:
    bank_configured = bool(str(globals().get("API_PASSWORD") or "").strip() and str(globals().get("BANK_ACCOUNT_NUMBER") or "").strip())
    bank_account = str(globals().get("BANK_ACCOUNT_NUMBER") or "").strip() or "N/A"
    pending_bank = sum(
        1 for item in pending_orders.values()
        if isinstance(item, dict) and str(item.get("payment_method") or "").strip().lower() in {"bank_transfer", "mbbank", "bank"}
    )

    last_check_time = float(globals().get("_bank_api_last_check_time", 0.0) or 0.0)
    last_status = str(globals().get("_bank_api_last_status", "unknown") or "unknown")
    last_error = str(globals().get("_bank_api_last_error", "") or "")
    last_tx = int(globals().get("_bank_api_last_tx_count", 0) or 0)
    fail_count = int(globals().get("_bank_api_fail_count", 0) or 0)
    total_checks = int(globals().get("_bank_api_total_checks", 0) or 0)
    total_success = int(globals().get("_bank_api_total_success", 0) or 0)
    interval = int(globals().get("BANK_CHECK_INTERVAL_SECONDS", 15) or 15)

    if last_check_time > 0:
        age = max(0, int(time.time() - last_check_time))
        last_check_text = f"{age}s ago"
    else:
        last_check_text = "chÆ°a cháº¡y"

    if not bank_configured:
        bank_status = "danger"
        bank_label = "config missing"
    elif last_status == "ok" and (time.time() - last_check_time) < (interval * 4 + 30):
        bank_status = "live"
        bank_label = "200 OK"
    elif last_status == "error":
        bank_status = "danger"
        bank_label = "API error"
    elif last_check_time == 0:
        bank_status = "warn"
        bank_label = "Ä‘ang chá» pending"
    else:
        bank_status = "warn"
        bank_label = "stale"

    success_rate = f"{int(total_success * 100 / total_checks)}%" if total_checks > 0 else "â€”"
    bank_note = (
        f"Account {bank_account} Â· pending: {pending_bank} Â· last check: {last_check_text} Â· "
        f"tx: {last_tx} Â· success: {total_success}/{total_checks} ({success_rate}) Â· fails: {fail_count}"
    )
    if last_status == "error" and last_error:
        bank_note += f" Â· err: {last_error[:120]}"

    bot_username = str(globals().get("BOT_USERNAME") or "").strip() or "N/A"
    admin_username = str(globals().get("ADMIN_USERNAME") or "").strip() or "N/A"
    admin_user_id = str(globals().get("ADMIN_USER_ID") or "").strip() or "N/A"
    uptime_seconds = max(0, int(time.time() - float(getattr(app_state, "bot_start_time", time.time()) or time.time())))
    uptime_text = f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m"
    
    import app.core.config_env as config_env
    mbbank_enabled = getattr(config_env, "ENABLE_PAYMENT_MBBANK", True)
    binance_enabled = getattr(config_env, "ENABLE_PAYMENT_BINANCE_SPOT", True)
    
    mbbank_btn = f"<form method='post' action='{_admin_web_action_url(request)}' style='display:inline'><input type='hidden' name='action' value='system_toggle'><input type='hidden' name='mode' value='{'mbbank_off' if mbbank_enabled else 'mbbank_on'}'><button class='button small {'danger' if mbbank_enabled else 'success'}'>{'Táº¯t' if mbbank_enabled else 'Báº­t'}</button></form>"
    binance_btn = f"<form method='post' action='{_admin_web_action_url(request)}' style='display:inline'><input type='hidden' name='action' value='system_toggle'><input type='hidden' name='mode' value='{'binance_off' if binance_enabled else 'binance_on'}'><button class='button small {'danger' if binance_enabled else 'success'}'>{'Táº¯t' if binance_enabled else 'Báº­t'}</button></form>"

    rows = [
        (bank_status, f"Cron MBBank ({bank_label})", f"{escape(bank_note)} <br><br><b>Cá»•ng MBBank:</b> <span class='tag {'success' if mbbank_enabled else 'danger'}'>{'Báº¬T' if mbbank_enabled else 'Táº®T'}</span> {mbbank_btn}"),
        ("live", "Bot user", f"@{escape(bot_username)} Â· users: {len(user_data_db)} Â· uptime: {escape(uptime_text)}"),
        ("live", "Bot admin", f"@{escape(admin_username)} Â· admin_id: {escape(admin_user_id)}"),
        ("live" if not MAINTENANCE_MODE else "danger", "Maintenance", f"maintenance {_admin_web_bool_text(MAINTENANCE_MODE)} Â· ai {_admin_web_bool_text(AI_AUTO_REPLY)}"),
        ("live", "Runtime queues", f"pending pay: {len(pending_orders)} Â· manual pending: {len(pending_manual_orders)} Â· support open: {_admin_web_active_count(live_chats)}"),
        ("live", "Binance Spot", f"Cá»•ng thanh toÃ¡n USDT tá»± Ä‘á»™ng qua Binance API <br><br><b>Tráº¡ng thÃ¡i:</b> <span class='tag {'success' if binance_enabled else 'danger'}'>{'Báº¬T' if binance_enabled else 'Táº®T'}</span> {binance_btn}"),
    ]
    status_class_map = {"live": "readonly", "warn": "write", "danger": "danger"}
    return "".join(
        f"<tr><td><span class='tag {status_class_map.get(status, 'readonly')}'>{escape(status)}</span></td><td>{escape(name)}</td><td>{note}</td></tr>"
        for status, name, note in rows
    )


def _admin_web_render_ops_log_panel() -> str:
    root = _admin_web_log_root()
    candidates = [
        root / "bot.log",
        root / "bot.log.1",
        root / "admin_preview.out.log",
        root / "admin_preview.err.log",
    ]
    all_lines = []
    for path in candidates:
        content = _admin_web_tail_text(path, max_lines=50)
        if not content:
            continue
        for line in content.splitlines():
            stripped = line.strip()
            if stripped:
                all_lines.append(stripped)

    if not all_lines:
        return "<div class='ecg-monitor'><div class='ecg-header'><span class='ecg-dot'></span> LOG MONITOR</div><div class='ecg-body'><p class='ecg-empty'>ChÆ°a tÃ¬m tháº¥y file log trong thÆ° má»¥c bot.</p></div></div>"

    # Keep last 40 lines
    display_lines = all_lines[-40:]
    line_items = []
    for i, line in enumerate(display_lines):
        # Detect log level for coloring
        level_class = "ecg-info"
        if " - ERROR" in line or "ERROR:" in line:
            level_class = "ecg-error"
        elif " - WARNING" in line or "WARNING:" in line:
            level_class = "ecg-warn"
        elif "SUCCESS" in line.upper() or "Ready to serve" in line or "initialized" in line.lower():
            level_class = "ecg-success"

        line_items.append(f"<div class='ecg-line {level_class}' style='animation-delay:{i * 0.05:.2f}s'><span class='ecg-pulse'></span>{escape(line)}</div>")

    lines_html = "".join(line_items)
    return (
        "<div class='ecg-monitor'>"
        "<div class='ecg-header'><span class='ecg-dot'></span> LOG MONITOR <span class='ecg-badge'>LIVE</span></div>"
        "<div class='ecg-canvas'><svg class='ecg-svg' viewBox='0 0 600 60' preserveAspectRatio='none'><polyline class='ecg-wave' points='0,30 30,30 45,30 55,10 60,50 65,30 80,30 120,30 135,30 145,10 150,50 155,30 170,30 210,30 225,30 235,10 240,50 245,30 260,30 300,30 315,30 325,10 330,50 335,30 350,30 390,30 405,30 415,10 420,50 425,30 440,30 480,30 495,30 505,10 510,50 515,30 530,30 570,30 585,30 595,10 600,50'/></svg></div>"
        f"<div class='ecg-body'>{lines_html}</div>"
        "</div>"
    )


def _admin_web_render_legacy_link_rows(limit=80):
    rows = []
    source = list(available_links) if isinstance(available_links, set) else list(available_links or [])
    for index, link in enumerate(source[:limit], 1):
        link_text = str(link or "").strip()
        if not link_text:
            continue
        search = _admin_web_row_search(link_text)
        rows.append(
            f'<tr class="data-row" data-search="{search}" data-kind="legacy-link">'
            f"<td>{index}</td>"
            f"<td><code>{escape(_admin_web_short(link_text, 140))}</code></td>"
            f"<td><span class='tag readonly'>active</span></td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='3' class='muted'>Kho link legacy Ä‘ang trá»‘ng.</td></tr>"


def _admin_web_render_support_rows(request=None, limit=120):
    rows = []
    sources = [
        ("live_chat", live_chats if isinstance(live_chats, dict) else {}),
        ("warranty", warranty_claims if isinstance(warranty_claims, dict) else {}),
        ("withdrawal", withdrawal_requests if isinstance(withdrawal_requests, dict) else {}),
    ]
    for kind, data in sources:
        for item_id, info in list(data.items())[:limit]:
            item = info if isinstance(info, dict) else {}
            status = _admin_web_plain_display(item.get("status") or "pending") or "pending"
            search = _admin_web_row_search(kind, item_id, item.get("user_id"), status, item.get("order_code"))
            rows.append(
                f'<tr class="data-row" data-search="{search}" data-kind="{escape(kind)}">'
                f"<td><span class='tag {escape(kind)}'>{escape(kind)}</span></td>"
                f"<td><code>{escape(str(item_id))}</code></td>"
                f"<td>{escape(str(item.get('user_id') or ''))}</td>"
                f"<td>{escape(status)}</td>"
                f"<td>{escape(_admin_web_short(item.get('description') or item.get('bank_info') or item.get('order_code') or '', 90))}</td>"
                f"<td>{_admin_web_row_link(request, kind, str(item_id))}</td>"
                "</tr>"
            )
            if len(rows) >= limit:
                break
    return "".join(rows) or "<tr><td colspan='6' class='muted'>ChÆ°a cÃ³ ticket há»— trá»£.</td></tr>"


def _admin_web_render_audit_rows(limit=120):
    rows = []
    events = admin_action_log if isinstance(admin_action_log, list) else []
    for event in reversed(events[-limit:]):
        if not isinstance(event, dict):
            continue
        status = str(event.get("status") or "unknown")
        status_class = "readonly" if status == "ok" else "danger"
        search = _admin_web_row_search(event.get("action"), event.get("target"), event.get("message"), event.get("ip"), status)
        rows.append(
            f'<tr class="data-row" data-search="{search}" data-kind="{escape(status)}">'
            f"<td>{escape(_admin_web_format_timestamp(event.get('timestamp')))}</td>"
            f"<td><code>{escape(str(event.get('action') or 'unknown'))}</code></td>"
            f"<td>{escape(str(event.get('target') or ''))}</td>"
            f"<td><span class='tag {status_class}'>{escape(status)}</span></td>"
            f"<td>{escape(str(event.get('ip') or ''))}</td>"
            f"<td>{escape(_admin_web_short(event.get('message') or '', 120))}</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='6' class='muted'>ChÆ°a cÃ³ audit log.</td></tr>"


def _admin_web_render_payment_config(request) -> str:
    import app.core.config_env as config_env
    rows = (
        ("MBBank", bool(str(getattr(config_env, "API_PASSWORD", "")).strip())),
        ("Bank API token", bool(str(getattr(config_env, "API_TOKEN", "")).strip())),
        ("Binance API key", bool(str(getattr(config_env, "BINANCE_SPOT_API_KEY", "")).strip())),
        ("Binance API secret", bool(str(getattr(config_env, "BINANCE_SPOT_API_SECRET", "")).strip())),
        ("USDT BEP20 wallet", bool(str(getattr(config_env, "USDT_BEP20_WALLET_ADDRESS", "")).strip())),
        ("Binance Pay ID", bool(str(getattr(config_env, "BINANCE_PAY_ID", "")).strip())),
    )
    status_rows = "".join(
        f"<tr><td>{escape(name)}</td><td><span class='tag {'ok' if configured else 'warn'}'>{'ÄÃ£ cáº¥u hÃ¬nh' if configured else 'ChÆ°a cáº¥u hÃ¬nh'}</span></td></tr>"
        for name, configured in rows
    )
    return f"""
    <div style="padding:16px;">
      <h3>Cáº¥u hÃ¬nh Thanh toÃ¡n</h3>
      <p class="muted">Read-only. Cáº­p nháº­t secret trong deployment environment rá»“i restart bot.</p>
      <table><thead><tr><th>Dá»‹ch vá»¥</th><th>Tráº¡ng thÃ¡i</th></tr></thead><tbody>{status_rows}</tbody></table>
    </div>
    """

def _admin_web_overview_empty(text: str) -> str:
    return f'<div class="overview-empty">{escape(text)}</div>'


def _admin_web_overview_pending_items(request, limit: int = 6) -> str:
    rows = []
    for order_code, info in list(pending_manual_orders.items())[:limit]:
        item = info if isinstance(info, dict) else {}
        product_name = item.get("product_name") or item.get("product_id") or "N/A"
        product_id = item.get("product_id") or ""
        user_id = item.get("user_id") or ""
        amount = _admin_web_money(item.get("amount"))
        search = _admin_web_row_search(order_code, product_name, product_id, user_id, amount)
        rows.append(
            f'<a class="overview-item data-row" data-search="{search}" data-kind="pending" href="{escape(_admin_web_item_url(request, "order", str(order_code)), quote=True)}">'
            '<div class="overview-main">'
            f'<div class="overview-title"><code>{escape(str(order_code))}</code><b>{escape(_admin_web_short(product_name, 64))}</b></div>'
            f'<span>{escape(str(product_id))}</span>'
            "</div>"
            f'<div class="overview-meta"><span>User {escape(str(user_id) or "N/A")}</span><b>{escape(amount)}</b></div>'
            "</a>"
        )
    return "".join(rows) or _admin_web_overview_empty("KhÃ´ng cÃ³ Ä‘Æ¡n manual pending.")


def _admin_web_overview_order_items(request, limit: int = 6) -> str:
    rows = []
    for order in _admin_web_recent_orders(limit):
        if not isinstance(order, dict):
            continue
        order_code = _admin_web_order_code(order)
        product_name = order.get("product_name") or order.get("product_id") or "N/A"
        raw_status = str(order.get("status") or "N/A")
        status = _admin_web_plain_display(raw_status) or raw_status
        try:
            status_label = status_text(status)
        except Exception:
            status_label = status
        status_label = _admin_web_plain_display(status_label) or status
        status_class = "readonly" if "hoan" in status_label.casefold() or "complete" in status.casefold() else "write"
        if any(word in status.casefold() for word in ("cancel", "refund", "fail", "huy")):
            status_class = "danger"
        search = _admin_web_row_search(order_code, product_name, order.get("product_id"), order.get("user_id"), status)
        rows.append(
            f'<a class="overview-item data-row" data-search="{search}" data-kind="{escape(status.casefold())}" href="{escape(_admin_web_item_url(request, "order", order_code), quote=True)}">'
            '<div class="overview-main">'
            f'<div class="overview-title"><code>{escape(order_code)}</code><b>{escape(_admin_web_short(product_name, 68))}</b></div>'
            f'<span>{escape(_admin_web_short(order.get("product_id") or "", 42))}</span>'
            "</div>"
            '<div class="overview-meta">'
            f'<span class="tag {status_class}">{escape(_admin_web_short(status_label, 24))}</span>'
            f'<b>{_admin_web_money(order.get("amount"))}</b>'
            "</div>"
            "</a>"
        )
    return "".join(rows) or _admin_web_overview_empty("ChÆ°a cÃ³ Ä‘Æ¡n hÃ ng gáº§n Ä‘Ã¢y.")


def _admin_web_overview_audit_items(limit: int = 6) -> str:
    rows = []
    events = admin_action_log if isinstance(admin_action_log, list) else []
    for event in reversed(events[-limit:]):
        if not isinstance(event, dict):
            continue
        status = str(event.get("status") or "unknown")
        status_class = "readonly" if status == "ok" else "danger"
        search = _admin_web_row_search(event.get("action"), event.get("target"), event.get("message"), event.get("ip"), status)
        rows.append(
            f'<article class="overview-item data-row" data-search="{search}" data-kind="{escape(status)}">'
            '<div class="overview-main">'
            f'<div class="overview-title"><code>{escape(str(event.get("action") or "unknown"))}</code><b>{escape(_admin_web_short(event.get("target") or "system", 56))}</b></div>'
            f'<span>{escape(_admin_web_short(event.get("message") or "No message", 72))}</span>'
            "</div>"
            '<div class="overview-meta">'
            f'<span class="tag {status_class}">{escape(status)}</span>'
            f'<b>{escape(_admin_web_format_timestamp(event.get("timestamp")))}</b>'
            "</div>"
            "</article>"
        )
    return "".join(rows) or _admin_web_overview_empty("ChÆ°a cÃ³ audit log.")


def _admin_web_revenue_chart(days: int = 30) -> str:
    from datetime import datetime, timedelta, timezone
    import json

    tz = timezone(timedelta(hours=7))
    today = datetime.now(tz).date()
    date_labels = [(today - timedelta(days=days - 1 - i)) for i in range(days)]
    date_map: dict = {d: 0 for d in date_labels}

    for order in _admin_web_completed_orders():
        if not isinstance(order, dict):
            continue
        amount = int(order.get("amount") or order.get("price") or 0)
        if amount <= 0:
            continue
        ts_raw = order.get("timestamp") or order.get("completed_at") or order.get("created_at") or order.get("paid_at") or ""
        try:
            if isinstance(ts_raw, (int, float)) and float(ts_raw) > 0:
                dt = datetime.fromtimestamp(float(ts_raw), tz=tz)
            elif isinstance(ts_raw, str) and ts_raw.strip():
                ts_clean = ts_raw.strip().replace("Z", "+00:00")
                dt = datetime.fromisoformat(ts_clean).astimezone(tz)
            else:
                continue
            d = dt.date()
            if d in date_map:
                date_map[d] += amount
        except Exception:
            continue

    values = [date_map[d] for d in date_labels]
    max_val = max(values) if any(v > 0 for v in values) else 1

    # SVG bar chart
    W, H, PAD_L, PAD_B = 600, 180, 50, 30
    bar_w = max(2, (W - PAD_L - 10) // days - 2)
    bar_area_w = W - PAD_L - 10

    def fmt_vnd(v):
        if v >= 1_000_000:
            return f"{v/1_000_000:.1f}M"
        if v >= 1_000:
            return f"{v/1_000:.0f}K"
        return str(v)

    bars_svg = []
    for i, (d, v) in enumerate(zip(date_labels, values)):
        x = PAD_L + int(i * bar_area_w / days)
        bar_h = max(2, int((v / max_val) * (H - PAD_B - 20))) if v > 0 else 2
        y = H - PAD_B - bar_h
        is_today = (d == today)
        color = "#4ade80" if is_today else "#3b82f6"
        tip = f"{d.strftime('%d/%m')}: {v:,}Ä‘"
        bars_svg.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" fill="{color}" rx="2" opacity="0.85">'
            f'<title>{tip}</title></rect>'
        )
        # x-axis label every 5 days or today
        if i % 5 == 0 or is_today:
            bars_svg.append(
                f'<text x="{x + bar_w//2}" y="{H - PAD_B + 14}" text-anchor="middle" '
                f'font-size="9" fill="{"#4ade80" if is_today else "#888"}">{d.strftime("%d/%m")}</text>'
            )

    # y-axis gridlines
    grid_svg = []
    for frac in (0.25, 0.5, 0.75, 1.0):
        gy = H - PAD_B - int(frac * (H - PAD_B - 20))
        lbl = fmt_vnd(int(max_val * frac))
        grid_svg.append(
            f'<line x1="{PAD_L}" y1="{gy}" x2="{W - 10}" y2="{gy}" stroke="#333" stroke-width="1" stroke-dasharray="3,3"/>'
            f'<text x="{PAD_L - 4}" y="{gy + 4}" text-anchor="end" font-size="9" fill="#666">{lbl}</text>'
        )

    total_period = sum(values)
    week_vals = values[-7:]
    total_week = sum(week_vals)

    svg = (
        f'<svg viewBox="0 0 {W} {H}" style="width:100%;max-width:{W}px;height:auto;display:block;" xmlns="http://www.w3.org/2000/svg">'
        + "".join(grid_svg)
        + "".join(bars_svg)
        + f'<line x1="{PAD_L}" y1="{H - PAD_B}" x2="{W - 10}" y2="{H - PAD_B}" stroke="#444" stroke-width="1"/>'
        + "</svg>"
    )

    return f"""
<section class="mini-panel queue-panel" style="grid-column:1/-1;">
  <div class="card-head">
    <h3>Doanh thu {days} ngÃ y gáº§n nháº¥t</h3>
    <span class="muted" style="font-size:12px;">
      Tuáº§n: <b style="color:#4ade80;">{total_week:,}Ä‘</b>
      &nbsp;|&nbsp; {days} ngÃ y: <b style="color:#3b82f6;">{total_period:,}Ä‘</b>
    </span>
  </div>
  <div style="padding:8px 4px 0;">{svg}</div>
</section>"""


def _admin_web_overview_board(request) -> str:
    return f"""
<div class="overview-board">
  {_admin_web_revenue_chart(30)}
  <section class="mini-panel queue-panel">
    <div class="card-head"><h3>HÃ ng Ä‘á»£i cáº§n xá»­ lÃ½</h3><a class="panel-link" href="#ops">{len(pending_manual_orders)} manual</a></div>
    <div class="overview-list">{_admin_web_overview_pending_items(request)}</div>
  </section>
  <section class="mini-panel queue-panel">
    <div class="card-head"><h3>ÄÆ¡n má»›i gáº§n Ä‘Ã¢y</h3><a class="panel-link" href="#orders">{len(order_history)} total</a></div>
    <div class="overview-list">{_admin_web_overview_order_items(request)}</div>
  </section>
  <section class="mini-panel queue-panel">
    <div class="card-head"><h3>Audit gáº§n Ä‘Ã¢y</h3><a class="panel-link" href="#audit">web</a></div>
    <div class="overview-list">{_admin_web_overview_audit_items()}</div>
  </section>
</div>
"""


def _admin_web_hidden_return(entity: str, item_id: str) -> str:
    return (
        f'<input type="hidden" name="return_entity" value="{escape(str(entity), quote=True)}">'
        f'<input type="hidden" name="return_id" value="{escape(str(item_id), quote=True)}">'
    )


def _admin_web_detail_shell(request, entity: str, item_id: str, title: str, summary: str, main: str, raw_data, message: str | None = None, is_error: bool = False) -> str:
    alert = (
        f'<script>document.addEventListener("DOMContentLoaded", () => showToast({json.dumps(message)}, {"true" if is_error else "false"}));</script>'
        if message
        else ""
    )
    back_url = _admin_web_page_url(request, "/admin")
    return f"""
{alert}
<div class="detail-shell">
  <div class="detail-topbar">
    <a class="button" href="{escape(back_url, quote=True)}">Vá» dashboard</a>
    <span class="tag">{escape(entity)}</span>
  </div>
  <section class="workspace-head detail-head">
    <div>
      <span class="eyebrow">object detail</span>
      <h1>{escape(title)}</h1>
      <p>{escape(str(item_id))}</p>
    </div>
  </section>
  <div class="detail-grid">
    <section class="module-section">
      <div class="summary-grid">{summary}</div>
      {main}
    </section>
    <aside class="raw-panel">
      <h2>Raw data</h2>
      {_admin_web_json_block(raw_data)}
    </aside>
  </div>
</div>
"""


def _admin_web_summary_card(label: str, value, kind: str = "") -> str:
    display_value = _admin_web_plain_display(value)
    label_folded = str(label or "").casefold()
    icon_class = "metric-detail"
    if any(token in label_folded for token in ("tiá»n", "giÃ¡", "sá»‘ dÆ°", "spent", "amount")):
        icon_class += " metric-detail-money"
    elif any(token in label_folded for token in ("status", "tráº¡ng thÃ¡i", "records", "orders")):
        icon_class += " metric-detail-order"
    elif any(token in label_folded for token in ("user", "owner")):
        icon_class += " metric-detail-user"
    elif any(token in label_folded for token in ("stock", "loáº¡i", "sync", "partner")):
        icon_class += " metric-detail-product"
    elif any(token in label_folded for token in ("coupon", "used")):
        icon_class += " metric-detail-promo"
    elif any(token in label_folded for token in ("báº£o hÃ nh", "bh", "háº¿t háº¡n")):
        icon_class += " metric-detail-support"
    return f'<div class="metric {icon_class} {escape(kind)}"><span>{escape(label)}</span><b title="{escape(display_value, quote=True)}">{escape(display_value)}</b></div>'


def _admin_web_recent_order_table_for_user(request, user_id: str, limit: int = 30) -> str:
    rows = []
    target = str(user_id)
    for order in reversed(order_history):
        if not isinstance(order, dict) or str(order.get("user_id") or "") != target:
            continue
        code = _admin_web_order_code(order)
        rows.append(
            "<tr>"
            f"<td><code>{escape(code)}</code></td>"
            f"<td>{escape(_admin_web_short(order.get('product_name') or order.get('product_id') or '', 90))}</td>"
            f"<td>{_admin_web_money(order.get('amount'))}</td>"
            f"<td>{escape(_admin_web_plain_display(order.get('status') or ''))}</td>"
            f"<td>{_admin_web_row_link(request, 'order', code)}</td>"
            "</tr>"
        )
        if len(rows) >= limit:
            break
    body = "".join(rows) or "<tr><td colspan='5' class='muted'>ChÆ°a cÃ³ Ä‘Æ¡n hÃ ng.</td></tr>"
    return f'<div class="table-scroll"><table class="data-table"><thead><tr><th>MÃ£</th><th>Sáº£n pháº©m</th><th>Tiá»n</th><th>Status</th><th></th></tr></thead><tbody>{body}</tbody></table></div>'


def _admin_web_order_warranty_summary_cards(order: dict) -> str:
    if not isinstance(order, dict) or not order:
        return (
            _admin_web_summary_card("Báº£o hÃ nh", "N/A")
            + _admin_web_summary_card("Háº¿t háº¡n BH", "N/A", "write")
            + _admin_web_summary_card("Tráº¡ng thÃ¡i BH", "ChÆ°a rÃµ", "write")
        )

    status_text = _admin_web_plain_display(order.get("status") or "")
    status_folded = status_text.casefold()
    refunded_at = order.get("refunded_at")
    try:
        refunded_at_value = float(refunded_at or 0)
    except (TypeError, ValueError):
        refunded_at_value = 0
    if refunded_at_value > 0 or any(token in status_folded for token in ("hoÃ n tiá»n", "hoan tien", "refund", "refunded", "há»§y", "huy", "cancel")):
        refund_time = _admin_web_format_timestamp(refunded_at_value) if refunded_at_value > 0 else "KhÃ´ng Ã¡p dá»¥ng"
        return (
            _admin_web_summary_card("Báº£o hÃ nh", "KhÃ´ng Ã¡p dá»¥ng", "danger")
            + _admin_web_summary_card("Káº¿t thÃºc BH", refund_time, "danger")
            + _admin_web_summary_card("Tráº¡ng thÃ¡i BH", "ÄÃ£ hoÃ n tiá»n", "danger")
        )

    product = {}
    product_id = str(order.get("product_id") or "").strip()
    if product_id and isinstance(products, dict):
        candidate = products.get(product_id)
        if isinstance(candidate, dict):
            product = candidate

    resolver_order = dict(order)
    if product:
        resolver_order.setdefault("warranty", product.get("warranty"))
        resolver_order.setdefault("duration", product.get("duration"))

    try:
        warranty_info = resolve_order_warranty_info(resolver_order)
    except (NameError, TypeError, ValueError, KeyError, AttributeError):
        warranty_info = {}

    if not product_id:
        product_id = str(warranty_info.get("product_id") or "").strip()
        if product_id and isinstance(products, dict):
            candidate = products.get(product_id)
            if isinstance(candidate, dict):
                product = candidate

    warranty_text = str(
        warranty_info.get("warranty_text")
        or order.get("warranty")
        or product.get("warranty")
        or ""
    ).strip() or "N/A"

    reason = str(warranty_info.get("reason") or "")
    known = bool(warranty_info.get("known"))
    expired = bool(warranty_info.get("expired"))
    expires_at = warranty_info.get("expires_at")
    expiry_kind = "write"

    if reason == "lifetime_warranty":
        expiry_text = "KhÃ´ng giá»›i háº¡n"
        status_text = "CÃ²n báº£o hÃ nh"
        expiry_kind = "readonly"
    elif reason == "no_warranty":
        expiry_text = "KhÃ´ng báº£o hÃ nh"
        status_text = "KhÃ´ng báº£o hÃ nh"
        expiry_kind = "danger"
    elif expires_at:
        expiry_text = _admin_web_format_timestamp(expires_at)
        status_text = "Háº¿t háº¡n" if expired else "CÃ²n báº£o hÃ nh"
        expiry_kind = "danger" if expired else "readonly"
    elif known:
        expiry_text = "KhÃ´ng xÃ¡c Ä‘á»‹nh"
        status_text = "Theo chÃ­nh sÃ¡ch"
    else:
        expiry_text = "KhÃ´ng xÃ¡c Ä‘á»‹nh"
        status_text = "ChÆ°a rÃµ"

    return (
        _admin_web_summary_card("Báº£o hÃ nh", warranty_text)
        + _admin_web_summary_card("Háº¿t háº¡n BH", expiry_text, expiry_kind)
        + _admin_web_summary_card("Tráº¡ng thÃ¡i BH", status_text, expiry_kind)
    )


def _admin_web_product_detail_body(request, product_id: str, message: str | None = None, is_error: bool = False):
    product = products.get(product_id)
    if not isinstance(product, dict):
        return _admin_web_detail_shell(
            request,
            "product",
            product_id,
            "KhÃ´ng tÃ¬m tháº¥y sáº£n pháº©m",
            _admin_web_summary_card("status", "not found", "danger"),
            "",
            {},
            message=message,
            is_error=True,
        )
    action_url = _admin_web_action_url(request)
    product_type = _admin_web_product_type(product)
    stock_count = _admin_web_stock_count(product)
    pending_count = sum(
        1
        for order in pending_manual_orders.values()
        if isinstance(order, dict) and str(order.get("product_id") or "") == str(product_id)
    )
    sold_count = sum(
        1
        for order in order_history
        if isinstance(order, dict) and str(order.get("product_id") or "") == str(product_id)
    )
    summary = "".join(
        [
            _admin_web_summary_card("Loáº¡i", product_type),
            _admin_web_summary_card("GiÃ¡", _admin_web_money(product.get("price"))),
            _admin_web_summary_card("Stock", stock_count),
            _admin_web_summary_card("Báº£o hÃ nh", product.get("warranty") or "KhÃ´ng"),
            _admin_web_summary_card("Pending manual", pending_count),
            _admin_web_summary_card("Orders", sold_count),
            _admin_web_summary_card("Sync", product.get("ctt_sync_state") or "active"),
        ]
    )
    stock_disabled = "disabled" if product.get("requires_gmail") or product.get("is_supplier_source_resell") or product.get("is_social_source_service") else ""
    category_name = _admin_web_product_category(product)
    image_path = _admin_web_product_image_path(product_id)
    category_image_path = _admin_web_category_image_path(category_name) if category_name else None
    if image_path is not None:
        image_preview_html = (
            f'<img src="{escape(_admin_web_product_image_url(request, product_id), quote=True)}" '
            f'alt="Product image" style="max-width:100%;max-height:280px;border-radius:12px;'
            f'border:1px solid var(--glass-line);background:#0b1220;display:block;margin-bottom:10px;">'
            f'<form method="post" action="{action_url}" class="form-grid" '
            f'data-confirm="XÃ³a áº£nh riÃªng cá»§a sáº£n pháº©m nÃ y?">'
            f'<input type="hidden" name="action" value="product_image_delete">'
            f'{_admin_web_hidden_return("product", product_id)}'
            f'<input type="hidden" name="product_id" value="{escape(product_id, quote=True)}">'
            f'<button class="wide danger" type="submit">XÃ³a áº£nh riÃªng</button>'
            f'</form>'
        )
    else:
        image_preview_html = '<p class="muted" style="margin:0 0 10px;">ChÆ°a cÃ³ áº£nh riÃªng cho sáº£n pháº©m nÃ y.</p>'

    if category_name and category_image_path is not None:
        category_image_preview = (
            f'<p class="muted" style="margin:14px 0 6px;">áº¢nh danh má»¥c <b>{escape(category_name)}</b> '
            f'(Ã¡p dá»¥ng cho má»i sáº£n pháº©m chÆ°a cÃ³ áº£nh riÃªng):</p>'
            f'<img src="{escape(_admin_web_category_image_url(request, category_name), quote=True)}" '
            f'alt="Category image" style="max-width:100%;max-height:200px;border-radius:12px;'
            f'border:1px solid var(--glass-line);background:#0b1220;display:block;margin-bottom:10px;">'
            f'<form method="post" action="{action_url}" class="form-grid" '
            f'data-confirm="XÃ³a áº£nh chung cá»§a danh má»¥c {escape(category_name, quote=True)}?">'
            f'<input type="hidden" name="action" value="category_image_delete">'
            f'{_admin_web_hidden_return("product", product_id)}'
            f'<input type="hidden" name="category_name" value="{escape(category_name, quote=True)}">'
            f'<button class="wide danger" type="submit">XÃ³a áº£nh danh má»¥c</button>'
            f'</form>'
        )
    elif category_name:
        category_image_preview = (
            f'<p class="muted" style="margin:14px 0 6px;">Danh má»¥c <b>{escape(category_name)}</b> '
            f'chÆ°a cÃ³ áº£nh chung. Tick <i>"Ãp dá»¥ng cho cáº£ danh má»¥c"</i> bÃªn dÆ°á»›i Ä‘á»ƒ upload.</p>'
        )
    else:
        category_image_preview = ""

    apply_category_checkbox = (
        f'<label class="wide" style="display:flex;align-items:center;gap:8px;font-weight:600;">'
        f'<input type="checkbox" name="apply_to_category" value="1" style="width:auto;margin:0;"> '
        f'Ãp dá»¥ng cho cáº£ danh má»¥c '
        f'<span class="muted" style="font-weight:400;">(má»i sáº£n pháº©m cÃ¹ng danh má»¥c chÆ°a cÃ³ áº£nh riÃªng sáº½ dÃ¹ng áº£nh nÃ y)</span>'
        f'</label>'
        f'<label class="wide">TÃªn danh má»¥c Ã¡p dá»¥ng '
        f'<span class="muted" style="font-weight:400;">(Ä‘á»ƒ trá»‘ng = dÃ¹ng danh má»¥c hiá»‡n táº¡i cá»§a sáº£n pháº©m)</span>'
        f'<input name="category_name_override" placeholder="VD: AI Tools (GPT, Copilot...)" '
        f'value="{escape(category_name, quote=True)}"></label>'
    )

    # Preview: list of products that share the resolved category, so admin can verify
    # before applying the image at category level (avoids surprises from mis-classification).
    preview_html = ""
    if category_name:
        affected = []
        for pid, prod in products.items():
            if not isinstance(prod, dict):
                continue
            if _admin_web_product_category(prod) != category_name:
                continue
            affected.append((pid, prod))
        affected.sort(key=lambda x: str(x[1].get("name") or x[0]).casefold())

        rows = []
        for pid, prod in affected[:200]:
            has_own_img = _admin_web_product_image_path(pid) is not None
            tag_class = "tag readonly" if has_own_img else "tag write"
            tag_text = "cÃ³ áº£nh riÃªng" if has_own_img else "sáº½ dÃ¹ng áº£nh chung"
            is_self = pid == product_id
            row_style = "background:rgba(99,179,237,0.08);" if is_self else ""
            # Default tick: every product in this category (admin can untick mismatches)
            checkbox_html = (
                f'<input type="checkbox" name="selected_products" value="{escape(pid, quote=True)}" '
                f'class="apply-row-check" checked style="width:auto;margin:0;">'
            )
            self_badge = ' <span class="tag">Ä‘ang xem</span>' if is_self else ''
            short_name = escape(_admin_web_short(str(prod.get("name") or pid), 80))
            row_link = _admin_web_row_link(request, "product", str(pid))
            rows.append(
                f'<tr style="{row_style}">'
                f'<td style="text-align:center;">{checkbox_html}</td>'
                f'<td><code>{escape(pid)}</code>{self_badge}</td>'
                f'<td>{short_name}</td>'
                f'<td><span class="{tag_class}">{tag_text}</span></td>'
                f'<td>{row_link}</td>'
                f'</tr>'
            )
        if not rows:
            rows.append('<tr><td colspan="5" class="muted">ChÆ°a cÃ³ sáº£n pháº©m nÃ o trong danh má»¥c nÃ y.</td></tr>')

        more_note = ""
        if len(affected) > 200:
            more_note = f'<p class="muted" style="margin:6px 0 0;">â€¦ vÃ  {len(affected) - 200} sáº£n pháº©m khÃ¡c (chá»‰ hiá»‡n 200 Ä‘áº§u).</p>'

        # JS for select-all toggle (small inline helper)
        select_helper_js = """
<script>
(function(){
  var box = document.currentScript.previousElementSibling;
  var master = box.querySelector('.apply-master-check');
  var rowChecks = box.querySelectorAll('.apply-row-check');
  if (master) {
    master.addEventListener('change', function(){
      rowChecks.forEach(function(cb){ cb.checked = master.checked; });
    });
  }
})();
</script>
"""

        preview_html = f"""
<details open style="margin-top:14px;background:rgba(255,255,255,0.02);border:1px solid var(--glass-line);border-radius:10px;padding:10px 14px;">
  <summary style="cursor:pointer;font-weight:600;">
    ðŸ” Xem trÆ°á»›c {len(affected)} sáº£n pháº©m trong danh má»¥c <b>{escape(category_name)}</b>
    <span class="muted" style="font-weight:400;">(tick tá»«ng sáº£n pháº©m muá»‘n Ã¡p dá»¥ng áº£nh; bá» tick náº¿u sáº£n pháº©m bá»‹ xáº¿p nháº§m)</span>
  </summary>
  <div class="apply-preview-box">
  <div style="overflow:auto;margin-top:10px;">
    <table class="data-table" style="width:100%;font-size:13px;">
      <thead><tr>
        <th style="width:36px;text-align:center;"><input type="checkbox" class="apply-master-check" checked title="Tick/Bá» tick táº¥t cáº£" style="width:auto;margin:0;"></th>
        <th>Product ID</th><th>TÃªn</th><th>Tráº¡ng thÃ¡i áº£nh</th><th></th>
      </tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
  {more_note}
  <p class="muted" style="margin:8px 0 0;">
    <b>CÃ¡ch Ã¡p dá»¥ng:</b><br>
    â€¢ Tick cÃ¡c sáº£n pháº©m muá»‘n dÃ¹ng <b>chung 1 áº£nh</b> (máº·c Ä‘á»‹nh tick háº¿t) â†’ áº£nh sáº½ Ä‘Æ°á»£c copy cho má»—i sáº£n pháº©m Ä‘Ã£ tick.<br>
    â€¢ Hoáº·c tick checkbox <i>"Ãp dá»¥ng cho cáº£ danh má»¥c"</i> bÃªn dÆ°á»›i â†’ lÆ°u 1 áº£nh dÃ¹ng chung cho cáº£ danh má»¥c (tiáº¿t kiá»‡m dung lÆ°á»£ng, má»i sáº£n pháº©m chÆ°a cÃ³ áº£nh riÃªng tá»± Ä‘á»™ng dÃ¹ng).<br>
    â€¢ Sáº£n pháº©m cÃ³ "áº£nh riÃªng" sáº½ luÃ´n Æ°u tiÃªn áº£nh riÃªng â€” báº¡n cáº§n xÃ³a áº£nh riÃªng trÆ°á»›c náº¿u muá»‘n Ä‘Ã¨.
  </p>
  </div>{select_helper_js}
</details>
"""

    image_upload_url = f"/admin/product_image_upload{_admin_web_key_query(request)}"
    image_section = f"""
<section class="action-card">
  <div class="card-head"><h3>áº¢nh sáº£n pháº©m</h3><span class="tag write">media</span></div>
  {image_preview_html}
  {category_image_preview}
  <form method="post" action="{escape(image_upload_url, quote=True)}" enctype="multipart/form-data" class="form-grid">
    <input type="hidden" name="product_id" value="{escape(product_id, quote=True)}">
    <label class="wide">Chá»n áº£nh (jpg/png/webp, â‰¤ 8MB)
      <input type="file" name="image" accept="image/jpeg,image/png,image/webp" required id="img-file-input">
    </label>
    <div id="img-preview-wrap" style="display:none;margin:6px 0 10px;">
      <img id="img-preview-thumb" src="" alt="Preview"
        style="max-width:100%;max-height:240px;border-radius:10px;border:1px solid var(--glass-line);background:#0b1220;display:block;">
      <p id="img-preview-info" class="muted" style="margin:4px 0 0;font-size:12px;"></p>
    </div>
    <script>
    (function(){{
      var inp = document.getElementById('img-file-input');
      var wrap = document.getElementById('img-preview-wrap');
      var thumb = document.getElementById('img-preview-thumb');
      var info = document.getElementById('img-preview-info');
      if (!inp) return;
      inp.addEventListener('change', function(){{
        var f = inp.files && inp.files[0];
        if (!f) {{ wrap.style.display='none'; return; }}
        var url = URL.createObjectURL(f);
        thumb.onload = function(){{ URL.revokeObjectURL(url); }};
        thumb.src = url;
        info.textContent = f.name + ' â€” ' + (f.size/1024).toFixed(1) + ' KB';
        wrap.style.display = 'block';
      }});
    }})();
    </script>
    {preview_html}
    {apply_category_checkbox}
    <button class="wide" type="submit">Táº£i lÃªn / Thay áº£nh</button>
  </form>
</section>
"""
    main = f"""
{image_section}
<section class="action-card">
  <div class="card-head"><h3>Sá»­a sáº£n pháº©m</h3><span class="tag write">editable</span></div>
  <form method="post" action="{action_url}" class="form-grid">
    <input type="hidden" name="action" value="product_update">
    {_admin_web_hidden_return("product", product_id)}
    <label>Product ID<input name="product_id" value="{escape(product_id, quote=True)}" readonly></label>
    <label>GiÃ¡ bÃ¡n<input name="price" value="{escape(str(product.get('price') or ''), quote=True)}"></label>
    <label>GiÃ¡ vá»‘n<input name="cost_price" value="{escape(str(product.get('cost_price') if product.get('cost_price') is not None else ''), quote=True)}" placeholder="Local/manual"></label>
    <label class="wide">TÃªn<input name="name" value="{escape(str(product.get('name') or ''), quote=True)}"></label>
    <label class="wide">Danh má»¥c (store_category) <span class="muted" style="font-weight:400;">(Ä‘á»ƒ trá»‘ng = giá»¯ nguyÃªn)</span><input name="store_category" placeholder="VD: AI Tools (GPT, Copilot...)" value="{escape(str(product.get('store_category') or ''), quote=True)}"></label>
    <label>Thá»i háº¡n<input name="duration" value="{escape(str(product.get('duration') or ''), quote=True)}"></label>
    <label>Báº£o hÃ nh<input name="warranty" value="{escape(str(product.get('warranty') or ''), quote=True)}" placeholder="VD: 7 ngÃ y, 30 ngÃ y, KhÃ´ng"></label>
    <label>Giá»›i háº¡n manual<input name="max_pending_orders" value="{escape(str(product.get('max_pending_orders') or ''), quote=True)}"></label>
    <label class="wide">MÃ´ táº£<textarea name="description">{escape(str(product.get('description') or ''))}</textarea></label>
    <label class="wide">ThÃªm stock local<textarea name="stock_items" {stock_disabled} placeholder="Má»—i dÃ²ng 1 item"></textarea></label>
    <button class="wide" type="submit">LÆ°u thay Ä‘á»•i</button>
  </form>
</section>
<section class="action-card">
  <div class="card-head"><h3>XÃ³a sáº£n pháº©m</h3><span class="tag danger">danger</span></div>
  <form method="post" action="{action_url}" class="form-grid" data-confirm="XÃ³a vÄ©nh viá»…n sáº£n pháº©m nÃ y khá»i catalog? ÄÆ¡n hÃ ng cÅ© sáº½ váº«n giá»¯ trong lá»‹ch sá»­.">
    <input type="hidden" name="action" value="product_delete">
    <input type="hidden" name="product_id" value="{escape(product_id, quote=True)}">
    <button class="wide danger" type="submit">XÃ³a sáº£n pháº©m</button>
  </form>
</section>
<section class="action-card">
  <div class="card-head"><h3>Stock local</h3><span class="tag danger">careful</span></div>
  <form method="post" action="{action_url}" class="form-grid" data-confirm="XÃ³a toÃ n bá»™ stock local cá»§a sáº£n pháº©m nÃ y?">
    <input type="hidden" name="action" value="product_stock">
    {_admin_web_hidden_return("product", product_id)}
    <input type="hidden" name="product_id" value="{escape(product_id, quote=True)}">
    <input type="hidden" name="mode" value="clear_stock">
    <button class="wide danger" type="submit" {stock_disabled}>XÃ³a toÃ n bá»™ stock local</button>
  </form>
</section>
"""
    return _admin_web_detail_shell(
        request,
        "product",
        product_id,
        str(product.get("name") or product_id),
        summary,
        main,
        product,
        message=message,
        is_error=is_error,
    )


def _admin_web_user_detail_body(request, user_id: str, message: str | None = None, is_error: bool = False):
    profile = user_data_db.get(str(user_id))
    if not isinstance(profile, dict):
        profile = {}
    banned = str(user_id).isdigit() and int(str(user_id)) in banned_users
    orders_count = sum(1 for order in order_history if isinstance(order, dict) and str(order.get("user_id") or "") == str(user_id))
    summary = "".join(
        [
            _admin_web_summary_card("Sá»‘ dÆ°", _admin_web_money(profile.get("balance"))),
            _admin_web_summary_card("Orders", orders_count),
            _admin_web_summary_card("Status", "ban" if banned else "active", "danger" if banned else "readonly"),
            _admin_web_summary_card("Spent", _admin_web_money(profile.get("total_spent") or profile.get("spent") or 0)),
        ]
    )
    action_url = _admin_web_action_url(request)
    main = f"""
<section class="action-card">
  <div class="card-head"><h3>Há»“ sÆ¡ user</h3><span class="tag write">profile</span></div>
  <form method="post" action="{action_url}" class="form-grid">
    <input type="hidden" name="action" value="user_profile">
    {_admin_web_hidden_return("user", user_id)}
    <label>User ID<input name="user_id" value="{escape(str(user_id), quote=True)}" readonly></label>
    <label>Username<input name="username" value="{escape(str(profile.get('username') or ''), quote=True)}"></label>
    <label class="wide">TÃªn<input name="full_name" value="{escape(str(profile.get('full_name') or profile.get('first_name') or ''), quote=True)}"></label>
    <label>Email<input name="email" value="{escape(str(profile.get('email') or ''), quote=True)}"></label>
    <label>Ghi chÃº<input name="admin_note" value="{escape(str(profile.get('admin_note') or ''), quote=True)}"></label>
    <button class="wide" type="submit">LÆ°u há»“ sÆ¡</button>
  </form>
</section>
<section class="action-card">
  <div class="card-head"><h3>VÃ­ & ban</h3><span class="tag danger">money</span></div>
  <form method="post" action="{action_url}" class="form-grid">
    <input type="hidden" name="action" value="user_balance">
    {_admin_web_hidden_return("user", user_id)}
    <label>User ID<input name="user_id" value="{escape(str(user_id), quote=True)}" readonly></label>
    <label>Sá»‘ tiá»n<input name="amount" placeholder="100000"></label>
    <label>Kiá»ƒu<select name="mode"><option value="add">Cá»™ng</option><option value="sub">Trá»«</option><option value="set">Set</option></select></label>
    <label>LÃ½ do<input name="reason" value="Admin web detail"></label>
    <button class="wide" type="submit">Cáº­p nháº­t vÃ­</button>
  </form>
  <form method="post" action="{action_url}" class="form-grid" data-confirm="Cáº­p nháº­t ban/unban user nÃ y?">
    <input type="hidden" name="action" value="user_ban">
    {_admin_web_hidden_return("user", user_id)}
    <input type="hidden" name="user_id" value="{escape(str(user_id), quote=True)}">
    <label class="wide">Tráº¡ng thÃ¡i<select name="mode"><option value="ban">Ban</option><option value="unban">Unban</option></select></label>
    <button class="wide danger" type="submit">Ban / unban</button>
  </form>
</section>
<section class="module-section">
  <div class="section-head"><div><h2>ÄÆ¡n hÃ ng cá»§a user</h2></div></div>
  {_admin_web_recent_order_table_for_user(request, str(user_id))}
</section>
"""
    title = str(profile.get("full_name") or profile.get("first_name") or profile.get("username") or user_id)
    return _admin_web_detail_shell(request, "user", str(user_id), title, summary, main, profile, message=message, is_error=is_error)


def _admin_web_order_detail_body(request, order_code: str, message: str | None = None, is_error: bool = False):
    records = _admin_web_find_order_records(order_code)
    primary = records[0][1] if records else {}
    if not isinstance(primary, dict):
        primary = {}
    action_url = _admin_web_action_url(request)
    summary = "".join(
        [
            _admin_web_summary_card("Records", len(records)),
            _admin_web_summary_card("Tiá»n", _admin_web_money(primary.get("amount"))),
            _admin_web_summary_card("Status", primary.get("status") or "N/A"),
            _admin_web_summary_card("User", primary.get("user_id") or ""),
            _admin_web_order_warranty_summary_cards(primary),
        ]
    )
    raw_payload = {"matches": [{"table": table, "record": record} for table, record in records]}
    main = f"""
<section class="action-card">
  <div class="card-head"><h3>CÃ´ng cá»¥ Ä‘Æ¡n hÃ ng</h3><span class="tag write">order</span></div>
  <form method="post" action="{action_url}" class="form-grid">
    <input type="hidden" name="action" value="order_tools">
    {_admin_web_hidden_return("order", order_code)}
    <label>MÃ£ Ä‘Æ¡n<input name="order_code" value="{escape(str(order_code), quote=True)}" readonly></label>
    <label>Thao tÃ¡c<select name="mode"><option value="set_email">Gáº¯n email</option><option value="admin_note">Ghi chÃº admin</option></select></label>
    <label class="wide">GiÃ¡ trá»‹<input name="value" value="{escape(str(primary.get('email') or primary.get('customer_email') or primary.get('admin_note') or ''), quote=True)}"></label>
    <button class="wide" type="submit">Cáº­p nháº­t Ä‘Æ¡n</button>
  </form>
</section>
"""
    return _admin_web_detail_shell(request, "order", str(order_code), f"Order {order_code}", summary, main, raw_payload, message=message, is_error=is_error)


def _admin_web_api_traffic_chart(analytics: dict) -> str:
    daily = list((analytics or {}).get("daily") or [])
    if not daily:
        return '<div class="api-empty-state">ChÆ°a cÃ³ request trong 14 ngÃ y.</div>'
    maximum = max(1, max(int(item.get("requests") or 0) for item in daily))
    bars = []
    for item in daily:
        total = int(item.get("requests") or 0)
        errors = int(item.get("errors") or 0)
        height = max(4, round(total * 100 / maximum))
        error_height = round(errors * 100 / max(1, total))
        bars.append(
            f'<div class="api-chart-column" title="{escape(str(item.get("day")))}: {total} request, {errors} lá»—i">'
            f'<div class="api-chart-bar" style="height:{height}%"><i style="height:{error_height}%"></i></div>'
            f'<small>{escape(str(item.get("day") or "")[-5:])}</small></div>'
        )
    return f'<div class="api-traffic-chart">{"".join(bars)}</div>'


def _admin_web_api_log_rows(fingerprint: str) -> str:
    rows = []
    for item in db_api_recent_logs(fingerprint, 80):
        status = int(item.get("status_code") or 0)
        rows.append(
            "<tr>"
            f'<td>{escape(_admin_web_format_timestamp(item.get("requested_at")))}</td>'
            f'<td><code>{escape(str(item.get("method") or ""))}</code></td>'
            f'<td><code>{escape(str(item.get("endpoint") or ""))}</code></td>'
            f'<td><span class="tag {"danger" if status >= 400 else "readonly"}">{status}</span></td>'
            f'<td>{float(item.get("response_ms") or 0):.1f} ms</td>'
            f'<td><code>{escape(str(item.get("client_ip") or ""))}</code></td>'
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='6' class='muted'>ChÆ°a cÃ³ access log.</td></tr>"


def _admin_web_api_ledger_rows(fingerprint: str) -> str:
    rows = []
    for item in db_api_partner_ledger(fingerprint, limit=100):
        amount = int(item.get("amount") or 0)
        entry_type = str(item.get("entry_type") or "adjustment")
        rows.append(
            f'<tr><td>{escape(_admin_web_format_timestamp(item.get("created_at")))}</td>'
            f'<td><span class="ledger-pill {escape(entry_type)}">{escape(entry_type.title())}</span></td>'
            f'<td class="{"money-positive" if amount > 0 else "money-negative"}">{amount:+,}Ä‘</td>'
            f'<td>{int(item.get("balance_after") or 0):,}Ä‘</td>'
            f'<td><code>{escape(str(item.get("reference") or "â€”"))}</code></td>'
            f'<td>{escape(_admin_web_short(item.get("reason") or "", 72))}</td></tr>'
        )
    return "".join(rows) or "<tr><td colspan='6' class='muted'>ChÆ°a cÃ³ giao dá»‹ch trong ledger má»›i.</td></tr>"


def _admin_web_api_detail_body(request, api_key: str, message: str | None = None, is_error: bool = False):
    resolved_api_key = _admin_web_find_api_key(api_key) or api_key
    api_key = resolved_api_key
    data = api_keys.get(api_key)
    normalized = data if isinstance(data, dict) else {"name": str(data), "balance": 0}
    action_url = _admin_web_action_url(request)
    api_public_id = _admin_web_api_public_id(str(api_key))
    fingerprint = _api_key_fingerprint(str(api_key))
    balance = _admin_web_int(normalized.get("balance"), 0)
    analytics = db_api_analytics(fingerprint, 14)
    allowed_ips = "\n".join(_api_normalize_allowed_ips(normalized.get("allowed_ips") or []))
    rate_limit = _api_partner_rate_limit(normalized)
    alert_threshold = max(0, _admin_web_int(normalized.get("low_balance_threshold"), 100000))
    alert_enabled = normalized.get("low_balance_alert_enabled") is not False
    tier = _api_partner_tier(str(api_key), normalized)
    ledger = db_api_partner_ledger_summary(fingerprint)
    summary = "".join([
        _admin_web_summary_card("Sá»‘ dÆ°", _admin_web_money(balance)),
        _admin_web_summary_card("Tier", f'{tier["name"]} Â· -{tier["discount_percent"]}%'),
        _admin_web_summary_card("Sáº£n lÆ°á»£ng thÃ¡ng", _admin_web_money(tier["monthly_volume"])),
        _admin_web_summary_card("Usage ledger", _admin_web_money(abs(ledger["usage"]))),
        _admin_web_summary_card("Refund", _admin_web_money(ledger["refund"])),
        _admin_web_summary_card("Requests 14 ngÃ y", analytics.get("total", 0)),
        _admin_web_summary_card("Tá»· lá»‡ lá»—i", f'{analytics.get("error_rate", 0)}%'),
        _admin_web_summary_card("Latency TB", f'{analytics.get("avg_ms", 0)} ms'),
        _admin_web_summary_card("Quota", f"{rate_limit}/phÃºt"),
    ])
    warning = '<div class="alert error">Sá»‘ dÆ° vÆ°á»£t ngÆ°á»¡ng kiá»ƒm tra. HÃ£y Ä‘á»‘i soÃ¡t trÆ°á»›c khi báº­t láº¡i key.</div>' if abs(balance) >= ADMIN_WEB_SUSPICIOUS_BALANCE_THRESHOLD else ""
    main = f"""
{warning}
<div class="api-detail-grid">
  <section class="action-card api-security-card">
    <div class="card-head"><h3>Security & Control</h3><span class="tag api">{escape(api_public_id)}</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="api_partner"><input type="hidden" name="mode" value="configure">
      {_admin_web_hidden_return("api", api_public_id)}<input type="hidden" name="target" value="{escape(api_public_id, quote=True)}">
      <label class="wide">IP whitelist <textarea name="allowed_ips" placeholder="203.0.113.10&#10;2001:db8::/48">{escape(allowed_ips)}</textarea><small>IPv4, IPv6 hoáº·c CIDR; Ä‘á»ƒ trá»‘ng cho phÃ©p má»i IP.</small></label>
      <label>Quota/phÃºt<input name="rate_limit" type="number" min="1" max="10000" value="{rate_limit}"></label>
      <label>NgÆ°á»¡ng cáº£nh bÃ¡o<input name="low_balance_threshold" type="number" min="0" value="{alert_threshold}"></label>
      <label class="toggle-field"><input type="checkbox" name="alert_enabled" value="1" {'checked' if alert_enabled else ''}><span class="switch"></span>Cáº£nh bÃ¡o Telegram</label>
      <label class="wide">Ghi chÃº admin<input name="admin_note" value="{escape(str(normalized.get('admin_note') or ''), quote=True)}"></label>
      <label>Cháº¿ Ä‘á»™ cáº¥p báº­c<select name="tier_mode"><option value="auto" {'selected' if tier['mode'] == 'auto' else ''}>Tá»± Ä‘á»™ng theo doanh sá»‘ thÃ¡ng</option><option value="manual" {'selected' if tier['mode'] == 'manual' else ''}>Admin chá»‰ Ä‘á»‹nh</option></select></label>
      <label>Cáº¥p báº­c API<select name="tier_override">{''.join(f'<option value="{item["id"]}" {"selected" if item["id"] == tier["id"] else ""}>{item["name"]} â€” giáº£m {item["discount_percent"]}%</option>' for item in API_PARTNER_TIERS)}</select></label>
      <div class="wide tier-progress"><b>{tier['name']} Â· giáº£m {tier['discount_percent']}%</b><small>Doanh sá»‘ thÃ¡ng: {tier['monthly_volume']:,}Ä‘</small>{f'<small>CÃ²n {tier["remaining_to_next"]:,}Ä‘ Ä‘á»ƒ lÃªn {tier["next_tier"]["name"]}</small>' if tier['next_tier'] else '<small>ÄÃ£ Ä‘áº¡t cáº¥p cao nháº¥t</small>'}</div>
      <button class="wide" type="submit">LÆ°u báº£o máº­t & cáº¥p báº­c</button>
    </form>
  </section>
  <section class="action-card api-wallet-card">
    <div class="card-head"><h3>VÃ­ & vÃ²ng Ä‘á»i key</h3><span class="tag {'readonly' if normalized.get('enabled') is not False else 'danger'}">{'ON' if normalized.get('enabled') is not False else 'REVOKED'}</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="api_partner">{_admin_web_hidden_return("api", api_public_id)}
      <input type="hidden" name="target" value="{escape(api_public_id, quote=True)}">
      <label>Thao tÃ¡c<select name="mode"><option value="topup">Cá»™ng</option><option value="subtract">Trá»«</option><option value="set_balance">Set sá»‘ dÆ°</option><option value="enable">Báº­t key</option></select></label>
      <label>Sá»‘ tiá»n<input name="amount" type="number" min="0" placeholder="500000"></label>
      <button class="wide" type="submit">Cáº­p nháº­t partner</button>
    </form>
    <div class="danger-zone">
      <form method="post" action="{action_url}" data-confirm="Thu há»“i key nÃ y ngay láº­p tá»©c?">
        <input type="hidden" name="action" value="api_partner"><input type="hidden" name="mode" value="revoke"><input type="hidden" name="target" value="{escape(api_public_id, quote=True)}">{_admin_web_hidden_return("api", api_public_id)}
        <button class="danger" type="submit">Thu há»“i key</button>
      </form>
      <form method="post" action="{action_url}" data-confirm="Táº¡o key má»›i vÃ  vÃ´ hiá»‡u key hiá»‡n táº¡i?">
        <input type="hidden" name="action" value="api_partner"><input type="hidden" name="mode" value="regenerate"><input type="hidden" name="target" value="{escape(api_public_id, quote=True)}">
        <button type="submit">Regenerate key</button>
      </form>
    </div>
  </section>
</div>
<section class="module-section ledger-panel"><div class="section-head"><div><h2>Sao kÃª dÃ²ng tiá»n</h2><p>Deposit, Usage vÃ  Refund tÃ¡ch báº¡ch; má»—i dÃ²ng cÃ³ running balance.</p></div><div class="ledger-summary"><span>Deposit <b class="money-positive">+{ledger['deposit']:,}Ä‘</b></span><span>Usage <b class="money-negative">{ledger['usage']:,}Ä‘</b></span><span>Refund <b class="money-positive">+{ledger['refund']:,}Ä‘</b></span></div></div><div class="table-scroll"><table class="data-table api-ledger-table"><thead><tr><th>Thá»i gian</th><th>Loáº¡i</th><th>Biáº¿n Ä‘á»™ng</th><th>Sá»‘ dÆ° sau</th><th>Tham chiáº¿u</th><th>Ná»™i dung</th></tr></thead><tbody>{_admin_web_api_ledger_rows(fingerprint)}</tbody></table></div></section>
<section class="module-section api-chart-panel"><div class="section-head"><div><h2>LÆ°u lÆ°á»£ng 14 ngÃ y</h2><p>Lá»—i HTTP hiá»ƒn thá»‹ báº±ng pháº§n Ä‘á» trong má»—i cá»™t.</p></div></div>{_admin_web_api_traffic_chart(analytics)}</section>
<section class="module-section"><div class="section-head"><div><h2>Access logs</h2><p>Tá»‘i Ä‘a 80 request gáº§n nháº¥t; khÃ´ng lÆ°u key, body hoáº·c query string.</p></div></div><div class="table-scroll"><table class="data-table api-log-table"><thead><tr><th>Thá»i gian</th><th>Method</th><th>Endpoint</th><th>Status</th><th>Latency</th><th>IP</th></tr></thead><tbody>{_admin_web_api_log_rows(fingerprint)}</tbody></table></div></section>
"""
    safe_raw = dict(normalized)
    safe_raw.pop("rotated_to", None)
    return _admin_web_detail_shell(request, "api", api_public_id, str(normalized.get("name") or api_public_id), summary, main, safe_raw, message=message, is_error=is_error)


def _admin_web_coupon_detail_body(request, code: str, message: str | None = None, is_error: bool = False):
    data = coupons.get(code) if isinstance(coupons, dict) else None
    item = data if isinstance(data, dict) else {}
    action_url = _admin_web_action_url(request)
    summary = "".join(
        [
            _admin_web_summary_card("Giáº£m", _admin_web_money(item.get("discount"))),
            _admin_web_summary_card("Used", f"{item.get('used', 0)} / {item.get('quantity', 0)}"),
            _admin_web_summary_card("Háº¿t háº¡n", item.get("expires") or "N/A"),
        ]
    )
    main = f"""
<section class="action-card">
  <div class="card-head"><h3>Coupon</h3><span class="tag write">promo</span></div>
  <form method="post" action="{action_url}" class="form-grid">
    <input type="hidden" name="action" value="coupon">
    {_admin_web_hidden_return("coupon", code)}
    <label>Thao tÃ¡c<select name="mode"><option value="add">Cáº­p nháº­t</option><option value="delete">XÃ³a</option></select></label>
    <label>Code<input name="code" value="{escape(str(code), quote=True)}" readonly></label>
    <label>Sá»‘ lÆ°á»£ng<input name="quantity" value="{escape(str(item.get('quantity') or ''), quote=True)}"></label>
    <label>Giáº£m tiá»n<input name="discount" value="{escape(str(item.get('discount') or ''), quote=True)}"></label>
    <label class="wide">Sá»‘ ngÃ y háº¿t háº¡n má»›i<input name="days" placeholder="30"></label>
    <button class="wide" type="submit">LÆ°u coupon</button>
  </form>
</section>
"""
    return _admin_web_detail_shell(request, "coupon", code, f"Coupon {code}", summary, main, item, message=message, is_error=is_error)


def _admin_web_support_detail_body(request, entity: str, item_id: str, message: str | None = None, is_error: bool = False):
    source_map = {
        "live_chat": (live_chats, LIVE_CHATS_FILE),
        "warranty": (warranty_claims, WARRANTY_CLAIMS_FILE),
        "withdrawal": (withdrawal_requests, WITHDRAWALS_FILE),
    }
    data, _table = source_map.get(entity, ({}, ""))
    item = _admin_web_mapping_get(data, item_id)
    record = item if isinstance(item, dict) else {}
    action_url = _admin_web_action_url(request)
    summary = "".join(
        [
            _admin_web_summary_card("Loáº¡i", entity),
            _admin_web_summary_card("Status", record.get("status") or "pending"),
            _admin_web_summary_card("User", record.get("user_id") or item_id),
            _admin_web_summary_card("Order", record.get("order_code") or ""),
        ]
    )
    main = f"""
<section class="action-card">
  <div class="card-head"><h3>Cáº­p nháº­t ticket</h3><span class="tag write">support</span></div>
  <form method="post" action="{action_url}" class="form-grid">
    <input type="hidden" name="action" value="support_update">
    {_admin_web_hidden_return(entity, item_id)}
    <input type="hidden" name="entity" value="{escape(entity, quote=True)}">
    <input type="hidden" name="item_id" value="{escape(item_id, quote=True)}">
    <label>Status<select name="status"><option value="pending">pending</option><option value="active">active</option><option value="resolved">resolved</option><option value="closed">closed</option><option value="rejected">rejected</option></select></label>
    <label>Ghi chÃº<input name="admin_note" value="{escape(str(record.get('admin_note') or ''), quote=True)}"></label>
    <button class="wide" type="submit">Cáº­p nháº­t ticket</button>
  </form>
</section>
"""
    return _admin_web_detail_shell(request, entity, item_id, f"{entity} {item_id}", summary, main, record, message=message, is_error=is_error)


def _admin_web_detail_body(request, entity: str, item_id: str, message: str | None = None, is_error: bool = False) -> str:
    entity = str(entity or "").strip()
    item_id = str(item_id or "").strip()
    if entity == "product":
        return _admin_web_product_detail_body(request, item_id, message, is_error)
    if entity == "user":
        return _admin_web_user_detail_body(request, item_id, message, is_error)
    if entity == "order":
        return _admin_web_order_detail_body(request, item_id, message, is_error)
    if entity == "api":
        return _admin_web_api_detail_body(request, item_id, message, is_error)
    if entity == "coupon":
        return _admin_web_coupon_detail_body(request, item_id, message, is_error)
    if entity in {"live_chat", "warranty", "withdrawal"}:
        return _admin_web_support_detail_body(request, entity, item_id, message, is_error)
    return _admin_web_detail_shell(
        request,
        entity or "unknown",
        item_id or "unknown",
        "Khong ho tro object nay",
        _admin_web_summary_card("status", "unsupported", "danger"),
        "",
        {},
        message=message,
        is_error=True,
    )


def _admin_web_action_cards(request) -> str:
    action_url = _admin_web_action_url(request)
    return f"""
<div class="action-stack action-board">
  <div class="action-column">
    <div class="action-group-label">User & vÃ­ <span>money / profile / risk</span></div>
  <section class="action-card is-wallet">
    <div class="card-head"><h3>VÃ­ user</h3><span class="tag danger">money</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="user_balance">
      <label>User ID<input name="user_id" placeholder="123456789" required></label>
      <label>Sá»‘ tiá»n<input name="amount" placeholder="100000" required></label>
      <label>Kiá»ƒu
        <select name="mode">
          <option value="add">Cá»™ng tiá»n</option>
          <option value="sub">Trá»« tiá»n</option>
          <option value="set">Set sá»‘ dÆ°</option>
        </select>
      </label>
      <label class="wide">LÃ½ do<input name="reason" value="Admin web"></label>
      <button class="wide" type="submit">Thá»±c hiá»‡n</button>
    </form>
  </section>
  <section class="action-card">
    <div class="card-head"><h3>Há»“ sÆ¡ user</h3><span class="tag write">profile</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="user_profile">
      <label>User ID<input name="user_id" placeholder="123456789" required></label>
      <label>Username<input name="username" placeholder="@username"></label>
      <label class="wide">TÃªn hiá»ƒn thá»‹<input name="full_name" placeholder="TÃªn khÃ¡ch"></label>
      <label class="wide">Email<input name="email" placeholder="email nháº­n hÃ ng"></label>
      <label class="wide">Ghi chÃº admin<textarea name="admin_note" placeholder="Ghi chÃº ná»™i bá»™"></textarea></label>
      <button class="wide" type="submit">LÆ°u há»“ sÆ¡</button>
    </form>
  </section>
  <section class="action-card is-critical">
    <div class="card-head"><h3>Ban / unban</h3><span class="tag danger">risk</span></div>
  <form method="post" action="{action_url}" class="form-grid" data-confirm="Cáº­p nháº­t tráº¡ng thÃ¡i ban user?">
      <input type="hidden" name="action" value="user_ban">
      <label>User ID<input name="user_id" required></label>
      <label>Trang thai
        <select name="mode"><option value="ban">Ban</option><option value="unban">Unban</option></select>
      </label>
      <button class="wide danger" type="submit">Cáº­p nháº­t user</button>
    </form>
  </section>
  </div>
  <div class="action-column action-column-catalog">
    <div class="action-group-label">Catalog <span>products</span></div>
  <section class="action-card is-catalog">
    <div class="card-head"><h3>Sáº£n pháº©m</h3><span class="tag write">catalog</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="product_update">
      <label>Product ID<input name="product_id" required></label>
      <label>GiÃ¡ bÃ¡n má»›i<input name="price" placeholder="bá» trá»‘ng náº¿u khÃ´ng Ä‘á»•i"></label>
      <label>GiÃ¡ vá»‘n má»›i<input name="cost_price" placeholder="local/manual"></label>
      <label class="wide">TÃªn má»›i<input name="name" placeholder="bá» trá»‘ng náº¿u khÃ´ng Ä‘á»•i"></label>
      <label class="wide">Danh má»¥c<input name="store_category" placeholder="vd: Streaming, Social, Tools"></label>
      <label>Thá»i háº¡n<input name="duration" placeholder="vd: 30 ngÃ y"></label>
      <label>Báº£o hÃ nh<input name="warranty" placeholder="vd: 7 ngÃ y, 30 ngÃ y"></label>
      <label>Giá»›i háº¡n manual<input name="max_pending_orders" placeholder="vd: 10"></label>
      <label class="wide">MÃ´ táº£<textarea name="description" placeholder="bá» trá»‘ng náº¿u khÃ´ng Ä‘á»•i"></textarea></label>
      <label class="wide">ThÃªm stock local<textarea name="stock_items" placeholder="Má»—i dÃ²ng 1 item, chá»‰ nÃªn dÃ¹ng vá»›i sáº£n pháº©m local stock"></textarea></label>
      <button class="wide" type="submit">LÆ°u sáº£n pháº©m</button>
    </form>
  </section>
  <section class="action-card is-catalog">
    <div class="card-head"><h3>Táº¡o sáº£n pháº©m</h3><span class="tag write">new</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="product_create">
      <label>Product ID<input name="product_id" placeholder="bá» trá»‘ng Ä‘á»ƒ tá»± táº¡o"></label>
      <label>GiÃ¡ bÃ¡n<input name="price" placeholder="35000" required></label>
      <label>GiÃ¡ vá»‘n<input name="cost_price" placeholder="báº¯t buá»™c Ä‘á»ƒ tÃ­nh lÃ£i" required></label>
      <label class="wide">TÃªn<input name="name" placeholder="TÃªn sáº£n pháº©m" required></label>
      <label>Loáº¡i<select name="requires_gmail"><option value="0">Local stock</option><option value="1">Manual/Gmail</option></select></label>
      <label>Thá»i háº¡n<input name="duration" placeholder="30 ngÃ y"></label>
      <label>Báº£o hÃ nh<input name="warranty" placeholder="7 ngÃ y, 30 ngÃ y, KhÃ´ng"></label>
      <label class="wide">MÃ´ táº£<textarea name="description" placeholder="MÃ´ táº£ ngáº¯n"></textarea></label>
      <label class="wide">Stock ban Ä‘áº§u<textarea name="stock_items" placeholder="Má»—i dÃ²ng 1 item, chá»‰ dÃ¹ng vá»›i local stock"></textarea></label>
      <button class="wide" type="submit">Táº¡o sáº£n pháº©m</button>
    </form>
  </section>
  <section class="action-card is-critical">
    <div class="card-head"><h3>Kho sáº£n pháº©m</h3><span class="tag danger">stock</span></div>
    <form method="post" action="{action_url}" class="form-grid" data-confirm="XÃ³a toÃ n bá»™ stock local cá»§a sáº£n pháº©m nÃ y?">
      <input type="hidden" name="action" value="product_stock">
      <input type="hidden" name="mode" value="clear_stock">
      <label class="wide">Product ID<input name="product_id" placeholder="product_id local stock" required></label>
      <button class="wide danger" type="submit">XÃ³a stock local</button>
    </form>
    <form method="post" action="{action_url}" class="form-grid" data-confirm="XÃ³a vÄ©nh viá»…n sáº£n pháº©m khá»i catalog?">
      <input type="hidden" name="action" value="product_delete">
      <label class="wide">Product ID<input name="product_id" placeholder="product_id cáº§n xÃ³a" required></label>
      <button class="wide danger" type="submit">XÃ³a sáº£n pháº©m</button>
    </form>
  </section>
  </div>
  <div class="action-column">
    <div class="action-group-label">Váº­n hÃ nh <span>api / orders / support</span></div>
  <section class="action-card">
    <div class="card-head"><h3>API partner</h3><span class="tag write">partner</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="api_partner">
      <label>Thao tÃ¡c
        <select name="mode"><option value="topup">Náº¡p tiá»n key</option><option value="create">Táº¡o key</option><option value="disable">Táº¯t key</option><option value="enable">Báº­t key</option></select>
      </label>
      <label>Sá»‘ tiá»n<input name="amount" placeholder="500000"></label>
      <label class="wide">Key hoáº·c tÃªn partner<input name="target" placeholder="DINO... hoáº·c tÃªn"></label>
      <button class="wide" type="submit">Cáº­p nháº­t API</button>
    </form>
  </section>
  <section class="action-card">
    <div class="card-head"><h3>ÄÆ¡n hÃ ng</h3><span class="tag write">orders</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="order_tools">
      <label>MÃ£ Ä‘Æ¡n<input name="order_code" placeholder="ICLD123456" required></label>
      <label>Thao tÃ¡c
        <select name="mode"><option value="set_email">Gáº¯n email</option><option value="admin_note">Ghi chÃº admin</option></select>
      </label>
      <label class="wide">GiÃ¡ trá»‹<input name="value" placeholder="email hoáº·c ghi chÃº"></label>
      <button class="wide" type="submit">Cáº­p nháº­t Ä‘Æ¡n</button>
    </form>
  </section>
  <section class="action-card">
    <div class="card-head"><h3>Kho link legacy</h3><span class="tag write">legacy</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="legacy_link">
      <label>Thao tÃ¡c
        <select name="mode"><option value="replace">Thay link Ä‘ang dÃ¹ng</option><option value="add">ThÃªm link</option><option value="delete">XÃ³a link</option><option value="clear">XÃ³a toÃ n bá»™</option></select>
      </label>
      <label class="wide">Link<textarea name="link" placeholder="DÃ¡n link legacy, má»—i dÃ²ng 1 link náº¿u thÃªm nhiá»u"></textarea></label>
      <button class="wide" type="submit">Cáº­p nháº­t kho link</button>
    </form>
  </section>
  <section class="action-card">
    <div class="card-head"><h3>Coupon</h3><span class="tag write">promo</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="coupon">
      <label>Thao tÃ¡c
        <select name="mode"><option value="add">ThÃªm / cáº­p nháº­t</option><option value="delete">XÃ³a coupon</option></select>
      </label>
      <label>Ma coupon<input name="code" placeholder="SALE2026" required></label>
      <label>Sá»‘ lÆ°á»£ng<input name="quantity" placeholder="100"></label>
      <label>Giáº£m tiá»n<input name="discount" placeholder="35000"></label>
      <label class="wide">Sá»‘ ngÃ y háº¿t háº¡n<input name="days" placeholder="30"></label>
      <button class="wide" type="submit">LÆ°u coupon</button>
    </form>
  </section>
  <section class="action-card">
    <div class="card-head"><h3>Support ticket</h3><span class="tag write">support</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="support_update">
      <label>Loáº¡i
        <select name="entity"><option value="live_chat">Live chat</option><option value="warranty">Báº£o hÃ nh</option><option value="withdrawal">RÃºt tiá»n</option></select>
      </label>
      <label>ID ticket<input name="item_id" placeholder="ticket/order id" required></label>
      <label>Status<input name="status" placeholder="pending / resolved / rejected"></label>
      <label class="wide">Ghi chÃº<textarea name="admin_note" placeholder="Ghi chÃº xá»­ lÃ½"></textarea></label>
      <button class="wide" type="submit">Cáº­p nháº­t support</button>
    </form>
  </section>
  <section class="action-card is-critical">
    <div class="card-head"><h3>Há»‡ thá»‘ng</h3><span class="tag danger">ops</span></div>
    <form method="post" action="{action_url}" class="form-grid" data-confirm="Cáº­p nháº­t tráº¡ng thÃ¡i há»‡ thá»‘ng?">
      <input type="hidden" name="action" value="system_toggle">
      <label class="wide">Thao tÃ¡c
        <select name="mode">
          <option value="maintenance_on">Báº­t báº£o trÃ¬</option>
          <option value="maintenance_off">Táº¯t báº£o trÃ¬</option>
          <option value="ai_on">Báº­t AI auto reply</option>
          <option value="ai_off">Táº¯t AI auto reply</option>
        </select>
      </label>
      <button class="wide danger" type="submit">Cáº­p nháº­t há»‡ thá»‘ng</button>
    </form>
  </section>
  <section class="action-card is-critical">
    <div class="card-head"><h3>Pending manual</h3><span class="tag danger">cleanup</span></div>
    <form method="post" action="{action_url}" class="form-grid" data-confirm="XÃ³a pending manual sáº½ giáº£i phÃ³ng slot. Báº¡n Ä‘Ã£ kiá»ƒm tra hoÃ n tiá»n náº¿u cáº§n?">
      <input type="hidden" name="action" value="pending_manual">
      <label>Thao tÃ¡c
        <select name="mode"><option value="clear_one">XÃ³a 1 Ä‘Æ¡n</option><option value="clear_all">XÃ³a táº¥t cáº£</option></select>
      </label>
      <label>MÃ£ Ä‘Æ¡n<input name="order_code" placeholder="bá» trá»‘ng náº¿u xÃ³a táº¥t cáº£"></label>
      <button class="wide danger" type="submit">Dá»n pending</button>
    </form>
  </section>
  </div>
</div>
"""


def _admin_web_tables() -> str:
    return f"""
<div class="action-stack">
  <section>
    <h2>User top balance</h2>
    <div class="table-scroll"><table class="mini-table"><thead><tr><th>ID</th><th>TÃªn</th><th>Sá»‘ dÆ°</th><th>Tráº¡ng thÃ¡i</th></tr></thead><tbody>{_admin_web_render_users()}</tbody></table></div>
  </section>
  <section>
    <h2>Sáº£n pháº©m</h2>
    <div class="table-scroll"><table class="mini-table"><thead><tr><th>ID</th><th>TÃªn</th><th>GiÃ¡</th><th>Stock</th></tr></thead><tbody>{_admin_web_render_products()}</tbody></table></div>
  </section>
  <section>
    <h2>API partner</h2>
    <div class="table-scroll"><table class="mini-table"><thead><tr><th>Key</th><th>TÃªn</th><th>Sá»‘ dÆ°</th><th>On/off</th></tr></thead><tbody>{_admin_web_render_api_keys()}</tbody></table></div>
  </section>
  <section>
    <h2>Don gan day</h2>
    <div class="table-scroll"><table class="mini-table"><thead><tr><th>MÃ£</th><th>Sáº£n pháº©m</th><th>Status</th><th>Tiá»n</th></tr></thead><tbody>{_admin_web_render_orders()}</tbody></table></div>
  </section>
  <section>
    <h2>Audit web admin</h2>
    <div class="table-scroll"><table class="mini-table"><thead><tr><th>LÃºc</th><th>Action</th><th>Target</th><th>Status</th><th>Ghi chÃº</th></tr></thead><tbody>{_admin_web_render_audit_log()}</tbody></table></div>
  </section>
</div>
"""


def _admin_web_unread_count() -> tuple[int, str]:
    details = []
    c_manual = len(pending_manual_orders) if isinstance(pending_manual_orders, dict) else 0
    if c_manual: details.append(f"{c_manual} Ä‘Æ¡n manual")
    
    c_chat = sum(1 for v in (live_chats.values() if isinstance(live_chats, dict) else []) if isinstance(v, dict) and v.get("status") in {"active", "open", "pending"})
    if c_chat: details.append(f"{c_chat} tin nháº¯n live chat")
    
    c_war = sum(1 for v in (warranty_claims.values() if isinstance(warranty_claims, dict) else []) if isinstance(v, dict) and v.get("status") in {"pending"})
    if c_war: details.append(f"{c_war} yÃªu cáº§u báº£o hÃ nh")
    
    c_with = sum(1 for v in (withdrawal_requests.values() if isinstance(withdrawal_requests, dict) else []) if isinstance(v, dict) and v.get("status") in {"pending"})
    if c_with: details.append(f"{c_with} lá»‡nh rÃºt tiá»n")
    
    total = c_manual + c_chat + c_war + c_with
    msg = "Äang chá» xá»­ lÃ½:\\n- " + "\\n- ".join(details) if total > 0 else "KhÃ´ng cÃ³ thÃ´ng bÃ¡o má»›i."
    return total, msg

def _admin_web_layout(title: str, body: str, request=None) -> str:
    key_query = _admin_web_key_query(request) if request is not None else ""
    unread, unread_msg = _admin_web_unread_count()
    bell_html = f'<a href="javascript:void(0)" onclick="showToast(`{unread_msg}`)" title="ThÃ´ng bÃ¡o pending" style="position:relative;">ðŸ””<span style="position:absolute;top:-4px;right:-4px;background:var(--red);color:#fff;border-radius:10px;padding:2px 6px;font-size:10px;font-weight:bold;line-height:1;">{unread}</span></a>' if unread > 0 else '<a href="javascript:void(0)" onclick="showToast(`KhÃ´ng cÃ³ thÃ´ng bÃ¡o má»›i!`)" style="opacity:0.3;cursor:pointer;">ðŸ””</a>'
    csrf_token = escape(_admin_web_csrf_token(request)) if request is not None else ""
    csrf_input = f'<input type="hidden" name="csrf_token" value="{csrf_token}">'
    body = re.sub(r'(<form\b(?=[^>]*\bmethod=["\']post["\'])[^>]*>)', rf'\1{csrf_input}', body, flags=re.IGNORECASE)
    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
{ADMIN_WEB_REDESIGN_CSS}
{ADMIN_WEB_VIP_CSS}
{ADMIN_WEB_OPS_CSS}
  </style>
</head>
<body>
  <header class="admin-topbar"><nav>
    <button id="mobileMenuToggle" class="mobile-menu-toggle" type="button" aria-label="Má»Ÿ menu Ä‘iá»u hÆ°á»›ng" aria-controls="adminNavLinks" aria-expanded="false" onclick="toggleMobileMenu()"><span></span><span></span><span></span></button>
    <strong class="admin-brand"><span class="admin-brand-mark">D</span><span>Dino <b>Ops</b><small>Control center</small></span></strong>
    <div class="topbar-actions">{bell_html}<button id="themeToggle" onclick="toggleTheme()" title="Äá»•i giao diá»‡n" aria-label="Äá»•i giao diá»‡n sÃ¡ng tá»‘i">ðŸŒ™</button></div>
    <div id="adminNavLinks" class="admin-nav-links"><a href="/admin{key_query}">Dashboard</a><a href="/admin/resell{key_query}">API Resell</a><a href="/admin/supplier_catalog{key_query}">SupplierCatalog</a><a href="/admin/categories{key_query}">Danh má»¥c</a><a href="/admin/commands{key_query}">Lá»‡nh admin</a><form method="post" action="/admin/logout">{csrf_input}<button id="admin-logout" type="submit">ÄÄƒng xuáº¥t</button></form></div>
  </nav></header>
  <button id="mobileMenuBackdrop" class="mobile-menu-backdrop" type="button" aria-label="ÄÃ³ng menu" onclick="toggleMobileMenu(false)"></button>
  <div id="toast-container"></div>
  <main>{body}</main>
<script>
function toggleMobileMenu(force) {{
  const links = document.getElementById('adminNavLinks');
  const toggle = document.getElementById('mobileMenuToggle');
  const backdrop = document.getElementById('mobileMenuBackdrop');
  if (!links || !toggle) return;
  const open = typeof force === 'boolean' ? force : !links.classList.contains('is-open');
  links.classList.toggle('is-open', open);
  backdrop?.classList.toggle('is-open', open);
  toggle.classList.toggle('is-open', open);
  toggle.setAttribute('aria-expanded', String(open));
  document.body.classList.toggle('menu-open', open);
}}
document.addEventListener('keydown', event => {{ if (event.key === 'Escape') toggleMobileMenu(false); }});
document.addEventListener('click', event => {{ if (event.target.closest('#adminNavLinks a')) toggleMobileMenu(false); }});
function toggleTheme() {{
  document.documentElement.classList.toggle('dark-mode');
  const isDark = document.documentElement.classList.contains('dark-mode');
  localStorage.setItem('admin_theme', isDark ? 'dark' : 'light');
  document.getElementById('themeToggle').textContent = isDark ? 'â˜€ï¸' : 'ðŸŒ™';
}}
if (localStorage.getItem('admin_theme') === 'dark') {{
  document.documentElement.classList.add('dark-mode');
  document.addEventListener('DOMContentLoaded', () => document.getElementById('themeToggle').textContent = 'â˜€ï¸');
}}
function showToast(message, isError = false) {{
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast ' + (isError ? 'error' : 'success');
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {{
    toast.classList.add('hide');
    toast.addEventListener('animationend', () => toast.remove());
  }}, 3000);
}}
document.addEventListener('submit', function(event) {{
  var form = event.target;
  if (form.tagName !== 'FORM') form = form.closest('form');
  if (!form || !form.dataset.confirm) return;
  if (!window.confirm(form.dataset.confirm)) {{
    event.preventDefault();
    event.stopImmediatePropagation();
  }}
}}, true);
</script>
</body>
</html>"""


def _admin_web_metric_target(label: str, kind: str) -> str:
    label_text = str(label or "").casefold()
    kind_text = str(kind or "").casefold()
    if "manual pending" in label_text:
        return "ops"
    if "coupon" in label_text or "promo" in kind_text:
        return "promo"
    if "support" in label_text or "support" in kind_text:
        return "support"
    if "user" in label_text or "users" in kind_text:
        return "users"
    if "api" in label_text or "api" in kind_text:
        return "api"
    if "product" in kind_text:
        return "products"
    if "order" in kind_text or "revenue" in kind_text:
        return "orders"
    return "overview"


def _admin_web_dashboard_body(request=None, message: str | None = None, is_error: bool = False) -> str:
    finance = _admin_web_financial_summary()
    today_revenue = finance["today_revenue"]
    completed_orders = finance["completed"]
    active_api_keys = sum(
        1
        for data in api_keys.values()
        if isinstance(data, dict) and data.get("enabled") is not False
    )
    api_balance = sum(
        _admin_web_int(data.get("balance"), 0)
        for data in api_keys.values()
        if isinstance(data, dict)
    )
    suspicious_api_balances = sum(
        1
        for data in api_keys.values()
        if isinstance(data, dict)
        and abs(_admin_web_int(data.get("balance"), 0)) >= ADMIN_WEB_SUSPICIOUS_BALANCE_THRESHOLD
        and str(data.get("user_id") or "").strip() != str(ADMIN_USER_ID).strip()
    )
    try:
        promo_spent_today = int(get_daily_promo_spent())
    except Exception:
        promo_spent_today = 0
    open_support = (
        _admin_web_active_count(live_chats)
        + sum(1 for item in warranty_claims.values() if isinstance(item, dict) and item.get("status") in (None, "", "pending", "open"))
        + sum(1 for item in withdrawal_requests.values() if isinstance(item, dict) and item.get("status") in (None, "", "pending", "open"))
    )
    # Compute bot uptime
    _uptime_seconds = int(time.time() - app_state.bot_start_time)
    _uptime_days = _uptime_seconds // 86400
    _uptime_hours = (_uptime_seconds % 86400) // 3600
    _uptime_mins = (_uptime_seconds % 3600) // 60
    if _uptime_days > 0:
        _uptime_text = f"{_uptime_days}d {_uptime_hours}h {_uptime_mins}m"
    elif _uptime_hours > 0:
        _uptime_text = f"{_uptime_hours}h {_uptime_mins}m"
    else:
        _uptime_text = f"{_uptime_mins}m"
    metrics = [
        ("Doanh thu hÃ´m nay", f"{today_revenue:,} VND", "revenue"),
        ("LÃ£i gá»™p hÃ´m nay", f"{finance['today_profit']:,} VND", "revenue"),
        ("Tá»•ng doanh thu", f"{finance['revenue']:,} VND", "revenue"),
        ("Tá»•ng lÃ£i cÃ³ snapshot", f"{finance['profit']:,} VND", "revenue"),
        ("Äá»™ phá»§ giÃ¡ vá»‘n", f"{finance['costed']}/{completed_orders} Ä‘Æ¡n", "revenue"),
        ("ÄÆ¡n thÃ nh cÃ´ng", completed_orders, "orders"),
        ("Pending pay", len(pending_orders), "orders"),
        ("Sáº£n pháº©m", len(products), "products"),
        ("Low stock", _admin_web_low_stock_count(), "products"),
        ("Kho link legacy", len(available_links) if isinstance(available_links, set) else 0, "products"),
        ("Users", len(user_data_db), "users"),
        ("Manual pending", len(pending_manual_orders), "orders"),
        ("API partner on", f"{active_api_keys}/{len(api_keys)}", "api"),
        ("Sá»‘ dÆ° API", f"{api_balance:,} VND", "api metric-wide"),
        ("Coupon", len(coupons) if isinstance(coupons, dict) else 0, "promo"),
        ("Promo hÃ´m nay", f"{promo_spent_today:,} VND", "promo"),
        ("Support open", open_support, "support"),
        ("Bot uptime", _uptime_text, "support"),
    ]
    _get_cat_fn = globals().get("get_product_category") or (lambda n: "")
    _all_cats = set(
        str(p.get("store_category") or "") or str(_get_cat_fn(str(p.get("name") or "")) or "")
        for p in products.values() if isinstance(p, dict)
    )
    _cats_with_img = sum(1 for c in _all_cats if c and _admin_web_category_image_path(c) is not None)
    metrics.append(("áº¢nh danh má»¥c", f"{_cats_with_img}/{len(_all_cats)}", "products"))
    cards = "".join(
        f'<a class="metric metric-{escape(kind)}" href="#{escape(_admin_web_metric_target(k, kind), quote=True)}" data-page-link="{escape(_admin_web_metric_target(k, kind), quote=True)}" aria-label="Má»Ÿ {escape(k, quote=True)}">'
        f'<span>{escape(k)}</span><b>{escape(str(v))}</b></a>'
        for k, v, kind in metrics
    )
    plan_rows = [
        ("live", "Dashboard module", "Tá»•ng quan, products, orders, users, API, promo, support, ops, audit."),
        ("live", "Action web", "VÃ­ user, ban/unban, product update, stock add, API partner, coupon, system toggle, clear pending."),
        ("live", "Audit log", "Ghi riÃªng data_admin_action_log.json cho má»—i action web."),
        ("next", "RBAC + 2-step confirm", "Tach viewer/operator/finance/owner va yeu cau confirm rieng cho tien/refund/restore."),
        ("next", "Deep CRUD", "Trang detail rieng cho order/product/user, refund co preview, backup restore co preview."),
    ]
    plan_html = "".join(
        f"<tr><td><span class='tag {'readonly' if status == 'live' else 'write'}'>{escape(status)}</span></td><td>{escape(task)}</td><td>{escape(note)}</td></tr>"
        for status, task, note in plan_rows
    )
    alert = (
        f'<script>document.addEventListener("DOMContentLoaded", () => showToast({json.dumps(message)}, {"true" if is_error else "false"}));</script>'
        if message
        else ""
    )
    actions = _admin_web_action_cards(request) if request is not None else ""
    return f"""
{alert}
<div class="admin-console">
  <aside class="side-rail">
    <div class="brand-block">
      <b>Dino Admin</b>
      <span>MMO ops center</span>
    </div>
    <a href="#overview" data-page-link="overview">Tá»•ng quan</a>
    <a href="#actions" data-page-link="actions">Actions</a>
    <a href="#products" data-page-link="products">Sáº£n pháº©m</a>
    <a href="#legacy" data-page-link="legacy">Kho link</a>
    <a href="#orders" data-page-link="orders">ÄÆ¡n hÃ ng</a>
    <a href="#users" data-page-link="users">Users</a>
    <a href="#api" data-page-link="api">API partner</a>
    <a href="/admin/resell{_admin_web_key_query(request) if request is not None else ''}">API Resell</a>
    <a href="/admin/supplier_catalog{_admin_web_key_query(request) if request is not None else ''}">SupplierCatalog</a>
    <a href="#promo" data-page-link="promo">Khuyáº¿n mÃ£i</a>
    <a href="#support" data-page-link="support">Há»— trá»£</a>
    <a href="#ops" data-page-link="ops">Váº­n hÃ nh</a>
    <a href="#audit" data-page-link="audit">Audit</a>
    <a href="/admin/commands{_admin_web_key_query(request) if request is not None else ''}">Lá»‡nh admin</a>
  </aside>
  <section class="workspace">
    <div class="workspace-head">
      <div>
        <span class="eyebrow">MMO admin app</span>
        <h1>Dino Control Center</h1>
        <p>Báº£ng Ä‘iá»u khiá»ƒn táº­p trung cho sáº£n pháº©m, kho, Ä‘Æ¡n hÃ ng, user, vÃ­, API partner, coupon, support vÃ  váº­n hÃ nh.</p>
      </div>
      <div class="console-tools">
        <input id="globalSearch" placeholder="TÃ¬m trong module hiá»‡n táº¡i..." oninput="filterAdminTables()">
        <div class="status-cluster">
          <span class="tag {'danger' if MAINTENANCE_MODE else 'readonly'}">maintenance {_admin_web_bool_text(MAINTENANCE_MODE)}</span>
          <span class="tag {'readonly' if AI_AUTO_REPLY else 'write'}">ai {_admin_web_bool_text(AI_AUTO_REPLY)}</span>
        </div>
        <div class="quick-actions">
          <a id="globalOrderLookup" href="#" style="display:none"></a>
          <a href="#actions" data-page-link="actions">Quick actions</a>
          <a href="#products" data-page-link="products">Catalog</a>
          <a href="#audit" data-page-link="audit">Audit trail</a>
        </div>
      </div>
    </div>

    <section class="module-section admin-page active" id="overview">
      <div class="section-head">
        <div><h2>Tá»•ng quan</h2><p>Chá»‰ sá»‘ váº­n hÃ nh hiá»‡n táº¡i, cáº­p nháº­t trá»±c tiáº¿p tá»« runtime.</p></div>
      </div>
      <div class="grid">{cards}</div>
      {_admin_web_overview_board(request)}
    </section>

    <section class="module-section admin-page" id="actions">
      <div class="section-head"><div><h2>Actions</h2><p>Thao tÃ¡c ghi trá»±c tiáº¿p vÃ o database/runtime, cÃ³ audit log báº¯t buá»™c.</p></div></div>
      <div class="actions-grid">{actions}</div>
    </section>

    <section class="module-section admin-page" id="products">
      <div class="section-head">
        <div><h2>Sáº£n pháº©m & tá»“n kho</h2><p>Quáº£n lÃ½ catalog local, manual, SupplierSource vÃ  SocialSource. Äang hiá»ƒn thá»‹ {min(len(products), ADMIN_WEB_PRODUCT_TABLE_LIMIT):,}/{len(products):,} sáº£n pháº©m má»›i nháº¥t Ä‘á»ƒ dashboard táº£i nhanh.</p></div>
        <select onchange="filterTableKind('productsTable', this.value)"><option value="">Táº¥t cáº£ loáº¡i</option><option value="local">local</option><option value="manual">manual</option><option value="supplier_source">supplier_source</option><option value="ctt">ctt</option></select>
      </div>
      <div class="table-scroll"><table class="data-table" id="productsTable"><thead><tr><th>ID</th><th>TÃªn</th><th>Loáº¡i</th><th>GiÃ¡</th><th>Stock</th><th>Pending</th><th>Sold</th><th>Sync</th><th></th></tr></thead><tbody>{_admin_web_render_product_rows(request, limit=ADMIN_WEB_PRODUCT_TABLE_LIMIT)}</tbody></table></div>
    </section>

    <section class="module-section admin-page" id="legacy">
      <div class="section-head"><div><h2>Kho link legacy</h2><p>Link dÃ¹ng cho flow iCloud/API legacy. CÃ³ thá»ƒ thay, thÃªm, xÃ³a trá»±c tiáº¿p á»Ÿ Actions.</p></div></div>
      <div class="table-scroll"><table class="data-table" id="legacyLinksTable"><thead><tr><th>#</th><th>Link</th><th>Status</th></tr></thead><tbody>{_admin_web_render_legacy_link_rows()}</tbody></table></div>
    </section>

    <section class="module-section admin-page" id="orders">
      <div class="section-head"><div><h2>ÄÆ¡n hÃ ng</h2><p>Recent orders vÃ  tráº¡ng thÃ¡i thanh toÃ¡n/giao hÃ ng. Äang hiá»ƒn thá»‹ {min(len(order_history), ADMIN_WEB_ORDER_TABLE_LIMIT):,}/{len(order_history):,} Ä‘Æ¡n má»›i nháº¥t.</p></div></div>
      <div class="table-scroll"><table class="data-table" id="ordersTable"><thead><tr><th>MÃ£</th><th>Sáº£n pháº©m</th><th>User</th><th>Status</th><th>Tiá»n</th><th>Qty</th><th>LÃºc</th><th></th></tr></thead><tbody>{_admin_web_render_order_rows(request, limit=ADMIN_WEB_ORDER_TABLE_LIMIT)}</tbody></table></div>
    </section>

    <section class="module-section admin-page" id="users">
      <div class="section-head">
        <div><h2>Users & vÃ­</h2><p>Top users theo sá»‘ dÆ°, Ä‘Æ¡n hÃ ng vÃ  tráº¡ng thÃ¡i ban. Äang hiá»ƒn thá»‹ {min(len(user_data_db), ADMIN_WEB_USER_TABLE_LIMIT):,}/{len(user_data_db):,} user.</p></div>
        <select onchange="filterTableKind('usersTable', this.value)"><option value="">Táº¥t cáº£</option><option value="active">active</option><option value="banned">banned</option></select>
      </div>
      <div class="table-scroll"><table class="data-table" id="usersTable"><thead><tr><th>ID</th><th>User</th><th>Sá»‘ dÆ°</th><th>Orders</th><th>Total spent</th><th>Status</th><th></th></tr></thead><tbody>{_admin_web_render_user_rows(request, limit=ADMIN_WEB_USER_TABLE_LIMIT)}</tbody></table></div>
    </section>

    <section class="module-section admin-page api-operations-page" id="api">
      <div class="api-hero">
        <div><span class="eyebrow">Partner infrastructure</span><h2>API Operations Center</h2><p>Báº£o máº­t key, kiá»ƒm soÃ¡t lÆ°u lÆ°á»£ng, váº­n hÃ nh vÃ­ vÃ  theo dÃµi sá»©c khá»e API táº¡i má»™t nÆ¡i.</p></div>
        <a class="button dark" href="/admin/api-partners/export.csv{_admin_web_key_query(request) if request is not None else ''}">Xuáº¥t CSV</a>
      </div>
      <div class="api-kpi-grid">
        <article><span>Tá»•ng partner</span><b>{len(api_keys):,}</b><small>ÄÃ£ Ä‘Äƒng kÃ½</small></article>
        <article><span>Äang hoáº¡t Ä‘á»™ng</span><b>{sum(1 for d in api_keys.values() if not isinstance(d, dict) or d.get('enabled') is not False):,}</b><small>Key Ä‘ang ON</small></article>
        <article><span>Sá»‘ dÆ° tháº¥p</span><b>{sum(1 for d in api_keys.values() if isinstance(d, dict) and _admin_web_int(d.get('balance'), 0) <= max(0, _admin_web_int(d.get('low_balance_threshold'), 100000))):,}</b><small>Cáº§n theo dÃµi</small></article>
        <article><span>Requests 14 ngÃ y</span><b>{db_api_analytics('', 14).get('total', 0):,}</b><small>{db_api_analytics('', 14).get('error_rate', 0)}% lá»—i</small></article>
      </div>
      <div class="api-filter-bar">
        <select id="apiStatusFilter" onchange="filterApiPartners()"><option value="">Má»i tráº¡ng thÃ¡i</option><option value="active">Äang hoáº¡t Ä‘á»™ng</option><option value="disabled">ÄÃ£ thu há»“i</option><option value="admin">Admin</option></select>
        <select id="apiBalanceFilter" onchange="filterApiPartners()"><option value="">Má»i sá»‘ dÆ°</option><option value="low">DÆ°á»›i ngÆ°á»¡ng</option></select>
        <span class="tag {'danger' if suspicious_api_balances else 'readonly'}">{suspicious_api_balances} báº¥t thÆ°á»ng</span>
      </div>
      <div class="table-scroll"><table class="data-table api-partner-table" id="apiTable"><thead><tr><th>Key / Public ID</th><th>Partner</th><th>Sá»‘ dÆ°</th><th>Tráº¡ng thÃ¡i</th><th>Quota & Alert</th><th>Ghi chÃº</th><th>Thao tÃ¡c nhanh</th></tr></thead><tbody>{_admin_web_render_api_partner_rows(request, limit=ADMIN_WEB_API_TABLE_LIMIT)}</tbody></table></div>
    </section>

    <section class="module-section admin-page" id="promo">
      <div class="section-head"><div><h2>Khuyáº¿n mÃ£i</h2><p>Coupon hiá»‡n cÃ³, flash sale vÃ  combo sáº½ má»Ÿ rá»™ng á»Ÿ phase sau.</p></div></div>
      <div class="split-grid">
        <div class="table-scroll"><table class="data-table" id="couponTable"><thead><tr><th>Code</th><th>Giáº£m</th><th>Used</th><th>Háº¿t háº¡n</th><th></th></tr></thead><tbody>{_admin_web_render_coupon_rows(request)}</tbody></table></div>
        <div class="mini-panel">
          <h3>Promo snapshot</h3>
          <p><b>{len(flash_sales) if isinstance(flash_sales, dict) else 0}</b> flash sale</p>
          <p><b>{len(combo_deals) if isinstance(combo_deals, dict) else 0}</b> combo deal</p>
          <p><b>{len(active_giveaways) if isinstance(active_giveaways, dict) else 0}</b> giveaway</p>
          <p><b>{_admin_web_money(promo_spent_today)}</b> promo spent hÃ´m nay</p>
        </div>
      </div>
    </section>

    <section class="module-section admin-page" id="support">
      <div class="section-head"><div><h2>Há»— trá»£</h2><p>Live chat, báº£o hÃ nh vÃ  rÃºt tiá»n gom chung Ä‘á»ƒ admin khÃ´ng bá» sÃ³t ticket.</p></div></div>
      <div class="table-scroll"><table class="data-table" id="supportTable"><thead><tr><th>Loáº¡i</th><th>ID</th><th>User</th><th>Status</th><th>Ná»™i dung</th><th></th></tr></thead><tbody>{_admin_web_render_support_rows(request)}</tbody></table></div>
    </section>

    <section class="module-section admin-page" id="ops">
      <div class="section-head"><div><h2>Váº­n hÃ nh</h2><p>Tráº¡ng thÃ¡i cron MBBank, bot user/admin, log runtime vÃ  manual pending.</p></div></div>
      <div class="split-grid">
        <div class="table-scroll"><table class="data-table"><thead><tr><th>Status</th><th>Module</th><th>Ghi chÃº</th></tr></thead><tbody>{_admin_web_render_ops_status_rows(request)}</tbody></table></div>
        <div class="ops-log-panel">{_admin_web_render_ops_log_panel()}</div>
      </div>
      <div class="split-grid">
        <div class="table-scroll"><table class="data-table" id="pendingManualTable"><thead><tr><th>MÃ£</th><th>Sáº£n pháº©m</th><th>User</th><th>Tiá»n</th><th>LÃºc</th></tr></thead><tbody>{_admin_web_render_pending_manual_rows()}</tbody></table></div>
        <div class="table-scroll">
          {_admin_web_render_payment_config(request)}
          <table class="data-table" style="margin-top:20px;"><thead><tr><th>Status</th><th>Module</th><th>Ghi chÃº</th></tr></thead><tbody>{plan_html}</tbody></table>
        </div>
      </div>
    </section>

    <section class="module-section admin-page" id="audit">
      <div class="section-head"><div><h2>Audit</h2><p>Lá»‹ch sá»­ thao tÃ¡c tá»« web admin.</p></div></div>
      <div class="table-scroll"><table class="data-table" id="auditTable"><thead><tr><th>LÃºc</th><th>Action</th><th>Target</th><th>Status</th><th>IP</th><th>Message</th></tr></thead><tbody>{_admin_web_render_audit_rows()}</tbody></table></div>
    </section>
  </section>
</div>
<script>
let initialAdminPage = '';
try {{
  initialAdminPage = decodeURIComponent((location.hash || '').replace('#', ''));
}} catch (error) {{
  initialAdminPage = '';
}}
if (initialAdminPage && document.getElementById(initialAdminPage)) {{
  history.replaceState(null, '', location.pathname + location.search);
}}
function normalizeText(value) {{
  return (value || '').toString().toLowerCase();
}}
function normalizeOrderLookup(value) {{
  const candidate = (value || '').toString().trim().toUpperCase().replace(/\\s+/g, '');
  return /^(?:ICLD\\d{{6}}|MANUAL[A-Z0-9]{{6,}}|PROD[A-Z0-9]{{6,}})$/.test(candidate) ? candidate : '';
}}
function adminDetailUrl(entity, id) {{
  const params = new URLSearchParams(location.search);
  params.set('entity', entity);
  params.set('id', id);
  return '/admin/item?' + params.toString();
}}
function updateGlobalOrderLookup() {{
  const link = document.getElementById('globalOrderLookup');
  const search = document.getElementById('globalSearch');
  if (!link || !search) return;
  const orderCode = normalizeOrderLookup(search.value);
  if (!orderCode) {{
    link.style.display = 'none';
    link.removeAttribute('href');
    link.textContent = '';
    return;
  }}
  link.href = adminDetailUrl('order', orderCode);
  link.textContent = 'Mo chi tiet ' + orderCode;
  link.style.display = '';
}}
function activeAdminPage() {{
  return document.querySelector('.admin-page.active') || document;
}}
function applyAdminFilters(scope) {{
  const q = normalizeText(document.getElementById('globalSearch')?.value);
  updateGlobalOrderLookup();
  const root = scope || activeAdminPage();
  root.querySelectorAll('table').forEach(table => {{
    const kind = table.dataset.kindFilter || '';
    table.querySelectorAll('tr.data-row').forEach(row => {{
      const text = normalizeText(row.dataset.search || row.innerText);
      const matchesText = !q || text.includes(q);
      const matchesKind = !kind || row.dataset.kind === kind;
      row.style.display = matchesText && matchesKind ? '' : 'none';
    }});
  }});
  root.querySelectorAll('.overview-list .data-row').forEach(row => {{
    const text = normalizeText(row.dataset.search || row.innerText);
    row.style.display = !q || text.includes(q) ? '' : 'none';
  }});
}}
function filterAdminTables() {{
  applyAdminFilters();
  if (document.getElementById('api')?.classList.contains('active')) filterApiPartners();
}}
function filterTableKind(tableId, kind) {{
  const table = document.getElementById(tableId);
  if (!table) return;
  table.dataset.kindFilter = kind || '';
  applyAdminFilters(table.closest('.admin-page') || table);
}}
function filterApiPartners() {{
  const table = document.getElementById('apiTable');
  if (!table) return;
  const status = document.getElementById('apiStatusFilter')?.value || '';
  const balance = document.getElementById('apiBalanceFilter')?.value || '';
  const q = normalizeText(document.getElementById('globalSearch')?.value);
  table.querySelectorAll('tr.data-row').forEach(row => {{
    const matchesStatus = !status || row.dataset.kind === status;
    const matchesBalance = balance !== 'low' || row.dataset.low === '1';
    const matchesText = !q || normalizeText(row.dataset.search || row.innerText).includes(q);
    row.style.display = matchesStatus && matchesBalance && matchesText ? '' : 'none';
  }});
}}
document.getElementById('globalSearch')?.addEventListener('keydown', event => {{
  if (event.key !== 'Enter') return;
  const orderCode = normalizeOrderLookup(event.currentTarget.value);
  if (!orderCode) return;
  event.preventDefault();
  window.location.href = adminDetailUrl('order', orderCode);
}});
function setAdminPage() {{
  const fallback = 'overview';
  const pageOverride = setAdminPage.pageOverride || '';
  setAdminPage.pageOverride = '';
  let page = pageOverride || fallback;
  try {{
    page = pageOverride || decodeURIComponent((location.hash || '#' + fallback).replace('#', '')) || fallback;
  }} catch (error) {{
    page = fallback;
  }}
  const target = document.getElementById(page) ? page : fallback;
  document.querySelectorAll('.admin-page').forEach(section => {{
    section.classList.toggle('active', section.id === target);
  }});
  document.querySelectorAll('[data-page-link]').forEach(link => {{
    link.classList.toggle('active', link.dataset.pageLink === target);
  }});
  const activeRailLink = document.querySelector('.side-rail [data-page-link].active');
  const sideRail = activeRailLink?.closest('.side-rail');
  if (activeRailLink && sideRail && window.matchMedia('(max-width: 860px)').matches) {{
    window.requestAnimationFrame(() => {{
      const centeredLeft = activeRailLink.offsetLeft - (sideRail.clientWidth - activeRailLink.offsetWidth) / 2;
      sideRail.scrollTo({{ left: Math.max(0, centeredLeft), behavior: 'smooth' }});
    }});
  }}
  const search = document.getElementById('globalSearch');
  if (search) search.placeholder = target === 'overview' ? 'TÃ¬m trong cÃ¡c báº£ng...' : 'TÃ¬m trong module hiá»‡n táº¡i...';
  applyAdminFilters(document.getElementById(target));
  window.setTimeout(() => window.scrollTo({{ top: 0, left: 0, behavior: 'auto' }}), 0);
}}
document.querySelectorAll('[data-page-link]').forEach(link => {{
  link.addEventListener('click', event => {{
    const target = link.dataset.pageLink || 'overview';
    if (!document.getElementById(target)) return;
    event.preventDefault();
    if (location.hash !== '#' + target) {{
      history.replaceState(null, '', '#' + target);
    }}
    setAdminPage.pageOverride = target;
    setAdminPage();
  }});
}});
window.addEventListener('hashchange', setAdminPage);
setAdminPage.pageOverride = initialAdminPage || '';
setAdminPage();
initialAdminPage = '';
</script>
"""


def _admin_web_commands_body() -> str:
    groups = []
    for group in ADMIN_WEB_COMMAND_GROUPS:
        commands = []
        for name, syntax, description, risk in group["commands"]:
            searchable = " ".join([group["group"], name, syntax, description, risk]).lower()
            commands.append(
                f'<article class="command-card" data-risk="{escape(risk)}" data-search="{escape(searchable)}">'
                f"<code>{escape(syntax)}</code>"
                f"<p>{escape(description)}</p>"
                f'<span class="tag {escape(risk)}">{escape(risk)}</span>'
                "</article>"
            )
        groups.append(
            '<section class="command-group">'
            f"<h2>{escape(group['group'])}</h2>"
            f'<div class="command-list">{"".join(commands)}</div>'
            "</section>"
        )
    return f"""
<section class="hero">
  <span class="eyebrow">command catalog</span>
  <h1>All admin commands.</h1>
  <p>Danh sÃ¡ch toÃ n bá»™ lá»‡nh admin Ä‘ang cÃ³ trong bot, lá»c theo tá»« khÃ³a vÃ  má»©c rá»§i ro Ä‘á»ƒ quáº£n lÃ½ váº­n hÃ nh nhanh hÆ¡n trÃªn web.</p>
  <div class="hero-actions">
    <a class="button dark" href="/admin" onclick="this.href='/admin'+location.search">Dashboard</a>
    <a class="button" href="/api/admin/commands" onclick="this.href='/api/admin/commands'+location.search">JSON catalog</a>
  </div>
</section>
<div class="toolbar">
  <input id="q" placeholder="TÃ¬m lá»‡nh, nhÃ³m, mÃ´ táº£..." oninput="filterCommands()">
  <select id="risk" onchange="filterCommands()">
    <option value="">Táº¥t cáº£ risk</option>
    <option value="readonly">readonly</option>
    <option value="write">write</option>
    <option value="danger">danger</option>
    <option value="conversation">conversation</option>
    <option value="user">user</option>
  </select>
</div>
<div class="command-groups" id="commands">{"".join(groups)}</div>
<script>
function filterCommands() {{
  const q = document.getElementById('q').value.toLowerCase();
  const risk = document.getElementById('risk').value;
  document.querySelectorAll('.command-card').forEach(card => {{
    const text = card.dataset.search || card.innerText.toLowerCase();
    const rowRisk = card.dataset.risk || '';
    card.style.display = text.includes(q) && (!risk || rowRisk === risk) ? '' : 'none';
  }});
  document.querySelectorAll('.command-group').forEach(group => {{
    const visible = Array.from(group.querySelectorAll('.command-card')).some(card => card.style.display !== 'none');
    group.style.display = visible ? '' : 'none';
  }});
}}
</script>
"""


def _admin_web_form_text(form, name: str) -> str:
    value = form.get(name)
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "").strip()


def _admin_web_safe_header(request, name: str) -> str:
    if request is None:
        return ""
    headers = getattr(request, "headers", {}) or {}
    try:
        return str(headers.get(name) or "").strip()
    except (AttributeError, TypeError, ValueError):
        return ""


def _admin_web_client_ip(request) -> str:
    forwarded_for = _admin_web_safe_header(request, "x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()[:80]
    client = getattr(request, "client", None)
    return str(getattr(client, "host", "") or "")[:80]


def _admin_web_mask_sensitive(value, visible: int = 5) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= visible * 2 + 3:
        return text
    return f"{text[:visible]}...{text[-visible:]}"


def _admin_web_api_public_id(api_key: str) -> str:
    text = str(api_key or "").strip()
    if not text:
        return ""
    digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    return f"ak_{digest[:16]}"


def _admin_web_api_display_key(api_key: str) -> str:
    public_id = _admin_web_api_public_id(api_key)
    return public_id or "hidden"


def _admin_web_api_wallet_note(data: dict, balance: int) -> str:
    if not isinstance(data, dict):
        return ""
    parts = []
    wallet_mode = str(data.get("wallet_mode") or "").strip()
    if wallet_mode:
        parts.append(wallet_mode)
    if data.get("shared_wallet_enabled"):
        parts.append("shared wallet")
    owner = data.get("user_id")
    if owner:
        parts.append(f"owner {owner}")
    if abs(int(balance or 0)) >= ADMIN_WEB_SUSPICIOUS_BALANCE_THRESHOLD and str(data.get("user_id") or "").strip() != str(ADMIN_USER_ID).strip():
        parts.append("Sá»‘ dÆ° báº¥t thÆ°á»ng")
    note = str(data.get("note") or "").strip()
    if note:
        parts.append(note)
    return " | ".join(parts)


def _admin_web_mask_target(action: str, target: str) -> str:
    if action in {"api_partner"}:
        return _admin_web_mask_sensitive(target, 6)
    return str(target or "")


def _admin_web_notify_enabled() -> bool:
    try:
        return bool(ADMIN_USER_ID and globals().get("bot_instance"))
    except (NameError, TypeError, ValueError):
        return False


def _admin_web_notify_details_text(details: dict) -> str:
    if not isinstance(details, dict) or not details:
        return ""
    parts = []
    for key, value in details.items():
        if value in (None, "", [], {}):
            continue
        parts.append(f"{key}={_admin_web_short(_admin_web_plain_display(value), 80)}")
    return ", ".join(parts[:8])


def _admin_web_action_label(action: str) -> str:
    return {
        "user_balance": "Cáº­p nháº­t vÃ­ user",
        "user_ban": "Ban/unban user",
        "user_profile": "Sá»­a há»“ sÆ¡ user",
        "product_create": "ThÃªm sáº£n pháº©m",
        "product_update": "Sá»­a sáº£n pháº©m",
        "product_stock": "Tá»“n kho sáº£n pháº©m",
        "product_delete": "XÃ³a sáº£n pháº©m",
        "api_partner": "API partner",
        "order_tools": "CÃ´ng cá»¥ Ä‘Æ¡n hÃ ng",
        "coupon": "Coupon",
        "system_toggle": "Há»‡ thá»‘ng",
        "pending_manual": "Pending manual",
        "support_update": "Support",
        "web_login": "ÄÄƒng nháº­p web admin",
    }.get(str(action or ""), str(action or "unknown"))


def _admin_web_notify_message(event: dict, title: str) -> str:
    action = str(event.get("action") or "unknown")
    target = _admin_web_mask_target(action, str(event.get("target") or ""))
    details = _admin_web_notify_details_text(event.get("details") or {})
    lines = [
        f"<b>{escape(title)}</b>",
        f"<b>Action:</b> <code>{escape(_admin_web_action_label(action))}</code>",
        f"<b>Status:</b> <code>{escape(str(event.get('status') or 'unknown'))}</code>",
    ]
    if target:
        lines.append(f"<b>Target:</b> <code>{escape(target)}</code>")
    message = _admin_web_plain_display(event.get("message") or "")
    if message:
        lines.append(f"<b>Káº¿t quáº£:</b> {escape(_admin_web_short(message, 220))}")
    if details:
        lines.append(f"<b>Details:</b> <code>{escape(details)}</code>")
    lines.extend(
        [
            f"<b>IP:</b> <code>{escape(str(event.get('ip') or 'unknown'))}</code>",
            f"<b>User-Agent:</b> <code>{escape(_admin_web_short(event.get('user_agent') or 'unknown', 150))}</code>",
            f"<b>Time:</b> <code>{escape(_admin_web_format_timestamp(event.get('timestamp')))}</code>",
        ]
    )
    return "\n".join(lines)


async def _admin_web_send_admin_notification(text: str) -> bool:
    if not _admin_web_notify_enabled():
        return False
    try:
        sent = await safe_send_admin(globals().get("bot_instance"), text)
        return bool(sent)
    except Exception:
        logger.exception("Admin web Telegram notification failed")
        return False


async def _admin_web_notify_action_event(event: dict) -> bool:
    title = "ADMIN WEB ACTION"
    if str(event.get("status") or "") != "ok":
        title = "ADMIN WEB ACTION ERROR"
    return await _admin_web_send_admin_notification(_admin_web_notify_message(event, title))


async def _admin_web_notify_login(request) -> bool:
    now = int(time.time())
    ip = _admin_web_client_ip(request)
    user_agent = _admin_web_safe_header(request, "user-agent")[:180]
    cache_key = f"{ip}|{user_agent}"
    last_sent = _admin_web_login_notify_cache.get(cache_key, 0)
    if now - int(last_sent or 0) < ADMIN_WEB_LOGIN_NOTIFY_COOLDOWN_SECONDS:
        return False
    _admin_web_login_notify_cache[cache_key] = now
    if len(_admin_web_login_notify_cache) > ADMIN_WEB_LOGIN_NOTIFY_CACHE_MAX:
        expired_before = now - ADMIN_WEB_LOGIN_NOTIFY_COOLDOWN_SECONDS
        for key, timestamp in list(_admin_web_login_notify_cache.items()):
            if int(timestamp or 0) < expired_before:
                _admin_web_login_notify_cache.pop(key, None)
        if len(_admin_web_login_notify_cache) > ADMIN_WEB_LOGIN_NOTIFY_CACHE_MAX:
            oldest_keys = sorted(
                _admin_web_login_notify_cache,
                key=lambda key: int(_admin_web_login_notify_cache.get(key) or 0),
            )
            for key in oldest_keys[: len(_admin_web_login_notify_cache) - ADMIN_WEB_LOGIN_NOTIFY_CACHE_MAX]:
                _admin_web_login_notify_cache.pop(key, None)
    event = {
        "timestamp": now,
        "actor": _admin_web_actor_label(request),
        "action": "web_login",
        "target": "admin_dashboard",
        "status": "ok",
        "message": "Admin Ä‘Ã£ má»Ÿ dashboard web.",
        "ip": ip,
        "user_agent": user_agent,
        "details": {"path": str(getattr(request, "url", "") or "/admin")[:160]},
    }
    return await _admin_web_send_admin_notification(_admin_web_notify_message(event, "ADMIN WEB LOGIN"))


def _admin_web_actor_label(request) -> str:
    return ADMIN_WEB_USERNAME if _admin_web_authorized(request) else "unknown"


def _admin_web_audit_target(action: str, form) -> str:
    target_field = {
        "user_balance": "user_id",
        "user_ban": "user_id",
        "user_profile": "user_id",
        "product_create": "product_id",
        "product_update": "product_id",
        "product_stock": "product_id",
        "product_delete": "product_id",
        "api_partner": "target",
        "order_tools": "order_code",
        "coupon": "code",
        "system_toggle": "mode",
        "pending_manual": "order_code",
        "support_update": "item_id",
        "category_create": "category_name",
        "category_update": "category_name",
        "category_visibility": "category_name",
        "category_delete": "category_name",
    }.get(action or "")
    return _admin_web_form_text(form, target_field)[:160] if target_field else ""


def _admin_web_audit_details(action: str, form) -> dict:
    if action == "user_balance":
        return {
            "mode": _admin_web_form_text(form, "mode"),
            "amount": _admin_web_int(_admin_web_form_text(form, "amount"), 0),
        }
    if action == "user_ban":
        return {"mode": _admin_web_form_text(form, "mode")}
    if action == "user_profile":
        return {
            "username_changed": bool(_admin_web_form_text(form, "username")),
            "email_changed": bool(_admin_web_form_text(form, "email")),
            "note_changed": bool(_admin_web_form_text(form, "admin_note")),
        }
    if action == "product_create":
        stock_lines = [
            line.strip()
            for line in _admin_web_form_text(form, "stock_items").splitlines()
            if line.strip()
        ]
        return {
            "requires_gmail": _admin_web_form_text(form, "requires_gmail"),
            "stock_lines": len(stock_lines),
        }
    if action == "product_update":
        stock_lines = [
            line.strip()
            for line in _admin_web_form_text(form, "stock_items").splitlines()
            if line.strip()
        ]
        return {
            "name_changed": bool(_admin_web_form_text(form, "name")),
            "price_changed": bool(_admin_web_form_text(form, "price")),
            "description_changed": bool(_admin_web_form_text(form, "description")),
            "duration_changed": bool(_admin_web_form_text(form, "duration")),
            "limit_changed": bool(_admin_web_form_text(form, "max_pending_orders")),
            "stock_lines": len(stock_lines),
        }
    if action == "product_stock":
        return {"mode": _admin_web_form_text(form, "mode")}
    if action == "product_delete":
        return {"product_id": _admin_web_form_text(form, "product_id")}
    if action == "api_partner":
        return {
            "mode": _admin_web_form_text(form, "mode"),
            "amount": _admin_web_int(_admin_web_form_text(form, "amount"), 0),
        }
    if action == "order_tools":
        return {"mode": _admin_web_form_text(form, "mode")}
    if action == "coupon":
        return {
            "mode": _admin_web_form_text(form, "mode"),
            "discount": _admin_web_int(_admin_web_form_text(form, "discount"), 0),
            "quantity": _admin_web_int(_admin_web_form_text(form, "quantity"), 0),
        }
    if action == "system_toggle":
        return {"mode": _admin_web_form_text(form, "mode")}
    if action == "pending_manual":
        return {"mode": _admin_web_form_text(form, "mode")}
    if action == "support_update":
        return {
            "entity": _admin_web_form_text(form, "entity"),
            "status": _admin_web_form_text(form, "status"),
        }
    return {}


def _admin_web_record_action(action: str, ok: bool, message: str, form=None, request=None):
    global admin_action_log
    if not isinstance(admin_action_log, list):
        admin_action_log = []
    event = {
        "timestamp": int(time.time()),
        "actor": _admin_web_actor_label(request),
        "action": str(action or "unknown")[:80],
        "target": _admin_web_audit_target(action, form or {}),
        "status": "ok" if ok else "error",
        "message": str(message or "")[:500],
        "ip": _admin_web_client_ip(request),
        "user_agent": _admin_web_safe_header(request, "user-agent")[:180],
        "details": _admin_web_audit_details(action, form or {}),
    }
    admin_action_log.append(event)
    if len(admin_action_log) > ADMIN_WEB_AUDIT_LIMIT:
        del admin_action_log[:-ADMIN_WEB_AUDIT_LIMIT]
    return event


async def _admin_web_read_urlencoded_form(request):
    raw_body = await request.body()
    text = raw_body.decode("utf-8", errors="replace")
    return parse_qs(text, keep_blank_values=True)


def _admin_web_find_api_key(target: str):
    target_text = str(target or "").strip()
    if not target_text:
        return None
    if target_text in api_keys:
        return target_text
    for api_key, data in api_keys.items():
        if _admin_web_api_public_id(str(api_key)) == target_text:
            return api_key
        name = data.get("name") if isinstance(data, dict) else str(data)
        if str(name or "").strip().casefold() == target_text.casefold():
            return api_key
    return None


def _admin_web_find_order_records(order_code: str):
    target = str(order_code or "").strip().upper()
    if not target:
        return []
    found = []
    for order in order_history:
        if isinstance(order, dict) and _admin_web_order_code(order).upper() == target:
            found.append((HISTORY_FILE, order))
    for mapping, table_name in (
        (pending_orders, PENDING_ORDERS_FILE),
        (pending_manual_orders, PENDING_MANUAL_ORDERS_FILE),
    ):
        if not isinstance(mapping, dict):
            continue
        direct = mapping.get(target)
        if isinstance(direct, dict):
            found.append((table_name, direct))
        for key, order in mapping.items():
            if key == target:
                continue
            if isinstance(order, dict) and _admin_web_order_code(order).upper() == target:
                found.append((table_name, order))
    return found


async def _admin_web_action_user_balance(form):
    user_id = _admin_web_form_text(form, "user_id")
    if not user_id.isdigit():
        return False, "User ID khÃ´ng há»£p lá»‡."
    amount = _admin_web_int(_admin_web_form_text(form, "amount"), None)
    if amount is None or amount < 0:
        return False, "Sá»‘ tiá»n khÃ´ng há»£p lá»‡."
    mode = _admin_web_form_text(form, "mode") or "add"
    reason = _admin_web_form_text(form, "reason") or "Admin web"
    profile = user_data_db.get(user_id)
    if not isinstance(profile, dict):
        profile = {"user_id": int(user_id), "balance": 0}
        user_data_db[user_id] = profile
    current = _admin_web_int(profile.get("balance"), 0)
    if mode == "add":
        new_balance = current + amount
    elif mode == "sub":
        new_balance = max(0, current - amount)
    elif mode == "set":
        new_balance = amount
    else:
        return False, "Kiá»ƒu cáº­p nháº­t vÃ­ khÃ´ng há»£p lá»‡."
    db_update_balance(int(user_id), int(new_balance), reason=f"{reason} ({mode})")
    await save_data(force=True, tables=[USERS_FILE, TRANSACTION_HISTORY_FILE])
    return True, f"Da cap nhat vi user {user_id}: {current:,} -> {new_balance:,} VND."


async def _admin_web_action_user_ban(form):
    user_id = _admin_web_form_text(form, "user_id")
    if not user_id.isdigit():
        return False, "User ID khÃ´ng há»£p lá»‡."
    target_id = int(user_id)
    mode = _admin_web_form_text(form, "mode") or "ban"
    if mode == "ban":
        banned_users.add(target_id)
        msg = f"Da ban user {target_id}."
    elif mode == "unban":
        banned_users.discard(target_id)
        msg = f"Da unban user {target_id}."
    else:
        return False, "Thao tÃ¡c ban/unban khÃ´ng há»£p lá»‡."
    await save_data(force=True, tables=[BANNED_USERS_FILE])
    return True, msg


async def _admin_web_action_user_profile(form):
    user_id = _admin_web_form_text(form, "user_id")
    if not user_id.isdigit():
        return False, "User ID khÃ´ng há»£p lá»‡."
    profile = user_data_db.get(user_id)
    if not isinstance(profile, dict):
        profile = {"user_id": int(user_id), "balance": 0}
        user_data_db[user_id] = profile
    fields = {
        "full_name": _admin_web_form_text(form, "full_name"),
        "username": _admin_web_form_text(form, "username"),
        "email": _admin_web_form_text(form, "email"),
        "admin_note": _admin_web_form_text(form, "admin_note"),
    }
    changed = []
    for field_name, value in fields.items():
        if value:
            profile[field_name] = value
            changed.append(field_name)
    if not changed:
        return False, "ChÆ°a cÃ³ thay Ä‘á»•i há»“ sÆ¡ user."
    await save_data(force=True, tables=[USERS_FILE])
    return True, f"Da cap nhat user {user_id}: {', '.join(changed)}."


async def _admin_web_action_product_create(form):
    product_id = _admin_web_form_text(form, "product_id")
    if not product_id:
        product_id = f"web_{int(time.time())}_{secrets.token_hex(3)}"
    if product_id in products:
        return False, "Product ID da ton tai."
    name = _admin_web_form_text(form, "name")
    if not name:
        return False, "TÃªn sáº£n pháº©m khÃ´ng Ä‘Æ°á»£c rá»—ng."
    price = _admin_web_int(_admin_web_form_text(form, "price"), None)
    if price is None or price < 0:
        return False, "GiÃ¡ sáº£n pháº©m khÃ´ng há»£p lá»‡."
    cost_price = _admin_web_int(_admin_web_form_text(form, "cost_price"), None)
    if cost_price is None or cost_price < 0:
        return False, "GiÃ¡ vá»‘n khÃ´ng há»£p lá»‡."
    requires_gmail = _admin_web_form_text(form, "requires_gmail") in {"1", "true", "yes", "on"}
    stock_items = [
        line.strip()
        for line in _admin_web_form_text(form, "stock_items").splitlines()
        if line.strip()
    ]
    warranty = _admin_web_form_text(form, "warranty")
    products[product_id] = {
        "name": name,
        "price": int(price),
        "cost_price": int(cost_price),
        "description": _admin_web_form_text(form, "description"),
        "duration": _admin_web_form_text(form, "duration"),
        "warranty": warranty or "KhÃ´ng",
        "requires_gmail": requires_gmail,
        "stock": [] if requires_gmail else stock_items,
        "created_by": "admin_web",
        "created_at": int(time.time()),
    }
    if requires_gmail:
        products[product_id]["max_pending_orders"] = 10
    await save_data(force=True, tables=[PRODUCTS_FILE])
    return True, f"Da tao san pham {product_id}."


async def _admin_web_action_product_update(form):
    product_id = _admin_web_form_text(form, "product_id")
    product = products.get(product_id)
    if not isinstance(product, dict):
        return False, "Khong tim thay product_id."
    name = _admin_web_form_text(form, "name")
    price_text = _admin_web_form_text(form, "price")
    cost_price_text = _admin_web_form_text(form, "cost_price")
    description = _admin_web_form_text(form, "description")
    duration = _admin_web_form_text(form, "duration")
    max_pending_text = _admin_web_form_text(form, "max_pending_orders")
    stock_text = _admin_web_form_text(form, "stock_items")
    store_category = _admin_web_form_text(form, "store_category")
    changes = []
    if store_category:
        old_category = _admin_web_product_category(product)
        product["store_category"] = store_category
        # If category changed, drop cached category file_id so bot re-resolves the image.
        if old_category != store_category:
            product.pop("category_image_file_id", None)
        changes.append("danh muc")
    if name:
        product["name"] = name
        changes.append("ten")
    if price_text:
        price = _admin_web_int(price_text, None)
        if price is None or price < 0:
            return False, "GiÃ¡ má»›i khÃ´ng há»£p lá»‡."
        product["price"] = int(price)
        changes.append("gia ban")
    if cost_price_text:
        cost_price = _admin_web_int(cost_price_text, None)
        if cost_price is None or cost_price < 0:
            return False, "GiÃ¡ vá»‘n má»›i khÃ´ng há»£p lá»‡."
        product["cost_price"] = int(cost_price)
        changes.append("gia von")
    if description:
        product["description"] = description
        changes.append("mo ta")
    if duration:
        product["duration"] = duration
        changes.append("thoi han")
    warranty = _admin_web_form_text(form, "warranty")
    if warranty:
        product["warranty"] = warranty
        changes.append("bao hanh")
    if max_pending_text:
        max_pending = _admin_web_int(max_pending_text, None)
        if max_pending is None or max_pending < 1:
            return False, "Giá»›i háº¡n manual khÃ´ng há»£p lá»‡."
        product["max_pending_orders"] = int(max_pending)
        changes.append("gioi han manual")
    if stock_text:
        if product.get("requires_gmail") or product.get("is_supplier_source_resell") or product.get("is_social_source_service"):
            return False, "Chi them stock local cho san pham auto/local stock."
        items = [line.strip() for line in stock_text.splitlines() if line.strip()]
        if not items:
            return False, "Stock them vao dang rong."
        current_stock = product.get("stock")
        if not isinstance(current_stock, list):
            current_stock = []
        product["stock"] = current_stock + items
        changes.append(f"stock +{len(items)}")
    if not changes:
        return False, "ChÆ°a cÃ³ thay Ä‘á»•i nÃ o Ä‘á»ƒ lÆ°u."
    await save_data(force=True, tables=[PRODUCTS_FILE])
    return True, f"Da cap nhat {product_id}: {', '.join(changes)}."


async def _admin_web_action_product_stock(form):
    product_id = _admin_web_form_text(form, "product_id")
    product = products.get(product_id)
    if not isinstance(product, dict):
        return False, "Khong tim thay product_id."
    mode = _admin_web_form_text(form, "mode")
    if mode == "clear_stock":
        if product.get("requires_gmail") or product.get("is_supplier_source_resell") or product.get("is_social_source_service"):
            return False, "Chi xoa stock local cho san pham local stock."
        count = len(product.get("stock") or []) if isinstance(product.get("stock"), list) else 0
        product["stock"] = []
        await save_data(force=True, tables=[PRODUCTS_FILE])
        return True, f"Da xoa {count} stock local cua {product_id}."
    return False, "Thao tÃ¡c stock khÃ´ng há»£p lá»‡."


async def _admin_web_action_product_delete(form):
    product_id = _admin_web_form_text(form, "product_id")
    if not product_id:
        return False, "Thieu product_id."
    product = products.get(product_id)
    if not isinstance(product, dict):
        return False, "Khong tim thay product_id."
    product_name = str(product.get("name") or product_id)
    products.pop(product_id, None)
    await save_data(force=True, tables=[PRODUCTS_FILE])
    return True, f"Da xoa san pham {product_id}: {product_name}."


async def _admin_web_action_legacy_link(form):
    mode = _admin_web_form_text(form, "mode") or "replace"
    link_text = _admin_web_form_text(form, "link")
    links = [line.strip() for line in link_text.splitlines() if line.strip()]
    if mode in {"add", "replace", "delete"} and not links:
        return False, "Can nhap it nhat 1 link."
    if not isinstance(available_links, set):
        return False, "Kho link legacy khong hop le."
    if mode == "replace":
        available_links.clear()
        available_links.update(links)
        await save_data(force=True, tables=[LINKS_FILE])
        return True, f"Da thay kho link legacy bang {len(links)} link."
    if mode == "add":
        before = len(available_links)
        available_links.update(links)
        added = len(available_links) - before
        await save_data(force=True, tables=[LINKS_FILE])
        return True, f"Da them {added} link legacy. Tong hien tai: {len(available_links)}."
    if mode == "delete":
        removed = 0
        for link in links:
            if link in available_links:
                available_links.discard(link)
                removed += 1
        await save_data(force=True, tables=[LINKS_FILE])
        return True, f"Da xoa {removed} link legacy. Con lai: {len(available_links)}."
    if mode == "clear":
        count = len(available_links)
        available_links.clear()
        await save_data(force=True, tables=[LINKS_FILE])
        return True, f"Da xoa toan bo {count} link legacy."
    return False, "Thao tac kho link legacy khong hop le."


async def _admin_web_action_api_partner(form):
    mode = _admin_web_form_text(form, "mode") or "topup"
    target = _admin_web_form_text(form, "target")
    amount = _admin_web_int(_admin_web_form_text(form, "amount"), 0)
    if mode == "create":
        partner_name = target or f"Partner{len(api_keys) + 1}"
        new_key = _api_generate_partner_key()
        api_keys[new_key] = {
            "name": partner_name,
            "balance": max(0, int(amount or 0)),
            "enabled": True,
            "rate_limit_per_minute": 60,
            "allowed_ips": [],
            "low_balance_threshold": 100000,
            "low_balance_alert_enabled": True,
            "created_at": int(time.time()),
        }
        await save_data(force=True, tables=[API_KEYS_FILE])
        return True, f"ÄÃ£ táº¡o API partner {partner_name}. Key má»›i (chá»‰ hiá»ƒn thá»‹ láº§n nÃ y): {new_key}"

    api_key = _admin_web_find_api_key(target)
    if not api_key:
        return False, "KhÃ´ng tÃ¬m tháº¥y API key/partner."
    data = _api_normalize_partner_key(api_key)
    if not isinstance(data, dict):
        return False, "Dá»¯ liá»‡u API key khÃ´ng há»£p lá»‡."

    partner_name = data.get("name") or api_key
    if mode in {"topup", "subtract", "set_balance"}:
        if mode != "set_balance" and amount <= 0:
            return False, "Sá»‘ tiá»n pháº£i lá»›n hÆ¡n 0."
        if mode == "set_balance" and amount < 0:
            return False, "Sá»‘ dÆ° khÃ´ng Ä‘Æ°á»£c Ã¢m."
        if mode == "set_balance":
            adjusted, new_balance, _ = await safe_api_set_balance(
                api_key, amount, save=True, reason=f"Admin web set {partner_name}",
                ledger_type="adjustment", admin_actor="admin_web",
            )
        else:
            delta = amount if mode == "topup" else -amount
            current = _api_get_partner_display_balance(api_key, data)
            if current + delta < 0:
                return False, "Sá»‘ dÆ° khÃ´ng Ä‘á»§ Ä‘á»ƒ trá»«."
            adjusted, new_balance, _ = await safe_api_adjust_balance(
                api_key, delta, save=True, reason=f"Admin web {mode} {partner_name}",
                ledger_type="deposit" if mode == "topup" else "adjustment", admin_actor="admin_web",
            )
        if not adjusted:
            return False, "KhÃ´ng cáº­p nháº­t Ä‘Æ°á»£c sá»‘ dÆ° partner."
        return True, f"ÄÃ£ cáº­p nháº­t {partner_name}: sá»‘ dÆ° má»›i {int(new_balance):,} VND."

    if mode == "configure":
        try:
            data["allowed_ips"] = _api_normalize_allowed_ips(_admin_web_form_text(form, "allowed_ips"))
        except ValueError as exc:
            return False, str(exc)
        data["rate_limit_per_minute"] = max(1, min(10000, _admin_web_int(_admin_web_form_text(form, "rate_limit"), 60)))
        data["low_balance_threshold"] = max(0, _admin_web_int(_admin_web_form_text(form, "low_balance_threshold"), 100000))
        data["low_balance_alert_enabled"] = bool(_admin_web_form_text(form, "alert_enabled"))
        data["admin_note"] = _admin_web_form_text(form, "admin_note")[:500]
        tier_mode = _admin_web_form_text(form, "tier_mode").lower()
        tier_override = _admin_web_form_text(form, "tier_override").lower()
        data["tier_mode"] = tier_mode if tier_mode in {"auto", "manual"} else "auto"
        data["tier_override"] = tier_override if tier_override in {tier["id"] for tier in API_PARTNER_TIERS} else "standard"
        data["updated_at"] = int(time.time())
        await save_data(force=True, tables=[API_KEYS_FILE])
        return True, f"ÄÃ£ lÆ°u báº£o máº­t, quota vÃ  tier pricing cho {partner_name}."

    if mode in {"disable", "revoke"}:
        data["enabled"] = False
        data["revoked_at"] = int(time.time())
        await save_data(force=True, tables=[API_KEYS_FILE])
        return True, f"ÄÃ£ thu há»“i API key cá»§a {partner_name}."
    if mode == "enable":
        if data.get("rotated_to"):
            return False, "Key cÅ© Ä‘Ã£ regenerate, khÃ´ng thá»ƒ báº­t láº¡i. HÃ£y dÃ¹ng key má»›i."
        data["enabled"] = True
        data.pop("revoked_at", None)
        await save_data(force=True, tables=[API_KEYS_FILE])
        return True, f"ÄÃ£ báº­t API key cá»§a {partner_name}."
    if mode == "regenerate":
        result = await _api_rotate_partner_key(api_key)
        if not result:
            return False, "KhÃ´ng regenerate Ä‘Æ°á»£c API key."
        new_key, new_data = result
        return True, f"ÄÃ£ regenerate {new_data.get('name') or partner_name}. Key má»›i (chá»‰ hiá»ƒn thá»‹ láº§n nÃ y): {new_key}"
    return False, "Thao tÃ¡c API partner khÃ´ng há»£p lá»‡."


async def _admin_web_action_order_tools(form):
    order_code = _admin_web_form_text(form, "order_code").upper()
    if not order_code:
        return False, "Ma don khong duoc rong."
    records = _admin_web_find_order_records(order_code)
    if not records:
        return False, "Khong tim thay ma don."
    mode = _admin_web_form_text(form, "mode") or "set_email"
    value = _admin_web_form_text(form, "value")
    if not value:
        return False, "GiÃ¡ trá»‹ cáº­p nháº­t khÃ´ng Ä‘Æ°á»£c rá»—ng."
    if mode == "set_email":
        try:
            is_valid_email = bool(EMAIL_REGEX.match(value))
        except Exception:
            is_valid_email = "@" in value and "." in value
        if not is_valid_email:
            return False, "Email khÃ´ng há»£p lá»‡."
        for _, record in records:
            record["email"] = value
            record["customer_email"] = value
            record["delivery_email"] = value
        label = "email"
    elif mode == "admin_note":
        for _, record in records:
            record["admin_note"] = value[:1000]
        label = "ghi chu"
    else:
        return False, "Thao tÃ¡c Ä‘Æ¡n hÃ ng khÃ´ng há»£p lá»‡."
    tables = sorted({table_name for table_name, _ in records})
    await save_data(force=True, tables=tables)
    return True, f"Da cap nhat {label} cho {order_code} ({len(records)} record)."


async def _admin_web_action_coupon(form):
    if not isinstance(coupons, dict):
        return False, "Dá»¯ liá»‡u coupon khÃ´ng há»£p lá»‡."
    mode = _admin_web_form_text(form, "mode") or "add"
    code = _admin_web_form_text(form, "code").upper()
    if not code:
        return False, "Ma coupon khong duoc rong."
    if mode == "delete":
        if code not in coupons:
            return False, "Khong tim thay coupon."
        coupons.pop(code, None)
        await save_data(force=True, tables=[COUPONS_FILE])
        return True, f"Da xoa coupon {code}."
    if mode != "add":
        return False, "Thao tÃ¡c coupon khÃ´ng há»£p lá»‡."
    quantity = _admin_web_int(_admin_web_form_text(form, "quantity"), 0)
    discount = _admin_web_int(_admin_web_form_text(form, "discount"), 0)
    days = _admin_web_int(_admin_web_form_text(form, "days"), 30)
    if quantity < 0 or discount < 0 or days < 0:
        return False, "So luong, giam tien va so ngay phai >= 0."
    expires = time.strftime("%d-%m-%Y", time.localtime(time.time() + (days * 86400)))
    previous_used = 0
    if isinstance(coupons.get(code), dict):
        previous_used = _admin_web_int(coupons[code].get("used"), 0)
    coupons[code] = {
        "discount": int(discount),
        "quantity": int(quantity),
        "expires": expires,
        "used": previous_used,
    }
    await save_data(force=True, tables=[COUPONS_FILE])
    return True, f"Da luu coupon {code}: giam {discount:,} VND, SL {quantity}, het han {expires}."


def _admin_web_update_env(key: str, value: str):
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists(): return
    content = env_path.read_text("utf-8")
    if f"\n{key}=" in content or content.startswith(f"{key}="):
        content = re.sub(rf"^{key}=.*$", f"{key}={value}", content, flags=re.MULTILINE)
    else:
        content += f"\n{key}={value}\n"
    env_path.write_text(content, "utf-8")

async def _admin_web_action_system_toggle(form):
    global MAINTENANCE_MODE, AI_AUTO_REPLY
    mode = _admin_web_form_text(form, "mode")
    changed = []
    if mode == "maintenance_on":
        MAINTENANCE_MODE = True
        changed.append("MAINTENANCE_MODE")
        message = "Da bat maintenance mode."
    elif mode == "maintenance_off":
        MAINTENANCE_MODE = False
        changed.append("MAINTENANCE_MODE")
        message = "Da tat maintenance mode."
    elif mode == "ai_on":
        AI_AUTO_REPLY = True
        changed.append("AI_AUTO_REPLY")
        message = "Da bat AI auto reply."
    elif mode == "ai_off":
        AI_AUTO_REPLY = False
        changed.append("AI_AUTO_REPLY")
        message = "Da tat AI auto reply."
    elif mode in {"mbbank_on", "mbbank_off"}:
        import app.core.config_env as config_env
        val = mode == "mbbank_on"
        config_env.ENABLE_PAYMENT_MBBANK = val
        _admin_web_update_env("ENABLE_PAYMENT_MBBANK", "true" if val else "false")
        message = f"Da {'bat' if val else 'tat'} MBBank."
    elif mode in {"binance_on", "binance_off"}:
        import app.core.config_env as config_env
        val = mode == "binance_on"
        config_env.ENABLE_PAYMENT_BINANCE_SPOT = val
        _admin_web_update_env("ENABLE_PAYMENT_BINANCE_SPOT", "true" if val else "false")
        message = f"Da {'bat' if val else 'tat'} Binance Spot."
    else:
        return False, "Thao tÃ¡c há»‡ thá»‘ng khÃ´ng há»£p lá»‡."
    try:
        from app.core.runtime_loader import sync_runtime_bindings

        sync_runtime_bindings(globals(), changed)
    except Exception as sync_error:
        logger.warning(f"Admin web system sync skipped: {sync_error}")
    return True, message


async def _admin_web_action_pending_manual(form):
    mode = _admin_web_form_text(form, "mode") or "clear_one"
    if mode == "clear_all":
        count = len(pending_manual_orders)
        pending_manual_orders.clear()
        await save_data(force=True, tables=[PENDING_MANUAL_ORDERS_FILE])
        return True, f"Da xoa {count} don manual pending."
    if mode != "clear_one":
        return False, "Thao tÃ¡c pending manual khÃ´ng há»£p lá»‡."
    order_code = _admin_web_form_text(form, "order_code").upper()
    if not order_code:
        return False, "Can nhap ma don de xoa 1 pending manual."
    if order_code not in pending_manual_orders:
        return False, "Khong tim thay don pending manual."
    pending_manual_orders.pop(order_code, None)
    await save_data(force=True, tables=[PENDING_MANUAL_ORDERS_FILE])
    return True, f"Da xoa pending manual {order_code}."


async def _admin_web_action_support_update(form):
    entity = _admin_web_form_text(form, "entity")
    item_id = _admin_web_form_text(form, "item_id")
    status = _admin_web_form_text(form, "status") or "pending"
    admin_note = _admin_web_form_text(form, "admin_note")
    source_map = {
        "live_chat": (live_chats, LIVE_CHATS_FILE),
        "warranty": (warranty_claims, WARRANTY_CLAIMS_FILE),
        "withdrawal": (withdrawal_requests, WITHDRAWALS_FILE),
    }
    data, table_name = source_map.get(entity, ({}, ""))
    item = _admin_web_mapping_get(data, item_id)
    if not isinstance(data, dict) or not isinstance(item, dict):
        return False, "Khong tim thay ticket ho tro."
    target_key = item_id
    if target_key not in data and str(target_key).isdigit() and int(str(target_key)) in data:
        target_key = int(str(target_key))
    data[target_key]["status"] = status
    if admin_note:
        data[target_key]["admin_note"] = admin_note[:1000]
    data[target_key]["updated_at"] = int(time.time())
    data[target_key]["updated_by"] = "admin_web"
    await save_data(force=True, tables=[table_name])
    return True, f"Da cap nhat {entity} {item_id}: {status}."


async def _admin_web_action_ops_config_update(form):
    return False, "Cáº¥u hÃ¬nh thanh toÃ¡n lÃ  read-only trÃªn web. HÃ£y cáº­p nháº­t secret trong deployment environment rá»“i restart bot."


def _admin_web_category_exists(category_name: str) -> bool:
    name = str(category_name or "").strip()
    if not name:
        return False
    if name in store_categories:
        return True
    return any(
        isinstance(product, dict) and _admin_web_product_category(product) == name
        for product in products.values()
    )


def _admin_web_category_form_config(form, current=None) -> dict:
    config = dict(current or {})
    sort_text = _admin_web_form_text(form, "sort_order")
    if sort_text:
        config["sort_order"] = max(0, _admin_web_int(sort_text, 0))
    elif "sort_order" not in config:
        config["sort_order"] = len(store_categories) + 1
    config["emoji_id"] = _admin_web_form_text(form, "emoji_id")[:40]
    config["icon_url"] = _admin_web_form_text(form, "icon_url")[:500]
    if "hidden" in form:
        config["hidden"] = _admin_web_form_text(form, "hidden") in {"1", "true", "yes", "on"}
    else:
        config.setdefault("hidden", False)
    config["updated_at"] = int(time.time())
    return config


async def _admin_web_action_category_create(form):
    name = _admin_web_form_text(form, "category_name")
    if not name:
        return False, "TÃªn danh má»¥c khÃ´ng Ä‘Æ°á»£c rá»—ng."
    if len(name) > 100:
        return False, "TÃªn danh má»¥c quÃ¡ dÃ i."
    if _admin_web_category_exists(name):
        return False, "Danh má»¥c Ä‘Ã£ tá»“n táº¡i."
    store_categories[name] = _admin_web_category_form_config(form)
    await save_data(force=True, tables=[STORE_CATEGORIES_FILE])
    return True, f"ÄÃ£ thÃªm danh má»¥c {name}."


async def _admin_web_action_category_update(form):
    old_name = _admin_web_form_text(form, "category_name")
    new_name = _admin_web_form_text(form, "new_name") or old_name
    if not old_name or not _admin_web_category_exists(old_name):
        return False, "KhÃ´ng tÃ¬m tháº¥y danh má»¥c."
    if len(new_name) > 100:
        return False, "TÃªn danh má»¥c quÃ¡ dÃ i."
    if new_name != old_name and _admin_web_category_exists(new_name):
        return False, "TÃªn danh má»¥c má»›i Ä‘Ã£ tá»“n táº¡i."
    config = _admin_web_category_form_config(form, _admin_web_category_config(old_name))
    moved_products = 0
    if new_name != old_name:
        for product in products.values():
            if isinstance(product, dict) and _admin_web_product_category(product) == old_name:
                product["store_category"] = new_name
                product.pop("category_image_file_id", None)
                moved_products += 1
        old_image = _admin_web_category_image_path(old_name)
        if old_image is not None:
            new_image = ADMIN_WEB_CATEGORY_IMAGE_DIR / f"{_admin_web_category_slug(new_name)}{old_image.suffix.lower()}"
            if not new_image.exists():
                old_image.rename(new_image)
        store_categories.pop(old_name, None)
    store_categories[new_name] = config
    await save_data(force=True, tables=[STORE_CATEGORIES_FILE, PRODUCTS_FILE])
    return True, f"ÄÃ£ cáº­p nháº­t danh má»¥c {new_name} ({moved_products} sáº£n pháº©m Ä‘Æ°á»£c chuyá»ƒn)."


async def _admin_web_action_category_visibility(form):
    name = _admin_web_form_text(form, "category_name")
    if not _admin_web_category_exists(name):
        return False, "KhÃ´ng tÃ¬m tháº¥y danh má»¥c."
    mode = _admin_web_form_text(form, "mode")
    if mode not in {"hide", "show"}:
        return False, "Tráº¡ng thÃ¡i danh má»¥c khÃ´ng há»£p lá»‡."
    config = dict(_admin_web_category_config(name))
    config["hidden"] = mode == "hide"
    config.setdefault("sort_order", len(store_categories) + 1)
    config["updated_at"] = int(time.time())
    store_categories[name] = config
    await save_data(force=True, tables=[STORE_CATEGORIES_FILE])
    return True, f"ÄÃ£ {'áº©n' if mode == 'hide' else 'hiá»‡n'} danh má»¥c {name}."


async def _admin_web_action_category_delete(form):
    name = _admin_web_form_text(form, "category_name")
    fallback = "Sáº£n Pháº©m KhÃ¡c"
    if not _admin_web_category_exists(name):
        return False, "KhÃ´ng tÃ¬m tháº¥y danh má»¥c."
    if name == fallback:
        return False, "KhÃ´ng thá»ƒ xÃ³a danh má»¥c máº·c Ä‘á»‹nh."
    moved = 0
    for product in products.values():
        if isinstance(product, dict) and _admin_web_product_category(product) == name:
            product["store_category"] = fallback
            product.pop("category_image_file_id", None)
            moved += 1
    store_categories.pop(name, None)
    image_path = _admin_web_category_image_path(name)
    if image_path is not None:
        image_path.unlink()
    await save_data(force=True, tables=[STORE_CATEGORIES_FILE, PRODUCTS_FILE])
    return True, f"ÄÃ£ xÃ³a danh má»¥c {name}; chuyá»ƒn {moved} sáº£n pháº©m sang {fallback}."


def _admin_web_action_registry():
    return {
        "user_balance": _admin_web_action_user_balance,
        "user_ban": _admin_web_action_user_ban,
        "user_profile": _admin_web_action_user_profile,
        "product_create": _admin_web_action_product_create,
        "product_update": _admin_web_action_product_update,
        "product_stock": _admin_web_action_product_stock,
        "product_delete": _admin_web_action_product_delete,
        "legacy_link": _admin_web_action_legacy_link,
        "api_partner": _admin_web_action_api_partner,
        "order_tools": _admin_web_action_order_tools,
        "coupon": _admin_web_action_coupon,
        "system_toggle": _admin_web_action_system_toggle,
        "pending_manual": _admin_web_action_pending_manual,
        "ops_config_update": _admin_web_action_ops_config_update,
        "support_update": _admin_web_action_support_update,
        "supplier_catalog_resell": _admin_web_action_supplier_catalog_resell,
        "product_image_delete": _admin_web_action_product_image_delete,
        "category_image_delete": _admin_web_action_category_image_delete,
        "category_create": _admin_web_action_category_create,
        "category_update": _admin_web_action_category_update,
        "category_visibility": _admin_web_action_category_visibility,
        "category_delete": _admin_web_action_category_delete,
    }


async def _admin_web_dispatch_action(form, request=None):
    action = _admin_web_form_text(form, "action")
    try:
        handler = _admin_web_action_registry().get(action)
        if handler is None:
            ok, message = False, "Action khÃ´ng há»£p lá»‡."
        else:
            ok, message = await handler(form)
    except Exception as exc:
        logger.exception("Admin web action failed")
        ok, message = False, f"Loi action: {type(exc).__name__}: {exc}"

    try:
        event = _admin_web_record_action(action, ok, message, form=form, request=request)
        await save_data(force=True, tables=[ADMIN_ACTION_LOG_FILE])
        await _admin_web_notify_action_event(event)
    except Exception:
        logger.exception("Admin web audit save failed")
    return ok, message


async def _admin_web_action_product_image_delete(form):
    product_id = _admin_web_form_text(form, "product_id")
    product = products.get(product_id)
    if not isinstance(product, dict):
        return False, "Khong tim thay product_id."
    image_path = _admin_web_product_image_path(product_id)
    deleted = False
    if image_path is not None:
        try:
            image_path.unlink()
            deleted = True
        except Exception as exc:
            return False, f"Khong xoa duoc anh: {type(exc).__name__}: {exc}"
    product.pop("image_local", None)
    product.pop("image_file_id", None)
    if deleted:
        await save_data(force=True, tables=[PRODUCTS_FILE])
        return True, f"Da xoa anh san pham {product_id}."
    return False, "San pham chua co anh."


async def _admin_web_action_category_image_delete(form):
    category_name = _admin_web_form_text(form, "category_name")
    if not category_name:
        return False, "Thieu ten danh muc."
    image_path = _admin_web_category_image_path(category_name)
    if image_path is None:
        return False, "Danh muc chua co anh."
    try:
        image_path.unlink()
    except Exception as exc:
        return False, f"Khong xoa duoc anh: {type(exc).__name__}: {exc}"
    cleared = 0
    for pid, prod in list(products.items()):
        if not isinstance(prod, dict):
            continue
        if _admin_web_product_category(prod) != category_name:
            continue
        if prod.pop("category_image_file_id", None) is not None:
            cleared += 1
    if cleared:
        await save_data(force=True, tables=[PRODUCTS_FILE])
    return True, f"Da xoa anh danh muc {category_name} (reset {cleared} cache)."


@app.get("/admin/assets/banner.png", include_in_schema=False)
async def admin_web_banner_asset():
    return FileResponse(ADMIN_WEB_BANNER_PATH, media_type="image/png")


@app.get("/admin/product_image", include_in_schema=False)
async def admin_web_product_image_view(request: Request):
    _admin_web_require(request)
    product_id = str(request.query_params.get("id") or "").strip()
    image_path = _admin_web_product_image_path(product_id)
    if image_path is None:
        raise HTTPException(status_code=404, detail="Image not found")
    ext = image_path.suffix.lower().lstrip(".")
    media = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    return FileResponse(image_path, media_type=media)


@app.get("/admin/category_image", include_in_schema=False)
async def admin_web_category_image_view(request: Request):
    _admin_web_require(request)
    category_name = str(request.query_params.get("name") or "").strip()
    image_path = _admin_web_category_image_path(category_name)
    if image_path is None:
        raise HTTPException(status_code=404, detail="Image not found")
    ext = image_path.suffix.lower().lstrip(".")
    media = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    return FileResponse(image_path, media_type=media)


@app.post("/admin/category_image_upload", include_in_schema=False)
async def admin_web_category_image_upload(request: Request):
    _admin_web_require(request)
    _admin_web_require_same_origin(request)
    form = await request.form()
    _admin_web_require_csrf(request, form)
    category_name = str(form.get("category_name") or "").strip()
    image = form.get("image")
    ok, message = False, ""
    if not _admin_web_category_exists(category_name):
        message = "KhÃ´ng tÃ¬m tháº¥y danh má»¥c."
    elif image is None or not hasattr(image, "read"):
        message = "ChÆ°a chá»n file áº£nh."
    else:
        filename = str(getattr(image, "filename", "") or "").lower()
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        content_type = str(getattr(image, "content_type", "") or "").lower()
        if content_type == "image/jpeg":
            ext = "jpg"
        elif content_type == "image/png":
            ext = "png"
        elif content_type == "image/webp":
            ext = "webp"
        if ext not in ADMIN_WEB_PRODUCT_IMAGE_EXTS:
            message = "Äá»‹nh dáº¡ng khÃ´ng há»— trá»£; chá»‰ nháº­n JPG, PNG hoáº·c WEBP."
        else:
            data = await image.read()
            if not data:
                message = "File áº£nh rá»—ng."
            elif len(data) > ADMIN_WEB_PRODUCT_IMAGE_MAX_BYTES:
                message = "áº¢nh quÃ¡ lá»›n; tá»‘i Ä‘a 8 MB."
            else:
                slug = _admin_web_category_slug(category_name)
                for old_ext in ADMIN_WEB_PRODUCT_IMAGE_EXTS:
                    old_path = ADMIN_WEB_CATEGORY_IMAGE_DIR / f"{slug}.{old_ext}"
                    if old_path.is_file():
                        old_path.unlink()
                (ADMIN_WEB_CATEGORY_IMAGE_DIR / f"{slug}.{ext}").write_bytes(data)
                for product in products.values():
                    if isinstance(product, dict) and _admin_web_product_category(product) == category_name:
                        product.pop("category_image_file_id", None)
                await save_data(force=True, tables=[PRODUCTS_FILE])
                ok, message = True, f"ÄÃ£ táº£i áº£nh cho danh má»¥c {category_name}."
    notice_class = "success" if ok else "danger"
    body = f'<div class="notice {notice_class}">{escape(message)}</div>' + _admin_web_categories_body(request)
    return HTMLResponse(_admin_web_layout("Dino Admin â€” Danh Má»¥c", body, request))


@app.post("/admin/product_image_upload", include_in_schema=False)
async def admin_web_product_image_upload(request: Request):
    _admin_web_require(request)
    _admin_web_require_same_origin(request)
    form = await request.form()
    _admin_web_require_csrf(request, form)
    product_id = str(form.get("product_id") or "").strip()
    apply_to_category = str(form.get("apply_to_category") or "").strip()
    category_name_override = str(form.get("category_name_override") or "").strip()
    selected_products = [str(v) for v in form.getlist("selected_products") if str(v).strip()]
    image = form.get("image")

    if image is None or not hasattr(image, "read"):
        body = _admin_web_product_detail_body(request, product_id, message="Chua chon file anh.", is_error=True)
        return HTMLResponse(_admin_web_layout("Dino Admin Web", body, request))

    product = products.get(product_id)
    if not isinstance(product, dict):
        body = _admin_web_dashboard_body(request, message="Khong tim thay product_id.", is_error=True)
        return HTMLResponse(_admin_web_layout("Dino Admin Web", body, request))

    apply_category = bool(apply_to_category)
    override_name = category_name_override
    if apply_category:
        category_name = override_name or _admin_web_product_category(product)
    else:
        category_name = ""
    if apply_category and not category_name:
        body = _admin_web_product_detail_body(request, product_id, message="Vui long nhap ten danh muc o o 'Ten danh muc ap dung'.", is_error=True)
        return HTMLResponse(_admin_web_layout("Dino Admin Web", body, request))

    filename = (image.filename or "").lower()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    content_type = (image.content_type or "").lower()
    if content_type == "image/jpeg" and ext not in ADMIN_WEB_PRODUCT_IMAGE_EXTS:
        ext = "jpg"
    elif content_type == "image/png":
        ext = "png"
    elif content_type == "image/webp":
        ext = "webp"
    if ext not in ADMIN_WEB_PRODUCT_IMAGE_EXTS:
        body = _admin_web_product_detail_body(request, product_id, message="Dinh dang anh khong ho tro (chi nhan jpg/png/webp).", is_error=True)
        return HTMLResponse(_admin_web_layout("Dino Admin Web", body, request))

    data = await image.read()
    if not data:
        body = _admin_web_product_detail_body(request, product_id, message="File anh rong.", is_error=True)
        return HTMLResponse(_admin_web_layout("Dino Admin Web", body, request))
    if len(data) > ADMIN_WEB_PRODUCT_IMAGE_MAX_BYTES:
        body = _admin_web_product_detail_body(request, product_id, message="Anh qua lon (toi da 8MB).", is_error=True)
        return HTMLResponse(_admin_web_layout("Dino Admin Web", body, request))

    if apply_category:
        slug = _admin_web_category_slug(category_name)
        for old_ext in ADMIN_WEB_PRODUCT_IMAGE_EXTS:
            old_path = ADMIN_WEB_CATEGORY_IMAGE_DIR / f"{slug}.{old_ext}"
            if old_path.is_file():
                try:
                    old_path.unlink()
                except Exception:
                    pass
        target = ADMIN_WEB_CATEGORY_IMAGE_DIR / f"{slug}.{ext}"
        try:
            target.write_bytes(data)
        except Exception as exc:
            body = _admin_web_product_detail_body(request, product_id, message=f"Khong luu duoc anh danh muc: {type(exc).__name__}: {exc}", is_error=True)
            return HTMLResponse(_admin_web_layout("Dino Admin Web", body, request))

        # Invalidate cached telegram file_id on every product whose effective category matches,
        # so the bot re-uploads from the new on-disk image.
        cleared = 0
        for pid, prod in list(products.items()):
            if not isinstance(prod, dict):
                continue
            if _admin_web_product_category(prod) != category_name:
                continue
            if prod.pop("category_image_file_id", None) is not None:
                cleared += 1
        await save_data(force=True, tables=[PRODUCTS_FILE])

        try:
            event = _admin_web_record_action(
                "category_image_upload",
                True,
                f"Da tai anh danh muc {category_name} ({len(data)} bytes), reset cache {cleared} san pham.",
                form={"product_id": product_id, "category_name": category_name},
                request=request,
            )
            await save_data(force=True, tables=[ADMIN_ACTION_LOG_FILE])
            await _admin_web_notify_action_event(event)
        except Exception:
            logger.exception("Admin web audit save failed")

        body = _admin_web_product_detail_body(request, product_id, message=f"Da tai anh cho danh muc {category_name}.", is_error=False)
        return HTMLResponse(_admin_web_layout("Dino Admin Web", body, request))

    # Per-product upload â€” copies the same image to each selected product.
    # selected_products is a list of product_ids ticked in the preview table.
    # If the list is empty, fall back to applying only to the current product.
    targets = [pid for pid in selected_products if pid in products and isinstance(products.get(pid), dict)]
    if not targets:
        targets = [product_id]
    # Always include the current product the form was submitted from
    if product_id not in targets:
        targets.append(product_id)

    saved = []
    errors = []
    for pid in targets:
        prod = products.get(pid)
        if not isinstance(prod, dict):
            continue
        for old_ext in ADMIN_WEB_PRODUCT_IMAGE_EXTS:
            old_path = ADMIN_WEB_PRODUCT_IMAGE_DIR / f"{pid}.{old_ext}"
            if old_path.is_file():
                try:
                    old_path.unlink()
                except Exception:
                    pass
        target = ADMIN_WEB_PRODUCT_IMAGE_DIR / f"{pid}.{ext}"
        try:
            target.write_bytes(data)
        except Exception as exc:
            errors.append(f"{pid}: {type(exc).__name__}: {exc}")
            continue
        prod["image_local"] = target.name
        prod.pop("image_file_id", None)  # invalidate cached telegram file_id
        saved.append(pid)

    if saved:
        await save_data(force=True, tables=[PRODUCTS_FILE])

    summary_msg = f"Da tai anh cho {len(saved)} san pham ({len(data)} bytes/san pham)."
    if errors:
        summary_msg += f" Loi {len(errors)}: " + "; ".join(errors[:3])

    try:
        event = _admin_web_record_action(
            "product_image_upload",
            bool(saved),
            summary_msg,
            form={"product_id": product_id, "count": len(saved)},
            request=request,
        )
        await save_data(force=True, tables=[ADMIN_ACTION_LOG_FILE])
        await _admin_web_notify_action_event(event)
    except Exception:
        logger.exception("Admin web audit save failed")

    body = _admin_web_product_detail_body(request, product_id, message=summary_msg, is_error=not saved)
    return HTMLResponse(_admin_web_layout("Dino Admin Web", body, request))


async def _admin_web_action_supplier_catalog_resell(form):
    shop_product_id = _admin_web_form_text(form, "shop_product_id")
    mode = _admin_web_form_text(form, "mode") or "enable"
    if not shop_product_id:
        return False, "Thieu shop_product_id."

    existing_id = ""
    for pid, product in products.items():
        if not isinstance(product, dict):
            continue
        if product.get("resell_source") == "supplier_catalog" and str(product.get("supplier_source_variant_id") or product.get("supplier_source_product_id") or "") == str(shop_product_id):
            existing_id = str(pid)
            break

    if mode == "disable":
        if not existing_id:
            return False, "San pham SupplierCatalog nay chua co trong bot."
        products[existing_id]["resell_enabled"] = False
        await save_data(force=True, tables=[PRODUCTS_FILE])
        return True, f"Da tat SupplierCatalog resell {existing_id}."

    try:
        markup = float(_admin_web_form_text(form, "markup") or 30)
        if markup < 0:
            raise ValueError("markup")
    except ValueError:
        return False, "Markup phai la so >= 0."

    custom_name = _admin_web_form_text(form, "custom_name")
    try:
        from app.integrations.supplier_source import supplier_catalog_get_product_info
        result = await supplier_catalog_get_product_info(shop_product_id, log_error=False)
    except Exception as exc:
        return False, f"Loi goi SupplierCatalog API: {type(exc).__name__}: {exc}"

    if not result.get("success"):
        return False, f"Khong lay duoc san pham SupplierCatalog: {result.get('error') or 'unknown_error'}"

    data = result.get("data", {}) if isinstance(result.get("data"), dict) else {}
    source_price = _admin_web_int(data.get("price"), 0)
    stock = _admin_web_int(data.get("stock"), 0)
    selling_price = int(source_price * (1 + markup / 100))
    api_description = str(data.get("description") or "").strip()
    custom_description = _admin_web_form_text(form, "custom_description")
    final_description = custom_description or api_description or "<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> TÃ i khoáº£n chÃ­nh hÃ£ng\n<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“§</tg-emoji> Giao hÃ ng tá»± Ä‘á»™ng qua Telegram"

    if existing_id:
        product_id = existing_id
        product = products[product_id]
        product.update({
            "name": custom_name or data.get("productTitle") or product.get("name") or f"SupplierCatalog #{shop_product_id}",
            "price": selling_price,
            "description": final_description,
            "supplier_source_price": source_price,
            "markup_percent": markup,
            "supplier_source_stock": stock,
            "resell_enabled": True,
        })
        message = f"Da bat/cap nhat SupplierCatalog resell {product_id}."
    else:
        import uuid
        product_id = f"resell_shop_{str(uuid.uuid4())[:8]}"
        products[product_id] = {
            "name": custom_name or data.get("productTitle") or f"SupplierCatalog #{shop_product_id}",
            "price": selling_price,
            "description": final_description,
            "duration": "Theo thÃ´ng tin sáº£n pháº©m",
            "warranty": "Báº£o hÃ nh theo quy Ä‘á»‹nh",
            "requires_gmail": False,
            "stock": [],
            "is_supplier_source_resell": True,
            "resell_source": "supplier_catalog",
            "supplier_source_product_id": str(shop_product_id),
            "supplier_source_variant_id": str(shop_product_id),
            "supplier_source_price": source_price,
            "markup_percent": markup,
            "supplier_source_stock": stock,
            "supplier_catalog_currency": "vnd",
            "resell_enabled": True,
            "created_at": time.time(),
        }
        message = f"Da them SupplierCatalog resell {product_id}."

    await save_data(force=True, tables=[PRODUCTS_FILE])
    return True, message


def _admin_web_resell_body(request):
    key_query = _admin_web_key_query(request)
    supplier_catalog_count = 0
    supplier_source_count = 0
    ctt_count = 0
    for product in products.values():
        if not isinstance(product, dict):
            continue
        source = str(product.get("resell_source") or "supplier_source").lower()
        if source == "supplier_catalog":
            supplier_catalog_count += 1
        elif source == "social_source" or product.get("is_ctt_service"):
            ctt_count += 1
        elif product.get("is_supplier_source_resell"):
            supplier_source_count += 1
    return f"""
<section class="module-section">
  <div class="section-head">
    <div>
      <h2>Quáº£n lÃ½ API Resell</h2>
      <p>Chá»n nguá»“n API cáº§n quáº£n lÃ½. Báº¥m vÃ o Ä‘Ã¢u ra Ä‘Ãºng khu Ä‘Ã³, khá»i lá»¥c command rá»‘i máº¯t.</p>
    </div>
    <span class="tag write">resell hub</span>
  </div>
  <div class="stats-grid">
    <a class="stat-card" href="/admin/supplier_catalog{key_query}" style="text-decoration:none;color:inherit;">
      <small>SUPPLIER_CATALOG</small>
      <strong>{supplier_catalog_count}</strong>
      <span>Tick sáº£n pháº©m, chá»‰nh %, tÃªn, mÃ´ táº£, báº­t/táº¯t khá»i bot.</span>
    </a>
    <a class="stat-card" href="/admin/commands{key_query}#add_resell" style="text-decoration:none;color:inherit;">
      <small>SUPPLIER_SOURCE</small>
      <strong>{supplier_source_count}</strong>
      <span>Quáº£n lÃ½ lá»‡nh SupplierSource: add/list/edit markup/sync/xÃ³a.</span>
    </a>
    <a class="stat-card" href="/admin/commands{key_query}#add_ctt" style="text-decoration:none;color:inherit;">
      <small>SOCIAL_SOURCE</small>
      <strong>{ctt_count}</strong>
      <span>Quáº£n lÃ½ dá»‹ch vá»¥ SOCIAL_SOURCE: add/list/sync/balance/xÃ³a.</span>
    </a>
  </div>
</section>
<section class="module-section">
  <div class="section-head"><div><h2>Lá»‘i táº¯t thao tÃ¡c</h2><p>CÃ¡c nÃºt nhanh Ä‘á»ƒ nháº£y Ä‘Ãºng trang quáº£n trá»‹ API.</p></div></div>
  <div class="toolbar" style="gap:10px;flex-wrap:wrap;">
    <a class="button" href="/admin/supplier_catalog{key_query}">Má»Ÿ SupplierCatalog picker</a>
    <a class="button" href="/admin/commands{key_query}">Má»Ÿ lá»‡nh SupplierSource/SOCIAL_SOURCE</a>
    <a class="button" href="/admin{key_query}#api-partner">Vá» API partner</a>
  </div>
</section>
"""


@app.get("/admin/resell", tags=["Admin"])
async def admin_web_resell(request: Request):
    _admin_web_require(request)
    await _admin_web_notify_login(request)
    return HTMLResponse(_admin_web_layout("Dino Admin â€” API Resell", _admin_web_resell_body(request), request))


def _admin_web_supplier_catalog_body(request, message: str | None = None, is_error: bool = False):
    return_msg = ""
    if message:
        return_msg = f'<div class="alert {"error" if is_error else "success"}">{escape(message)}</div>'
    return f"""
<section class="module-section supplier_catalog-page">
  <style>
    .supplier_catalog-page {{ position:relative; overflow:hidden; border-radius:28px; padding:0; background:linear-gradient(135deg,rgba(15,23,42,.96),rgba(30,41,59,.92) 46%,rgba(8,47,73,.94)); color:#eaf6ff; box-shadow:0 28px 80px rgba(2,8,23,.35); }}
    .supplier_catalog-page::before {{ content:""; position:absolute; inset:-120px -90px auto auto; width:320px; height:320px; border-radius:999px; background:radial-gradient(circle,rgba(34,211,238,.42),transparent 68%); filter:blur(8px); pointer-events:none; }}
    .supplier_catalog-page::after {{ content:""; position:absolute; left:-120px; bottom:-150px; width:360px; height:360px; border-radius:999px; background:radial-gradient(circle,rgba(168,85,247,.32),transparent 66%); pointer-events:none; }}
    .supplier_catalog-hero {{ position:relative; z-index:1; padding:24px; border-bottom:1px solid rgba(255,255,255,.12); background:linear-gradient(135deg,rgba(255,255,255,.12),rgba(255,255,255,.04)); backdrop-filter:blur(18px); }}
    .supplier_catalog-hero-top {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px; flex-wrap:wrap; }}
    .supplier_catalog-kicker {{ display:inline-flex; align-items:center; gap:8px; padding:7px 11px; border-radius:999px; color:#a7f3d0; background:rgba(16,185,129,.14); border:1px solid rgba(110,231,183,.28); font-size:12px; font-weight:900; letter-spacing:.08em; text-transform:uppercase; }}
    .supplier_catalog-hero h2 {{ margin:12px 0 8px; font-size:clamp(28px,4vw,46px); line-height:.98; letter-spacing:-.055em; color:#fff; text-shadow:0 12px 34px rgba(0,0,0,.24); }}
    .supplier_catalog-hero p {{ max-width:760px; margin:0; color:rgba(226,242,255,.78); font-size:15px; line-height:1.65; }}
    .supplier_catalog-pills {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:18px; }}
    .supplier_catalog-pill {{ padding:9px 12px; border-radius:999px; border:1px solid rgba(255,255,255,.14); background:rgba(255,255,255,.08); color:#e0f2fe; font-size:12px; font-weight:800; }}
    .supplier_catalog-status-orb {{ width:74px; height:74px; border-radius:24px; display:grid; place-items:center; font-size:32px; background:linear-gradient(135deg,#22d3ee,#6366f1 58%,#a855f7); box-shadow:0 18px 45px rgba(34,211,238,.28), inset 0 1px 0 rgba(255,255,255,.4); transform:rotate(-4deg); }}
    .supplier_catalog-content {{ position:relative; z-index:1; padding:20px; }}
    .supplier_catalog-toolbar {{ display:flex; gap:12px; align-items:center; margin-bottom:16px; padding:12px; border:1px solid rgba(255,255,255,.12); border-radius:20px; background:rgba(255,255,255,.08); backdrop-filter:blur(14px); }}
    .supplier_catalog-search-wrap {{ position:relative; flex:1; }}
    .supplier_catalog-search-wrap::before {{ content:"ðŸ”Ž"; position:absolute; left:16px; top:50%; transform:translateY(-50%); opacity:.72; z-index:1; }}
    .supplier_catalog-toolbar input {{ width:100%; min-height:48px; padding:0 16px 0 46px; border-radius:16px; border:1px solid rgba(255,255,255,.16); background:rgba(15,23,42,.58); color:#fff; outline:none; box-sizing:border-box; box-shadow:inset 0 1px 0 rgba(255,255,255,.08); }}
    .supplier_catalog-toolbar input::placeholder {{ color:rgba(226,232,240,.62); }}
    .supplier_catalog-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(335px,1fr)); gap:16px; }}
    .supplier_catalog-card {{ position:relative; border:1px solid rgba(255,255,255,.14); border-radius:24px; padding:18px; background:linear-gradient(180deg,rgba(255,255,255,.94),rgba(248,250,252,.88)); color:#0f172a; box-shadow:0 22px 52px rgba(2,8,23,.22); overflow:hidden; transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease; }}
    .supplier_catalog-card::before {{ content:""; position:absolute; inset:0 0 auto 0; height:4px; background:linear-gradient(90deg,#22d3ee,#6366f1,#a855f7,#f59e0b); }}
    .supplier_catalog-card:hover {{ transform:translateY(-3px); box-shadow:0 28px 70px rgba(2,8,23,.28); border-color:rgba(34,211,238,.42); }}
    .supplier_catalog-card-head {{ display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:14px; }}
    .supplier_catalog-title {{ min-width:0; }}
    .supplier_catalog-title b {{ display:block; line-height:1.32; overflow-wrap:anywhere; font-size:16px; letter-spacing:-.015em; }}
    .supplier_catalog-title small {{ display:block; margin-top:6px; color:#64748b; overflow-wrap:anywhere; font-weight:700; }}
    .supplier_catalog-id {{ flex:0 0 auto; padding:7px 10px; border-radius:12px; background:#eef2ff; color:#3730a3; border:1px solid #c7d2fe; font-weight:900; }}
    .supplier_catalog-metrics {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:9px; margin:14px 0; }}
    .supplier_catalog-metric {{ border:1px solid #e2e8f0; border-radius:16px; padding:11px; background:linear-gradient(180deg,#fff,#f8fafc); min-width:0; box-shadow:inset 0 1px 0 rgba(255,255,255,.9); }}
    .supplier_catalog-metric small {{ display:block; color:#64748b; font-size:11px; margin-bottom:5px; font-weight:900; text-transform:uppercase; letter-spacing:.04em; }}
    .supplier_catalog-metric strong, .supplier_catalog-metric span {{ display:block; overflow-wrap:anywhere; }}
    .supplier_catalog-sell-price {{ color:#0f766e; }}
    .supplier_catalog-form {{ display:grid; grid-template-columns:96px minmax(0,1fr); gap:9px; align-items:center; }}
    .supplier_catalog-form label {{ font-size:12px; color:#475569; font-weight:900; }}
    .supplier_catalog-form input, .supplier_catalog-form textarea {{ width:100%; min-width:0; box-sizing:border-box; border:1px solid #dbe4ef; border-radius:14px; background:#fff; color:#0f172a; padding:11px 12px; outline:none; transition:border-color .16s ease, box-shadow .16s ease; }}
    .supplier_catalog-form input:focus, .supplier_catalog-form textarea:focus {{ border-color:#22d3ee; box-shadow:0 0 0 4px rgba(34,211,238,.16); }}
    .supplier_catalog-actions {{ grid-column:1/-1; display:flex; gap:9px; flex-wrap:wrap; margin-top:6px; }}
    .supplier_catalog-actions button {{ flex:1 1 140px; min-height:44px; border-radius:14px; font-weight:900; box-shadow:0 12px 26px rgba(37,99,235,.18); }}
    .supplier_catalog-actions form {{ flex:1 1 140px; display:flex; }}
    .supplier_catalog-actions form button {{ width:100%; }}
    .supplier_catalog-desc {{ grid-column:1/-1; margin-top:6px; border:1px dashed #cbd5e1; border-radius:16px; padding:0 12px 10px; background:#f8fafc; }}
    .supplier_catalog-desc summary {{ cursor:pointer; font-weight:900; padding:11px 0; color:#334155; }}
    .supplier_catalog-desc textarea {{ min-height:104px; resize:vertical; }}
    @media (max-width:560px) {{
      .supplier_catalog-page {{ border-radius:20px; }}
      .supplier_catalog-hero {{ padding:18px; }}
      .supplier_catalog-content {{ padding:14px; }}
      .supplier_catalog-status-orb {{ width:58px; height:58px; border-radius:18px; font-size:26px; }}
      .supplier_catalog-grid {{ grid-template-columns:1fr; }}
      .supplier_catalog-card {{ padding:15px; border-radius:20px; }}
      .supplier_catalog-metrics {{ grid-template-columns:1fr 1fr; }}
      .supplier_catalog-metric:last-child {{ grid-column:1/-1; }}
      .supplier_catalog-form {{ grid-template-columns:1fr; }}
      .supplier_catalog-actions {{ flex-direction:column; }}
      .supplier_catalog-actions button, .supplier_catalog-actions form {{ width:100%; flex:auto; }}
    }}
  </style>
  <div class="supplier_catalog-hero">
    <div class="supplier_catalog-hero-top">
      <div>
        <span class="supplier_catalog-kicker">âš¡ one-click supplier control</span>
        <h2>SupplierCatalog Resell</h2>
        <p>Chá»n sáº£n pháº©m tá»« API nguá»“n, chá»‰nh markup, tÃªn bÃ¡n vÃ  mÃ´ táº£ trong má»™t giao diá»‡n card xá»‹n hÆ¡n â€” dÃ¹ng ngon trÃªn PC láº«n mobile, khÃ´ng cÃ²n máº¥t nÃºt khÃ³ chá»‹u ná»¯a.</p>
        <div class="supplier_catalog-pills">
          <span class="supplier_catalog-pill">Auto sync giÃ¡</span>
          <span class="supplier_catalog-pill">Responsive mobile</span>
          <span class="supplier_catalog-pill">Báº­t / táº¯t tá»©c thÃ¬</span>
        </div>
      </div>
      <div class="supplier_catalog-status-orb">ðŸ¦–</div>
    </div>
  </div>
  <div class="supplier_catalog-content">
    {return_msg}
    <div class="supplier_catalog-toolbar"><div class="supplier_catalog-search-wrap"><input id="supplier_catalog-filter" placeholder="TÃ¬m Grok, Gmail, Netflix, Capcut..." oninput="filterShopbotRows()"></div></div>
    <div id="supplier_catalog-list"><p class="muted">Äang táº£i SupplierCatalog API...</p></div>
  </div>
</section>
<script>
const supplier_catalogKeyQuery = {json.dumps(_admin_web_key_query(request))};
const supplier_catalogActionUrl = '/admin/action' + supplier_catalogKeyQuery;
function money(v) {{ return (Number(v || 0)).toLocaleString('vi-VN') + ' VND'; }}
function esc(s) {{ return String(s ?? '').replace(/[&<>\"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}}[c])); }}
async function loadShopbotProducts() {{
  const box = document.getElementById('supplier_catalog-list');
  try {{
    const res = await fetch('/api/admin/supplier_catalog/products' + supplier_catalogKeyQuery);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'API error');
    const cards = data.products.map(p => {{
      const mode = p.enabled ? 'update' : 'enable';
      const btn = p.enabled ? 'LÆ°u chá»‰nh sá»­a' : 'Báº­t lÃªn bot';
      const dangerForm = p.enabled ? `
        <form method="post" action="${{supplier_catalogActionUrl}}">
          <input type="hidden" name="action" value="supplier_catalog_resell">
          <input type="hidden" name="mode" value="disable">
          <input type="hidden" name="shop_product_id" value="${{esc(p.id)}}">
          <button type="submit" class="danger">Táº¯t khá»i bot</button>
        </form>` : '';
      const markup = Number(p.markup_percent || 30);
      const sourcePrice = Number(p.price_vnd || 0);
      const sellPrice = Math.round(sourcePrice * (1 + markup / 100));
      const description = p.local_description || p.description || '';
      return `<article class="supplier_catalog-card data-row" data-search="${{esc((p.name || '') + ' ' + p.id + ' ' + description)}}">
        <div class="supplier_catalog-card-head">
          <div class="supplier_catalog-title">
            <b>${{esc(p.name || 'KhÃ´ng tÃªn')}}</b>
            <small>${{p.local_product_id ? 'Äang bÃ¡n: ' + esc(p.local_product_id) : 'ChÆ°a báº­t trong bot'}}</small>
          </div>
          <code class="supplier_catalog-id">#${{esc(p.id)}}</code>
        </div>
        <div class="supplier_catalog-metrics">
          <div class="supplier_catalog-metric"><small>GiÃ¡ nguá»“n</small><span>${{money(sourcePrice)}}</span></div>
          <div class="supplier_catalog-metric"><small>GiÃ¡ bÃ¡n</small><strong class="supplier_catalog-sell-price">${{money(sellPrice)}}</strong><small>Ä‚n ${{markup}}%</small></div>
          <div class="supplier_catalog-metric"><small>Kho</small><span class="tag readonly">${{esc(p.stock)}}</span></div>
        </div>
        <form method="post" action="${{supplier_catalogActionUrl}}" class="supplier_catalog-form">
          <input type="hidden" name="action" value="supplier_catalog_resell">
          <input type="hidden" name="mode" value="${{mode}}">
          <input type="hidden" name="shop_product_id" value="${{esc(p.id)}}">
          <label>Markup %</label>
          <input name="markup" value="${{esc(markup)}}" title="Markup %" inputmode="decimal" oninput="updateShopbotSellPrice(this, ${{sourcePrice}})">
          <label>TÃªn bÃ¡n</label>
          <input name="custom_name" value="${{esc(p.local_name || p.name || '')}}" title="TÃªn bÃ¡n trong bot">
          <details class="supplier_catalog-desc">
            <summary>MÃ´ táº£ API / sá»­a mÃ´ táº£ bÃ¡n</summary>
            <textarea name="custom_description">${{esc(description)}}</textarea>
            <small class="muted">Äá»ƒ nguyÃªn = dÃ¹ng mÃ´ táº£ API. Sá»­a á»Ÿ Ä‘Ã¢y rá»“i báº¥m lÆ°u.</small>
          </details>
          <div class="supplier_catalog-actions">
            <button type="submit">${{btn}}</button>
            ${{dangerForm}}
          </div>
        </form>
      </article>`;
    }}).join('');
    box.innerHTML = `<div class="supplier_catalog-grid">${{cards}}</div>`;
  }} catch (err) {{
    box.innerHTML = '<div class="alert error">KhÃ´ng táº£i Ä‘Æ°á»£c SupplierCatalog API: ' + esc(err.message || err) + '</div>';
  }}
}}
function updateShopbotSellPrice(input, sourcePrice) {{
  const row = input.closest('.supplier_catalog-card');
  const markup = Number(input.value || 0);
  const sell = Math.round(Number(sourcePrice || 0) * (1 + markup / 100));
  const priceEl = row && row.querySelector('.supplier_catalog-sell-price');
  const smallEl = priceEl && priceEl.nextElementSibling;
  if (priceEl) priceEl.textContent = money(sell);
  if (smallEl) smallEl.textContent = 'Ä‚n ' + markup + '%';
}}
function filterShopbotRows() {{
  const q = document.getElementById('supplier_catalog-filter').value.toLowerCase();
  document.querySelectorAll('#supplier_catalog-list .data-row').forEach(row => {{
    row.style.display = row.dataset.search.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
loadShopbotProducts();
</script>
"""


@app.get("/admin/supplier_catalog", tags=["Admin"])
async def admin_web_supplier_catalog(request: Request):
    _admin_web_require(request)
    await _admin_web_notify_login(request)
    return HTMLResponse(_admin_web_layout("Dino Admin â€” SupplierCatalog Resell", _admin_web_supplier_catalog_body(request), request))


@app.get("/api/admin/supplier_catalog/products", tags=["Admin"])
async def api_admin_supplier_catalog_products(request: Request):
    _admin_web_require(request)
    try:
        from app.integrations.supplier_source import supplier_catalog_get_products
        result = await supplier_catalog_get_products(log_error=False)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "products": []}
    if not result.get("success"):
        return {"ok": False, "error": str(result.get("error") or "unknown_error"), "products": []}

    enabled_map = {}
    for pid, product in products.items():
        if not isinstance(product, dict) or product.get("resell_source") != "supplier_catalog":
            continue
        source_id = str(product.get("supplier_source_variant_id") or product.get("supplier_source_product_id") or "")
        enabled_map[source_id] = {
            "enabled": product.get("resell_enabled") is not False,
            "local_product_id": str(pid),
            "markup_percent": product.get("markup_percent", 30),
            "local_name": product.get("name") or "",
            "local_description": product.get("description") or "",
        }

    out = []
    for product in result.get("products") or []:
        source_id = str(product.get("id") or "")
        state = enabled_map.get(source_id, {})
        markup_percent = float(state.get("markup_percent") or 30)
        source_price = _admin_web_int(product.get("price_vnd"), 0)
        out.append({
            "id": source_id,
            "name": str(product.get("name") or ""),
            "price_vnd": source_price,
            "sell_price_vnd": int(source_price * (1 + markup_percent / 100)),
            "markup_percent": markup_percent,
            "stock": _admin_web_int(product.get("stock"), 0),
            "description": str(product.get("description") or ""),
            "enabled": bool(state.get("enabled")),
            "local_product_id": state.get("local_product_id") or "",
            "local_name": state.get("local_name") or "",
            "local_description": state.get("local_description") or "",
        })
    return {"ok": True, "products": out}


def _admin_web_categories_media_body_legacy(request):
    from html import escape as _esc
    get_cat = globals().get("get_product_category")
    products_data = globals().get("products", {})

    # Build category â†’ product list map
    cat_map: dict = {}
    for pid, prod in (products_data.items() if isinstance(products_data, dict) else []):
        cat = str(prod.get("store_category") or "").strip()
        if not cat and callable(get_cat):
            try:
                cat = str(get_cat(prod.get("name") or "") or "")
            except Exception:
                cat = ""
        cat = cat or "Sáº£n Pháº©m KhÃ¡c"
        cat_map.setdefault(cat, []).append((pid, prod))

    rows_html = ""
    for cat_name in sorted(cat_map.keys()):
        prods = cat_map[cat_name]
        img_path = _admin_web_category_image_path(cat_name)
        has_img = img_path is not None
        slug = _admin_web_category_slug(cat_name)
        count = len(prods)
        own_img_count = sum(1 for pid, _ in prods if _admin_web_product_image_path(pid) is not None)

        if has_img:
            img_url = _admin_web_category_image_url(request, cat_name)
            thumb = f'<img src="{_esc(img_url, quote=True)}" style="height:48px;width:64px;object-fit:cover;border-radius:6px;border:1px solid var(--glass-line);">'
            status_badge = '<span class="tag success" style="font-size:11px;">âœ… CÃ³ áº£nh</span>'
        else:
            thumb = '<div style="height:48px;width:64px;border-radius:6px;border:1px dashed #555;display:flex;align-items:center;justify-content:center;color:#555;font-size:18px;">ðŸ–¼</div>'
            status_badge = '<span class="tag danger" style="font-size:11px;">âŒ ChÆ°a cÃ³</span>'

        key_qs = _admin_web_key_query(request)
        sample_pid = prods[0][0] if prods else ""
        detail_url = _admin_web_page_url(request, "/admin/item", {"entity": "product", "id": sample_pid}) if sample_pid else "#"
        upload_action = f"/admin/product_image_upload{key_qs}"
        delete_form = (
            f'<form method="post" action="/admin/action{key_qs}" style="display:inline;">'
            f'<input type="hidden" name="action" value="category_image_delete">'
            f'<input type="hidden" name="category_name" value="{_esc(cat_name, quote=True)}">'
            f'<button type="submit" class="btn-xs danger" onclick="return confirm(\'XoÃ¡ áº£nh danh má»¥c {_esc(cat_name)}?\')">ðŸ—‘</button>'
            f'</form>'
        ) if has_img else ""
        row_id = f"cat-row-{slug}"
        upload_form = (
            f'<form method="post" action="{_esc(upload_action, quote=True)}" enctype="multipart/form-data" style="display:flex;gap:4px;align-items:center;margin-top:4px;">'
            f'<input type="hidden" name="product_id" value="{_esc(sample_pid, quote=True)}">'
            f'<input type="hidden" name="apply_to_category" value="1">'
            f'<input type="hidden" name="category_name_override" value="{_esc(cat_name, quote=True)}">'
            f'<input type="file" name="image" accept="image/jpeg,image/png,image/webp" required style="font-size:11px;max-width:140px;">'
            f'<button type="submit" class="btn-xs">â¬† Upload</button>'
            f'</form>'
        ) if sample_pid else ""

        rows_html += f"""
<tr id="{_esc(row_id)}">
  <td style="padding:8px 6px;">{thumb}</td>
  <td style="padding:8px 6px;"><b>{_esc(cat_name)}</b><br><span class="muted" style="font-size:11px;">slug: {_esc(slug)}</span>{upload_form}</td>
  <td style="padding:8px 6px;text-align:center;">{count}</td>
  <td style="padding:8px 6px;text-align:center;color:#aaa;font-size:12px;">{own_img_count} / {count}</td>
  <td style="padding:8px 6px;text-align:center;">{status_badge}</td>
  <td style="padding:8px 6px;text-align:center;">
    {delete_form}
    <a href="{_esc(detail_url, quote=True)}" class="btn-xs" style="margin-left:4px;">ðŸ“¦</a>
  </td>
</tr>"""

    total_cats = len(cat_map)
    cats_with_img = sum(1 for c in cat_map if _admin_web_category_image_path(c) is not None)

    body = f"""
<section class="action-card">
  <div class="card-head">
    <h3>Quáº£n lÃ½ áº£nh danh má»¥c</h3>
    <span class="tag">media</span>
  </div>
  <p class="muted" style="margin:4px 0 12px;">
    Tá»•ng: <b>{total_cats}</b> danh má»¥c â€”
    <span style="color:#4ade80;">âœ… {cats_with_img} cÃ³ áº£nh</span> &nbsp;|&nbsp;
    <span style="color:#f87171;">âŒ {total_cats - cats_with_img} chÆ°a cÃ³</span>
  </p>
  <p class="muted" style="font-size:12px;margin-bottom:10px;">
    Äá»ƒ upload áº£nh danh má»¥c: vÃ o trang chi tiáº¿t sáº£n pháº©m thuá»™c danh má»¥c Ä‘Ã³ â†’ pháº§n <b>áº¢nh sáº£n pháº©m</b> â†’ tick <i>"Ãp dá»¥ng cho toÃ n bá»™ danh má»¥c"</i>.
  </p>
  <div style="overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;font-size:13px;">
    <thead>
      <tr style="border-bottom:1px solid var(--glass-line);color:#aaa;font-size:11px;text-transform:uppercase;">
        <th style="padding:6px;text-align:left;">áº¢nh</th>
        <th style="padding:6px;text-align:left;">Danh má»¥c</th>
        <th style="padding:6px;text-align:center;">SP</th>
        <th style="padding:6px;text-align:center;">áº¢nh riÃªng</th>
        <th style="padding:6px;text-align:center;">Tráº¡ng thÃ¡i</th>
        <th style="padding:6px;text-align:center;">HÃ nh Ä‘á»™ng</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  </div>
</section>"""
    return body


def _admin_web_categories_body(request):
    products_data = products if isinstance(products, dict) else {}
    category_data = store_categories if isinstance(store_categories, dict) else {}
    cat_map = {str(name): [] for name in category_data if str(name).strip()}
    for pid, product in products_data.items():
        if isinstance(product, dict):
            name = _admin_web_product_category(product) or "Sáº£n Pháº©m KhÃ¡c"
            cat_map.setdefault(name, []).append((pid, product))

    def sort_key(name):
        config = _admin_web_category_config(name)
        return (_admin_web_int(config.get("sort_order"), 9999), str(name).casefold())

    action_url = _admin_web_action_url(request)
    upload_url = f"/admin/category_image_upload{_admin_web_key_query(request)}"
    rows = []
    for index, category_name in enumerate(sorted(cat_map, key=sort_key), 1):
        category_products = cat_map[category_name]
        config = _admin_web_category_config(category_name)
        total_stock = sum(
            max(0, stock) for _, product in category_products
            if isinstance((stock := _admin_web_stock_count(product)), int)
        )
        hidden = config.get("hidden") is True
        status = '<span class="tag danger">áº¨n</span>' if hidden else '<span class="tag success">Hiá»ƒn thá»‹</span>'
        if _admin_web_category_image_path(category_name):
            preview = (
                f'<img src="{escape(_admin_web_category_image_url(request, category_name), quote=True)}" '
                'style="width:30px;height:30px;object-fit:cover;border-radius:8px;vertical-align:middle">'
            )
            media_preview = (
                f'<img src="{escape(_admin_web_category_image_url(request, category_name), quote=True)}" '
                'alt="" class="category-media-preview">'
            )
        else:
            preview = '<span style="font-size:20px">ðŸ“¦</span>'
            media_preview = '<span class="category-media-placeholder">ðŸ“¦</span>'
        detail_url = (
            _admin_web_page_url(request, "/admin/item", {"entity": "product", "id": category_products[0][0]})
            if category_products else ""
        )
        detail_link = (
            f'<a class="btn-xs secondary category-action-link" href="{escape(detail_url, quote=True)}">'
            f'{"Má»Ÿ sáº£n pháº©m" if len(category_products) == 1 else "Má»Ÿ SP Ä‘áº§u tiÃªn"}</a>'
            if detail_url else '<span class="category-empty-label">ChÆ°a cÃ³ sáº£n pháº©m</span>'
        )
        toggle_mode, toggle_label = ("show", "Hiá»‡n") if hidden else ("hide", "áº¨n")
        editor_id = f"category-editor-{index}"
        delete_control = (
            '<span class="category-system-note">Danh má»¥c há»‡ thá»‘ng, khÃ´ng thá»ƒ xÃ³a</span>'
            if category_name == "Sáº£n Pháº©m KhÃ¡c"
            else f"""
              <form method="post" action="{escape(action_url, quote=True)}"
                    data-confirm="XÃ³a danh má»¥c nÃ y? Sáº£n pháº©m sáº½ Ä‘Æ°á»£c chuyá»ƒn sang Sáº£n Pháº©m KhÃ¡c.">
                <input type="hidden" name="action" value="category_delete">
                <input type="hidden" name="return_page" value="categories">
                <input type="hidden" name="category_name" value="{escape(category_name, quote=True)}">
                <button class="btn-xs danger" type="submit">XÃ³a danh má»¥c</button>
              </form>"""
        )
        rows.append(f"""
<tr class="data-row category-main-row" data-search="{escape(category_name.casefold(), quote=True)}">
  <td>
    <div class="category-identity">
      <span class="category-icon">{preview}</span>
      <span><b>{escape(category_name)}</b><small>{escape(str(config.get("icon_url") or "ChÆ°a Ä‘áº·t icon web"))}</small></span>
    </div>
  </td>
  <td><span class="category-order">#{escape(str(config.get("sort_order", index)))}</span></td>
  <td><b class="category-number">{total_stock}</b><small>Ä‘Æ¡n vá»‹ tá»“n</small></td>
  <td><b class="category-number">{len(category_products)}</b><small>sáº£n pháº©m</small></td>
  <td>{status}</td>
  <td>
    <div class="category-row-actions">
      <button type="button" class="btn-xs secondary category-edit-toggle"
              data-category-editor="{editor_id}" aria-expanded="false">Sá»­a</button>
      <form method="post" action="{escape(action_url, quote=True)}">
        <input type="hidden" name="action" value="category_visibility">
        <input type="hidden" name="return_page" value="categories">
        <input type="hidden" name="category_name" value="{escape(category_name, quote=True)}">
        <input type="hidden" name="mode" value="{toggle_mode}">
        <button class="btn-xs secondary" type="submit">{toggle_label}</button>
      </form>
      {detail_link}
    </div>
  </td>
</tr>
<tr class="category-editor-row" id="{editor_id}" hidden>
  <td colspan="6">
    <div class="category-editor-shell">
      <div class="category-editor-main">
        <div class="category-editor-heading">
          <div><span>Chá»‰nh sá»­a danh má»¥c</span><strong>{escape(category_name)}</strong></div>
          <button type="button" class="category-editor-close" data-category-close="{editor_id}" aria-label="ÄÃ³ng">Ã—</button>
        </div>
        <form method="post" action="{escape(action_url, quote=True)}" class="category-edit-form">
          <input type="hidden" name="action" value="category_update">
          <input type="hidden" name="return_page" value="categories">
          <input type="hidden" name="category_name" value="{escape(category_name, quote=True)}">
          <label>TÃªn danh má»¥c
            <input name="new_name" value="{escape(category_name, quote=True)}" required>
          </label>
          <label>Thá»© tá»±
            <input type="number" name="sort_order" value="{escape(str(config.get("sort_order", index)), quote=True)}">
          </label>
          <label>Premium Emoji ID
            <input name="emoji_id" value="{escape(str(config.get("emoji_id") or ""), quote=True)}" placeholder="KhÃ´ng báº¯t buá»™c">
          </label>
          <label class="category-field-icon">Icon web URL/path
            <input name="icon_url" value="{escape(str(config.get("icon_url") or ""), quote=True)}" placeholder="/static/... hoáº·c https://...">
          </label>
          <div class="category-save-bar">
            <span>Äá»•i tÃªn sáº½ cáº­p nháº­t toÃ n bá»™ sáº£n pháº©m trong danh má»¥c.</span>
            <button type="submit">LÆ°u thay Ä‘á»•i</button>
          </div>
        </form>
      </div>
      <aside class="category-media-card">
        <div class="category-media-top">{media_preview}<div><b>áº¢nh danh má»¥c</b><small>PNG, JPG hoáº·c WebP</small></div></div>
        <form method="post" action="{escape(upload_url, quote=True)}" enctype="multipart/form-data" class="category-upload-form">
          <input type="hidden" name="category_name" value="{escape(category_name, quote=True)}">
          <input type="file" name="image" accept="image/jpeg,image/png,image/webp" required>
          <button class="btn-xs" type="submit">Táº£i áº£nh má»›i</button>
        </form>
        <div class="category-danger-zone">{delete_control}</div>
      </aside>
    </div>
  </td>
</tr>""")

    category_count = len(cat_map)
    hidden_count = sum(1 for name in cat_map if _admin_web_category_config(name).get("hidden") is True)
    total_products = sum(len(items) for items in cat_map.values())

    return f"""
<section class="action-card category-manager">
  <div class="category-page-head">
    <div><span class="category-eyebrow">Quáº£n lÃ½ cá»­a hÃ ng</span><h3>Danh má»¥c sáº£n pháº©m</h3>
      <p class="muted">Sáº¯p xáº¿p menu, quáº£n lÃ½ hiá»ƒn thá»‹ vÃ  hÃ¬nh áº£nh Ä‘áº¡i diá»‡n cho tá»«ng nhÃ³m sáº£n pháº©m.</p>
    </div>
    <div class="category-summary">
      <span><b>{category_count}</b> danh má»¥c</span>
      <span><b>{total_products}</b> sáº£n pháº©m</span>
      <span><b>{hidden_count}</b> Ä‘ang áº©n</span>
    </div>
  </div>
  <details class="category-create-panel">
    <summary><span><b>ï¼‹ ThÃªm danh má»¥c má»›i</b><small>Táº¡o má»™t nhÃ³m sáº£n pháº©m má»›i trong menu cá»­a hÃ ng</small></span><i>âŒ„</i></summary>
    <form method="post" action="{escape(action_url, quote=True)}" class="category-create-form">
      <input type="hidden" name="action" value="category_create">
      <input type="hidden" name="return_page" value="categories">
      <label>TÃªn danh má»¥c<input name="category_name" placeholder="VÃ­ dá»¥: CÃ´ng cá»¥ AI" required></label>
      <label>Thá»© tá»±<input type="number" name="sort_order" placeholder="Tá»± Ä‘á»™ng"></label>
      <label>Icon web<input name="icon_url" placeholder="/static/... hoáº·c URL"></label>
      <label>Premium Emoji ID<input name="emoji_id" placeholder="KhÃ´ng báº¯t buá»™c"></label>
      <label class="check-label"><input type="checkbox" name="hidden" value="1"> Táº¡o á»Ÿ tráº¡ng thÃ¡i áº©n</label>
      <button type="submit">ThÃªm danh má»¥c</button>
    </form>
  </details>
  <div class="category-table-head"><div><b>Danh sÃ¡ch danh má»¥c</b><small>Nháº¥n â€œSá»­aâ€ Ä‘á»ƒ má»Ÿ báº£ng chá»‰nh sá»­a riÃªng</small></div>
    <span class="category-safe-note">XÃ³a danh má»¥c khÃ´ng xÃ³a sáº£n pháº©m</span>
  </div>
  <div class="table-scroll"><table class="data-table category-table">
    <thead><tr><th>Danh má»¥c</th><th>Thá»© tá»±</th><th>Tá»•ng tá»“n</th><th>Sáº£n pháº©m</th><th>Tráº¡ng thÃ¡i</th><th>Thao tÃ¡c</th></tr></thead>
    <tbody>{''.join(rows) or '<tr><td colspan="6" class="muted">ChÆ°a cÃ³ danh má»¥c.</td></tr>'}</tbody>
  </table></div>
</section>
<style>
.category-manager{{overflow:hidden;padding:0!important}}.category-page-head{{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;padding:24px}}
.category-page-head h3{{margin:5px 0 7px;font-size:24px}}.category-page-head p{{margin:0;max-width:680px}}.category-eyebrow{{color:var(--ops-green,#7cf29a);font-size:9px;font-weight:900;letter-spacing:.14em;text-transform:uppercase}}
.category-summary{{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}}.category-summary span{{padding:9px 12px;border:1px solid var(--ops-line,var(--line));border-radius:10px;background:rgba(124,242,154,.035);font-size:11px;white-space:nowrap}}.category-summary b{{color:var(--ops-text,var(--ink));font-size:14px}}
.category-create-panel{{margin:0 24px 22px;border:1px solid var(--ops-line,var(--line));border-radius:14px;background:rgba(124,242,154,.025)}}.category-create-panel>summary{{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;cursor:pointer;list-style:none}}.category-create-panel>summary::-webkit-details-marker{{display:none}}.category-create-panel>summary span{{display:grid;gap:3px}}.category-create-panel>summary small{{color:var(--ops-muted,var(--muted));font-weight:500}}.category-create-panel>summary i{{font-size:18px;transition:.2s}}.category-create-panel[open]>summary i{{transform:rotate(180deg)}}
.category-create-form{{display:grid;grid-template-columns:minmax(220px,1.3fr) 100px minmax(180px,1fr) minmax(180px,1fr);gap:12px;align-items:end;padding:16px;border-top:1px solid var(--ops-line,var(--line))}}.category-create-form input{{min-width:0}}.category-create-form .check-label{{align-self:center}}
.check-label{{display:flex!important;align-items:center;gap:8px;white-space:nowrap;margin:0!important}}.check-label input{{width:auto!important;min-height:0!important;margin:0!important}}.category-create-form button{{min-height:42px}}
.category-table-head{{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:0 24px 12px}}.category-table-head>div{{display:grid;gap:3px}}.category-table-head small{{color:var(--ops-muted,var(--muted));font-size:11px}}.category-safe-note{{color:var(--ops-muted,var(--muted));font-size:10px}}
.category-manager>.table-scroll{{margin:0;border-width:1px 0 0!important;border-radius:0!important;max-height:none}}.category-table{{min-width:880px}}.category-table th:first-child,.category-table td:first-child{{padding-left:24px}}.category-table th:last-child,.category-table td:last-child{{padding-right:24px}}
.category-identity{{display:flex;align-items:center;gap:12px;min-width:240px}}.category-icon{{width:38px;height:38px;display:grid;place-items:center;flex:0 0 auto;border:1px solid var(--ops-line,var(--line));border-radius:10px;background:rgba(255,255,255,.025);overflow:hidden}}.category-icon img{{width:100%!important;height:100%!important;border-radius:0!important}}.category-identity>span:last-child{{display:grid;gap:3px}}.category-identity small{{display:block;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.category-order{{font-weight:800;color:var(--ops-text,var(--ink))}}.category-number{{display:block;font-size:14px}}.category-table td>small{{display:block;margin-top:2px;color:var(--ops-muted,var(--muted));font-size:9px}}
.category-row-actions{{display:flex;align-items:center;gap:6px;white-space:nowrap}}.category-row-actions form{{display:inline-flex;margin:0}}.category-row-actions .btn-xs,.category-action-link{{min-height:32px;padding:6px 10px;text-decoration:none}}.category-empty-label{{color:var(--ops-muted,var(--muted));font-size:10px}}
.category-editor-row[hidden]{{display:none!important}}.category-editor-row>td{{padding:0!important;background:#0b1a12!important}}.category-editor-shell{{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(280px,.7fr);gap:0;border-bottom:1px solid var(--ops-line,var(--line));box-shadow:inset 4px 0 0 var(--ops-green,#7cf29a)}}.category-editor-main{{padding:22px 24px}}.category-editor-heading{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px}}.category-editor-heading>div{{display:grid;gap:3px}}.category-editor-heading span{{color:var(--ops-muted,var(--muted));font-size:9px;font-weight:800;letter-spacing:.1em;text-transform:uppercase}}.category-editor-heading strong{{font-size:17px}}.category-editor-close{{width:32px;min-height:32px;padding:0;border-color:var(--ops-line,var(--line));color:var(--ops-text,var(--ink));background:transparent;box-shadow:none}}
.category-edit-form{{display:grid;grid-template-columns:minmax(180px,1.2fr) 110px minmax(180px,1fr);gap:12px}}.category-field-icon{{grid-column:1/-1}}.category-save-bar{{grid-column:1/-1;display:flex;justify-content:space-between;align-items:center;gap:12px;padding-top:4px}}.category-save-bar span{{color:var(--ops-muted,var(--muted));font-size:10px}}.category-save-bar button{{min-width:150px}}
.category-media-card{{padding:22px;border-left:1px solid var(--ops-line,var(--line));background:rgba(0,0,0,.12)}}.category-media-top{{display:flex;align-items:center;gap:12px;margin-bottom:14px}}.category-media-top>div{{display:grid;gap:3px}}.category-media-top small{{color:var(--ops-muted,var(--muted));font-size:10px}}.category-media-preview,.category-media-placeholder{{width:54px;height:54px;display:grid;place-items:center;object-fit:cover;border:1px solid var(--ops-line,var(--line));border-radius:12px;background:#08130e;font-size:25px}}.category-upload-form{{display:grid;gap:9px}}.category-upload-form input[type=file]{{font-size:10px;padding:8px}}.category-danger-zone{{display:flex;align-items:center;min-height:44px;margin-top:16px;padding-top:14px;border-top:1px solid rgba(255,122,122,.14)}}.category-danger-zone form{{margin:0}}.category-system-note{{color:var(--ops-muted,var(--muted));font-size:10px}}
@media(max-width:1100px){{.category-create-form{{grid-template-columns:1fr 1fr}}.category-editor-shell{{grid-template-columns:1fr}}.category-media-card{{border-top:1px solid var(--ops-line,var(--line));border-left:0}}}}
@media(max-width:720px){{.category-page-head{{align-items:flex-start;flex-direction:column;padding:18px}}.category-summary{{justify-content:flex-start}}.category-create-panel{{margin:0 18px 18px}}.category-create-form,.category-edit-form{{grid-template-columns:1fr}}.category-field-icon,.category-save-bar{{grid-column:auto}}.category-table-head{{align-items:flex-start;flex-direction:column;padding:0 18px 12px}}.category-editor-shell{{position:sticky;left:0;width:calc(100vw - 36px)}}.category-editor-main,.category-media-card{{padding:18px}}.category-save-bar{{align-items:stretch;flex-direction:column}}.category-save-bar button{{width:100%}}}}
</style>
<script>
document.querySelectorAll('[data-category-editor]').forEach(button => {{
  button.addEventListener('click', () => {{
    const target = document.getElementById(button.dataset.categoryEditor);
    if (!target) return;
    const shouldOpen = target.hidden;
    document.querySelectorAll('.category-editor-row').forEach(row => {{ row.hidden = true; }});
    document.querySelectorAll('[data-category-editor]').forEach(toggle => {{
      toggle.setAttribute('aria-expanded', 'false');
      toggle.textContent = 'Sá»­a';
    }});
    if (shouldOpen) {{
      target.hidden = false;
      button.setAttribute('aria-expanded', 'true');
      button.textContent = 'ÄÃ³ng';
      target.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
    }}
  }});
}});
document.querySelectorAll('[data-category-close]').forEach(button => {{
  button.addEventListener('click', () => {{
    const target = document.getElementById(button.dataset.categoryClose);
    if (target) target.hidden = true;
    const toggle = document.querySelector(`[data-category-editor="${{button.dataset.categoryClose}}"]`);
    if (toggle) {{
      toggle.setAttribute('aria-expanded', 'false');
      toggle.textContent = 'Sá»­a';
    }}
  }});
}});
</script>"""


@app.get("/admin/categories", tags=["Admin"])
async def admin_web_categories(request: Request):
    _admin_web_require(request)
    await _admin_web_notify_login(request)
    body = _admin_web_categories_body(request)
    return HTMLResponse(_admin_web_layout("Dino Admin â€” Danh Má»¥c", body, request))


@app.get("/admin/login", include_in_schema=False)
async def admin_web_login_page(request: Request):
    if _admin_web_authorized(request):
        return RedirectResponse("/admin", status_code=303)
    telegram_error_code = str(request.query_params.get("telegram_error") or "")
    telegram_error_message = {
        "config": "ÄÄƒng nháº­p Telegram chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh Ä‘áº§y Ä‘á»§.",
        "denied": "Báº¡n Ä‘Ã£ há»§y hoáº·c tá»« chá»‘i Ä‘Äƒng nháº­p Telegram.",
        "state": "PhiÃªn xÃ¡c thá»±c Telegram khÃ´ng há»£p lá»‡ hoáº·c Ä‘Ã£ háº¿t háº¡n.",
        "token": "KhÃ´ng thá»ƒ xÃ¡c minh pháº£n há»“i tá»« Telegram.",
        "identity": "ID Token Telegram khÃ´ng há»£p lá»‡.",
        "forbidden": "TÃ i khoáº£n Telegram nÃ y khÃ´ng cÃ³ quyá»n quáº£n trá»‹.",
    }.get(telegram_error_code, "ÄÄƒng nháº­p Telegram khÃ´ng thÃ nh cÃ´ng." if telegram_error_code else "")
    telegram_button = ""
    if _admin_web_telegram_login_enabled():
        telegram_button = """
        <a class="telegram-login-button" href="/admin/login/telegram">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21.6 3.2 18.4 19c-.2 1.1-.9 1.4-1.8.9l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.4-5 9.1-8.2c.4-.4-.1-.6-.6-.2L6 12.8 1.2 11.3c-1-.3-1.1-1 .2-1.5L20 2.6c.9-.3 1.8.2 1.6.6Z"/></svg>
          <span>ÄÄƒng nháº­p báº±ng Telegram</span>
        </a>
        """
    return HTMLResponse(f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#07110d"><title>ÄÄƒng nháº­p â€” Dino Ops</title>
<style>{ADMIN_WEB_OPS_CSS}
.telegram-login-button{{display:flex;align-items:center;justify-content:center;gap:11px;width:100%;box-sizing:border-box;padding:14px 18px;margin:18px 0 14px;border-radius:13px;background:#229ed9;color:#fff!important;text-decoration:none;font-weight:800;box-shadow:0 10px 28px rgba(34,158,217,.24);transition:.2s ease}}
.telegram-login-button:hover{{background:#168dcc;transform:translateY(-1px)}}.telegram-login-button svg{{width:23px;height:23px;fill:currentColor}}
</style></head>
<body class="admin-login-page">
  <div class="login-ambient login-ambient-a"></div><div class="login-ambient login-ambient-b"></div>
  <main class="login-shell">
    <section class="login-story">
      <a class="login-brand" href="/docs"><span class="admin-brand-mark">D</span><span>Dino <b>Ops</b></span></a>
      <div class="login-copy">
        <span class="login-eyebrow"><i></i> ADMIN OPERATIONS</span>
        <h1>Má»i hoáº¡t Ä‘á»™ng.<br><em>Má»™t trung tÃ¢m.</em></h1>
        <p>Theo dÃµi doanh thu, Ä‘Æ¡n hÃ ng, tá»“n kho, sáº£n pháº©m manual vÃ  API partner trong thá»i gian thá»±c.</p>
        <div class="login-signals">
          <div><span>01</span><b>Commerce</b><small>ÄÆ¡n hÃ ng & doanh thu</small></div>
          <div><span>02</span><b>Inventory</b><small>Kho & sáº£n pháº©m manual</small></div>
          <div><span>03</span><b>Partners</b><small>API & váº­n hÃ nh vÃ­</small></div>
        </div>
      </div>
      <footer><i></i> Dino Store secured workspace</footer>
    </section>
    <section class="login-panel">
      <div class="login-card">
        <div class="login-card-head"><span class="login-lock">âŒ</span><div><h2>ChÃ o má»«ng trá»Ÿ láº¡i</h2><p>ÄÄƒng nháº­p Ä‘á»ƒ tiáº¿p tá»¥c vÃ o Control Center.</p></div></div>
        {f'<div class="login-error"><b>KhÃ´ng thá»ƒ Ä‘Äƒng nháº­p Telegram</b><span>{telegram_error_message}</span></div>' if telegram_error_message else ''}
        {telegram_button}
        <div class="login-security"><i></i><span>PhiÃªn Ä‘Äƒng nháº­p Ä‘Æ°á»£c báº£o vá»‡ vÃ  tá»± Ä‘á»™ng háº¿t háº¡n.</span></div>
      </div>
    </section>
  </main>
</body></html>""")


def _admin_web_create_login_response(request, redirect_path="/admin"):
    session_token = _admin_web_session_token()
    expires_at = int(session_token.split(".", 1)[0])
    db_create_admin_session(session_token, expires_at)
    response = RedirectResponse(redirect_path, status_code=303)
    response.set_cookie(
        ADMIN_WEB_SESSION_COOKIE,
        session_token,
        max_age=int(ADMIN_WEB_SESSION_HOURS) * 3600,
        httponly=True,
        secure=PUBLIC_API_SCHEME == "https" or request.url.scheme == "https",
        samesite="strict",
        path="/",
    )
    return response


def _admin_web_telegram_error_response(code: str):
    response = RedirectResponse(f"/admin/login?telegram_error={quote(str(code))}", status_code=303)
    response.delete_cookie(ADMIN_WEB_TELEGRAM_OIDC_COOKIE, path="/admin/login/telegram")
    return response


@app.get("/admin/login/telegram", include_in_schema=False)
async def admin_web_telegram_login(request: Request):
    if _admin_web_authorized(request):
        return RedirectResponse("/admin", status_code=303)
    if not _admin_web_telegram_login_enabled():
        return _admin_web_telegram_error_response("config")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    nonce = secrets.token_urlsafe(32)
    challenge = _admin_web_b64url_encode(hashlib.sha256(verifier.encode("ascii")).digest())
    redirect_uri = _admin_web_telegram_redirect_uri(request)
    params = {
        "client_id": TELEGRAM_LOGIN_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    authorization_url = ADMIN_WEB_TELEGRAM_AUTH_URL + "?" + urlencode(params)
    oidc_cookie = _admin_web_telegram_oidc_cookie(
        {
            "state": state,
            "verifier": verifier,
            "nonce": nonce,
            "redirect_uri": redirect_uri,
            "issued_at": int(time.time()),
        }
    )
    response = RedirectResponse(authorization_url, status_code=303)
    response.set_cookie(
        ADMIN_WEB_TELEGRAM_OIDC_COOKIE,
        oidc_cookie,
        max_age=ADMIN_WEB_TELEGRAM_OIDC_TTL_SECONDS,
        httponly=True,
        secure=PUBLIC_API_SCHEME == "https" or request.url.scheme == "https",
        samesite="lax",
        path="/admin/login/telegram",
    )
    return response


@app.get("/admin/login/telegram/callback", include_in_schema=False)
async def admin_web_telegram_callback(request: Request):
    if request.query_params.get("error"):
        return _admin_web_telegram_error_response("denied")
    code = str(request.query_params.get("code") or "").strip()
    state = str(request.query_params.get("state") or "").strip()
    oidc_data = _admin_web_telegram_oidc_cookie_data(
        request.cookies.get(ADMIN_WEB_TELEGRAM_OIDC_COOKIE)
    )
    if (
        not code
        or not state
        or not oidc_data
        or not hmac.compare_digest(state, str(oidc_data.get("state") or ""))
    ):
        return _admin_web_telegram_error_response("state")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_response = await client.post(
                ADMIN_WEB_TELEGRAM_TOKEN_URL,
                auth=(TELEGRAM_LOGIN_CLIENT_ID, TELEGRAM_LOGIN_CLIENT_SECRET),
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": str(oidc_data.get("redirect_uri") or ""),
                    "client_id": TELEGRAM_LOGIN_CLIENT_ID,
                    "code_verifier": str(oidc_data.get("verifier") or ""),
                },
                headers={"Accept": "application/json"},
            )
            if token_response.status_code != 200:
                logger.warning("Telegram OIDC token exchange failed with status %s", token_response.status_code)
                return _admin_web_telegram_error_response("token")
            token_data = token_response.json()
            id_token = str(token_data.get("id_token") or "")
            jwks_response = await client.get(
                ADMIN_WEB_TELEGRAM_JWKS_URL,
                headers={"Accept": "application/json"},
            )
            if jwks_response.status_code != 200:
                return _admin_web_telegram_error_response("identity")
            claims = _admin_web_verify_telegram_id_token(
                id_token,
                jwks_response.json(),
                str(oidc_data.get("nonce") or ""),
            )
    except (httpx.HTTPError, ValueError, TypeError, json.JSONDecodeError):
        logger.exception("Telegram OIDC login failed")
        return _admin_web_telegram_error_response("token")
    if not claims:
        return _admin_web_telegram_error_response("identity")
    telegram_user_id = str(claims.get("id") or claims.get("sub") or "").strip()
    if not telegram_user_id or not hmac.compare_digest(telegram_user_id, str(ADMIN_USER_ID)):
        logger.warning("Rejected Telegram web admin login for user_id=%s", telegram_user_id or "unknown")
        return _admin_web_telegram_error_response("forbidden")
    response = _admin_web_create_login_response(request)
    response.delete_cookie(ADMIN_WEB_TELEGRAM_OIDC_COOKIE, path="/admin/login/telegram")
    return response


@app.post("/admin/login", include_in_schema=False)
async def admin_web_login(request: Request):
    return RedirectResponse("/admin/login/telegram", status_code=303)


@app.post("/admin/logout", include_in_schema=False)
async def admin_web_logout(request: Request):
    _admin_web_require(request)
    _admin_web_require_same_origin(request)
    form = await _admin_web_read_urlencoded_form(request)
    _admin_web_require_csrf(request, form)
    db_revoke_admin_session(_admin_web_auth_token_from_request(request))
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie(ADMIN_WEB_SESSION_COOKIE, path="/")
    return response


@app.get("/admin", tags=["Admin"])
async def admin_web_dashboard(request: Request):
    _admin_web_require(request)
    await _admin_web_notify_login(request)
    return HTMLResponse(_admin_web_layout("Dino Admin Web", _admin_web_dashboard_body(request), request))


@app.post("/admin/action", tags=["Admin"])
async def admin_web_action(request: Request):
    _admin_web_require(request)
    _admin_web_require_same_origin(request)
    form = {}
    try:
        form = await _admin_web_read_urlencoded_form(request)
        _admin_web_require_csrf(request, form)
        ok, message = await _admin_web_dispatch_action(form, request)
    except Exception as exc:
        logger.exception("Admin web action failed")
        ok, message = False, f"Loi action: {type(exc).__name__}: {exc}"
    return_entity = _admin_web_form_text(form, "return_entity")
    return_id = _admin_web_form_text(form, "return_id")
    return_page = _admin_web_form_text(form, "return_page")
    if return_page == "categories":
        notice_class = "success" if ok else "danger"
        notice = f'<div class="notice {notice_class}">{escape(message)}</div>' if message else ""
        body = notice + _admin_web_categories_body(request)
    elif return_entity and return_id:
        body = _admin_web_detail_body(request, return_entity, return_id, message=message, is_error=not ok)
    else:
        body = _admin_web_dashboard_body(request, message=message, is_error=not ok)
    return HTMLResponse(_admin_web_layout("Dino Admin Web", body, request))


@app.get("/admin/api-partners/export.csv", include_in_schema=False)
async def admin_web_api_partners_export(request: Request):
    _admin_web_require(request)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["public_id", "partner", "owner_user_id", "balance_vnd", "status", "allowed_ips", "rate_limit_per_minute", "low_balance_threshold", "alert_enabled", "admin_note"])
    for api_key, raw in api_keys.items():
        data = raw if isinstance(raw, dict) else {"name": str(raw), "balance": 0}
        writer.writerow([
            _admin_web_api_public_id(str(api_key)),
            data.get("name") or "",
            data.get("user_id") or "",
            _admin_web_int(data.get("balance"), 0),
            "active" if data.get("enabled") is not False else "revoked",
            ";".join(_api_normalize_allowed_ips(data.get("allowed_ips") or [])),
            _api_partner_rate_limit(data),
            max(0, _admin_web_int(data.get("low_balance_threshold"), 100000)),
            "yes" if data.get("low_balance_alert_enabled") is not False else "no",
            data.get("admin_note") or "",
        ])
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="dino-api-partners.csv"', "Cache-Control": "no-store"},
    )


@app.get("/admin/item", tags=["Admin"])
async def admin_web_item(request: Request):
    _admin_web_require(request)
    await _admin_web_notify_login(request)
    entity = str(request.query_params.get("entity") or "").strip()
    item_id = str(request.query_params.get("id") or "").strip()
    body = _admin_web_detail_body(request, entity, item_id)
    return HTMLResponse(_admin_web_layout("Dino Admin Detail", body, request))


@app.get("/admin/commands", tags=["Admin"])
async def admin_web_commands(request: Request):
    _admin_web_require(request)
    await _admin_web_notify_login(request)
    return HTMLResponse(_admin_web_layout("Dino Admin Commands", _admin_web_commands_body(), request))


@app.get("/api/admin/commands", tags=["Admin"])
async def api_admin_command_catalog(
    x_api_key: str = Header(None),
    authorization: str = Header(None),
):
    actor = _api_require_actor(x_api_key=x_api_key, authorization=authorization)
    if not actor.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin API key required")
    return {
        "ok": True,
        "data": {
            "groups": ADMIN_WEB_COMMAND_GROUPS,
            "commands": _admin_web_flat_commands(),
            "total": len(_admin_web_flat_commands()),
        },
    }

