async def _apply_referral_if_needed(context: ContextTypes.DEFAULT_TYPE, user, referrer_id: int | None) -> bool:
    """Apply referral once for new referral profile only."""
    if not referrer_id or referrer_id == user.id:
        return False
    user_id_str = str(user.id)
    if user_id_str in referral_data:
        return False
    referral_data[user_id_str] = {'referrer_id': referrer_id, 'referred_users': [], 'total_commission': 0, 'commission_history': []}
    referrer_id_str = str(referrer_id)
    referral_data.setdefault(referrer_id_str, {'referred_users': [], 'total_commission': 0, 'commission_history': []})
    if user.id not in referral_data[referrer_id_str]['referred_users']:
        referral_data[referrer_id_str]['referred_users'].append(user.id)
    await save_data(tables=[REFERRAL_DATA_FILE])
    try:
        message = lt(referrer_id, "{success} <b>GIỚI THIỆU THÀNH CÔNG!</b>\n\n👤 <b>Người mới:</b> {user}\n{id_icon} <b>ID:</b> <code>{id}</code>\n\n{tag} Bạn sẽ nhận {percent}% hoa hồng khi người này mua hàng!", "{success} <b>REFERRAL SUCCESSFUL!</b>\n\n👤 <b>New user:</b> {user}\n{id_icon} <b>ID:</b> <code>{id}</code>\n\n{tag} You will earn {percent}% commission when this user purchases!", "{success} <b>推荐成功！</b>\n\n👤 <b>新用户：</b> {user}\n{id_icon} <b>ID：</b> <code>{id}</code>\n\n{tag} 此用户购买时，您将获得 {percent}% 佣金！", success=E_SUCCESS, user=format_user_name_html(user=user), id_icon=E_ID, id=user.id, tag=E_TAG, percent=REFERRAL_COMMISSION_PERCENT)
        await context.bot.send_message(referrer_id, message, parse_mode=ParseMode.HTML)
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Cannot notify referrer {referrer_id}: {e}")
    return True


def _build_registration_challenge() -> dict:
    if random.choice((True, False)):
        left, right = random.randint(1, 8), random.randint(1, 8)
        return {"question": f"{left} + {right}", "answer": left + right}
    left = random.randint(3, 12)
    right = random.randint(1, left - 1)
    return {"question": f"{left} - {right}", "answer": left - right}


async def _send_registration_challenge(update, context, referrer_id: int | None = None) -> None:
    challenge = _build_registration_challenge()
    if context.user_data is not None:
        context.user_data["registration_challenge"] = challenge
        if referrer_id:
            context.user_data["pending_referrer_id"] = referrer_id

    # Profile chưa tồn tại ở bước này nên phải lấy ngôn ngữ từ client Telegram.
    lang = resolve_lang(update.effective_user)
    await update.message.reply_html(
        f"{E_TIP} <b>{t('verify_title', lang=lang)}</b>\n\n"
        f"{t('verify_prompt', lang=lang)}\n\n"
        f"<b>{challenge['question']} = ?</b>\n\n"
        f"{t('verify_example', lang=lang)}"
    )


def _get_pending_registration_referrer(context, user) -> int | None:
    if context.user_data is None:
        return None
    pending_referrer = context.user_data.pop("pending_referrer_id", None)
    try:
        parsed_pending = int(pending_referrer) if pending_referrer is not None else None
        if parsed_pending and parsed_pending != user.id:
            return parsed_pending
    except (ValueError, TypeError, KeyError, IndexError):
        logger.debug("Invalid pending referrer ignored")
    return None


