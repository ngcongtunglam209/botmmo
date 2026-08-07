# ==============================================================================
#  AUTO SYNC RESELL JOB (Chạy mỗi 30 phút)
# ==============================================================================
async def auto_sync_resell_job(context):
    """
    Background job: Tự động sync giá/stock từ SupplierSource mỗi 30 phút
    - Cập nhật giá nếu SupplierSource thay đổi giá gốc
    - Cập nhật stock
    - Thông báo Admin nếu có sản phẩm hết hàng
    """
    resell_products = {pid: p for pid, p in products.items() if p.get("is_supplier_source_resell")}
    
    if not resell_products:
        return  # Không có sản phẩm resell
    
    logger.info(f"[AUTO SYNC] Đang sync {len(resell_products)} sản phẩm resell...")
    
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
                
                # Cập nhật giá nếu thay đổi
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
                
                # Cập nhật stock
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
                
                # Check hết hàng
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
            logger.error(f"[AUTO SYNC] Lỗi sync {p['name']}: {e}")
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
    
    # Thông báo Admin nếu có thay đổi quan trọng
    if out_of_stock or price_changed or auth_failed_products or stale_variants or sync_errors:
        msg = "<tg-emoji emoji-id=\"5462956611033117422\">🔄</tg-emoji> <b>[AUTO SYNC] CẬP NHẬT TỪ NGUỒN</b>\n\n"
        
        if price_changed:
            msg += "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>GIÁ THAY ĐỔI:</b>\n"
            for pc in price_changed[:5]:  # Max 5 items
                safe_name = html.escape(str(pc["name"]))
                markup_text = f"{float(pc['markup']):g}"
                msg += (
                    f"• <b>{safe_name}</b>\n"
                    f"  Nguồn: {pc['old']:,} → {pc['new']:,} · "
                    f"Bán: {pc['old_sell_price']:,} → {pc['sell_price']:,} · "
                    f"Markup: +{markup_text}%\n"
                )
            msg += "\n"
        
        if out_of_stock:
            msg += "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>HẾT HÀNG:</b>\n"
            for name in out_of_stock[:5]:  # Max 5 items
                msg += f"• {html.escape(str(name))}\n"
            msg += "\n"

        if auth_failed_products:
            msg += (
                "❌ "
                "<b>SUPPLIER_SOURCE AUTH LỖI:</b>\n"
                f"Token SupplierSource có thể không hợp lệ hoặc đã hết hạn. Ảnh hưởng {len(auth_failed_products)} sản phẩm.\n\n"
            )

        if stale_variants:
            msg += "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>VARIANT BỊ XÓA UPSTREAM:</b>\n"
            for stale in stale_variants[:5]:
                msg += (
                    f"• {html.escape(str(stale['name']))} → "
                    f"<code>{html.escape(str(stale['variant_id']))}</code>\n"
                )
            msg += "\n"

        if sync_errors:
            msg += "❌ <b>LỖI KHÁC:</b>\n"
            for sync_error in sync_errors[:5]:
                msg += (
                    f"• {html.escape(str(sync_error['name']))}: "
                    f"{html.escape(str(sync_error['error']))}\n"
                )
        
        try:
            await context.bot.send_message(
                ADMIN_USER_ID,
                msg,
                parse_mode=ParseMode.HTML
            )
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.error(f"[AUTO SYNC] Lỗi gửi thông báo Admin: {e}")

# ==============================================================================
#  ADMIN COMMAND WRAPPER (FIX LỖI THIẾU HÀM)
# ==============================================================================
async def auto_sync_ctt_job(context):
    refresh_ctt_runtime_config()
    """Background job: mirror toàn bộ catalog social từ SocialSource."""
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
        preview = "\n".join(f"• <code>{html.escape(str(item))}</code>" for item in errors[:5])
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
    """Wrapper để bảo vệ các lệnh Admin"""
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        # Không phản hồi hoặc báo lỗi
        return
        
    try:
        await func(update, context)
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Lỗi khi thực thi lệnh Admin: {e}", exc_info=True)
        logger.error(f"Error in backup db: {e}"); await update.message.reply_text("❌ Có lỗi xảy ra khi backup, vui lòng kiểm tra logs.")



