# ==============================================================================
#  AUTO SYNC RESELL JOB (Cháº¡y má»—i 30 phÃºt)
# ==============================================================================
async def auto_sync_resell_job(context):
    """
    Background job: Tá»± Ä‘á»™ng sync giÃ¡/stock tá»« SupplierSource má»—i 30 phÃºt
    - Cáº­p nháº­t giÃ¡ náº¿u SupplierSource thay Ä‘á»•i giÃ¡ gá»‘c
    - Cáº­p nháº­t stock
    - ThÃ´ng bÃ¡o Admin náº¿u cÃ³ sáº£n pháº©m háº¿t hÃ ng
    """
    resell_products = {pid: p for pid, p in products.items() if p.get("is_supplier_source_resell")}
    
    if not resell_products:
        return  # KhÃ´ng cÃ³ sáº£n pháº©m resell
    
    logger.info(f"[AUTO SYNC] Äang sync {len(resell_products)} sáº£n pháº©m resell...")
    
    updated = 0
    out_of_stock = []
    price_changed = []
    auth_failed_products = []
    stale_variants = []
    sync_errors = []
    product_state_changed = False

    # SupplierCatalog exposes one catalog endpoint, so fetch it once per cron cycle
    # instead of downloading the same catalog once for every local product.
    supplier_catalog_products = {
        pid: p
        for pid, p in resell_products.items()
        if str(p.get("resell_source") or "supplier_source").lower() == "supplier_catalog"
    }
    supplier_catalog_catalog_result = None
    supplier_catalog_catalog_by_id = {}
    if supplier_catalog_products:
        supplier_catalog_catalog_result = await supplier_catalog_get_products()
        if supplier_catalog_catalog_result.get("success"):
            supplier_catalog_catalog_by_id = {
                str(item.get("id") or "").strip(): item
                for item in supplier_catalog_catalog_result.get("products", [])
                if str(item.get("id") or "").strip()
            }
    
    for pid, p in resell_products.items():
        variant_id = p.get("supplier_source_variant_id")
        if not variant_id:
            continue
        
        try:
            if str(p.get("resell_source") or "supplier_source").lower() == "supplier_catalog":
                if not supplier_catalog_catalog_result.get("success"):
                    result = supplier_catalog_catalog_result
                else:
                    supplier_catalog_product = supplier_catalog_catalog_by_id.get(str(variant_id).strip())
                    result = (
                        _supplier_catalog_product_to_supplier_source_variant(supplier_catalog_product)
                        if supplier_catalog_product
                        else {"success": False, "error": "supplier_catalog_product_not_found", "status_code": 404}
                    )
            else:
                result = await supplier_get_variant_info(p)
            
            if result.get("success"):
                data = result.get("data", {})
                new_supplier_source_price = int(data.get("price", 0))
                new_stock = data.get("stock", 0)
                markup = p.get("markup_percent", 0)
                old_price = p.get("supplier_source_price", 0)
                old_sell_price = p.get("price", 0)
                old_stock = p.get("supplier_source_stock", 0)
                
                # Cáº­p nháº­t giÃ¡ náº¿u thay Ä‘á»•i
                if new_supplier_source_price != old_price:
                    products[pid]["supplier_source_price"] = new_supplier_source_price
                    products[pid]["price"] = int(new_supplier_source_price * (1 + markup / 100))
                    product_state_changed = True
                    price_changed.append({
                        "name": p['name'],
                        "old": old_price,
                        "new": new_supplier_source_price,
                        "old_sell_price": old_sell_price,
                        "sell_price": products[pid]["price"],
                        "markup": markup,
                    })
                
                # Cáº­p nháº­t stock
                if new_stock != old_stock:
                    products[pid]["supplier_source_stock"] = new_stock
                    product_state_changed = True
                if _supplier_source_update_purchase_block_state(
                    product_id=p.get("supplier_source_product_id"),
                    variant_id=variant_id,
                    blocked=False,
                    persist=False,
                ):
                    product_state_changed = True
                
                # Check háº¿t hÃ ng
                if new_stock == 0 and old_stock > 0:
                    out_of_stock.append(p['name'])
                
                updated += 1
            else:
                status_code = int(result.get("status_code", 0) or 0)
                error_text = str(result.get("error") or "Unknown supplier error")
                normalized_error = error_text.lower()
                source = str(p.get("resell_source") or "supplier_source").lower()
                if status_code in (401, 403):
                    auth_failed_products.append(p['name'])
                elif status_code == 404 and (
                    "variant not found" in normalized_error
                    or "supplier_catalog_product_not_found" in normalized_error
                ):
                    stale_variants.append({
                        "name": p['name'],
                        "variant_id": variant_id,
                    })
                    products.pop(pid, None)
                    product_state_changed = True
                elif _supplier_source_is_purchase_unavailable_error(error_text, status_code):
                    if _supplier_source_update_purchase_block_state(
                        product_id=p.get("supplier_source_product_id"),
                        variant_id=variant_id,
                        blocked=True,
                        reason=error_text,
                        force_stock_zero=True,
                        persist=False,
                    ):
                        product_state_changed = True
                    sync_errors.append({
                        "name": p['name'],
                        "error": f"{error_text} (da tam ngung ban)",
                    })
                else:
                    sync_errors.append({
                        "name": p['name'],
                        "error": error_text,
                    })
        except (ValueError, TypeError, KeyError, IndexError) as e:
            logger.error(f"[AUTO SYNC] Lá»—i sync {p['name']}: {e}")
            sync_errors.append({
                "name": p['name'],
                "error": str(e),
            })
    
    if product_state_changed:
        await save_data(force=True)
        logger.info("[AUTO SYNC] Supplier stock state saved")

    # The 60-second stock cron is intentionally silent on Telegram. Details
    # remain available in the system log without flooding the admin chat.
    return
    
    # ThÃ´ng bÃ¡o Admin náº¿u cÃ³ thay Ä‘á»•i quan trá»ng
    if out_of_stock or price_changed or auth_failed_products or stale_variants or sync_errors:
        msg = "<tg-emoji emoji-id=\"5462956611033117422\">ðŸ”„</tg-emoji> <b>[AUTO SYNC] Cáº¬P NHáº¬T Tá»ª NGUá»’N</b>\n\n"
        
        if price_changed:
            msg += "<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> <b>GIÃ THAY Äá»”I:</b>\n"
            for pc in price_changed[:5]:  # Max 5 items
                safe_name = html.escape(str(pc["name"]))
                markup_text = f"{float(pc['markup']):g}"
                msg += (
                    f"â€¢ <b>{safe_name}</b>\n"
                    f"  Nguá»“n: {pc['old']:,} â†’ {pc['new']:,} Â· "
                    f"BÃ¡n: {pc['old_sell_price']:,} â†’ {pc['sell_price']:,} Â· "
                    f"Markup: +{markup_text}%\n"
                )
            msg += "\n"
        
        if out_of_stock:
            msg += "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>Háº¾T HÃ€NG:</b>\n"
            for name in out_of_stock[:5]:  # Max 5 items
                msg += f"â€¢ {html.escape(str(name))}\n"
            msg += "\n"

        if auth_failed_products:
            msg += (
                "âŒ "
                "<b>SUPPLIER_SOURCE AUTH Lá»–I:</b>\n"
                f"Token SupplierSource cÃ³ thá»ƒ khÃ´ng há»£p lá»‡ hoáº·c Ä‘Ã£ háº¿t háº¡n. áº¢nh hÆ°á»Ÿng {len(auth_failed_products)} sáº£n pháº©m.\n\n"
            )

        if stale_variants:
            msg += "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>VARIANT Bá»Š XÃ“A UPSTREAM:</b>\n"
            for stale in stale_variants[:5]:
                msg += (
                    f"â€¢ {html.escape(str(stale['name']))} â†’ "
                    f"<code>{html.escape(str(stale['variant_id']))}</code>\n"
                )
            msg += "\n"

        if sync_errors:
            msg += "âŒ <b>Lá»–I KHÃC:</b>\n"
            for sync_error in sync_errors[:5]:
                msg += (
                    f"â€¢ {html.escape(str(sync_error['name']))}: "
                    f"{html.escape(str(sync_error['error']))}\n"
                )
        
        try:
            await context.bot.send_message(
                ADMIN_USER_ID,
                msg,
                parse_mode=ParseMode.HTML
            )
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.error(f"[AUTO SYNC] Lá»—i gá»­i thÃ´ng bÃ¡o Admin: {e}")

