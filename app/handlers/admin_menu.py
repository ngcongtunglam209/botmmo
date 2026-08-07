def build_admin_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            _btn("Kho & Sáº£n pháº©m", icon_id="5854908544712707500", callback_data="adm:kho"),
            _btn("ÄÆ¡n hÃ ng & DT", icon_id="6271437775908639096", callback_data="adm:don"),
        ],
        [
            _btn("NgÆ°á»i dÃ¹ng", icon_id="5453957997418004470", callback_data="adm:users"),
            _btn("Marketing", icon_id="6143344362035090821", callback_data="adm:mk"),
        ],
        [
            _btn("Resell", icon_id="5370715282044100355", callback_data="adm:resell"),
            _btn("API Partners", icon_id="5436359785534466562", callback_data="adm:api"),
        ],
        [
            _btn("Há»‡ thá»‘ng & Tools", icon_id="5341715473882955310", callback_data="adm:sys"),
        ],
    ])

def build_admin_back_row() -> list:
    return [_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data="adm:home")]

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return
    text = (
        "<tg-emoji emoji-id=\"6124902618574625426\">ðŸ‘‘</tg-emoji> <b>Báº¢NG ÄIá»€U KHIá»‚N ADMIN</b> <tg-emoji emoji-id=\"6124902618574625426\">ðŸ‘‘</tg-emoji>\n"
        "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
        "Chá»n má»¥c cáº§n quáº£n lÃ½:"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=build_admin_main_menu())

