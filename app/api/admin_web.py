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
ADMIN_WEB_SESSION_COOKIE = "lamshop_admin_session"
ADMIN_WEB_LOGIN_WINDOW_SECONDS = 5 * 60
ADMIN_WEB_LOGIN_MAX_ATTEMPTS = 5
ADMIN_WEB_TELEGRAM_OIDC_COOKIE = "lamshop_admin_telegram_oidc"
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

# Single stylesheet for every admin surface (dashboard, detail pages, login).
# Replaces admin_redesign.css + vip_admin.css + admin_ops_2026.css, which were
# stacked in that order and overrode each other with !important.
ADMIN_WEB_UI_CSS = (Path(__file__).parent / "static" / "admin_ui.css").read_text(encoding="utf-8")

ADMIN_WEB_FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500'
    '&amp;family=Manrope:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet">'
)

ADMIN_WEB_COMMAND_GROUPS = [
    {
        "group": "Tổng quan hệ thống",
        "commands": [
            ("admin", "/admin", "Mở bảng điều khiển admin trên Telegram.", "readonly"),
            ("helpadmin", "/helpadmin", "Alias của /admin.", "readonly"),
            ("uptime", "/uptime", "Xem uptime, thông tin hệ thống.", "readonly"),
            ("status", "/status", "Alias của /uptime.", "readonly"),
            ("backup", "/backup", "Tạo và gửi backup dữ liệu.", "danger"),
            ("nhapdata", "/nhapdata", "Restore dữ liệu từ file backup zip.", "danger"),
            ("testing", "/testing", "Lệnh test nội bộ.", "danger"),
        ],
    },
    {
        "group": "Sản phẩm và tồn kho",
        "commands": [
            ("products", "/products", "Danh sách sản phẩm store.", "readonly"),
            ("newproduct", "/newproduct", "Conversation tạo sản phẩm mới.", "conversation"),
            ("editproduct", "/editproduct", "Conversation sửa sản phẩm.", "conversation"),
            ("delproduct", "/delproduct <product_id>", "Xóa sản phẩm.", "danger"),
            ("addstock", "/addstock", "Conversation thêm stock local.", "conversation"),
            ("viewstock", "/viewstock", "Xem stock local.", "readonly"),
            ("delstock", "/delstock", "Conversation xóa stock local.", "conversation"),
            ("setlimit", "/setlimit <product_id> <so_luong>", "Đặt giới hạn pending/manual.", "write"),
        ],
    },
    {
        "group": "Đơn hàng và thanh toán",
        "commands": [
            ("duyet", "/duyet <ma_don>", "Duyệt đơn thủ công/manual.", "write"),
            ("pending", "/pending", "Xem đơn manual đang chờ.", "readonly"),
            ("clearpending", "/clearpending", "Xóa pending manual.", "danger"),
            ("refund", "/refund <ma_don>", "Hoàn tiền đơn hàng user/API partner.", "danger"),
            ("find", "/find <ma_don|user_id>", "Tìm đơn hàng.", "readonly"),
            ("doanhthu", "/doanhthu", "Thống kê doanh thu.", "readonly"),
            ("setemail", "/setemail <ma_don> <email>", "Gắn email nhận hàng cho đơn.", "write"),
            ("transactions", "/transactions", "Xem lịch sử giao dịch ví.", "readonly"),
            ("lichsugiaodich", "/lichsugiaodich", "Alias của /transactions.", "readonly"),
        ],
    },
    {
        "group": "User và ví",
        "commands": [
            ("users", "/users", "Danh sách user.", "readonly"),
            ("info", "/info <user_id>", "Xem thông tin user.", "readonly"),
            ("ban", "/ban <user_id>", "Cấm user.", "danger"),
            ("unban", "/unban <user_id>", "Gỡ cấm user.", "write"),
            ("bc", "/bc <noi_dung>", "Broadcast tin nhắn.", "danger"),
            ("addmoney", "/addmoney <user_id> <so_tien>", "Cộng tiền vào ví user/API.", "danger"),
            ("submoney", "/submoney <user_id> <so_tien>", "Trừ tiền ví user/API.", "danger"),
            ("pending_withdrawals", "/pending_withdrawals", "Xem yêu cầu rút tiền.", "readonly"),
        ],
    },
    {
        "group": "Coupon, khuyến mãi, game",
        "commands": [
            ("sale", "/sale <noi_dung>", "Gửi thông báo sale.", "danger"),
            ("addcoupon", "/addcoupon ...", "Thêm coupon.", "write"),
            ("delcoupon", "/delcoupon <code>", "Xóa coupon.", "write"),
            ("listcoupons", "/listcoupons", "Danh sách coupon.", "readonly"),
            ("rewardtop", "/rewardtop", "Thưởng top buyer/referral.", "danger"),
            ("promobudget", "/promobudget", "Xem ngân sách khuyến mãi.", "readonly"),
            ("ngansachkm", "/ngansachkm", "Alias của /promobudget.", "readonly"),
            ("flashsale", "/flashsale ...", "Quản lý flash sale.", "write"),
            ("combo", "/combo ...", "Quản lý combo deal.", "write"),
            ("create_ga", "/create_ga", "Conversation tạo giveaway.", "conversation"),
            ("list_ga", "/list_ga", "Danh sách giveaway.", "readonly"),
            ("listga", "/listga", "Alias của /list_ga.", "readonly"),
            ("endga", "/endga <ga_id>", "Kết thúc giveaway.", "write"),
            ("end_ga", "/end_ga <ga_id>", "Alias của /endga.", "write"),
        ],
    },
    {
        "group": "API partner",
        "commands": [
            ("api", "/api", "Danh sách API key partner.", "readonly"),
            ("addapi", "/addapi <ten> <so_du>", "Tạo API key partner.", "danger"),
            ("delapi", "/delapi <key>", "Xóa/vô hiệu API key.", "danger"),
            ("napi", "/napi ...", "Nạp ví API partner.", "write"),
            ("helpapi", "/helpapi", "Hướng dẫn API.", "readonly"),
            ("dkyapi", "/dkyapi", "User đăng ký API partner.", "user"),
            ("dkapi", "/dkapi", "Alias đăng ký API.", "user"),
            ("dangkyapi", "/dangkyapi", "Alias đăng ký API.", "user"),
            ("regapi", "/regapi", "Alias đăng ký API.", "user"),
            ("napapi", "/napapi", "User nạp ví API.", "user"),
            ("topupapi", "/topupapi", "Alias nạp ví API.", "user"),
        ],
    },
    {
        "group": "Hỗ trợ, thông báo, vận hành",
        "commands": [
            ("notify", "/notify <product_id> <out|back>", "Thông báo hết/có hàng.", "write"),
            ("resetnotify", "/resetnotify", "Reset cờ thông báo stock.", "write"),
            ("analytics", "/analytics", "Thống kê nâng cao.", "readonly"),
            ("chats", "/chats", "Danh sách live chat.", "readonly"),
            ("chat", "/chat <user_id>", "Mở chat admin với user.", "conversation"),
            ("closechat", "/closechat", "Đóng chat admin.", "write"),
            ("baotri", "/baotri", "Bật/tắt maintenance mode.", "danger"),
            ("aimode", "/aimode", "Bật/tắt AI auto reply.", "write"),
        ],
    },
]


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


def _admin_web_row_link(request, entity: str, item_id: str, label: str = "Mở") -> str:
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
    return "".join(rows) or "<tr><td colspan='4' class='muted'>Chưa có sản phẩm.</td></tr>"


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
    return "".join(rows) or "<tr><td colspan='4' class='muted'>Chưa có user.</td></tr>"


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
    return "".join(rows) or "<tr><td colspan='4' class='muted'>Chưa có API key.</td></tr>"


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
    return "".join(rows) or "<tr><td colspan='4' class='muted'>Chưa có đơn hàng.</td></tr>"


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
    return "".join(rows) or "<tr><td colspan='5' class='muted'>Chưa có audit log.</td></tr>"


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
        sync_state = "active"
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
    return "".join(rows) or "<tr><td colspan='9' class='muted'>Chưa có sản phẩm.</td></tr>"


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
    return "".join(rows) or "<tr><td colspan='7' class='muted'>Chưa có user.</td></tr>"


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
    return "".join(rows) or "<tr><td colspan='8' class='muted'>Chưa có đơn hàng.</td></tr>"


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
            f'<td class="{balance_class}"><b>{_admin_web_money(balance)}</b><small class="{"low-balance" if is_low else ""}">Ngưỡng {_admin_web_money(threshold)}</small></td>'
            f"<td><span class='api-status-dot {'is-on' if enabled else 'is-off'}'></span>{'Đang hoạt động' if enabled else 'Đã thu hồi'}</td>"
            f"<td><b>{quota}/phút</b><small>{'Telegram ON' if normalized.get('low_balance_alert_enabled') is not False else 'Alert OFF'}</small></td>"
            f"<td>{escape(_admin_web_short(note, 80))}</td>"
            f'<td><form method="post" action="{action_url}" class="api-quick-wallet"><input type="hidden" name="action" value="api_partner"><input type="hidden" name="mode" value="topup"><input type="hidden" name="target" value="{escape(api_public_id, quote=True)}"><input name="amount" type="number" min="1" placeholder="Số tiền" aria-label="Số tiền cộng nhanh"><button type="submit" title="Cộng số dư">+</button></form>{_admin_web_row_link(request, "api", api_public_id)}</td>'
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='7' class='muted'>Chưa có API partner.</td></tr>"


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
    return "".join(rows) or "<tr><td colspan='5' class='muted'>Chưa có coupon.</td></tr>"


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
    return "".join(rows) or "<tr><td colspan='5' class='muted'>Không có đơn manual pending.</td></tr>"


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
        last_check_text = "chưa chạy"

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
        bank_label = "đang chờ pending"
    else:
        bank_status = "warn"
        bank_label = "stale"

    success_rate = f"{int(total_success * 100 / total_checks)}%" if total_checks > 0 else "—"
    bank_note = (
        f"Account {bank_account} · pending: {pending_bank} · last check: {last_check_text} · "
        f"tx: {last_tx} · success: {total_success}/{total_checks} ({success_rate}) · fails: {fail_count}"
    )
    if last_status == "error" and last_error:
        bank_note += f" · err: {last_error[:120]}"

    bot_username = str(globals().get("BOT_USERNAME") or "").strip() or "N/A"
    admin_username = str(globals().get("ADMIN_USERNAME") or "").strip() or "N/A"
    admin_user_id = str(globals().get("ADMIN_USER_ID") or "").strip() or "N/A"
    uptime_seconds = max(0, int(time.time() - float(getattr(app_state, "bot_start_time", time.time()) or time.time())))
    uptime_text = f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m"
    
    import app.core.config_env as config_env
    mbbank_enabled = getattr(config_env, "ENABLE_PAYMENT_MBBANK", True)
    binance_enabled = getattr(config_env, "ENABLE_PAYMENT_BINANCE_SPOT", True)
    
    mbbank_btn = f"<form method='post' action='{_admin_web_action_url(request)}' style='display:inline'><input type='hidden' name='action' value='system_toggle'><input type='hidden' name='mode' value='{'mbbank_off' if mbbank_enabled else 'mbbank_on'}'><button class='button small {'danger' if mbbank_enabled else 'success'}'>{'Tắt' if mbbank_enabled else 'Bật'}</button></form>"
    binance_btn = f"<form method='post' action='{_admin_web_action_url(request)}' style='display:inline'><input type='hidden' name='action' value='system_toggle'><input type='hidden' name='mode' value='{'binance_off' if binance_enabled else 'binance_on'}'><button class='button small {'danger' if binance_enabled else 'success'}'>{'Tắt' if binance_enabled else 'Bật'}</button></form>"

    rows = [
        (bank_status, f"Cron MBBank ({bank_label})", f"{escape(bank_note)} <br><br><b>Cổng MBBank:</b> <span class='tag {'success' if mbbank_enabled else 'danger'}'>{'BẬT' if mbbank_enabled else 'TẮT'}</span> {mbbank_btn}"),
        ("live", "Bot user", f"@{escape(bot_username)} · users: {len(user_data_db)} · uptime: {escape(uptime_text)}"),
        ("live", "Bot admin", f"@{escape(admin_username)} · admin_id: {escape(admin_user_id)}"),
        ("live" if not MAINTENANCE_MODE else "danger", "Maintenance", f"maintenance {_admin_web_bool_text(MAINTENANCE_MODE)} · ai {_admin_web_bool_text(AI_AUTO_REPLY)}"),
        ("live", "Runtime queues", f"pending pay: {len(pending_orders)} · manual pending: {len(pending_manual_orders)} · support open: {_admin_web_active_count(live_chats)}"),
        ("live", "Binance Spot", f"Cổng thanh toán USDT tự động qua Binance API <br><br><b>Trạng thái:</b> <span class='tag {'success' if binance_enabled else 'danger'}'>{'BẬT' if binance_enabled else 'TẮT'}</span> {binance_btn}"),
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
        return "<div class='ecg-monitor'><div class='ecg-header'><span class='ecg-dot'></span> LOG MONITOR</div><div class='ecg-body'><p class='ecg-empty'>Chưa tìm thấy file log trong thư mục bot.</p></div></div>"

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
    return "".join(rows) or "<tr><td colspan='6' class='muted'>Chưa có ticket hỗ trợ.</td></tr>"


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
    return "".join(rows) or "<tr><td colspan='6' class='muted'>Chưa có audit log.</td></tr>"


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
        f"<tr><td>{escape(name)}</td><td><span class='tag {'ok' if configured else 'warn'}'>{'Đã cấu hình' if configured else 'Chưa cấu hình'}</span></td></tr>"
        for name, configured in rows
    )
    return f"""
    <div style="padding:16px;">
      <h3>Cấu hình Thanh toán</h3>
      <p class="muted">Read-only. Cập nhật secret trong deployment environment rồi restart bot.</p>
      <table><thead><tr><th>Dịch vụ</th><th>Trạng thái</th></tr></thead><tbody>{status_rows}</tbody></table>
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
    return "".join(rows) or _admin_web_overview_empty("Không có đơn manual pending.")


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
    return "".join(rows) or _admin_web_overview_empty("Chưa có đơn hàng gần đây.")


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
    return "".join(rows) or _admin_web_overview_empty("Chưa có audit log.")


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
        color = "var(--accent)" if is_today else "var(--chart-bar)"
        tip = f"{d.strftime('%d/%m')}: {v:,}đ"
        bars_svg.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" fill="{color}" rx="2" opacity="0.85">'
            f'<title>{tip}</title></rect>'
        )
        # x-axis label every 5 days or today
        if i % 5 == 0 or is_today:
            bars_svg.append(
                f'<text x="{x + bar_w//2}" y="{H - PAD_B + 14}" text-anchor="middle" '
                f'font-size="9" fill="{"var(--accent)" if is_today else "var(--muted)"}">{d.strftime("%d/%m")}</text>'
            )

    # y-axis gridlines
    grid_svg = []
    for frac in (0.25, 0.5, 0.75, 1.0):
        gy = H - PAD_B - int(frac * (H - PAD_B - 20))
        lbl = fmt_vnd(int(max_val * frac))
        grid_svg.append(
            f'<line x1="{PAD_L}" y1="{gy}" x2="{W - 10}" y2="{gy}" stroke="var(--line)" stroke-width="1"/>'
            f'<text x="{PAD_L - 6}" y="{gy + 4}" text-anchor="end" font-size="9" fill="var(--muted)">{lbl}</text>'
        )

    total_period = sum(values)
    week_vals = values[-7:]
    total_week = sum(week_vals)

    svg = (
        f'<svg viewBox="0 0 {W} {H}" class="revenue-chart" xmlns="http://www.w3.org/2000/svg">'
        + "".join(grid_svg)
        + "".join(bars_svg)
        + f'<line x1="{PAD_L}" y1="{H - PAD_B}" x2="{W - 10}" y2="{H - PAD_B}" stroke="var(--line-2)" stroke-width="1"/>'
        + "</svg>"
    )

    return f"""
