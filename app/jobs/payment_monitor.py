def _get_store_order_total_refund(order_details: dict, actual_amount: int) -> int:
    """Total amount the customer should get back for a failed paid store order."""
    try:
        return int(
            order_details.get(
                "original_price",
                order_details.get(
                    "total_amount",
                    int(actual_amount or 0) + int(order_details.get("balance_used", 0) or 0),
                ),
            )
            or 0
        )
    except (TypeError, ValueError, KeyError, IndexError):
        return int(actual_amount or 0) + int(order_details.get("balance_used", 0) or 0)


async def _reserve_or_reuse_pending_store_items(
    order_code: str,
    order_details: dict,
    prod_id: str,
    qty: int,
):
    """
    Reserve stock for a paid pending store order and persist that reservation
    immediately so a restart does not pop a different batch of items.
    """
    reserve_result = await consume_local_stock_items(
        prod_id,
        qty,
        order_code=order_code,
        order_state=order_details,
        persist_tables=(PRODUCTS_FILE, PENDING_ORDERS_FILE),
        source="payment_monitor",
    )
    reserved_batch = reserve_result.get("items")
    if reserved_batch:
        logger.info(f"Reserved {qty} item(s) for paid pending order {order_code}")
    return reserved_batch


async def _mark_pending_payment_message_completed(context, order_details: dict):
    message_id = order_details.get("message_id")
    user_id = order_details.get("user_id")
    if not message_id or not user_id:
        return

    completed_button = InlineKeyboardButton(
        lt(user_id, "Đã hoàn thành", "Completed", "已完成"),
        callback_data="ignore",
        api_kwargs={
            "icon_custom_emoji_id": "6269163801178804220",
            "style": "success",
        },
    )

    try:
        await context.bot.edit_message_reply_markup(
            chat_id=user_id,
            message_id=message_id,
            reply_markup=InlineKeyboardMarkup([[completed_button]]),
        )
    except (Forbidden, BadRequest):
        pass


def _find_pending_api_deposit_reference(description: str):
    raw_description = str(description or "")
    no_space_description = raw_description.replace(" ", "")
    
    match_api = NAPI_PATTERN.search(raw_description) or NAPI_PATTERN.search(no_space_description)
    if match_api:
        return match_api.group(1).upper()

    for pending_ref, details in pending_api_deposits.items():
        if not isinstance(details, dict):
            continue
        if str(details.get("reference_type") or "").strip().lower() != "telegram_id":
            continue
        transfer_content = str(details.get("transfer_content") or pending_ref or "").strip()
        if not transfer_content:
            continue
            
        if re.search(rf"(?<!\d){re.escape(transfer_content)}(?!\d)", raw_description):
            return str(pending_ref)
            
        if re.search(rf"(?<!\d){re.escape(transfer_content.replace(' ', ''))}(?!\d)", no_space_description):
            return str(pending_ref)
            
    return None


def _find_pending_order_code_by_transfer_description(description: str):
    raw_description = str(description or "")
    normalized_description = raw_description.lower()
    no_space_desc = normalized_description.replace(" ", "")
    raw_no_space = raw_description.replace(" ", "")

    for order_code, details in pending_orders.items():
        if not isinstance(details, dict):
            continue
        transfer_content = str(details.get("transfer_content") or "").strip()
        if transfer_content:
            if transfer_content.lower() in normalized_description:
                return str(order_code)
            if transfer_content.replace(" ", "").lower() in no_space_desc:
                return str(order_code)

    for order_code, details in pending_orders.items():
        if not isinstance(details, dict):
            continue
        secret_transfer_code = str(details.get("secret_transfer_code") or "").strip()
        if secret_transfer_code:
            if re.search(
                rf"(?<![0-9A-Za-z]){re.escape(secret_transfer_code)}(?![0-9A-Za-z])",
                raw_description,
                flags=re.IGNORECASE,
            ):
                return str(order_code)
            if re.search(
                rf"(?<![0-9A-Za-z]){re.escape(secret_transfer_code.replace(' ', ''))}(?![0-9A-Za-z])",
                raw_no_space,
                flags=re.IGNORECASE,
            ):
                return str(order_code)

    return None


def _build_bank_api_timeout():
    return httpx.Timeout(
        BANK_API_TIMEOUT_SECONDS,
        connect=3.0,
        read=BANK_API_TIMEOUT_SECONDS,
        write=3.0,
        pool=3.0,
    )


def _format_bank_api_error(bank_err) -> str:
    err_parts = [type(bank_err).__name__]
    err_text = str(bank_err or "").strip()
    if err_text:
        err_parts.append(err_text[:500])

    response_obj = getattr(bank_err, "response", None)
    if response_obj is not None:
        status_code = getattr(response_obj, "status_code", "")
        response_text = str(getattr(response_obj, "text", "") or "").strip()
        if status_code:
            err_parts.append(f"HTTP {status_code}")
        if response_text:
            err_parts.append(f"body={response_text[:500]}")

    return " | ".join(err_parts)


def _is_temporary_bank_api_error(bank_err) -> bool:
    if isinstance(
        bank_err,
        (
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.ConnectError,
            httpx.NetworkError,
        ),
    ):
        return True

    response_obj = getattr(bank_err, "response", None)
    status_code = getattr(response_obj, "status_code", None)
    return status_code in {502, 503, 504}