# ==============================================================================
#  ADMIN COMMAND WRAPPER (FIX Lá»–I THIáº¾U HÃ€M)
# ==============================================================================
async def auto_sync_ctt_job(context):
    refresh_ctt_runtime_config()
    """Background job: mirror toÃ n bá»™ catalog social tá»« SocialSource."""
    if not SOCIAL_SOURCE_API_KEY:
        return

    logger.info("[AUTO SYNC][SOCIAL_SOURCE] Dang sync catalog social...")
    sync_result = await ctt_sync_catalog(force_refresh=True, log_error=False)
    if not sync_result.get("success"):
        error_text = str(sync_result.get("error") or "unknown_error")
        logger.warning(f"[AUTO SYNC][SOCIAL_SOURCE] Sync that bai: {error_text}")
        try:
            await safe_send_admin(
                context.bot,
                f"{E_LIMIT} <b>[AUTO SYNC][SOCIAL_SOURCE] THAT BAI</b>\n"
                f"Loi: <code>{html.escape(error_text)}</code>",
            )
        except (TelegramError, ValueError, KeyError, AttributeError):
            pass
        return

    logger.info(
        "[AUTO SYNC][SOCIAL_SOURCE] Done | total=%s created=%s updated=%s inactive=%s invalid=%s",
        int(sync_result.get("total_services", 0) or 0),
        int(sync_result.get("created", 0) or 0),
        int(sync_result.get("updated", 0) or 0),
        int(sync_result.get("inactive", 0) or 0),
        int(sync_result.get("invalid", 0) or 0),
    )

    should_notify = any(
        int(sync_result.get(field_name, 0) or 0) > 0
        for field_name in ("created", "reactivated", "inactive")
    )
    if not should_notify:
        return

    errors = list(sync_result.get("errors") or [])
    error_block = ""
    if errors:
        preview = "\n".join(f"â€¢ <code>{html.escape(str(item))}</code>" for item in errors[:5])
        error_block = f"\nLoi bo qua:\n{preview}"

    try:
        await safe_send_admin(
            context.bot,
            f"{E_SUCCESS} <b>[AUTO SYNC][SOCIAL_SOURCE] CAP NHAT CATALOG SOCIAL</b>\n"
            f"Total: <b>{int(sync_result.get('total_services', 0) or 0)}</b>\n"
            f"Created: <b>{int(sync_result.get('created', 0) or 0)}</b>\n"
            f"Reactivated: <b>{int(sync_result.get('reactivated', 0) or 0)}</b>\n"
            f"Inactive: <b>{int(sync_result.get('inactive', 0) or 0)}</b>\n"
            f"Invalid: <b>{int(sync_result.get('invalid', 0) or 0)}</b>\n"
            f"Active catalog: <b>{int(sync_result.get('active_products', 0) or 0)}</b>"
            f"{error_block}",
        )
    except (TelegramError, ValueError, KeyError, AttributeError):
        pass