<section class="mini-panel revenue-panel">
  <div class="card-head">
    <h3>Doanh thu {days} ngày gần nhất</h3>
    <span class="chart-legend">
      <span>Tuần <b class="money-positive">{total_week:,}đ</b></span>
      <span>{days} ngày <b>{total_period:,}đ</b></span>
    </span>
  </div>
  <div class="chart-body">{svg}</div>
</section>"""


def _admin_web_overview_board(request) -> str:
    return f"""
<div class="overview-board">
  {_admin_web_revenue_chart(30)}
  <section class="mini-panel queue-panel">
    <div class="card-head"><h3>Hàng đợi cần xử lý</h3><a class="panel-link" href="#ops">{len(pending_manual_orders)} manual</a></div>
    <div class="overview-list">{_admin_web_overview_pending_items(request)}</div>
  </section>
  <section class="mini-panel queue-panel">
    <div class="card-head"><h3>Đơn mới gần đây</h3><a class="panel-link" href="#orders">{len(order_history)} total</a></div>
    <div class="overview-list">{_admin_web_overview_order_items(request)}</div>
  </section>
  <section class="mini-panel queue-panel">
    <div class="card-head"><h3>Audit gần đây</h3><a class="panel-link" href="#audit">web</a></div>
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
    <a class="button" href="{escape(back_url, quote=True)}">Về dashboard</a>
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
    if any(token in label_folded for token in ("tiền", "giá", "số dư", "spent", "amount")):
        icon_class += " metric-detail-money"
    elif any(token in label_folded for token in ("status", "trạng thái", "records", "orders")):
        icon_class += " metric-detail-order"
    elif any(token in label_folded for token in ("user", "owner")):
        icon_class += " metric-detail-user"
    elif any(token in label_folded for token in ("stock", "loại", "sync", "partner")):
        icon_class += " metric-detail-product"
    elif any(token in label_folded for token in ("coupon", "used")):
        icon_class += " metric-detail-promo"
    elif any(token in label_folded for token in ("bảo hành", "bh", "hết hạn")):
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
    body = "".join(rows) or "<tr><td colspan='5' class='muted'>Chưa có đơn hàng.</td></tr>"
    return f'<div class="table-scroll"><table class="data-table"><thead><tr><th>Mã</th><th>Sản phẩm</th><th>Tiền</th><th>Status</th><th></th></tr></thead><tbody>{body}</tbody></table></div>'


def _admin_web_order_warranty_summary_cards(order: dict) -> str:
    if not isinstance(order, dict) or not order:
        return (
            _admin_web_summary_card("Bảo hành", "N/A")
            + _admin_web_summary_card("Hết hạn BH", "N/A", "write")
            + _admin_web_summary_card("Trạng thái BH", "Chưa rõ", "write")
        )

    status_text = _admin_web_plain_display(order.get("status") or "")
    status_folded = status_text.casefold()
    refunded_at = order.get("refunded_at")
    try:
        refunded_at_value = float(refunded_at or 0)
    except (TypeError, ValueError):
        refunded_at_value = 0
    if refunded_at_value > 0 or any(token in status_folded for token in ("hoàn tiền", "hoan tien", "refund", "refunded", "hủy", "huy", "cancel")):
        refund_time = _admin_web_format_timestamp(refunded_at_value) if refunded_at_value > 0 else "Không áp dụng"
        return (
            _admin_web_summary_card("Bảo hành", "Không áp dụng", "danger")
            + _admin_web_summary_card("Kết thúc BH", refund_time, "danger")
            + _admin_web_summary_card("Trạng thái BH", "Đã hoàn tiền", "danger")
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
        expiry_text = "Không giới hạn"
        status_text = "Còn bảo hành"
        expiry_kind = "readonly"
    elif reason == "no_warranty":
        expiry_text = "Không bảo hành"
        status_text = "Không bảo hành"
        expiry_kind = "danger"
    elif expires_at:
        expiry_text = _admin_web_format_timestamp(expires_at)
        status_text = "Hết hạn" if expired else "Còn bảo hành"
        expiry_kind = "danger" if expired else "readonly"
    elif known:
        expiry_text = "Không xác định"
        status_text = "Theo chính sách"
    else:
        expiry_text = "Không xác định"
        status_text = "Chưa rõ"

    return (
        _admin_web_summary_card("Bảo hành", warranty_text)
        + _admin_web_summary_card("Hết hạn BH", expiry_text, expiry_kind)
        + _admin_web_summary_card("Trạng thái BH", status_text, expiry_kind)
    )


def _admin_web_product_detail_body(request, product_id: str, message: str | None = None, is_error: bool = False):
    product = products.get(product_id)
    if not isinstance(product, dict):
        return _admin_web_detail_shell(
            request,
            "product",
            product_id,
            "Không tìm thấy sản phẩm",
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
            _admin_web_summary_card("Loại", product_type),
            _admin_web_summary_card("Giá", _admin_web_money(product.get("price"))),
            _admin_web_summary_card("Stock", stock_count),
            _admin_web_summary_card("Bảo hành", product.get("warranty") or "Không"),
            _admin_web_summary_card("Pending manual", pending_count),
            _admin_web_summary_card("Orders", sold_count),
        ]
    )
    stock_disabled = "disabled" if product.get("requires_gmail") else ""
    category_name = _admin_web_product_category(product)
    image_path = _admin_web_product_image_path(product_id)
    category_image_path = _admin_web_category_image_path(category_name) if category_name else None
    if image_path is not None:
        image_preview_html = (
            f'<img src="{escape(_admin_web_product_image_url(request, product_id), quote=True)}" '
            f'alt="Product image" style="max-width:100%;max-height:280px;border-radius:12px;'
            f'border:1px solid var(--glass-line);background:#0b1220;display:block;margin-bottom:10px;">'
            f'<form method="post" action="{action_url}" class="form-grid" '
            f'data-confirm="Xóa ảnh riêng của sản phẩm này?">'
            f'<input type="hidden" name="action" value="product_image_delete">'
            f'{_admin_web_hidden_return("product", product_id)}'
            f'<input type="hidden" name="product_id" value="{escape(product_id, quote=True)}">'
            f'<button class="wide danger" type="submit">Xóa ảnh riêng</button>'
            f'</form>'
        )
    else:
        image_preview_html = '<p class="muted" style="margin:0 0 10px;">Chưa có ảnh riêng cho sản phẩm này.</p>'

    if category_name and category_image_path is not None:
        category_image_preview = (
            f'<p class="muted" style="margin:14px 0 6px;">Ảnh danh mục <b>{escape(category_name)}</b> '
            f'(áp dụng cho mọi sản phẩm chưa có ảnh riêng):</p>'
            f'<img src="{escape(_admin_web_category_image_url(request, category_name), quote=True)}" '
            f'alt="Category image" style="max-width:100%;max-height:200px;border-radius:12px;'
            f'border:1px solid var(--glass-line);background:#0b1220;display:block;margin-bottom:10px;">'
            f'<form method="post" action="{action_url}" class="form-grid" '
            f'data-confirm="Xóa ảnh chung của danh mục {escape(category_name, quote=True)}?">'
            f'<input type="hidden" name="action" value="category_image_delete">'
            f'{_admin_web_hidden_return("product", product_id)}'
            f'<input type="hidden" name="category_name" value="{escape(category_name, quote=True)}">'
            f'<button class="wide danger" type="submit">Xóa ảnh danh mục</button>'
            f'</form>'
        )
    elif category_name:
        category_image_preview = (
            f'<p class="muted" style="margin:14px 0 6px;">Danh mục <b>{escape(category_name)}</b> '
            f'chưa có ảnh chung. Tick <i>"Áp dụng cho cả danh mục"</i> bên dưới để upload.</p>'
        )
    else:
        category_image_preview = ""

    apply_category_checkbox = (
        f'<label class="wide" style="display:flex;align-items:center;gap:8px;font-weight:600;">'
        f'<input type="checkbox" name="apply_to_category" value="1" style="width:auto;margin:0;"> '
        f'Áp dụng cho cả danh mục '
        f'<span class="muted" style="font-weight:400;">(mọi sản phẩm cùng danh mục chưa có ảnh riêng sẽ dùng ảnh này)</span>'
        f'</label>'
        f'<label class="wide">Tên danh mục áp dụng '
        f'<span class="muted" style="font-weight:400;">(để trống = dùng danh mục hiện tại của sản phẩm)</span>'
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
            tag_text = "có ảnh riêng" if has_own_img else "sẽ dùng ảnh chung"
            is_self = pid == product_id
            row_style = "background:rgba(99,179,237,0.08);" if is_self else ""
            # Default tick: every product in this category (admin can untick mismatches)
            checkbox_html = (
                f'<input type="checkbox" name="selected_products" value="{escape(pid, quote=True)}" '
                f'class="apply-row-check" checked style="width:auto;margin:0;">'
            )
            self_badge = ' <span class="tag">đang xem</span>' if is_self else ''
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
            rows.append('<tr><td colspan="5" class="muted">Chưa có sản phẩm nào trong danh mục này.</td></tr>')

        more_note = ""
        if len(affected) > 200:
            more_note = f'<p class="muted" style="margin:6px 0 0;">… và {len(affected) - 200} sản phẩm khác (chỉ hiện 200 đầu).</p>'

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
    🔍 Xem trước {len(affected)} sản phẩm trong danh mục <b>{escape(category_name)}</b>
    <span class="muted" style="font-weight:400;">(tick từng sản phẩm muốn áp dụng ảnh; bỏ tick nếu sản phẩm bị xếp nhầm)</span>
  </summary>
  <div class="apply-preview-box">
  <div style="overflow:auto;margin-top:10px;">
    <table class="data-table" style="width:100%;font-size:13px;">
      <thead><tr>
        <th style="width:36px;text-align:center;"><input type="checkbox" class="apply-master-check" checked title="Tick/Bỏ tick tất cả" style="width:auto;margin:0;"></th>
        <th>Product ID</th><th>Tên</th><th>Trạng thái ảnh</th><th></th>
      </tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
  {more_note}
  <p class="muted" style="margin:8px 0 0;">
    <b>Cách áp dụng:</b><br>
    • Tick các sản phẩm muốn dùng <b>chung 1 ảnh</b> (mặc định tick hết) → ảnh sẽ được copy cho mỗi sản phẩm đã tick.<br>
    • Hoặc tick checkbox <i>"Áp dụng cho cả danh mục"</i> bên dưới → lưu 1 ảnh dùng chung cho cả danh mục (tiết kiệm dung lượng, mọi sản phẩm chưa có ảnh riêng tự động dùng).<br>
    • Sản phẩm có "ảnh riêng" sẽ luôn ưu tiên ảnh riêng — bạn cần xóa ảnh riêng trước nếu muốn đè.
  </p>
  </div>{select_helper_js}
</details>
"""

    image_upload_url = f"/admin/product_image_upload{_admin_web_key_query(request)}"
    image_section = f"""
<section class="action-card">
  <div class="card-head"><h3>Ảnh sản phẩm</h3><span class="tag write">media</span></div>
  {image_preview_html}
  {category_image_preview}
  <form method="post" action="{escape(image_upload_url, quote=True)}" enctype="multipart/form-data" class="form-grid">
    <input type="hidden" name="product_id" value="{escape(product_id, quote=True)}">
    <label class="wide">Chọn ảnh (jpg/png/webp, ≤ 8MB)
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
        info.textContent = f.name + ' — ' + (f.size/1024).toFixed(1) + ' KB';
        wrap.style.display = 'block';
      }});
    }})();
    </script>
    {preview_html}
    {apply_category_checkbox}
    <button class="wide" type="submit">Tải lên / Thay ảnh</button>
  </form>
