"""Phiên đăng nhập, CSRF, same-origin và đăng nhập Telegram OIDC.

Giữ nguyên định dạng token và cookie của web cũ nên phiên đang mở không bị đá ra
khi triển khai bản mới.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Any
from urllib.parse import urlsplit

from .repo import sessions
from .settings import get_settings

logger = logging.getLogger(__name__)

TELEGRAM_AUTH_URL = "https://oauth.telegram.org/auth"
TELEGRAM_TOKEN_URL = "https://oauth.telegram.org/token"
TELEGRAM_JWKS_URL = "https://oauth.telegram.org/.well-known/jwks.json"
TELEGRAM_ISSUER = "https://oauth.telegram.org"
OIDC_COOKIE = "lamshop_admin_telegram_oidc"
OIDC_COOKIE_PATH = "/admin/login/telegram"


# --- helper mã hóa ----------------------------------------------------------

def b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def b64url_decode(value: str) -> bytes:
    text = str(value or "")
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str) -> str:
    secret = get_settings().session_secret.encode()
    return hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()


# --- phiên đăng nhập --------------------------------------------------------

def new_session_token() -> tuple[str, int]:
    """Trả (token, expires_at). Token = expires.nonce.signature."""
    settings = get_settings()
    expires_at = int(time.time()) + settings.session_hours * 3600
    payload = f"{expires_at}.{secrets.token_hex(16)}"
    return f"{payload}.{_sign(payload)}", expires_at


def session_token_valid(token: str) -> bool:
    """Chữ ký đúng và chưa hết hạn. Chưa kiểm tra token có trong DB."""
    try:
        expires_at, nonce, signature = str(token or "").split(".", 2)
    except ValueError:
        return False
    try:
        if int(expires_at) < int(time.time()) or len(nonce) != 32:
            return False
    except ValueError:
        return False
    return hmac.compare_digest(signature, _sign(f"{expires_at}.{nonce}"))


def session_active(token: str) -> bool:
    """Hợp lệ về chữ ký VÀ còn tồn tại trong bảng admin_sessions."""
    return session_token_valid(token) and sessions.exists(token)


def csrf_token_for(session: str) -> str:
    if not session_token_valid(session):
        return ""
    return _sign(f"csrf.{session}")


def csrf_valid(session: str, supplied: str) -> bool:
    expected = csrf_token_for(session)
    if not expected or not supplied:
        return False
    return hmac.compare_digest(str(supplied), expected)


def origin_allowed(origin: str, base_url: str) -> bool:
    """So host của Origin với host của app và PUBLIC_API_URL.

    Chỉ so host chứ không so scheme: sau proxy TLS trình duyệt gửi https trong
    khi app vẫn thấy http, lệch scheme ở đây là chuyện triển khai chứ không phải
    request xuyên site.
    """
    if not origin:
        return True
    allowed = {urlsplit(str(base_url)).netloc.casefold()}
    public_url = get_settings().public_api_url
    if public_url:
        allowed.add(urlsplit(public_url).netloc.casefold())
    allowed.discard("")
    return urlsplit(origin).netloc.casefold() in allowed


# --- Telegram OIDC ----------------------------------------------------------

def oidc_cookie_encode(payload: dict) -> str:
    encoded = b64url_encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    )
    return f"{encoded}.{_sign(f'telegram_oidc.{encoded}')}"


def oidc_cookie_decode(value: str) -> dict:
    try:
        encoded, signature = str(value or "").split(".", 1)
    except ValueError:
        return {}
    if not hmac.compare_digest(signature, _sign(f"telegram_oidc.{encoded}")):
        return {}
    try:
        payload = json.loads(b64url_decode(encoded).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    issued_at = int(payload.get("issued_at") or 0)
    ttl = get_settings().oidc_ttl_seconds
    if issued_at <= 0 or abs(int(time.time()) - issued_at) > ttl:
        return {}
    return payload


def build_authorization_url(state: str, nonce: str, verifier: str, redirect_uri: str) -> str:
    from urllib.parse import urlencode

    challenge = b64url_encode(hashlib.sha256(verifier.encode("ascii")).digest())
    params = {
        "client_id": get_settings().telegram_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{TELEGRAM_AUTH_URL}?{urlencode(params)}"


# alg -> (kty, crv) của khóa JWKS phải khớp. Telegram công bố cả 4 alg trong
# openid-configuration và có thể ký ID Token bằng bất kỳ alg nào.
_JWS_ALGS = {
    "RS256": ("RSA", None),
    "ES256": ("EC", "P-256"),
    "ES256K": ("EC", "secp256k1"),
    "EdDSA": ("OKP", "Ed25519"),
}


def _verify_jws_signature(alg: str, key: dict, signature: bytes, data: bytes) -> None:
    """Raise InvalidSignature/ValueError nếu chữ ký sai."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

    def as_int(name: str) -> int:
        return int.from_bytes(b64url_decode(key[name]), "big")

    if alg == "RS256":
        rsa.RSAPublicNumbers(as_int("e"), as_int("n")).public_key().verify(
            signature, data, padding.PKCS1v15(), hashes.SHA256()
        )
    elif alg in ("ES256", "ES256K"):
        # JWS dùng r||s thô 64 byte, cryptography cần DER.
        if len(signature) != 64:
            raise ValueError("bad EC signature length")
        curve = ec.SECP256R1() if alg == "ES256" else ec.SECP256K1()
        ec.EllipticCurvePublicNumbers(as_int("x"), as_int("y"), curve).public_key().verify(
            encode_dss_signature(
                int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
            ),
            data,
            ec.ECDSA(hashes.SHA256()),
        )
    elif alg == "EdDSA":
        ed25519.Ed25519PublicKey.from_public_bytes(b64url_decode(key["x"])).verify(signature, data)
    else:
        raise ValueError(f"unsupported alg {alg}")


