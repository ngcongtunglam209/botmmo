# --- USER WALLET TOP-UP ---
#
# Nap tien vao vi de mua hang. Tien nap KHONG duoc rut ra: phan so du den tu
# nap duoc theo doi rieng o user_data_db[uid]["balance_topup"], va
# get_withdrawable_balance() tru phan do ra. Cach nay giu shop khoi bi dung
# lam kenh chuyen tien (nap roi rut sang tai khoan khac ma khong mua gi).


def _topup_amount_bounds_text(user_id) -> str:
    return lt(
        user_id,
        "Số tiền nạp từ <b>{min}</b> đến <b>{max}</b>.",
        "Top-up amount must be between <b>{min}</b> and <b>{max}</b>.",
        "充值金额需在 <b>{min}</b> 至 <b>{max}</b> 之间。",
        min=format_money(MIN_USER_TOPUP_AMOUNT, user_id),
        max=format_money(MAX_USER_TOPUP_AMOUNT, user_id),
    )


def _topup_amount_example_text(user_id) -> str:
    """Vi du so tien go vao, viet bang chinh don vi khach dang thay."""
    from decimal import Decimal

    currency = get_user_display_currency(user_id)
    if currency == "VND":
        return "100000"
    rate = get_display_rate_vnd_per_unit(currency)
    if rate <= 0:
        return "100000"
    return f"{Decimal(100000) / rate:.2f}"


def get_user_topup_balance(user_id) -> int:
    """Phan so du den tu nap tien (khong duoc rut)."""
    profile = user_data_db.get(str(user_id))
    if not isinstance(profile, dict):
        return 0
    try:
        return max(0, int(profile.get("balance_topup", 0) or 0))
    except (TypeError, ValueError):
        return 0


def get_withdrawable_balance(user_id) -> int:
    """So du rut duoc = tong so du tru phan tu nap."""
    profile = user_data_db.get(str(user_id))
    if not isinstance(profile, dict):
        return 0
    try:
        balance = int(profile.get("balance", 0) or 0)
    except (TypeError, ValueError):
        balance = 0
    return max(0, balance - get_user_topup_balance(user_id))


def _generate_user_topup_code(user_id) -> str:
    for _ in range(50):
        code = f"NAPU{int(user_id)}{random.randint(1000, 9999)}"
        if code not in pending_user_topups:
            return code
    return f"NAPU{int(user_id)}{int(time.time() * 1000) % 100000}"


def get_user_pending_topup(user_id):
    """Ma nap dang cho cua user (moi user chi giu 1 ma tai mot thoi diem)."""
    user_id_int = int(user_id)
    for code, details in pending_user_topups.items():
        if isinstance(details, dict) and int(details.get("user_id", 0) or 0) == user_id_int:
            return code, details
    return None, None


def build_user_topup_qr_url(code: str, amount: int) -> str:
    """QR nap vi dung chung khung VietQR voi phan mua hang (qr.sepay.vn)."""
    return create_vietqr_link(int(amount), str(code))