async def auto_refresh_ctt_orders_job(context):
    refresh_ctt_runtime_config()
    """Refresh active SOCIAL_SOURCE orders and apply automatic refunds for canceled/partial results."""
    if not SOCIAL_SOURCE_API_KEY:
        return

    now_ts = time.time()
    scanned = 0
    changed = 0
    refunded = 0
    max_scan = 10
    min_refresh_age = 900

    for order_data in reversed(order_history):
        if scanned >= max_scan:
            break
        if not isinstance(order_data, dict) or not order_data.get("is_social_source_service"):
            continue
        if order_data.get("refunded_at"):
            continue

        supplier_status = str(order_data.get("ctt_supplier_status") or "").strip().casefold()
        if supplier_status in {"completed", "complete"}:
            continue

        try:
            last_refreshed_at = float(order_data.get("ctt_status_refreshed_at") or 0)
        except (TypeError, ValueError):
            last_refreshed_at = 0
        if last_refreshed_at and (now_ts - last_refreshed_at) < min_refresh_age:
            continue

        try:
            before_refund = int(order_data.get("ctt_auto_refunded_amount", 0) or 0)
        except (TypeError, ValueError):
            before_refund = 0

        result = await refresh_ctt_order_status(order_data, persist=False)
        scanned += 1
        if result.get("changed"):
            changed += 1

        try:
            after_refund = int(order_data.get("ctt_auto_refunded_amount", 0) or 0)
        except (TypeError, ValueError):
            after_refund = before_refund
        if after_refund > before_refund:
            refunded += 1

    if changed:
        await save_data(force=True, tables=[HISTORY_FILE])
        logger.info(
            "[AUTO SOCIAL_SOURCE STATUS] refreshed=%s changed=%s refunded=%s",
            scanned,
            changed,
            refunded,
        )


async def admin_command_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, func) -> None:
    """Wrapper Ä‘á»ƒ báº£o vá»‡ cÃ¡c lá»‡nh Admin"""
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        # KhÃ´ng pháº£n há»“i hoáº·c bÃ¡o lá»—i
        return
        
    try:
        await func(update, context)
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Lá»—i khi thá»±c thi lá»‡nh Admin: {e}", exc_info=True)
        logger.error(f"Error in backup db: {e}"); await update.message.reply_text("âŒ CÃ³ lá»—i xáº£y ra khi backup, vui lÃ²ng kiá»ƒm tra logs.")



