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
        "ÄÃ£ hoÃ n thÃ nh",
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
                    refund_text = f"\n\n<tg-emoji emoji-id=\"5462956611033117422\">â™»ï¸</tg-emoji> <b>ÄÃ£ hoÃ n láº¡i:</b> +{balance_used:,} VNÄ vÃ o vÃ­ (Do Ä‘Æ¡n háº¿t háº¡n)."

            if details.get("type") == "store_product":
                caption = (
                    f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>ÄÆ N HÃ€NG ÄÃƒ Háº¾T Háº N</b> <tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji>\n\n"
                    f"ÄÆ¡n hÃ ng nÃ y Ä‘Ã£ háº¿t háº¡n thanh toÃ¡n.\n"
                    f"Vui lÃ²ng táº¡o Ä‘Æ¡n má»›i náº¿u báº¡n váº«n muá»‘n mua.{refund_text}"
                )
                reply_markup = create_back_button_menu("<tg-emoji emoji-id=\"5247134066322447995\">ðŸ›’</tg-emoji> Táº¡o Ä‘Æ¡n má»›i", "muahang_start")
            else:
                caption = (
                    f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>ÄÆ N HÃ€NG ÄÃƒ Háº¾T Háº N</b> <tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji>\n\n"
                    f"ÄÆ¡n hÃ ng cho email <b>{details.get('email', 'N/A')}</b> Ä‘Ã£ háº¿t háº¡n thanh toÃ¡n.\n"
                    f"Vui lÃ²ng táº¡o Ä‘Æ¡n má»›i náº¿u báº¡n váº«n muá»‘n mua.{refund_text}"
                )
                reply_markup = create_back_button_menu("<tg-emoji emoji-id=\"5247134066322447995\">ðŸ›’</tg-emoji> Táº¡o Ä‘Æ¡n má»›i", "muahang_start")

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
        logger.debug(f"DINO CRON (Binance Spot): TÃ¬m tháº¥y {len(deposits)} giao dá»‹ch náº¡p tá»« {start_timestamp_ms}")
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
        logger.debug("DINO CRON: KhÃ´ng cÃ³ Ä‘Æ¡n chá», bá» qua gá»i API bank.")
        return

    logger.debug(f"DINO CRON: Báº¯t Ä‘áº§u quÃ©t... ÄÆ¡n chá»: {len(pending_orders)} | API Náº¡p chá»: {len(pending_api_deposits)}")
    synthetic_transactions: list = []
    await _scan_usdt_bep20_payments(synthetic_transactions)
    await _scan_binance_pay_id_payments(synthetic_transactions)
    await _scan_binance_pay_payments(synthetic_transactions)
    await _scan_binance_spot_payments(synthetic_transactions)

    try:
        # Strip whitespace to prevent copy-paste errors
        clean_password = API_PASSWORD.strip()
        clean_account = BANK_ACCOUNT_NUMBER.strip()
        login_username = os.getenv("BANK_LOGIN_USERNAME", clean_account).strip()
        
        transactions = list(synthetic_transactions)

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
                f"âŒ Bank API request failed: {' | '.join(err_parts)}"
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
            log_bank_api_error(f"âŒ Lá»–I API BANK: {msg} | Keys: {str(api_key_info)[:30]}...")
            # Notify Admin if critical - with backoff to prevent spam
            _bank_api_fail_count += 1
            now_ts = time.time()
            if len(pending_orders) > 0 and (_bank_api_fail_count <= 3 or (now_ts - _bank_api_last_alert_time) >= 600):
                 _bank_api_last_alert_time = now_ts
                 await context.bot.send_message(
                     ADMIN_USER_ID,
                     f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>Lá»–I Káº¾T Ná»I BANK API</b> (láº§n {_bank_api_fail_count})\n\nServer tráº£ vá»: {msg}",
                     parse_mode=ParseMode.HTML
                 )
            if not transactions:
                return
        else:
            _bank_api_fail_count = 0
            tx_count_now = len(api_data.get("transactions", []))
            transactions.extend(api_data.get("transactions", []))
            logger.debug(f"DINO CRON: TÃ¬m tháº¥y {tx_count_now} giao dá»‹ch tá»« API.")
            _bank_api_last_status = "ok"
            _bank_api_last_error = ""
            _bank_api_last_tx_count = tx_count_now
            _bank_api_total_success += 1
        _bank_api_last_check_time = time.time()
        _bank_api_total_checks += 1

        if synthetic_transactions:
            logger.info(f"DINO CRON: TÃ¬m tháº¥y {len(synthetic_transactions)} giao dá»‹ch thanh toÃ¡n Ä‘Ã£ xÃ¡c nháº­n tá»« crypto/bank scan.")

        for tx in transactions:
            # FIX: Chuyá»ƒn tx_id sang string Ä‘á»ƒ Ä‘á»“ng bá»™
            tx_id = str(tx.get("transactionID", "")) # Default to empty string if missing
            description = tx.get("description", "")
            amount = tx.get("amount", 0)
            
            # Skip invalid transactions
            if not tx_id or not description:
                continue

            if db_check_tx_exists(tx_id): 
                continue
            
            # FIX: DÃ¹ng compiled regex patterns Ä‘á»ƒ tÄƒng tá»‘c
            no_space_description = description.replace(" ", "")
            match_order = ICLD_PATTERN.search(description) or ICLD_PATTERN.search(no_space_description)
            secret_order_code = _find_pending_order_code_by_transfer_description(description)
            api_deposit_reference = _find_pending_api_deposit_reference(description)

            if not (secret_order_code or match_order or api_deposit_reference):
                continue
            if not db_claim_transaction(tx_id):
                continue

            if secret_order_code or match_order: 
                # === Xá»¬ LÃ MUA LINK / QR BANK ===
                order_code = str(secret_order_code) if secret_order_code else f"ICLD{match_order.group(1)}"
                logger.info(f"DINO CRON: PhÃ¡t hiá»‡n mÃ£ Ä‘Æ¡n {order_code} trong giao dá»‹ch {tx_id}")

                order_details = await pending_get(order_code)
                if order_details:
                    expected_amount, actual_amount = int(order_details["amount"]), int(amount)
                    
                    logger.info(f"CRON: So sÃ¡nh tiá»n - Mong Ä‘á»£i: {expected_amount}, Thá»±c táº¿: {actual_amount}")

                    if actual_amount == expected_amount:
                        # Handle Store Product vs iCloud Package
                        if order_details.get("type") == "store_product":
                            prod_id = order_details.get("product_id")
                            qty = order_details.get("quantity", 1)
                            p = products.get(prod_id)
                            
                            # FIX: Check product exists - handle deleted products gracefully
                            if not p:
                                logger.error(f"âŒ CRITICAL: Product {prod_id} khÃ´ng tá»“n táº¡i (Ä‘Ã£ bá»‹ xÃ³a?) cho Ä‘Æ¡n {order_code}!")
                                
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
                                    reason="Sáº£n pháº©m khÃ´ng cÃ²n tá»“n táº¡i",
                                    order_data=order_details,
                                )

                                try:
                                    await context.bot.send_message(
                                        order_details['user_id'],
                                        f"{E_ERROR} <b>XIN Lá»–I - Sáº¢N PHáº¨M KHÃ”NG KHáº¢ Dá»¤NG</b>\n\n"
                                        f"Sáº£n pháº©m báº¡n Ä‘áº·t (MÃ£: <code>{prod_id}</code>) hiá»‡n khÃ´ng cÃ²n kháº£ dá»¥ng.\n\n"
                                        f"{E_TAG} <b>Sá»‘ tiá»n CK:</b> {actual_amount:,} VNÄ\n"
                                        f"{E_TAG} <b>ÄÃ£ hoÃ n vÃ­:</b> +{_deleted_total:,} VNÄ\n"
                                        f"{E_TAG} <b>MÃ£ Ä‘Æ¡n:</b> <code>{order_code}</code>\n\n"
                                        f"ToÃ n bá»™ tiá»n Ä‘Ã£ Ä‘Æ°á»£c hoÃ n vÃ o VÃ­ Bot.\n"
                                        f"Khoáº£n hoÃ n tá»« {BANK_REFUND_MIN_AMOUNT:,} VNÄ sáº½ cÃ³ thÃªm lá»±a chá»n nháº­n qua ngÃ¢n hÃ ng.",
                                        parse_mode=ParseMode.HTML
                                    )
                                except (ValueError, TypeError, KeyError, IndexError) as e:
                                    logger.error(f"KhÃ´ng gá»­i Ä‘Æ°á»£c thÃ´ng bÃ¡o cho user {order_details['user_id']}: {e}")
                                
                                # Alert admin with action buttons
                                try:
                                    await context.bot.send_message(
                                        ADMIN_USER_ID,
                                        f"<tg-emoji emoji-id=\"5447644880824181073\">ðŸš¨</tg-emoji> <b>Lá»–I NGHIÃŠM TRá»ŒNG - Sáº¢N PHáº¨M KHÃ”NG Tá»’N Táº I</b>\n\n"
                                        f"<b>Chi tiáº¿t:</b>\n"
                                        f"â€¢ ÄÆ¡n hÃ ng: <code>{order_code}</code>\n"
                                        f"â€¢ Product ID: <code>{prod_id}</code>\n"
                                        f"â€¢ KhÃ¡ch: {order_details.get('full_name')} (ID: <code>{order_details['user_id']}</code>)\n"
                                        f"â€¢ Sá»‘ tiá»n Ä‘Ã£ nháº­n: {actual_amount:,} VNÄ\n"
                                        f"â€¢ Tá»•ng Ä‘Ã£ hoÃ n vÃ­: {_deleted_total:,} VNÄ\n\n"
                                        f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> Há»‡ thá»‘ng Ä‘Ã£ tá»± Ä‘á»™ng hoÃ n tiá»n. Vui lÃ²ng kiá»ƒm tra nguyÃªn nhÃ¢n product bá»‹ xÃ³a.",
                                        parse_mode=ParseMode.HTML
                                    )
                                except (TelegramError, ValueError, KeyError, AttributeError) as e:
                                    logger.error(f"KhÃ´ng gá»­i Ä‘Æ°á»£c alert cho admin: {e}")
                                
                                # Mark transaction as processed to avoid re-checking
                                db_add_tx(tx_id)
                                await pending_pop(order_code)
                                data_changed = True
                                continue
                            
                            requires_gmail = p.get('requires_gmail', False)
                            
                            if requires_gmail:
                                # MANUAL PRODUCT: KhÃ´ng cáº§n stock, Ä‘á»£i email tá»« user
                                await context.bot.send_message(
                                    order_details['user_id'],
                                    f"{E_SUCCESS} <b>THANH TOÃN THÃ€NH CÃ”NG!</b>\n\n"
                                    f"{E_TAG} <b>Sáº£n pháº©m:</b> {p['name']}\n"
                                    f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ”¢</tg-emoji> <b>Sá»‘ lÆ°á»£ng:</b> {qty}\n"
                                    f"{E_TAG} <b>ÄÃ£ thanh toÃ¡n:</b> {actual_amount:,} VNÄ\n"
                                    f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> <b>MÃ£ Ä‘Æ¡n:</b> <code>{order_code}</code>\n\n"
                                    f"{E_GLOBE} <b>Vui lÃ²ng nháº­p email nháº­n dá»‹ch vá»¥:</b>\n"
                                    f"<i>Email nÃ y sáº½ Ä‘Æ°á»£c dÃ¹ng Ä‘á»ƒ Admin setup/gá»­i thÃ´ng tin cho báº¡n</i>\n\n"
                                    f"<b>CÃ¡ch gá»­i email:</b>\n"
                                    f"â€¢ Reply tin nháº¯n nÃ y vá»›i email cá»§a báº¡n\n"
                                    f"â€¢ Hoáº·c dÃ¹ng lá»‡nh: <code>/guimail email@abc.com</code>",
                                    parse_mode=ParseMode.HTML
                                )
                                
                                # LÆ°u vÃ o pending_manual_orders
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
                                
                                # XÃ³a khá»i pending_orders (safe delete)
                                await _mark_pending_payment_message_completed(context, order_details)
                                await pending_pop(order_code)
                                db_add_tx(tx_id)
                                data_changed = True
                                
                                # Log cho admin
                                await context.bot.send_message(
                                    ADMIN_USER_ID,
                                    f"<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> <b>ÄÃƒ NHáº¬N THANH TOÃN - ÄÆ N MANUAL</b>\n"
                                    f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> MÃ£: <code>{order_code}</code>\n"
                                    f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> SP: {p['name']}\n"
                                    f"<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> {actual_amount:,} VNÄ\n"
                                    f"<tg-emoji emoji-id=\"5213349767672769194\">â³</tg-emoji> Äang chá» khÃ¡ch nháº­p email...",
                                    parse_mode=ParseMode.HTML
                                )
                                
                                # Skip pháº§n xá»­ lÃ½ stock bÃªn dÆ°á»›i
                                continue

                            if p.get('is_social_source_service') or order_details.get('is_social_source_service'):
                                balance_used_order = int(order_details.get("balance_used", 0) or 0)
                                total_paid_social = actual_amount + balance_used_order
                                await context.bot.send_message(
                                    order_details['user_id'],
                                    f"{E_SUCCESS} <b>THANH TOÃN THÃ€NH CÃ”NG!</b>\n\n"
                                    f"{E_TAG} Sáº£n pháº©m: <b>{p['name']}</b>\n"
                                    f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ”¢</tg-emoji> Sá»‘ lÆ°á»£ng: {qty}\n"
                                    f"{E_TAG} Thanh toÃ¡n: {actual_amount:,} VNÄ\n\n"
                                    f"{E_LOADING} <b>Äang táº¡o Ä‘Æ¡n social trÃªn nguá»“n...</b>",
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
                                        product_name=p.get('name', 'Dá»‹ch vá»¥ social'),
                                        reason="Lá»—i nguá»“n cung cáº¥p dá»‹ch vá»¥ social",
                                        order_data=order_details,
                                    )

                                    await context.bot.send_message(
                                        order_details['user_id'],
                                        f"âŒ <b>Lá»–I NGUá»’N CUNG Cáº¤P Dá»ŠCH Vá»¤ SOCIAL</b>\n\n"
                                        f"ÄÆ¡n social khÃ´ng thá»ƒ táº¡o trÃªn nguá»“n vÃ o lÃºc nÃ y.\n"
                                        f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> ÄÃ£ hoÃ n <b>{refund_amount:,} VNÄ</b> vÃ o vÃ­ Bot.\n\n"
                                        f"MÃ£ Ä‘Æ¡n: <code>{order_code}</code>",
                                        parse_mode=ParseMode.HTML,
                                    )
                                    await safe_send_admin(
                                        context.bot,
                                        f"{E_SOS} <b>SOCIAL_SOURCE PAYMENT ORDER FAILED</b>\n"
                                        f"{E_ID} ÄÆ¡n: <code>{order_code}</code>\n"
                                        f"{E_USER} User: <code>{order_details['user_id']}</code>\n"
                                        f"{E_TAG} SP: {html.escape(p['name'])} x{qty}\n"
                                        f"{E_TAG} HoÃ n vÃ­: {refund_amount:,} VNÄ\n"
                                        f"{E_ERROR} Lá»—i: <code>{html.escape(str(supplier_result.get('error') or 'unknown_error'))}</code>",
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
                                    f"{E_SUCCESS} <b>ÄÆ N SOCIAL ÄÃƒ Táº O THÃ€NH CÃ”NG</b>\n\n"
                                    f"{E_TAG} Sáº£n pháº©m: {html.escape(str(p['name']))}\n"
                                    f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ”¢</tg-emoji> Sá»‘ lÆ°á»£ng: {qty}\n"
                                    f"<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> MÃ£ Ä‘Æ¡n: <code>{html.escape(str(completed_order.get('order_code') or order_code))}</code>\n"
                                    f"<tg-emoji emoji-id=\"6059654836918423763\">ðŸ“Š</tg-emoji> Tá»•ng Ä‘Æ¡n vá»‹ nguá»“n: {int(supplier_result.get('supplier_quantity', 0) or 0):,}\n"
                                    f"<tg-emoji emoji-id=\"5231489647946768652\">ðŸ”—</tg-emoji> Target: <code>{html.escape(str(supplier_result.get('target_link') or 'N/A'))}</code>\n"
                                    f"<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> MÃ£ supplier: <code>{html.escape(str(supplier_result.get('supplier_order_id') or ''))}</code>\n"
                                    f"{E_STAT} Tráº¡ng thÃ¡i nguá»“n: {html.escape(str(supplier_result.get('supplier_status') or 'Pending'))}",
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=create_success_menu(),
                                )

                                await send_live_order_notification(
                                    context,
                                    order_details.get("full_name", "KhÃ¡ch hÃ ng"),
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
                            # Náº¿u lÃ  sáº£n pháº©m resell tá»« SupplierSource, mua tá»« API thay vÃ¬ láº¥y tá»« stock local
                            if p.get('is_supplier_source_resell'):
                                supplier_source_product_id = p.get('supplier_source_product_id')
                                supplier_source_variant_id = p.get('supplier_source_variant_id')
                                
                                await context.bot.send_message(
                                    order_details['user_id'],
                                    f"{E_SUCCESS} <b>THANH TOÃN THÃ€NH CÃ”NG!</b>\n\n"
                                    f"{E_TAG} Sáº£n pháº©m: <b>{p['name']}</b>\n"
                                    f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ”¢</tg-emoji> Sá»‘ lÆ°á»£ng: {qty}\n"
                                    f"{E_TAG} Thanh toÃ¡n: {actual_amount:,} VNÄ\n\n"
                                    f"{E_LOADING} <b>Äang láº¥y tÃ i khoáº£n tá»« há»‡ thá»‘ng...</b>",
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
                                        product_name=p.get('name', 'Sáº£n pháº©m'),
                                        reason="Sáº£n pháº©m táº¡m táº¯t resell",
                                        order_data=order_details,
                                    )
                                    await context.bot.send_message(
                                        order_details['user_id'],
                                        f"âŒ <b>Sáº¢N PHáº¨M ÄANG Táº M Táº®T RESELL</b>\n\n"
                                        f"ÄÆ¡n <code>{order_code}</code> Ä‘Ã£ Ä‘Æ°á»£c hoÃ n <b>{refund_amount:,} VNÄ</b> vÃ o vÃ­ Bot.",
                                        parse_mode=ParseMode.HTML,
                                    )
                                    await pending_pop(order_code)
                                    db_add_tx(tx_id)
                                    data_changed = True
                                    continue
                                
                                # Gá»i API nguá»“n ngoÃ i Ä‘á»ƒ mua sáº£n pháº©m
                                supplier_source_result = await supplier_create_order(p, qty)
                                
                                if not supplier_source_result.get("success"):
                                    # Lá»—i API - ThÃ´ng bÃ¡o Admin vÃ  hoÃ n tiá»n
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
                                        product_name=p.get('name', 'Sáº£n pháº©m'),
                                        reason=f"Lá»—i nguá»“n cung cáº¥p: {error}",
                                        order_data=order_details,
                                    )
                                    refund_breakdown_line = ""
                                    if balance_used_order > 0:
                                        refund_breakdown_line = (
                                            f"<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> "
                                            f"Tá»•ng hoÃ n thá»±c táº¿: <b>{refund_amount:,} VNÄ</b> "
                                            f"(gá»“m {balance_used_order:,} VNÄ Ä‘Ã£ trá»« tá»« vÃ­)\n"
                                        )
                                        
                                    await context.bot.send_message(
                                        order_details['user_id'],
                                        f"âŒ <b>Lá»–I Há»† THá»NG NGUá»’N CUNG Cáº¤P</b>\n\n"
                                        f"Ráº¥t xin lá»—i, sáº£n pháº©m hiá»‡n táº¡i táº¡m khÃ´ng thá»ƒ giao dá»‹ch (cÃ³ thá»ƒ do háº¿t hÃ ng hoáº·c káº¹t máº¡ng).\n"
                                        f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> <b>ÄÃ£ tá»± Ä‘á»™ng hoÃ n {refund_amount:,} VNÄ</b> vÃ o sá»‘ dÆ° vÃ­ Bot cá»§a báº¡n.\n\n"
                                        f"MÃ£ Ä‘Æ¡n: <code>{order_code}</code>\n"
                                        f"Báº¡n cÃ³ thá»ƒ dÃ¹ng vÃ­ Ä‘á»ƒ mua láº¡i sau, hoáº·c mua máº·t hÃ ng khÃ¡c.",
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
                                        f"{E_SOS} <b>Lá»–I API NGUá»’N CUNG Cáº¤P KHI THANH TOÃN QR/USDT</b>\n\n"
                                        f"{E_TAG} SP: {html.escape(p['name'])}\n"
                                        f"{E_ID} ÄÆ¡n: <code>{order_code}</code>\n"
                                        f"<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¤</tg-emoji> User: <code>{order_details['user_id']}</code>\n"
                                        f"{E_TAG} Tiá»n: {actual_amount:,} VNÄ\n\n"
                                        f"{E_LIMIT} Lá»—i: <code>{html.escape(str(error))}</code>\n\n"
                                        f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> ÄÃƒ Tá»° Äá»˜NG HOÃ€N VÃ€O Sá» DÆ¯ VÃ KHÃCH!",
                                    )
                                    if balance_used_order > 0:
                                        await safe_send_admin(
                                            context.bot,
                                            f"{E_TAG} HoÃ n thá»±c táº¿: {refund_amount:,} VNÄ = CK {actual_amount:,} VNÄ + VÃ­ {balance_used_order:,} VNÄ\n"
                                            f"{E_ID} ÄÆ¡n: <code>{order_code}</code>",
                                        )
                                    await pending_pop(order_code)
                                    db_add_tx(tx_id)
                                    data_changed = True
                                    continue
                                
                                # Parse delivered content tá»« nguá»“n ngoÃ i
                                supplier_source_orders = supplier_source_result.get("data", [])
                                items_bought = []
                                
                                for dm_order in supplier_source_orders:
                                    delivered = dm_order.get("deliveredContent")
                                    if delivered:
                                        logger.info(f"DEBUG SUPPLIER CONTENT TYPE: {type(delivered).__name__}")
                                        items_bought.extend(normalize_delivered_items(delivered))
                                
                                # Náº¿u chÆ°a cÃ³ content, thá»­ láº¥y order details
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
                                    # Váº«n khÃ´ng cÃ³ content
                                    await context.bot.send_message(
                                        order_details['user_id'],
                                        f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>ÄANG Xá»¬ LÃ...</b>\n\n"
                                        f"ÄÆ¡n hÃ ng Ä‘Ã£ táº¡o nhÆ°ng Ä‘ang chá» giao hÃ ng tá»« nguá»“n.\n"
                                        f"Admin sáº½ gá»­i tÃ i khoáº£n sá»›m nháº¥t.\n\n"
                                        f"MÃ£ Ä‘Æ¡n: <code>{order_code}</code>",
                                        parse_mode=ParseMode.HTML
                                    )
                                    await context.bot.send_message(
                                        ADMIN_USER_ID,
                                        f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>NGUá»’N CUNG Cáº¤P CHÆ¯A TRáº¢ HÃ€NG</b>\n\n"
                                        f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> SP: {p['name']}\n"
                                        f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ†”</tg-emoji> ÄÆ¡n: <code>{order_code}</code>\n"
                                        f"Nguá»“n cung cáº¥p chÆ°a tráº£ content. Cáº§n check manual.",
                                        parse_mode=ParseMode.HTML
                                    )
                                    await _mark_pending_payment_message_completed(context, order_details)
                                    await pending_pop(order_code)
                                    db_add_tx(tx_id)
                                    data_changed = True
                                    continue
                                
                                # ThÃ nh cÃ´ng! Gá»­i cho khÃ¡ch (code tiáº¿p tá»¥c bÃªn dÆ°á»›i vá»›i items_bought)
                                # KhÃ´ng cáº§n xá»­ lÃ½ stock local vÃ¬ Ä‘Ã£ láº¥y tá»« API
                                
                                purchase_date = datetime.datetime.fromtimestamp(current_time).strftime('%d/%m/%Y %H:%M:%S')
                                product_description_txt = format_product_description_for_txt(p)
                                
                                file_content = "="*60 + "\n"
                                file_content += "           THÃ”NG TIN ÄÆ N HÃ€NG\n"
                                file_content += "="*60 + "\n\n"
                                file_content += f"<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“‹</tg-emoji> MÃƒ ÄÆ N HÃ€NG    : {order_code}\n"
                                file_content += f"<tg-emoji emoji-id=\"5413879192267805083\">ðŸ“…</tg-emoji> NGÃ€Y MUA       : {purchase_date}\n"
                                file_content += f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> Sáº¢N PHáº¨M       : {p['name']}\n"
                                file_content += f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ”¢</tg-emoji> Sá» LÆ¯á»¢NG       : {qty}\n"
                                file_content += f"<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> THANH TOÃN     : {actual_amount:,} VNÄ\n"
                                if product_description_txt:
                                    file_content += f"\nMÃ” Táº¢ Sáº¢N PHáº¨M:\n{product_description_txt}\n\n"
                                file_content += f"<tg-emoji emoji-id=\"5213349767672769194\">â°</tg-emoji> THá»œI Háº N       : {p.get('duration', 'N/A')}\n"
                                file_content += f"<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡ï¸</tg-emoji> Báº¢O HÃ€NH       : {p.get('warranty', 'KhÃ´ng')}\n"
                                file_content += "\n" + "="*60 + "\n"
                                file_content += "           TÃ€I KHOáº¢N Cá»¦A Báº N\n"
                                file_content += "="*60 + "\n\n"
                                
                                for i, item in enumerate(items_bought, 1):
                                    file_content += f"[{i}] {item}\n"
                                
                                file_content += "\n" + "="*60 + "\n"
                                file_content += "LÆ¯U Ã: Vui lÃ²ng Ä‘á»•i máº­t kháº©u sau khi Ä‘Äƒng nháº­p!\n"
                                file_content += "="*60 + "\n"
                                
                                delivery_result = await deliver_items_as_txt(
                                    context,
                                    order_details['user_id'],
                                    order_code,
                                    items_bought,
                                    file_content=file_content,
                                    file_prefix="DonHang",
                                    caption_html=f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“</tg-emoji> <b>THÃ”NG TIN TÃ€I KHOáº¢N</b>\n\nMÃ£ Ä‘Æ¡n: <code>{order_code}</code>\n<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> {p['name']} x{qty}",
                                )
                                delivery_status = OrderStatus.COMPLETED.value if delivery_result.get("delivered") else "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Chá» gá»­i thá»§ cÃ´ng (Nguá»“n ngoÃ i)"
                                if not delivery_result.get("delivered"):
                                    await safe_send_message(
                                        context,
                                        order_details['user_id'],
                                        f"âŒ CÃ³ lá»—i khi gá»­i tÃ i khoáº£n cho Ä‘Æ¡n <code>{order_code}</code>.\n"
                                        "Admin Ä‘Ã£ nháº­n cáº£nh bÃ¡o vÃ  sáº½ gá»­i thá»§ cÃ´ng sá»›m nháº¥t.",
                                        parse_mode=ParseMode.HTML,
                                    )
                                    await safe_send_admin(
                                        context.bot,
                                        f"{E_SOS} <b>DELIVERY FAILED (NGUá»’N NGOÃ€I)</b>\n"
                                        f"{E_ID} ÄÆ¡n: <code>{order_code}</code>\n"
                                        f"{E_USER} User: <code>{order_details['user_id']}</code>\n"
                                        f"{E_TAG} SP: {html.escape(p['name'])} x{qty}\n"
                                        f"{E_STAT} Fallback gá»­i: {delivery_result.get('sent_items', 0)}/{len(items_bought)} items\n"
                                        f"{E_ERROR} Errors: <code>{html.escape(' | '.join(delivery_result.get('errors', [])[-3:]) or 'n/a')}</code>",
                                    )
                                
                                # Log lá»‹ch sá»­
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
                                
                                # ThÃ´ng bÃ¡o Admin (sau khi Ä‘Ã£ save data an toÃ n)
                                try:
                                    supplier_source_cost = p.get('supplier_source_price', 0) * qty
                                    await context.bot.send_message(
                                        ADMIN_USER_ID,
                                        f"{E_SUCCESS} <b>ÄÆ N RESELL THÃ€NH CÃ”NG!</b>\n\n"
                                        f"{E_TAG} SP: {p['name']} x{qty}\n"
                                        f"{E_ID} MÃ£: <code>{order_code}</code>\n"
                                        f"{E_TAG} BÃ¡n: {actual_amount:,} VNÄ\n"
                                        f"<tg-emoji emoji-id=\"5863724849851011383\">ðŸ’µ</tg-emoji> Gá»‘c: {supplier_source_cost:,} VNÄ\n"
                                        f"{E_STAT} Lá»i: {actual_amount - supplier_source_cost:,} VNÄ",
                                        parse_mode=ParseMode.HTML
                                    )
                                except (TelegramError, ValueError, KeyError, AttributeError) as admin_err:
                                    logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Supplier admin notification failed: {admin_err}")
                                continue
                            
                            # ===== END SUPPLIER_SOURCE AUTO RESELL =====
                            
                            # AUTO PRODUCT: Cáº§n check stock (Sáº£n pháº©m cÃ³ stock local)
                            # FIX BUG #5: DÃ¹ng lock Ä‘á»ƒ trÃ¡nh race condition
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
                                    f"âŒ <b>Ráº¤T TIáº¾C!</b>\n\n"
                                    f"Sáº£n pháº©m <b>{p['name']}</b> vá»«a Ä‘Æ°á»£c mua háº¿t bá»Ÿi khÃ¡ch khÃ¡c.\n\n"
                                    f"<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> ÄÆ¡n hÃ ng Ä‘Ã£ Ä‘Æ°á»£c hoÃ n tiá»n tá»± Ä‘á»™ng: <b>+{total_refund:,} VNÄ</b>\n"
                                    f"<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> Sá»‘ dÆ° má»›i: <b>{new_balance:,} VNÄ</b>",
                                    parse_mode=ParseMode.HTML
                                )
                                
                                # Log cho admin
                                await context.bot.send_message(
                                    ADMIN_USER_ID,
                                    f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>RACE CONDITION - Háº¾T HÃ€NG!</b>\n"
                                    f"ÄÆ¡n: <code>{order_code}</code>\n"
                                    f"SP: {p['name']}\n"
                                    f"YÃªu cáº§u: {qty} | CÃ²n: {current_stock}\n\n"
                                    f"ÄÃ£ auto refund: {total_refund:,} VNÄ -> User {order_details['user_id']}",
                                    parse_mode=ParseMode.HTML
                                )
                                
                                # Cleanup (safe delete)
                                await pending_pop(order_code)
                                db_add_tx(tx_id)
                                data_changed = True
                                continue
                            
                            
                            # Delivery cho AUTO product (manual Ä‘Ã£ Ä‘Æ°á»£c handle á»Ÿ trÃªn vá»›i continue)
                            
                            # Gá»­i header message trÆ°á»›c
                            try:
                                await context.bot.send_message(
                                    order_details['user_id'],
                                    f"{E_SUCCESS} <b>THANH TOÃN THÃ€NH CÃ”NG</b>\n\n"
                                    f"{E_TAG} <b>Sáº£n pháº©m:</b> {p['name']}\n"
                                    f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> <b>Sá»‘ lÆ°á»£ng:</b> {qty}\n"
                                    f"{E_TAG} <b>Thanh toÃ¡n:</b> {actual_amount:,} VND\n"
                                    f"{E_LOADING} <b>Thá»i háº¡n:</b> {p.get('duration', 'N/A')}\n"
                                    f"<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡ï¸</tg-emoji> <b>Báº£o hÃ nh:</b> {p.get('warranty', 'KhÃ´ng')}\n\n"
                                    f"{E_TIP} <b>Há»‡ thá»‘ng Ä‘ang gá»­i thÃ´ng tin tÃ i khoáº£n ngay sau tin nháº¯n nÃ y...</b>",
                                    parse_mode=ParseMode.HTML
                                )
                            except (TelegramError, ValueError, KeyError, AttributeError) as e:
                                logger.error(f"Lá»—i gá»­i header message: {e}")
                            
                            purchase_date = datetime.datetime.fromtimestamp(current_time).strftime('%d/%m/%Y %H:%M:%S')
                            product_description_txt = format_product_description_for_txt(p)
                            file_content = "="*60 + "\n"
                            file_content += "           THÃ”NG TIN ÄÆ N HÃ€NG\n"
                            file_content += "="*60 + "\n\n"
                            file_content += f"MÃ£ Ä‘Æ¡n hÃ ng    : {order_code}\n"
                            file_content += f"NgÃ y mua       : {purchase_date}\n"
                            file_content += f"Sáº£n pháº©m       : {p['name']}\n"
                            file_content += f"Sá»‘ lÆ°á»£ng       : {qty}\n"
                            file_content += f"Thanh toÃ¡n     : {actual_amount:,} VND\n"
                            if product_description_txt:
                                file_content += f"\nMÃ´ táº£ sáº£n pháº©m:\n{product_description_txt}\n\n"
                            file_content += f"Thá»i háº¡n       : {p.get('duration', 'N/A')}\n"
                            file_content += f"Báº£o hÃ nh       : {p.get('warranty', 'KhÃ´ng')}\n"
                            file_content += "\n" + "="*60 + "\n"
                            file_content += "           DANH SÃCH TÃ€I KHOáº¢N\n"
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
                                caption_html=f"<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“‹</tg-emoji> <b>File tÃ i khoáº£n</b>\nMÃ£ Ä‘Æ¡n: <code>{order_code}</code>",
                                reply_markup=create_success_menu(),
                            )
                            delivery_status = "HoÃ n thÃ nh" if delivery_result.get("delivered") else "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Chá» gá»­i thá»§ cÃ´ng (AUTO Local)"
                            if not delivery_result.get("delivered"):
                                await safe_send_admin(
                                    context.bot,
                                    f"{E_SOS} <b>DELIVERY FAILED (AUTO LOCAL)</b>\n"
                                    f"{E_ID} ÄÆ¡n: <code>{order_code}</code>\n"
                                    f"{E_USER} User: <code>{order_details['user_id']}</code>\n"
                                    f"{E_TAG} SP: {html.escape(p['name'])} x{qty}\n"
                                    f"{E_STAT} Fallback gá»­i: {delivery_result.get('sent_items', 0)}/{len(items_bought)} items\n"
                                    f"{E_ERROR} Errors: <code>{html.escape(' | '.join(delivery_result.get('errors', [])[-3:]) or 'n/a')}</code>",
                                )
                                await safe_send_message(
                                    context,
                                    order_details['user_id'],
                                    f"âŒ CÃ³ lá»—i khi gá»­i tÃ i khoáº£n cho Ä‘Æ¡n <code>{order_code}</code>.\n"
                                    "Admin Ä‘Ã£ nháº­n cáº£nh bÃ¡o vÃ  sáº½ gá»­i thá»§ cÃ´ng sá»›m nháº¥t.",
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=create_success_menu(),
                                )
                            
                            # Táº¡o completed_order cho AUTO product (LÆ¯U items Ä‘á»ƒ khÃ´i phá»¥c náº¿u cáº§n)
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
                            await send_live_order_notification(context, order_details.get("full_name", "KhÃ¡ch hÃ ng"), total_paid, product_name=p['name'], quantity=qty, order_code=order_code)
                            
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
                            
                            # Auto-broadcast náº¿u háº¿t hÃ ng
                            remaining_stock = int(get_local_stock_available_count(products.get(prod_id)) or 0)
                            if delivery_result.get("delivered"):
                                create_background_task(send_post_purchase_followups(context, order_details['user_id'], prod_id))
                            if remaining_stock == 0:
                                create_background_task(broadcast_out_of_stock(context, p['name'], prod_id))
                            
                            # Admin notification (safe - sau khi Ä‘Ã£ save)
                            try:
                                await safe_send_admin(context.bot, f"{E_SUCCESS} <b>ÄÆ N HÃ€NG STORE Má»šI</b>\n<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> MÃ£: <code>{order_code}</code>\n{E_TAG} SP: {html.escape(p['name'])} (x{qty})\n{E_TAG} {actual_amount:,} VNÄ")
                            except (TelegramError, ValueError, KeyError, AttributeError) as admin_err:
                                logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Store admin notification failed: {admin_err}")
                            
                            # SKIP shared cleanup (Ä‘Ã£ xá»­ lÃ½ á»Ÿ trÃªn)
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
                                    f"Link kÃ­ch hoáº¡t gÃ³i iCloud 2TB - {order_code}",
                                    order_details.get("full_name", "báº¡n"),
                                    link_to_send,
                                )
                                if email_sent:
                                    await context.bot.send_message(
                                        user_id,
                                        f"{E_SUCCESS} <b>THANH TOÃN THÃ€NH CÃ”NG</b> {E_SUCCESS}\n\n"
                                        f"Cáº£m Æ¡n báº¡n! Link kÃ­ch hoáº¡t Ä‘Ã£ Ä‘Æ°á»£c gá»­i Ä‘áº¿n email <b>{email}</b>.",
                                        parse_mode=ParseMode.HTML,
                                        reply_markup=create_success_menu(),
                                    )
                                else:
                                    await context.bot.send_message(
                                        user_id,
                                        f"{E_SUCCESS} <b>THANH TOÃN THÃ€NH CÃ”NG</b> {E_SUCCESS}\n\n"
                                        f"ÄÆ¡n cá»§a báº¡n Ä‘Ã£ hoÃ n táº¥t nhÆ°ng gá»­i email kÃ­ch hoáº¡t tháº¥t báº¡i.\n"
                                        f"Vui lÃ²ng liÃªn há»‡ Admin vÃ  cung cáº¥p mÃ£ Ä‘Æ¡n <code>{order_code}</code>.",
                                        parse_mode=ParseMode.HTML,
                                        reply_markup=create_success_menu(),
                                    )
                                
                                await send_live_order_notification(context, order_details.get("full_name", "KhÃ¡ch hÃ ng"), actual_amount, product_name="iCloud 2TB", quantity=1, order_code=order_code)
                                
                                try:
                                    email_status = "ThÃ nh cÃ´ng" if email_sent else f"Tháº¥t báº¡i ({html.escape(str(email_error or 'Unknown error'))})"
                                    admin_notification = (
                                        f"{E_SUCCESS} <b>ÄÆ N HÃ€NG Má»šI</b>\n"
                                        f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> <b>MÃ£ Ä‘Æ¡n:</b> <code>{order_code}</code>\n"
                                        f"<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¤</tg-emoji> <b>KhÃ¡ch:</b> {html.escape(order_details.get('full_name', 'N/A'))} (@{html.escape(order_details.get('username') or 'N/A')})\n"
                                        f"{E_GLOBE} <b>Email:</b> <code>{html.escape(email)}</code> | {E_TAG} <b>GiÃ¡:</b> {actual_amount:,} VNÄ\n"
                                        f"<tg-emoji emoji-id=\"6129860303619363484\">âœ‰ï¸</tg-emoji> <b>Email:</b> {email_status}"
                                    )
                                    await safe_send_admin(context.bot, admin_notification)
                                except (TelegramError, ValueError, KeyError, AttributeError) as admin_err:
                                    logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> iCloud admin notification failed: {admin_err}")
                            else:
                                await context.bot.send_message(user_id, f"{E_SUCCESS} <b>THANH TOÃN THÃ€NH CÃ”NG</b>\n\nTuy nhiÃªn, há»‡ thá»‘ng Ä‘ang táº¡m háº¿t link. Admin sáº½ gá»­i link cho báº¡n sá»›m nháº¥t.", parse_mode=ParseMode.HTML)
                                await safe_send_admin(context.bot, f"{E_SOS} <b>Cáº¢NH BÃO: Háº¾T LINK!</b> {E_SOS}\n\nKhÃ¡ch <b>{html.escape(email)}</b> Ä‘Ã£ thanh toÃ¡n. Vui lÃ²ng <code>/addlink</code>.")
                            
                            coupon_code_used = order_details.get("coupon_code")
                            if coupon_code_used:
                                coupon_code_used = coupon_code_used.upper()
                                if coupon_code_used in coupons:
                                    coupons[coupon_code_used]['used'] = coupons[coupon_code_used].get('used', 0) + 1
                        # FIX BUG #12: DÃ¹ng db_add_order Ä‘á»ƒ update index
                        db_add_order(completed_order)
                        db_add_tx(tx_id)
                        await _mark_pending_payment_message_completed(context, order_details)
                        await pending_pop(order_code)
                        data_changed = True
                    else:
                        logger.warning(f"Giao dá»‹ch gáº§n Ä‘Ãºng! Code: {order_code}, Mong Ä‘á»£i: {expected_amount}, Thá»±c táº¿: {actual_amount}")
                        alert_message = ( f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>Cáº¢NH BÃO GIAO Dá»ŠCH ÄÃNG NGá»œ</b> <tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji>\n\n" f"PhÃ¡t hiá»‡n giao dá»‹ch cÃ³ mÃ£ Ä‘Æ¡n hÃ ng Ä‘ang chá» nhÆ°ng sai sá»‘ tiá»n.\n\n" f"- <b>MÃ£ Ä‘Æ¡n hÃ ng:</b> <code>{order_code}</code>\n" f"- <b>KhÃ¡ch hÃ ng:</b> {html.escape(order_details.get('full_name', 'N/A'))} (@{html.escape(order_details.get('username') or 'N/A')})\n" f"- <b>Sá»‘ tiá»n Ä‘Ãºng:</b> <pre>{expected_amount:,} VNÄ</pre>\n" f"- <b>Sá»‘ tiá»n Ä‘Ã£ chuyá»ƒn:</b> <pre>{actual_amount:,} VNÄ</pre>\n\n" f"Vui lÃ²ng kiá»ƒm tra vÃ  xá»­ lÃ½ thá»§ cÃ´ng. Giao dá»‹ch nÃ y chÆ°a Ä‘Æ°á»£c tá»± Ä‘á»™ng xá»­ lÃ½." )
                        await safe_send_admin(context.bot, alert_message); db_add_tx(tx_id); data_changed = True

                else:
                    if not db_check_tx_exists(tx_id):
                        db_add_tx(tx_id); data_changed = True
                        logger.warning(f'CRON: PhÃ¡t hiá»‡n thanh toÃ¡n trá»…/orphan: {order_code} - {int(amount):,} VNÄ (Ä‘Æ¡n Ä‘Ã£ háº¿t háº¡n hoáº·c Ä‘Ã£ xá»­ lÃ½)')
                        existing_order = order_index.get(order_code)
                        if not existing_order:
                            await safe_send_admin(
                                context.bot,
                                f'<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>THANH TOÃN TRá»„ - Cáº¦N Xá»¬ LÃ</b>\n\n'
                                f'MÃ£ Ä‘Æ¡n: <code>{order_code}</code>\n'
                                f'Sá»‘ tiá»n: <b>{int(amount):,} VNÄ</b>\n'
                                f'MÃ´ táº£ GD: <code>{html.escape(description[:100])}</code>\n'
                                f'TX ID: <code>{tx_id}</code>\n\n'
                                f'ÄÆ¡n hÃ ng nÃ y Ä‘Ã£ háº¿t háº¡n hoáº·c khÃ´ng tá»“n táº¡i trong hÃ ng chá».\n'
                                f'Vui lÃ²ng kiá»ƒm tra vÃ  hoÃ n tiá»n náº¿u cáº§n: <code>/refund {order_code}</code>'
                            )

            elif api_deposit_reference:
                # === Xá»¬ LÃ Náº P TIá»€N API ===
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
                            f"{E_LIMIT} <b>Náº P API Lá»–I Cáº¤U HÃŒNH</b>\n"
                            f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> Code: <code>{deposit_code}</code>\n"
                            f"<tg-emoji emoji-id=\"5350481781306958339\">ðŸ§¾</tg-emoji> LÃ½ do: Sá»‘ tiá»n ká»³ vá»ng khÃ´ng há»£p lá»‡ ({amount_expected})."
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
                                f"{E_LIMIT} <b>Náº P API Lá»–I KEY</b>\n"
                                f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> Code: <code>{deposit_code}</code>\n"
                                f"<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> Nháº­n: {amount_received:,} VNÄ\n"
                                f"<tg-emoji emoji-id=\"5350481781306958339\">ðŸ§¾</tg-emoji> LÃ½ do: API key khÃ´ng tá»“n táº¡i hoáº·c Ä‘Ã£ bá»‹ xÃ³a."
                            )
                            continue

                        key_data = _api_normalize_partner_key(key)
                        if not isinstance(key_data, dict):
                            db_add_tx(tx_id)
                            pending_api_deposits.pop(deposit_code, None)
                            data_changed = True
                            await safe_send_admin(
                                context.bot,
                                f"{E_LIMIT} <b>Náº P API Lá»–I Dá»® LIá»†U</b>\n"
                                f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> Code: <code>{deposit_code}</code>\n"
                                f"<tg-emoji emoji-id=\"5350481781306958339\">ðŸ§¾</tg-emoji> LÃ½ do: Dá»¯ liá»‡u API key khÃ´ng há»£p lá»‡."
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
                                f"{E_LIMIT} <b>Náº P API Lá»–I KHÃ“A VÃ</b>\n"
                                f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> Code: <code>{deposit_code}</code>\n"
                                f"<tg-emoji emoji-id=\"5350481781306958339\">ðŸ§¾</tg-emoji> LÃ½ do: KhÃ´ng thá»ƒ cáº­p nháº­t sá»‘ dÆ° API key."
                            )
                            continue
                        p_name = details.get("partner_name", key_data.get("name", "N/A"))
                        
                        db_add_tx(tx_id)
                        pending_api_deposits.pop(deposit_code, None)
                        data_changed = True
                        
                        await safe_send_admin(
                            context.bot,
                            f"{E_SUCCESS} <b>Náº P TIá»€N API THÃ€NH CÃ”NG</b>\n\n"
                            f"<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¤</tg-emoji> <b>Partner:</b> {html.escape(str(p_name))}\n"
                            f"{E_TAG} <b>Náº¡p vÃ o:</b> {amount_received:,} VNÄ\n"
                            f"<tg-emoji emoji-id=\"5863724849851011383\">ðŸ’µ</tg-emoji> <b>Sá»‘ dÆ° má»›i:</b> {new_bal:,} VNÄ\n"
                            f"{E_TAG} <b>MÃ£ GD:</b> <code>{deposit_code}</code>"
                        )
                        
                        # Gá»­i thÃ´ng bÃ¡o cho user (náº¿u cÃ³ user_id Ä‘Æ°á»£c lÆ°u)
                        user_id_to_notify = details.get("user_id")
                        if user_id_to_notify:
                            try:
                                await context.bot.send_message(
                                    chat_id=user_id_to_notify,
                                    text=(
                                        f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> <b>Náº P TIá»€N API THÃ€NH CÃ”NG!</b>\n\n"
                                        f"<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¤</tg-emoji> <b>Partner:</b> {html.escape(str(p_name))}\n"
                                        f"<tg-emoji emoji-id=\"5397916757333654639\">âž•</tg-emoji> <b>ÄÃ£ náº¡p:</b> {amount_received:,} VNÄ\n"
                                        f"<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> <b>Sá»‘ dÆ° má»›i:</b> {new_bal:,} VNÄ\n"
                                        f"<i>Cáº£m Æ¡n báº¡n Ä‘Ã£ náº¡p tiá»n!</i>"
                                    ),
                                    parse_mode=ParseMode.HTML
                                )
                            except (TelegramError, ValueError, KeyError, AttributeError) as e:
                                logger.error(f"Khong the gui thong bao nap API thanh cong cho user {user_id_to_notify}: {e}")
                    else:
                         # Thiáº¿u tiá»n
                         db_add_tx(tx_id); data_changed = True
                         await safe_send_admin(
                            context.bot,
                            f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>Lá»–I Náº P API (THIáº¾U TIá»€N)</b>\nCode: {deposit_code}\nNháº­n: {amount_received:,}\nCáº§n: {amount_expected:,}"
                         )

    except (TelegramError, httpx.HTTPError, sqlite3.Error, ValueError, KeyError) as e: logger.error(f"âŒ Lá»–I KHÃ”NG XÃC Äá»ŠNH TRONG check_payment_job: {e}", exc_info=True)
    if data_changed: await save_critical_tables(HISTORY_FILE, PROCESSED_TX_FILE, PENDING_ORDERS_FILE, USERS_FILE, API_KEYS_FILE, "data_pending_api_deposits.json")