def _build_topup_caption(user_id, code: str, amount: int) -> str:
    minutes = max(1, USER_TOPUP_EXPIRATION_SECONDS // 60)
    return lt(
        user_id,
        "<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> <b>NẠP TIỀN VÀO VÍ</b>\n\n"
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số tiền:</b> {amount}\n"
        "<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Nội dung:</b> <code>{code}</code>\n"
        "<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>Hiệu lực:</b> {minutes} phút\n\n"
        "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Chuyển <b>đúng số tiền</b> và <b>đúng nội dung</b>. "
        "Bot tự cộng tiền sau 1-3 phút.\n"
        "<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Tiền trong ví chỉ dùng để mua hàng, không rút ra được.",
        "<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> <b>TOP UP YOUR WALLET</b>\n\n"
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Amount:</b> {amount}\n"
        "<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Transfer note:</b> <code>{code}</code>\n"
        "<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>Valid for:</b> {minutes} minutes\n\n"
        "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Send the <b>exact amount</b> with the <b>exact note</b>. "
        "The bot credits your wallet within 1-3 minutes.\n"
        "<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Wallet funds can only be spent on purchases, not withdrawn.",
        "<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> <b>钱包充值</b>\n\n"
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>金额：</b> {amount}\n"
        "<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>转账备注：</b> <code>{code}</code>\n"
        "<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>有效期：</b> {minutes} 分钟\n\n"
        "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 请转账<b>准确金额</b>并填写<b>准确备注</b>，机器人将在 1-3 分钟内入账。\n"
        "<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> 钱包余额仅可用于购物，不可提现。",
        amount=format_money(amount, user_id),
        code=code,
        minutes=minutes,
    )


def _build_binance_topup_caption(user_id, code: str, amount: int, quote_data: dict) -> str:
    minutes = max(1, USER_TOPUP_EXPIRATION_SECONDS // 60)
    return lt(
        user_id,
        '<tg-emoji emoji-id="{icon}">🌐</tg-emoji> <b>NẠP VÍ QUA BINANCE PAY</b>\n\n'
        '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>Số tiền nạp:</b> {amount}\n'
        '<tg-emoji emoji-id="5281029063459234079">🤑</tg-emoji> <b>Số USDT cần chuyển:</b> <code>{crypto}</code>\n'
        '<tg-emoji emoji-id="5373251851074415873">📝</tg-emoji> <b>ID Binance:</b> <code>{payid}</code>\n'
        '<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>Hiệu lực:</b> {minutes} phút\n'
        '<tg-emoji emoji-id="5972022360025336988">🔸</tg-emoji> <b>Mã lệnh nạp:</b> <code>{code}</code>\n\n'
        '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> Chuyển <b>đúng {crypto} USDT</b> — kể cả số lẻ cuối. '
        'Số lẻ đó là thứ duy nhất giúp bot nhận ra lệnh nạp của bạn.\n'
        '- Thừa hoặc thiếu dù chỉ 0.0001 USDT thì bot <b>không tự cộng</b> được, phải nhờ hỗ trợ đối soát tay.\n'
        '- Chỉ chuyển qua <b>Binance Pay</b> tới đúng ID ở trên.\n'
        '<tg-emoji emoji-id="5460753627817723162">💡</tg-emoji> Tiền trong ví chỉ dùng để mua hàng, không rút ra được.',
        '<tg-emoji emoji-id="{icon}">🌐</tg-emoji> <b>TOP UP VIA BINANCE PAY</b>\n\n'
        '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>Top-up amount:</b> {amount}\n'
        '<tg-emoji emoji-id="5281029063459234079">🤑</tg-emoji> <b>USDT to send:</b> <code>{crypto}</code>\n'
        '<tg-emoji emoji-id="5373251851074415873">📝</tg-emoji> <b>Binance ID:</b> <code>{payid}</code>\n'
        '<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>Valid for:</b> {minutes} minutes\n'
        '<tg-emoji emoji-id="5972022360025336988">🔸</tg-emoji> <b>Top-up code:</b> <code>{code}</code>\n\n'
        '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> Send <b>exactly {crypto} USDT</b>, including the trailing '
        'decimals. Those decimals are the only thing that identifies your top-up.\n'
        '- If you send even 0.0001 USDT more or less, the bot <b>cannot credit it automatically</b> and support has to '
        'reconcile it by hand.\n'
        '- Send via <b>Binance Pay</b> to the ID above only.\n'
        '<tg-emoji emoji-id="5460753627817723162">💡</tg-emoji> Wallet funds can only be spent on purchases, not withdrawn.',
        '<tg-emoji emoji-id="{icon}">🌐</tg-emoji> <b>BINANCE PAY 充值</b>\n\n'
        '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>充值金额：</b> {amount}\n'
        '<tg-emoji emoji-id="5281029063459234079">🤑</tg-emoji> <b>需转 USDT：</b> <code>{crypto}</code>\n'
        '<tg-emoji emoji-id="5373251851074415873">📝</tg-emoji> <b>Binance ID：</b> <code>{payid}</code>\n'
        '<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>有效期：</b> {minutes} 分钟\n'
        '<tg-emoji emoji-id="5972022360025336988">🔸</tg-emoji> <b>充值单号：</b> <code>{code}</code>\n\n'
        '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> 请转入<b>准确的 {crypto} USDT</b>，包括末尾小数。'
        '该小数是识别您充值单的唯一依据。\n'
        '- 多转或少转哪怕 0.0001 USDT，机器人都<b>无法自动入账</b>，需联系客服人工核对。\n'
        '- 仅通过 <b>Binance Pay</b> 转至上方 ID。\n'
        '<tg-emoji emoji-id="5460753627817723162">💡</tg-emoji> 钱包余额仅可用于购物，不可提现。',
        icon=CRYPTO_BUTTON_ICON_ID,
        amount=format_money(amount, user_id),
        crypto=html.escape(str(quote_data.get("amount_text") or "")),
        payid=html.escape(str(quote_data.get("binance_pay_id") or "")),
        minutes=minutes,
        code=code,
    )


def _build_topup_keyboard(user_id, code: str, quote_data: dict | None = None):
    rows = []
    if isinstance(quote_data, dict):
        binance_pay_id = str(quote_data.get("binance_pay_id") or "").strip()
        amount_text = str(quote_data.get("amount_text") or "").strip()
        if binance_pay_id:
            rows.append([InlineKeyboardButton(
                lt(user_id, "📋 Sao chép ID Binance", "📋 Copy Binance ID", "📋 复制 Binance ID"),
                copy_text=CopyTextButton(binance_pay_id),
            )])
        if amount_text:
            rows.append([InlineKeyboardButton(
                lt(user_id, "📋 Sao chép số tiền", "📋 Copy amount", "📋 复制金额"),
                copy_text=CopyTextButton(amount_text),
            )])
    rows.append([_btn(lt(user_id, "Hủy lệnh nạp", "Cancel top-up", "取消充值"),
                      icon_id="5273914604752216432", callback_data=f"topup_cancel:{code}")])
    rows.append([_btn(lt(user_id, "Quay lại", "Back", "返回"),
                      icon_id="6206032691075223572", callback_data="my_stats")])
    return InlineKeyboardMarkup(rows)


def _build_nowpayments_topup_keyboard(user_id, code: str, payment: dict):
    rows = []
    address = str(payment.get("pay_address") or "").strip()
    amount_text = format(payment["pay_amount"], "f") if payment.get("pay_amount") is not None else ""
    extra_id = str(payment.get("payin_extra_id") or "").strip()
    if address:
        rows.append([InlineKeyboardButton(
            lt(user_id, "\U0001F4CB Sao chép địa chỉ ví", "\U0001F4CB Copy wallet address", "\U0001F4CB 复制钱包地址"),
            copy_text=CopyTextButton(address),
        )])
    if amount_text:
        rows.append([InlineKeyboardButton(
            lt(user_id, "\U0001F4CB Sao chép số tiền", "\U0001F4CB Copy amount", "\U0001F4CB 复制金额"),
            copy_text=CopyTextButton(amount_text),
        )])
    if extra_id:
        rows.append([InlineKeyboardButton(
            lt(user_id, "\U0001F4CB Sao chép MEMO/TAG", "\U0001F4CB Copy MEMO/TAG", "\U0001F4CB 复制 MEMO/TAG"),
            copy_text=CopyTextButton(extra_id),
        )])
    rows.append([_btn(lt(user_id, "Hủy lệnh nạp", "Cancel top-up", "取消充值"),
                      icon_id="5273914604752216432", callback_data=f"topup_cancel:{code}")])
    rows.append([_btn(lt(user_id, "Quay lại", "Back", "返回"),
                      icon_id="6206032691075223572", callback_data="my_stats")])
    return InlineKeyboardMarkup(rows)


def _build_nowpayments_topup_caption(user_id, code: str, amount: int, payment: dict) -> str:
    from app.integrations.nowpayments_api import nowpayments_pay_currency_label

    minutes = max(1, USER_TOPUP_EXPIRATION_SECONDS // 60)
    extra_id = str(payment.get("payin_extra_id") or "").strip()
    # Mang nao bat buoc memo ma khach bo trong thi tien vao vi tong cua san,
    # khong ai lan ra la cua lenh nap nao.
    extra_line = ""
    if extra_id:
        extra_line = lt(
            user_id,
            "\n\u2022 <b>MEMO/TAG (bắt buộc):</b> <code>{extra}</code>",
            "\n\u2022 <b>MEMO/TAG (required):</b> <code>{extra}</code>",
            "\n\u2022 <b>MEMO/TAG（必填）：</b> <code>{extra}</code>",
            extra=html.escape(extra_id),
        )
    return lt(
        user_id,
        "<b>NẠP VÍ BẰNG USDT</b>\n\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        "<blockquote>\u2022 <b>Số tiền nạp:</b> {amount}\n"
        "\u2022 <b>Số tiền USDT:</b> <code>{crypto}</code>\n"
        "\u2022 <b>Địa chỉ ví:</b> <code>{wallet}</code>{extra}\n"
        "\u2022 <b>Mạng lưới:</b> {network}\n"
        "\u2022 <b>Mã nạp:</b> <code>{code}</code></blockquote>\n\n"
        "\u26A0\uFE0F Chuyển <b>đúng số tiền ở trên</b> và chỉ dùng mạng <b>{network}</b>. "
        "Chuyển sai mạng có thể mất tiền.\nHết hạn sau {minutes} phút.",
        "<b>TOP UP WITH USDT</b>\n\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        "<blockquote>\u2022 <b>Top-up amount:</b> {amount}\n"
        "\u2022 <b>USDT amount:</b> <code>{crypto}</code>\n"
        "\u2022 <b>Wallet address:</b> <code>{wallet}</code>{extra}\n"
        "\u2022 <b>Network:</b> {network}\n"
        "\u2022 <b>Top-up code:</b> <code>{code}</code></blockquote>\n\n"
        "\u26A0\uFE0F Send the <b>exact amount above</b> and use only the <b>{network}</b> network. "
        "Funds sent through another network may be lost.\nExpires in {minutes} minutes.",
        "<b>USDT 充值</b>\n\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        "<blockquote>\u2022 <b>充值金额：</b> {amount}\n"
        "\u2022 <b>USDT 金额：</b> <code>{crypto}</code>\n"
        "\u2022 <b>钱包地址：</b> <code>{wallet}</code>{extra}\n"
        "\u2022 <b>网络：</b> {network}\n"
        "\u2022 <b>充值码：</b> <code>{code}</code></blockquote>\n\n"
        "\u26A0\uFE0F 请转入<b>上方准确金额</b>，且仅使用 <b>{network}</b> 网络，转错网络可能造成资金丢失。\n"
        "{minutes} 分钟后过期。",
        amount=format_money(amount, user_id),
        crypto=html.escape(format(payment["pay_amount"], "f")),
        wallet=html.escape(str(payment.get("pay_address") or "")),
        extra=extra_line,
        network=html.escape(nowpayments_pay_currency_label(str(payment.get("pay_currency") or ""))),
        code=code,
        minutes=minutes,
    )


def _build_rpay_topup_keyboard(user_id, code: str, invoice: dict):
    rows = []
    url_payment = str(invoice.get("url_payment") or "").strip()
    address = str(invoice.get("address") or "").strip()
    amount_text = str(invoice.get("amount_text") or "").strip()
    if url_payment.startswith("http"):
        rows.append([InlineKeyboardButton(
            lt(user_id, "🌐 Mở trang thanh toán", "🌐 Open payment page", "🌐 打开支付页面"),
            url=url_payment,
        )])
    if address:
        rows.append([InlineKeyboardButton(
            lt(user_id, "📋 Sao chép địa chỉ ví", "📋 Copy wallet address", "📋 复制钱包地址"),
            copy_text=CopyTextButton(address),
        )])
    if amount_text:
        rows.append([InlineKeyboardButton(
            lt(user_id, "📋 Sao chép số tiền", "📋 Copy amount", "📋 复制金额"),
            copy_text=CopyTextButton(amount_text),
        )])
    rows.append([_btn(lt(user_id, "Hủy lệnh nạp", "Cancel top-up", "取消充值"),
                      icon_id="5273914604752216432", callback_data=f"topup_cancel:{code}")])
    rows.append([_btn(lt(user_id, "Quay lại", "Back", "返回"),
                      icon_id="6206032691075223572", callback_data="my_stats")])
    return InlineKeyboardMarkup(rows)


def _build_rpay_topup_caption(user_id, code: str, amount: int, invoice: dict) -> str:
    minutes = max(1, USER_TOPUP_EXPIRATION_SECONDS // 60)
    network_name = str(invoice.get("network_name") or invoice.get("network") or "").strip() or "USDT"
    token_symbol = str(invoice.get("token") or "USDT").strip()
    expires_at = str(invoice.get("expires_at") or "").strip() or (
        datetime.now() + timedelta(seconds=USER_TOPUP_EXPIRATION_SECONDS)
    ).strftime('%H:%M:%S')
    return lt(
        user_id,
        '<tg-emoji emoji-id="5281029063459234079">🤑</tg-emoji> <b>NẠP VÍ BẰNG {token} ({network})</b>\n\n'
        '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>Số tiền nạp:</b> {amount}\n'
        '<tg-emoji emoji-id="5281029063459234079">🤑</tg-emoji> <b>Số {token} cần chuyển:</b> <code>{crypto}</code>\n'
        '<tg-emoji emoji-id="5373251851074415873">📝</tg-emoji> <b>Địa chỉ ví:</b> <code>{wallet}</code>\n'
        '<tg-emoji emoji-id="5972022360025336988">🔸</tg-emoji> <b>Mạng lưới:</b> {network}\n'
        '<tg-emoji emoji-id="5972022360025336988">🔸</tg-emoji> <b>Mã lệnh nạp:</b> <code>{code}</code>\n'
        '<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>Hiệu lực:</b> {minutes} phút (hết hạn {expires})\n\n'
        '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> Chuyển <b>đúng số tiền ở trên</b> để hệ thống tự cộng ví.\n'
        '- Chỉ dùng mạng <b>{network}</b>. Chuyển sai mạng sẽ mất tiền.\n'
        '<tg-emoji emoji-id="5460753627817723162">💡</tg-emoji> Tiền trong ví chỉ dùng để mua hàng, không rút ra được.',
        '<tg-emoji emoji-id="5281029063459234079">🤑</tg-emoji> <b>TOP UP WITH {token} ({network})</b>\n\n'
        '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>Top-up amount:</b> {amount}\n'
        '<tg-emoji emoji-id="5281029063459234079">🤑</tg-emoji> <b>{token} to send:</b> <code>{crypto}</code>\n'
        '<tg-emoji emoji-id="5373251851074415873">📝</tg-emoji> <b>Wallet address:</b> <code>{wallet}</code>\n'
        '<tg-emoji emoji-id="5972022360025336988">🔸</tg-emoji> <b>Network:</b> {network}\n'
        '<tg-emoji emoji-id="5972022360025336988">🔸</tg-emoji> <b>Top-up code:</b> <code>{code}</code>\n'
        '<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>Valid for:</b> {minutes} minutes (expires {expires})\n\n'
        '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> Send the <b>exact amount above</b> so the bot credits your wallet automatically.\n'
        '- Use only the <b>{network}</b> network. Funds sent through another network may be lost.\n'
        '<tg-emoji emoji-id="5460753627817723162">💡</tg-emoji> Wallet funds can only be spent on purchases, not withdrawn.',
        '<tg-emoji emoji-id="5281029063459234079">🤑</tg-emoji> <b>{token} 充值（{network}）</b>\n\n'
        '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>充值金额：</b> {amount}\n'
        '<tg-emoji emoji-id="5281029063459234079">🤑</tg-emoji> <b>需转 {token}：</b> <code>{crypto}</code>\n'
        '<tg-emoji emoji-id="5373251851074415873">📝</tg-emoji> <b>钱包地址：</b> <code>{wallet}</code>\n'
        '<tg-emoji emoji-id="5972022360025336988">🔸</tg-emoji> <b>网络：</b> {network}\n'
        '<tg-emoji emoji-id="5972022360025336988">🔸</tg-emoji> <b>充值单号：</b> <code>{code}</code>\n'
        '<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>有效期：</b> {minutes} 分钟（{expires} 到期）\n\n'
        '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> 请转入<b>上方准确金额</b>，系统将自动入账。\n'
        '- 仅使用 <b>{network}</b> 网络，转错网络可能造成资金丢失。\n'
        '<tg-emoji emoji-id="5460753627817723162">💡</tg-emoji> 钱包余额仅可用于购物，不可提现。',
        token=html.escape(token_symbol),
        network=html.escape(network_name),
        amount=format_money(amount, user_id),
        crypto=html.escape(str(invoice.get("amount_text") or "")),
        wallet=html.escape(str(invoice.get("address") or "")),
        code=code,
        minutes=minutes,
        expires=html.escape(expires_at),
    )


def available_topup_methods() -> list:
    """Cac cong nap vi dang bat, theo thu tu hien cho khach."""
    methods = []
    if is_bank_transfer_enabled():
        methods.append("bank")
    if is_usdt_payment_enabled():
        methods.append("usdt")
    if is_binance_pay_enabled():
        methods.append("binance")
    from app.integrations.nowpayments_api import is_nowpayments_enabled
    if is_nowpayments_enabled():
        methods.append("nowpay")
    # Khong cong nao bat -> van cho QR ngan hang de khong khoa han duong nap.
    return methods or ["bank"]


async def show_topup_method_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int) -> bool:
    """Hoi khach tra bang gi. Chi mot cong dang bat thi bo qua man hinh nay."""
    user_id = update.effective_user.id
    methods = available_topup_methods()
    if len(methods) == 1:
        return await create_user_topup_request(update, context, amount, method=methods[0])

    rows = []
    if "bank" in methods:
        rows.append([_btn(lt(user_id, "Chuyển khoản (QR)", "Bank transfer (QR)", "银行转账（QR）"),
                          icon_id=BANK_BUTTON_ICON_ID, callback_data=f"topup_pay:bank:{int(amount)}", style="success")])
    if "usdt" in methods:
        rows.append([_btn("USDT (RPay)", icon_id="5281029063459234079",
                          callback_data=f"topup_pay:usdt:{int(amount)}", style="success")])
    if "binance" in methods:
        rows.append([_btn("Binance Pay (USDT)", icon_id=CRYPTO_BUTTON_ICON_ID,
                          callback_data=f"topup_pay:binance:{int(amount)}", style="success")])
    if "nowpay" in methods:
        rows.append([_btn("USDT (NOWPayments)", icon_id="5281029063459234079",
                          callback_data=f"topup_pay:nowpay:{int(amount)}", style="success")])
    rows.append([_btn(lt(user_id, "Quay lại", "Back", "返回"),
                      icon_id="6206032691075223572", callback_data="my_stats")])

    text = lt(
        user_id,
        "<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>NẠP TIỀN VÀO VÍ</b>\n\n"
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số tiền:</b> {amount}\n\n"
        "<tg-emoji emoji-id=\"6186252635805323641\">👇</tg-emoji> Chọn phương thức thanh toán:",
        "<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>TOP UP YOUR WALLET</b>\n\n"
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Amount:</b> {amount}\n\n"
        "<tg-emoji emoji-id=\"6186252635805323641\">👇</tg-emoji> Choose a payment method:",
        "<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>钱包充值</b>\n\n"
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>金额：</b> {amount}\n\n"
        "<tg-emoji emoji-id=\"6186252635805323641\">👇</tg-emoji> 请选择付款方式：",
        amount=format_money(amount, user_id),
    )
    await safe_bot_send_html(
        context.bot,
        update.effective_chat.id,
        text,
        reply_markup=InlineKeyboardMarkup(rows),
    )
    return True


async def create_user_topup_request(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int, method: str = "bank", network: str = "") -> bool:
    """Tao ma nap + QR. Tra False neu khong tao duoc (da co ma cho / sai so tien)."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    method = str(method or "bank").strip().lower()

    if amount < MIN_USER_TOPUP_AMOUNT or amount > MAX_USER_TOPUP_AMOUNT:
        await safe_bot_send_html(context.bot, chat_id, f"{E_LIMIT} " + _topup_amount_bounds_text(user.id))
        return False

    existing_code, existing_details = get_user_pending_topup(user.id)
    if existing_code:
        await safe_bot_send_html(
            context.bot,
            chat_id,
            lt(
                user.id,
                "{limit} Bạn đang có lệnh nạp <code>{code}</code> ({amount}) chưa hoàn tất.\n"
                "Hoàn tất hoặc hủy lệnh cũ trước khi tạo lệnh mới.",
                "{limit} You already have a pending top-up <code>{code}</code> ({amount}).\n"
                "Finish or cancel it before creating a new one.",
                "{limit} 您已有待处理的充值 <code>{code}</code>（{amount}）。\n请先完成或取消后再创建。",
                limit=E_LIMIT,
                code=existing_code,
                amount=format_money(int((existing_details or {}).get("amount", 0) or 0), user.id),
            ),
            reply_markup=_build_topup_keyboard(user.id, existing_code),
        )
        return False

    code = _generate_user_topup_code(user.id)
    record = {
        "code": code,
        "user_id": int(user.id),
        "amount": int(amount),
        "time": time.time(),
        "full_name": user.full_name,
        "username": user.username,
        "provider": "bank",
    }
    quote_data = None
    rpay_invoice = None
    np_payment = None

    if method == "usdt":
        if not is_usdt_payment_enabled():
            await safe_bot_send_html(
                context.bot,
                chat_id,
                f"{E_LIMIT} " + lt(user.id, "Phương thức thanh toán này chưa được cấu hình.", "This payment method is not configured yet.", "此付款方式尚未配置。"),
            )
            return False
        try:
            rpay_invoice = await create_rpay_order(
                order_code=code,
                amount_vnd=int(amount),
                goods_name="Wallet topup",
                goods_detail=code,
                network=network,
                expire_minutes=max(1, USER_TOPUP_EXPIRATION_SECONDS // 60),
            )
        except Exception as e:
            logger.error(f"[topup] Khong tao duoc hoa don USDT cho {user.id}: {e}")
            await safe_bot_send_html(
                context.bot,
                chat_id,
                f"{E_LIMIT} " + lt(user.id, "Không thể tạo hóa đơn USDT. Vui lòng thử lại sau.", "Could not create the USDT invoice. Please try again later.", "无法创建 USDT 账单，请稍后重试。"),
            )
            return False
        # `rpay_request_id` la bi mat callback phai khop lai, `rpay_trans_id` la
        # thu duong poll hoi trang thai - thieu mot trong hai thi khach tra tien
        # xong khong ai cong.
        record.update({
            "provider": "rpay",
            "payment_method": "usdt_rpay",
            "rpay_trans_id": str(rpay_invoice.get("trans_id") or ""),
            "rpay_request_id": str(rpay_invoice.get("request_id") or ""),
            "rpay_amount": str(rpay_invoice.get("amount_text") or ""),
            "rpay_token": str(rpay_invoice.get("token") or "USDT"),
            "rpay_network": str(rpay_invoice.get("network") or ""),
            "rpay_network_name": str(rpay_invoice.get("network_name") or ""),
            "rpay_address": str(rpay_invoice.get("address") or ""),
            "rpay_url_payment": str(rpay_invoice.get("url_payment") or ""),
            "rpay_expires_at": str(rpay_invoice.get("expires_at") or ""),
            "rpay_rate": str(rpay_invoice.get("rate", USDT_RATE_VND_PER_USDT)),
        })

    if method == "binance":
        if not is_binance_pay_enabled():
            await safe_bot_send_html(
                context.bot,
                chat_id,
                f"{E_LIMIT} " + lt(user.id, "Phương thức thanh toán này chưa được cấu hình.", "This payment method is not configured yet.", "此付款方式尚未配置。"),
            )
            return False
        try:
            quote_data = await create_binance_pay_order(order_code=code, amount_vnd=int(amount))
        except Exception as e:
            logger.error(f"[topup] Khong tao duoc lenh nap Binance Pay cho {user.id}: {e}")
            await safe_bot_send_html(
                context.bot,
                chat_id,
                f"{E_LIMIT} " + lt(user.id, "Không thể tạo lệnh nạp Binance Pay. Vui lòng thử lại sau.", "Could not create the Binance Pay top-up. Please try again later.", "无法创建 Binance Pay 充值单，请稍后重试。"),
            )
            return False
        # Doi soat Binance Pay khop theo dung chuoi so tien nay, nen no phai duoc
        # luu y het nhu da hien cho khach.
        record.update({
            "provider": "binance_pay",
            "payment_method": "binance_pay",
            "binance_pay_amount": str(quote_data.get("amount_text") or ""),
            "binance_pay_id": str(quote_data.get("binance_pay_id") or ""),
            "binance_pay_rate": str(quote_data.get("rate", USDT_RATE_VND_PER_USDT)),
        })

    if method == "nowpay":
        from app.integrations.nowpayments_api import (
            create_nowpayments_payment,
            is_nowpayments_enabled,
            nowpayments_currencies_for_amount,
        )
        from app.integrations.payments_core import convert_vnd_to_usdt, get_live_usdt_vnd_rate

        if not is_nowpayments_enabled():
            await safe_bot_send_html(
                context.bot,
                chat_id,
                f"{E_LIMIT} " + lt(user.id, "Phương thức thanh toán này chưa được cấu hình.", "This payment method is not configured yet.", "此付款方式尚未配置。"),
            )
            return False
        currency = str(network or "").strip().lower()
        if not currency:
            # Khong chon mang thi lay mang dau tien con tra duoc so tien nay -
            # san cua TRC20 cao hon BEP20 toi 200 lan nen khong the mac dinh bua.
            try:
                live_rate = await get_live_usdt_vnd_rate()
                candidates = await nowpayments_currencies_for_amount(
                    convert_vnd_to_usdt(int(amount), rate=live_rate)
                )
            except Exception as e:
                logger.error(f"[topup] Khong loc duoc mang NOWPayments cho {user.id}: {e}")
                candidates = []
            if not candidates:
                await safe_bot_send_html(
                    context.bot,
                    chat_id,
                    f"{E_LIMIT} " + lt(user.id, "Số tiền này nhỏ hơn mức tối thiểu của mọi mạng USDT.", "This amount is below the minimum for every USDT network.", "此金额低于所有 USDT 网络的最低限额。"),
                )
                return False
            currency = candidates[0]
        try:
            np_payment = await create_nowpayments_payment(
                order_code=code,
                amount_vnd=int(amount),
                pay_currency=currency,
            )
        except Exception as e:
            logger.error(f"[topup] Khong tao duoc lenh nap NOWPayments cho {user.id}: {e}")
            await safe_bot_send_html(
                context.bot,
                chat_id,
                f"{E_LIMIT} " + lt(user.id, "Không thể tạo hóa đơn USDT. Vui lòng thử lại sau.", "Could not create the USDT invoice. Please try again later.", "无法创建 USDT 账单，请稍后重试。"),
            )
            return False
        # `nowpayments_payment_id` la thu duy nhat duong poll du phong dung de
        # hoi lai trang thai khi IPN khong toi.
        record.update({
            "provider": "nowpayments",
            "payment_method": "usdt_nowpayments",
            "nowpayments_payment_id": str(np_payment.get("payment_id") or ""),
            "nowpayments_amount": format(np_payment["pay_amount"], "f"),
            "nowpayments_currency": str(np_payment.get("pay_currency") or currency),
            "nowpayments_address": str(np_payment.get("pay_address") or ""),
            "nowpayments_extra_id": str(np_payment.get("payin_extra_id") or ""),
            "nowpayments_rate": str(np_payment.get("rate", USDT_RATE_VND_PER_USDT)),
        })

    pending_user_topups[code] = record
    await save_data(force=True, tables=[USER_TOPUP_FILE])

    if np_payment is not None:
        from app.integrations.nowpayments_api import nowpayments_qr_photo
        caption = _build_nowpayments_topup_caption(user.id, code, amount, np_payment)
        photo = nowpayments_qr_photo(str(np_payment.get("pay_address") or ""))
        keyboard = _build_nowpayments_topup_keyboard(user.id, code, np_payment)
    elif rpay_invoice is not None:
        caption = _build_rpay_topup_caption(user.id, code, amount, rpay_invoice)
        photo = rpay_qr_photo(rpay_invoice)
        keyboard = _build_rpay_topup_keyboard(user.id, code, rpay_invoice)
    elif quote_data is not None:
        caption = _build_binance_topup_caption(user.id, code, amount, quote_data)
        photo = binance_pay_qr_photo()
        keyboard = _build_topup_keyboard(user.id, code, quote_data)
    else:
        caption = _build_topup_caption(user.id, code, amount)
        photo = build_user_topup_qr_url(code, amount)
        keyboard = _build_topup_keyboard(user.id, code)
    try:
        if not photo:
            raise ValueError("khong tao duoc anh QR")
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"[topup] Khong gui duoc QR nap tien cho {user.id}: {e}")
        await safe_bot_send_html(context.bot, chat_id, caption, reply_markup=keyboard)
    return True


async def start_user_topup_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False):
    """Hoi so tien can nap."""
    if await check_if_banned(update):
        return
    user_id = update.effective_user.id
    await clear_user_state(context)
    context.user_data['state'] = 'awaiting_topup_amount'
    # Ty gia phai co truoc khi ve man hinh, khong thi khach EN/ZH thay so VND.
    await warm_display_rates()

    msg = lt(
        user_id,
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>NẠP TIỀN VÀO VÍ</b>\n\n"
        "Nhập số tiền muốn nạp (chỉ số).\n{bounds}\n\n"
        "Ví dụ: <code>{example}</code>\n\nGõ /cancel để hủy.",
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>TOP UP YOUR WALLET</b>\n\n"
        "Enter the amount you want to add (numbers only).\n{bounds}\n\n"
        "Example: <code>{example}</code>\n\nSend /cancel to abort.",
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>钱包充值</b>\n\n"
        "请输入充值金额（仅数字）。\n{bounds}\n\n示例：<code>{example}</code>\n\n发送 /cancel 取消。",
        bounds=_topup_amount_bounds_text(user_id),
        example=_topup_amount_example_text(user_id),
    )
    keyboard = InlineKeyboardMarkup([
        [_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data="my_stats")]
    ])
    if is_callback:
        await safe_edit_message(update.callback_query, text=msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def naptien_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/naptien [so_tien]"""
    if await check_if_banned(update):
        return
    if context.args:
        await warm_display_rates()
        amount = parse_money_to_vnd(context.args[0], update.effective_user.id)
        if amount is None:
            await update.message.reply_html(f"{E_LIMIT} " + _topup_amount_bounds_text(update.effective_user.id))
            return
        await clear_user_state(context)
        if amount < MIN_USER_TOPUP_AMOUNT or amount > MAX_USER_TOPUP_AMOUNT:
            await update.message.reply_html(f"{E_LIMIT} " + _topup_amount_bounds_text(update.effective_user.id))
            return
        await show_topup_method_choice(update, context, amount)
        return
    await start_user_topup_flow(update, context, is_callback=False)


async def handle_topup_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str):
    user_id = update.effective_user.id
    amount = parse_money_to_vnd(user_input, user_id)
    if amount is None or amount < MIN_USER_TOPUP_AMOUNT or amount > MAX_USER_TOPUP_AMOUNT:
        await update.message.reply_html(f"{E_LIMIT} " + _topup_amount_bounds_text(user_id))
        return
    await clear_user_state(context)
    await show_topup_method_choice(update, context, amount)


async def _show_topup_network_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int, networks: list) -> None:
    """Chuyen sai mang la mat tien, nen mang phai do khach chon co y thuc."""
    from app.integrations.rpay_api import rpay_network_label

    user_id = update.effective_user.id
    rows = [[
        _btn(rpay_network_label(network), icon_id="5281029063459234079",
             callback_data=f"topup_rpaynet:{network}:{int(amount)}", style="success")
    ] for network in networks]
    rows.append([_btn(lt(user_id, "Quay lại", "Back", "返回"),
                      icon_id="6206032691075223572", callback_data="my_stats")])
    await safe_edit_message(
        update.callback_query,
        text=lt(
            user_id,
            "<b>Chọn mạng lưới USDT</b>\n\nChuyển sai mạng sẽ <b>mất tiền</b>. "
            "Hãy chọn đúng mạng mà ví của bạn hỗ trợ.",
            "<b>Choose the USDT network</b>\n\nSending on the wrong network <b>loses the funds</b>. "
            "Pick the network your wallet actually supports.",
            "<b>请选择 USDT 网络</b>\n\n转错网络会<b>造成资金丢失</b>。请选择您钱包支持的网络。",
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def _show_topup_nowpayments_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int, currencies: list) -> None:
    user_id = update.effective_user.id
    from app.integrations.nowpayments_api import nowpayments_pay_currency_label

    rows = [[
        _btn(nowpayments_pay_currency_label(currency), icon_id="5281029063459234079",
             callback_data=f"topup_npnet:{currency}:{int(amount)}", style="success")
    ] for currency in currencies]
    rows.append([_btn(lt(user_id, "Quay lại", "Back", "返回"),
                      icon_id="6206032691075223572", callback_data="my_stats")])
    await safe_bot_send_html(
        context.bot,
        update.effective_chat.id,
        lt(
            user_id,
            "<b>Chọn mạng lưới USDT</b>\n\nChuyển sai mạng có thể <b>mất tiền</b>. "
            "Hãy chọn đúng mạng mà ví của bạn hỗ trợ.",
            "<b>Choose the USDT network</b>\n\nSending on the wrong network can <b>lose the funds</b>. "
            "Pick the network your wallet actually supports.",
            "<b>请选择 USDT 网络</b>\n\n转错网络可能<b>造成资金丢失</b>。请选择您钱包支持的网络。",
        ),
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def handle_topup_nowpayments_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, payload: str) -> bool:
    """`topup_npnet:<currency>:<so tien VND>` tu man hinh chon mang."""
    query = update.callback_query
    user_id = update.effective_user.id
    from app.integrations.nowpayments_api import NOWPAYMENTS_CURRENCIES

    currency, _, amount_text = str(payload or "").partition(":")
    try:
        amount = int(amount_text)
    except (TypeError, ValueError):
        await safe_answer(query, lt(user_id, "Số tiền không hợp lệ.", "Invalid amount.", "金额无效。"), show_alert=True)
        return True
    if currency not in NOWPAYMENTS_CURRENCIES:
        await safe_answer(
            query,
            lt(user_id, "Mạng lưới không khả dụng.", "This network is not available.", "该网络不可用。"),
            show_alert=True,
        )
        return True

    await safe_answer(query)
    try:
        await query.delete_message()
    except Exception:
        pass
    return await create_user_topup_request(update, context, amount, method="nowpay", network=currency)


async def handle_topup_method_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, payload: str) -> bool:
    """`topup_pay:<method>:<so tien VND>` tu man hinh chon phuong thuc."""
    query = update.callback_query
    user_id = update.effective_user.id
    method, _, amount_text = str(payload or "").partition(":")
    try:
        amount = int(amount_text)
    except (TypeError, ValueError):
        await safe_answer(query, lt(user_id, "Số tiền không hợp lệ.", "Invalid amount.", "金额无效。"), show_alert=True)
        return True
    if method not in available_topup_methods():
        await safe_answer(
            query,
            lt(user_id, "Phương thức này hiện không khả dụng.", "This method is not available.", "该方式当前不可用。"),
            show_alert=True,
        )
        return True

    if method == "usdt":
        from app.integrations.rpay_api import rpay_available_networks
        networks = rpay_available_networks()
        if len(networks) > 1:
            await safe_answer(query)
            await _show_topup_network_choice(update, context, amount, networks)
            return True

    if method == "nowpay":
        from app.integrations.nowpayments_api import nowpayments_currencies_for_amount
        from app.integrations.payments_core import convert_vnd_to_usdt, get_live_usdt_vnd_rate

        try:
            live_rate = await get_live_usdt_vnd_rate()
            currencies = await nowpayments_currencies_for_amount(
                convert_vnd_to_usdt(int(amount), rate=live_rate)
            )
        except Exception as exc:
            logger.error(f"[topup] Khong loc duoc mang NOWPayments: {exc}")
            await safe_answer(
                query,
                lt(user_id, "Không lấy được tỉ giá, thử lại sau.", "Could not fetch the rate, try again later.", "无法获取汇率，请稍后重试。"),
                show_alert=True,
            )
            return True
        if not currencies:
            await safe_answer(
                query,
                lt(user_id, "Số tiền này nhỏ hơn mức tối thiểu của mọi mạng USDT.", "This amount is below the minimum for every USDT network.", "此金额低于所有 USDT 网络的最低限额。"),
                show_alert=True,
            )
            return True
        if len(currencies) > 1:
            await safe_answer(query)
            await _show_topup_nowpayments_choice(update, context, amount, currencies)
            return True

    await safe_answer(query)
    try:
        await query.delete_message()
    except (TelegramError, ValueError, AttributeError):
        pass
    await create_user_topup_request(update, context, amount, method=method)
    return True


async def handle_topup_network_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, payload: str) -> bool:
    """`topup_rpaynet:<mang>:<so tien VND>`."""
    from app.integrations.rpay_api import rpay_available_networks

    query = update.callback_query
    user_id = update.effective_user.id
    network, _, amount_text = str(payload or "").partition(":")
    try:
        amount = int(amount_text)
    except (TypeError, ValueError):
        await safe_answer(query, lt(user_id, "Số tiền không hợp lệ.", "Invalid amount.", "金额无效。"), show_alert=True)
        return True
    if network not in rpay_available_networks():
        await safe_answer(
            query,
            lt(user_id, "Mạng lưới không khả dụng.", "This network is not available.", "该网络不可用。"),
            show_alert=True,
        )
        return True

    await safe_answer(query)
    try:
        await query.delete_message()
    except (TelegramError, ValueError, AttributeError):
        pass
    await create_user_topup_request(update, context, amount, method="usdt", network=network)
    return True


