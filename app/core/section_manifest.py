from __future__ import annotations

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_ROOT.parent

SECTION_FILES = [
    APP_ROOT / "core" / "boot_dependencies.py",
    APP_ROOT / "core" / "emoji_runtime.py",
    APP_ROOT / "core" / "config_env.py",
    APP_ROOT / "core" / "runtime_state.py",
    APP_ROOT / "integrations" / "payments_core.py",
    APP_ROOT / "integrations" / "sepay_api.py",
    APP_ROOT / "database" / "storage.py",
    APP_ROOT / "utils" / "telegram_io.py",
    APP_ROOT / "services" / "orders_delivery.py",
    APP_ROOT / "services" / "referrals_stats.py",
    APP_ROOT / "jobs" / "support_and_warranty.py",
    APP_ROOT / "services" / "games_withdrawals_db.py",
    APP_ROOT / "integrations" / "ai_core.py",
    APP_ROOT / "services" / "support_automation.py",
    APP_ROOT / "handlers" / "product_catalog.py",
    APP_ROOT / "handlers" / "stock_management.py",
    APP_ROOT / "handlers" / "giveaway.py",
    APP_ROOT / "services" / "store_menu.py",
    APP_ROOT / "services" / "local_stock_guard.py",
    APP_ROOT / "handlers" / "store_callback.py",
    APP_ROOT / "utils" / "i18n.py",
    APP_ROOT / "utils" / "ui_and_email.py",
    APP_ROOT / "handlers" / "payment_generation.py",
    APP_ROOT / "handlers" / "user_topup.py",
    APP_ROOT / "services" / "notifications_async.py",
    APP_ROOT / "jobs" / "payment_monitor.py",
    APP_ROOT / "jobs" / "backup_and_rewards.py",
    APP_ROOT / "handlers" / "games_waitlist.py",
    APP_ROOT / "handlers" / "flashsale_wheel.py",
    APP_ROOT / "handlers" / "user_entry.py",
    APP_ROOT / "handlers" / "priority_and_text.py",
    APP_ROOT / "handlers" / "media_and_referrals.py",
    APP_ROOT / "handlers" / "callback_games.py",
    APP_ROOT / "services" / "admin_refund.py",
    APP_ROOT / "services" / "admin_orders.py",
    APP_ROOT / "services" / "admin_support.py",
    APP_ROOT / "services" / "admin_withdrawals.py",
    APP_ROOT / "handlers" / "callback_admin.py",
    APP_ROOT / "handlers" / "callback_router.py",
    APP_ROOT / "handlers" / "public_commands.py",
    APP_ROOT / "handlers" / "admin_catalog_commands.py",
    APP_ROOT / "handlers" / "admin_user_commands.py",
    APP_ROOT / "handlers" / "admin_sales.py",
    APP_ROOT / "handlers" / "admin_orders.py",
    APP_ROOT / "handlers" / "admin_ops.py",
    APP_ROOT / "handlers" / "admin_menu.py",
    APP_ROOT / "handlers" / "admin_api.py",
    APP_ROOT / "models" / "api_models.py",
    APP_ROOT / "api" / "helpers.py",
    APP_ROOT / "api" / "order_pipeline.py",
    APP_ROOT / "api" / "public_url.py",
    # Toan bo tang HTTP (admin web + partner API + docs) nam o package app/web.
    APP_ROOT / "api" / "web_mount.py",
    APP_ROOT / "api" / "server.py",
    APP_ROOT / "core" / "lifecycle.py",
    APP_ROOT / "jobs" / "admin_background.py",
    APP_ROOT / "legacy_entry.py",
]

def _module_name_from_path(path: Path) -> str:
    relative = path.resolve().relative_to(PROJECT_ROOT)
    return ".".join(relative.with_suffix("").parts)

SECTION_MODULES = [_module_name_from_path(path) for path in SECTION_FILES]

