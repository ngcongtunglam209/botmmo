"""Escape HTML trong tin nhan gui admin/kenh, va sinh bi mat bang CSPRNG."""

import html
import re
from pathlib import Path

import pytest

from app.core.runtime_loader import load_modules


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


# Ten hien thi Telegram do khach tu dat -> di thang vao tin nhan parse_mode=HTML.
EVIL_NAME = '<a href="https://evil.example">CLICK</a>'


@pytest.fixture
def modules():
    return load_modules()


def test_tg_emoji_retry_does_not_turn_escaped_text_back_into_markup(modules):
    """Lan gui lai sau khi bo tg-emoji van giu parse_mode=HTML.

    _plain_text_preserve_emoji() co html.unescape() ben trong, nen neu khong
    escape lai thi ten khach da escape dung se thanh the <a> song trong chat
    admin ngay o lan retry.
    """
    io_mod = modules["app.utils.telegram_io"]
    plain = io_mod._plain_text_preserve_emoji(f"<b>Khach:</b> {html.escape(EVIL_NAME)}")
    # Ham nen tang van unescape - day chinh la ly do phai escape lai o tren.
    assert "<a href=" in plain
    # Sau khi escape lai thi khong con the song nao.
    assert "<a href=" not in html.escape(plain, quote=False)


def test_delivered_payload_helper_keeps_angle_brackets(modules):
    """Bo doi chieu: ham danh cho payload KHONG duoc dien giai HTML."""
    delivery = modules["app.services.orders_delivery"]
    assert delivery._clean_delivery_line("acc|Ab<x>cd") == "acc|Ab<x>cd"
    assert delivery._clean_delivery_line("acc|a&amp;b") == "acc|a&amp;b"


@pytest.mark.parametrize(
    "path,pattern",
    [
        ("app/services/notifications_async.py", r"Khách hàng:</b> \{html\.escape"),
        ("app/handlers/admin_ops.py", r"Khách: \{html\.escape"),
        ("app/handlers/admin_orders.py", r"\{html\.escape\(str\(details\.get\('full_name'\)"),
        ("app/handlers/admin_sales.py", r"<b>User:</b> \{html\.escape"),
        ("app/jobs/payment_monitor.py", r"Khách: \{html\.escape\(str\(order_details\.get\('full_name'\)"),
        ("app/handlers/callback_router.py", r"<i>\{html\.escape\(str\(query_text"),
        ("app/handlers/callback_router.py", r"@\{html\.escape\(str\(user\.username"),
    ],
)
def test_user_supplied_names_are_escaped_before_reaching_html_messages(path, pattern):
    """Ten/username/noi dung phieu do khach dat, gui trong tin parse_mode=HTML.

    Khong escape thi khach chen duoc link phishing vao chat admin, hoac chi mot
    dau '<' la Telegram tu choi ca tin nhan va admin mat thong bao.
    """
    source = _source(path)
    assert re.search(pattern, source), f"{path}: thieu html.escape ({pattern})"


def test_no_admin_html_message_interpolates_full_name_raw():
    """Chan tai pham: khong con cho nao nhet full_name tho vao tin HTML."""
    offenders = []
    for path in (
        "app/handlers/admin_orders.py",
        "app/handlers/admin_sales.py",
        "app/jobs/payment_monitor.py",
        "app/services/notifications_async.py",
    ):
        for lineno, line in enumerate(_source(path).splitlines(), 1):
            if "html.escape" in line:
                continue
            if re.search(r"\{[a-z_]*\.?get\(['\"]full_name['\"]\)?[^}]*\}", line):
                offenders.append(f"{path}:{lineno}")
    assert not offenders, f"full_name chua escape: {offenders}"


# --- Bi mat phai sinh bang CSPRNG ------------------------------------------

def test_partner_api_key_and_transfer_code_use_secrets():
    """random la Mersenne Twister: doan duoc trang thai tu output da lo."""
    api_source = _source("app/handlers/admin_api.py")
    assert "secrets.choice" in api_source
    assert "random.choices(string.ascii_uppercase" not in api_source

    ui_source = _source("app/utils/ui_and_email.py")
    assert "random.choices(digits" not in ui_source
    assert ui_source.count("secrets.choice(digits)") == 2


def test_generated_transfer_codes_have_the_requested_shape(modules):
    ui = modules["app.utils.ui_and_email"]
    saved = dict(ui.pending_orders)
    ui.pending_orders.clear()
    try:
        codes = {ui.generate_secret_transfer_code(6) for _ in range(50)}
        assert all(len(code) == 6 and code.isdigit() for code in codes)
        assert len(codes) > 1, "ma bi mat khong duoc lap lai co dinh"
    finally:
        ui.pending_orders.clear()
        ui.pending_orders.update(saved)


# --- reply_to_ticket: phai nam trong cong kiem quyen admin ------------------

def test_reply_to_ticket_is_behind_the_admin_gate():
    source = _source("app/handlers/callback_admin.py")
    gate = source[source.index("admin_only_prefixes = ("):source.index(")", source.index("admin_only_prefixes = ("))]
    assert "'reply_to_ticket:'" in gate


def test_the_dead_duplicate_gate_is_gone():
    """Ban sao admin_only_prefixes trong callback_router chua bao gio duoc doc."""
    source = _source("app/handlers/callback_router.py")
    assert "admin_only_prefixes" not in source


# --- Chong gia mao IP va header ngoai ASCII --------------------------------

class _FakeReq:
    def __init__(self, xff=None, peer="10.0.0.9"):
        self.headers = {"x-forwarded-for": xff} if xff else {}
        self.client = type("C", (), {"host": peer})()


def test_login_rate_limit_ip_ignores_the_client_supplied_hop():
    """Caddy NOI THEM vao X-Forwarded-For, khong ghi de.

    Doc phan tu dau la de client tu chon khoa dem -> doi mot cai la reset bo
    dem chong do mat khau. Phan tu cuoi moi la cai proxy tin cay vua ghi.
    """
    from app.web import deps

    # Client gia mao '1.2.3.4', Caddy noi IP that '203.0.113.7' vao cuoi.
    assert deps.client_ip(_FakeReq("1.2.3.4, 203.0.113.7")) == "203.0.113.7"
    assert deps.client_ip(_FakeReq("203.0.113.7")) == "203.0.113.7"
    assert deps.client_ip(_FakeReq(" , 203.0.113.7 ")) == "203.0.113.7"
    # Khong co header thi dung dia chi peer.
    assert deps.client_ip(_FakeReq()) == "10.0.0.9"


def test_api_key_comparison_survives_a_non_ascii_header(modules):
    """Header co ky tu > 127 tung lam hmac.compare_digest nem TypeError -> 500."""
    helpers = modules["app.api.helpers"]
    equals = helpers._api_secret_equals
    assert equals("abc", "abc") is True
    assert equals("abc", "abd") is False
    assert equals("Bearer é", "abc") is False   # truoc day: TypeError
    assert equals("é中文", "abc") is False
