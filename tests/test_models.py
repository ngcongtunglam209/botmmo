"""Tests for Pydantic data models."""

from __future__ import annotations

import time

import pytest
from pydantic import ValidationError

from app.models.order import Order, OrderStatus, PendingOrder
from app.models.payment import (
    PaymentMethod,
    WheelPrize,
    WithdrawalRequest,
    WithdrawalStatus,
)
from app.models.product import FlashSale, Product
from app.models.user import TransactionRecord, UserProfile, VIPRank

# ============================================================
#  Order Model Tests
# ============================================================

class TestOrder:
    def test_create_from_dict(self, sample_order_data):
        order = Order.from_dict(sample_order_data)
        assert order.order_code == "ICLD123456"
        assert order.user_id == 1000000001
        assert order.amount == 35000
        assert order.product_name == "ChatGPT Plus 1 Tháng"
        assert order.quantity == 1

    def test_roundtrip_to_legacy(self, sample_order_data):
        order = Order.from_dict(sample_order_data)
        legacy = order.to_legacy_dict()
        assert legacy["order_code"] == "ICLD123456"
        assert legacy["amount"] == 35000
        assert isinstance(legacy, dict)

    def test_defaults(self):
        order = Order(order_code="TEST001", user_id=123, amount=10000)
        assert order.quantity == 1
        assert order.balance_used == 0
        assert order.items == []
        assert order.payment_method == "bank_transfer"
        assert order.type == "store_product"

    def test_extra_fields_allowed(self, sample_order_data):
        sample_order_data["some_future_field"] = "hello"
        order = Order.from_dict(sample_order_data)
        assert order.order_code == "ICLD123456"

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            Order(order_code="TEST", user_id=1, amount=-100)


class TestOrderStatus:
    def test_from_legacy_vietnamese(self):
        assert OrderStatus.from_legacy("Hoàn thành") == OrderStatus.COMPLETED

    def test_from_legacy_with_emoji(self):
        raw = '<tg-emoji emoji-id="5462956611033117422">♻️</tg-emoji> Đã hoàn tiền (Ví Bot)'
        assert OrderStatus.from_legacy(raw) == OrderStatus.REFUNDED

    def test_from_legacy_english(self):
        assert OrderStatus.from_legacy("completed") == OrderStatus.COMPLETED

    def test_from_legacy_unknown(self):
        assert OrderStatus.from_legacy("some_random_status") == OrderStatus.PROCESSING


class TestPendingOrder:
    def test_create_from_dict(self, sample_pending_order_data):
        pending = PendingOrder.from_dict(sample_pending_order_data)
        assert pending.user_id == 1000000001
        assert pending.amount == 35000
        assert pending.status == "pending_payment"

    def test_defaults(self):
        pending = PendingOrder(user_id=123, amount=50000)
        assert pending.quantity == 1
        assert pending.payment_method == "bank_transfer"
        assert pending.balance_used == 0


# ============================================================
#  User Model Tests
# ============================================================

class TestUserProfile:
    def test_create_from_dict(self, sample_user_data):
        user = UserProfile.from_dict(1000000001, sample_user_data)
        assert user.user_id == 1000000001
        assert user.full_name == "Test User"
        assert user.balance == 100000
        assert user.total_spent == 500000

    def test_vip_rank_bronze(self):
        user = UserProfile(user_id=1, total_spent=0)
        rank = user.get_vip_rank()
        assert "Đồng" in rank.name
        assert rank.discount == 0

    def test_vip_rank_silver(self):
        user = UserProfile(user_id=1, total_spent=500000)
        rank = user.get_vip_rank()
        assert "Bạc" in rank.name
        assert rank.discount == 2

    def test_vip_rank_gold(self):
        user = UserProfile(user_id=1, total_spent=1_000_000)
        rank = user.get_vip_rank()
        assert "Vàng" in rank.name
        assert rank.discount == 5

    def test_vip_rank_diamond(self):
        user = UserProfile(user_id=1, total_spent=5_000_000)
        rank = user.get_vip_rank()
        assert "Kim Cương" in rank.name
        assert rank.discount == 8

    def test_vip_rank_master(self):
        user = UserProfile(user_id=1, total_spent=10_000_000)
        rank = user.get_vip_rank()
        assert "Cao Thủ" in rank.name
        assert rank.discount == 8

    def test_discount_percent(self):
        user = UserProfile(user_id=1, total_spent=2_000_000)
        assert user.get_discount_percent() == 5  # Gold level


