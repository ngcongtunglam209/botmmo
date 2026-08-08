"""Khai báo mọi collection kv_store mà web dùng.

Một chỗ duy nhất ánh xạ tên nghiệp vụ sang key kv_store, thay cho hàng chục hằng
`*_FILE` rải khắp config_env.
"""

from __future__ import annotations

from .base import DictCollection, ListCollection

products = DictCollection("data_products.json")
store_categories = DictCollection("data_store_categories.json")
custom_store_icons = DictCollection("data_custom_store_icons.json")

order_history = ListCollection("data_order_history.json")
pending_orders = DictCollection("data_pending_orders.json")
pending_manual_orders = DictCollection("data_pending_manual_orders.json")
pending_user_topups = DictCollection("data_pending_user_topups.json")

users = DictCollection("data_users.json")
banned_users = ListCollection("data_banned_users.json")
transaction_history = DictCollection("data_transaction_history.json")
referral_data = DictCollection("data_referral_data.json")

api_keys = DictCollection("data_api_keys.json")

coupons = DictCollection("data_coupons.json")
flash_sales = DictCollection("data_flash_sales.json")
combo_deals = DictCollection("data_combo_deals.json")
giveaways = DictCollection("data_giveaways.json")
promo_budget = DictCollection("data_promo_budget.json")

live_chats = DictCollection("data_live_chats.json")
warranty_claims = DictCollection("data_warranty_claims.json")
withdrawals = DictCollection("data_withdrawals.json")
product_ratings = DictCollection("data_product_ratings.json")

admin_action_log = ListCollection("data_admin_action_log.json")