</section>
"""
    main = f"""
{image_section}
<section class="action-card">
  <div class="card-head"><h3>Sửa sản phẩm</h3><span class="tag write">editable</span></div>
  <form method="post" action="{action_url}" class="form-grid">
    <input type="hidden" name="action" value="product_update">
    {_admin_web_hidden_return("product", product_id)}
    <label>Product ID<input name="product_id" value="{escape(product_id, quote=True)}" readonly></label>
    <label>Giá bán<input name="price" value="{escape(str(product.get('price') or ''), quote=True)}"></label>
    <label>Giá vốn<input name="cost_price" value="{escape(str(product.get('cost_price') if product.get('cost_price') is not None else ''), quote=True)}" placeholder="Local/manual"></label>
    <label class="wide">Tên<input name="name" value="{escape(str(product.get('name') or ''), quote=True)}"></label>
    <label class="wide">Danh mục (store_category) <span class="muted" style="font-weight:400;">(để trống = giữ nguyên)</span><input name="store_category" placeholder="VD: AI Tools (GPT, Copilot...)" value="{escape(str(product.get('store_category') or ''), quote=True)}"></label>
    <label>Thời hạn<input name="duration" value="{escape(str(product.get('duration') or ''), quote=True)}"></label>
    <label>Bảo hành<input name="warranty" value="{escape(str(product.get('warranty') or ''), quote=True)}" placeholder="VD: 7 ngày, 30 ngày, Không"></label>
    <label>Giới hạn manual<input name="max_pending_orders" value="{escape(str(product.get('max_pending_orders') or ''), quote=True)}"></label>
    <label class="wide">Mô tả<textarea name="description">{escape(str(product.get('description') or ''))}</textarea></label>
    <label class="wide">Thêm stock local<textarea name="stock_items" {stock_disabled} placeholder="Mỗi dòng 1 item"></textarea></label>
    <button class="wide" type="submit">Lưu thay đổi</button>
  </form>
</section>
<section class="action-card">
  <div class="card-head"><h3>Xóa sản phẩm</h3><span class="tag danger">danger</span></div>
  <form method="post" action="{action_url}" class="form-grid" data-confirm="Xóa vĩnh viễn sản phẩm này khỏi catalog? Đơn hàng cũ sẽ vẫn giữ trong lịch sử.">
    <input type="hidden" name="action" value="product_delete">
    <input type="hidden" name="product_id" value="{escape(product_id, quote=True)}">
    <button class="wide danger" type="submit">Xóa sản phẩm</button>
  </form>
</section>
<section class="action-card">
  <div class="card-head"><h3>Stock local</h3><span class="tag danger">careful</span></div>
  <form method="post" action="{action_url}" class="form-grid" data-confirm="Xóa toàn bộ stock local của sản phẩm này?">
    <input type="hidden" name="action" value="product_stock">
    {_admin_web_hidden_return("product", product_id)}
    <input type="hidden" name="product_id" value="{escape(product_id, quote=True)}">
    <input type="hidden" name="mode" value="clear_stock">
    <button class="wide danger" type="submit" {stock_disabled}>Xóa toàn bộ stock local</button>
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
            _admin_web_summary_card("Số dư", _admin_web_money(profile.get("balance"))),
            _admin_web_summary_card("Orders", orders_count),
            _admin_web_summary_card("Status", "ban" if banned else "active", "danger" if banned else "readonly"),
            _admin_web_summary_card("Spent", _admin_web_money(profile.get("total_spent") or profile.get("spent") or 0)),
        ]
    )
    action_url = _admin_web_action_url(request)
    main = f"""
<section class="action-card">
  <div class="card-head"><h3>Hồ sơ user</h3><span class="tag write">profile</span></div>
  <form method="post" action="{action_url}" class="form-grid">
    <input type="hidden" name="action" value="user_profile">
    {_admin_web_hidden_return("user", user_id)}
    <label>User ID<input name="user_id" value="{escape(str(user_id), quote=True)}" readonly></label>
    <label>Username<input name="username" value="{escape(str(profile.get('username') or ''), quote=True)}"></label>
    <label class="wide">Tên<input name="full_name" value="{escape(str(profile.get('full_name') or profile.get('first_name') or ''), quote=True)}"></label>
    <label>Email<input name="email" value="{escape(str(profile.get('email') or ''), quote=True)}"></label>
    <label>Ghi chú<input name="admin_note" value="{escape(str(profile.get('admin_note') or ''), quote=True)}"></label>
    <button class="wide" type="submit">Lưu hồ sơ</button>
  </form>
</section>
<section class="action-card">
  <div class="card-head"><h3>Ví & ban</h3><span class="tag danger">money</span></div>
  <form method="post" action="{action_url}" class="form-grid">
    <input type="hidden" name="action" value="user_balance">
    {_admin_web_hidden_return("user", user_id)}
    <label>User ID<input name="user_id" value="{escape(str(user_id), quote=True)}" readonly></label>
    <label>Số tiền<input name="amount" placeholder="100000"></label>
    <label>Kiểu<select name="mode"><option value="add">Cộng</option><option value="sub">Trừ</option><option value="set">Set</option></select></label>
    <label>Lý do<input name="reason" value="Admin web detail"></label>
    <button class="wide" type="submit">Cập nhật ví</button>
  </form>
  <form method="post" action="{action_url}" class="form-grid" data-confirm="Cập nhật ban/unban user này?">
    <input type="hidden" name="action" value="user_ban">
    {_admin_web_hidden_return("user", user_id)}
    <input type="hidden" name="user_id" value="{escape(str(user_id), quote=True)}">
    <label class="wide">Trạng thái<select name="mode"><option value="ban">Ban</option><option value="unban">Unban</option></select></label>
    <button class="wide danger" type="submit">Ban / unban</button>
  </form>
</section>
<section class="module-section">
  <div class="section-head"><div><h2>Đơn hàng của user</h2></div></div>
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
            _admin_web_summary_card("Tiền", _admin_web_money(primary.get("amount"))),
            _admin_web_summary_card("Status", primary.get("status") or "N/A"),
            _admin_web_summary_card("User", primary.get("user_id") or ""),
            _admin_web_order_warranty_summary_cards(primary),
        ]
    )
    raw_payload = {"matches": [{"table": table, "record": record} for table, record in records]}
    main = f"""
<section class="action-card">
  <div class="card-head"><h3>Công cụ đơn hàng</h3><span class="tag write">order</span></div>
  <form method="post" action="{action_url}" class="form-grid">
    <input type="hidden" name="action" value="order_tools">
    {_admin_web_hidden_return("order", order_code)}
    <label>Mã đơn<input name="order_code" value="{escape(str(order_code), quote=True)}" readonly></label>
    <label>Thao tác<select name="mode"><option value="set_email">Gắn email</option><option value="admin_note">Ghi chú admin</option></select></label>
    <label class="wide">Giá trị<input name="value" value="{escape(str(primary.get('email') or primary.get('customer_email') or primary.get('admin_note') or ''), quote=True)}"></label>
    <button class="wide" type="submit">Cập nhật đơn</button>
  </form>