# ==============================================================================
#  HELPER: Batch Error Reporting (Job Queue)
# ==============================================================================
# ==============================================================================
#  HELPER: Unresolved Error Reminder (Job Queue)
# ==============================================================================
async def send_batched_error_reports(context: ContextTypes.DEFAULT_TYPE):
    """
    Cron Job: Nháº¯c nhá»Ÿ Admin vá» cÃ¡c Ä‘Æ¡n bÃ¡o lá»—i CHÆ¯A Xá»¬ LÃ (Unresolved)
    """
    global pending_error_reports
    
    # Filter unresolved reports
    unresolved = [r for r in pending_error_reports if not r.get('resolved', False)]
    
    if not unresolved:
        # Cleanup resolved ones to save memory
        pending_error_reports = [] 
        return
    
    # Gá»­i thÃ´ng bÃ¡o nháº¯c nhá»Ÿ
    count = len(unresolved)
    summary_msg = f"{E_TIP} <b>Sáº¾P Æ I! CÃ’N {count} ÄÆ N Lá»–I CHÆ¯A Xá»¬ LÃ:</b>\n\n"
    
    for i, report in enumerate(unresolved, 1):
        waiting_time_min = int((time.time() - report['timestamp']) / 60)
        time_str = f"{waiting_time_min}p trÆ°á»›c" if waiting_time_min < 60 else f"{int(waiting_time_min/60)}h trÆ°á»›c"
        
        summary_msg += (
            f"{i}. <code>{report['order_code']}</code> - {html.escape(report['product_name'])}\n"
            f"   {E_USER} {html.escape(report['username'] or 'N/A')} (BÃ¡o láº§n {report.get('report_count', 1)})\n"
            f"   {E_CALENDAR} Mua: {report.get('purchase_date', 'N/A')} - <tg-emoji emoji-id=\"5213349767672769194\">â°</tg-emoji> {time_str}\n"
        )
        
    summary_msg += "\n<tg-emoji emoji-id=\"6186252635805323641\">ðŸ‘‡</tg-emoji> Vui lÃ²ng check tin nháº¯n trÃªn Ä‘á»ƒ xá»­ lÃ½!"
    
    try:
        await safe_send_admin(context.bot, summary_msg)
    except (ValueError, TypeError, KeyError, IndexError) as e:
        logger.error(f"Cannot send reminder summary: {e}")
    
    # Cleanup: Keep only unresolved
    pending_error_reports = unresolved
    
