"""Cấu hình cho web admin mới.

Đọc thẳng từ biến môi trường, không phụ thuộc app.core.config_env hay
runtime_loader. Một chỗ duy nhất để biết web cần env nào.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = Path(__file__).resolve().parent


def _env(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or "").strip()


def _env_int(name: str, default: int, minimum: int | None = None) -> int:
    try:
        value = int(_env(name, str(default)) or default)
    except ValueError:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    return value


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Snapshot cấu hình lúc khởi động."""

    db_path: str
    session_secret: str
    session_hours: int
    session_cookie: str
    admin_user_id: str

    telegram_client_id: str
    telegram_client_secret: str
    telegram_redirect_uri: str
    telegram_bot_token: str

    public_api_url: str
    public_api_scheme: str

    upload_dir: Path
    product_image_dir: Path
    category_image_dir: Path
    asset_dir: Path

    notify_admin: bool
    log_file: Path

    product_table_limit: int = 3000
    order_table_limit: int = 260
    user_table_limit: int = 260
    api_table_limit: int = 260
    audit_limit: int = 500

    login_window_seconds: int = 5 * 60
    login_max_attempts: int = 5
    oidc_ttl_seconds: int = 10 * 60

    image_max_bytes: int = 8 * 1024 * 1024
    image_extensions: frozenset[str] = field(
        default_factory=lambda: frozenset({"jpg", "jpeg", "png", "webp"})
    )

    @property
    def telegram_login_enabled(self) -> bool:
        return bool(
            self.telegram_client_id and self.telegram_client_secret and self.admin_user_id
        )

    @property
    def cookie_secure(self) -> bool:
        return self.public_api_scheme == "https"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    upload_dir = PROJECT_ROOT / "app" / "api" / "static"
    public_api_url = _env("PUBLIC_API_URL")
    scheme = "https" if public_api_url.startswith("https://") else "http"

    telegram_token = _env("TELEGRAM_TOKEN")
    client_id = _env("TELEGRAM_LOGIN_CLIENT_ID") or telegram_token.split(":", 1)[0]

    session_secret = _env("ADMIN_WEB_SESSION_SECRET")
    if not session_secret:
        # Cùng fallback với web cũ: dùng bot token nên session vẫn ổn định
        # qua các lần restart, thay vì random mỗi lần khởi động.
        session_secret = telegram_token or "lamshop-admin-web-dev-secret"

    settings = Settings(
        db_path=_env("DB_PATH", str(PROJECT_ROOT / "database.sqlite")),
        session_secret=session_secret,
        session_hours=_env_int("ADMIN_WEB_SESSION_HOURS", 8, minimum=1),
        session_cookie="lamshop_admin_session",
        admin_user_id=_env("ADMIN_USER_ID"),
        telegram_client_id=client_id,
        telegram_client_secret=_env("TELEGRAM_LOGIN_CLIENT_SECRET"),
        telegram_redirect_uri=_env("TELEGRAM_LOGIN_REDIRECT_URI"),
        telegram_bot_token=telegram_token,
        public_api_url=public_api_url,
        public_api_scheme=scheme,
        upload_dir=upload_dir,
        product_image_dir=upload_dir / "products",
        category_image_dir=upload_dir / "categories",
        asset_dir=PROJECT_ROOT / "app" / "api" / "assets",
        notify_admin=_env_bool("ADMIN_WEB_NOTIFY", True),
        log_file=Path(_env("LOG_FILE") or PROJECT_ROOT / "bot.log"),
    )
    settings.product_image_dir.mkdir(parents=True, exist_ok=True)
    settings.category_image_dir.mkdir(parents=True, exist_ok=True)
    return settings