def verify_id_token(id_token: str, jwks: dict, expected_nonce: str) -> dict:
    """Xác minh chữ ký (RS256/ES256/ES256K/EdDSA) và các claim bắt buộc. Trả {} nếu không hợp lệ."""
    from cryptography.exceptions import InvalidSignature

    def reject(reason: str) -> dict:
        logger.warning("Telegram ID Token bị từ chối: %s", reason)
        return {}

    settings = get_settings()
    try:
        header_part, payload_part, signature_part = str(id_token or "").split(".", 2)
        header = json.loads(b64url_decode(header_part).decode("utf-8"))
        claims = json.loads(b64url_decode(payload_part).decode("utf-8"))
        alg = str(header.get("alg") or "")
        if alg not in _JWS_ALGS:
            return reject(f"alg={alg!r}")
        kty, crv = _JWS_ALGS[alg]
        kid = str(header.get("kid") or "")
        key = next(
            (
                item
                for item in (jwks.get("keys") or [])
                if isinstance(item, dict)
                and item.get("kty") == kty
                and (crv is None or item.get("crv") == crv)
                and str(item.get("kid") or "") == kid
            ),
            None,
        )
        if not key:
            return reject(f"không có khóa JWKS cho kid={kid!r} alg={alg}")
        try:
            _verify_jws_signature(
                alg, key, b64url_decode(signature_part), f"{header_part}.{payload_part}".encode("ascii")
            )
        except (InvalidSignature, ValueError):
            return reject(f"chữ ký sai (alg={alg})")

        now = int(time.time())
        audience = claims.get("aud")
        client_id = str(settings.telegram_client_id)
        if isinstance(audience, list):
            audience_ok = client_id in {str(item) for item in audience}
        else:
            audience_ok = hmac.compare_digest(str(audience), client_id)
        if claims.get("iss") != TELEGRAM_ISSUER:
            return reject(f"iss={claims.get('iss')!r}")
        if not audience_ok:
            return reject(f"aud={audience!r}")
        if int(claims.get("exp") or 0) < now - 30:
            return reject(f"hết hạn exp={claims.get('exp')} now={now}")
        if int(claims.get("iat") or 0) > now + 60:
            return reject(f"iat tương lai iat={claims.get('iat')} now={now}")
        token_nonce = claims.get("nonce")
        if token_nonce is not None and (
            not expected_nonce
            or not hmac.compare_digest(str(token_nonce), str(expected_nonce))
        ):
            return reject("nonce không khớp")
        return claims
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return reject(f"token lỗi định dạng: {type(exc).__name__}")


def claims_are_admin(claims: dict[str, Any]) -> bool:
    telegram_id = str(claims.get("id") or claims.get("sub") or "").strip()
    admin_id = get_settings().admin_user_id
    if not telegram_id or not admin_id:
        return False
    return hmac.compare_digest(telegram_id, str(admin_id))