async def auto_remind_email_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Cron Job: Tá»± Ä‘á»™ng nháº¯c user nháº­p email náº¿u quÃªn (Má»—i 5 phÃºt)
    """
    current_time = time.time()
    
    # Iterate copy to avoid runtime error if dict changes
    for order_code, order in list(pending_manual_orders.items()):
        
        # Chá»‰ check Ä‘Æ¡n Ä‘ang chá» email
        if order.get('status') == 'awaiting_email' and not order.get('email'):
            
            user_id = order.get('user_id')
            start_time = order.get('timestamp', 0)
            last_reminded = order.get('last_reminded', 0)
            
            # Äiá»u kiá»‡n nháº¯c:
            # 1. ÄÃ£ qua 2 phÃºt ká»ƒ tá»« lÃºc mua (Ä‘á»ƒ há» ká»‹p nháº­p)
            # 2. ÄÃ£ qua 15 phÃºt ká»ƒ tá»« láº§n nháº¯c cuá»‘i (trÃ¡nh spam)
            # 3. Tá»•ng thá»i gian chá» < 24h (sau 24h thÃ´i nháº¯c)
            
            minutes_waiting = (current_time - start_time) / 60
            minutes_since_last = (current_time - last_reminded) / 60
            
            if minutes_waiting > 2 and minutes_since_last > 15 and minutes_waiting < 1440:
                try:
                    product_name = order.get('product_name', 'Sáº£n pháº©m')
                    
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"<tg-emoji emoji-id=\"5447644880824181073\">ðŸ””</tg-emoji> <b>THÃ”NG BÃO Tá»ª BOT</b>\n\n"
                            f"Báº¡n Æ¡i, mÃ¬nh tháº¥y báº¡n vá»«a mua <b>{product_name}</b> nhÆ°ng chÆ°a nháº­p Email nháº­n hÃ ng nÃ¨.\n\n"
                            f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> <b>MÃ£ Ä‘Æ¡n:</b> <code>{order_code}</code>\n\n"
                            f"<tg-emoji emoji-id=\"6186252635805323641\">ðŸ‘‰</tg-emoji> Vui lÃ²ng <b>nháº­p Ä‘á»‹a chá»‰ Email</b> cá»§a báº¡n vÃ o Ä‘Ã¢y ngay nhÃ©!\n\n"
                            f"<b>CÃ¡ch gá»­i email:</b>\n"
                            f"â€¢ Reply tin nháº¯n nÃ y vá»›i email cá»§a báº¡n\n"
                            f"â€¢ Hoáº·c dÃ¹ng lá»‡nh: <code>/guimail email@abc.com</code>"
                        ),
                        parse_mode=ParseMode.HTML
                    )
                    
                    # Update status
                    pending_manual_orders[order_code]['last_reminded'] = current_time
                    await save_data()
                    logger.info(f"<tg-emoji emoji-id=\"5447644880824181073\">ðŸ””</tg-emoji> ÄÃ£ nháº¯c user {user_id} nháº­p email cho Ä‘Æ¡n {order_code}")
                    
                except (TelegramError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(f"KhÃ´ng thá»ƒ nháº¯c user {user_id}: {e}")
                    # CÃ³ thá»ƒ Ä‘Ã¡nh dáº¥u failed Ä‘á»ƒ khÃ´ng nháº¯c láº¡i ngay
                    pending_manual_orders[order_code]['last_reminded'] = current_time # Skip this turn

# ==============================================================================
#  VIP/RANK SYSTEM â€” Há»‡ thá»‘ng cáº¥p báº­c theo sá»‘ Ä‘Æ¡n hoÃ n thÃ nh
# ==============================================================================

VIP_RANKS = [
    {"name": "â­ï¸ Äá»“ng",         "min_orders": 0,  "min_spent": 0,        "discount": 0},
    {"name": "â­ï¸ Báº¡c",          "min_orders": 0,  "min_spent": 500000,   "discount": 0},
    {"name": "â­ï¸ VÃ ng",         "min_orders": 0,  "min_spent": 1000000,  "discount": 0},
    {"name": "<tg-emoji emoji-id=\"5240228673738527951\">ðŸ’Ž</tg-emoji> Kim CÆ°Æ¡ng",    "min_orders": 0,  "min_spent": 5000000,  "discount": 0},
    {"name": "â­ï¸ Cao Thá»§",      "min_orders": 0,  "min_spent": 10000000, "discount": 0},
]


def _get_previous_month_maintenance_window(reference_dt=None):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    now = reference_dt.astimezone(tz) if reference_dt else datetime.now(tz)
    current_month_start = datetime(now.year, now.month, 1, tzinfo=tz)
    last_day_previous_month = current_month_start.date() - timedelta(days=1)
    previous_month_start = datetime(
        last_day_previous_month.year,
        last_day_previous_month.month,
        1,
        tzinfo=tz,
    )
    return previous_month_start, current_month_start, previous_month_start.strftime("%m/%Y")


def _calculate_orders_spent_in_period(orders, start_ts: float, end_ts: float) -> int:
    total_spent = 0
    for order in orders:
        if not is_completed_order(order):
            continue
        try:
            order_ts = float(order.get("timestamp", 0) or 0)
            if start_ts <= order_ts < end_ts:
                total_spent += int(order.get("amount", 0) or 0)
        except (ValueError, TypeError):
            continue
    return total_spent


def get_user_vip_rank(user_id) -> dict:
    """TÃ­nh rank VIP dá»±a trÃªn tá»•ng Ä‘Æ¡n hoÃ n thÃ nh vÃ  tá»•ng chi tiÃªu."""
    merged_orders = {}
    for order in user_order_index.get(str(user_id), []):
        order_code = str(order.get("order_code") or "")
        if order_code:
            merged_orders[order_code] = order
    for order in _api_get_orders_for_user(user_id):
        order_code = str(order.get("order_code") or "")
        if order_code:
            merged_orders[order_code] = order
    user_orders = list(merged_orders.values())
    completed = [o for o in user_orders if is_completed_order(o)]
    total_orders = len(completed)
    total_spent = sum(o.get('amount', 0) for o in completed)

    base_rank_index = 0
    next_lifetime_rank = None
    for i, rank in enumerate(VIP_RANKS):
        if total_orders >= rank["min_orders"] and total_spent >= rank["min_spent"]:
            base_rank_index = i
            next_lifetime_rank = VIP_RANKS[i + 1] if i + 1 < len(VIP_RANKS) else None
        else:
            next_lifetime_rank = rank
            break

    previous_month_start, current_month_start, period_label = _get_previous_month_maintenance_window()
    monthly_spend = _calculate_orders_spent_in_period(
        user_orders,
        previous_month_start.timestamp(),
        current_month_start.timestamp(),
    )
    maintenance_status = {
        "period_label": period_label,
        "monthly_spend": monthly_spend,
        "minimum_required": VIP_MONTHLY_MAINTENANCE_MIN_SPEND,
        "met_requirement": monthly_spend >= VIP_MONTHLY_MAINTENANCE_MIN_SPEND,
        "remaining_to_maintain": max(0, VIP_MONTHLY_MAINTENANCE_MIN_SPEND - monthly_spend),
    }
    demoted_by_maintenance = base_rank_index > 0 and not maintenance_status["met_requirement"]
    effective_rank_index = max(0, base_rank_index - 1) if demoted_by_maintenance else base_rank_index
    current_rank = VIP_RANKS[effective_rank_index]
    base_rank = VIP_RANKS[base_rank_index]

    if demoted_by_maintenance:
        next_rank = base_rank
    else:
        next_rank = next_lifetime_rank

    return {
        "rank": current_rank,
        "base_rank": base_rank,
        "next_rank": next_rank,
        "total_orders": total_orders,
        "total_spent": total_spent,
        "discount_percent": 0,
        "demoted_by_maintenance": demoted_by_maintenance,
        "maintenance_status": maintenance_status,
    }

def apply_vip_discount(user_id, original_price: int) -> tuple:
    """Tráº£ vá» (giÃ¡_sau_giáº£m, pháº§n_trÄƒm_giáº£m, tÃªn_rank)."""
    vip = get_user_vip_rank(user_id)
    return original_price, 0, vip["rank"]["name"]


# ==============================================================================
#  /UPTIME â€” Bot uptime + system stats
# ==============================================================================

async def uptime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hiá»ƒn thá»‹ thá»i gian bot Ä‘Ã£ cháº¡y vÃ  thÃ´ng tin há»‡ thá»‘ng."""
    now = datetime.now()
    delta = now - BOT_START_TIME
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_str = ""
    if days > 0:
        uptime_str += f"{days} ngÃ y "
    uptime_str += f"{hours}h {minutes}m {seconds}s"
    
    # System info
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Process info
        proc = psutil.Process()
        proc_mem = proc.memory_info().rss / (1024 * 1024)  # MB
        
        sys_info = (
            f"\n<tg-emoji emoji-id=\"6059654836918423763\">ðŸ“Š</tg-emoji> <b>Há»† THá»NG</b>\n"
            f"â”œ CPU: <b>{cpu_percent}%</b>\n"
            f"â”œ RAM: <b>{mem.percent}%</b> ({mem.used // (1024**2):,}/{mem.total // (1024**2):,} MB)\n"
            f"â”œ Disk: <b>{disk.percent}%</b> ({disk.used // (1024**3):,}/{disk.total // (1024**3):,} GB)\n"
            f"â”” Bot RAM: <b>{proc_mem:.1f} MB</b>\n"
        )
    except ImportError:
        sys_info = "\n<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <i>CÃ i psutil Ä‘á»ƒ xem thÃ´ng tin há»‡ thá»‘ng: pip install psutil</i>\n"
    except Exception as e:
        logger.exception(f"Loi doc system info: {e}", exc_info=e)
        sys_info = f"\n<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <i>Lá»—i Ä‘á»c system info: {e}</i>\n"
    
    # Bot stats
    total_users = len(user_data_db)
    total_orders = len(order_history)
    total_products = len(products)
    
    msg = (
        f"<tg-emoji emoji-id=\"5303145396254563405\">ðŸ¤–</tg-emoji> <b>BOT STATUS</b>\n"
        f"{'â”' * 28}\n\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">â±ï¸</tg-emoji> Uptime: <b>{uptime_str}</b>\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">ðŸ•</tg-emoji> Khá»Ÿi cháº¡y: {BOT_START_TIME.strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"{sys_info}\n"
        f"<tg-emoji emoji-id=\"6059654836918423763\">ðŸ“ˆ</tg-emoji> <b>THá»NG KÃŠ</b>\n"
        f"â”œ Users: <b>{total_users:,}</b>\n"
        f"â”œ ÄÆ¡n hÃ ng: <b>{total_orders:,}</b>\n"
        f"â”œ Sáº£n pháº©m: <b>{total_products}</b>\n"
        f"â”” Pending: <b>{len(pending_orders)}</b>\n"
    )
    
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# ==============================================================================
#  PAYMENT REMINDER JOB â€” Nháº¯c thanh toÃ¡n Ä‘Æ¡n pending > 15 phÃºt  
# ==============================================================================

