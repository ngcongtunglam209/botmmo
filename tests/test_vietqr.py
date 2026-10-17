"""VietQR payload against the two worked examples in NAPAS' own spec
("Quy dinh ve dinh dang VietQR" v1.0, sections 6.1.1 and 6.1.3)."""

import pytest

from app.utils import vietqr

STATIC_EXAMPLE = (
    "00020101021138570010A00000072701270006970403011200110123456780208QRIBFTTA"
    "53037045802VN6304F4E5"
)
DYNAMIC_EXAMPLE = (
    "00020101021238570010A00000072701270006970403011300110123456780208QRIBFTTA"
    "530370454061800005802VN62340107NPS68690819thanh toan don hang63042E2E"
)


def test_crc_matches_the_spec_examples():
    assert vietqr.crc16_ccitt_false(STATIC_EXAMPLE[:-4]) == "F4E5"
    assert vietqr.crc16_ccitt_false(DYNAMIC_EXAMPLE[:-4]) == "2E2E"


def test_static_qr_to_account_reproduces_spec_6_1_1():
    # The printed example in the PDF declares the account sub-field as 12 chars
    # but carries 13 digits (its table says "01 13 0011012345678"); the CRC F4E5
    # was computed over that typo. Compare against the corrected body and check
    # the CRC is self-consistent; the dynamic example below proves CRC + layout.
    payload = vietqr.build_vietqr_payload("970403", "0011012345678")
    assert payload[:-4] == (
        "00020101021138570010A00000072701270006970403011300110123456780208QRIBFTTA"
        "53037045802VN6304"
    )
    assert payload[-4:] == vietqr.crc16_ccitt_false(payload[:-4])


def test_dynamic_qr_with_amount_and_content_reproduces_spec_6_1_3():
    payload = vietqr.build_vietqr_payload(
        "970403", "0011012345678", amount=180000, add_info="thanh toan don hang", bill_number="NPS6869",
    )
    assert payload == DYNAMIC_EXAMPLE


def test_our_order_qr_carries_the_transfer_content_banks_prefill():
    payload = vietqr.build_vietqr_payload("970422", "0837324643", amount=39900, add_info="Co len nha minh 123456")
    # Dynamic, VND, exact amount, content under 62/08 — what GPM Pay echoes back.
    assert payload.startswith("000201010212")
    assert "5303704" in payload and "540539900" in payload
    assert "0822Co len nha minh 123456" in payload
    assert vietqr.crc16_ccitt_false(payload[:-4]) == payload[-4:]


def test_content_is_sanitised_to_ans_and_capped():
    payload = vietqr.build_vietqr_payload("970422", "1", amount=1, add_info="Tiền " + "x" * 80)
    # Non-ASCII dropped, capped at 50 so the 62 template never overflows 99.
    assert "Ti" in payload and "ề" not in payload
    assert len(payload) < 200


def test_bank_bin_resolves_from_short_code_or_override():
    assert vietqr.resolve_bank_bin("MB") == "970422"
    assert vietqr.resolve_bank_bin("vietcombank") == "970436"
    assert vietqr.resolve_bank_bin("XYZ", bank_bin="970499") == "970499"
    with pytest.raises(ValueError):
        vietqr.resolve_bank_bin("XYZ")
    with pytest.raises(ValueError):
        vietqr.resolve_bank_bin("MB", bank_bin="97042")


def test_png_is_rendered_locally():
    png = vietqr.make_vietqr_png("MB", "0837324643", 39900, "NAPU5551234")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(png) > 300
