def register_handlers(application) -> None:
    """Gắn toàn bộ handler vào application. Tách riêng để test được scope chat."""
    application.add_error_handler(error_handler_callback)

    # Cửa hàng, ví và mọi lệnh cá nhân chỉ chạy trong chat riêng. Trong group,
    # câu trả lời của bot lộ số dư/đơn hàng cho cả nhóm, và bất kỳ ai cũng gõ
    # được lệnh của người khác. Chỉ giveaway và guard tiếng Trung sống ở group.
    PRIVATE = filters.ChatType.PRIVATE

    def private_command(command, callback):
        return CommandHandler(command, callback, filters=PRIVATE)

    # <tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> FIX: Priority Email Handler (Group -1) - Chạy TRƯỚC mọi thứ để bắt email
    # Đảm bảo bot luôn phản hồi email dù đang ở state nào
    application.add_handler(
        MessageHandler(filters.ALL & filters.ChatType.GROUPS, chinese_language_guard_handler),
        group=-2,
    )
    application.add_handler(
        MessageHandler(filters.UpdateType.EDITED_MESSAGE & filters.ChatType.GROUPS, chinese_language_guard_handler),
        group=-2,
    )
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & PRIVATE, priority_email_handler), group=-1)

    # --- STORE CONVERSATION HANDLERS (UPDATED: Thêm states mới) ---
    add_prod_handler = ConversationHandler(
        entry_points=[private_command('newproduct', add_product_start)],
        states={
            ADD_PROD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prod_name)],
            ADD_PROD_NAME_SUGGEST: [CallbackQueryHandler(receive_prod_name_suggest, pattern='^name_suggest_')],
            ADD_PROD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prod_price)],
            ADD_PROD_DESC_CHOICE: [CallbackQueryHandler(receive_prod_desc_choice, pattern='^desc_choice_')],
            ADD_PROD_AI_DESC: [CallbackQueryHandler(receive_prod_ai_desc_action, pattern='^ai_desc_')],
            ADD_PROD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prod_desc)],
            ADD_PROD_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prod_duration)],
            ADD_PROD_GMAIL: [CallbackQueryHandler(receive_prod_gmail, pattern='^prod_gmail_')],
            ADD_PROD_WARRANTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_prod_warranty)],
            ADD_PROD_CONFIRM: [CallbackQueryHandler(receive_prod_confirm, pattern='^prod_confirm_')]
        },
        fallbacks=[private_command('cancel', cancel_conversation)],
        per_message=False,
        per_chat=True,
        per_user=True
    )
    application.add_handler(add_prod_handler)
    
    add_stock_handler = ConversationHandler(
        entry_points=[private_command('addstock', add_stock_start)],
        states={
            STOCK_SELECT: [CallbackQueryHandler(stock_select_product, pattern='^(sel_stock_|stock_page_)')],
            STOCK_INPUT: [MessageHandler((filters.Document.ALL | filters.TEXT) & ~filters.COMMAND, receive_stock_input)],
        },
        fallbacks=[private_command('cancel', cancel_conversation)],
        per_message=False,
        per_chat=True,
        per_user=True
    )
    application.add_handler(add_stock_handler)
    
    # NEW: Edit Product Handler
    edit_prod_handler = ConversationHandler(
        entry_points=[private_command('editproduct', edit_product_start)],
        states={
            EDIT_PROD_SELECT: [CallbackQueryHandler(edit_prod_select, pattern='^(edit_sel_|edit_page_)')],
            EDIT_PROD_FIELD: [CallbackQueryHandler(edit_prod_field, pattern='^edit_field_|cancel_edit'),
                              CallbackQueryHandler(receive_edit_ai_desc_action, pattern='^ai_edit_desc_')],
            EDIT_PROD_AI_DESC: [CallbackQueryHandler(receive_edit_ai_desc_action, pattern='^ai_edit_desc_')],
            EDIT_PROD_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_prod_receive_value)]
        },
        fallbacks=[private_command('cancel', cancel_conversation)],
    )
    application.add_handler(edit_prod_handler)
    
    # NEW: Stock Management Handler
    stock_mgmt_handler = ConversationHandler(
        entry_points=[
            private_command(['viewstock', 'delstock'], view_stock_start),
            CallbackQueryHandler(view_stock_start, pattern='^adm:x:viewstock$')
        ],
        states={
            STOCK_VIEW: [CallbackQueryHandler(view_stock_select, pattern='^(view_stock_|del_stock_sel_)')],
            STOCK_DELETE_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, stock_delete_handler)]
        },
        fallbacks=[private_command('cancel', cancel_conversation)],
    )
    application.add_handler(stock_mgmt_handler)
    
    # NEW: Transactions Command
    application.add_handler(private_command(["transactions", "lichsugiaodich"], transactions_command))
    
    # Create Giveaway Conversation
    create_ga_handler = ConversationHandler(
        entry_points=[private_command('create_ga', create_ga_start)],
        states={
            GA_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ga_title)],
            GA_PRIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ga_prize)],
            GA_MODE: [CallbackQueryHandler(receive_ga_mode, pattern="^ga_mode_")], # NEW
            GA_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ga_time)],
            GA_BANNER: [MessageHandler(filters.PHOTO | filters.VIDEO | filters.TEXT, receive_ga_banner)],
            GA_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ga_channel)],
        },
        fallbacks=[private_command('cancel', cancel_conversation)],
    )

    application.add_handler(create_ga_handler)
    
    # NEW: GA Comment & Edit Handlers (Before other handlers)
    # FIX: Thêm ~filters.ChatType.PRIVATE để không chặn email replies trong private chat
    application.add_handler(MessageHandler(filters.TEXT & filters.REPLY & ~filters.COMMAND & ~filters.ChatType.PRIVATE, ga_comment_handler))
    application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, ga_edit_handler))
    
    # Register commands
    application.add_handler(CommandHandler(["start", "menu"], start_command))
    application.add_handler(private_command(["registered", "REGISTERED"], registered_command))
    application.add_handler(private_command("helpapi", helpapi_command))
    application.add_handler(private_command(["napapi", "topupapi"], napapi_command))
    application.add_handler(private_command("cancel", cancel_command))
    application.add_handler(private_command("guimail", guimail_command))  # NEW: Email submission command
    application.add_handler(private_command("lichsu", lichsu_command))
    application.add_handler(private_command(["naptien", "topup", "napvi"], naptien_command))
    application.add_handler(private_command(["baoloi", "huongdanbaoloi"], huongdan_baoloi_command)) # NEW
    application.add_handler(private_command("ask", ask_command))
    application.add_handler(private_command(["dkyapi", "dkapi", "dangkyapi", "regapi"], dkyapi_command))
    
    # === NEW COMMANDS ===
    # Moved to admin_handlers
    
    # Manually added commands for walkthrough
    application.add_handler(private_command("mystats", lambda u, c: show_my_stats(u, c, is_callback=False)))
    application.add_handler(private_command("myref", lambda u, c: show_my_referral(u, c, is_callback=False)))
    application.add_handler(private_command("toprefs", lambda u, c: show_top_referrers(u, c, is_callback=False)))

    # Dice Game Command
    application.add_handler(private_command("wheel", wheel_command))
    application.add_handler(private_command("vongquay", wheel_command))
    application.add_handler(private_command("dice", dice_game_command))
    application.add_handler(private_command("choi", dice_game_command))
    application.add_handler(private_command("xucxac", dice_game_command))

    # Withdrawal Commands
    application.add_handler(private_command("ruttien", withdrawal_command))
    # pending_withdrawals moved to admin_handlers

    # NEW: Rank commands (user-facing)
    application.add_handler(private_command(["rank", "vip", "hang"], rank_command))
    
    # Admin Money Commands
    # addmoney, submoney moved to admin_handlers

    application.add_handler(CallbackQueryHandler(priority_button_handler), group=-3)
    
    # FIX 1: Dòng gây lỗi NameError đã được vô hiệu hóa.
    # application.add_handler(MessageHandler(filters.REPLY & ~filters.COMMAND, ticket_reply_handler))
    
    # Use text_message_handler as the main handler (it calls chat_with_ai internally)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & PRIVATE, text_message_handler))
    
    # Unified Photo Handler (Handles both Report Error & Warranty Claims)
    application.add_handler(MessageHandler(filters.PHOTO & PRIVATE, photo_message_handler))
    
    # === JOB SCHEDULERS ===
    if application.job_queue:

        application.job_queue.run_daily(warranty_reminder_job, time=dt_time(9, 0, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")))
        application.job_queue.run_repeating(auto_end_giveaway_job, interval=60, first=30)
        # NEW: Auto remind pending emails
        application.job_queue.run_repeating(auto_remind_email_job, interval=300, first=10)
        application.job_queue.run_repeating(auto_close_inactive_chats_job, interval=60, first=30, name="auto_close_chats")
    
    admin_handlers = {
        # "show": show_command, # REPLACED BY ADMIN
        "admin": admin_command,
        "helpadmin": admin_command,
        "backup": backup_command,
        "nhapdata": nhapdata_command,
        
        # --- KHO LINK ---
        
        # --- STORE ---
        "products": listproducts_command,
        "setlimit": setlimit_command,
        "delproduct": delproduct_command,

        # --- GIVEAWAY ---
        "list_ga": list_ga_command,
        "listga": list_ga_command,
        "endga": endga_command, # Manual End GA command
        "end_ga": endga_command,

        # --- COUPON & KHUYẾN MÃI ---
        "sale": sale_command,
        "addcoupon": addcoupon_command,
        "delcoupon": delcoupon_command, 
        "listcoupons": listcoupons_command,
        "rewardtop": rewardtop_command,
        
        # --- QUẢN LÝ USER ---
        "users": listusers_command,
        "info": userinfo_command, 
        "ban": ban_command, 
        "unban": unban_command,
        "bc": broadcast_command,
        "bcsp": bcsp_command,
        "broadcastsp": bcsp_command, 
        
        # --- ĐƠN HÀNG & DOANH THU ---
        "duyet": duyet_command,
        "pending": pending_manual_command,
        "clearpending": clearpending_command,
        "refund": refund_command, 
        "find": find_order_command, 
        "doanhthu": doanhthu_command,
        "promobudget": promobudget_command,
        "ngansachkm": promobudget_command,
        "setemail": setemail_command, # NEW
        
        # --- HỆ THỐNG & API ADMIN ---
        "baotri": baotri_command,
        "xacminh": xacminh_command,
        "verify": xacminh_command,
        "aimode": aimode_command,
        "api": listapi_command,
        "addapi": addapi_command, 
        "delapi": delapi_command, 
        "napi": napi_command,
        
        # --- BROADCAST NOTIFICATIONS ---
        "notify": notify_command,
        "resetnotify": resetnotify_command,
        "setstockchannel": setstockchannel_command,
        "stockchannel": stockchannel_command,

        # --- NEW ADMIN COMMANDS ---
        "analytics": analytics_command,
        "chats": chats_command,
        "chat": chat_command, 
        "closechat": lambda u, c: clear_user_state(c),
        "pending_withdrawals": pending_withdrawals_command,
        "addmoney": addmoney_command,
        "submoney": submoney_command,
        "sodumb": sodumb_command,
        
        "icon": icon_command,
        
        # --- TESTING ---
        "testing": testing_command,
        
        # --- FLASH SALE & COMBO ---
        "flashsale": flashsale_command,
        "combo": combo_command,
        
        # --- SYSTEM MONITORING ---
        "uptime": uptime_command,
        "status": uptime_command,
    }

    for command, func in admin_handlers.items():
        application.add_handler(private_command(command, lambda u, c, f=func: admin_command_wrapper(u, c, f)))

def main() -> None:
    if not TELEGRAM_TOKEN or (ENABLE_PAYMENT_SEPAY and not SEPAY_WEBHOOK_API_KEY):
        logger.critical("!!! CẢNH BÁO: Thiếu biến cấu hình cần thiết !!!")
        return

    if not acquire_single_instance_lock():
        logger.critical(
            "❌ Bot instance lock is active. Có thể đang có 1 process local khác chạy bot này."
        )
        logger.critical(
            "<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Hãy tắt instance cũ trước khi chạy lại để tránh conflict getUpdates."
        )
        return

    load_data()
    # FIX: Thêm post_shutdown để cleanup resources đúng cách
    # FIX: Increase connection timeout to avoid ConnectTimeout error
    request = HTTPXRequest(
        connection_pool_size=8, 
        connect_timeout=45.0, 
        read_timeout=45.0, 
        write_timeout=30.0, 
        pool_timeout=30.0
    )
    application = Application.builder().token(TELEGRAM_TOKEN).request(request).post_init(post_init).post_shutdown(pre_shutdown).build()

    # Đăng ký trình xử lý lỗi toàn cục
    # Đăng ký trình xử lý lỗi và toàn bộ handler
    register_handlers(application)

    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(
            check_payment_job,
            interval=BANK_CHECK_INTERVAL_SECONDS,
            first=10,
            job_kwargs={"max_instances": 1, "coalesce": True},
        )
        job_queue.run_daily(cleanup_expired_coupons_job, time=dt_time(hour=0, minute=5, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")), name="daily_coupon_cleanup")
        job_queue.run_repeating(cleanup_flash_sales_job, interval=60, first=30, name="flash_sale_cleanup")
        # NEW: Auto-Backup Job (Telegram 6h, Email 3d)
        # job_queue.run_repeating(auto_backup_job, interval=BACKUP_INTERVAL_TELEGRAM, first=60, name="auto_backup")
        
        # NEW: Payment Reminder Job (check mỗi 3 phút)
        job_queue.run_repeating(payment_reminder_job, interval=180, first=60, name="payment_reminder")
        
        # Batch Error Reporting Job (1h)
        job_queue.run_repeating(send_batched_error_reports, interval=3600, first=60, name="batch_error_report")
        
        # Tỉ giá hiển thị (VND/USD/CNY) cho menu và thống kê - cache 5 phút
        job_queue.run_repeating(refresh_display_rates_job, interval=300, first=1, name="display_rates")

        # Tối ưu: Background task để debounced save
        job_queue.run_repeating(save_data_debounced, interval=_cache["save_debounce"], first=5)
    else:
        logger.warning("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Job queue không khả dụng, bỏ qua đăng ký cron jobs.")

    # ============================================
    #  STARTUP BANNER (TYRANT EDITION)
    # ============================================
    startup_banner = r"""
██████╗ ██╗███╗   ██╗ ██████╗     ██████╗ ██████╗  ██████╗ 
██╔══██╗██║████╗  ██║██╔═══██╗    ██╔══██╗██╔══██╗██╔═══██╗
██║  ██║██║██╔██╗ ██║██║   ██║    ██████╔╝██████╔╝██║   ██║
██║  ██║██║██║╚██╗██║██║   ██║    ██╔═══╝ ██╔══██╗██║   ██║
██████╔╝██║██║ ╚████║╚██████╔╝    ██║     ██║  ██║╚██████╔╝
╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝ 
                                                         
               __
              / _)
     _.----._/ /   I AM THE KING!
    /         /    
 __/ (  | (  |     
/__.-'|_|--|_|     
    """
    try:
        print(startup_banner)
    except UnicodeEncodeError:
        print("[LAM SHOP] LAM SHOP BOT STARTING...")
    
    logger.info(f"<tg-emoji emoji-id=\"5303145396254563405\">🦖</tg-emoji> AI Model:      {AI_MODEL}")
    logger.info(f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> Products:      {len(products)}")
    logger.info(f"<tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> Users:         {len(user_data_db)}")
    logger.info(f"<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> Orders:        {len(order_history)}")
    logger.info(f"<tg-emoji emoji-id=\"5350481781306958339\">💾</tg-emoji> Database:      SQLite KV Store (WAL)")
    logger.info(f"<tg-emoji emoji-id=\"5436359785534466562\">🔌</tg-emoji> API Port:      {API_SERVER_PORT}")
    logger.info(f"<tg-emoji emoji-id=\"5213349767672769194\">⏱</tg-emoji> Bank Cron:     {BANK_CHECK_INTERVAL_SECONDS}s")
    logger.info(f"<tg-emoji emoji-id=\"5231489647946768652\">🌍</tg-emoji> USDT (RPay):   {'ON' if is_usdt_payment_enabled() else 'OFF'} | Binance Pay: {'ON' if is_binance_pay_enabled() else 'OFF'}")
    logger.info(f"<tg-emoji emoji-id=\"5303145396254563405\">🤖</tg-emoji> AI Auto-Reply: {'ON' if AI_AUTO_REPLY else 'OFF'}")
    
    logger.info("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> LAM SHOP: Bot started successfully! Ready to serve... <tg-emoji emoji-id=\"5303145396254563405\">🦖</tg-emoji>")
    
    # Tối ưu: Cấu hình polling để phản hồi nhanh hơn
    try:
        application.run_polling(
            poll_interval=0.5,  # Giảm xuống 0.5s để phản hồi nhanh hơn
            timeout=10,  # Giảm timeout để không chờ lâu
            bootstrap_retries=5,
            drop_pending_updates=True  # Bỏ qua updates cũ
        )
    except Conflict as e:
        conflict_text = str(e or "")
        conflict_text_lower = conflict_text.lower()
        if "terminated by other getupdates request" in conflict_text_lower:
            logger.critical("❌ Conflict: getUpdates bị tranh chấp. Sẽ tự restart để thử lại...")
        elif "webhook is active" in conflict_text_lower or "can't use getupdates method while webhook is active" in conflict_text_lower:
            logger.critical("❌ Conflict: Token đang ở chế độ webhook. Đã xóa webhook, sẽ retry...")
        else:
            logger.critical(f"❌ Conflict không xác định: {conflict_text}")
        raise
    except (ValueError, TypeError, KeyError, IndexError) as e:
        logger.critical(f"❌ Bot crash bất ngờ: {e}", exc_info=True)
        raise
    finally:
        release_single_instance_lock()

if __name__ == "__main__":
    # NOTE: Retry loop đã được xử lý bởi app/main.py → run().
    # Block này chỉ dùng nếu chạy trực tiếp file legacy_entry.py.
    main()

