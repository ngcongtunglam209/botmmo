import asyncio
import csv
import io

import pytest

from app.core.runtime_loader import load_modules


def _modules():
    modules = load_modules()
    return modules["app.api.helpers"], modules["app.api.admin_web"]


def test_partner_ip_whitelist_supports_ipv4_ipv6_and_cidr():
    helpers, _ = _modules()
    rules = helpers._api_normalize_allowed_ips("203.0.113.10\n2001:db8::/48 10.0.0.9/24")

    assert rules == ["203.0.113.10", "2001:db8::/48", "10.0.0.0/24"]
    assert helpers._api_partner_ip_allowed({"allowed_ips": rules}, "10.0.0.42")
    assert helpers._api_partner_ip_allowed({"allowed_ips": rules}, "2001:db8::5")
    assert not helpers._api_partner_ip_allowed({"allowed_ips": rules}, "198.51.100.7")
    assert helpers._api_partner_ip_allowed({"allowed_ips": []}, "198.51.100.7")
    with pytest.raises(ValueError):
        helpers._api_normalize_allowed_ips("not-an-ip")


def test_rate_limit_is_bounded_and_defaults_to_60():
    helpers, _ = _modules()
    assert helpers._api_partner_rate_limit({}) == 60
    assert helpers._api_partner_rate_limit({"rate_limit_per_minute": 0}) == 60
    assert helpers._api_partner_rate_limit({"rate_limit_per_minute": 99999}) == 10000


def test_rotation_preserves_config_and_order_lineage(monkeypatch):
    helpers, _ = _modules()
    old_key = "sk_live_test_old"
    helpers.api_keys[old_key] = {
        "name": "Test Partner",
        "balance": 250000,
        "enabled": True,
        "allowed_ips": ["203.0.113.10"],
        "rate_limit_per_minute": 99,
    }

    async def no_save(*_args, **_kwargs):
        return None

    monkeypatch.setattr(helpers, "save_data", no_save)
    try:
        new_key, new_data = asyncio.run(helpers._api_rotate_partner_key(old_key))
        assert new_key != old_key
        assert helpers.api_keys[old_key]["enabled"] is False
        assert helpers.api_keys[old_key]["rotated_to"] == new_key
        assert new_data["balance"] == 250000
        assert new_data["allowed_ips"] == ["203.0.113.10"]
        assert new_data["rate_limit_per_minute"] == 99
        actor = helpers._api_build_actor_for_partner(new_key, new_data)
        order = {"api_partner_key_hash": helpers._api_key_fingerprint(old_key)}
        assert helpers._api_order_belongs_to_actor(order, actor)
    finally:
        helpers.api_keys.pop(old_key, None)
        if "new_key" in locals():
            helpers.api_keys.pop(new_key, None)


def test_csv_shape_never_contains_raw_api_key():
    helpers, admin = _modules()
    raw_key = "sk_live_secret_export_test"
    public_id = admin._admin_web_api_public_id(raw_key)
    output = io.StringIO()
    csv.writer(output).writerow([public_id, "Partner"])

    assert public_id in output.getvalue()
    assert raw_key not in output.getvalue()
