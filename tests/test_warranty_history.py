from __future__ import annotations

from app.services.warranty_history import (
    get_latest_warranty_replacement,
    get_original_delivery_items,
    get_original_delivery_link,
    record_warranty_replacement,
)


def test_record_replacement_preserves_original_account():
    order = {"items": ["old@example.com|old-pass"], "link": "Store Product"}

    record_warranty_replacement(
        order,
        ["new@example.com|new-pass"],
        source="auto_stock",
        admin_user_id=123,
        created_at=100,
    )

    assert get_original_delivery_items(order) == ["old@example.com|old-pass"]
    assert get_original_delivery_link(order) == ""
    assert get_latest_warranty_replacement(order)["items"] == ["new@example.com|new-pass"]
    assert order["support_status"] == "warranty_replaced"


def test_latest_replacement_is_selected_for_manual_product():
    order = {"items": ["youtube-old|pass"]}
    record_warranty_replacement(order, ["youtube-first|pass"], source="manual", created_at=100)
    record_warranty_replacement(order, ["youtube-latest|pass"], source="manual", created_at=200)

    assert get_original_delivery_items(order) == ["youtube-old|pass"]
    assert get_latest_warranty_replacement(order)["items"] == ["youtube-latest|pass"]


def test_resend_link_preserves_original_link():
    order = {"link": "https://old.example/invite"}
    record_warranty_replacement(order, ["https://new.example/invite"], source="store_stock", created_at=100)
    order["link"] = "https://new.example/invite"

    assert get_original_delivery_link(order) == "https://old.example/invite"
    assert get_latest_warranty_replacement(order)["items"] == ["https://new.example/invite"]