async def cleanup_expired_coupons_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("CRON: Báº¯t Ä‘áº§u quÃ©t mÃ£ giáº£m giÃ¡ khÃ´ng há»£p lá»‡...")
    today = datetime.now().date(); invalid_codes = []
    for code, details in list(coupons.items()):
        is_expired, is_used_up = False, False
        expiry_str = details.get('expires')
        if expiry_str:
            try:
                if datetime.strptime(expiry_str, '%d-%m-%Y').date() < today: is_expired = True
            except ValueError: logger.warning(f"Lá»—i Ä‘á»‹nh dáº¡ng ngÃ y á»Ÿ mÃ£ giáº£m giÃ¡ '{code}': '{expiry_str}'")
        quantity = details.get('quantity')
        if isinstance(quantity, int) and details.get('used', 0) >= quantity: is_used_up = True
        if is_expired or is_used_up:
            reason = "háº¿t háº¡n" if is_expired else "háº¿t lÆ°á»£t sá»­ dá»¥ng"; invalid_codes.append(f"{code} ({reason})"); coupons.pop(code, None)
    if invalid_codes:
        logger.info(f"<tg-emoji emoji-id=\"5462956611033117422\">ðŸ§¹</tg-emoji> ÄÃ£ tá»± Ä‘á»™ng xÃ³a {len(invalid_codes)} mÃ£ giáº£m giÃ¡: {', '.join(invalid_codes)}"); await save_data()
        try:
            report_text = f"<tg-emoji emoji-id=\"5462956611033117422\">ðŸ§¹</tg-emoji> <b>BÃO CÃO Dá»ŒN Dáº¸P HÃ€NG NGÃ€Y</b>\n\nÄÃ£ tá»± Ä‘á»™ng xÃ³a <b>{len(invalid_codes)}</b> mÃ£ giáº£m giÃ¡ khÃ´ng há»£p lá»‡:\n- <code>" + "</code>\n- <code>".join(invalid_codes) + "</code>"
            await safe_send_admin(context.bot, report_text)
        except (TelegramError, ValueError, KeyError, AttributeError) as e: logger.error(f"KhÃ´ng thá»ƒ gá»­i tin nháº¯n bÃ¡o cÃ¡o dá»n dáº¹p cho admin: {e}")
    else: logger.info("CRON: KhÃ´ng cÃ³ mÃ£ giáº£m giÃ¡ nÃ o cáº§n dá»n dáº¹p.")

