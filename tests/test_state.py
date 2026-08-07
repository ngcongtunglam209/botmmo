"""Tests for the centralized AppState container."""

from __future__ import annotations

import asyncio

import pytest

from app.state import AppState, app_state


class TestAppState:
    def test_singleton_exists(self):
        """Module-level app_state should be an AppState instance."""
        assert isinstance(app_state, AppState)

    def test_fresh_state_has_empty_collections(self):
        state = AppState()
        assert state.order_history == []
        assert state.user_data_db == {}
        assert state.products == {}
        assert state.available_links == set()
        assert state.banned_users == set()
        assert state.pending_orders == {}
        assert state.api_keys == {}

    def test_fresh_state_has_locks(self):
        state = AppState()
        assert isinstance(state.file_lock, asyncio.Lock)
        assert isinstance(state.pending_orders_lock, asyncio.Lock)
        assert isinstance(state.global_stock_lock, asyncio.Lock)

    def test_bridge_from_globals(self):
        state = AppState()
        namespace = {
            "order_history": [{"code": "ICLD001"}],
            "user_data_db": {"123": {"balance": 50000}},
            "products": {"p1": {"name": "Test"}},
            "available_links": {"link1", "link2"},
            "MAINTENANCE_MODE": True,
            "bot_instance": "fake_bot",
        }
        state.bridge_from_globals(namespace)

        assert len(state.order_history) == 1
        assert state.order_history[0]["code"] == "ICLD001"
        assert state.user_data_db["123"]["balance"] == 50000
        assert state.available_links == {"link1", "link2"}
        assert state.maintenance_mode is True
        assert state.bot_instance == "fake_bot"

    def test_export_to_globals(self):
        state = AppState()
        state.order_history = [{"code": "ICLD002"}]
        state.products = {"p1": {"name": "Export Test"}}
        state.available_links = {"exported_link"}

        namespace = {}
        state.export_to_globals(namespace)

        assert namespace["order_history"] == [{"code": "ICLD002"}]
        assert namespace["products"]["p1"]["name"] == "Export Test"
        assert "exported_link" in namespace["available_links"]

    def test_bridge_roundtrip(self):
        """Data should survive bridge_from → export_to cycle."""
        original = {
            "order_history": [{"x": 1}, {"x": 2}],
            "user_data_db": {"456": {"name": "Alice"}},
            "banned_users": {"bad_user"},
            "coupons": {"SALE20": {"discount": 20}},
        }

        state = AppState()
        state.bridge_from_globals(original)

        exported = {}
        state.export_to_globals(exported)

        assert exported["order_history"] == original["order_history"]
        assert exported["user_data_db"] == original["user_data_db"]
        assert exported["banned_users"] == original["banned_users"]

    def test_persisted_fields_complete(self):
        """All persisted field names should be valid attributes of AppState."""
        state = AppState()
        for field_name in state.PERSISTED_FIELDS:
            assert hasattr(state, field_name), f"Missing persisted field: {field_name}"

    def test_runtime_fields_complete(self):
        """All runtime field names should be valid attributes of AppState."""
        state = AppState()
        for field_name in state.RUNTIME_FIELDS:
            assert hasattr(state, field_name), f"Missing runtime field: {field_name}"

    def test_independent_instances(self):
        """Two AppState instances should NOT share mutable data."""
        a = AppState()
        b = AppState()
        a.order_history.append({"test": True})
        assert len(b.order_history) == 0

    def test_default_flags(self):
        state = AppState()
        assert state.maintenance_mode is False
        assert state.ai_auto_reply is True
        assert state.bot_instance is None
        assert state.public_api_url == ""