_payment_reminded = set()  # Track Ä‘Ã£ nháº¯c Ä‘á»ƒ khÃ´ng spam

async def payment_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cron job: Nháº¯c user thanh toÃ¡n náº¿u Ä‘Æ¡n pending > 15 phÃºt."""
    if not pending_orders:
        return
    
    current_time = time.time()
    REMIND_AFTER_SECONDS = 15 * 60  # 15 phÃºt
    MAX_PENDING_SECONDS = 60 * 60   # 1 giá» â€” auto há»§y
    
    orders_to_remove = []
    
    for order_code, order_details in list(pending_orders.items()):
        start_time = order_details.get('timestamp', 0)
        if not start_time:
            continue
        
        elapsed = current_time - start_time
        user_id = order_details.get('user_id')
        if not user_id:
            continue
        
        reminder_key = f"{order_code}_{user_id}"
        
        # QuÃ¡ 1 giá» â†’ tá»± há»§y
        if elapsed > MAX_PENDING_SECONDS:
            orders_to_remove.append(order_code)
            _payment_reminded.discard(reminder_key)
            try:
                product_name = order_details.get('product_name') or order_details.get('product', 'Sáº£n pháº©m')
                await context.bot.send_message(
                    user_id,
                    f"<tg-emoji emoji-id=\"5213349767672769194\">â°</tg-emoji> <b>ÄÆ N HÃ€NG ÄÃƒ Háº¾T Háº N</b>\n\n"
                    f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ†”</tg-emoji> MÃ£: <code>{html.escape(str(order_code))}</code>\n"
                    f"<tg-emoji emoji-id=\"6260059243605398502\">ðŸ“Œ</tg-emoji> SP: {html.escape(str(product_name))}\n\n"
                    "ÄÆ¡n hÃ ng Ä‘Ã£ bá»‹ há»§y do quÃ¡ thá»i gian thanh toÃ¡n (60 phÃºt).\n"
                    "Vui lÃ²ng Ä‘áº·t láº¡i náº¿u cáº§n.",
                    parse_mode=ParseMode.HTML
                )
            except TelegramError:
                pass  # User cÃ³ thá»ƒ Ä‘Ã£ block bot
            except Exception as e:
                logger.exception(f"Payment reminder send_message cancelled order failed for user {user_id}: {e}", exc_info=e)
            continue
        
        # QuÃ¡ 15 phÃºt + chÆ°a nháº¯c â†’ gá»­i nháº¯c nhá»Ÿ
        if elapsed > REMIND_AFTER_SECONDS and reminder_key not in _payment_reminded:
            _payment_reminded.add(reminder_key)
            try:
                product_name = order_details.get('product_name') or order_details.get('product', 'Sáº£n pháº©m')
                amount = order_details.get('amount', 0)
                minutes_left = max(1, int((MAX_PENDING_SECONDS - elapsed) / 60))
                await context.bot.send_message(
                    user_id,
                    f"<tg-emoji emoji-id=\"5213349767672769194\">â°</tg-emoji> <b>NHáº®C NHá»ž THANH TOÃN</b>\n\n"
                    f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ†”</tg-emoji> MÃ£ Ä‘Æ¡n: <code>{html.escape(str(order_code))}</code>\n"
                    f"<tg-emoji emoji-id=\"6260059243605398502\">ðŸ“Œ</tg-emoji> Sáº£n pháº©m: {html.escape(str(product_name))}\n"
                    f"<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> Sá»‘ tiá»n: <b>{amount:,} VNÄ</b>\n\n"
                    f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Báº¡n chÆ°a thanh toÃ¡n Ä‘Æ¡n hÃ ng nÃ y.\n"
                    f"ÄÆ¡n sáº½ tá»± há»§y sau <b>{minutes_left} phÃºt</b> náº¿u khÃ´ng nháº­n Ä‘Æ°á»£c thanh toÃ¡n.\n\n"
                    "<tg-emoji emoji-id=\"5460753627817723162\">ðŸ’¡</tg-emoji> Náº¿u Ä‘Ã£ chuyá»ƒn khoáº£n, vui lÃ²ng Ä‘á»£i 1-2 phÃºt Ä‘á»ƒ há»‡ thá»‘ng xÃ¡c nháº­n.",
                    parse_mode=ParseMode.HTML
                )
            except TelegramError:
                pass
            except Exception as e:
                logger.exception(f"Payment reminder send_message remind order failed for user {user_id}: {e}", exc_info=e)
    
    # XÃ³a cÃ¡c Ä‘Æ¡n háº¿t háº¡n
    for code in orders_to_remove:
        pending_orders.pop(code, None)
    
    if orders_to_remove:
        create_background_task(save_data())
        logger.info(f"<tg-emoji emoji-id=\"5213349767672769194\">â°</tg-emoji> Payment reminder: ÄÃ£ há»§y {len(orders_to_remove)} Ä‘Æ¡n háº¿t háº¡n.")

# ==============================================================================
#  /RANK â€” Xem VIP rank cÃ¡ nhÃ¢n
# ==============================================================================

async def rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hiá»ƒn thá»‹ VIP rank cá»§a user."""
    from app.services.games_withdrawals_db import check_if_banned
    if await check_if_banned(update): return
    
    user_id = update.effective_user.id
    vip = get_user_vip_rank(user_id)
    
    rank = vip["rank"]
    base_rank = vip.get("base_rank") or rank
    next_rank = vip["next_rank"]
    maintenance_status = vip.get("maintenance_status") or {}
    
    msg = (
        f"â­ï¸ <b>Háº NG THÃ€NH VIÃŠN Cá»¦A Báº N</b>\n"
        f"{'â”' * 28}\n\n"
        f"â­ï¸ Rank: <b>{rank['name']}</b>\n"
        f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> Tá»•ng Ä‘Æ¡n: <b>{vip['total_orders']}</b>\n"
        f"<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> Tá»•ng chi: <b>{vip['total_spent']:,} VNÄ</b>\n"
        f"<tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ</tg-emoji> Æ¯u Ä‘Ã£i: <b>KhÃ´ng cÃ²n giáº£m giÃ¡ theo rank</b>\n"
    )

    if vip.get("demoted_by_maintenance"):
        msg += (
            f"\n<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> "
            f"ThÃ¡ng {maintenance_status.get('period_label', 'trÆ°á»›c')} báº¡n chá»‰ chi "
            f"<b>{maintenance_status.get('monthly_spend', 0):,} VNÄ</b>, dÆ°á»›i má»©c duy trÃ¬ "
            f"<b>{VIP_MONTHLY_MAINTENANCE_MIN_SPEND:,} VNÄ</b> nÃªn Ä‘ang bá»‹ tá»¥t 1 báº­c.\n"
            f"<tg-emoji emoji-id=\"5972022360025336988\">â¬†ï¸</tg-emoji> "
            f"Cáº§n chi tá»‘i thiá»ƒu <b>{maintenance_status.get('remaining_to_maintain', 0):,} VNÄ</b> "
            f"trong thÃ¡ng nÃ y Ä‘á»ƒ láº¥y láº¡i <b>{base_rank['name']}</b> vÃ o thÃ¡ng sau.\n"
        )
    if next_rank:
        if vip.get("demoted_by_maintenance"):
            msg += (
                f"\n<tg-emoji emoji-id=\"5972022360025336988\">â¬†ï¸</tg-emoji> <b>Rank cáº§n láº¥y láº¡i: {next_rank['name']}</b>\n"
                f"â”” Äiá»u kiá»‡n: thÃ¡ng nÃ y chi tá»‘i thiá»ƒu <b>{VIP_MONTHLY_MAINTENANCE_MIN_SPEND:,} VNÄ</b>\n"
            )
        else:
            orders_need = max(0, next_rank["min_orders"] - vip["total_orders"])
            spent_need = max(0, next_rank["min_spent"] - vip["total_spent"])
            msg += (
                f"\n<tg-emoji emoji-id=\"5972022360025336988\">â¬†ï¸</tg-emoji> <b>Rank tiáº¿p theo: {next_rank['name']}</b>\n"
                f"â”œ Cáº§n thÃªm: <b>{orders_need}</b> Ä‘Æ¡n hÃ ng\n"
                f"â”” Cáº§n chi thÃªm: <b>{spent_need:,} VNÄ</b>\n"
            )
    else:
        msg += "\n<tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ‰</tg-emoji> <b>Báº¡n Ä‘Ã£ Ä‘áº¡t háº¡ng cao nháº¥t!</b> <tg-emoji emoji-id=\"6124902618574625426\">ðŸ‘‘</tg-emoji>\n"
    
    # Báº£ng xáº¿p háº¡ng
    msg += (
        f"\n{'â”' * 28}\n"
        "<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“‹</tg-emoji> <b>CÃC Cáº¤P Báº¬C:</b>\n"
    )
    for r in VIP_RANKS:
        marker = " â† Báº¡n" if r["name"] == rank["name"] else ""
        msg += f"  {r['name']} â€” {r['min_orders']}+ Ä‘Æ¡n{marker}\n"
    msg += f"\n<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Quy táº¯c duy trÃ¬: náº¿u thÃ¡ng trÆ°á»›c chi dÆ°á»›i <b>{VIP_MONTHLY_MAINTENANCE_MIN_SPEND:,} VNÄ</b> thÃ¬ sáº½ tá»¥t 1 báº­c trong thÃ¡ng nÃ y."
    
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# ==============================================================================
#  HÃ€M MAIN (KHá»žI CHáº Y BOT)
# ==============================================================================