class TestVIPRank:
    def test_default_ranks(self):
        ranks = VIPRank.default_ranks()
        assert len(ranks) == 5
        assert ranks[0].min_spend == 0
        assert ranks[-1].min_spend == 10_000_000


class TestTransactionRecord:
    def test_create(self):
        record = TransactionRecord(amount=50000, new_balance=150000, reason="Purchase refund")
        assert record.amount == 50000
        assert record.new_balance == 150000
        assert record.reason == "Purchase refund"
        assert record.timestamp > 0


# ============================================================
#  Product Model Tests
# ============================================================

class TestProduct:
    def test_create_from_dict(self, sample_product_data):
        product = Product.from_dict("prod_001", sample_product_data)
        assert product.product_id == "prod_001"
        assert product.name == "ChatGPT Plus 1 Tháng"
        assert product.price == 35000
        assert product.available_stock_count() == 3

    def test_in_stock(self, sample_product_data):
        product = Product.from_dict("prod_001", sample_product_data)
        assert product.is_in_stock(quantity=3) is True
        assert product.is_in_stock(quantity=4) is False

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            Product(name="Bad", price=-100)


class TestFlashSale:
    def test_active(self):
        sale = FlashSale(
            product_id="p1",
            discount_percent=20,
            start_time=time.time() - 60,
            end_time=time.time() + 3600,
        )
        assert sale.is_active() is True
        assert sale.is_sold_out() is False

    def test_expired(self):
        sale = FlashSale(
            product_id="p1",
            discount_percent=20,
            start_time=time.time() - 7200,
            end_time=time.time() - 3600,
        )
        assert sale.is_active() is False

    def test_sold_out(self):
        sale = FlashSale(
            product_id="p1",
            discount_percent=20,
            start_time=time.time() - 60,
            end_time=time.time() + 3600,
            max_quantity=10,
            sold_count=10,
        )
        assert sale.is_sold_out() is True


# ============================================================
#  Payment Model Tests
# ============================================================

class TestPaymentMethod:
    def test_enum_values(self):
        assert PaymentMethod.BANK_TRANSFER == "bank_transfer"
        assert PaymentMethod.USDT_RPAY == "usdt_rpay"
        assert PaymentMethod.BALANCE == "balance"


class TestWithdrawalRequest:
    def test_create(self):
        req = WithdrawalRequest(
            request_id="WD001",
            user_id=123,
            amount=200000,
            bank_name="Vietcombank",
            account_number="1234567890",
            account_holder="NGUYEN VAN A",
        )
        assert req.status == WithdrawalStatus.PENDING
        assert req.amount == 200000

    def test_from_dict(self):
        data = {
            "request_id": "WD002",
            "user_id": 456,
            "amount": 500000,
            "status": "pending",
            "bank_name": "MB",
        }
        req = WithdrawalRequest.from_dict(data)
        assert req.user_id == 456


class TestWheelPrize:
    def test_default_prizes(self):
        prizes = WheelPrize.default_prizes()
        assert len(prizes) == 8
        total_weight = sum(p.weight for p in prizes)
        assert total_weight == 1000  # Weights should sum to ~1000

    def test_prize_types(self):
        prizes = WheelPrize.default_prizes()
        types = {p.type for p in prizes}
        assert types == {"balance", "coupon", "nothing"}

