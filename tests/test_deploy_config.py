"""Cau hinh trien khai phai nhat quan giua compose, Caddyfile va code.

Khong test duoc bang cach chay bot, nhung lech nhau o day lam sap site hoac mo
cua cho request gia mao, nen pin lai bang test.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _caddyfile() -> str:
    return (ROOT / "Caddyfile").read_text(encoding="utf-8")


def _compose() -> dict:
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def test_caddy_upstream_port_is_not_hardcoded():
    """Caddyfile tro dung port ma bot bind.

    Truoc day docker-compose tham so hoa API_SERVER_PORT nhung Caddyfile hardcode
    8080, nen doi bien do la site sap ma khong co dau hieu gi.
    """
    text = _caddyfile()
    match = re.search(r"reverse_proxy\s+bot:(\S+)", text)
    assert match, "khong thay reverse_proxy toi bot"
    upstream = match.group(1)
    assert "API_SERVER_PORT" in upstream, f"port dang hardcode: {upstream}"


def test_caddy_container_receives_the_port_variable():
    """Caddyfile doc {$API_SERVER_PORT} nen container caddy phai co bien do."""
    env = _compose()["services"]["caddy"].get("environment") or {}
    if isinstance(env, list):
        env = dict(item.split("=", 1) for item in env)
    assert "API_SERVER_PORT" in env, "caddy khong nhan API_SERVER_PORT -> roi ve mac dinh"
    assert "API_SERVER_PORT" in str(env["API_SERVER_PORT"])


def test_bot_expose_and_caddy_upstream_use_the_same_variable():
    expose = _compose()["services"]["bot"].get("expose") or []
    assert any("API_SERVER_PORT" in str(item) for item in expose), expose


def test_admin_panel_refuses_to_be_framed():
    """Cookie phien la SameSite=strict nen CSRF da bi chan; con lai clickjacking."""
    text = _caddyfile()
    block = re.search(r"header\s+/admin\*\s*\{(.+?)\}", text, re.S)
    assert block, "khong thay khoi header cho /admin"
    body = block.group(1)
    assert "X-Frame-Options" in body and "DENY" in body
    assert "frame-ancestors" in body


def test_bot_port_is_never_published_to_the_host():
    """Chi Caddy duoc lo ra ngoai.

    Chong do brute-force dang nhap tin X-Forwarded-For, nen port cua bot ma lo
    thang ra VPS la bo qua duoc gioi han so lan.
    """
    bot = _compose()["services"]["bot"]
    assert not bot.get("ports"), f"bot khong duoc publish port: {bot.get('ports')}"
    assert bot.get("expose"), "bot phai dung expose (chi noi bo docker network)"