async def automatic_reward_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tá»± Ä‘á»™ng trao thÆ°á»Ÿng Top tuáº§n/thÃ¡ng"""
    now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    today = now.date()
    
    # --- THÆ¯á»žNG TUáº¦N (Cháº¡y vÃ o thá»© 2 hÃ ng tuáº§n) ---
    if today.weekday() == 0: # 0 = Thá»© 2
        # Láº¥y dá»¯ liá»‡u tuáº§n trÆ°á»›c (Thá»© 2 tuáº§n trÆ°á»›c -> Chá»§ nháº­t tuáº§n trÆ°á»›c)
        start_date = today - timedelta(days=7)
        end_date = today - timedelta(days=1)
        
        start_dt = datetime.combine(start_date, dt_time.min)
        end_dt = datetime.combine(end_date, dt_time.max)
        
        await process_top_buyer_reward(context, start_dt, end_dt, "WEEKLY", 2, 15)

    # --- THÆ¯á»žNG THÃNG (Cháº¡y vÃ o ngÃ y 1 hÃ ng thÃ¡ng) ---
    if today.day == 1:
        # Láº¥y dá»¯ liá»‡u thÃ¡ng trÆ°á»›c
        first_day_this_month = today
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        
        start_dt = datetime.combine(first_day_last_month, dt_time.min)
        end_dt = datetime.combine(last_day_last_month, dt_time.max)
        
        await process_top_buyer_reward(context, start_dt, end_dt, "MONTHLY", 1, 50)

async def process_top_buyer_reward(context, start_dt, end_dt, reward_type, quantity, discount_percent):
    start_ts = start_dt.timestamp()
    end_ts = end_dt.timestamp()
    
    # Lá»c Ä‘Æ¡n hÃ ng hoÃ n thÃ nh trong khoáº£ng thá»i gian
    eligible_orders = [
        o for o in order_history 
        if is_completed_order(o)
        and start_ts <= o.get("timestamp", 0) <= end_ts
    ]
    
    if not eligible_orders:
        return

    # Äáº¿m sá»‘ Ä‘Æ¡n theo user
    user_counts = Counter(
        resolved_uid for resolved_uid in (_api_get_effective_order_user_id(order) for order in eligible_orders)
        if resolved_uid
    )
    if not user_counts:
        return
        
    # Láº¥y Top 1
    top_user_id, count = user_counts.most_common(1)[0]
    
    # Táº¡o Coupon
    coupons_created = []
    for _ in range(quantity):
        # MÃ£: TOPWEEK-ID-RANDOM hoáº·c TOPMONTH-ID-RANDOM
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
    
    # Gá»­i thÃ´ng bÃ¡o cho User
    user_info = user_data_db.get(str(top_user_id), {})
    full_name = user_info.get("first_name", "KhÃ¡ch hÃ ng")
    
    period_name = "TUáº¦N" if reward_type == "WEEKLY" else "THÃNG"
    time_range_str = f"{start_dt.strftime('%d/%m')} - {end_dt.strftime('%d/%m')}"
    
    msg = (
        f"â­ï¸ <b>CHÃšC Má»ªNG TOP 1 NGÆ¯á»œI MUA HÃ€NG {period_name} QUA!</b> â­ï¸\n"
        f"<i>({time_range_str})</i>\n\n"
        f"Xin chÃ o <b>{full_name}</b>,\n"
        f"Báº¡n lÃ  ngÆ°á»i mua hÃ ng nhiá»u nháº¥t trong {period_name.lower()} vá»«a qua vá»›i <b>{count} Ä‘Æ¡n hÃ ng</b>.\n\n"
        f"<tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ</tg-emoji> <b>Pháº§n thÆ°á»Ÿng cá»§a báº¡n:</b>\n"
        f"<b>{quantity}x MÃ£ giáº£m giÃ¡ {discount_percent}%</b>\n\n"
    )
    
    for code in coupons_created:
        msg += f"<tg-emoji emoji-id=\"5377624166436445368\">ðŸŽŸï¸</tg-emoji> <code>{code}</code>\n"
        
    msg += "\n<i>(Háº¡n sá»­ dá»¥ng: 30 ngÃ y. Ãp dá»¥ng cho Ä‘Æ¡n hÃ ng tiáº¿p theo)</i>"
    
    try:
        await context.bot.send_message(top_user_id, msg, parse_mode=ParseMode.HTML)
        
        # ThÃ´ng bÃ¡o Admin
        admin_msg = (
            f"{E_SUCCESS} <b>ÄÃƒ Tá»° Äá»˜NG TRAO THÆ¯á»žNG {period_name}</b>\n\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¤</tg-emoji> <b>User:</b> {full_name} (ID: <code>{top_user_id}</code>)\n"
            f"{E_STAT} <b>ThÃ nh tÃ­ch:</b> {count} Ä‘Æ¡n\n"
            f"{E_TAG} <b>Pháº§n thÆ°á»Ÿng:</b> {quantity} mÃ£ {discount_percent}%\n"
            f"<tg-emoji emoji-id=\"5377624166436445368\">ðŸŽŸï¸</tg-emoji> <b>MÃ£:</b> {', '.join(coupons_created)}"
        )
        await safe_send_admin(context.bot, admin_msg)
        
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Lá»—i gá»­i thÆ°á»Ÿng {reward_type} cho user {top_user_id}: {e}")