async def cancel_user_topup(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str) -> bool:
    """Huy lenh nap dang cho. Chi chu so huu duoc huy."""
    query = update.callback_query
    details = pending_user_topups.get(code)
    if not isinstance(details, dict) or int(details.get("user_id", 0) or 0) != int(update.effective_user.id):
        await safe_answer(query, lt(update.effective_user.id, "Lệnh nạp không tồn tại.", "Top-up request not found.", "找不到该充值请求。"), show_alert=True)
        return True

    pending_user_topups.pop(code, None)
    await save_data(force=True, tables=[USER_TOPUP_FILE])
    await safe_answer(query, lt(update.effective_user.id, "Đã hủy lệnh nạp.", "Top-up cancelled.", "已取消充值。"))
    try:
        await query.delete_message()
    except (TelegramError, ValueError, AttributeError):
        pass
    return True


def cleanup_expired_user_topups(current_time: float) -> bool:
    expired = [
        code for code, details in list(pending_user_topups.items())
        if not isinstance(details, dict)
        or current_time - float(details.get("time", 0) or 0) > USER_TOPUP_EXPIRATION_SECONDS
    ]
    for code in expired:
        pending_user_topups.pop(code, None)
    return bool(expired)


def find_pending_user_topup_reference(description: str):
    """Tim ma NAPU trong noi dung chuyen khoan."""
    raw_description = str(description or "")
    match = NAPU_PATTERN.search(raw_description) or NAPU_PATTERN.search(raw_description.replace(" ", ""))
    if match:
        return match.group(1).upper()
    return None