async def _cleanup_expired_pending_orders(context: ContextTypes.DEFAULT_TYPE, current_time: float) -> bool:
    pending_snapshot = await pending_items_snapshot()
    expired_codes = [code for code, details in pending_snapshot if current_time - details.get("time", 0) > ORDER_EXPIRATION_SECONDS]
    for code in expired_codes:
        details = await pending_pop(code)
        if not details:
            continue
        try:
            # RPay tu het han hoa don theo expireMinutes da gui luc tao, khong
            # co endpoint huy nen khong can goi gi them o day.
            user_id = details.get('user_id')
            refund_text = ""
            balance_used = details.get('balance_used', 0)
            if balance_used > 0:
                current_user_data = user_data_db.get(str(user_id))
                if current_user_data:
                    current_balance = current_user_data.get('balance', 0)
                    new_balance = current_balance + balance_used
                    db_update_balance(user_id, new_balance)
                    refund_text = f"\n\n<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> <b>Đã hoàn lại:</b> +{balance_used:,} VNĐ vào ví (Do đơn hết hạn)."

            if details.get("type") == "store_product":
                caption = (
                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>ĐƠN HÀNG ĐÃ HẾT HẠN</b> <tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>\n\n"
                    f"Đơn hàng này đã hết hạn thanh toán.\n"
                    f"Vui lòng tạo đơn mới nếu bạn vẫn muốn mua.{refund_text}"
                )
                reply_markup = create_back_button_menu("<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> Tạo đơn mới", "store_main", user_id=user_id)
            else:
                caption = (
                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>ĐƠN HÀNG ĐÃ HẾT HẠN</b> <tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>\n\n"
                    f"Đơn hàng cho email <b>{details.get('email', 'N/A')}</b> đã hết hạn thanh toán.\n"
                    f"Vui lòng tạo đơn mới nếu bạn vẫn muốn mua.{refund_text}"
                )
                reply_markup = create_back_button_menu("<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> Tạo đơn mới", "store_main", user_id=user_id)

            if details.get('message_id'):
                if details.get("message_kind") == "text":
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=details['message_id'],
                        text=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                else:
                    await context.bot.edit_message_caption(
                        chat_id=user_id,
                        message_id=details['message_id'],
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
        except (Forbidden, BadRequest):
            pass
    return bool(expired_codes)


def _cleanup_expired_api_deposits(current_time: float) -> bool:
    expired_deposits = [code for code, details in list(pending_api_deposits.items()) if current_time - details.get("time", 0) > 600]
    for code in expired_deposits:
       if code in pending_api_deposits:
           pending_api_deposits.pop(code, None)
    return bool(expired_deposits)


async def _scan_rpay_payments(synthetic_transactions: list) -> dict:
    """RPay: rut het hoa don callback da xac nhan (duong chinh, gan tuc thi),
    roi doi soat lai bang GetInvoiceStatus (du phong khi callback bi mat).

    Ca hai deu nap dung dang {"transactionID","description","amount"} vao
    `synthetic_transactions`, dung chung pipeline khop-don/cong-tien ben duoi
    (check_payment_job) - trung trans_id giua callback va poll van chi cong 1
    lan nho db_claim_transaction() khoa theo transactionID.

    Tra ve trang thai suc khoe: {"enabled": bool, "ok": bool, "error": str,
    "count": int}.
    """
    from app.integrations.rpay_api import (
        is_rpay_enabled,
        rpay_callback_inbox,
        rpay_poll_pending_invoices,
    )

    if not is_rpay_enabled():
        return {"enabled": False, "ok": True, "error": "", "count": 0}

    found = 0

    # 1) Callback inbox - rut het (khong co await xen giua doc/xoa nen an toan).
    if rpay_callback_inbox:
        drained, rpay_callback_inbox[:] = list(rpay_callback_inbox), []
        synthetic_transactions.extend(drained)
        found += len(drained)

    # 2) Poll du phong - hoi trang thai tung hoa don RPay dang cho.
    try:
        polled = await rpay_poll_pending_invoices()
        for tx in polled:
            if db_check_tx_exists(tx["transactionID"]):
                continue
            synthetic_transactions.append(tx)
            found += 1
    except Exception as e:
        logger.warning(f"RPay poll scan failed: {e}")
        return {"enabled": True, "ok": False, "error": str(e), "count": found}

    return {"enabled": True, "ok": True, "error": "", "count": found}



async def _scan_binance_pay_payments(synthetic_transactions: list) -> dict:
    """Binance Pay: doi soat bang feed lich su (khong co callback).

    Feed khong tra ve noi dung chuyen khoan nen khong khop duoc theo ma ICLD.
    Chi con SO TIEN + CUA SO THOI GIAN. Ba rang buoc giu cho no an toan:

      1. So tien phai trung tuyet doi. Moi don da duoc cap so le rieng luc tao
         (allocate_binance_pay_amount), nen trong dieu kien binh thuong khong
         hai don nao dung chung mot so.
      2. Neu van co hai don cung so tien (vi du don khoi phuc tu file cu), CA
         HAI deu bi bo qua. Cong nham nguoi la mat hang, tha de admin doi soat
         tay.
      3. Giao dich phai roi trong [tao don - leeway, het han + leeway].

    So tien cong cho khach luon lay tu don pending, khong bao gio tu feed.
    """
    from app.integrations.binancepay_api import (
        fetch_binance_pay_transactions,
        is_binance_pay_enabled,
    )

    if not is_binance_pay_enabled():
        return {"enabled": False, "ok": True, "error": "", "count": 0}

    pending_by_amount: dict = {}
    for order_code, order_details in await pending_items_snapshot():
        if order_details.get("provider") != "binance_pay" or order_details.get("status") != "pending_payment":
            continue
        expected_vnd = int(order_details.get("amount", 0) or 0)
        amount_text = str(order_details.get("binance_pay_amount") or "").strip()
        created_ts = float(order_details.get("timestamp") or order_details.get("time") or 0)
        if expected_vnd <= 0 or not amount_text or created_ts <= 0:
            continue
        pending_by_amount.setdefault(amount_text, []).append((order_code, expected_vnd, created_ts))

    if not pending_by_amount:
        return {"enabled": True, "ok": True, "error": "", "count": 0}

    for amount_text, orders in pending_by_amount.items():
        if len(orders) > 1:
            logger.error(
                "Binance Pay: %s don dang cho cung so tien %s USDT (%s) -> bo qua het, can doi soat tay",
                len(orders),
                amount_text,
                ", ".join(code for code, _vnd, _ts in orders),
            )

    try:
        transfers = await fetch_binance_pay_transactions()
    except Exception as e:
        logger.warning(f"Binance Pay history scan failed: {e}")
        return {"enabled": True, "ok": False, "error": str(e), "count": 0}

    found = 0
    leeway_ms = BINANCE_PAY_MATCH_LEEWAY_SECONDS * 1000
    matched_amounts = set()
    for transfer in transfers:
        amount_text = transfer["amount_text"]
        orders = pending_by_amount.get(amount_text)
        # Bo qua ca cum khi trung so tien (rang buoc 2), va khi mot giao dich
        # khac trong cung vong quet da khop don nay roi.
        if not orders or len(orders) != 1 or amount_text in matched_amounts:
            continue

        order_code, expected_vnd, created_ts = orders[0]
        transaction_ref = binance_pay_normalize_ref(transfer["transaction_id"])
        if db_check_tx_exists(transaction_ref):
            continue

        created_ts_ms = int(created_ts * 1000)
        expire_ts_ms = created_ts_ms + (ORDER_EXPIRATION_SECONDS * 1000)
        timestamp_ms = int(transfer.get("timestamp_ms") or 0)
        if timestamp_ms <= 0:
            continue
        if timestamp_ms < created_ts_ms - leeway_ms or timestamp_ms > expire_ts_ms + leeway_ms:
            continue

        matched_amounts.add(amount_text)
        synthetic_transactions.append({
            "transactionID": transaction_ref,
            "description": order_code,
            "amount": expected_vnd,
        })
        found += 1

    return {"enabled": True, "ok": True, "error": "", "count": found}


async def _scan_sepay_payments(synthetic_transactions: list) -> dict:
    """SePay: rut het giao dich webhook da nhan (duong chinh, gan tuc thi),
    roi doi soat lai bang poll API (du phong khi webhook bi mat/chua bat).

    Ca hai deu nap dung dang {"transactionID","description","amount"} vao
    `synthetic_transactions`, dung chung pipeline khop-don/cong-tien ben duoi
    (check_payment_job) - trung tx_id giua webhook va poll van chi cong 1 lan
    nho db_claim_transaction() khoa theo transactionID.

    Tra ve trang thai suc khoe cho check_payment_job cap nhat thong ke va canh
    bao admin: {"enabled": bool, "ok": bool, "error": str, "count": int}.
    """
    from app.integrations.sepay_api import sepay_webhook_inbox, sepay_fetch_history

    if not ENABLE_PAYMENT_SEPAY:
        return {"enabled": False, "ok": True, "error": "", "count": 0}

    found = 0

    # 1) Webhook inbox - rut het (khong co await xen giua doc/xoa nen an toan).
    if sepay_webhook_inbox:
        drained, sepay_webhook_inbox[:] = list(sepay_webhook_inbox), []
        synthetic_transactions.extend(drained)
        found += len(drained)

    # 2) Poll du phong - chi chay khi co cau hinh SEPAY_API_TOKEN.
    try:
        polled = await sepay_fetch_history()
        for tx in polled:
            if db_check_tx_exists(tx["transactionID"]):
                continue
            synthetic_transactions.append(tx)
            found += 1
    except Exception as e:
        logger.warning(f"SePay poll scan failed: {e}")
        return {"enabled": True, "ok": False, "error": str(e), "count": found}

    return {"enabled": True, "ok": True, "error": "", "count": found}


async def check_payment_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    global _bank_api_fail_count, _bank_api_last_alert_time
    global _bank_api_last_check_time, _bank_api_last_status, _bank_api_last_error, _bank_api_last_tx_count, _bank_api_total_checks, _bank_api_total_success
    data_changed = False
    current_time = time.time()

    data_changed |= await _cleanup_expired_pending_orders(context, current_time)
    data_changed |= _cleanup_expired_api_deposits(current_time)
    data_changed |= cleanup_expired_user_topups(current_time)

    if not pending_orders and not pending_api_deposits and not pending_user_topups:
        if data_changed:
            await save_data()
        logger.debug("LAM SHOP CRON: Không có đơn chờ, bỏ qua gọi API bank.")
        return

    logger.debug(
        f"LAM SHOP CRON: Bắt đầu quét... Đơn chờ: {len(pending_orders)} | "
        f"API Nạp chờ: {len(pending_api_deposits)} | Ví nạp chờ: {len(pending_user_topups)}"
    )
    synthetic_transactions: list = []
    rpay_status = await _scan_rpay_payments(synthetic_transactions)
    if not rpay_status["ok"]:
        logger.warning(f"❌ LỖI API RPAY: {rpay_status['error'] or 'Unknown Error'}")
    binance_pay_status = await _scan_binance_pay_payments(synthetic_transactions)
    if not binance_pay_status["ok"]:
        logger.warning(f"❌ LỖI FEED BINANCE PAY: {binance_pay_status['error'] or 'Unknown Error'}")
    sepay_status = await _scan_sepay_payments(synthetic_transactions)

    try:
        transactions = list(synthetic_transactions)

        # Suc khoe duong ngan hang = suc khoe SePay (webhook + poll doi soat).
        _bank_api_last_check_time = time.time()
        _bank_api_total_checks += 1
        if sepay_status["ok"]:
            _bank_api_fail_count = 0
            _bank_api_last_status = "ok" if sepay_status["enabled"] else "disabled"
            _bank_api_last_error = ""
            _bank_api_last_tx_count = sepay_status["count"]
            _bank_api_total_success += 1
        else:
            msg = sepay_status["error"] or "Unknown Error"
            logger.warning(f"❌ LỖI API SEPAY: {msg}")
            _bank_api_last_status = "error"
            _bank_api_last_error = msg[:240]
            _bank_api_fail_count += 1
            # Canh bao admin co backoff de khong spam.
            now_ts = time.time()
            if len(pending_orders) > 0 and (_bank_api_fail_count <= 3 or (now_ts - _bank_api_last_alert_time) >= 600):
                _bank_api_last_alert_time = now_ts
                await context.bot.send_message(
                    ADMIN_USER_ID,
                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>LỖI KẾT NỐI SEPAY API</b> (lần {_bank_api_fail_count})\n\nServer trả về: {msg}",
                    parse_mode=ParseMode.HTML
                )
            # Webhook van co the da day giao dich ve -> chi thoat khi rong.
            if not transactions:
                return

        if synthetic_transactions:
            logger.info(f"LAM SHOP CRON: Tìm thấy {len(synthetic_transactions)} giao dịch thanh toán đã xác nhận từ crypto/bank scan.")

        for tx in transactions:
            # FIX: Chuyển tx_id sang string để đồng bộ
            tx_id = str(tx.get("transactionID", "")) # Default to empty string if missing
            description = tx.get("description", "")
            amount = tx.get("amount", 0)
            
            # Skip invalid transactions
            if not tx_id or not description:
                continue

            if db_check_tx_exists(tx_id): 
                continue
            
            # FIX: Dùng compiled regex patterns để tăng tốc
            no_space_description = description.replace(" ", "")
            match_order = ICLD_PATTERN.search(description) or ICLD_PATTERN.search(no_space_description)
            secret_order_code = _find_pending_order_code_by_transfer_description(description)
            api_deposit_reference = _find_pending_api_deposit_reference(description)
            user_topup_reference = find_pending_user_topup_reference(description)

            if not (secret_order_code or match_order or api_deposit_reference or user_topup_reference):
                continue
            if not db_claim_transaction(tx_id):
                continue

            if user_topup_reference:
                # === NẠP TIỀN VÀO VÍ NGƯỜI DÙNG ===
                handled = await credit_user_topup(context, str(user_topup_reference), int(amount))
                db_add_tx(tx_id)
                data_changed = True
                if not handled:
                    # Ma het han hoac da xu ly: tien da vao tai khoan nen phai bao admin
                    # doi soat tay, khong duoc im lang bo qua.
                    logger.warning(
                        f"CRON: Ma nap {user_topup_reference} khong con trong hang cho (tx {tx_id})"
                    )
                    await safe_send_admin(
                        context.bot,
                        f"{E_LIMIT} <b>NẠP VÍ KHÔNG KHỚP LỆNH</b>\n"
                        f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Mã: <code>{user_topup_reference}</code>\n"
                        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số tiền: {int(amount):,} VNĐ\n"
                        f"<tg-emoji emoji-id=\"5350481781306958339\">🧾</tg-emoji> TX: <code>{tx_id}</code>\n"
                        f"<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Lệnh nạp đã hết hạn hoặc đã xử lý. Cộng tay: <code>/addmoney &lt;user_id&gt; {int(amount)}</code>"
                    )
                continue

            if secret_order_code or match_order: 
                # === XỬ LÝ MUA LINK / QR BANK ===
                order_code = str(secret_order_code) if secret_order_code else f"ICLD{match_order.group(1)}"
                logger.info(f"LAM SHOP CRON: Phát hiện mã đơn {order_code} trong giao dịch {tx_id}")

                order_details = await pending_get(order_code)
                if order_details:
                    expected_amount, actual_amount = int(order_details["amount"]), int(amount)
                    
                    logger.info(f"CRON: So sánh tiền - Mong đợi: {expected_amount}, Thực tế: {actual_amount}")

                    if actual_amount == expected_amount:
                        # Handle Store Product
                        if order_details.get("type") == "store_product":
                            prod_id = order_details.get("product_id")
                            qty = order_details.get("quantity", 1)
                            p = products.get(prod_id)
                            
                            # FIX: Check product exists - handle deleted products gracefully
                            if not p:
                                logger.error(f"❌ CRITICAL: Product {prod_id} không tồn tại (đã bị xóa?) cho đơn {order_code}!")
                                
                                deleted_balance_used = int(order_details.get('balance_used', 0))
                                _deleted_total = actual_amount + deleted_balance_used
                                
                                refund_user = db_get_user(order_details['user_id'])
                                refund_bal = refund_user.get('balance', 0) if refund_user else 0
                                db_update_balance(
                                    order_details['user_id'],
                                    refund_bal + _deleted_total,
                                    reason=f"Refund: product deleted {order_code}",
                                )
                                await record_wallet_refund(
                                    context,
                                    order_code=order_code,
                                    user_id=order_details['user_id'],
                                    amount=_deleted_total,
                                    product_name=order_details.get('product_name') or str(prod_id),
                                    reason="Sản phẩm không còn tồn tại",
                                    order_data=order_details,
                                )

                                try:
                                    await context.bot.send_message(
                                        order_details['user_id'],
                                        f"{E_ERROR} <b>XIN LỖI - SẢN PHẨM KHÔNG KHẢ DỤNG</b>\n\n"
                                        f"Sản phẩm bạn đặt (Mã: <code>{prod_id}</code>) hiện không còn khả dụng.\n\n"
                                        f"{E_TAG} <b>Số tiền CK:</b> {actual_amount:,} VNĐ\n"
                                        f"{E_TAG} <b>Đã hoàn ví:</b> +{_deleted_total:,} VNĐ\n"
                                        f"{E_TAG} <b>Mã đơn:</b> <code>{order_code}</code>\n\n"
                                        f"Toàn bộ tiền đã được hoàn vào Ví Bot.\n"
                                        f"Khoản hoàn từ {BANK_REFUND_MIN_AMOUNT:,} VNĐ sẽ có thêm lựa chọn nhận qua ngân hàng.",
                                        parse_mode=ParseMode.HTML
                                    )
                                except (ValueError, TypeError, KeyError, IndexError) as e:
                                    logger.error(f"Không gửi được thông báo cho user {order_details['user_id']}: {e}")
                                
                                # Alert admin with action buttons
                                try:
                                    await context.bot.send_message(
                                        ADMIN_USER_ID,
                                        f"<tg-emoji emoji-id=\"5447644880824181073\">🚨</tg-emoji> <b>LỖI NGHIÊM TRỌNG - SẢN PHẨM KHÔNG TỒN TẠI</b>\n\n"
                                        f"<b>Chi tiết:</b>\n"
                                        f"• Đơn hàng: <code>{order_code}</code>\n"
                                        f"• Product ID: <code>{prod_id}</code>\n"
                                        f"• Khách: {order_details.get('full_name')} (ID: <code>{order_details['user_id']}</code>)\n"
                                        f"• Số tiền đã nhận: {actual_amount:,} VNĐ\n"
                                        f"• Tổng đã hoàn ví: {_deleted_total:,} VNĐ\n\n"
                                        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Hệ thống đã tự động hoàn tiền. Vui lòng kiểm tra nguyên nhân product bị xóa.",
                                        parse_mode=ParseMode.HTML
                                    )
                                except (TelegramError, ValueError, KeyError, AttributeError) as e:
                                    logger.error(f"Không gửi được alert cho admin: {e}")
                                
                                # Mark transaction as processed to avoid re-checking
                                db_add_tx(tx_id)
                                await pending_pop(order_code)
                                data_changed = True
                                continue
                            
                            requires_gmail = p.get('requires_gmail', False)
                            
                            if requires_gmail:
                                # MANUAL PRODUCT: Không cần stock, đợi email từ user
                                await context.bot.send_message(
                                    order_details['user_id'],
                                    f"{E_SUCCESS} <b>THANH TOÁN THÀNH CÔNG!</b>\n\n"
                                    f"{E_TAG} <b>Sản phẩm:</b> {p['name']}\n"
                                    f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> <b>Số lượng:</b> {qty}\n"
                                    f"{E_TAG} <b>Đã thanh toán:</b> {actual_amount:,} VNĐ\n"
                                    f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n\n"
                                    f"{E_GLOBE} <b>Vui lòng nhập email nhận dịch vụ:</b>\n"
                                    f"<i>Email này sẽ được dùng để Admin setup/gửi thông tin cho bạn</i>\n\n"
                                    f"<b>Cách gửi email:</b>\n"
                                    f"• Reply tin nhắn này với email của bạn\n"
                                    f"• Hoặc dùng lệnh: <code>/guimail email@abc.com</code>",
                                    parse_mode=ParseMode.HTML
                                )
                                
                                # Lưu vào pending_manual_orders
                                balance_used_manual = int(order_details.get('balance_used', 0))
                                total_paid_manual = actual_amount + balance_used_manual
                                pending_manual_orders[order_code] = {
                                    'user_id': order_details['user_id'],
                                    'full_name': order_details.get('full_name'),
                                    'username': order_details.get('username'),
                                    'product_id': prod_id,
                                    'product_name': p['name'],
                                    'quantity': qty,
                                    'amount': total_paid_manual,
                                    'balance_used': balance_used_manual,
                                    'qr_amount': actual_amount,
                                    'timestamp': current_time,
                                    'status': 'awaiting_email',
                                    'coupon_code': order_details.get('coupon_code'),
                                    'payment_method': order_details.get('payment_method', 'bank_transfer'),
                                }

                                coupon_code_used = order_details.get('coupon_code')
                                if coupon_code_used:
                                    coupon_code_used = coupon_code_used.upper()
                                    if coupon_code_used in coupons:
                                        coupons[coupon_code_used]['used'] = coupons[coupon_code_used].get('used', 0) + 1
                                
                                # Xóa khỏi pending_orders (safe delete)
                                await _mark_pending_payment_message_completed(context, order_details)
                                await pending_pop(order_code)
                                db_add_tx(tx_id)
                                data_changed = True
                                
                                # Log cho admin
                                await context.bot.send_message(
                                    ADMIN_USER_ID,
                                    f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>ĐÃ NHẬN THANH TOÁN - ĐƠN MANUAL</b>\n"
                                    f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Mã: <code>{order_code}</code>\n"
                                    f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> SP: {p['name']}\n"
                                    f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> {actual_amount:,} VNĐ\n"
                                    f"<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Đang chờ khách nhập email...",
                                    parse_mode=ParseMode.HTML
                                )
                                
                                # Skip phần xử lý stock bên dưới
                                continue

                            
                            # AUTO PRODUCT: Cần check stock (Sản phẩm có stock local)
                            # FIX BUG #5: Dùng lock để tránh race condition
                            items_bought = await _reserve_or_reuse_pending_store_items(
                                order_code,
                                order_details,
                                prod_id,
                                qty,
                            )
                            
                            if items_bought is None:
                                current_stock = get_local_stock_available_count(p)
                                current_stock = int(current_stock or 0)
                                total_refund = int(order_details.get("original_price", actual_amount + order_details.get("balance_used", 0)))
                                current_user = db_get_user(order_details['user_id'])
                                current_balance = current_user.get("balance", 0) if current_user else 0
                                new_balance = current_balance + total_refund
                                db_update_balance(
                                    order_details['user_id'],
                                    new_balance,
                                    reason=f"Auto refund (Out of stock): {order_code}"
                                )
                                await context.bot.send_message(
                                    order_details['user_id'],
                                    f"❌ <b>RẤT TIẾC!</b>\n\n"
                                    f"Sản phẩm <b>{p['name']}</b> vừa được mua hết bởi khách khác.\n\n"
                                    f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Đơn hàng đã được hoàn tiền tự động: <b>+{total_refund:,} VNĐ</b>\n"
                                    f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> Số dư mới: <b>{new_balance:,} VNĐ</b>",
                                    parse_mode=ParseMode.HTML
                                )
                                
                                # Log cho admin
                                await context.bot.send_message(
                                    ADMIN_USER_ID,
                                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>RACE CONDITION - HẾT HÀNG!</b>\n"
                                    f"Đơn: <code>{order_code}</code>\n"
                                    f"SP: {p['name']}\n"
                                    f"Yêu cầu: {qty} | Còn: {current_stock}\n\n"
                                    f"Đã auto refund: {total_refund:,} VNĐ -> User {order_details['user_id']}",
                                    parse_mode=ParseMode.HTML
                                )
                                
                                # Cleanup (safe delete)
                                await pending_pop(order_code)
                                db_add_tx(tx_id)
                                data_changed = True
                                continue
                            
                            
                            # Delivery cho AUTO product (manual đã được handle ở trên với continue)
                            
                            # Gửi header message trước
                            try:
                                await context.bot.send_message(
                                    order_details['user_id'],
                                    f"{E_SUCCESS} <b>THANH TOÁN THÀNH CÔNG</b>\n\n"
                                    f"{E_TAG} <b>Sản phẩm:</b> {p['name']}\n"
                                    f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Số lượng:</b> {qty}\n"
                                    f"{E_TAG} <b>Thanh toán:</b> {actual_amount:,} VND\n"
                                    f"{E_LOADING} <b>Thời hạn:</b> {p.get('duration', 'N/A')}\n"
                                    f"<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>Bảo hành:</b> {p.get('warranty', 'Không')}\n\n"
                                    f"{E_TIP} <b>Hệ thống đang gửi thông tin tài khoản ngay sau tin nhắn này...</b>",
                                    parse_mode=ParseMode.HTML
                                )
                            except (TelegramError, ValueError, KeyError, AttributeError) as e:
                                logger.error(f"Lỗi gửi header message: {e}")
                            
                            purchase_date = datetime.fromtimestamp(current_time).strftime('%d/%m/%Y %H:%M:%S')
                            product_description_txt = format_product_description_for_txt(p)
                            file_content = "="*60 + "\n"
                            file_content += "           THÔNG TIN ĐƠN HÀNG\n"
                            file_content += "="*60 + "\n\n"
                            file_content += f"Mã đơn hàng    : {order_code}\n"
                            file_content += f"Ngày mua       : {purchase_date}\n"
                            file_content += f"Sản phẩm       : {p['name']}\n"
                            file_content += f"Số lượng       : {qty}\n"
                            file_content += f"Thanh toán     : {actual_amount:,} VND\n"
                            if product_description_txt:
                                file_content += f"\nMô tả sản phẩm:\n{product_description_txt}\n\n"
                            file_content += f"Thời hạn       : {p.get('duration', 'N/A')}\n"
                            file_content += f"Bảo hành       : {p.get('warranty', 'Không')}\n"
                            file_content += "\n" + "="*60 + "\n"
                            file_content += "           DANH SÁCH TÀI KHOẢN\n"
                            file_content += "="*60 + "\n\n"
                            for idx_f, item_f in enumerate(items_bought, 1):
                                file_content += f"{idx_f:03d}. {item_f}\n"
                            file_content += "\n" + "="*60 + "\n"

                            delivery_result = await deliver_items_as_txt(
                                context,
                                order_details['user_id'],
                                order_code,
                                items_bought,
                                file_content=file_content,
                                file_prefix="DonHang",
                                caption_html=f"<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> <b>File tài khoản</b>\nMã đơn: <code>{order_code}</code>",
                                reply_markup=create_success_menu(user_id=order_details['user_id']),
                            )
                            delivery_status = "Hoàn thành" if delivery_result.get("delivered") else "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Chờ gửi thủ công (AUTO Local)"
                            if not delivery_result.get("delivered"):
                                await safe_send_admin(
                                    context.bot,
                                    f"{E_SOS} <b>DELIVERY FAILED (AUTO LOCAL)</b>\n"
                                    f"{E_ID} Đơn: <code>{order_code}</code>\n"
                                    f"{E_USER} User: <code>{order_details['user_id']}</code>\n"
                                    f"{E_TAG} SP: {html.escape(p['name'])} x{qty}\n"
                                    f"{E_STAT} Fallback gửi: {delivery_result.get('sent_items', 0)}/{len(items_bought)} items\n"
                                    f"{E_ERROR} Errors: <code>{html.escape(' | '.join(delivery_result.get('errors', [])[-3:]) or 'n/a')}</code>",
                                )
                                await safe_send_message(
                                    context,
                                    order_details['user_id'],
                                    f"❌ Có lỗi khi gửi tài khoản cho đơn <code>{order_code}</code>.\n"
                                    "Admin đã nhận cảnh báo và sẽ gửi thủ công sớm nhất.",
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=create_success_menu(user_id=order_details['user_id']),
                                )
                            
                            # Tạo completed_order cho AUTO product (LƯU items để khôi phục nếu cần)
                            warranty_text = p.get('warranty', '')
                            warranty_expires = calculate_warranty_expiry(current_time, warranty_text)

                            balance_used_order = int(order_details.get('balance_used', 0))
                            total_paid = actual_amount + balance_used_order

                            completed_order = {
                                "user_id": order_details['user_id'],
                                "order_code": order_code,
                                "amount": total_paid,
                                "balance_used": balance_used_order,
                                "qr_amount": actual_amount,
                                "status": delivery_status,
                                "timestamp": current_time,
                                "full_name": order_details.get("full_name"),
                                "username": order_details.get("username"),
                                "type": "store_product",
                                "product_id": prod_id,
                                "product_name": p['name'],
                                "quantity": qty,
                                "items": items_bought,
                                "payment_method": order_details.get("payment_method", "bank_transfer"),
                                "delivery_method": delivery_result.get("method", "failed"),
                                "email": "N/A",
                                "coupon_used": order_details.get("coupon_code") or "",
                                "warranty_expires": warranty_expires,
                                "warranty_status": "active" if warranty_expires else None,
                                "warranty_claim_id": None
                            }

                            coupon_code_used = order_details.get("coupon_code")
                            if coupon_code_used:
                                coupon_code_used = coupon_code_used.upper()
                                if coupon_code_used in coupons:
                                    coupons[coupon_code_used]['used'] = coupons[coupon_code_used].get('used', 0) + 1
                            
                            # Live Notification
                            await send_live_order_notification(context, order_details.get("full_name", "Khách hàng"), total_paid, product_name=p['name'], quantity=qty, order_code=order_code)
                            
                            db_add_order(completed_order)
                            await _mark_pending_payment_message_completed(context, order_details)
                            await pending_pop(order_code)
                            db_add_tx(tx_id)
                            data_changed = True
                            
                            # Critical: force-save order + stock + tx immediately (no debounce)
                            await save_critical_tables(HISTORY_FILE, PROCESSED_TX_FILE, PRODUCTS_FILE, PENDING_ORDERS_FILE, USERS_FILE)
                            
                            # === PROCESS REFERRAL COMMISSION ===
                            await process_referral_commission(context, order_details['user_id'], actual_amount)
                            # ===================================
                            
                            # Auto-broadcast nếu hết hàng
                            remaining_stock = int(get_local_stock_available_count(products.get(prod_id)) or 0)
                            if delivery_result.get("delivered"):
                                create_background_task(send_post_purchase_followups(context, order_details['user_id'], prod_id))
                            if remaining_stock == 0:
                                create_background_task(broadcast_out_of_stock(context, p['name'], prod_id))
                            
                            # Admin notification (safe - sau khi đã save)
                            try:
                                await safe_send_admin(context.bot, f"{E_SUCCESS} <b>ĐƠN HÀNG STORE MỚI</b>\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Mã: <code>{order_code}</code>\n{E_TAG} SP: {html.escape(p['name'])} (x{qty})\n{E_TAG} {actual_amount:,} VNĐ")
                            except (TelegramError, ValueError, KeyError, AttributeError) as admin_err:
                                logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Store admin notification failed: {admin_err}")
                            
                            # SKIP shared cleanup (đã xử lý ở trên)
                            continue
                        
                        # Cac loai don khac store_product khong con luong nao tao ra
                        else:
                            logger.warning(
                                f"CRON: Don {order_code} co type khong ho tro "
                                f"({order_details.get('type')}), chi ghi nhan giao dich"
                            )
                            db_add_tx(tx_id)
                            await _mark_pending_payment_message_completed(context, order_details)
                            await pending_pop(order_code)
                            data_changed = True
                    else:
                        logger.warning(f"Giao dịch gần đúng! Code: {order_code}, Mong đợi: {expected_amount}, Thực tế: {actual_amount}")
                        alert_message = ( f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>CẢNH BÁO GIAO DỊCH ĐÁNG NGỜ</b> <tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>\n\n" f"Phát hiện giao dịch có mã đơn hàng đang chờ nhưng sai số tiền.\n\n" f"- <b>Mã đơn hàng:</b> <code>{order_code}</code>\n" f"- <b>Khách hàng:</b> {html.escape(order_details.get('full_name', 'N/A'))} (@{html.escape(order_details.get('username') or 'N/A')})\n" f"- <b>Số tiền đúng:</b> <pre>{expected_amount:,} VNĐ</pre>\n" f"- <b>Số tiền đã chuyển:</b> <pre>{actual_amount:,} VNĐ</pre>\n\n" f"Vui lòng kiểm tra và xử lý thủ công. Giao dịch này chưa được tự động xử lý." )
                        await safe_send_admin(context.bot, alert_message); db_add_tx(tx_id); data_changed = True

                else:
                    if not db_check_tx_exists(tx_id):
                        db_add_tx(tx_id); data_changed = True
                        logger.warning(f'CRON: Phát hiện thanh toán trễ/orphan: {order_code} - {int(amount):,} VNĐ (đơn đã hết hạn hoặc đã xử lý)')
                        existing_order = order_index.get(order_code)
                        if not existing_order:
                            await safe_send_admin(
                                context.bot,
                                f'<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>THANH TOÁN TRỄ - CẦN XỬ LÝ</b>\n\n'
                                f'Mã đơn: <code>{order_code}</code>\n'
                                f'Số tiền: <b>{int(amount):,} VNĐ</b>\n'
                                f'Mô tả GD: <code>{html.escape(description[:100])}</code>\n'
                                f'TX ID: <code>{tx_id}</code>\n\n'
                                f'Đơn hàng này đã hết hạn hoặc không tồn tại trong hàng chờ.\n'
                                f'Vui lòng kiểm tra và hoàn tiền nếu cần: <code>/refund {order_code}</code>'
                            )

            elif api_deposit_reference:
                # === XỬ LÝ NẠP TIỀN API ===
                deposit_code = str(api_deposit_reference)
                if deposit_code in pending_api_deposits:
                    details = pending_api_deposits[deposit_code]
                    amount_expected = int(details.get("amount", 0))
                    amount_received = int(amount)
                    reference_type = str(details.get("reference_type") or "").strip().lower()
                    allow_flexible_amount = reference_type == "telegram_id" and amount_expected <= 0
                    if amount_expected <= 0 and not allow_flexible_amount:
                        db_add_tx(tx_id)
                        pending_api_deposits.pop(deposit_code, None)
                        data_changed = True
                        await safe_send_admin(
                            context.bot,
                            f"{E_LIMIT} <b>NẠP API LỖI CẤU HÌNH</b>\n"
                            f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Code: <code>{deposit_code}</code>\n"
                            f"<tg-emoji emoji-id=\"5350481781306958339\">🧾</tg-emoji> Lý do: Số tiền kỳ vọng không hợp lệ ({amount_expected})."
                        )
                        continue
                    
                    if allow_flexible_amount or amount_received >= amount_expected:
                        key = details.get("api_key")
                        if not key or key not in api_keys:
                            db_add_tx(tx_id)
                            pending_api_deposits.pop(deposit_code, None)
                            data_changed = True
                            await safe_send_admin(
                                context.bot,
                                f"{E_LIMIT} <b>NẠP API LỖI KEY</b>\n"
                                f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Code: <code>{deposit_code}</code>\n"
                                f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Nhận: {amount_received:,} VNĐ\n"
                                f"<tg-emoji emoji-id=\"5350481781306958339\">🧾</tg-emoji> Lý do: API key không tồn tại hoặc đã bị xóa."
                            )
                            continue

                        key_data = _api_normalize_partner_key(key)
                        if not isinstance(key_data, dict):
                            db_add_tx(tx_id)
                            pending_api_deposits.pop(deposit_code, None)
                            data_changed = True
                            await safe_send_admin(
                                context.bot,
                                f"{E_LIMIT} <b>NẠP API LỖI DỮ LIỆU</b>\n"
                                f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Code: <code>{deposit_code}</code>\n"
                                f"<tg-emoji emoji-id=\"5350481781306958339\">🧾</tg-emoji> Lý do: Dữ liệu API key không hợp lệ."
                            )
                            continue

                        adjusted, new_bal, key_data = await safe_api_adjust_balance(
                            key,
                            amount_received,
                            save=False,
                            reason=f"API deposit {deposit_code}",
                        )
                        if not adjusted or not isinstance(key_data, dict):
                            db_add_tx(tx_id)
                            pending_api_deposits.pop(deposit_code, None)
                            data_changed = True
                            await safe_send_admin(
                                context.bot,
                                f"{E_LIMIT} <b>NẠP API LỖI KHÓA VÍ</b>\n"
                                f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Code: <code>{deposit_code}</code>\n"
                                f"<tg-emoji emoji-id=\"5350481781306958339\">🧾</tg-emoji> Lý do: Không thể cập nhật số dư API key."
                            )
                            continue
                        p_name = details.get("partner_name", key_data.get("name", "N/A"))
                        
                        db_add_tx(tx_id)
                        pending_api_deposits.pop(deposit_code, None)
                        data_changed = True
                        
                        await safe_send_admin(
                            context.bot,
                            f"{E_SUCCESS} <b>NẠP TIỀN API THÀNH CÔNG</b>\n\n"
                            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Partner:</b> {html.escape(str(p_name))}\n"
                            f"{E_TAG} <b>Nạp vào:</b> {amount_received:,} VNĐ\n"
                            f"<tg-emoji emoji-id=\"5863724849851011383\">💵</tg-emoji> <b>Số dư mới:</b> {new_bal:,} VNĐ\n"
                            f"{E_TAG} <b>Mã GD:</b> <code>{deposit_code}</code>"
                        )
                        
                        # Gửi thông báo cho user (nếu có user_id được lưu)
                        user_id_to_notify = details.get("user_id")
                        if user_id_to_notify:
                            try:
                                await context.bot.send_message(
                                    chat_id=user_id_to_notify,
                                    text=lt(
                                        user_id_to_notify,
                                        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>NẠP TIỀN API THÀNH CÔNG</b>\n\n"
                                        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Partner:</b> {html.escape(str(p_name))}\n"
                                        f"<tg-emoji emoji-id=\"5397916757333654639\">➕</tg-emoji> <b>Đã nạp:</b> {amount_received:,} VNĐ\n"
                                        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số dư mới:</b> {new_bal:,} VNĐ\n"
                                        f"<i>Cảm ơn bạn đã nạp tiền.</i>",
                                        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>API WALLET TOPPED UP</b>\n\n"
                                        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Partner:</b> {html.escape(str(p_name))}\n"
                                        f"<tg-emoji emoji-id=\"5397916757333654639\">➕</tg-emoji> <b>Added:</b> {amount_received:,} VND\n"
                                        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>New balance:</b> {new_bal:,} VND\n"
                                        f"<i>Thank you for your top-up.</i>",
                                        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>API 钱包充值成功</b>\n\n"
                                        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>合作方：</b>{html.escape(str(p_name))}\n"
                                        f"<tg-emoji emoji-id=\"5397916757333654639\">➕</tg-emoji> <b>充值：</b>{amount_received:,} VND\n"
                                        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>新余额：</b>{new_bal:,} VND\n"
                                        f"<i>感谢您的充值。</i>",
                                    ),
                                    parse_mode=ParseMode.HTML
                                )
                            except (TelegramError, ValueError, KeyError, AttributeError) as e:
                                logger.error(f"Khong the gui thong bao nap API thanh cong cho user {user_id_to_notify}: {e}")
                    else:
                         # Thiếu tiền
                         db_add_tx(tx_id); data_changed = True
                         await safe_send_admin(
                            context.bot,
                            f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>LỖI NẠP API (THIẾU TIỀN)</b>\nCode: {deposit_code}\nNhận: {amount_received:,}\nCần: {amount_expected:,}"
                         )

    except (TelegramError, httpx.HTTPError, sqlite3.Error, ValueError, KeyError) as e: logger.error(f"❌ LỖI KHÔNG XÁC ĐỊNH TRONG check_payment_job: {e}", exc_info=True)
    if data_changed: await save_critical_tables(HISTORY_FILE, PROCESSED_TX_FILE, PENDING_ORDERS_FILE, USERS_FILE, API_KEYS_FILE, "data_pending_api_deposits.json")

async def cleanup_expired_coupons_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("CRON: Bắt đầu quét mã giảm giá không hợp lệ...")
    today = datetime.now().date(); invalid_codes = []
    for code, details in list(coupons.items()):
        is_expired, is_used_up = False, False
        expiry_str = details.get('expires')
        if expiry_str:
            try:
                if datetime.strptime(expiry_str, '%d-%m-%Y').date() < today: is_expired = True
            except ValueError: logger.warning(f"Lỗi định dạng ngày ở mã giảm giá '{code}': '{expiry_str}'")
        quantity = details.get('quantity')
        if isinstance(quantity, int) and details.get('used', 0) >= quantity: is_used_up = True
        if is_expired or is_used_up:
            reason = "hết hạn" if is_expired else "hết lượt sử dụng"; invalid_codes.append(f"{code} ({reason})"); coupons.pop(code, None)
    if invalid_codes:
        logger.info(f"<tg-emoji emoji-id=\"5462956611033117422\">🧹</tg-emoji> Đã tự động xóa {len(invalid_codes)} mã giảm giá: {', '.join(invalid_codes)}"); await save_data()
        try:
            report_text = f"<tg-emoji emoji-id=\"5462956611033117422\">🧹</tg-emoji> <b>BÁO CÁO DỌN DẸP HÀNG NGÀY</b>\n\nĐã tự động xóa <b>{len(invalid_codes)}</b> mã giảm giá không hợp lệ:\n- <code>" + "</code>\n- <code>".join(invalid_codes) + "</code>"
            await safe_send_admin(context.bot, report_text)
        except (TelegramError, ValueError, KeyError, AttributeError) as e: logger.error(f"Không thể gửi tin nhắn báo cáo dọn dẹp cho admin: {e}")
    else: logger.info("CRON: Không có mã giảm giá nào cần dọn dẹp.")

async def automatic_reward_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tự động trao thưởng Top tuần/tháng"""
    now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    today = now.date()
    
    # --- THƯỞNG TUẦN (Chạy vào thứ 2 hàng tuần) ---
    if today.weekday() == 0: # 0 = Thứ 2
        # Lấy dữ liệu tuần trước (Thứ 2 tuần trước -> Chủ nhật tuần trước)
        start_date = today - timedelta(days=7)
        end_date = today - timedelta(days=1)
        
        start_dt = datetime.combine(start_date, dt_time.min)
        end_dt = datetime.combine(end_date, dt_time.max)
        
        await process_top_buyer_reward(context, start_dt, end_dt, "WEEKLY", 2, 15)

    # --- THƯỞNG THÁNG (Chạy vào ngày 1 hàng tháng) ---
    if today.day == 1:
        # Lấy dữ liệu tháng trước
        first_day_this_month = today
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        
        start_dt = datetime.combine(first_day_last_month, dt_time.min)
        end_dt = datetime.combine(last_day_last_month, dt_time.max)
        
        await process_top_buyer_reward(context, start_dt, end_dt, "MONTHLY", 1, 50)

async def process_top_buyer_reward(context, start_dt, end_dt, reward_type, quantity, discount_percent):
    start_ts = start_dt.timestamp()
    end_ts = end_dt.timestamp()
    
    # Lọc đơn hàng hoàn thành trong khoảng thời gian
    eligible_orders = [
        o for o in order_history 
        if is_completed_order(o)
        and start_ts <= o.get("timestamp", 0) <= end_ts
    ]
    
    if not eligible_orders:
        return

    # Đếm số đơn theo user
    user_counts = Counter(
        resolved_uid for resolved_uid in (_api_get_effective_order_user_id(order) for order in eligible_orders)
        if resolved_uid
    )
    if not user_counts:
        return
        
    # Lấy Top 1
    top_user_id, count = user_counts.most_common(1)[0]
    
    # Tạo Coupon
    coupons_created = []
    for _ in range(quantity):
        # Mã: TOPWEEK-ID-RANDOM hoặc TOPMONTH-ID-RANDOM
        prefix = "TOPWEEK" if reward_type == "WEEKLY" else "TOPMONTH"
        code = f"{prefix}-{top_user_id}-{random.randint(1000,9999)}"
        
        expires_str = (datetime.now() + timedelta(days=30)).strftime('%d-%m-%Y')
        
        coupons[code] = {
            "discount": discount_percent,
            "is_percent": True,
            "quantity": 1,
            "expires": expires_str,
            "used": 0
        }
        coupons_created.append(code)
        
    await save_data()
    
    # Gửi thông báo cho User
    user_info = user_data_db.get(str(top_user_id), {})
    full_name = user_info.get("first_name", "Khách hàng")
    
    period_name = "TUẦN" if reward_type == "WEEKLY" else "THÁNG"
    time_range_str = f"{start_dt.strftime('%d/%m')} - {end_dt.strftime('%d/%m')}"
    
    msg = (
        f"⭐️ <b>CHÚC MỪNG TOP 1 NGƯỜI MUA HÀNG {period_name} QUA!</b> ⭐️\n"
        f"<i>({time_range_str})</i>\n\n"
        f"Xin chào <b>{full_name}</b>,\n"
        f"Bạn là người mua hàng nhiều nhất trong {period_name.lower()} vừa qua với <b>{count} đơn hàng</b>.\n\n"
        f"<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> <b>Phần thưởng của bạn:</b>\n"
        f"<b>{quantity}x Mã giảm giá {discount_percent}%</b>\n\n"
    )
    
    for code in coupons_created:
        msg += f"<tg-emoji emoji-id=\"5377624166436445368\">🎟️</tg-emoji> <code>{code}</code>\n"
        
    msg += "\n<i>(Hạn sử dụng: 30 ngày. Áp dụng cho đơn hàng tiếp theo)</i>"
    
    try:
        await context.bot.send_message(top_user_id, msg, parse_mode=ParseMode.HTML)
        
        # Thông báo Admin
        admin_msg = (
            f"{E_SUCCESS} <b>ĐÃ TỰ ĐỘNG TRAO THƯỞNG {period_name}</b>\n\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>User:</b> {full_name} (ID: <code>{top_user_id}</code>)\n"
            f"{E_STAT} <b>Thành tích:</b> {count} đơn\n"
            f"{E_TAG} <b>Phần thưởng:</b> {quantity} mã {discount_percent}%\n"
            f"<tg-emoji emoji-id=\"5377624166436445368\">🎟️</tg-emoji> <b>Mã:</b> {', '.join(coupons_created)}"
        )
        await safe_send_admin(context.bot, admin_msg)
        
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Lỗi gửi thưởng {reward_type} cho user {top_user_id}: {e}")


