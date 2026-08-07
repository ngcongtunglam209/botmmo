"""
Centralized application state container.

Replaces the 30+ global mutable variables scattered across runtime_state.py
and config_env.py with a single, well-typed, thread-safe state object.

Usage (after migration):
    from app.state import app_state
    app_state.order_history.append(new_order)
    user = app_state.user_data_db.get(str(user_id))

During the transition period, the exec()-based runtime_loader still populates
globals into the shared namespace. `bridge_from_globals()` syncs those into
this AppState so new code can use either approach.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppState:
    """Single source of truth for all mutable application state.

    Every field here was previously a bare global variable in runtime_state.py.
    Grouping them in one object makes dependencies explicit and enables testing
    (inject a fresh AppState per test instead of monkey-patching 30 globals).
    """

    # ── Core data stores ──────────────────────────────────────────────
    pending_orders: dict = field(default_factory=dict)
    pending_user_topups: dict = field(default_factory=dict)
    processed_transaction_ids: set = field(default_factory=set)
    order_history: list = field(default_factory=list)
    user_data_db: dict = field(default_factory=dict)
    banned_users: set = field(default_factory=set)
    coupons: dict = field(default_factory=dict)
    api_keys: dict = field(default_factory=dict)
    pending_api_deposits: dict = field(default_factory=dict)
    products: dict = field(default_factory=dict)
    pending_manual_orders: dict = field(default_factory=dict)
    custom_store_icons: dict = field(default_factory=dict)
    store_categories: dict = field(default_factory=dict)

    # ── Order indexes (O(1) lookup) ───────────────────────────────────
    order_index: dict = field(default_factory=dict)
    user_order_index: dict = field(default_factory=dict)
    api_partner_ref_index: dict = field(default_factory=dict)

    # ── Advanced features ─────────────────────────────────────────────
    warranty_claims: dict = field(default_factory=dict)
    product_ratings: dict = field(default_factory=dict)
    referral_data: dict = field(default_factory=dict)
    live_chats: dict = field(default_factory=dict)
    active_giveaways: dict = field(default_factory=dict)
    dice_game_data: dict = field(default_factory=dict)
    withdrawal_requests: dict = field(default_factory=dict)
    transaction_history: dict = field(default_factory=dict)
    admin_action_log: list = field(default_factory=list)
    daily_promo_tracker: dict = field(default_factory=dict)

    # ── Commerce features ─────────────────────────────────────────────
    stock_waitlist: dict = field(default_factory=dict)
    flash_sales: dict = field(default_factory=dict)
    combo_deals: dict = field(default_factory=dict)
    wheel_data: dict = field(default_factory=dict)

    # ── Runtime state (NOT persisted to DB) ───────────────────────────
    bot_instance: Any = None
    http_client: Any = None
    pending_api_registrations: set = field(default_factory=set)
    notified_out_of_stock: set = field(default_factory=set)
    pending_error_reports: list = field(default_factory=list)
    background_tasks: set = field(default_factory=set)
    reserved_order_codes: set = field(default_factory=set)

    # ── Concurrency locks ─────────────────────────────────────────────
    file_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    pending_orders_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    global_stock_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    api_key_locks_guard: asyncio.Lock = field(default_factory=asyncio.Lock)
    refund_locks_guard: asyncio.Lock = field(default_factory=asyncio.Lock)
    product_stock_locks: dict = field(default_factory=dict)
    api_key_locks: dict = field(default_factory=dict)
    refund_locks: dict = field(default_factory=dict)

    # ── Runtime flags ─────────────────────────────────────────────────
    maintenance_mode: bool = False
    ai_auto_reply: bool = True

    # ── Config (read-only after boot) ─────────────────────────────────
    public_api_url: str = ""
    bot_start_time: float = field(default_factory=time.time)

    # ── Data file name constants ──────────────────────────────────────
    # (These map to KV store keys in SQLite)
    DB_PATH: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "database.sqlite"
    ))

    # ── Bridge methods ────────────────────────────────────────────────

    # Names of data fields that are persisted to the SQLite KV store
    PERSISTED_FIELDS: tuple = (
        "pending_orders", "pending_user_topups", "processed_transaction_ids",
        "order_history", "user_data_db", "banned_users", "coupons",
        "api_keys", "pending_api_deposits", "products", "custom_store_icons",
        "store_categories",
        "pending_manual_orders", "warranty_claims", "product_ratings",
        "referral_data", "live_chats", "active_giveaways", "dice_game_data",
        "withdrawal_requests", "transaction_history", "admin_action_log",
        "daily_promo_tracker", "stock_waitlist", "flash_sales", "combo_deals",
        "wheel_data",
    )

    # Names of runtime state fields (not persisted)
    RUNTIME_FIELDS: tuple = (
        "order_index", "user_order_index", "api_partner_ref_index",
        "bot_instance", "http_client", "pending_api_registrations",
        "notified_out_of_stock", "pending_error_reports", "background_tasks",
        "reserved_order_codes",
    )

    def bridge_from_globals(self, namespace: dict[str, Any]) -> None:
        """Pull current values from the exec() shared namespace into this state.

        Call this after `load_data()` / `sync_runtime_bindings()` to keep
        AppState in sync with legacy globals during the migration period.
        """
        all_fields = self.PERSISTED_FIELDS + self.RUNTIME_FIELDS
        for name in all_fields:
            if name in namespace:
                setattr(self, name, namespace[name])

        # Also grab flags
        for flag in ("maintenance_mode", "ai_auto_reply", "public_api_url", "bot_instance"):
            upper = flag.upper()
            if upper in namespace:
                setattr(self, flag, namespace[upper])
            elif flag in namespace:
                setattr(self, flag, namespace[flag])

    def export_to_globals(self, namespace: dict[str, Any]) -> None:
        """Push state back to the exec() shared namespace.

        Use sparingly — only during save_data() or when legacy code needs
        the updated values.
        """
        all_fields = self.PERSISTED_FIELDS + self.RUNTIME_FIELDS
        for name in all_fields:
            namespace[name] = getattr(self, name)


# Module-level singleton — import and use directly
app_state = AppState()