async def credit_user_topup(context: ContextTypes.DEFAULT_TYPE, code: str, amount_received: int) -> bool:
    """Cong tien nap vao vi. Tra True neu da xu ly xong ma nap nay."""
    details = pending_user_topups.get(code)
    if not isinstance(details, dict):
        return False

    user_id = int(details.get("user_id", 0) or 0)
    amount_expected = int(details.get("amount", 0) or 0)
    amount_received = int(amount_received)

    # Chuyen thieu tien: khong tu cong, de admin doi soat tay.
    if amount_received < amount_expected:
        pending_user_topups.pop(code, None)
        await safe_send_admin(
            context.bot,
            f"{E_LIMIT} <b>NẠP VÍ SAI SỐ TIỀN</b>\n"
            f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Mã: <code>{code}</code>\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> User: <code>{user_id}</code>\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Nhận {amount_received:,} / cần {amount_expected:,} VNĐ\n"
            f"<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Cộng tay: <code>/addmoney {user_id} {amount_received}</code>"
        )
        try:
            await context.bot.send_message(
                user_id,
                lt(
                    user_id,
                    "{limit} Số tiền chuyển không khớp lệnh nạp <code>{code}</code>. Admin sẽ kiểm tra và xử lý thủ công.",
                    "{limit} The transferred amount does not match top-up <code>{code}</code>. An admin will handle it manually.",
                    "{limit} 转账金额与充值单 <code>{code}</code> 不符，管理员将手动处理。",
                    limit=E_LIMIT, code=code,
                ),
                parse_mode=ParseMode.HTML,
            )
        except (TelegramError, ValueError, KeyError, AttributeError):
            pass
        return True

    user_record = db_get_user(user_id)
    current_balance = int((user_record or {}).get("balance", 0) or 0)
    new_balance = current_balance + amount_received
    db_update_balance(user_id, new_balance, reason=f"Topup: {code}")
    pending_user_topups.pop(code, None)
    await save_data(force=True, tables=[USERS_FILE, USER_TOPUP_FILE])

    try:
        await context.bot.send_message(
            user_id,
            lt(
                user_id,
                "{ok} <b>NẠP TIỀN THÀNH CÔNG</b>\n\n"
                "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Đã nạp:</b> +{amount}\n"
                "<tg-emoji emoji-id=\"4967667085606912536\">👛</tg-emoji> <b>Số dư mới:</b> {balance}\n\n"
                "Gõ /start để mua hàng ngay.",
                "{ok} <b>TOP-UP SUCCESSFUL</b>\n\n"
                "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Added:</b> +{amount}\n"
                "<tg-emoji emoji-id=\"4967667085606912536\">👛</tg-emoji> <b>New balance:</b> {balance}\n\n"
                "Send /start to shop now.",
                "{ok} <b>充值成功</b>\n\n"
                "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>已充值：</b> +{amount}\n"
                "<tg-emoji emoji-id=\"4967667085606912536\">👛</tg-emoji> <b>新余额：</b> {balance}\n\n"
                "发送 /start 立即购物。",
                ok=E_SUCCESS,
                amount=format_money(amount_received, user_id),
                balance=format_money(new_balance, user_id),
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=create_back_button_menu(user_id=user_id),
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"[topup] Khong bao duoc cho user {user_id}: {e}")

    await safe_send_admin(
        context.bot,
        f"{E_SUCCESS} <b>NẠP VÍ THÀNH CÔNG</b>\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Mã: <code>{code}</code>\n"
        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> User: <code>{user_id}</code>\n"
        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> +{amount_received:,} VNĐ | Số dư: {new_balance:,} VNĐ"
    )
    return True
