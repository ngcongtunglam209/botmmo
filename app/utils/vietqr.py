"""Sinh mã VietQR (NAPAS 247 chuyển tới tài khoản) tại chỗ, không qua img.vietqr.io.

Chuẩn: "Quy định về định dạng VietQR" v1.0 (09/2021) của NAPAS, dựa trên EMVCo
Merchant-Presented QR. Payload là chuỗi TLV (ID 2 ký tự + độ dài 2 chữ số + giá
trị), chốt bằng CRC16/CCITT-FALSE. Hai ví dụ chuẩn trong tài liệu (mục 6.1.1 và
6.1.3) được dùng làm test đối chiếu — sai một byte là app ngân hàng báo QR lỗi.

Module thường (import bình thường), không nằm trong SECTION_FILES.
"""

from __future__ import annotations

import io

NAPAS_AID = "A000000727"
SERVICE_TO_ACCOUNT = "QRIBFTTA"
CURRENCY_VND = "704"
COUNTRY_VN = "VN"

# Mã BIN do NHNN cấp. img.vietqr.io nhận mã chữ (MB, VCB...) rồi tự tra; ở đây ta
# tra lấy. Ngân hàng không có trong bảng thì đặt BANK_BIN trong .env.
BANK_BINS: dict[str, str] = {
    "MB": "970422", "MBBANK": "970422",
    "VCB": "970436", "VIETCOMBANK": "970436",
    "TCB": "970407", "TECHCOMBANK": "970407",
    "ACB": "970416",
    "VPB": "970432", "VPBANK": "970432",
    "TPB": "970423", "TPBANK": "970423",
    "BIDV": "970418",
    "VBA": "970405", "AGRIBANK": "970405",
    "ICB": "970415", "CTG": "970415", "VIETINBANK": "970415",
    "STB": "970403", "SACOMBANK": "970403",
    "MSB": "970426",
    "HDB": "970437", "HDBANK": "970437",
    "VIB": "970441",
    "SHB": "970443",
    "OCB": "970448",
    "SEAB": "970440", "SEABANK": "970440",
    "LPB": "970449", "LPBANK": "970449", "LIENVIETPOSTBANK": "970449",
    "EIB": "970431", "EXIMBANK": "970431",
    "NAB": "970428", "NAMABANK": "970428",
    "BAB": "970409", "BACABANK": "970409",
    "PVCB": "970412", "PVCOMBANK": "970412",
    "VCCB": "970454", "BVBANK": "970454",
    "CAKE": "546034",
    "UBANK": "546035",
    "TIMO": "963388",
}


def resolve_bank_bin(bank_id: str, bank_bin: str = "") -> str:
    """BIN 6 chữ số từ BANK_BIN (ưu tiên) hoặc tra BANK_ID trong bảng."""
    override = str(bank_bin or "").strip()
    if override:
        if not (override.isdigit() and len(override) == 6):
            raise ValueError(f"BANK_BIN phải là 6 chữ số, nhận: {override!r}")
        return override
    key = str(bank_id or "").strip().upper().replace(" ", "")
    try:
        return BANK_BINS[key]
    except KeyError:
        raise ValueError(f"Không biết BIN của ngân hàng {bank_id!r}; đặt BANK_BIN trong .env") from None


def crc16_ccitt_false(data: str) -> str:
    """CRC theo ISO/IEC 13239: đa thức 0x1021, khởi tạo 0xFFFF, không đảo bit."""
    crc = 0xFFFF
    for byte in data.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def _tlv(tag: str, value: str) -> str:
    if len(value) > 99:
        raise ValueError(f"Trường {tag} dài {len(value)} > 99")
    return f"{tag}{len(value):02d}{value}"


def _ans(value: str, limit: int) -> str:
    """Giữ ASCII in được (bộ ký tự ANS của spec), cắt theo giới hạn."""
    return "".join(ch for ch in str(value or "") if 32 <= ord(ch) < 127).strip()[:limit]


def build_vietqr_payload(
    bank_bin: str,
    account_number: str,
    amount: int | None = None,
    add_info: str = "",
    bill_number: str = "",
) -> str:
    """Chuỗi QR hoàn chỉnh (đã kèm CRC).

    `amount` khác None -> QR động (01=12, một lần dùng), có trường 54. VND không
    có phần thập phân nên số tiền là chuỗi số nguyên. `add_info` đi vào 62/08
    (mục đích giao dịch) — đây là "nội dung chuyển khoản" mà app ngân hàng điền
    sẵn và GPM Pay bắn về trong webhook. Spec giới hạn 25 ký tự nhưng các app
    đều nhận tới ~50 (img.vietqr.io cũng sinh như vậy); cắt ở 50 cho an toàn.
    """
    bank_bin = str(bank_bin or "").strip()
    account_number = _ans(account_number, 19)
    if not (bank_bin.isdigit() and len(bank_bin) == 6):
        raise ValueError("bank_bin phải là 6 chữ số")
    if not account_number:
        raise ValueError("Thiếu số tài khoản")

    merchant = _tlv("00", bank_bin) + _tlv("01", account_number)
    account_info = _tlv("00", NAPAS_AID) + _tlv("01", merchant) + _tlv("02", SERVICE_TO_ACCOUNT)

    parts = [
        _tlv("00", "01"),
        _tlv("01", "12" if amount is not None else "11"),
        _tlv("38", account_info),
        _tlv("53", CURRENCY_VND),
    ]
    if amount is not None:
        amount = int(amount)
        if amount <= 0:
            raise ValueError("Số tiền phải > 0")
        parts.append(_tlv("54", str(amount)))
    parts.append(_tlv("58", COUNTRY_VN))

    extra = ""
    if bill_number:
        extra += _tlv("01", _ans(bill_number, 25))
    if add_info:
        extra += _tlv("08", _ans(add_info, 50))
    if extra:
        parts.append(_tlv("62", extra))

    body = "".join(parts) + "6304"
    return body + crc16_ccitt_false(body)


def render_qr_png(payload: str, scale: int = 10) -> bytes:
    """PNG của payload. segno thuần Python, không cần Pillow."""
    import segno

    buffer = io.BytesIO()
    segno.make(payload, error="m", micro=False).save(buffer, kind="png", scale=scale, border=2)
    return buffer.getvalue()


def make_vietqr_png(
    bank_id: str,
    account_number: str,
    amount: int | None,
    add_info: str,
    bank_bin: str = "",
) -> bytes:
    """Ảnh QR chuyển khoản sẵn sàng gửi lên Telegram (bytes)."""
    payload = build_vietqr_payload(
        resolve_bank_bin(bank_id, bank_bin),
        account_number,
        amount=amount,
        add_info=add_info,
    )
    return render_qr_png(payload)
