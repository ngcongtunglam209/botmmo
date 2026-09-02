import pytest

from app.core.runtime_loader import load_modules


@pytest.fixture(scope="module")
def delivery():
    return load_modules()["app.services.orders_delivery"]


ITEMS = ["buyer1@mail.com|pw-4471", "buyer2@mail.com|pw-9038"]


def test_order_txt_is_written_in_the_buyer_language(delivery):
    vietnamese = delivery.build_store_order_txt_content(
        "LS-8841", "ChatGPT Plus 1 tháng", 2, 498000, "30 ngày", "7 ngày", ITEMS, lang="vi"
    )
    english = delivery.build_store_order_txt_content(
        "LS-8842", "Canva Pro", 1, 180000, "1 year", "30 days", ITEMS, lang="en"
    )
    chinese = delivery.build_store_order_txt_content(
        "LS-8843", "Netflix Premium", 1, 95000, "1 个月", "7 天", ITEMS, lang="zh"
    )

    assert "THÔNG TIN ĐƠN HÀNG" in vietnamese
    assert "Mã đơn hàng" in vietnamese and "Bảo hành" in vietnamese
    assert "ORDER INFORMATION" in english and "Warranty" in english
    assert "订单信息" in chinese and "保修" in chinese


def test_an_unknown_language_falls_back_to_vietnamese(delivery):
    content = delivery.build_store_order_txt_content(
        "LS-8844", "Spotify", 1, 72000, "1 tháng", "7 ngày", ITEMS, lang="fr"
    )

    assert "THÔNG TIN ĐƠN HÀNG" in content


@pytest.mark.parametrize("lang", ["vi", "en", "zh"])
def test_a_file_we_generated_is_recognised_when_it_comes_back(delivery, lang):
    content = delivery.build_store_order_txt_content(
        "LS-8845", "Claude Pro", 2, 798000, "30 days", "7 days", ITEMS, lang=lang
    )

    assert delivery._looks_like_supplier_summary_block(content)
    recovered = delivery.normalize_delivered_items(content)
    assert len(recovered) == 2
    assert all("@mail.com" in line for line in recovered)


def test_accented_supplier_payload_keeps_only_the_accounts(delivery):
    # NFKD does not decompose đ/Đ, so folding used to leave "đon" behind and
    # every accent-free marker missed the line.
    payload = (
        "THÔNG TIN ĐƠN HÀNG\n"
        "Mã đơn hàng : ABC-123\n"
        "Ngày mua    : 01/08/2026\n"
        "DANH SÁCH TÀI KHOẢN\n"
        "[1] mail1@x.com|pw1\n"
        "[2] mail2@x.com|pw2\n"
        "Lưu ý: không đổi mật khẩu\n"
    )

    assert delivery.normalize_delivered_items(payload) == ["mail1@x.com|pw1", "mail2@x.com|pw2"]


def test_folding_maps_the_vietnamese_d(delivery):
    assert delivery._fold_delivery_text("Mã ĐƠN hàng") == "ma don hang"