</section>
"""
    return _admin_web_detail_shell(request, "order", str(order_code), f"Order {order_code}", summary, main, raw_payload, message=message, is_error=is_error)


def _admin_web_api_traffic_chart(analytics: dict) -> str:
    daily = list((analytics or {}).get("daily") or [])
    if not daily:
        return '<div class="api-empty-state">Chưa có request trong 14 ngày.</div>'
    maximum = max(1, max(int(item.get("requests") or 0) for item in daily))
    bars = []
    for item in daily:
        total = int(item.get("requests") or 0)
        errors = int(item.get("errors") or 0)
        height = max(4, round(total * 100 / maximum))
        error_height = round(errors * 100 / max(1, total))
        bars.append(
            f'<div class="api-chart-column" title="{escape(str(item.get("day")))}: {total} request, {errors} lỗi">'
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
    return "".join(rows) or "<tr><td colspan='6' class='muted'>Chưa có access log.</td></tr>"


def _admin_web_api_ledger_rows(fingerprint: str) -> str:
    rows = []
    for item in db_api_partner_ledger(fingerprint, limit=100):
        amount = int(item.get("amount") or 0)
        entry_type = str(item.get("entry_type") or "adjustment")
        rows.append(
            f'<tr><td>{escape(_admin_web_format_timestamp(item.get("created_at")))}</td>'
            f'<td><span class="ledger-pill {escape(entry_type)}">{escape(entry_type.title())}</span></td>'
            f'<td class="{"money-positive" if amount > 0 else "money-negative"}">{amount:+,}đ</td>'
            f'<td>{int(item.get("balance_after") or 0):,}đ</td>'
            f'<td><code>{escape(str(item.get("reference") or "—"))}</code></td>'
            f'<td>{escape(_admin_web_short(item.get("reason") or "", 72))}</td></tr>'
        )
    return "".join(rows) or "<tr><td colspan='6' class='muted'>Chưa có giao dịch trong ledger mới.</td></tr>"


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
        _admin_web_summary_card("Số dư", _admin_web_money(balance)),
        _admin_web_summary_card("Tier", f'{tier["name"]} · -{tier["discount_percent"]}%'),
        _admin_web_summary_card("Sản lượng tháng", _admin_web_money(tier["monthly_volume"])),
        _admin_web_summary_card("Usage ledger", _admin_web_money(abs(ledger["usage"]))),
        _admin_web_summary_card("Refund", _admin_web_money(ledger["refund"])),
        _admin_web_summary_card("Requests 14 ngày", analytics.get("total", 0)),
        _admin_web_summary_card("Tỷ lệ lỗi", f'{analytics.get("error_rate", 0)}%'),
        _admin_web_summary_card("Latency TB", f'{analytics.get("avg_ms", 0)} ms'),
        _admin_web_summary_card("Quota", f"{rate_limit}/phút"),
    ])
    warning = '<div class="alert error">Số dư vượt ngưỡng kiểm tra. Hãy đối soát trước khi bật lại key.</div>' if abs(balance) >= ADMIN_WEB_SUSPICIOUS_BALANCE_THRESHOLD else ""
    main = f"""
{warning}
<div class="api-detail-grid">
  <section class="action-card api-security-card">
    <div class="card-head"><h3>Security & Control</h3><span class="tag api">{escape(api_public_id)}</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="api_partner"><input type="hidden" name="mode" value="configure">
      {_admin_web_hidden_return("api", api_public_id)}<input type="hidden" name="target" value="{escape(api_public_id, quote=True)}">
      <label class="wide">IP whitelist <textarea name="allowed_ips" placeholder="203.0.113.10&#10;2001:db8::/48">{escape(allowed_ips)}</textarea><small>IPv4, IPv6 hoặc CIDR; để trống cho phép mọi IP.</small></label>
      <label>Quota/phút<input name="rate_limit" type="number" min="1" max="10000" value="{rate_limit}"></label>
      <label>Ngưỡng cảnh báo<input name="low_balance_threshold" type="number" min="0" value="{alert_threshold}"></label>
      <label class="toggle-field"><input type="checkbox" name="alert_enabled" value="1" {'checked' if alert_enabled else ''}><span class="switch"></span>Cảnh báo Telegram</label>
      <label class="wide">Ghi chú admin<input name="admin_note" value="{escape(str(normalized.get('admin_note') or ''), quote=True)}"></label>
      <label>Chế độ cấp bậc<select name="tier_mode"><option value="auto" {'selected' if tier['mode'] == 'auto' else ''}>Tự động theo doanh số tháng</option><option value="manual" {'selected' if tier['mode'] == 'manual' else ''}>Admin chỉ định</option></select></label>
      <label>Cấp bậc API<select name="tier_override">{''.join(f'<option value="{item["id"]}" {"selected" if item["id"] == tier["id"] else ""}>{item["name"]} — giảm {item["discount_percent"]}%</option>' for item in API_PARTNER_TIERS)}</select></label>
      <div class="wide tier-progress"><b>{tier['name']} · giảm {tier['discount_percent']}%</b><small>Doanh số tháng: {tier['monthly_volume']:,}đ</small>{f'<small>Còn {tier["remaining_to_next"]:,}đ để lên {tier["next_tier"]["name"]}</small>' if tier['next_tier'] else '<small>Đã đạt cấp cao nhất</small>'}</div>
      <button class="wide" type="submit">Lưu bảo mật & cấp bậc</button>
    </form>
  </section>
  <section class="action-card api-wallet-card">
    <div class="card-head"><h3>Ví & vòng đời key</h3><span class="tag {'readonly' if normalized.get('enabled') is not False else 'danger'}">{'ON' if normalized.get('enabled') is not False else 'REVOKED'}</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="api_partner">{_admin_web_hidden_return("api", api_public_id)}
      <input type="hidden" name="target" value="{escape(api_public_id, quote=True)}">
      <label>Thao tác<select name="mode"><option value="topup">Cộng</option><option value="subtract">Trừ</option><option value="set_balance">Set số dư</option><option value="enable">Bật key</option></select></label>
      <label>Số tiền<input name="amount" type="number" min="0" placeholder="500000"></label>
      <button class="wide" type="submit">Cập nhật partner</button>
    </form>
    <div class="danger-zone">
      <form method="post" action="{action_url}" data-confirm="Thu hồi key này ngay lập tức?">
        <input type="hidden" name="action" value="api_partner"><input type="hidden" name="mode" value="revoke"><input type="hidden" name="target" value="{escape(api_public_id, quote=True)}">{_admin_web_hidden_return("api", api_public_id)}
        <button class="danger" type="submit">Thu hồi key</button>
      </form>
      <form method="post" action="{action_url}" data-confirm="Tạo key mới và vô hiệu key hiện tại?">
        <input type="hidden" name="action" value="api_partner"><input type="hidden" name="mode" value="regenerate"><input type="hidden" name="target" value="{escape(api_public_id, quote=True)}">
        <button type="submit">Regenerate key</button>
      </form>
    </div>
  </section>
</div>
<section class="module-section ledger-panel"><div class="section-head"><div><h2>Sao kê dòng tiền</h2><p>Deposit, Usage và Refund tách bạch; mỗi dòng có running balance.</p></div><div class="ledger-summary"><span>Deposit <b class="money-positive">+{ledger['deposit']:,}đ</b></span><span>Usage <b class="money-negative">{ledger['usage']:,}đ</b></span><span>Refund <b class="money-positive">+{ledger['refund']:,}đ</b></span></div></div><div class="table-scroll"><table class="data-table api-ledger-table"><thead><tr><th>Thời gian</th><th>Loại</th><th>Biến động</th><th>Số dư sau</th><th>Tham chiếu</th><th>Nội dung</th></tr></thead><tbody>{_admin_web_api_ledger_rows(fingerprint)}</tbody></table></div></section>
<section class="module-section api-chart-panel"><div class="section-head"><div><h2>Lưu lượng 14 ngày</h2><p>Lỗi HTTP hiển thị bằng phần đỏ trong mỗi cột.</p></div></div>{_admin_web_api_traffic_chart(analytics)}</section>
<section class="module-section"><div class="section-head"><div><h2>Access logs</h2><p>Tối đa 80 request gần nhất; không lưu key, body hoặc query string.</p></div></div><div class="table-scroll"><table class="data-table api-log-table"><thead><tr><th>Thời gian</th><th>Method</th><th>Endpoint</th><th>Status</th><th>Latency</th><th>IP</th></tr></thead><tbody>{_admin_web_api_log_rows(fingerprint)}</tbody></table></div></section>
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
            _admin_web_summary_card("Giảm", _admin_web_money(item.get("discount"))),
            _admin_web_summary_card("Used", f"{item.get('used', 0)} / {item.get('quantity', 0)}"),
            _admin_web_summary_card("Hết hạn", item.get("expires") or "N/A"),
        ]
    )
    main = f"""
<section class="action-card">
  <div class="card-head"><h3>Coupon</h3><span class="tag write">promo</span></div>
  <form method="post" action="{action_url}" class="form-grid">
    <input type="hidden" name="action" value="coupon">
    {_admin_web_hidden_return("coupon", code)}
    <label>Thao tác<select name="mode"><option value="add">Cập nhật</option><option value="delete">Xóa</option></select></label>
    <label>Code<input name="code" value="{escape(str(code), quote=True)}" readonly></label>
    <label>Số lượng<input name="quantity" value="{escape(str(item.get('quantity') or ''), quote=True)}"></label>
    <label>Giảm tiền<input name="discount" value="{escape(str(item.get('discount') or ''), quote=True)}"></label>
    <label class="wide">Số ngày hết hạn mới<input name="days" placeholder="30"></label>
    <button class="wide" type="submit">Lưu coupon</button>
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
            _admin_web_summary_card("Loại", entity),
            _admin_web_summary_card("Status", record.get("status") or "pending"),
            _admin_web_summary_card("User", record.get("user_id") or item_id),
            _admin_web_summary_card("Order", record.get("order_code") or ""),
        ]
    )
    main = f"""