async def _register_user_profile(context, user, referrer_id: int | None = None) -> bool:
    user_id_str = str(user.id)
    current_profile = user_data_db.get(user_id_str)
    now_iso = datetime.now().isoformat()

    if not current_profile:
        user_data_db[user_id_str] = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "is_premium": bool(getattr(user, "is_premium", False)),
            "lang": resolve_lang(user),
            "first_seen": now_iso,
            "balance": 0,
            "total_spent": 0,
            "coupon_savings": 0,
            "badges": [],
            "is_registered": True,
            "registered_at": now_iso,
        }
    else:
        current_profile["first_name"] = user.first_name
        current_profile["last_name"] = user.last_name
        current_profile["username"] = user.username
        current_profile["is_premium"] = bool(getattr(user, "is_premium", False))
        current_profile.setdefault("first_seen", now_iso)
        current_profile.setdefault("balance", 0)
        current_profile.setdefault("total_spent", 0)
        current_profile.setdefault("coupon_savings", 0)
        current_profile.setdefault("badges", [])
        current_profile["is_registered"] = True
        current_profile["registered_at"] = now_iso

    referral_applied = await _apply_referral_if_needed(context, user, referrer_id)

    if user_id_str not in referral_data:
        referral_data[user_id_str] = {
            'referred_users': [],
            'total_commission': 0,
            'commission_history': []
        }

    await save_data(force=True, tables=[USERS_FILE, REFERRAL_DATA_FILE])
    return referral_applied


async def handle_registration_challenge_answer(update, context, user_input: str) -> bool:
    if not REGISTRATION_CHALLENGE_ENABLED:
        return False

    user = update.effective_user
    if not user or user.id == ADMIN_USER_ID or is_user_registered(user.id):
        return False

    challenge = context.user_data.get("registration_challenge") if context.user_data is not None else None
    if not challenge:
        await _send_registration_challenge(update, context)
        return True

    lang = resolve_lang(user)

    try:
        answer = int(str(user_input or "").strip())
    except ValueError:
        await update.message.reply_html(
            f"{E_TIP} {t('verify_number_only', lang=lang)}\n\n"
            f"<b>{challenge.get('question')} = ?</b>"
        )
        return True

    if answer != int(challenge.get("answer", -1)):
        await update.message.reply_html(
            f"{E_ERROR} {t('verify_wrong', lang=lang)}\n\n"
            f"<b>{challenge.get('question')} = ?</b>"
        )
        return True

    referrer_id = _get_pending_registration_referrer(context, user)
    referral_applied = await _register_user_profile(context, user, referrer_id)
    if context.user_data is not None:
        context.user_data.pop("registration_challenge", None)

    referral_note = f"\n{E_SUCCESS} {t('verify_referral_saved', user_id=user.id)}" if referral_applied else ""
    await update.message.reply_html(
        f"{E_SUCCESS} <b>{t('verify_success', user_id=user.id)}</b>{referral_note}\n\n"
        f"{t('opening_main_menu', user_id=user.id)}"
    )
    await send_start_welcome_with_video(update, context, user)
    return True