async def handle_admin_menu_callback(query, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = query.data
    if not data.startswith("adm:"):
        return False

    action = data[4:]
    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID:
        await safe_answer(query, "<tg-emoji emoji-id=\"5424857974784925603\">â›”</tg-emoji> Báº¡n khÃ´ng cÃ³ quyá»n!", show_alert=True)
        return True

    await query.answer()

    async def _admin_edit(text: str, kb: InlineKeyboardMarkup) -> None:
        """Edit admin menu safely; fallback to new message if original cannot be edited."""
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
            return
        except BadRequest as e:
            err = str(e).lower()
            if "message is not modified" in err:
                return
            if "there is no text in the message to edit" in err or "message can't be edited" in err:
                sent = await safe_send_message(
                    context,
                    query.message.chat_id,
                    text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                )
                if sent is not None:
                    try:
                        await query.message.delete()
                    except (Forbidden, BadRequest):
                        pass
                return
            raise

    if action == "home":
        text = (
            "<tg-emoji emoji-id=\"6124902618574625426\">ðŸ‘‘</tg-emoji> <b>Báº¢NG ÄIá»€U KHIá»‚N ADMIN</b> <tg-emoji emoji-id=\"6124902618574625426\">ðŸ‘‘</tg-emoji>\n"
            "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
            "Chá»n má»¥c cáº§n quáº£n lÃ½:"
        )
        await _admin_edit(text, build_admin_main_menu())
        return True

    if action == "kho":
        kb = InlineKeyboardMarkup([
            [_btn("DS sáº£n pháº©m", icon_id="5854908544712707500", callback_data="adm:x:products"),
             _btn("Xem kho Stock", icon_id="6271698656517165534", callback_data="adm:x:viewstock")],
            [_btn("ThÃªm SP má»›i", icon_id="5397916757333654639", callback_data="adm:h:newproduct"),
             _btn("Sá»­a sáº£n pháº©m", icon_id="5828072695694102691", callback_data="adm:h:editproduct")],
            [_btn("ThÃªm hÃ ng vÃ o kho", icon_id="5443127283898405358", callback_data="adm:h:addstock"),
             _btn("ThÃªm link thá»§ cÃ´ng", icon_id="5271604874419647061", callback_data="adm:h:addlink")],
            [_btn("XÃ³a link", icon_id="5445267414562389170", callback_data="adm:x:dellink"),
             _btn("Giá»›i háº¡n Ä‘Æ¡n chá»", icon_id="5212985021870123409", callback_data="adm:h:setlimit")],
            [_btn("XÃ³a sáº£n pháº©m", icon_id="6114086705512321034", callback_data="adm:h:delproduct"),
             _btn("Gá»­i link bÃ¹", icon_id="4967770306555937780", callback_data="adm:h:guilink")],
            build_admin_back_row(),
        ])
        await _admin_edit("<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> <b>KHO & Sáº¢N PHáº¨M</b>\nChá»n thao tÃ¡c:", kb)
        return True

    if action == "don":
        kb = InlineKeyboardMarkup([
            [_btn("Duyá»‡t", icon_id="5021905410089550576", callback_data="adm:x:duyet"),
             _btn("ÄÆ¡n manual chá»", icon_id="5215327832040811010", callback_data="adm:x:pending")],
            [_btn("TÃ¬m Ä‘Æ¡n hÃ ng", icon_id="5355252098403412825", callback_data="adm:h:find"),
             _btn("HoÃ n tiá»n Ä‘Æ¡n", icon_id="6271636667254182477", callback_data="adm:h:refund")],
            [_btn("XÃ³a Ä‘Æ¡n stuck", icon_id="6183912183571682758", callback_data="adm:h:clearpending"),
             _btn("BÃ¡o cÃ¡o doanh thu", icon_id="5244837092042750681", callback_data="adm:x:doanhthu")],
            [_btn("NgÃ¢n sÃ¡ch KM", icon_id="5287231198098117669", callback_data="adm:x:promobudget"),
             _btn("PhÃ¢n tÃ­ch chi tiáº¿t", icon_id="5231200819986047254", callback_data="adm:x:analytics")],
            [_btn("Äá»•i email backup", icon_id="4967770306555937780", callback_data="adm:h:setemail")],
            build_admin_back_row(),
        ])
        await _admin_edit("<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> <b>ÄÆ N HÃ€NG & DOANH THU</b>\nChá»n thao tÃ¡c:", kb)
        return True

    if action == "users":
        kb = InlineKeyboardMarkup([
            [_btn("Danh sÃ¡ch user", icon_id="5256143829672672750", callback_data="adm:x:users"),
             _btn("Info chi tiáº¿t", icon_id="5309965701241379366", callback_data="adm:h:info")],
            [_btn("Cáº¥m user", icon_id="5240241223632954241", callback_data="adm:h:ban", style="danger"),
             _btn("Má»Ÿ cáº¥m user", icon_id="5021905410089550576", callback_data="adm:h:unban", style="success")],
            [_btn("Cá»™ng tiá»n user", icon_id="5397916757333654639", callback_data="adm:h:addmoney", style="success"),
             _btn("Trá»« tiá»n user", icon_id="5406745771280187626", callback_data="adm:h:submoney", style="danger")],
            [_btn("ÄÆ¡n rÃºt tiá»n chá»", icon_id="5212985021870123409", callback_data="adm:x:pending_withdrawals"),
             _btn("DS chat há»— trá»£", icon_id="5443038326535759644", callback_data="adm:x:chats")],
            [_btn("Chat vá»›i user", icon_id="5443038326535759644", callback_data="adm:h:chat", style="primary"),
             _btn("Broadcast", icon_id="6143344362035090821", callback_data="adm:h:bc")],
            build_admin_back_row(),
        ])
        await _admin_edit("<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¤</tg-emoji> <b>QUáº¢N LÃ NGÆ¯á»œI DÃ™NG</b>\nChá»n thao tÃ¡c:", kb)
        return True

    if action == "mk":
        kb = InlineKeyboardMarkup([
            [_btn("Táº¡o Sale iCloud", icon_id="5240228673738527951", callback_data="adm:h:sale"),
             _btn("ThÃªm coupon", icon_id="5377624166436445368", callback_data="adm:h:addcoupon")],
            [_btn("XÃ³a coupon", icon_id="5445267414562389170", callback_data="adm:h:delcoupon"),
             _btn("DS coupon", icon_id="5197269100878907942", callback_data="adm:x:listcoupons")],
            [_btn("Táº¡o Flash Sale", icon_id="5303290914041505430", callback_data="adm:h:flashsale"),
             _btn("DS Flash Sale", icon_id="5197269100878907942", callback_data="adm:h:flashsale_list")],
            [_btn("Dá»«ng Flash Sale", icon_id="6271674836628541366", callback_data="adm:h:flashsale_stop"),
             _btn("Táº¡o Combo Deal", icon_id="5854908544712707500", callback_data="adm:h:combo_create")],
            [_btn("DS Combo", icon_id="5197269100878907942", callback_data="adm:h:combo_list"),
             _btn("XÃ³a Combo", icon_id="5445267414562389170", callback_data="adm:h:combo_delete")],
            [_btn("ThÆ°á»Ÿng top user", icon_id="6206032691075223572", callback_data="adm:x:rewardtop"),
             _btn("Táº¡o Giveaway", icon_id="5193209274452425995", callback_data="adm:h:create_ga")],
            [_btn("DS Giveaway", icon_id="5197269100878907942", callback_data="adm:x:list_ga"),
             _btn("Káº¿t thÃºc GA", icon_id="6271674836628541366", callback_data="adm:h:end_ga")],
            build_admin_back_row(),
        ])
        await _admin_edit("<tg-emoji emoji-id=\"5377624166436445368\">ðŸŽŸ</tg-emoji> <b>MARKETING & KHUYáº¾N MÃƒI</b>\nChá»n thao tÃ¡c:", kb)
        return True

    if action == "resell":
        kb = InlineKeyboardMarkup([
            [_btn("ThÃªm SP resell", icon_id="5397916757333654639", callback_data="adm:h:add_resell"),
             _btn("DS SP resell", icon_id="5197269100878907942", callback_data="adm:x:list_resell")],
            [_btn("Sá»­a markup %", icon_id="5828072695694102691", callback_data="adm:h:edit_markup"),
             _btn("XÃ³a SP resell", icon_id="5445267414562389170", callback_data="adm:h:del_resell")],
            [_btn("Äá»“ng bá»™ giÃ¡ & kho", icon_id="5370715282044100355", callback_data="adm:x:sync_resell")],
            [_btn("DS dá»‹ch vá»¥ SOCIAL_SOURCE", icon_id="5197269100878907942", callback_data="adm:x:list_ctt"),
             _btn("Äá»“ng bá»™ SOCIAL_SOURCE", icon_id="5370715282044100355", callback_data="adm:x:sync_ctt")],
            [_btn("Sá»‘ dÆ° SOCIAL_SOURCE", icon_id="5278467510604160626", callback_data="adm:x:ctt_balance")],
            build_admin_back_row(),
        ])
        await _admin_edit("<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> <b>NGUá»’N NGOÃ€I</b>\nChá»n thao tÃ¡c:", kb)
        return True

    if action == "api":
        kb = InlineKeyboardMarkup([
            [_btn("API Partners", icon_id="5436359785534466562", callback_data="adm:x:api"),
             _btn("ThÃªm Partner", icon_id="5397916757333654639", callback_data="adm:h:addapi")],
            [_btn("XÃ³a Partner", icon_id="5445267414562389170", callback_data="adm:h:delapi"),
             _btn("Náº¡p tiá»n API", icon_id="5278467510604160626", callback_data="adm:h:napi")],
            build_admin_back_row(),
        ])
        await _admin_edit("<tg-emoji emoji-id=\"5303145396254563405\">ðŸ¤–</tg-emoji> <b>API PARTNERS</b>\nChá»n thao tÃ¡c:", kb)
        return True

    if action == "sys":
        _maintenance_icon = "<tg-emoji emoji-id=\"6269163801178804220\">ðŸŸ¢</tg-emoji>" if not MAINTENANCE_MODE else "<tg-emoji emoji-id=\"5318840353510408444\">ðŸ”´</tg-emoji>"
        _ai_icon = "<tg-emoji emoji-id=\"6269163801178804220\">ðŸŸ¢</tg-emoji>" if AI_AUTO_REPLY else "<tg-emoji emoji-id=\"5318840353510408444\">ðŸ”´</tg-emoji>"
        kb = InlineKeyboardMarkup([
            [_btn("Báº£o trÃ¬ ON/OFF", icon_id="5462921117423384478", callback_data="adm:h:baotri"),
             _btn("AI ON/OFF", icon_id="5287684458881756303", callback_data="adm:h:aimode")],
            [_btn("Test AI", icon_id="5443038326535759644", callback_data="adm:h:ask"),
             _btn("Backup thá»§ cÃ´ng", icon_id="5462956611033117422", callback_data="adm:x:backup")],
            [InlineKeyboardButton("<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¥</tg-emoji> Import dá»¯ liá»‡u", callback_data="adm:x:nhapdata"),
             _btn("Cháº¿ Ä‘á»™ test", icon_id="5411512278740640309", callback_data="adm:x:testing")],
            [_btn("ThÃ´ng bÃ¡o háº¿t hÃ ng", icon_id="5458603043203327669", callback_data="adm:x:notify"),
             _btn("Reset thÃ´ng bÃ¡o", icon_id="5370715282044100355", callback_data="adm:x:resetnotify")],
            build_admin_back_row(),
        ])
        await _admin_edit("<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡</tg-emoji> <b>Há»† THá»NG & TOOLS</b>\nChá»n thao tÃ¡c:", kb)
        return True

    if action.startswith("h:"):
        cmd = action[2:]
        if cmd == "add_ctt":
            kb = InlineKeyboardMarkup([
                [_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data="adm:resell")]
            ])
            await _admin_edit(
                "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>/add_ctt ÄÃƒ DEPRECATED</b>\n\n"
                "Catalog SOCIAL_SOURCE giá» Ä‘Æ°á»£c Ä‘á»“ng bá»™ tá»± Ä‘á»™ng tá»« nguá»“n.\n"
                "DÃ¹ng <code>/sync_ctt</code> Ä‘á»ƒ force refresh toÃ n bá»™ catalog social.",
                kb,
            )
            return True
        if cmd == "del_ctt":
            kb = InlineKeyboardMarkup([
                [_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data="adm:resell")]
            ])
            await _admin_edit(
                "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>/del_ctt KHÃ”NG CÃ’N LÃ€ FLOW CHÃNH</b>\n\n"
                "Dá»‹ch vá»¥ SOCIAL_SOURCE auto-managed sáº½ Ä‘Æ°á»£c Ä‘Ã¡nh dáº¥u inactive khi biáº¿n máº¥t tá»« nguá»“n.",
                kb,
            )
            return True
        hints = {
            "newproduct":     "<tg-emoji emoji-id=\"5397916757333654639\">âž•</tg-emoji> ThÃªm sáº£n pháº©m má»›i (Wizard):\n<code>/newproduct</code>",
            "editproduct":   "<tg-emoji emoji-id=\"5350752364246606166\">âœï¸</tg-emoji> Sá»­a sáº£n pháº©m:\n<code>/editproduct</code>",
            "addstock":       "<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¥</tg-emoji> ThÃªm hÃ ng vÃ o kho:\n<code>/addstock</code>",
            "addlink":        "<tg-emoji emoji-id=\"5397916757333654639\">âž•</tg-emoji> ThÃªm link thá»§ cÃ´ng:\n<code>/addlink [link]</code>",
            "setlimit":       "<tg-emoji emoji-id=\"5424857974784925603\">ðŸš«</tg-emoji> Giá»›i háº¡n Ä‘Æ¡n chá»:\n<code>/setlimit [product_id] [sá»‘]</code>",
            "delproduct":     "âŒ XÃ³a sáº£n pháº©m:\n<code>/delproduct [product_id]</code>",
            "guilink":        "<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¤</tg-emoji> Gá»­i link bÃ¹:\n<code>/guilink [email] [link]</code>",
            "find":           "<tg-emoji emoji-id=\"5429571366384842791\">ðŸ”</tg-emoji> TÃ¬m Ä‘Æ¡n hÃ ng:\n<code>/find [mÃ£_Ä‘Æ¡n]</code>",
            "refund":         "<tg-emoji emoji-id=\"5863724849851011383\">ðŸ’¸</tg-emoji> HoÃ n tiá»n Ä‘Æ¡n:\n<code>/refund [mÃ£_Ä‘Æ¡n]</code>",
            "clearpending":   "<tg-emoji emoji-id=\"5462956611033117422\">ðŸ§¹</tg-emoji> XÃ³a Ä‘Æ¡n stuck:\n<code>/clearpending [mÃ£/all]</code>",
            "setemail":       "<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“§</tg-emoji> Äá»•i email backup:\n<code>/setemail [email]</code>",
            "info":           "â„¹ï¸ Xem info user:\n<code>/info [user_id]</code>\nHoáº·c: <code>/info @username</code>",
            "ban":            "<tg-emoji emoji-id=\"5424857974784925603\">ðŸš«</tg-emoji> Cáº¥m user:\n<code>/ban [user_id]</code>",
            "unban":          "<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> Má»Ÿ cáº¥m user:\n<code>/unban [user_id]</code>",
            "addmoney":       "<tg-emoji emoji-id=\"5397916757333654639\">âž•</tg-emoji> Cá»™ng tiá»n user:\n<code>/addmoney [user_id] [sá»‘_tiá»n]</code>",
            "submoney":       "<tg-emoji emoji-id=\"5406745771280187626\">âž–</tg-emoji> Trá»« tiá»n user:\n<code>/submoney [user_id] [sá»‘_tiá»n]</code>",
            "chat":           "<tg-emoji emoji-id=\"6129860303619363484\">ðŸ’¬</tg-emoji> Chat vá»›i user:\n<code>/chat [user_id]</code>",
            "bc":             "<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“¢</tg-emoji> Broadcast (Reply vÃ o tin nháº¯n):\n<code>/bc</code>",
            "sale":           "<tg-emoji emoji-id=\"6260059243605398502\">ðŸ·</tg-emoji> Táº¡o Sale iCloud:\n<code>/sale [%_giáº£m] [sá»‘_lÆ°á»£ng] [sá»‘_ngÃ y]</code>",
            "addcoupon":      "<tg-emoji emoji-id=\"5377624166436445368\">ðŸŽŸ</tg-emoji> ThÃªm coupon:\n<code>/addcoupon [MÃ£] [Sl] [Tiá»n] [NgÃ y]</code>",
            "delcoupon":      "<tg-emoji emoji-id=\"5424857974784925603\">ðŸ—‘</tg-emoji> XÃ³a coupon:\n<code>/delcoupon [MÃ£]</code>",
            "flashsale":      "<tg-emoji emoji-id=\"5303290914041505430\">âš¡</tg-emoji> Táº¡o Flash Sale:\n<code>/flashsale [%_giáº£m] [sá»‘_phÃºt] [product_id / all]</code>\n\nVÃ­ dá»¥:\n<code>/flashsale 30 60 all</code> â€” Giáº£m 30% táº¥t cáº£ trong 60 phÃºt\n<code>/flashsale 50 30 netflix_1</code> â€” Giáº£m 50% SP cá»¥ thá»ƒ trong 30 phÃºt",
            "flashsale_list": "<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“‹</tg-emoji> Xem Flash Sale Ä‘ang cháº¡y:\n<code>/flashsale list</code>",
            "flashsale_stop": "<tg-emoji emoji-id=\"5447644880824181073\">â¹</tg-emoji> Dá»«ng Flash Sale:\n<code>/flashsale stop [flash_sale_id]</code>",
            "combo_create":   "<tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ</tg-emoji> Táº¡o Combo Deal:\n<code>/combo create</code>",
            "combo_list":     "<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“‹</tg-emoji> Xem Combo Ä‘ang cháº¡y:\n<code>/combo list</code>",
            "combo_delete":   "<tg-emoji emoji-id=\"5424857974784925603\">ðŸ—‘</tg-emoji> XÃ³a Combo:\n<code>/combo delete [combo_id]</code>",
            "add_resell":     "<tg-emoji emoji-id=\"5397916757333654639\">âž•</tg-emoji> ThÃªm SP resell:\n<code>/add_resell [supplier_source_product_id]</code>",
            "edit_markup":    "<tg-emoji emoji-id=\"5350752364246606166\">âœï¸</tg-emoji> Sá»­a markup %:\n<code>/edit_markup [product_id] [%]</code>",
            "del_resell":     "<tg-emoji emoji-id=\"5424857974784925603\">ðŸ—‘</tg-emoji> XÃ³a SP resell:\n<code>/del_resell [product_id]</code>",
            "add_ctt":        "<tg-emoji emoji-id=\"5397916757333654639\">âž•</tg-emoji> ThÃªm dá»‹ch vá»¥ SOCIAL_SOURCE:\n<code>/add_ctt [service_id] [package_quantity] [gia_ban_vnd] [ten_tuy_chinh]</code>",
            "del_ctt":        "<tg-emoji emoji-id=\"5424857974784925603\">ðŸ—‘</tg-emoji> XÃ³a dá»‹ch vá»¥ SOCIAL_SOURCE:\n<code>/del_ctt [product_id]</code>",
            "addapi":         "<tg-emoji emoji-id=\"5397916757333654639\">âž•</tg-emoji> ThÃªm Partner API:\n<code>/addapi [TÃªn_Ä‘á»‘i_tÃ¡c]</code>",
            "delapi":         "<tg-emoji emoji-id=\"5424857974784925603\">ðŸ—‘</tg-emoji> XÃ³a Partner:\n<code>/delapi [API_Key]</code>",
            "napi":           "<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> Náº¡p tiá»n API:\n<code>/napi [Key/TÃªn] [Sá»‘_tiá»n]</code>\nHoáº·c táº¡o QR:\n<code>/napi qr [Key/TÃªn] [Sá»‘_tiá»n]</code>",
            "create_ga":      "<tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ‰</tg-emoji> Táº¡o Giveaway má»›i:\n<code>/create_ga</code>",
            "end_ga":         "<tg-emoji emoji-id=\"5424857974784925603\">ðŸ”š</tg-emoji> Káº¿t thÃºc Giveaway:\n1. Reply vÃ o tin nháº¯n GA vÃ  gÃµ <code>/endga</code>\n2. Hoáº·c: <code>/endga [GA_ID]</code>",
            "baotri":         "<tg-emoji emoji-id=\"5215392879320505675\">ðŸ› </tg-emoji> Báº­t/Táº¯t báº£o trÃ¬:\n<code>/baotri on</code> hoáº·c <code>/baotri off</code>",
            "aimode":         "<tg-emoji emoji-id=\"5303145396254563405\">ðŸ¤–</tg-emoji> Báº­t/Táº¯t AI reply:\n<code>/aimode on</code> hoáº·c <code>/aimode off</code>",
            "ask":            "<tg-emoji emoji-id=\"5303145396254563405\">ðŸ¤–</tg-emoji> Test AI assistant:\n<code>/ask [cÃ¢u há»i]</code>",
        }
        hint = hints.get(cmd, f"DÃ¹ng lá»‡nh: <code>/{cmd}</code>")
        back_category = {
            "newproduct": "kho", "editproduct": "kho", "addstock": "kho",
            "addlink": "kho", "setlimit": "kho", "delproduct": "kho", "guilink": "kho",
            "find": "don", "refund": "don", "clearpending": "don", "setemail": "don",
            "info": "users", "ban": "users", "unban": "users", "addmoney": "users",
            "submoney": "users", "chat": "users", "bc": "users",
            "sale": "mk", "addcoupon": "mk", "delcoupon": "mk", "create_ga": "mk", "end_ga": "mk",
            "flashsale": "mk", "flashsale_list": "mk", "flashsale_stop": "mk",
            "combo_create": "mk", "combo_list": "mk", "combo_delete": "mk",
            "add_resell": "resell", "edit_markup": "resell", "del_resell": "resell",
            "add_ctt": "resell", "del_ctt": "resell",
            "addapi": "api", "delapi": "api", "napi": "api",
            "baotri": "sys", "aimode": "sys", "ask": "sys",
        }
        cat = back_category.get(cmd, "home")
        kb = InlineKeyboardMarkup([
            [_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data=f"adm:{cat}")]
        ])
        await _admin_edit(f"<tg-emoji emoji-id=\"5460753627817723162\">ðŸ’¡</tg-emoji> <b>HÆ¯á»šNG DáºªN Sá»¬ Dá»¤NG</b>\n\n{hint}", kb)
        return True

    if action.startswith("x:"):
        cmd = action[2:]
        if cmd == "nhapdata":
            kb = InlineKeyboardMarkup([
                [_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data="adm:sys")]
            ])
            await _admin_edit(
                "<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¥</tg-emoji> <b>IMPORT Dá»® LIá»†U Tá»ª BACKUP</b>\n\n"
                "CÃ¡ch dÃ¹ng:\n"
                "1. DÃ¹ng <code>/backup</code> hoáº·c láº¥y file ZIP backup sáºµn cÃ³.\n"
                "2. Reply vÃ o file ZIP Ä‘Ã³ vÃ  gÃµ <code>/nhapdata</code>.\n"
                "3. Hoáº·c gá»­i trá»±c tiáº¿p file .zip kÃ¨m caption <code>/nhapdata</code>.\n\n"
                "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Chá»‰ nháº­n file <code>.zip</code> backup há»£p lá»‡.",
                kb,
            )
            return True

        cmd_map = {
            "products":             listproducts_command,
            "kho":                  kholink_command,
            "dellink":              removelink_command,
            "duyet":                duyet_command,
            "pending":              pending_manual_command,
            "doanhthu":             doanhthu_command,
            "promobudget":          promobudget_command,
            "analytics":            analytics_command,
            "users":                listusers_command,
            "pending_withdrawals":  pending_withdrawals_command,
            "chats":                chats_command,
            "listcoupons":          listcoupons_command,
            "rewardtop":            rewardtop_command,
            "list_ga":              list_ga_command,
            "list_resell":          list_resell_command,
            "sync_resell":          sync_resell_command,
            "list_ctt":             list_ctt_command,
            "sync_ctt":             sync_ctt_command,
            "ctt_balance":          ctt_balance_command,
            "api":                  listapi_command,
            "backup":               backup_command,
            "testing":              testing_command,
            "notify":               notify_command,
            "resetnotify":          resetnotify_command,
        }
        handler_fn = cmd_map.get(cmd)
        if handler_fn:
            fake_update = update_from_callback(query)
            if fake_update:
                try:
                    await handler_fn(fake_update, context)
                except Exception as e:
                    logger.error(f"Admin menu exec error ({cmd}): {e}")
                    await context.bot.send_message(
                        ADMIN_USER_ID,
                        f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Lá»—i khi thá»±c thi <code>/{cmd}</code>: {html.escape(str(e))}",
                        parse_mode=ParseMode.HTML
                    )
        else:
            await context.bot.send_message(
                ADMIN_USER_ID,
                f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Chá»©c nÄƒng <code>{cmd}</code> chÆ°a Ä‘Æ°á»£c liÃªn káº¿t vá»›i menu.",
                parse_mode=ParseMode.HTML
            )
        return True

    return False