<section class="action-card">
  <div class="card-head"><h3>Cập nhật ticket</h3><span class="tag write">support</span></div>
  <form method="post" action="{action_url}" class="form-grid">
    <input type="hidden" name="action" value="support_update">
    {_admin_web_hidden_return(entity, item_id)}
    <input type="hidden" name="entity" value="{escape(entity, quote=True)}">
    <input type="hidden" name="item_id" value="{escape(item_id, quote=True)}">
    <label>Status<select name="status"><option value="pending">pending</option><option value="active">active</option><option value="resolved">resolved</option><option value="closed">closed</option><option value="rejected">rejected</option></select></label>
    <label>Ghi chú<input name="admin_note" value="{escape(str(record.get('admin_note') or ''), quote=True)}"></label>
    <button class="wide" type="submit">Cập nhật ticket</button>
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
    <div class="action-group-label">User & ví <span>money / profile / risk</span></div>
  <section class="action-card is-wallet">
    <div class="card-head"><h3>Ví user</h3><span class="tag danger">money</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="user_balance">
      <label>User ID<input name="user_id" placeholder="123456789" required></label>
      <label>Số tiền<input name="amount" placeholder="100000" required></label>
      <label>Kiểu
        <select name="mode">
          <option value="add">Cộng tiền</option>
          <option value="sub">Trừ tiền</option>
          <option value="set">Set số dư</option>
        </select>
      </label>
      <label class="wide">Lý do<input name="reason" value="Admin web"></label>
      <button class="wide" type="submit">Thực hiện</button>
    </form>
  </section>
  <section class="action-card">
    <div class="card-head"><h3>Hồ sơ user</h3><span class="tag write">profile</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="user_profile">
      <label>User ID<input name="user_id" placeholder="123456789" required></label>
      <label>Username<input name="username" placeholder="@username"></label>
      <label class="wide">Tên hiển thị<input name="full_name" placeholder="Tên khách"></label>
      <label class="wide">Email<input name="email" placeholder="email nhận hàng"></label>
      <label class="wide">Ghi chú admin<textarea name="admin_note" placeholder="Ghi chú nội bộ"></textarea></label>
      <button class="wide" type="submit">Lưu hồ sơ</button>
    </form>
  </section>
  <section class="action-card is-critical">
    <div class="card-head"><h3>Ban / unban</h3><span class="tag danger">risk</span></div>
  <form method="post" action="{action_url}" class="form-grid" data-confirm="Cập nhật trạng thái ban user?">
      <input type="hidden" name="action" value="user_ban">
      <label>User ID<input name="user_id" required></label>
      <label>Trang thai
        <select name="mode"><option value="ban">Ban</option><option value="unban">Unban</option></select>
      </label>
      <button class="wide danger" type="submit">Cập nhật user</button>
    </form>
  </section>
  </div>
  <div class="action-column action-column-catalog">
    <div class="action-group-label">Catalog <span>products</span></div>
  <section class="action-card is-catalog">
    <div class="card-head"><h3>Sản phẩm</h3><span class="tag write">catalog</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="product_update">
      <label>Product ID<input name="product_id" required></label>
      <label>Giá bán mới<input name="price" placeholder="bỏ trống nếu không đổi"></label>
      <label>Giá vốn mới<input name="cost_price" placeholder="local/manual"></label>
      <label class="wide">Tên mới<input name="name" placeholder="bỏ trống nếu không đổi"></label>
      <label class="wide">Danh mục<input name="store_category" placeholder="vd: Streaming, Social, Tools"></label>
      <label>Thời hạn<input name="duration" placeholder="vd: 30 ngày"></label>
      <label>Bảo hành<input name="warranty" placeholder="vd: 7 ngày, 30 ngày"></label>
      <label>Giới hạn manual<input name="max_pending_orders" placeholder="vd: 10"></label>
      <label class="wide">Mô tả<textarea name="description" placeholder="bỏ trống nếu không đổi"></textarea></label>
      <label class="wide">Thêm stock local<textarea name="stock_items" placeholder="Mỗi dòng 1 item, chỉ nên dùng với sản phẩm local stock"></textarea></label>
      <button class="wide" type="submit">Lưu sản phẩm</button>
    </form>
  </section>
  <section class="action-card is-catalog">
    <div class="card-head"><h3>Tạo sản phẩm</h3><span class="tag write">new</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="product_create">
      <label>Product ID<input name="product_id" placeholder="bỏ trống để tự tạo"></label>
      <label>Giá bán<input name="price" placeholder="35000" required></label>
      <label>Giá vốn<input name="cost_price" placeholder="bắt buộc để tính lãi" required></label>
      <label class="wide">Tên<input name="name" placeholder="Tên sản phẩm" required></label>
      <label>Loại<select name="requires_gmail"><option value="0">Local stock</option><option value="1">Manual/Gmail</option></select></label>
      <label>Thời hạn<input name="duration" placeholder="30 ngày"></label>
      <label>Bảo hành<input name="warranty" placeholder="7 ngày, 30 ngày, Không"></label>
      <label class="wide">Mô tả<textarea name="description" placeholder="Mô tả ngắn"></textarea></label>
      <label class="wide">Stock ban đầu<textarea name="stock_items" placeholder="Mỗi dòng 1 item, chỉ dùng với local stock"></textarea></label>
      <button class="wide" type="submit">Tạo sản phẩm</button>
    </form>
  </section>
  <section class="action-card is-critical">
    <div class="card-head"><h3>Kho sản phẩm</h3><span class="tag danger">stock</span></div>
    <form method="post" action="{action_url}" class="form-grid" data-confirm="Xóa toàn bộ stock local của sản phẩm này?">
      <input type="hidden" name="action" value="product_stock">
      <input type="hidden" name="mode" value="clear_stock">
      <label class="wide">Product ID<input name="product_id" placeholder="product_id local stock" required></label>
      <button class="wide danger" type="submit">Xóa stock local</button>
    </form>
    <form method="post" action="{action_url}" class="form-grid" data-confirm="Xóa vĩnh viễn sản phẩm khỏi catalog?">
      <input type="hidden" name="action" value="product_delete">
      <label class="wide">Product ID<input name="product_id" placeholder="product_id cần xóa" required></label>
      <button class="wide danger" type="submit">Xóa sản phẩm</button>
    </form>
  </section>
  </div>
  <div class="action-column">
    <div class="action-group-label">Vận hành <span>api / orders / support</span></div>
  <section class="action-card">
    <div class="card-head"><h3>API partner</h3><span class="tag write">partner</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="api_partner">
      <label>Thao tác
        <select name="mode"><option value="topup">Nạp tiền key</option><option value="create">Tạo key</option><option value="disable">Tắt key</option><option value="enable">Bật key</option></select>
      </label>
      <label>Số tiền<input name="amount" placeholder="500000"></label>
      <label class="wide">Key hoặc tên partner<input name="target" placeholder="LAMSHOP... hoặc tên"></label>
      <button class="wide" type="submit">Cập nhật API</button>
    </form>
  </section>
  <section class="action-card">
    <div class="card-head"><h3>Đơn hàng</h3><span class="tag write">orders</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="order_tools">
      <label>Mã đơn<input name="order_code" placeholder="ICLD123456" required></label>
      <label>Thao tác
        <select name="mode"><option value="set_email">Gắn email</option><option value="admin_note">Ghi chú admin</option></select>
      </label>
      <label class="wide">Giá trị<input name="value" placeholder="email hoặc ghi chú"></label>
      <button class="wide" type="submit">Cập nhật đơn</button>
    </form>
  </section>
  <section class="action-card">
    <div class="card-head"><h3>Coupon</h3><span class="tag write">promo</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="coupon">
      <label>Thao tác
        <select name="mode"><option value="add">Thêm / cập nhật</option><option value="delete">Xóa coupon</option></select>
      </label>
      <label>Ma coupon<input name="code" placeholder="SALE2026" required></label>
      <label>Số lượng<input name="quantity" placeholder="100"></label>
      <label>Giảm tiền<input name="discount" placeholder="35000"></label>
      <label class="wide">Số ngày hết hạn<input name="days" placeholder="30"></label>
      <button class="wide" type="submit">Lưu coupon</button>
    </form>
  </section>
  <section class="action-card">
    <div class="card-head"><h3>Support ticket</h3><span class="tag write">support</span></div>
    <form method="post" action="{action_url}" class="form-grid">
      <input type="hidden" name="action" value="support_update">
      <label>Loại
        <select name="entity"><option value="live_chat">Live chat</option><option value="warranty">Bảo hành</option><option value="withdrawal">Rút tiền</option></select>
      </label>
      <label>ID ticket<input name="item_id" placeholder="ticket/order id" required></label>
      <label>Status<input name="status" placeholder="pending / resolved / rejected"></label>
      <label class="wide">Ghi chú<textarea name="admin_note" placeholder="Ghi chú xử lý"></textarea></label>
      <button class="wide" type="submit">Cập nhật support</button>
    </form>
  </section>
  <section class="action-card is-critical">
    <div class="card-head"><h3>Hệ thống</h3><span class="tag danger">ops</span></div>
    <form method="post" action="{action_url}" class="form-grid" data-confirm="Cập nhật trạng thái hệ thống?">
      <input type="hidden" name="action" value="system_toggle">
      <label class="wide">Thao tác
        <select name="mode">
          <option value="maintenance_on">Bật bảo trì</option>
          <option value="maintenance_off">Tắt bảo trì</option>
          <option value="ai_on">Bật AI auto reply</option>
          <option value="ai_off">Tắt AI auto reply</option>
        </select>
      </label>
      <button class="wide danger" type="submit">Cập nhật hệ thống</button>
    </form>
  </section>
  <section class="action-card is-critical">
    <div class="card-head"><h3>Pending manual</h3><span class="tag danger">cleanup</span></div>
    <form method="post" action="{action_url}" class="form-grid" data-confirm="Xóa pending manual sẽ giải phóng slot. Bạn đã kiểm tra hoàn tiền nếu cần?">
      <input type="hidden" name="action" value="pending_manual">
      <label>Thao tác
        <select name="mode"><option value="clear_one">Xóa 1 đơn</option><option value="clear_all">Xóa tất cả</option></select>
      </label>
      <label>Mã đơn<input name="order_code" placeholder="bỏ trống nếu xóa tất cả"></label>
      <button class="wide danger" type="submit">Dọn pending</button>
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
    <div class="table-scroll"><table class="mini-table"><thead><tr><th>ID</th><th>Tên</th><th>Số dư</th><th>Trạng thái</th></tr></thead><tbody>{_admin_web_render_users()}</tbody></table></div>
  </section>
  <section>
    <h2>Sản phẩm</h2>
    <div class="table-scroll"><table class="mini-table"><thead><tr><th>ID</th><th>Tên</th><th>Giá</th><th>Stock</th></tr></thead><tbody>{_admin_web_render_products()}</tbody></table></div>
  </section>
  <section>
    <h2>API partner</h2>
    <div class="table-scroll"><table class="mini-table"><thead><tr><th>Key</th><th>Tên</th><th>Số dư</th><th>On/off</th></tr></thead><tbody>{_admin_web_render_api_keys()}</tbody></table></div>
  </section>
  <section>
    <h2>Don gan day</h2>
    <div class="table-scroll"><table class="mini-table"><thead><tr><th>Mã</th><th>Sản phẩm</th><th>Status</th><th>Tiền</th></tr></thead><tbody>{_admin_web_render_orders()}</tbody></table></div>
  </section>
  <section>
    <h2>Audit web admin</h2>
    <div class="table-scroll"><table class="mini-table"><thead><tr><th>Lúc</th><th>Action</th><th>Target</th><th>Status</th><th>Ghi chú</th></tr></thead><tbody>{_admin_web_render_audit_log()}</tbody></table></div>
  </section>