async def xacminh_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin: bật/tắt xác minh phép tính cho user mới trong runtime."""
    global REGISTRATION_CHALLENGE_ENABLED

    if update.effective_user.id != ADMIN_USER_ID:
        return

    arg = (context.args[0].strip().lower() if context.args else "")
    if arg in {"on", "bat", "bật", "1", "true", "yes"}:
        REGISTRATION_CHALLENGE_ENABLED = True
        status = "BAT"
    elif arg in {"off", "tat", "tắt", "0", "false", "no"}:
        REGISTRATION_CHALLENGE_ENABLED = False
        status = "TAT"
    else:
        status = "BAT" if REGISTRATION_CHALLENGE_ENABLED else "TAT"
        await update.message.reply_html(
            f"{E_TAG} <b>XÁC MINH USER MỚI:</b> <code>{status}</code>\n\n"
            "Dùng lệnh:\n"
            "• <code>/xacminh on</code> để bật xác minh\n"
            "• <code>/xacminh off</code> để tắt xác minh"
        )
        return

    await update.message.reply_html(
        f"{E_SUCCESS} <b>ĐÃ {status} XÁC MINH USER MỚI.</b>\n\n"
        f"Trạng thái hiện tại: <code>{status}</code>"
    )


async def registered_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await check_if_banned(update): return
    if MAINTENANCE_MODE and update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text(
            t("maintenance", lang=resolve_lang(update.effective_user)),
            parse_mode=ParseMode.HTML
        )
        return

    await clear_user_state(context)
    user = update.effective_user
    if not user:
        return

    if user.id == ADMIN_USER_ID or is_user_registered(user.id):
        await update.message.reply_html(
            f"{E_SUCCESS} <b>{t('already_verified', user_id=user.id)}</b>\n\n"
            f"{t('use_start', user_id=user.id)}"
        )
        return

    if not REGISTRATION_CHALLENGE_ENABLED:
        referrer_id = _get_pending_registration_referrer(context, user)
        await _register_user_profile(context, user, referrer_id)
        await update.message.reply_html(
            f"{E_SUCCESS} <b>"
            + lt(
                user.id,
                "ĐÃ XÁC MINH TỰ ĐỘNG.",
                "VERIFIED AUTOMATICALLY.",
                "已自动验证。",
            )
            + "</b>\n\n"
            + t("use_start", user_id=user.id)
        )
        return

    await _send_registration_challenge(update, context)


def _should_handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Require an explicit bot mention for /start and /menu inside groups."""
    chat_type = str(getattr(getattr(update, "effective_chat", None), "type", "") or "").lower()
    if chat_type == "private":
        return True
    if chat_type not in {"group", "supergroup"}:
        return True

    message = getattr(update, "effective_message", None) or getattr(update, "message", None)
    text = str(getattr(message, "text", "") or "").strip()
    command_token = text.split(maxsplit=1)[0] if text else ""
    if not command_token.startswith("/") or "@" not in command_token:
        return False

    command_name, mentioned_username = command_token[1:].split("@", 1)
    if command_name.casefold() not in {"start", "menu"}:
        return False

    valid_usernames = {str(BOT_USERNAME or "").strip().lstrip("@").casefold()}
    try:
        runtime_username = str(getattr(getattr(context, "bot", None), "username", "") or "")
    except RuntimeError:
        runtime_username = ""
    valid_usernames.add(runtime_username.strip().lstrip("@").casefold())
    valid_usernames.discard("")
    return mentioned_username.casefold() in valid_usernames


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _should_handle_start_command(update, context):
        return
    if await check_if_banned(update): return

    # Kiểm tra chế độ bảo trì
    if MAINTENANCE_MODE and update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text(t("maintenance", lang=resolve_lang(update.effective_user)), parse_mode=ParseMode.HTML)
        return

    await clear_user_state(context)
    
    # FIX BUG #25: Clear AI chat history khi /start để fresh conversation
    user_id = update.effective_user.id
    gemini_assistant.clear_chat(user_id)
    user = update.effective_user
    user_id_str = str(user.id)

    # Optional gate for first-time users. When disabled, accept every Telegram user
    # into data immediately while preserving referral tracking.
    if user.id != ADMIN_USER_ID and not is_user_registered(user.id):
        pending_referrer_id = None
        if context.args and len(context.args) > 0:
            arg = context.args[0]
            if arg.startswith('ref_'):
                try:
                    referrer_id = int(arg.replace('ref_', ''))
                    if referrer_id != user.id:
                        pending_referrer_id = referrer_id
                        if context.user_data is not None:
                            context.user_data["pending_referrer_id"] = referrer_id
                except ValueError:
                    pass

        if REGISTRATION_CHALLENGE_ENABLED:
            await _send_registration_challenge(update, context, pending_referrer_id)
            return

        await _register_user_profile(context, user, pending_referrer_id)
    
    # === REFERRAL SYSTEM ===
    # Check if user came through referral link
    if context.args and len(context.args) > 0:
        arg = context.args[0]
        if arg.startswith('ref_'):
            try:
                referrer_id = int(arg.replace('ref_', ''))
                
                # Don't allow self-referral
                if referrer_id != user.id:
                    # Check if this is a new user (not already referred)
                    if user_id_str not in referral_data:
                        # Initialize referral data for new user
                        referral_data[user_id_str] = {
                            'referrer_id': referrer_id,
                            'referred_users': [],
                            'total_commission': 0,
                            'commission_history': []
                        }
                        
                        # Update referrer's referral list
                        referrer_id_str = str(referrer_id)
                        if referrer_id_str not in referral_data:
                            referral_data[referrer_id_str] = {
                                'referred_users': [],
                                'total_commission': 0,
                                'commission_history': []
                            }
                        
                        if user.id not in referral_data[referrer_id_str]['referred_users']:
                            referral_data[referrer_id_str]['referred_users'].append(user.id)
                        
                        await save_data()
                        
                        # Notify referrer
                        try:
                            await context.bot.send_message(
                                referrer_id,
                                f"{E_SUCCESS} <b>BẠN VỪA GIỚI THIỆU THÀNH CÔNG!</b>\n\n"
                                f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Người mới:</b> {format_user_name_html(user=user)}\n"
                                f"{E_ID} <b>ID:</b> <code>{user.id}</code>\n\n"
                                f"{E_TAG} Bạn sẽ nhận {REFERRAL_COMMISSION_PERCENT}% hoa hồng khi người này mua hàng!",
                                parse_mode=ParseMode.HTML
                            )
                        except (TelegramError, ValueError, KeyError, AttributeError) as e:
                            logger.error(f"Cannot notify referrer {referrer_id}: {e}")
                            
            except ValueError:
                pass  # Invalid referral code, ignore
    
    profile_changed = False
    referral_changed = False
    now_iso = datetime.now().isoformat()

    # Initialize user data if new
    if user_id_str not in user_data_db:
        user_data_db[user_id_str] = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "is_premium": bool(getattr(user, "is_premium", False)),
            "lang": resolve_lang(user),
            "first_seen": now_iso,
            "balance": 0,
            "total_spent": 0,
            "coupon_savings": 0,
            "badges": [],
            "is_registered": True,
            "registered_at": now_iso,
        }
        profile_changed = True
    else:
        profile = user_data_db[user_id_str]
        if profile.get("first_name") != user.first_name:
            profile["first_name"] = user.first_name
            profile_changed = True
        if profile.get("last_name") != user.last_name:
            profile["last_name"] = user.last_name
            profile_changed = True
        if profile.get("username") != user.username:
            profile["username"] = user.username
            profile_changed = True
        if sync_user_premium_flag(user, profile):
            profile_changed = True
        if "first_seen" not in profile:
            profile["first_seen"] = now_iso
            profile_changed = True
        if "balance" not in profile:
            profile["balance"] = 0
            profile_changed = True
        if "total_spent" not in profile:
            profile["total_spent"] = 0
            profile_changed = True
        if "coupon_savings" not in profile:
            profile["coupon_savings"] = 0
            profile_changed = True
        if "badges" not in profile:
            profile["badges"] = []
            profile_changed = True
        if "is_registered" not in profile:
            profile["is_registered"] = True
            profile_changed = True
        if "registered_at" not in profile:
            profile["registered_at"] = profile.get("first_seen", now_iso)
            profile_changed = True

    # Initialize referral data if not exists (for existing users)
    if user_id_str not in referral_data:
        referral_data[user_id_str] = {
            'referred_users': [],
            'total_commission': 0,
            'commission_history': []
        }
        referral_changed = True

    if profile_changed or referral_changed:
        save_tables = []
        if profile_changed:
            save_tables.append(USERS_FILE)
        if referral_changed:
            save_tables.append(REFERRAL_DATA_FILE)
        await save_data(tables=save_tables)
    
    await send_start_welcome_with_video(update, context, user)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await clear_user_state(context)
    user_id = update.effective_user.id if update.effective_user else None
    await update.message.reply_html(t("cancelled", user_id=user_id), reply_markup=create_main_menu(user_id=user_id))

