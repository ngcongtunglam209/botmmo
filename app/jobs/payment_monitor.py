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
        "Đã hoàn thành",
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


def _ctt_inputs_from_pending_order(order_details: dict) -> dict:
    return {
        "link": str(order_details.get("ctt_target_link") or "").strip(),
        "comments": str(order_details.get("ctt_comments") or "").strip(),
    }


def _build_ctt_completed_order(order_code: str, order_details: dict, product_data: dict, total_paid: int, current_time: float, supplier_result: dict) -> dict:
    customer_order_code = _ctt_customer_order_code(order_code, supplier_result)
    completed_order = {
        "user_id": order_details['user_id'],
        "order_code": customer_order_code,
        "payment_reference_code": order_code,
        "amount": total_paid,
        "balance_used": int(order_details.get("balance_used", 0) or 0),
        "qr_amount": int(order_details.get("amount", 0) or 0),
        "status": ctt_build_local_order_status(supplier_result.get("supplier_status") or "Pending"),
        "timestamp": current_time,
        "full_name": order_details.get("full_name"),
        "username": order_details.get("username"),
        "type": "store_product",
        "product_id": order_details.get("product_id") or "",
        "product_name": product_data.get("name") or order_details.get("product_name") or "Social Service",
        "quantity": int(order_details.get("quantity", 1) or 1),
        "items": [],
        "payment_method": order_details.get("payment_method", "bank_transfer"),
        "delivery_method": "social_service",
        "email": "N/A",
        "coupon_used": order_details.get("coupon_code") or "",
        "is_social_source_service": True,
        "ctt_supplier_order_id": supplier_result.get("supplier_order_id") or "",
        "ctt_supplier_status": supplier_result.get("supplier_status") or "Pending",
        "ctt_supplier_quantity": int(supplier_result.get("supplier_quantity", 0) or 0),
        "ctt_target_link": supplier_result.get("target_link") or "",
        "ctt_comments": supplier_result.get("comments") or "",
    }
    if supplier_result.get("supplier_charge"):
        completed_order["ctt_supplier_charge"] = supplier_result.get("supplier_charge")
    if supplier_result.get("supplier_remains"):
        completed_order["ctt_supplier_remains"] = supplier_result.get("supplier_remains")
    if supplier_result.get("supplier_start_count"):
        completed_order["ctt_supplier_start_count"] = supplier_result.get("supplier_start_count")
    return completed_order


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
            if details.get("provider") == "binance_pay":
                try:
                    await close_binance_pay_order(
                        order_code=code,
                        prepay_id=str(details.get("binance_prepay_id") or ""),
                    )
                except Exception as e:
                    logger.exception(f"Cannot close expired Binance order {code}: {e}", exc_info=e)

            refund_text = ""
            balance_used = details.get('balance_used', 0)
            if balance_used > 0:
                user_id = details['user_id']
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
                reply_markup = create_back_button_menu("<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> Tạo đơn mới", "muahang_start")
            else:
                caption = (
                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>ĐƠN HÀNG ĐÃ HẾT HẠN</b> <tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>\n\n"
                    f"Đơn hàng cho email <b>{details.get('email', 'N/A')}</b> đã hết hạn thanh toán.\n"
                    f"Vui lòng tạo đơn mới nếu bạn vẫn muốn mua.{refund_text}"
                )
                reply_markup = create_back_button_menu("<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> Tạo đơn mới", "muahang_start")

            if details.get('message_id'):
                if details.get("message_kind") == "text":
                    await context.bot.edit_message_text(
                        chat_id=details['user_id'],
                        message_id=details['message_id'],
                        text=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                else:
                    await context.bot.edit_message_caption(
                        chat_id=details['user_id'],
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


async def _scan_usdt_bep20_payments(synthetic_transactions: list) -> None:
    from app.integrations.payments_core import fetch_usdt_bep20_transfers, is_usdt_bep20_enabled
    if not is_usdt_bep20_enabled():
        return
    usdt_pending_orders = []
    for order_code, order_details in await pending_items_snapshot():
        if order_details.get("provider") not in {"usdt_trc20", "usdt_multi"} or order_details.get("status") != "pending_payment":
            continue
        expected_amount = int(order_details.get("amount", 0) or 0)
        created_ts = float(order_details.get("timestamp") or order_details.get("time") or 0)
        if expected_amount <= 0 or created_ts <= 0:
            continue
        usdt_pending_orders.append((order_code, order_details, expected_amount, int(created_ts * 1000)))

    if not usdt_pending_orders:
        return
    start_timestamp_ms = max(0, min(item[3] for item in usdt_pending_orders) - 60_000)
    try:
        transfers = await fetch_usdt_bep20_transfers(
            USDT_BEP20_WALLET_ADDRESS,
            start_timestamp_ms=start_timestamp_ms,
        )
        matched_hashes = set()
        for order_code, order_details, expected_amount, created_ts_ms in sorted(usdt_pending_orders, key=lambda item: item[3]):
            expire_ts_ms = created_ts_ms + (ORDER_EXPIRATION_SECONDS * 1000)
            for transfer in transfers:
                tx_hash = str(transfer.get("hash") or "").strip()
                if not tx_hash or tx_hash in matched_hashes or db_check_tx_exists(f"BEP20:{tx_hash}"):
                    continue
                tx_amount = str(transfer.get("amount_display") or "").strip()
                expected_text = str(order_details.get("usdt_trc20_amount") or "").strip()
                try:
                    if Decimal(tx_amount) != Decimal(expected_text):
                        continue
                except (ValueError, ArithmeticError):
                    continue
                tx_timestamp = int(transfer.get("block_timestamp") or transfer.get("timestamp") or transfer.get("block_ts") or 0)
                if tx_timestamp and tx_timestamp < created_ts_ms:
                    continue
                if tx_timestamp and tx_timestamp > expire_ts_ms + (BANK_CHECK_INTERVAL_SECONDS * 1000):
                    continue
                matched_hashes.add(tx_hash)
                synthetic_transactions.append({
                    "transactionID": f"BEP20:{tx_hash}",
                    "description": order_code,
                    "amount": expected_amount,
                })
                break
    except Exception as e:
        logger.exception(f"USDT BEP20 scan failed: {e}", exc_info=e)


async def _scan_binance_pay_payments(synthetic_transactions: list) -> None:
    if not is_binance_pay_enabled():
        return
    for order_code, order_details in await pending_items_snapshot():
        if order_details.get("provider") != "binance_pay" or order_details.get("status") != "pending_payment":
            continue
        expected_amount = int(order_details.get("amount", 0) or 0)
        if expected_amount <= 0:
            continue
        try:
            binance_data = await query_binance_pay_order(
                order_code=order_code,
                prepay_id=str(order_details.get("binance_prepay_id") or ""),
            )
            order_status = str(binance_data.get("status") or "").upper()
            if order_status == "PAID":
                tx_ref = binance_data.get("transactionId") or order_details.get("binance_prepay_id") or order_code
                synthetic_transactions.append({
                    "transactionID": f"BINPAY:{tx_ref}",
                    "description": order_code,
                    "amount": expected_amount,
                })
        except Exception as e:
            logger.exception(f"Binance Pay query failed for {order_code}: {e}", exc_info=e)


async def _scan_binance_pay_id_payments(synthetic_transactions: list) -> None:
    from app.integrations.payments_core import fetch_binance_pay_id_transactions, is_binance_pay_id_enabled
    if not is_binance_pay_id_enabled():
        return
    pending = []
    for order_code, order_details in await pending_items_snapshot():
        if order_details.get("provider") not in {"binance_pay_id", "usdt_multi"} or order_details.get("status") != "pending_payment":
            continue
        expected_amount = int(order_details.get("amount", 0) or 0)
        created_ts = float(order_details.get("timestamp") or order_details.get("time") or 0)
        if expected_amount > 0 and created_ts > 0:
            pending.append((order_code, order_details, expected_amount, int(created_ts * 1000)))
    if not pending:
        return

    start_timestamp_ms = max(0, min(item[3] for item in pending) - 60_000)
    try:
        transfers = await fetch_binance_pay_id_transactions(start_timestamp_ms=start_timestamp_ms)
        matched_hashes = set()
        for order_code, order_details, expected_amount, created_ts_ms in sorted(pending, key=lambda item: item[3]):
            expire_ts_ms = created_ts_ms + (ORDER_EXPIRATION_SECONDS * 1000)
            for transfer in transfers:
                tx_hash = str(transfer.get("transactionId") or "").strip()
                if not tx_hash or tx_hash in matched_hashes or db_check_tx_exists(f"BINPAYID:{tx_hash}"):
                    continue
                try:
                    if Decimal(str(transfer.get("amount") or 0)) != Decimal(str(order_details.get("usdt_trc20_amount") or 0)):
                        continue
                except (TypeError, ValueError, ArithmeticError):
                    continue
                tx_timestamp = int(transfer.get("transactionTime") or 0)
                if tx_timestamp and (tx_timestamp < created_ts_ms or tx_timestamp > expire_ts_ms + (BANK_CHECK_INTERVAL_SECONDS * 1000)):
                    continue
                matched_hashes.add(tx_hash)
                synthetic_transactions.append({
                    "transactionID": f"BINPAYID:{tx_hash}",
                    "description": order_code,
                    "amount": expected_amount,
                })
                break
    except Exception as e:
        logger.exception(f"Binance Pay ID scan failed: {e}", exc_info=e)


async def _scan_binance_spot_payments(synthetic_transactions: list) -> None:
    from app.integrations.payments_core import is_binance_spot_enabled, fetch_binance_spot_deposits
    if not is_binance_spot_enabled():
        return
    usdt_pending_orders = []
    for order_code, order_details in await pending_items_snapshot():
        if order_details.get("provider") not in {"usdt_trc20", "usdt_multi"} or order_details.get("status") != "pending_payment":
            continue
        expected_amount = int(order_details.get("amount", 0) or 0)
        expected_quant = str(order_details.get("usdt_trc20_amount_quant") or "").strip()
        created_ts = float(order_details.get("timestamp") or order_details.get("time") or 0)
        if expected_amount <= 0 or not expected_quant or created_ts <= 0:
            continue
        usdt_pending_orders.append((order_code, order_details, expected_amount, expected_quant, int(created_ts * 1000)))

    if not usdt_pending_orders:
        return
    start_timestamp_ms = max(0, min(item[4] for item in usdt_pending_orders) - 60_000)
    try:
        deposits = await fetch_binance_spot_deposits(start_timestamp_ms=start_timestamp_ms)
        logger.debug(f"DINO CRON (Binance Spot): Tìm thấy {len(deposits)} giao dịch nạp từ {start_timestamp_ms}")
        if deposits:
            logger.debug(f"DEBUG Binance Spot Data: {[d.get('txId') + ' (' + str(d.get('amount')) + ' ' + d.get('coin') + ' status:' + str(d.get('status')) + ')' for d in deposits[:3]]}...")
        matched_hashes = set()
        for order_code, order_details, expected_amount, expected_quant, created_ts_ms in sorted(usdt_pending_orders, key=lambda item: item[4]):
            expire_ts_ms = created_ts_ms + (ORDER_EXPIRATION_SECONDS * 1000)
            for dep in deposits:
                # 1 = success
                if int(dep.get("status", 0)) != 1:
                    continue
                tx_id = str(dep.get("txId") or "").strip()
                if not tx_id or tx_id in matched_hashes or db_check_tx_exists(f"BINSPOT:{tx_id}"):
                    continue
                
                # Verify exact amount matches expected quote
                tx_amount = str(dep.get("amount") or "").strip()
                expected_text = str(order_details.get("usdt_trc20_amount") or "").strip()
                
                try:
                    if Decimal(tx_amount) != Decimal(expected_text):
                        continue
                except (ValueError, ArithmeticError):
                    continue
                    
                tx_timestamp = int(dep.get("insertTime") or 0)
                if tx_timestamp and tx_timestamp < created_ts_ms:
                    continue
                if tx_timestamp and tx_timestamp > expire_ts_ms + (BANK_CHECK_INTERVAL_SECONDS * 1000):
                    continue
                    
                matched_hashes.add(tx_id)
                synthetic_transactions.append({
                    "transactionID": f"BINSPOT:{tx_id}",
                    "description": order_code,
                    "amount": expected_amount,
                })
                break
    except Exception as e:
        logger.exception(f"Binance Spot scan failed: {e}", exc_info=e)


async def _scan_sepay_payments(synthetic_transactions: list) -> None:
    """SePay: rut het giao dich webhook da nhan (duong chinh, gan tuc thi),
    roi doi soat lai bang poll API (du phong khi webhook bi mat/chua bat).

    Ca hai deu nap dung dang {"transactionID","description","amount"} vao
    `synthetic_transactions`, dung chung pipeline khop-don/cong-tien ben duoi
    (check_payment_job) - trung tx_id giua webhook va poll van chi cong 1 lan
    nho db_claim_transaction() khoa theo transactionID.
    """
    from app.integrations.sepay_api import sepay_webhook_inbox, sepay_fetch_history

    if not ENABLE_PAYMENT_SEPAY:
        return

    # 1) Webhook inbox - rut het (khong co await xen giua doc/xoa nen an toan).
    if sepay_webhook_inbox:
        drained, sepay_webhook_inbox[:] = list(sepay_webhook_inbox), []
        synthetic_transactions.extend(drained)

    # 2) Poll du phong - chi chay khi co cau hinh SEPAY_API_TOKEN.
    try:
        polled = await sepay_fetch_history()
        for tx in polled:
            if db_check_tx_exists(tx["transactionID"]):
                continue
            synthetic_transactions.append(tx)
    except Exception as e:
        logger.warning(f"SePay poll scan failed: {e}")


async def check_payment_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    global _bank_api_fail_count, _bank_api_last_alert_time
    global _bank_api_last_check_time, _bank_api_last_status, _bank_api_last_error, _bank_api_last_tx_count, _bank_api_total_checks, _bank_api_total_success
    data_changed = False
    current_time = time.time()

    data_changed |= await _cleanup_expired_pending_orders(context, current_time)
    data_changed |= _cleanup_expired_api_deposits(current_time)

    if not pending_orders and not pending_api_deposits:
        if data_changed:
            await save_data()
        logger.debug("DINO CRON: Không có đơn chờ, bỏ qua gọi API bank.")
        return

    logger.debug(f"DINO CRON: Bắt đầu quét... Đơn chờ: {len(pending_orders)} | API Nạp chờ: {len(pending_api_deposits)}")
    synthetic_transactions: list = []
    await _scan_usdt_bep20_payments(synthetic_transactions)
    await _scan_binance_pay_id_payments(synthetic_transactions)
    await _scan_binance_pay_payments(synthetic_transactions)
    await _scan_binance_spot_payments(synthetic_transactions)
    await _scan_sepay_payments(synthetic_transactions)

    try:
        # Strip whitespace to prevent copy-paste errors
        clean_password = API_PASSWORD.strip()
        clean_account = BANK_ACCOUNT_NUMBER.strip()
        login_username = os.getenv("BANK_LOGIN_USERNAME", clean_account).strip()
        
        transactions = list(synthetic_transactions)

        if not ENABLE_PAYMENT_MBBANK:
            api_data = {"transactions": []}
            api_key_info = ["transactions"]
        else:
         try:
            import mbbank
            import datetime
            import asyncio
            
            def _fetch_mb_history():
                mb = mbbank.MBBank(username=login_username, password=clean_password)
                now = datetime.datetime.now()
                return mb.getTransactionAccountHistory(accountNo=clean_account, from_date=now - datetime.timedelta(days=2), to_date=now)
                
            history = await asyncio.to_thread(_fetch_mb_history)
            
            # map them to the same format
            bank_txs = []
            tx_list = getattr(history, 'transactionHistoryList', getattr(history, 'transactionHistoryList', []))
            if not tx_list and isinstance(history, dict):
                tx_list = history.get('transactionHistoryList', [])
                
            import warnings
            for tx in tx_list:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    if isinstance(tx, dict):
                        tx_dict = tx
                    elif hasattr(tx, 'model_dump'):
                        tx_dict = tx.model_dump()
                    elif hasattr(tx, 'dict'):
                        tx_dict = tx.dict()
                    else:
                        tx_dict = tx.__dict__
                    
                tx_id = tx_dict.get('refNo') or tx_dict.get('transactionId') or tx_dict.get('posappId') or ""
                desc = tx_dict.get('description', '')
                credit = tx_dict.get('creditAmount', 0)
                
                if int(credit) > 0:
                    bank_txs.append({
                        "transactionID": str(tx_id),
                        "description": str(desc),
                        "amount": int(credit)
                    })
            api_data = {"transactions": bank_txs}
            api_key_info = ["transactions"]

         except Exception as bank_err:
            bank_error_msg = str(bank_err)
            is_temporary_bank_error = True
            log_bank_error = logger.warning if is_temporary_bank_error else logger.error
            err_parts = [bank_error_msg]
            log_bank_error(
                f"❌ Bank API request failed: {' | '.join(err_parts)}"
            )
            api_data = {
                "msg": " | ".join(err_parts),
                "_temporary_bank_api_error": is_temporary_bank_error,
            }
            api_key_info = []
            _bank_api_last_status = "error"
            _bank_api_last_error = bank_error_msg[:240]
        
        # Log full response if pending orders exist to debug
        if pending_orders or pending_api_deposits:
             logger.debug(f"DEBUG: API Response keys: {str(api_key_info)[:30]}...")

        # Check for API Error
        if "transactions" not in api_data:
            msg = api_data.get("msg", "Unknown Error")
            is_temporary_bank_error = bool(api_data.get("_temporary_bank_api_error"))
            log_bank_api_error = logger.warning if is_temporary_bank_error else logger.error
            log_bank_api_error(f"❌ LỖI API BANK: {msg} | Keys: {str(api_key_info)[:30]}...")
            # Notify Admin if critical - with backoff to prevent spam
            _bank_api_fail_count += 1
            now_ts = time.time()
            if len(pending_orders) > 0 and (_bank_api_fail_count <= 3 or (now_ts - _bank_api_last_alert_time) >= 600):
                 _bank_api_last_alert_time = now_ts
                 await context.bot.send_message(
                     ADMIN_USER_ID,
                     f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>LỖI KẾT NỐI BANK API</b> (lần {_bank_api_fail_count})\n\nServer trả về: {msg}",
                     parse_mode=ParseMode.HTML
                 )
            if not transactions:
                return
        else:
            _bank_api_fail_count = 0
            tx_count_now = len(api_data.get("transactions", []))
            transactions.extend(api_data.get("transactions", []))
            logger.debug(f"DINO CRON: Tìm thấy {tx_count_now} giao dịch từ API.")
            _bank_api_last_status = "ok"
            _bank_api_last_error = ""
            _bank_api_last_tx_count = tx_count_now
            _bank_api_total_success += 1
        _bank_api_last_check_time = time.time()
        _bank_api_total_checks += 1

        if synthetic_transactions:
            logger.info(f"DINO CRON: Tìm thấy {len(synthetic_transactions)} giao dịch thanh toán đã xác nhận từ crypto/bank scan.")

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

            if not (secret_order_code or match_order or api_deposit_reference):
                continue
            if not db_claim_transaction(tx_id):
                continue

            if secret_order_code or match_order: 
                # === XỬ LÝ MUA LINK / QR BANK ===
                order_code = str(secret_order_code) if secret_order_code else f"ICLD{match_order.group(1)}"
                logger.info(f"DINO CRON: Phát hiện mã đơn {order_code} trong giao dịch {tx_id}")

                order_details = await pending_get(order_code)
                if order_details:
                    expected_amount, actual_amount = int(order_details["amount"]), int(amount)
                    
                    logger.info(f"CRON: So sánh tiền - Mong đợi: {expected_amount}, Thực tế: {actual_amount}")

                    if actual_amount == expected_amount:
                        # Handle Store Product vs iCloud Package
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

                            if p.get('is_social_source_service') or order_details.get('is_social_source_service'):
                                balance_used_order = int(order_details.get("balance_used", 0) or 0)
                                total_paid_social = actual_amount + balance_used_order
                                await context.bot.send_message(
                                    order_details['user_id'],
                                    f"{E_SUCCESS} <b>THANH TOÁN THÀNH CÔNG!</b>\n\n"
                                    f"{E_TAG} Sản phẩm: <b>{p['name']}</b>\n"
                                    f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> Số lượng: {qty}\n"
                                    f"{E_TAG} Thanh toán: {actual_amount:,} VNĐ\n\n"
                                    f"{E_LOADING} <b>Đang tạo đơn social trên nguồn...</b>",
                                    parse_mode=ParseMode.HTML,
                                )

                                supplier_result = await ctt_submit_local_service_order(
                                    p,
                                    qty,
                                    _ctt_inputs_from_pending_order(order_details),
                                )

                                if not supplier_result.get("success"):
                                    refund_amount = _get_store_order_total_refund(order_details, actual_amount)
                                    current_balance = int(user_data_db.get(str(order_details['user_id']), {}).get('balance', 0) or 0)
                                    new_balance = current_balance + refund_amount
                                    db_update_balance(order_details['user_id'], new_balance, reason=f"Refund: Social supplier error {p['name']}")
                                    await record_wallet_refund(
                                        context,
                                        order_code=order_code,
                                        user_id=order_details['user_id'],
                                        amount=refund_amount,
                                        product_name=p.get('name', 'Dịch vụ social'),
                                        reason="Lỗi nguồn cung cấp dịch vụ social",
                                        order_data=order_details,
                                    )

                                    await context.bot.send_message(
                                        order_details['user_id'],
                                        f"❌ <b>LỖI NGUỒN CUNG CẤP DỊCH VỤ SOCIAL</b>\n\n"
                                        f"Đơn social không thể tạo trên nguồn vào lúc này.\n"
                                        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã hoàn <b>{refund_amount:,} VNĐ</b> vào ví Bot.\n\n"
                                        f"Mã đơn: <code>{order_code}</code>",
                                        parse_mode=ParseMode.HTML,
                                    )
                                    await safe_send_admin(
                                        context.bot,
                                        f"{E_SOS} <b>SOCIAL_SOURCE PAYMENT ORDER FAILED</b>\n"
                                        f"{E_ID} Đơn: <code>{order_code}</code>\n"
                                        f"{E_USER} User: <code>{order_details['user_id']}</code>\n"
                                        f"{E_TAG} SP: {html.escape(p['name'])} x{qty}\n"
                                        f"{E_TAG} Hoàn ví: {refund_amount:,} VNĐ\n"
                                        f"{E_ERROR} Lỗi: <code>{html.escape(str(supplier_result.get('error') or 'unknown_error'))}</code>",
                                    )
                                    await pending_pop(order_code)
                                    db_add_tx(tx_id)
                                    data_changed = True
                                    continue

                                completed_order = _build_ctt_completed_order(
                                    order_code,
                                    order_details,
                                    p,
                                    total_paid_social,
                                    current_time,
                                    supplier_result,
                                )

                                coupon_code_used = order_details.get("coupon_code")
                                if coupon_code_used:
                                    coupon_code_used = coupon_code_used.upper()
                                    if coupon_code_used in coupons:
                                        coupons[coupon_code_used]['used'] = coupons[coupon_code_used].get('used', 0) + 1

                                db_add_order(completed_order)
                                await _mark_pending_payment_message_completed(context, order_details)
                                await pending_pop(order_code)
                                db_add_tx(tx_id)
                                data_changed = True
                                await save_critical_tables(HISTORY_FILE, PROCESSED_TX_FILE, PENDING_ORDERS_FILE, USERS_FILE)

                                await context.bot.send_message(
                                    order_details['user_id'],
                                    f"{E_SUCCESS} <b>ĐƠN SOCIAL ĐÃ TẠO THÀNH CÔNG</b>\n\n"
                                    f"{E_TAG} Sản phẩm: {html.escape(str(p['name']))}\n"
                                    f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> Số lượng: {qty}\n"
                                    f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> Mã đơn: <code>{html.escape(str(completed_order.get('order_code') or order_code))}</code>\n"
                                    f"<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> Tổng đơn vị nguồn: {int(supplier_result.get('supplier_quantity', 0) or 0):,}\n"
                                    f"<tg-emoji emoji-id=\"5231489647946768652\">🔗</tg-emoji> Target: <code>{html.escape(str(supplier_result.get('target_link') or 'N/A'))}</code>\n"
                                    f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> Mã supplier: <code>{html.escape(str(supplier_result.get('supplier_order_id') or ''))}</code>\n"
                                    f"{E_STAT} Trạng thái nguồn: {html.escape(str(supplier_result.get('supplier_status') or 'Pending'))}",
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=create_success_menu(),
                                )

                                await send_live_order_notification(
                                    context,
                                    order_details.get("full_name", "Khách hàng"),
                                    total_paid_social,
                                    product_name=p['name'],
                                    quantity=qty,
                                    order_code=completed_order.get("order_code") or order_code,
                                )
                                await notify_admin_store_order(
                                    context,
                                    order_code=completed_order.get("order_code") or order_code,
                                    user_id=order_details['user_id'],
                                    full_name=order_details.get("full_name"),
                                    username=order_details.get("username"),
                                    product_name=p['name'],
                                    quantity=qty,
                                    amount=total_paid_social,
                                    payment_method=order_details.get("payment_method", "bank_transfer"),
                                    items=[],
                                    delivery_method="social_service",
                                    is_resell=False,
                                )
                                continue
                            
                            # ===== SUPPLIER_SOURCE AUTO RESELL =====
                            # Nếu là sản phẩm resell từ SupplierSource, mua từ API thay vì lấy từ stock local
                            if p.get('is_supplier_source_resell'):
                                supplier_source_product_id = p.get('supplier_source_product_id')
                                supplier_source_variant_id = p.get('supplier_source_variant_id')
                                
                                await context.bot.send_message(
                                    order_details['user_id'],
                                    f"{E_SUCCESS} <b>THANH TOÁN THÀNH CÔNG!</b>\n\n"
                                    f"{E_TAG} Sản phẩm: <b>{p['name']}</b>\n"
                                    f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> Số lượng: {qty}\n"
                                    f"{E_TAG} Thanh toán: {actual_amount:,} VNĐ\n\n"
                                    f"{E_LOADING} <b>Đang lấy tài khoản từ hệ thống...</b>",
                                    parse_mode=ParseMode.HTML
                                )
                                
                                if not p.get('resell_enabled', True):
                                    refund_amount = _get_store_order_total_refund(order_details, actual_amount)
                                    current_balance = int(user_data_db.get(str(order_details['user_id']), {}).get('balance', 0) or 0)
                                    db_update_balance(order_details['user_id'], current_balance + refund_amount, reason=f"Refund: Resell disabled {p['name']}")
                                    await record_wallet_refund(
                                        context,
                                        order_code=order_code,
                                        user_id=order_details['user_id'],
                                        amount=refund_amount,
                                        product_name=p.get('name', 'Sản phẩm'),
                                        reason="Sản phẩm tạm tắt resell",
                                        order_data=order_details,
                                    )
                                    await context.bot.send_message(
                                        order_details['user_id'],
                                        f"❌ <b>SẢN PHẨM ĐANG TẠM TẮT RESELL</b>\n\n"
                                        f"Đơn <code>{order_code}</code> đã được hoàn <b>{refund_amount:,} VNĐ</b> vào ví Bot.",
                                        parse_mode=ParseMode.HTML,
                                    )
                                    await pending_pop(order_code)
                                    db_add_tx(tx_id)
                                    data_changed = True
                                    continue
                                
                                # Gọi API nguồn ngoài để mua sản phẩm
                                supplier_source_result = await supplier_create_order(p, qty)
                                
                                if not supplier_source_result.get("success"):
                                    # Lỗi API - Thông báo Admin và hoàn tiền
                                    error = supplier_source_result.get("error", "Unknown")
                                    
                                    balance_used_order = int(order_details.get("balance_used", 0) or 0)
                                    refund_amount = _get_store_order_total_refund(order_details, actual_amount)

                                    # Auto refund vao balance, including the wallet portion already deducted.
                                    current_balance = int(user_data_db.get(str(order_details['user_id']), {}).get('balance', 0) or 0)
                                    new_bal = current_balance + refund_amount
                                    db_update_balance(order_details['user_id'], new_bal, reason=f"Refund: Supplier API Error {p['name']}")
                                    await record_wallet_refund(
                                        context,
                                        order_code=order_code,
                                        user_id=order_details['user_id'],
                                        amount=refund_amount,
                                        product_name=p.get('name', 'Sản phẩm'),
                                        reason=f"Lỗi nguồn cung cấp: {error}",
                                        order_data=order_details,
                                    )
                                    refund_breakdown_line = ""
                                    if balance_used_order > 0:
                                        refund_breakdown_line = (
                                            f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> "
                                            f"Tổng hoàn thực tế: <b>{refund_amount:,} VNĐ</b> "
                                            f"(gồm {balance_used_order:,} VNĐ đã trừ từ ví)\n"
                                        )
                                        
                                    await context.bot.send_message(
                                        order_details['user_id'],
                                        f"❌ <b>LỖI HỆ THỐNG NGUỒN CUNG CẤP</b>\n\n"
                                        f"Rất xin lỗi, sản phẩm hiện tại tạm không thể giao dịch (có thể do hết hàng hoặc kẹt mạng).\n"
                                        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>Đã tự động hoàn {refund_amount:,} VNĐ</b> vào số dư ví Bot của bạn.\n\n"
                                        f"Mã đơn: <code>{order_code}</code>\n"
                                        f"Bạn có thể dùng ví để mua lại sau, hoặc mua mặt hàng khác.",
                                        parse_mode=ParseMode.HTML
                                    )
                                    if refund_breakdown_line:
                                        await context.bot.send_message(
                                            order_details['user_id'],
                                            refund_breakdown_line,
                                            parse_mode=ParseMode.HTML,
                                        )
                                    await safe_send_admin(
                                        context.bot,
                                        f"{E_SOS} <b>LỖI API NGUỒN CUNG CẤP KHI THANH TOÁN QR/USDT</b>\n\n"
                                        f"{E_TAG} SP: {html.escape(p['name'])}\n"
                                        f"{E_ID} Đơn: <code>{order_code}</code>\n"
                                        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> User: <code>{order_details['user_id']}</code>\n"
                                        f"{E_TAG} Tiền: {actual_amount:,} VNĐ\n\n"
                                        f"{E_LIMIT} Lỗi: <code>{html.escape(str(error))}</code>\n\n"
                                        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> ĐÃ TỰ ĐỘNG HOÀN VÀO SỐ DƯ VÍ KHÁCH!",
                                    )
                                    if balance_used_order > 0:
                                        await safe_send_admin(
                                            context.bot,
                                            f"{E_TAG} Hoàn thực tế: {refund_amount:,} VNĐ = CK {actual_amount:,} VNĐ + Ví {balance_used_order:,} VNĐ\n"
                                            f"{E_ID} Đơn: <code>{order_code}</code>",
                                        )
                                    await pending_pop(order_code)
                                    db_add_tx(tx_id)
                                    data_changed = True
                                    continue
                                
                                # Parse delivered content từ nguồn ngoài
                                supplier_source_orders = supplier_source_result.get("data", [])
                                items_bought = []
                                
                                for dm_order in supplier_source_orders:
                                    delivered = dm_order.get("deliveredContent")
                                    if delivered:
                                        logger.info(f"DEBUG SUPPLIER CONTENT TYPE: {type(delivered).__name__}")
                                        items_bought.extend(normalize_delivered_items(delivered))
                                
                                # Nếu chưa có content, thử lấy order details
                                if not items_bought:
                                    for dm_order in supplier_source_orders:
                                        dm_order_id = dm_order.get("id")
                                        if dm_order_id:
                                            detail = await supplier_get_order_details(p, dm_order_id)
                                            if detail.get("success"):
                                                dd = detail.get("data", {})
                                                delivered = dd.get("deliveredContent")
                                                if delivered:
                                                    items_bought.extend(normalize_delivered_items(delivered))
                                
                                if not items_bought:
                                    # Vẫn không có content
                                    await context.bot.send_message(
                                        order_details['user_id'],
                                        f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>ĐANG XỬ LÝ...</b>\n\n"
                                        f"Đơn hàng đã tạo nhưng đang chờ giao hàng từ nguồn.\n"
                                        f"Admin sẽ gửi tài khoản sớm nhất.\n\n"
                                        f"Mã đơn: <code>{order_code}</code>",
                                        parse_mode=ParseMode.HTML
                                    )
                                    await context.bot.send_message(
                                        ADMIN_USER_ID,
                                        f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>NGUỒN CUNG CẤP CHƯA TRẢ HÀNG</b>\n\n"
                                        f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> SP: {p['name']}\n"
                                        f"<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> Đơn: <code>{order_code}</code>\n"
                                        f"Nguồn cung cấp chưa trả content. Cần check manual.",
                                        parse_mode=ParseMode.HTML
                                    )
                                    await _mark_pending_payment_message_completed(context, order_details)
                                    await pending_pop(order_code)
                                    db_add_tx(tx_id)
                                    data_changed = True
                                    continue
                                
                                # Thành công! Gửi cho khách (code tiếp tục bên dưới với items_bought)
                                # Không cần xử lý stock local vì đã lấy từ API
                                
                                purchase_date = datetime.datetime.fromtimestamp(current_time).strftime('%d/%m/%Y %H:%M:%S')
                                product_description_txt = format_product_description_for_txt(p)
                                
                                file_content = "="*60 + "\n"
                                file_content += "           THÔNG TIN ĐƠN HÀNG\n"
                                file_content += "="*60 + "\n\n"
                                file_content += f"<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> MÃ ĐƠN HÀNG    : {order_code}\n"
                                file_content += f"<tg-emoji emoji-id=\"5413879192267805083\">📅</tg-emoji> NGÀY MUA       : {purchase_date}\n"
                                file_content += f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> SẢN PHẨM       : {p['name']}\n"
                                file_content += f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> SỐ LƯỢNG       : {qty}\n"
                                file_content += f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> THANH TOÁN     : {actual_amount:,} VNĐ\n"
                                if product_description_txt:
                                    file_content += f"\nMÔ TẢ SẢN PHẨM:\n{product_description_txt}\n\n"
                                file_content += f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> THỜI HẠN       : {p.get('duration', 'N/A')}\n"
                                file_content += f"<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> BẢO HÀNH       : {p.get('warranty', 'Không')}\n"
                                file_content += "\n" + "="*60 + "\n"
                                file_content += "           TÀI KHOẢN CỦA BẠN\n"
                                file_content += "="*60 + "\n\n"
                                
                                for i, item in enumerate(items_bought, 1):
                                    file_content += f"[{i}] {item}\n"
                                
                                file_content += "\n" + "="*60 + "\n"
                                file_content += "LƯU Ý: Vui lòng đổi mật khẩu sau khi đăng nhập!\n"
                                file_content += "="*60 + "\n"
                                
                                delivery_result = await deliver_items_as_txt(
                                    context,
                                    order_details['user_id'],
                                    order_code,
                                    items_bought,
                                    file_content=file_content,
                                    file_prefix="DonHang",
                                    caption_html=f"<tg-emoji emoji-id=\"5854908544712707500\">📁</tg-emoji> <b>THÔNG TIN TÀI KHOẢN</b>\n\nMã đơn: <code>{order_code}</code>\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> {p['name']} x{qty}",
                                )
                                delivery_status = OrderStatus.COMPLETED.value if delivery_result.get("delivered") else "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Chờ gửi thủ công (Nguồn ngoài)"
                                if not delivery_result.get("delivered"):
                                    await safe_send_message(
                                        context,
                                        order_details['user_id'],
                                        f"❌ Có lỗi khi gửi tài khoản cho đơn <code>{order_code}</code>.\n"
                                        "Admin đã nhận cảnh báo và sẽ gửi thủ công sớm nhất.",
                                        parse_mode=ParseMode.HTML,
                                    )
                                    await safe_send_admin(
                                        context.bot,
                                        f"{E_SOS} <b>DELIVERY FAILED (NGUỒN NGOÀI)</b>\n"
                                        f"{E_ID} Đơn: <code>{order_code}</code>\n"
                                        f"{E_USER} User: <code>{order_details['user_id']}</code>\n"
                                        f"{E_TAG} SP: {html.escape(p['name'])} x{qty}\n"
                                        f"{E_STAT} Fallback gửi: {delivery_result.get('sent_items', 0)}/{len(items_bought)} items\n"
                                        f"{E_ERROR} Errors: <code>{html.escape(' | '.join(delivery_result.get('errors', [])[-3:]) or 'n/a')}</code>",
                                    )
                                
                                # Log lịch sử
                                order_record = {
                                    'order_code': order_code,
                                    'timestamp': current_time,
                                    'product': p['name'],
                                    'product_name': p['name'],
                                    'quantity': qty,
                                    'amount': actual_amount,
                                    'user_id': order_details['user_id'],
                                    'items': items_bought,
                                    'status': delivery_status,
                                    'is_supplier_source_resell': True,
                                    'payment_method': order_details.get('payment_method', 'bank_transfer'),
                                    'delivery_method': delivery_result.get("method", "failed"),
                                }
                                db_add_order(order_record, schedule_save=False)
                                
                                await _mark_pending_payment_message_completed(context, order_details)
                                await pending_pop(order_code)
                                db_add_tx(tx_id)
                                data_changed = True
                                await save_critical_tables(HISTORY_FILE, PROCESSED_TX_FILE, PRODUCTS_FILE, PENDING_ORDERS_FILE)
                                
                                # Thông báo Admin (sau khi đã save data an toàn)
                                try:
                                    supplier_source_cost = p.get('supplier_source_price', 0) * qty
                                    await context.bot.send_message(
                                        ADMIN_USER_ID,
                                        f"{E_SUCCESS} <b>ĐƠN RESELL THÀNH CÔNG!</b>\n\n"
                                        f"{E_TAG} SP: {p['name']} x{qty}\n"
                                        f"{E_ID} Mã: <code>{order_code}</code>\n"
                                        f"{E_TAG} Bán: {actual_amount:,} VNĐ\n"
                                        f"<tg-emoji emoji-id=\"5863724849851011383\">💵</tg-emoji> Gốc: {supplier_source_cost:,} VNĐ\n"
                                        f"{E_STAT} Lời: {actual_amount - supplier_source_cost:,} VNĐ",
                                        parse_mode=ParseMode.HTML
                                    )
                                except (TelegramError, ValueError, KeyError, AttributeError) as admin_err:
                                    logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Supplier admin notification failed: {admin_err}")
                                continue
                            
                            # ===== END SUPPLIER_SOURCE AUTO RESELL =====
                            
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
                            
                            purchase_date = datetime.datetime.fromtimestamp(current_time).strftime('%d/%m/%Y %H:%M:%S')
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
                                reply_markup=create_success_menu(),
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
                                    reply_markup=create_success_menu(),
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
                        
                        # Existing iCloud Logic
                        elif order_details.get("type") != "store_product":
                            user_id, email = order_details["user_id"], order_details["email"]
                            completed_order = { "user_id": user_id, "order_code": order_code, "email": email, "amount": actual_amount, "coupon_used": order_details.get("coupon_code"), "link": "", "timestamp": current_time, "full_name": order_details.get("full_name"), "username": order_details.get("username"), "type": "icloud", "product_name": "iCloud 2TB", "payment_method": order_details.get("payment_method", "bank_transfer") }
                            
                            async with global_stock_lock:
                                if available_links:
                                    link_to_send = next(iter(available_links))
                                    # REMOVED available_links.discard(link_to_send) for '1-Link Mode'
                                    completed_order.update({"link": link_to_send, "status": OrderStatus.COMPLETED.value})
                                    has_link = True
                                else:
                                    completed_order["status"] = OrderStatus.PENDING_LINK.value
                                    has_link = False

                            if has_link:
                                email_sent, email_error = await send_activation_email(
                                    email,
                                    f"Link kích hoạt gói iCloud 2TB - {order_code}",
                                    order_details.get("full_name", "bạn"),
                                    link_to_send,
                                )
                                if email_sent:
                                    await context.bot.send_message(
                                        user_id,
                                        f"{E_SUCCESS} <b>THANH TOÁN THÀNH CÔNG</b> {E_SUCCESS}\n\n"
                                        f"Cảm ơn bạn! Link kích hoạt đã được gửi đến email <b>{email}</b>.",
                                        parse_mode=ParseMode.HTML,
                                        reply_markup=create_success_menu(),
                                    )
                                else:
                                    await context.bot.send_message(
                                        user_id,
                                        f"{E_SUCCESS} <b>THANH TOÁN THÀNH CÔNG</b> {E_SUCCESS}\n\n"
                                        f"Đơn của bạn đã hoàn tất nhưng gửi email kích hoạt thất bại.\n"
                                        f"Vui lòng liên hệ Admin và cung cấp mã đơn <code>{order_code}</code>.",
                                        parse_mode=ParseMode.HTML,
                                        reply_markup=create_success_menu(),
                                    )
                                
                                await send_live_order_notification(context, order_details.get("full_name", "Khách hàng"), actual_amount, product_name="iCloud 2TB", quantity=1, order_code=order_code)
                                
                                try:
                                    email_status = "Thành công" if email_sent else f"Thất bại ({html.escape(str(email_error or 'Unknown error'))})"
                                    admin_notification = (
                                        f"{E_SUCCESS} <b>ĐƠN HÀNG MỚI</b>\n"
                                        f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n"
                                        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Khách:</b> {html.escape(order_details.get('full_name', 'N/A'))} (@{html.escape(order_details.get('username') or 'N/A')})\n"
                                        f"{E_GLOBE} <b>Email:</b> <code>{html.escape(email)}</code> | {E_TAG} <b>Giá:</b> {actual_amount:,} VNĐ\n"
                                        f"<tg-emoji emoji-id=\"6129860303619363484\">✉️</tg-emoji> <b>Email:</b> {email_status}"
                                    )
                                    await safe_send_admin(context.bot, admin_notification)
                                except (TelegramError, ValueError, KeyError, AttributeError) as admin_err:
                                    logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> iCloud admin notification failed: {admin_err}")
                            else:
                                await context.bot.send_message(user_id, f"{E_SUCCESS} <b>THANH TOÁN THÀNH CÔNG</b>\n\nTuy nhiên, hệ thống đang tạm hết link. Admin sẽ gửi link cho bạn sớm nhất.", parse_mode=ParseMode.HTML)
                                await safe_send_admin(context.bot, f"{E_SOS} <b>CẢNH BÁO: HẾT LINK!</b> {E_SOS}\n\nKhách <b>{html.escape(email)}</b> đã thanh toán. Vui lòng <code>/addlink</code>.")
                            
                            coupon_code_used = order_details.get("coupon_code")
                            if coupon_code_used:
                                coupon_code_used = coupon_code_used.upper()
                                if coupon_code_used in coupons:
                                    coupons[coupon_code_used]['used'] = coupons[coupon_code_used].get('used', 0) + 1
                        # FIX BUG #12: Dùng db_add_order để update index
                        db_add_order(completed_order)
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
                                    text=(
                                        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>NẠP TIỀN API THÀNH CÔNG!</b>\n\n"
                                        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Partner:</b> {html.escape(str(p_name))}\n"
                                        f"<tg-emoji emoji-id=\"5397916757333654639\">➕</tg-emoji> <b>Đã nạp:</b> {amount_received:,} VNĐ\n"
                                        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số dư mới:</b> {new_bal:,} VNĐ\n"
                                        f"<i>Cảm ơn bạn đã nạp tiền!</i>"
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
        
        discount_amount = int(ICLOUD_PACKAGE_PRICE * discount_percent / 100)
        expires_str = (datetime.now() + timedelta(days=30)).strftime('%d-%m-%Y')
        
        coupons[code] = {
            "discount": discount_amount,
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