</div>
"""


def _admin_web_unread_count() -> tuple[int, str]:
    details = []
    c_manual = len(pending_manual_orders) if isinstance(pending_manual_orders, dict) else 0
    if c_manual: details.append(f"{c_manual} đơn manual")
    
    c_chat = sum(1 for v in (live_chats.values() if isinstance(live_chats, dict) else []) if isinstance(v, dict) and v.get("status") in {"active", "open", "pending"})
    if c_chat: details.append(f"{c_chat} tin nhắn live chat")
    
    c_war = sum(1 for v in (warranty_claims.values() if isinstance(warranty_claims, dict) else []) if isinstance(v, dict) and v.get("status") in {"pending"})
    if c_war: details.append(f"{c_war} yêu cầu bảo hành")
    
    c_with = sum(1 for v in (withdrawal_requests.values() if isinstance(withdrawal_requests, dict) else []) if isinstance(v, dict) and v.get("status") in {"pending"})
    if c_with: details.append(f"{c_with} lệnh rút tiền")
    
    total = c_manual + c_chat + c_war + c_with
    msg = "Đang chờ xử lý:\\n- " + "\\n- ".join(details) if total > 0 else "Không có thông báo mới."
    return total, msg

def _admin_web_layout(title: str, body: str, request=None) -> str:
    key_query = _admin_web_key_query(request) if request is not None else ""
    unread, unread_msg = _admin_web_unread_count()
    if unread > 0:
        bell_html = (
            '<a href="javascript:void(0)" title="Thông báo cần xử lý" aria-label="Thông báo cần xử lý"'
            f' onclick="showToast(`{unread_msg}`)">🔔<span class="bell-count">{unread}</span></a>'
        )
    else:
        bell_html = (
            '<a href="javascript:void(0)" title="Không có thông báo mới" aria-label="Không có thông báo mới"'
            ' onclick="showToast(`Không có thông báo mới`)">🔔</a>'
        )
    current_path = str(request.url.path) if request is not None else ""
    nav_items = (
        ("/admin", "Dashboard"),
        ("/admin/categories", "Danh mục"),
        ("/admin/commands", "Lệnh admin"),
    )
    nav_html = "".join(
        '<a href="{href}"{current}>{label}</a>'.format(
            href=f"{path}{key_query}",
            current=' aria-current="page"' if current_path == path else "",
            label=label,
        )
        for path, label in nav_items
    )
    csrf_token = escape(_admin_web_csrf_token(request)) if request is not None else ""
    csrf_input = f'<input type="hidden" name="csrf_token" value="{csrf_token}">'
    body = re.sub(r'(<form\b(?=[^>]*\bmethod=["\']post["\'])[^>]*>)', rf'\1{csrf_input}', body, flags=re.IGNORECASE)
    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <meta name="theme-color" content="#0b0c0f">
  <title>{escape(title)}</title>
  {ADMIN_WEB_FONT_LINKS}
  <style>
{ADMIN_WEB_UI_CSS}
  </style>
  <script>if (localStorage.getItem('admin_theme') === 'light') document.documentElement.classList.add('light-mode');</script>
</head>
<body>
  <a class="skip-link" href="#admin-main">Tới nội dung chính</a>
  <header class="admin-topbar"><nav>
    <button id="mobileMenuToggle" class="mobile-menu-toggle" type="button" aria-label="Mở menu điều hướng" aria-controls="adminNavLinks" aria-expanded="false" onclick="toggleMobileMenu()"><span></span><span></span><span></span></button>
    <strong class="admin-brand"><span class="admin-brand-mark">L</span><span>Lâm Shop <b>Ops</b><small>Control center</small></span></strong>
    <div class="topbar-actions">{bell_html}<button id="themeToggle" onclick="toggleTheme()" title="Đổi nền sáng/tối" aria-label="Đổi nền sáng tối">◐</button></div>
    <div id="adminNavLinks" class="admin-nav-links">{nav_html}<form method="post" action="/admin/logout">{csrf_input}<button id="admin-logout" type="submit">Đăng xuất</button></form></div>
  </nav></header>
  <button id="mobileMenuBackdrop" class="mobile-menu-backdrop" type="button" aria-label="Đóng menu" onclick="toggleMobileMenu(false)"></button>
  <div id="toast-container"></div>
  <main id="admin-main">{body}</main>
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
  const light = document.documentElement.classList.toggle('light-mode');
  localStorage.setItem('admin_theme', light ? 'light' : 'dark');
  document.getElementById('themeToggle').textContent = light ? '◑' : '◐';
}}
document.addEventListener('DOMContentLoaded', () => {{
  if (document.documentElement.classList.contains('light-mode')) {{
    document.getElementById('themeToggle').textContent = '◑';
  }}
}});
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
        ("Doanh thu hôm nay", f"{today_revenue:,} VND", "revenue"),
        ("Lãi gộp hôm nay", f"{finance['today_profit']:,} VND", "revenue"),
        ("Tổng doanh thu", f"{finance['revenue']:,} VND", "revenue"),
        ("Tổng lãi có snapshot", f"{finance['profit']:,} VND", "revenue"),
        ("Độ phủ giá vốn", f"{finance['costed']}/{completed_orders} đơn", "revenue"),
        ("Đơn thành công", completed_orders, "orders"),
        ("Pending pay", len(pending_orders), "orders"),
        ("Sản phẩm", len(products), "products"),
        ("Low stock", _admin_web_low_stock_count(), "products"),
        ("Users", len(user_data_db), "users"),
        ("Manual pending", len(pending_manual_orders), "orders"),
        ("API partner on", f"{active_api_keys}/{len(api_keys)}", "api"),
        ("Số dư API", f"{api_balance:,} VND", "api metric-wide"),
        ("Coupon", len(coupons) if isinstance(coupons, dict) else 0, "promo"),
        ("Promo hôm nay", f"{promo_spent_today:,} VND", "promo"),
        ("Support open", open_support, "support"),
        ("Bot uptime", _uptime_text, "support"),
    ]
    _get_cat_fn = globals().get("get_product_category") or (lambda n: "")
    _all_cats = set(
        str(p.get("store_category") or "") or str(_get_cat_fn(str(p.get("name") or "")) or "")
        for p in products.values() if isinstance(p, dict)
    )
    _cats_with_img = sum(1 for c in _all_cats if c and _admin_web_category_image_path(c) is not None)
    metrics.append(("Ảnh danh mục", f"{_cats_with_img}/{len(_all_cats)}", "products"))
    cards = "".join(
        f'<a class="metric metric-{escape(kind)}" href="#{escape(_admin_web_metric_target(k, kind), quote=True)}" data-page-link="{escape(_admin_web_metric_target(k, kind), quote=True)}" aria-label="Mở {escape(k, quote=True)}">'
        f'<span>{escape(k)}</span><b>{escape(str(v))}</b></a>'
        for k, v, kind in metrics
    )
    plan_rows = [
        ("live", "Dashboard module", "Tổng quan, products, orders, users, API, promo, support, ops, audit."),
        ("live", "Action web", "Ví user, ban/unban, product update, stock add, API partner, coupon, system toggle, clear pending."),
        ("live", "Audit log", "Ghi riêng data_admin_action_log.json cho mỗi action web."),
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
      <b>Lâm Shop Admin</b>
      <span>MMO ops center</span>
    </div>
    <a href="#overview" data-page-link="overview">Tổng quan</a>
    <a href="#actions" data-page-link="actions">Actions</a>
    <a href="#products" data-page-link="products">Sản phẩm</a>
    <a href="#orders" data-page-link="orders">Đơn hàng</a>
    <a href="#users" data-page-link="users">Users</a>
    <a href="#api" data-page-link="api">API partner</a>
    <a href="#promo" data-page-link="promo">Khuyến mãi</a>
    <a href="#support" data-page-link="support">Hỗ trợ</a>
    <a href="#ops" data-page-link="ops">Vận hành</a>
    <a href="#audit" data-page-link="audit">Audit</a>
    <a href="/admin/commands{_admin_web_key_query(request) if request is not None else ''}">Lệnh admin</a>
  </aside>
  <section class="workspace">
    <div class="workspace-head">
      <div>
        <span class="eyebrow">MMO admin app</span>
        <h1>Lâm Shop Control Center</h1>
        <p>Bảng điều khiển tập trung cho sản phẩm, kho, đơn hàng, user, ví, API partner, coupon, support và vận hành.</p>
      </div>
      <div class="console-tools">
        <input id="globalSearch" placeholder="Tìm trong module hiện tại..." oninput="filterAdminTables()">
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
        <div><h2>Tổng quan</h2><p>Chỉ số vận hành hiện tại, cập nhật trực tiếp từ runtime.</p></div>
      </div>
      <div class="grid">{cards}</div>
      {_admin_web_overview_board(request)}
    </section>

    <section class="module-section admin-page" id="actions">
      <div class="section-head"><div><h2>Actions</h2><p>Thao tác ghi trực tiếp vào database/runtime, có audit log bắt buộc.</p></div></div>
      <div class="actions-grid">{actions}</div>
    </section>

    <section class="module-section admin-page" id="products">
      <div class="section-head">
        <div><h2>Sản phẩm & tồn kho</h2><p>Quản lý catalog local và manual. Đang hiển thị {min(len(products), ADMIN_WEB_PRODUCT_TABLE_LIMIT):,}/{len(products):,} sản phẩm mới nhất để dashboard tải nhanh.</p></div>
        <select onchange="filterTableKind('productsTable', this.value)"><option value="">Tất cả loại</option><option value="local">local</option><option value="manual">manual</option></select>
      </div>
      <div class="table-scroll"><table class="data-table" id="productsTable"><thead><tr><th>ID</th><th>Tên</th><th>Loại</th><th>Giá</th><th>Stock</th><th>Pending</th><th>Sold</th><th>Sync</th><th></th></tr></thead><tbody>{_admin_web_render_product_rows(request, limit=ADMIN_WEB_PRODUCT_TABLE_LIMIT)}</tbody></table></div>
    </section>

    <section class="module-section admin-page" id="orders">
      <div class="section-head"><div><h2>Đơn hàng</h2><p>Recent orders và trạng thái thanh toán/giao hàng. Đang hiển thị {min(len(order_history), ADMIN_WEB_ORDER_TABLE_LIMIT):,}/{len(order_history):,} đơn mới nhất.</p></div></div>
      <div class="table-scroll"><table class="data-table" id="ordersTable"><thead><tr><th>Mã</th><th>Sản phẩm</th><th>User</th><th>Status</th><th>Tiền</th><th>Qty</th><th>Lúc</th><th></th></tr></thead><tbody>{_admin_web_render_order_rows(request, limit=ADMIN_WEB_ORDER_TABLE_LIMIT)}</tbody></table></div>
    </section>

    <section class="module-section admin-page" id="users">
      <div class="section-head">
        <div><h2>Users & ví</h2><p>Top users theo số dư, đơn hàng và trạng thái ban. Đang hiển thị {min(len(user_data_db), ADMIN_WEB_USER_TABLE_LIMIT):,}/{len(user_data_db):,} user.</p></div>
        <select onchange="filterTableKind('usersTable', this.value)"><option value="">Tất cả</option><option value="active">active</option><option value="banned">banned</option></select>
      </div>
      <div class="table-scroll"><table class="data-table" id="usersTable"><thead><tr><th>ID</th><th>User</th><th>Số dư</th><th>Orders</th><th>Total spent</th><th>Status</th><th></th></tr></thead><tbody>{_admin_web_render_user_rows(request, limit=ADMIN_WEB_USER_TABLE_LIMIT)}</tbody></table></div>
    </section>

    <section class="module-section admin-page api-operations-page" id="api">
      <div class="api-hero">
        <div><span class="eyebrow">Partner infrastructure</span><h2>API Operations Center</h2><p>Bảo mật key, kiểm soát lưu lượng, vận hành ví và theo dõi sức khỏe API tại một nơi.</p></div>
        <a class="button dark" href="/admin/api-partners/export.csv{_admin_web_key_query(request) if request is not None else ''}">Xuất CSV</a>
      </div>
      <div class="api-kpi-grid">
        <article><span>Tổng partner</span><b>{len(api_keys):,}</b><small>Đã đăng ký</small></article>
        <article><span>Đang hoạt động</span><b>{sum(1 for d in api_keys.values() if not isinstance(d, dict) or d.get('enabled') is not False):,}</b><small>Key đang ON</small></article>
        <article><span>Số dư thấp</span><b>{sum(1 for d in api_keys.values() if isinstance(d, dict) and _admin_web_int(d.get('balance'), 0) <= max(0, _admin_web_int(d.get('low_balance_threshold'), 100000))):,}</b><small>Cần theo dõi</small></article>
        <article><span>Requests 14 ngày</span><b>{db_api_analytics('', 14).get('total', 0):,}</b><small>{db_api_analytics('', 14).get('error_rate', 0)}% lỗi</small></article>
      </div>
      <div class="api-filter-bar">
        <select id="apiStatusFilter" onchange="filterApiPartners()"><option value="">Mọi trạng thái</option><option value="active">Đang hoạt động</option><option value="disabled">Đã thu hồi</option><option value="admin">Admin</option></select>
        <select id="apiBalanceFilter" onchange="filterApiPartners()"><option value="">Mọi số dư</option><option value="low">Dưới ngưỡng</option></select>
        <span class="tag {'danger' if suspicious_api_balances else 'readonly'}">{suspicious_api_balances} bất thường</span>
      </div>
      <div class="table-scroll"><table class="data-table api-partner-table" id="apiTable"><thead><tr><th>Key / Public ID</th><th>Partner</th><th>Số dư</th><th>Trạng thái</th><th>Quota & Alert</th><th>Ghi chú</th><th>Thao tác nhanh</th></tr></thead><tbody>{_admin_web_render_api_partner_rows(request, limit=ADMIN_WEB_API_TABLE_LIMIT)}</tbody></table></div>
    </section>

    <section class="module-section admin-page" id="promo">
      <div class="section-head"><div><h2>Khuyến mãi</h2><p>Coupon hiện có, flash sale và combo sẽ mở rộng ở phase sau.</p></div></div>
      <div class="split-grid">
        <div class="table-scroll"><table class="data-table" id="couponTable"><thead><tr><th>Code</th><th>Giảm</th><th>Used</th><th>Hết hạn</th><th></th></tr></thead><tbody>{_admin_web_render_coupon_rows(request)}</tbody></table></div>
        <div class="mini-panel">
          <h3>Promo snapshot</h3>
          <p><b>{len(flash_sales) if isinstance(flash_sales, dict) else 0}</b> flash sale</p>
          <p><b>{len(combo_deals) if isinstance(combo_deals, dict) else 0}</b> combo deal</p>
          <p><b>{len(active_giveaways) if isinstance(active_giveaways, dict) else 0}</b> giveaway</p>
          <p><b>{_admin_web_money(promo_spent_today)}</b> promo spent hôm nay</p>
        </div>
      </div>
    </section>

    <section class="module-section admin-page" id="support">
      <div class="section-head"><div><h2>Hỗ trợ</h2><p>Live chat, bảo hành và rút tiền gom chung để admin không bỏ sót ticket.</p></div></div>
      <div class="table-scroll"><table class="data-table" id="supportTable"><thead><tr><th>Loại</th><th>ID</th><th>User</th><th>Status</th><th>Nội dung</th><th></th></tr></thead><tbody>{_admin_web_render_support_rows(request)}</tbody></table></div>
    </section>

    <section class="module-section admin-page" id="ops">
      <div class="section-head"><div><h2>Vận hành</h2><p>Trạng thái cron MBBank, bot user/admin, log runtime và manual pending.</p></div></div>
      <div class="split-grid">
        <div class="table-scroll"><table class="data-table"><thead><tr><th>Status</th><th>Module</th><th>Ghi chú</th></tr></thead><tbody>{_admin_web_render_ops_status_rows(request)}</tbody></table></div>
        <div class="ops-log-panel">{_admin_web_render_ops_log_panel()}</div>
      </div>
      <div class="split-grid">
        <div class="table-scroll"><table class="data-table" id="pendingManualTable"><thead><tr><th>Mã</th><th>Sản phẩm</th><th>User</th><th>Tiền</th><th>Lúc</th></tr></thead><tbody>{_admin_web_render_pending_manual_rows()}</tbody></table></div>
        <div class="table-scroll">
          {_admin_web_render_payment_config(request)}
          <table class="data-table" style="margin-top:20px;"><thead><tr><th>Status</th><th>Module</th><th>Ghi chú</th></tr></thead><tbody>{plan_html}</tbody></table>
        </div>
      </div>
    </section>

    <section class="module-section admin-page" id="audit">
      <div class="section-head"><div><h2>Audit</h2><p>Lịch sử thao tác từ web admin.</p></div></div>
      <div class="table-scroll"><table class="data-table" id="auditTable"><thead><tr><th>Lúc</th><th>Action</th><th>Target</th><th>Status</th><th>IP</th><th>Message</th></tr></thead><tbody>{_admin_web_render_audit_rows()}</tbody></table></div>
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
  if (search) search.placeholder = target === 'overview' ? 'Tìm trong các bảng...' : 'Tìm trong module hiện tại...';
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
  <p>Danh sách toàn bộ lệnh admin đang có trong bot, lọc theo từ khóa và mức rủi ro để quản lý vận hành nhanh hơn trên web.</p>
  <div class="hero-actions">
    <a class="button dark" href="/admin" onclick="this.href='/admin'+location.search">Dashboard</a>
    <a class="button" href="/api/admin/commands" onclick="this.href='/api/admin/commands'+location.search">JSON catalog</a>
  </div>
</section>
<div class="toolbar">
  <input id="q" placeholder="Tìm lệnh, nhóm, mô tả..." oninput="filterCommands()">
  <select id="risk" onchange="filterCommands()">
    <option value="">Tất cả risk</option>
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
        parts.append("Số dư bất thường")
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
        "user_balance": "Cập nhật ví user",
        "user_ban": "Ban/unban user",
        "user_profile": "Sửa hồ sơ user",
        "product_create": "Thêm sản phẩm",
        "product_update": "Sửa sản phẩm",
        "product_stock": "Tồn kho sản phẩm",
        "product_delete": "Xóa sản phẩm",
        "api_partner": "API partner",
        "order_tools": "Công cụ đơn hàng",
        "coupon": "Coupon",
        "system_toggle": "Hệ thống",
        "pending_manual": "Pending manual",
        "support_update": "Support",
        "web_login": "Đăng nhập web admin",
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
        lines.append(f"<b>Kết quả:</b> {escape(_admin_web_short(message, 220))}")
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
        "message": "Admin đã mở dashboard web.",
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
        return False, "User ID không hợp lệ."
    amount = _admin_web_int(_admin_web_form_text(form, "amount"), None)
    if amount is None or amount < 0:
        return False, "Số tiền không hợp lệ."
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
        return False, "Kiểu cập nhật ví không hợp lệ."
    db_update_balance(int(user_id), int(new_balance), reason=f"{reason} ({mode})")
    await save_data(force=True, tables=[USERS_FILE, TRANSACTION_HISTORY_FILE])
    return True, f"Da cap nhat vi user {user_id}: {current:,} -> {new_balance:,} VND."


async def _admin_web_action_user_ban(form):
    user_id = _admin_web_form_text(form, "user_id")
    if not user_id.isdigit():
        return False, "User ID không hợp lệ."
    target_id = int(user_id)
    mode = _admin_web_form_text(form, "mode") or "ban"
    if mode == "ban":
        banned_users.add(target_id)
        msg = f"Da ban user {target_id}."
    elif mode == "unban":
        banned_users.discard(target_id)
        msg = f"Da unban user {target_id}."
    else:
        return False, "Thao tác ban/unban không hợp lệ."
    await save_data(force=True, tables=[BANNED_USERS_FILE])
    return True, msg


async def _admin_web_action_user_profile(form):
    user_id = _admin_web_form_text(form, "user_id")
    if not user_id.isdigit():
        return False, "User ID không hợp lệ."
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
        return False, "Chưa có thay đổi hồ sơ user."
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
        return False, "Tên sản phẩm không được rỗng."
    price = _admin_web_int(_admin_web_form_text(form, "price"), None)
    if price is None or price < 0:
        return False, "Giá sản phẩm không hợp lệ."
    cost_price = _admin_web_int(_admin_web_form_text(form, "cost_price"), None)
    if cost_price is None or cost_price < 0:
        return False, "Giá vốn không hợp lệ."
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
        "warranty": warranty or "Không",
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
            return False, "Giá mới không hợp lệ."
        product["price"] = int(price)
        changes.append("gia ban")
    if cost_price_text:
        cost_price = _admin_web_int(cost_price_text, None)
        if cost_price is None or cost_price < 0:
            return False, "Giá vốn mới không hợp lệ."
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
            return False, "Giới hạn manual không hợp lệ."
        product["max_pending_orders"] = int(max_pending)
        changes.append("gioi han manual")
    if stock_text:
        if product.get("requires_gmail"):
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
        return False, "Chưa có thay đổi nào để lưu."
    await save_data(force=True, tables=[PRODUCTS_FILE])
    return True, f"Da cap nhat {product_id}: {', '.join(changes)}."


async def _admin_web_action_product_stock(form):
    product_id = _admin_web_form_text(form, "product_id")
    product = products.get(product_id)
    if not isinstance(product, dict):
        return False, "Khong tim thay product_id."
    mode = _admin_web_form_text(form, "mode")
    if mode == "clear_stock":
        if product.get("requires_gmail"):
            return False, "Chi xoa stock local cho san pham local stock."
        count = len(product.get("stock") or []) if isinstance(product.get("stock"), list) else 0
        product["stock"] = []
        await save_data(force=True, tables=[PRODUCTS_FILE])
        return True, f"Da xoa {count} stock local cua {product_id}."
    return False, "Thao tác stock không hợp lệ."


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
        return True, f"Đã tạo API partner {partner_name}. Key mới (chỉ hiển thị lần này): {new_key}"

    api_key = _admin_web_find_api_key(target)
    if not api_key:
        return False, "Không tìm thấy API key/partner."
    data = _api_normalize_partner_key(api_key)
    if not isinstance(data, dict):
        return False, "Dữ liệu API key không hợp lệ."

    partner_name = data.get("name") or api_key
    if mode in {"topup", "subtract", "set_balance"}:
        if mode != "set_balance" and amount <= 0:
            return False, "Số tiền phải lớn hơn 0."
        if mode == "set_balance" and amount < 0:
            return False, "Số dư không được âm."
        if mode == "set_balance":
            adjusted, new_balance, _ = await safe_api_set_balance(
                api_key, amount, save=True, reason=f"Admin web set {partner_name}",
                ledger_type="adjustment", admin_actor="admin_web",
            )
        else:
            delta = amount if mode == "topup" else -amount
            current = _api_get_partner_display_balance(api_key, data)
            if current + delta < 0:
                return False, "Số dư không đủ để trừ."
            adjusted, new_balance, _ = await safe_api_adjust_balance(
                api_key, delta, save=True, reason=f"Admin web {mode} {partner_name}",
                ledger_type="deposit" if mode == "topup" else "adjustment", admin_actor="admin_web",
            )
        if not adjusted:
            return False, "Không cập nhật được số dư partner."
        return True, f"Đã cập nhật {partner_name}: số dư mới {int(new_balance):,} VND."

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
        return True, f"Đã lưu bảo mật, quota và tier pricing cho {partner_name}."

    if mode in {"disable", "revoke"}:
        data["enabled"] = False
        data["revoked_at"] = int(time.time())
        await save_data(force=True, tables=[API_KEYS_FILE])
        return True, f"Đã thu hồi API key của {partner_name}."
    if mode == "enable":
        if data.get("rotated_to"):
            return False, "Key cũ đã regenerate, không thể bật lại. Hãy dùng key mới."
        data["enabled"] = True
        data.pop("revoked_at", None)
        await save_data(force=True, tables=[API_KEYS_FILE])
        return True, f"Đã bật API key của {partner_name}."
    if mode == "regenerate":
        result = await _api_rotate_partner_key(api_key)
        if not result:
            return False, "Không regenerate được API key."
        new_key, new_data = result
        return True, f"Đã regenerate {new_data.get('name') or partner_name}. Key mới (chỉ hiển thị lần này): {new_key}"
    return False, "Thao tác API partner không hợp lệ."


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
        return False, "Giá trị cập nhật không được rỗng."
    if mode == "set_email":
        try:
            is_valid_email = bool(EMAIL_REGEX.match(value))
        except Exception:
            is_valid_email = "@" in value and "." in value
        if not is_valid_email:
            return False, "Email không hợp lệ."
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
        return False, "Thao tác đơn hàng không hợp lệ."
    tables = sorted({table_name for table_name, _ in records})
    await save_data(force=True, tables=tables)
    return True, f"Da cap nhat {label} cho {order_code} ({len(records)} record)."


async def _admin_web_action_coupon(form):
    if not isinstance(coupons, dict):
        return False, "Dữ liệu coupon không hợp lệ."
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
        return False, "Thao tác coupon không hợp lệ."
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
        return False, "Thao tác hệ thống không hợp lệ."
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
        return False, "Thao tác pending manual không hợp lệ."
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
    return False, "Cấu hình thanh toán là read-only trên web. Hãy cập nhật secret trong deployment environment rồi restart bot."


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
        return False, "Tên danh mục không được rỗng."
    if len(name) > 100:
        return False, "Tên danh mục quá dài."
    if _admin_web_category_exists(name):
        return False, "Danh mục đã tồn tại."
    store_categories[name] = _admin_web_category_form_config(form)
    await save_data(force=True, tables=[STORE_CATEGORIES_FILE])
    return True, f"Đã thêm danh mục {name}."


async def _admin_web_action_category_update(form):
    old_name = _admin_web_form_text(form, "category_name")
    new_name = _admin_web_form_text(form, "new_name") or old_name
    if not old_name or not _admin_web_category_exists(old_name):
        return False, "Không tìm thấy danh mục."
    if len(new_name) > 100:
        return False, "Tên danh mục quá dài."
    if new_name != old_name and _admin_web_category_exists(new_name):
        return False, "Tên danh mục mới đã tồn tại."
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
    return True, f"Đã cập nhật danh mục {new_name} ({moved_products} sản phẩm được chuyển)."


async def _admin_web_action_category_visibility(form):
    name = _admin_web_form_text(form, "category_name")
    if not _admin_web_category_exists(name):
        return False, "Không tìm thấy danh mục."
    mode = _admin_web_form_text(form, "mode")
    if mode not in {"hide", "show"}:
        return False, "Trạng thái danh mục không hợp lệ."
    config = dict(_admin_web_category_config(name))
    config["hidden"] = mode == "hide"
    config.setdefault("sort_order", len(store_categories) + 1)
    config["updated_at"] = int(time.time())
    store_categories[name] = config
    await save_data(force=True, tables=[STORE_CATEGORIES_FILE])
    return True, f"Đã {'ẩn' if mode == 'hide' else 'hiện'} danh mục {name}."


async def _admin_web_action_category_delete(form):
    name = _admin_web_form_text(form, "category_name")
    fallback = "Sản Phẩm Khác"
    if not _admin_web_category_exists(name):
        return False, "Không tìm thấy danh mục."
    if name == fallback:
        return False, "Không thể xóa danh mục mặc định."
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
    return True, f"Đã xóa danh mục {name}; chuyển {moved} sản phẩm sang {fallback}."


def _admin_web_action_registry():
    return {
        "user_balance": _admin_web_action_user_balance,
        "user_ban": _admin_web_action_user_ban,
        "user_profile": _admin_web_action_user_profile,
        "product_create": _admin_web_action_product_create,
        "product_update": _admin_web_action_product_update,
        "product_stock": _admin_web_action_product_stock,
        "product_delete": _admin_web_action_product_delete,
        "api_partner": _admin_web_action_api_partner,
        "order_tools": _admin_web_action_order_tools,
        "coupon": _admin_web_action_coupon,
        "system_toggle": _admin_web_action_system_toggle,
        "pending_manual": _admin_web_action_pending_manual,
        "ops_config_update": _admin_web_action_ops_config_update,
        "support_update": _admin_web_action_support_update,
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
            ok, message = False, "Action không hợp lệ."
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
        message = "Không tìm thấy danh mục."
    elif image is None or not hasattr(image, "read"):
        message = "Chưa chọn file ảnh."
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
            message = "Định dạng không hỗ trợ; chỉ nhận JPG, PNG hoặc WEBP."
        else:
            data = await image.read()
            if not data:
                message = "File ảnh rỗng."
            elif len(data) > ADMIN_WEB_PRODUCT_IMAGE_MAX_BYTES:
                message = "Ảnh quá lớn; tối đa 8 MB."
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
                ok, message = True, f"Đã tải ảnh cho danh mục {category_name}."
    notice_class = "success" if ok else "danger"
    body = f'<div class="notice {notice_class}">{escape(message)}</div>' + _admin_web_categories_body(request)
    return HTMLResponse(_admin_web_layout("Lâm Shop Admin — Danh Mục", body, request))


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
        return HTMLResponse(_admin_web_layout("Lâm Shop Admin Web", body, request))

    product = products.get(product_id)
    if not isinstance(product, dict):
        body = _admin_web_dashboard_body(request, message="Khong tim thay product_id.", is_error=True)
        return HTMLResponse(_admin_web_layout("Lâm Shop Admin Web", body, request))

    apply_category = bool(apply_to_category)
    override_name = category_name_override
    if apply_category:
        category_name = override_name or _admin_web_product_category(product)
    else:
        category_name = ""
    if apply_category and not category_name:
        body = _admin_web_product_detail_body(request, product_id, message="Vui long nhap ten danh muc o o 'Ten danh muc ap dung'.", is_error=True)
        return HTMLResponse(_admin_web_layout("Lâm Shop Admin Web", body, request))

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
        return HTMLResponse(_admin_web_layout("Lâm Shop Admin Web", body, request))

    data = await image.read()
    if not data:
        body = _admin_web_product_detail_body(request, product_id, message="File anh rong.", is_error=True)
        return HTMLResponse(_admin_web_layout("Lâm Shop Admin Web", body, request))
    if len(data) > ADMIN_WEB_PRODUCT_IMAGE_MAX_BYTES:
        body = _admin_web_product_detail_body(request, product_id, message="Anh qua lon (toi da 8MB).", is_error=True)
        return HTMLResponse(_admin_web_layout("Lâm Shop Admin Web", body, request))

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
            return HTMLResponse(_admin_web_layout("Lâm Shop Admin Web", body, request))

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
        return HTMLResponse(_admin_web_layout("Lâm Shop Admin Web", body, request))

    # Per-product upload — copies the same image to each selected product.
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
    return HTMLResponse(_admin_web_layout("Lâm Shop Admin Web", body, request))


def _admin_web_categories_body(request):
    products_data = products if isinstance(products, dict) else {}
    category_data = store_categories if isinstance(store_categories, dict) else {}
    cat_map = {str(name): [] for name in category_data if str(name).strip()}
    for pid, product in products_data.items():
        if isinstance(product, dict):
            name = _admin_web_product_category(product) or "Sản Phẩm Khác"
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
        status = '<span class="tag danger">Ẩn</span>' if hidden else '<span class="tag success">Hiển thị</span>'
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
            preview = '<span style="font-size:20px">📦</span>'
            media_preview = '<span class="category-media-placeholder">📦</span>'
        detail_url = (
            _admin_web_page_url(request, "/admin/item", {"entity": "product", "id": category_products[0][0]})
            if category_products else ""
        )
        detail_link = (
            f'<a class="btn-xs secondary category-action-link" href="{escape(detail_url, quote=True)}">'
            f'{"Mở sản phẩm" if len(category_products) == 1 else "Mở SP đầu tiên"}</a>'
            if detail_url else '<span class="category-empty-label">Chưa có sản phẩm</span>'
        )
        toggle_mode, toggle_label = ("show", "Hiện") if hidden else ("hide", "Ẩn")
        editor_id = f"category-editor-{index}"
        delete_control = (
            '<span class="category-system-note">Danh mục hệ thống, không thể xóa</span>'
            if category_name == "Sản Phẩm Khác"
            else f"""
              <form method="post" action="{escape(action_url, quote=True)}"
                    data-confirm="Xóa danh mục này? Sản phẩm sẽ được chuyển sang Sản Phẩm Khác.">
                <input type="hidden" name="action" value="category_delete">
                <input type="hidden" name="return_page" value="categories">
                <input type="hidden" name="category_name" value="{escape(category_name, quote=True)}">
                <button class="btn-xs danger" type="submit">Xóa danh mục</button>
              </form>"""
        )
        rows.append(f"""
