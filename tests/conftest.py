"""Shared test fixtures and configuration for the Dino Bot test suite."""

from __future__ import annotations

import os
import sys
import time

import pytest

# Ensure app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_order_data() -> dict:
    """A minimal completed order dict matching legacy format."""
    return {
        "order_code": "ICLD123456",
        "user_id": 1000000001,
        "amount": 35000,
        "status": "Hoàn thành",
        "timestamp": time.time() - 3600,
        "product_id": "prod_001",
        "product_name": "ChatGPT Plus 1 Tháng",
        "product_duration": "1 tháng",
        "quantity": 1,
        "items": ["https://example.com/link1"],
        "email": "test@example.com",
        "delivery_method": "stock_items",
        "payment_method": "bank_transfer",
        "full_name": "Test User",
        "username": "testuser",
        "type": "store_product",
        "completed_at": time.time(),
    }


@pytest.fixture
def sample_pending_order_data() -> dict:
    """A pending order waiting for payment."""
    return {
        "user_id": 1000000001,
        "amount": 35000,
        "time": time.time(),
        "status": "pending_payment",
        "product_id": "prod_001",
        "product_name": "ChatGPT Plus 1 Tháng",
        "quantity": 1,
        "transfer_content": "ICLD123456",
        "payment_method": "bank_transfer",
        "full_name": "Test User",
    }


@pytest.fixture
def sample_user_data() -> dict:
    """A user profile dict in legacy format."""
    return {
        "full_name": "Test User",
        "username": "testuser",
        "balance": 100000,
        "total_spent": 500000,
        "order_count": 15,
        "first_seen": time.time() - 86400 * 30,
        "last_seen": time.time(),
        "is_premium": False,
    }


@pytest.fixture
def sample_product_data() -> dict:
    """A product dict in legacy format."""
    return {
        "name": "ChatGPT Plus 1 Tháng",
        "price": 35000,
        "description": "Tài khoản ChatGPT Plus thời hạn 1 tháng",
        "duration": "1 tháng",
        "stock": ["link1", "link2", "link3"],
        "requires_gmail": False,
        "auto_delivery": True,
        "warranty_days": 30,
    }