def update_from_callback(query) -> object:
    class FakeMessage:
        def __init__(self, q):
            self.chat = q.message.chat
            self.chat_id = q.message.chat_id
            self.from_user = q.from_user
            self.text = ""
            self.reply_to_message = None
            self.photo = None
            self.document = None
            self.message_id = q.message.message_id
            self._query = q
        async def reply_text(self, *args, **kwargs):
            return await self._query.message.reply_text(*args, **kwargs)
        async def reply_html(self, *args, **kwargs):
            return await self._query.message.reply_html(*args, **kwargs)
        async def reply_photo(self, *args, **kwargs):
            return await self._query.message.reply_photo(*args, **kwargs)
        async def reply_document(self, *args, **kwargs):
            return await self._query.message.reply_document(*args, **kwargs)

    class FakeUpdate:
        def __init__(self, q):
            self.effective_user = q.from_user
            self.effective_chat = q.message.chat
            self.message = FakeMessage(q)
            self.callback_query = q
            self._bot = q.get_bot()

        def get_bot(self):
            return self._bot

    return FakeUpdate(query)

async def handle_admin_quick_action(query, context: ContextTypes.DEFAULT_TYPE):
    parts = query.data.split(":")
    if len(parts) < 3:
        await safe_answer(query, "Dá»¯ liá»‡u khÃ´ng há»£p lá»‡", show_alert=True)
        return

    action = parts[1]
    target_id_str = parts[2]

    try:
        target_id = int(target_id_str)
    except ValueError:
        await safe_answer(query, "ID khÃ´ng há»£p lá»‡", show_alert=True)
        return

    await query.answer()

    if action == "toggleban":
        if target_id == ADMIN_USER_ID:
            await query.message.reply_text("âŒ KhÃ´ng thá»ƒ cáº¥m chÃ­nh mÃ¬nh.")
            return
        if target_id in banned_users:
            banned_users.discard(target_id)
            await save_data()
            await query.message.reply_text(f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> ÄÃ£ má»Ÿ cáº¥m user ID: <code>{target_id}</code>", parse_mode=ParseMode.HTML)
        else:
            banned_users.add(target_id)
            await save_data()
            await query.message.reply_text(f"<tg-emoji emoji-id=\"5424857974784925603\">ðŸš«</tg-emoji> ÄÃ£ cáº¥m user ID: <code>{target_id}</code>", parse_mode=ParseMode.HTML)

    elif action == "addmoney":
        context.user_data['quick_action'] = f"addmoney:{target_id}"
        user_info = user_data_db.get(target_id_str, {})
        name = user_info.get('first_name', 'N/A')
        await query.message.reply_text(
            f"<tg-emoji emoji-id=\"5397916757333654639\">âž•</tg-emoji> <b>Cá»˜NG TIá»€N CHO USER</b>\n\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¤</tg-emoji> {name} (ID: <code>{target_id}</code>)\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> Sá»‘ dÆ° hiá»‡n táº¡i: {user_info.get('balance', 0):,} VNÄ\n\n"
            f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ”¢</tg-emoji> Nháº­p sá»‘ tiá»n cáº§n cá»™ng:\n"
            f"<i>(GÃµ /cancel Ä‘á»ƒ há»§y)</i>",
            parse_mode=ParseMode.HTML
        )

    elif action == "submoney":
        context.user_data['quick_action'] = f"submoney:{target_id}"
        user_info = user_data_db.get(target_id_str, {})
        name = user_info.get('first_name', 'N/A')
        await query.message.reply_text(
            f"<tg-emoji emoji-id=\"5406745771280187626\">âž–</tg-emoji> <b>TRá»ª TIá»€N USER</b>\n\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¤</tg-emoji> {name} (ID: <code>{target_id}</code>)\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> Sá»‘ dÆ° hiá»‡n táº¡i: {user_info.get('balance', 0):,} VNÄ\n\n"
            f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ”¢</tg-emoji> Nháº­p sá»‘ tiá»n cáº§n trá»«:\n"
            f"<i>(GÃµ /cancel Ä‘á»ƒ há»§y)</i>",
            parse_mode=ParseMode.HTML
        )

    elif action == "chat":
        context.user_data['admin_chat_target'] = target_id
        user_info = user_data_db.get(target_id_str, {})
        name = user_info.get('first_name', 'N/A')
        await query.message.reply_text(
            f"<tg-emoji emoji-id=\"6129860303619363484\">ðŸ’¬</tg-emoji> <b>CHAT Vá»šI USER</b>\n\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¤</tg-emoji> {name} (ID: <code>{target_id}</code>)\n\n"
            f"GÃµ tin nháº¯n Ä‘á»ƒ gá»­i cho user.\n"
            f"<i>GÃµ /cancel Ä‘á»ƒ thoÃ¡t.</i>",
            parse_mode=ParseMode.HTML
        )

async def warranty_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state = context.user_data.get('state')
    
    if user_state == 'awaiting_warranty_photo':
        order_code = context.user_data.get('warranty_claim_order')
        description = context.user_data.get('warranty_description')
        if not update.message.photo: return
        
        photo = update.message.photo[-1].file_id
        
        # Create warranty claim
        claim_id = f"WRC{int(time.time())}"
        warranty_claims[claim_id] = {
            'order_code': order_code,
            'user_id': update.effective_user.id,
            'product_id': order_index[order_code].get('product_id'),
            'description': description,
            'photos': [photo],
            'status': 'pending',
            'timestamp': time.time(),
            'admin_notes': ''
        }
        
        await save_data()
        await clear_user_state(context)
        
        # Notify user
        await update.message.reply_text(
            f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> <b>ÄÃƒ Gá»¬I YÃŠU Cáº¦U Báº¢O HÃ€NH</b>\n\n"
            f"MÃ£ yÃªu cáº§u: <code>{claim_id}</code>\n"
            f"Admin sáº½ xem xÃ©t trong 24h",
            parse_mode=ParseMode.HTML,
            reply_markup=create_main_menu(user_id=update.effective_user.id)
        )
        
        # Notify admin
        try:
            await context.bot.send_photo(
                ADMIN_USER_ID,
                photo=photo,
                caption=(
                    f"<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡ï¸</tg-emoji> <b>YÃŠU Cáº¦U Báº¢O HÃ€NH Má»šI</b>\n\n"
                    f"MÃ£: <code>{claim_id}</code>\n"
                    f"ÄÆ¡n: <code>{order_code}</code>\n"
                    f"User: {format_user_mention_html(update.effective_user)}\n\n"
                    f"MÃ´ táº£:\n<i>{description}</i>"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    _btn("Duyá»‡t", icon_id="5021905410089550576", callback_data=f"approve_warranty:{claim_id}"),
                    _btn("Tá»« chá»‘i", icon_id="6114086705512321034", callback_data=f"reject_warranty:{claim_id}")
                ]])
            )
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.error(f"Cannot notify admin of warranty claim: {e}")