# ==============================================================================
#  HELPER: Batch Error Reporting (Job Queue)
# ==============================================================================
# ==============================================================================
#  HELPER: Unresolved Error Reminder (Job Queue)
# ==============================================================================
async def send_batched_error_reports(context: ContextTypes.DEFAULT_TYPE):
    """
    Cron Job: Nhắc nhở Admin về các đơn báo lỗi CHƯA XỬ LÝ (Unresolved)
    """
    global pending_error_reports
    
    # Filter unresolved reports
    unresolved = [r for r in pending_error_reports if not r.get('resolved', False)]
    
    if not unresolved:
        # Cleanup resolved ones to save memory
        pending_error_reports = [] 
        return
    
    # Gửi thông báo nhắc nhở
    count = len(unresolved)
    summary_msg = f"{E_TIP} <b>SẾP ƠI! CÒN {count} ĐƠN LỖI CHƯA XỬ LÝ:</b>\n\n"
    
    for i, report in enumerate(unresolved, 1):
        waiting_time_min = int((time.time() - report['timestamp']) / 60)
        time_str = f"{waiting_time_min}p trước" if waiting_time_min < 60 else f"{int(waiting_time_min/60)}h trước"
        
        summary_msg += (
            f"{i}. <code>{report['order_code']}</code> - {html.escape(report['product_name'])}\n"
            f"   {E_USER} {html.escape(report['username'] or 'N/A')} (Báo lần {report.get('report_count', 1)})\n"
            f"   {E_CALENDAR} Mua: {report.get('purchase_date', 'N/A')} - <tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> {time_str}\n"
        )
        
    summary_msg += "\n<tg-emoji emoji-id=\"6186252635805323641\">👇</tg-emoji> Vui lòng check tin nhắn trên để xử lý!"
    
    try:
        await safe_send_admin(context.bot, summary_msg)
    except (ValueError, TypeError, KeyError, IndexError) as e:
        logger.error(f"Cannot send reminder summary: {e}")
    
    # Cleanup: Keep only unresolved
    pending_error_reports = unresolved
    
async def auto_remind_email_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Cron Job: Tự động nhắc user nhập email nếu quên (Mỗi 5 phút)
    """
    current_time = time.time()
    
    # Iterate copy to avoid runtime error if dict changes
    for order_code, order in list(pending_manual_orders.items()):
        
        # Chỉ check đơn đang chờ email
        if order.get('status') == 'awaiting_email' and not order.get('email'):
            
            user_id = order.get('user_id')
            start_time = order.get('timestamp', 0)
            last_reminded = order.get('last_reminded', 0)
            
            # Điều kiện nhắc:
            # 1. Đã qua 2 phút kể từ lúc mua (để họ kịp nhập)
            # 2. Đã qua 15 phút kể từ lần nhắc cuối (tránh spam)
            # 3. Tổng thời gian chờ < 24h (sau 24h thôi nhắc)
            
            minutes_waiting = (current_time - start_time) / 60
            minutes_since_last = (current_time - last_reminded) / 60
            
            if minutes_waiting > 2 and minutes_since_last > 15 and minutes_waiting < 1440:
                try:
                    product_name = order.get('product_name', 'Sản phẩm')
                    
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> <b>THÔNG BÁO TỪ BOT</b>\n\n"
                            f"Bạn ơi, mình thấy bạn vừa mua <b>{product_name}</b> nhưng chưa nhập Email nhận hàng nè.\n\n"
                            f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n\n"
                            f"<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Vui lòng <b>nhập địa chỉ Email</b> của bạn vào đây ngay nhé!\n\n"
                            f"<b>Cách gửi email:</b>\n"
                            f"• Reply tin nhắn này với email của bạn\n"
                            f"• Hoặc dùng lệnh: <code>/guimail email@abc.com</code>"
                        ),
                        parse_mode=ParseMode.HTML
                    )
                    
                    # Update status
                    pending_manual_orders[order_code]['last_reminded'] = current_time
                    await save_data()
                    logger.info(f"<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> Đã nhắc user {user_id} nhập email cho đơn {order_code}")
                    
                except (TelegramError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(f"Không thể nhắc user {user_id}: {e}")
                    # Có thể đánh dấu failed để không nhắc lại ngay
                    pending_manual_orders[order_code]['last_reminded'] = current_time # Skip this turn

# ==============================================================================
#  VIP/RANK SYSTEM — Hệ thống cấp bậc theo số đơn hoàn thành
# ==============================================================================

VIP_RANKS = [
    {"name": "⭐️ Đồng",         "min_orders": 0,  "min_spent": 0,        "discount": 0},
    {"name": "⭐️ Bạc",          "min_orders": 0,  "min_spent": 500000,   "discount": 0},
    {"name": "⭐️ Vàng",         "min_orders": 0,  "min_spent": 1000000,  "discount": 0},
    {"name": "<tg-emoji emoji-id=\"5240228673738527951\">💎</tg-emoji> Kim Cương",    "min_orders": 0,  "min_spent": 5000000,  "discount": 0},
    {"name": "⭐️ Cao Thủ",      "min_orders": 0,  "min_spent": 10000000, "discount": 0},
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
    """Tính rank VIP dựa trên tổng đơn hoàn thành và tổng chi tiêu."""
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
    """Trả về (giá_sau_giảm, phần_trăm_giảm, tên_rank)."""
    vip = get_user_vip_rank(user_id)
    return original_price, 0, vip["rank"]["name"]


# ==============================================================================
#  /UPTIME — Bot uptime + system stats
# ==============================================================================

async def uptime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hiển thị thời gian bot đã chạy và thông tin hệ thống."""
    now = datetime.now()
    delta = now - BOT_START_TIME
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_str = ""
    if days > 0:
        uptime_str += f"{days} ngày "
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
            f"\n<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>HỆ THỐNG</b>\n"
            f"├ CPU: <b>{cpu_percent}%</b>\n"
            f"├ RAM: <b>{mem.percent}%</b> ({mem.used // (1024**2):,}/{mem.total // (1024**2):,} MB)\n"
            f"├ Disk: <b>{disk.percent}%</b> ({disk.used // (1024**3):,}/{disk.total // (1024**3):,} GB)\n"
            f"└ Bot RAM: <b>{proc_mem:.1f} MB</b>\n"
        )
    except ImportError:
        sys_info = "\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <i>Cài psutil để xem thông tin hệ thống: pip install psutil</i>\n"
    except Exception as e:
        logger.exception(f"Loi doc system info: {e}", exc_info=e)
        sys_info = f"\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <i>Lỗi đọc system info: {e}</i>\n"
    
    # Bot stats
    total_users = len(user_data_db)
    total_orders = len(order_history)
    total_products = len(products)
    
    msg = (
        f"<tg-emoji emoji-id=\"5303145396254563405\">🤖</tg-emoji> <b>BOT STATUS</b>\n"
        f"{'━' * 28}\n\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">⏱️</tg-emoji> Uptime: <b>{uptime_str}</b>\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">🕐</tg-emoji> Khởi chạy: {BOT_START_TIME.strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"{sys_info}\n"
        f"<tg-emoji emoji-id=\"6059654836918423763\">📈</tg-emoji> <b>THỐNG KÊ</b>\n"
        f"├ Users: <b>{total_users:,}</b>\n"
        f"├ Đơn hàng: <b>{total_orders:,}</b>\n"
        f"├ Sản phẩm: <b>{total_products}</b>\n"
        f"└ Pending: <b>{len(pending_orders)}</b>\n"
    )
    
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# ==============================================================================
#  PAYMENT REMINDER JOB — Nhắc thanh toán đơn pending > 15 phút  
# ==============================================================================