async def guimail_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Cho phép khách gửi email bằng lệnh thay vì reply message.
    Cú pháp: 
    - /guimail abc@gmail.com (Tự động tìm đơn chờ email)
    - /guimail abc@gmail.com ICLD123456 (Chỉ định mã đơn)
    """
    user = update.effective_user
    if not user:
        return
    
    user_id = user.id
    if not context.args:
        await update.message.reply_html(lt(user_id, "📧 <b>HƯỚNG DẪN /guimail</b>\n\n<b>Tự tìm đơn:</b>\n<code>/guimail abc@gmail.com</code>\n\n<b>Chỉ định mã đơn:</b>\n<code>/guimail abc@gmail.com ICLD123456</code>\n\n💡 Dùng để gửi email nhận hàng cho đơn manual.", "📧 <b>/guimail GUIDE</b>\n\n<b>Find the order automatically:</b>\n<code>/guimail abc@gmail.com</code>\n\n<b>Specify an order code:</b>\n<code>/guimail abc@gmail.com ICLD123456</code>\n\n💡 Use this to submit the delivery email for a manual order.", "📧 <b>/guimail 使用指南</b>\n\n<b>自动查找订单：</b>\n<code>/guimail abc@gmail.com</code>\n\n<b>指定订单号：</b>\n<code>/guimail abc@gmail.com ICLD123456</code>\n\n💡 用于提交手动订单的收货邮箱。"))
        return
    
    # Extract email
    email_input = context.args[0].strip().lower()
    
    if not EMAIL_REGEX.match(email_input):
        await update.message.reply_html(lt(user_id, "❌ <b>EMAIL KHÔNG HỢP LỆ!</b>\n\nEmail đã nhập: <code>{email}</code>\n\nVui lòng nhập đúng định dạng.\n<i>Ví dụ: example@gmail.com</i>", "❌ <b>INVALID EMAIL!</b>\n\nEntered email: <code>{email}</code>\n\nEnter a valid email address.\n<i>Example: example@gmail.com</i>", "❌ <b>邮箱无效！</b>\n\n输入的邮箱：<code>{email}</code>\n\n请输入有效邮箱。\n<i>示例：example@gmail.com</i>", email=email_input))
        return
    order_code_specified = None
    if len(context.args) >= 2:
        order_code_specified = context.args[1].upper()
        if not MANUAL_EMAIL_ORDER_CODE_REGEX.match(order_code_specified):
            await update.message.reply_html(lt(user_id, "❌ <b>MÃ ĐƠN KHÔNG HỢP LỆ!</b>\n\nMã đã nhập: <code>{code}</code>\n\nĐịnh dạng ví dụ: <code>ICLD123456</code>", "❌ <b>INVALID ORDER CODE!</b>\n\nEntered code: <code>{code}</code>\n\nExample format: <code>ICLD123456</code>", "❌ <b>订单号无效！</b>\n\n输入的编号：<code>{code}</code>\n\n格式示例：<code>ICLD123456</code>", code=order_code_specified))
            return
    
    # Find order in pending_manual_orders
    found_order = None
    found_order_code = None
    
    for order_code, info in pending_manual_orders.items():
        # Check user match
        if str(info.get('user_id')) != str(user.id):
            continue
        
        # Check status
        if info.get('status') != 'awaiting_email':
            continue
        
        # If order code specified, match exactly
        if order_code_specified:
            if order_code == order_code_specified:
                found_order = info
                found_order_code = order_code
                break
        else:
            # Auto-detect: first awaiting_email order
            found_order = info
            found_order_code = order_code
            break
    
    if not found_order:
        if order_code_specified:
            error_msg = lt(user_id, "❌ <b>KHÔNG TÌM THẤY ĐƠN HÀNG</b>\n\nKhông tìm thấy đơn <code>{code}</code> đang chờ email của bạn.", "❌ <b>ORDER NOT FOUND</b>\n\nNo order <code>{code}</code> is waiting for your email.", "❌ <b>未找到订单</b>\n\n没有编号为 <code>{code}</code> 的订单正在等待您的邮箱。", code=order_code_specified)
        else:
            error_msg = lt(user_id, "❌ <b>KHÔNG TÌM THẤY ĐƠN HÀNG</b>\n\nBạn không có đơn nào đang chờ nhập email.", "❌ <b>ORDER NOT FOUND</b>\n\nYou have no order waiting for an email.", "❌ <b>未找到订单</b>\n\n您没有正在等待邮箱的订单。")
        error_msg += lt(user_id, "\n\nVui lòng liên hệ Admin nếu cần hỗ trợ.", "\n\nContact Admin if you need help.", "\n\n如需帮助，请联系管理员。")
        await update.message.reply_html(error_msg)
        return
    
    # Process order (same logic as priority_email_handler)
    try:
        # 1. Update Order
        found_order['email'] = email_input
        found_order['status'] = 'pending_admin'
        found_order['timestamp_email'] = time.time()
        
        # Save only the changed table to avoid full DB write in hot path.
        await save_data(force=True, tables=[PENDING_MANUAL_ORDERS_FILE])
        
        await update.message.reply_html(lt(user_id, "{success} <b>ĐÃ NHẬN EMAIL!</b>\n\n{globe} <b>Email:</b> <code>{email}</code>\n{tag} <b>Sản phẩm:</b> {product}\n🔸 <b>Mã đơn:</b> <code>{code}</code>\n\n{loading} <b>Admin đang xử lý...</b>\n⏱️ Thời gian: 1-30 phút\n\nBạn sẽ nhận thông báo khi hoàn thành.", "{success} <b>EMAIL RECEIVED!</b>\n\n{globe} <b>Email:</b> <code>{email}</code>\n{tag} <b>Product:</b> {product}\n🔸 <b>Order code:</b> <code>{code}</code>\n\n{loading} <b>Admin is processing it...</b>\n⏱️ Estimated time: 1-30 minutes\n\nYou will be notified when complete.", "{success} <b>邮箱已收到！</b>\n\n{globe} <b>邮箱：</b> <code>{email}</code>\n{tag} <b>商品：</b> {product}\n🔸 <b>订单号：</b> <code>{code}</code>\n\n{loading} <b>管理员正在处理...</b>\n⏱️ 预计时间：1-30 分钟\n\n完成后您将收到通知。", success=E_SUCCESS, globe=E_GLOBE, email=email_input, tag=E_TAG, product=found_order.get('product_name', 'N/A'), code=found_order_code, loading=E_LOADING))
        
        # 3. Notify Admin
        await notify_admin_manual_order(
            context, 
            found_order_code, 
            found_order['user_id'],
            found_order.get('full_name', 'Unknown'),
            email_input,
            found_order.get('product_name', 'Product'),
            int(found_order.get('quantity', 1)),
            int(found_order.get('amount', 0))
        )
        
        logger.info(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> /guimail: User {user.id} submitted email {email_input} for order {found_order_code}")
        
    except (ValueError, TypeError, KeyError, IndexError) as e:
        logger.error(f"❌ Error in guimail_command: {e}", exc_info=True)
        await update.message.reply_html(lt(user_id, "⚠️ <b>CÓ LỖI XẢY RA!</b>\n\nKhông thể lưu email. Vui lòng thử lại hoặc liên hệ Admin.", "⚠️ <b>AN ERROR OCCURRED!</b>\n\nCould not save the email. Try again or contact Admin.", "⚠️ <b>发生错误！</b>\n\n无法保存邮箱，请重试或联系管理员。"))

async def chat_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FIX BUG #21: AI luôn sẵn sàng với smart fallback
    Tự động trả lời mọi tin nhắn không phải command
    """
    if not update.message or not update.message.text: return
    user_msg = update.message.text
    user_id = update.effective_user.id
    user_state = context.user_data.get('state')

    # === NEW FEATURE STATE HANDLERS ===
    if user_state == 'awaiting_warranty_description':
        order_code = context.user_data.get('warranty_claim_order')
        found_order = order_index.get(order_code) if order_code else None
        if found_order and await _auto_reject_expired_support_message(update.message, context, found_order, order_code):
            return
        context.user_data['warranty_description'] = user_msg.strip()
        context.user_data['state'] = 'awaiting_warranty_photo'
        await update.message.reply_text(lt(user_id, "📸 Vui lòng gửi <b>ảnh chụp màn hình</b> vấn đề:", "📸 Send a <b>screenshot</b> of the issue:", "📸 请发送问题的<b>屏幕截图</b>："), parse_mode=ParseMode.HTML)
        return

    elif user_state == 'in_live_chat':
        user_id_str = str(user_id)
        if user_id_str not in live_chats:
            live_chats[user_id_str] = {'messages': [], 'status': 'active', 'last_activity': time.time(), 'unread_by_admin': 0}
        
        live_chats[user_id_str]['messages'].append({'from': 'user', 'text': user_msg, 'timestamp': time.time()})
        live_chats[user_id_str]['last_activity'] = time.time()
        live_chats[user_id_str]['unread_by_admin'] += 1
        await save_data()
        
        # Notify admin
        try:
             await context.bot.send_message(
                 ADMIN_USER_ID,
                 f"<tg-emoji emoji-id=\"6129860303619363484\">💬</tg-emoji> <b>TIN NHẮN MỚI</b>\nTừ: {format_user_mention_html(update.effective_user)}\nID: <code>{user_id}</code>\n\n<i>{html.escape(user_msg)}</i>",
                 parse_mode=ParseMode.HTML,
                 reply_markup=InlineKeyboardMarkup([
                     [InlineKeyboardButton("<tg-emoji emoji-id=\"6129860303619363484\">💬</tg-emoji> Mở chat", callback_data=f"admin_open_chat:{user_id}")],
                     [InlineKeyboardButton("❌ Đóng chat", callback_data=f"admin_close_chat:{user_id}")]
                 ])
             )
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.warning(f"Cannot notify admin about new live chat message: {e}")
        
        await update.message.reply_text(lt(user_id, "✅ Đã gửi! Admin sẽ trả lời sớm.\n/closechat để đóng chat.", "✅ Sent! Admin will reply soon.\nUse /closechat to close the chat.", "✅ 已发送！管理员会尽快回复。\n使用 /closechat 关闭聊天。"), reply_markup=create_main_menu(user_id=user_id))
        return

    # Check admin replying (Special Case)
    if user_id == ADMIN_USER_ID and context.user_data.get('admin_chatting_with'):
         target_uid = context.user_data['admin_chatting_with']
         target_uid_str = str(target_uid)
         if target_uid_str in live_chats:
             live_chats[target_uid_str]['messages'].append({'from': 'admin', 'text': user_msg, 'timestamp': time.time()})
             live_chats[target_uid_str]['last_activity'] = time.time()
             await save_data()
             try:
                 await context.bot.send_message(target_uid, f"<tg-emoji emoji-id=\"5350778980158956492\">👨</tg-emoji>‍<tg-emoji emoji-id=\"5854908544712707500\">💼</tg-emoji> <b>Admin:</b>\n{user_msg}", parse_mode=ParseMode.HTML)
                 await update.message.reply_text("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã gửi.")
             except (TelegramError, ValueError, KeyError, AttributeError) as e:
                 await update.message.reply_text("❌ Lỗi gửi tin, vui lòng kiểm tra kết nối.")
         return

    # === EXISTING LOGIC ===
    # Check nếu AI auto-reply bị tắt
    if not AI_AUTO_REPLY:
        return
    
    # Gửi action "đang nhập..." (best effort)
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    except (TelegramError, ValueError, KeyError, AttributeError):
        logger.debug("Suppressed error at L8962")

    try:
        # Lấy context của user
        user_info = db_get_user(user_id)
        user_orders = db_get_user_orders(user_id, limit=10)
        
        user_context = {
            'orders_count': len(user_orders),
            'balance': user_info.get('balance', 0) if user_info else 0,
            'last_order': user_orders[0] if user_orders else None
        }
        
        # FIX BUG #24: Gọi AI với context và user_id (để có chat history)
        reply_content = await ask_ai(user_msg, user_context, user_id=user_id)
        
        # Trả lời với HTML format để đẹp hơn.
        # Nếu message gốc đã bị xoá/sweep ở group thì fallback gửi thẳng vào chat.
        try:
            await update.message.reply_html(reply_content)
        except BadRequest as html_err:
            html_err_text = str(html_err or "")
            html_err_lower = html_err_text.lower()
            reply_sent = False

            if "message to be replied not found" in html_err_lower:
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=reply_content,
                        parse_mode=ParseMode.HTML
                    )
                    reply_sent = True
                except BadRequest as send_html_err:
                    if "can't parse entities" not in str(send_html_err or "").lower():
                        raise
            elif "can't parse entities" not in html_err_lower:
                raise

            if not reply_sent:
                try:
                    await update.message.reply_text(reply_content)
                except BadRequest as text_err:
                    if "message to be replied not found" in str(text_err or "").lower():
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=reply_content
                        )
                    else:
                        raise
            
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Lỗi khi gọi AI: {e}")
        # Fallback message thân thiện
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=t("ai_fallback", user_id=user_id)
            )
        except (TelegramError, ValueError, KeyError, AttributeError) as notify_err:
            logger.warning(f"Khong the gui fallback AI message: {notify_err}")