<tr class="data-row category-main-row" data-search="{escape(category_name.casefold(), quote=True)}">
  <td>
    <div class="category-identity">
      <span class="category-icon">{preview}</span>
      <span><b>{escape(category_name)}</b><small>{escape(str(config.get("icon_url") or "Chưa đặt icon web"))}</small></span>
    </div>
  </td>
  <td><span class="category-order">#{escape(str(config.get("sort_order", index)))}</span></td>
  <td><b class="category-number">{total_stock}</b><small>đơn vị tồn</small></td>
  <td><b class="category-number">{len(category_products)}</b><small>sản phẩm</small></td>
  <td>{status}</td>
  <td>
    <div class="category-row-actions">
      <button type="button" class="btn-xs secondary category-edit-toggle"
              data-category-editor="{editor_id}" aria-expanded="false">Sửa</button>
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
          <div><span>Chỉnh sửa danh mục</span><strong>{escape(category_name)}</strong></div>
          <button type="button" class="category-editor-close" data-category-close="{editor_id}" aria-label="Đóng">×</button>
        </div>
        <form method="post" action="{escape(action_url, quote=True)}" class="category-edit-form">
          <input type="hidden" name="action" value="category_update">
          <input type="hidden" name="return_page" value="categories">
          <input type="hidden" name="category_name" value="{escape(category_name, quote=True)}">
          <label>Tên danh mục
            <input name="new_name" value="{escape(category_name, quote=True)}" required>
          </label>
          <label>Thứ tự
            <input type="number" name="sort_order" value="{escape(str(config.get("sort_order", index)), quote=True)}">
          </label>
          <label>Premium Emoji ID
            <input name="emoji_id" value="{escape(str(config.get("emoji_id") or ""), quote=True)}" placeholder="Không bắt buộc">
          </label>
          <label class="category-field-icon">Icon web URL/path
            <input name="icon_url" value="{escape(str(config.get("icon_url") or ""), quote=True)}" placeholder="/static/... hoặc https://...">
          </label>
          <div class="category-save-bar">
            <span>Đổi tên sẽ cập nhật toàn bộ sản phẩm trong danh mục.</span>
            <button type="submit">Lưu thay đổi</button>
          </div>
        </form>
      </div>
      <aside class="category-media-card">
        <div class="category-media-top">{media_preview}<div><b>Ảnh danh mục</b><small>PNG, JPG hoặc WebP</small></div></div>
        <form method="post" action="{escape(upload_url, quote=True)}" enctype="multipart/form-data" class="category-upload-form">
          <input type="hidden" name="category_name" value="{escape(category_name, quote=True)}">
          <input type="file" name="image" accept="image/jpeg,image/png,image/webp" required>
          <button class="btn-xs" type="submit">Tải ảnh mới</button>
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
    <div><span class="category-eyebrow">Quản lý cửa hàng</span><h3>Danh mục sản phẩm</h3>
      <p class="muted">Sắp xếp menu, quản lý hiển thị và hình ảnh đại diện cho từng nhóm sản phẩm.</p>
    </div>
    <div class="category-summary">
      <span><b>{category_count}</b> danh mục</span>
      <span><b>{total_products}</b> sản phẩm</span>
      <span><b>{hidden_count}</b> đang ẩn</span>
    </div>
  </div>
  <details class="category-create-panel">
    <summary><span><b>＋ Thêm danh mục mới</b><small>Tạo một nhóm sản phẩm mới trong menu cửa hàng</small></span><i>⌄</i></summary>
    <form method="post" action="{escape(action_url, quote=True)}" class="category-create-form">
      <input type="hidden" name="action" value="category_create">
      <input type="hidden" name="return_page" value="categories">
      <label>Tên danh mục<input name="category_name" placeholder="Ví dụ: Công cụ AI" required></label>
      <label>Thứ tự<input type="number" name="sort_order" placeholder="Tự động"></label>
      <label>Icon web<input name="icon_url" placeholder="/static/... hoặc URL"></label>
      <label>Premium Emoji ID<input name="emoji_id" placeholder="Không bắt buộc"></label>
      <label class="check-label"><input type="checkbox" name="hidden" value="1"> Tạo ở trạng thái ẩn</label>
      <button type="submit">Thêm danh mục</button>
    </form>
  </details>
  <div class="category-table-head"><div><b>Danh sách danh mục</b><small>Nhấn “Sửa” để mở bảng chỉnh sửa riêng</small></div>
    <span class="category-safe-note">Xóa danh mục không xóa sản phẩm</span>
  </div>
  <div class="table-scroll"><table class="data-table category-table">
    <thead><tr><th>Danh mục</th><th>Thứ tự</th><th>Tổng tồn</th><th>Sản phẩm</th><th>Trạng thái</th><th>Thao tác</th></tr></thead>
    <tbody>{''.join(rows) or '<tr><td colspan="6" class="muted">Chưa có danh mục.</td></tr>'}</tbody>
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
      toggle.textContent = 'Sửa';
    }});
    if (shouldOpen) {{
      target.hidden = false;
      button.setAttribute('aria-expanded', 'true');
      button.textContent = 'Đóng';
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
      toggle.textContent = 'Sửa';
    }}
  }});
}});
</script>"""




@app.get("/admin/categories", tags=["Admin"])
async def admin_web_categories(request: Request):
    _admin_web_require(request)
    await _admin_web_notify_login(request)
    body = _admin_web_categories_body(request)
    return HTMLResponse(_admin_web_layout("Lâm Shop Admin — Danh Mục", body, request))


@app.get("/admin/login", include_in_schema=False)
async def admin_web_login_page(request: Request):
    if _admin_web_authorized(request):
        return RedirectResponse("/admin", status_code=303)
    telegram_error_code = str(request.query_params.get("telegram_error") or "")
    telegram_error_message = {
        "config": "Đăng nhập Telegram chưa được cấu hình đầy đủ.",
        "denied": "Bạn đã hủy hoặc từ chối đăng nhập Telegram.",
        "state": "Phiên xác thực Telegram không hợp lệ hoặc đã hết hạn.",
        "token": "Không thể xác minh phản hồi từ Telegram.",
        "identity": "ID Token Telegram không hợp lệ.",
        "forbidden": "Tài khoản Telegram này không có quyền quản trị.",
    }.get(telegram_error_code, "Đăng nhập Telegram không thành công." if telegram_error_code else "")
    telegram_button = ""
    if _admin_web_telegram_login_enabled():
        telegram_button = """
        <a class="telegram-login-button" href="/admin/login/telegram">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21.6 3.2 18.4 19c-.2 1.1-.9 1.4-1.8.9l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.4-5 9.1-8.2c.4-.4-.1-.6-.6-.2L6 12.8 1.2 11.3c-1-.3-1.1-1 .2-1.5L20 2.6c.9-.3 1.8.2 1.6.6Z"/></svg>
          <span>Đăng nhập bằng Telegram</span>
        </a>
        """
    return HTMLResponse(f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#0b0c0f"><title>Đăng nhập — Lâm Shop Ops</title>
{ADMIN_WEB_FONT_LINKS}
<style>{ADMIN_WEB_UI_CSS}</style></head>
<body class="admin-login-page">
  <main class="login-shell">
    <section class="login-story">
      <a class="login-brand" href="/docs"><span class="admin-brand-mark">L</span><span>Lâm Shop <b>Ops</b></span></a>
      <div class="login-copy">
        <span class="login-eyebrow"><i></i> ADMIN OPERATIONS</span>
        <h1>Mọi hoạt động.<br><em>Một trung tâm.</em></h1>
        <p>Theo dõi doanh thu, đơn hàng, tồn kho, sản phẩm manual và API partner trong thời gian thực.</p>
        <div class="login-signals">
          <div><span>01</span><b>Commerce</b><small>Đơn hàng & doanh thu</small></div>
          <div><span>02</span><b>Inventory</b><small>Kho & sản phẩm manual</small></div>
          <div><span>03</span><b>Partners</b><small>API & vận hành ví</small></div>
        </div>
      </div>
      <footer><i></i> Lâm Shop secured workspace</footer>
    </section>
    <section class="login-panel">
      <div class="login-card">
        <div class="login-card-head"><span class="login-lock"><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="4.5" y="10.5" width="15" height="10" rx="2.5"/><path d="M8 10.5V7.8a4 4 0 0 1 8 0v2.7"/></svg></span><div><h2>Chào mừng trở lại</h2><p>Đăng nhập để tiếp tục vào Control Center.</p></div></div>
        {f'<div class="login-error"><b>Không thể đăng nhập Telegram</b><span>{telegram_error_message}</span></div>' if telegram_error_message else ''}
        {telegram_button}
        <div class="login-security"><i></i><span>Phiên đăng nhập được bảo vệ và tự động hết hạn.</span></div>
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
    return HTMLResponse(_admin_web_layout("Lâm Shop Admin Web", _admin_web_dashboard_body(request), request))


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
    return HTMLResponse(_admin_web_layout("Lâm Shop Admin Web", body, request))


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
        headers={"Content-Disposition": 'attachment; filename="lamshop-api-partners.csv"', "Cache-Control": "no-store"},
    )


@app.get("/admin/item", tags=["Admin"])
async def admin_web_item(request: Request):
    _admin_web_require(request)
    await _admin_web_notify_login(request)
    entity = str(request.query_params.get("entity") or "").strip()
    item_id = str(request.query_params.get("id") or "").strip()
    body = _admin_web_detail_body(request, entity, item_id)
    return HTMLResponse(_admin_web_layout("Lâm Shop Admin Detail", body, request))


@app.get("/admin/commands", tags=["Admin"])
async def admin_web_commands(request: Request):
    _admin_web_require(request)
    await _admin_web_notify_login(request)
    return HTMLResponse(_admin_web_layout("Lâm Shop Admin Commands", _admin_web_commands_body(), request))


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