_payment_reminded = set()  # Track đã nhắc để không spam

async def payment_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cron job: Nhắc user thanh toán nếu đơn pending > 15 phút."""
    if not pending_orders:
        return
    
    current_time = time.time()
    REMIND_AFTER_SECONDS = 15 * 60  # 15 phút
    MAX_PENDING_SECONDS = 60 * 60   # 1 giờ — auto hủy
    
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
        
        # Quá 1 giờ → tự hủy
        if elapsed > MAX_PENDING_SECONDS:
            orders_to_remove.append(order_code)
            _payment_reminded.discard(reminder_key)
            try:
                product_name = order_details.get('product_name') or order_details.get('product', 'Sản phẩm')
                await context.bot.send_message(
                    user_id,
                    f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>ĐƠN HÀNG ĐÃ HẾT HẠN</b>\n\n"
                    f"<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> Mã: <code>{html.escape(str(order_code))}</code>\n"
                    f"<tg-emoji emoji-id=\"6260059243605398502\">📌</tg-emoji> SP: {html.escape(str(product_name))}\n\n"
                    "Đơn hàng đã bị hủy do quá thời gian thanh toán (60 phút).\n"
                    "Vui lòng đặt lại nếu cần.",
                    parse_mode=ParseMode.HTML
                )
            except TelegramError:
                pass  # User có thể đã block bot
            except Exception as e:
                logger.exception(f"Payment reminder send_message cancelled order failed for user {user_id}: {e}", exc_info=e)
            continue
        
        # Quá 15 phút + chưa nhắc → gửi nhắc nhở
        if elapsed > REMIND_AFTER_SECONDS and reminder_key not in _payment_reminded:
            _payment_reminded.add(reminder_key)
            try:
                product_name = order_details.get('product_name') or order_details.get('product', 'Sản phẩm')
                amount = order_details.get('amount', 0)
                minutes_left = max(1, int((MAX_PENDING_SECONDS - elapsed) / 60))
                await context.bot.send_message(
                    user_id,
                    f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>NHẮC NHỞ THANH TOÁN</b>\n\n"
                    f"<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> Mã đơn: <code>{html.escape(str(order_code))}</code>\n"
                    f"<tg-emoji emoji-id=\"6260059243605398502\">📌</tg-emoji> Sản phẩm: {html.escape(str(product_name))}\n"
                    f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số tiền: <b>{amount:,} VNĐ</b>\n\n"
                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Bạn chưa thanh toán đơn hàng này.\n"
                    f"Đơn sẽ tự hủy sau <b>{minutes_left} phút</b> nếu không nhận được thanh toán.\n\n"
                    "<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Nếu đã chuyển khoản, vui lòng đợi 1-2 phút để hệ thống xác nhận.",
                    parse_mode=ParseMode.HTML
                )
            except TelegramError:
                pass
            except Exception as e:
                logger.exception(f"Payment reminder send_message remind order failed for user {user_id}: {e}", exc_info=e)
    
    # Xóa các đơn hết hạn
    for code in orders_to_remove:
        pending_orders.pop(code, None)
    
    if orders_to_remove:
        create_background_task(save_data())
        logger.info(f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Payment reminder: Đã hủy {len(orders_to_remove)} đơn hết hạn.")

# ==============================================================================
#  /RANK — Xem VIP rank cá nhân
# ==============================================================================

async def rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hiển thị VIP rank của user."""
    from app.services.games_withdrawals_db import check_if_banned
    if await check_if_banned(update): return
    
    user_id = update.effective_user.id
    vip = get_user_vip_rank(user_id)
    
    rank = vip["rank"]
    base_rank = vip.get("base_rank") or rank
    next_rank = vip["next_rank"]
    maintenance_status = vip.get("maintenance_status") or {}
    
    msg = (
        f"⭐️ <b>HẠNG THÀNH VIÊN CỦA BẠN</b>\n"
        f"{'━' * 28}\n\n"
        f"⭐️ Rank: <b>{rank['name']}</b>\n"
        f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> Tổng đơn: <b>{vip['total_orders']}</b>\n"
        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Tổng chi: <b>{vip['total_spent']:,} VNĐ</b>\n"
        f"<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> Ưu đãi: <b>Không còn giảm giá theo rank</b>\n"
    )

    if vip.get("demoted_by_maintenance"):
        msg += (
            f"\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> "
            f"Tháng {maintenance_status.get('period_label', 'trước')} bạn chỉ chi "
            f"<b>{maintenance_status.get('monthly_spend', 0):,} VNĐ</b>, dưới mức duy trì "
            f"<b>{VIP_MONTHLY_MAINTENANCE_MIN_SPEND:,} VNĐ</b> nên đang bị tụt 1 bậc.\n"
            f"<tg-emoji emoji-id=\"5972022360025336988\">⬆️</tg-emoji> "
            f"Cần chi tối thiểu <b>{maintenance_status.get('remaining_to_maintain', 0):,} VNĐ</b> "
            f"trong tháng này để lấy lại <b>{base_rank['name']}</b> vào tháng sau.\n"
        )
    if next_rank:
        if vip.get("demoted_by_maintenance"):
            msg += (
                f"\n<tg-emoji emoji-id=\"5972022360025336988\">⬆️</tg-emoji> <b>Rank cần lấy lại: {next_rank['name']}</b>\n"
                f"└ Điều kiện: tháng này chi tối thiểu <b>{VIP_MONTHLY_MAINTENANCE_MIN_SPEND:,} VNĐ</b>\n"
            )
        else:
            orders_need = max(0, next_rank["min_orders"] - vip["total_orders"])
            spent_need = max(0, next_rank["min_spent"] - vip["total_spent"])
            msg += (
                f"\n<tg-emoji emoji-id=\"5972022360025336988\">⬆️</tg-emoji> <b>Rank tiếp theo: {next_rank['name']}</b>\n"
                f"├ Cần thêm: <b>{orders_need}</b> đơn hàng\n"
                f"└ Cần chi thêm: <b>{spent_need:,} VNĐ</b>\n"
            )
    else:
        msg += "\n<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> <b>Bạn đã đạt hạng cao nhất!</b> <tg-emoji emoji-id=\"6124902618574625426\">👑</tg-emoji>\n"
    
    # Bảng xếp hạng
    msg += (
        f"\n{'━' * 28}\n"
        "<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> <b>CÁC CẤP BẬC:</b>\n"
    )
    for r in VIP_RANKS:
        marker = " ← Bạn" if r["name"] == rank["name"] else ""
        msg += f"  {r['name']} — {r['min_orders']}+ đơn{marker}\n"
    msg += f"\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Quy tắc duy trì: nếu tháng trước chi dưới <b>{VIP_MONTHLY_MAINTENANCE_MIN_SPEND:,} VNĐ</b> thì sẽ tụt 1 bậc trong tháng này."
    
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# ==============================================================================
#  HÀM MAIN (KHỞI CHẠY BOT)
# ==============================================================================

