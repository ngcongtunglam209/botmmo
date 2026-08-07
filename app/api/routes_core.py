async def _api_create_order(
    actor: dict,
    partner_ref: str,
    customer_email: str | None = None,
    customer_id: str | None = None,
    note: str | None = None,
    product_id: str | None = None,
    quantity: int = 1,
    target_link: str | None = None,
    comments: str | None = None,
):
    if MAINTENANCE_MODE:
        raise HTTPException(status_code=503, detail="System is in maintenance mode")

    safe_partner_ref = _api_sanitize_partner_ref(partner_ref)
    if not safe_partner_ref:
        raise HTTPException(status_code=400, detail="partner_ref contains no valid characters")
    partner_ref_key = safe_partner_ref.upper()
    email_value = _api_clean_text(customer_email, 120)
    customer_id_value = _api_clean_text(customer_id, API_V2_MAX_CUSTOMER_ID_LEN)
    note_value = _api_clean_text(note, API_V2_MAX_NOTE_LEN)
    product_id_value = _api_clean_text(product_id, API_V2_MAX_PRODUCT_ID_LEN)
    target_link_value = _api_clean_text(target_link, 2000)
    comments_value = _api_clean_text(comments, 4000)
    if email_value and not EMAIL_REGEX.match(email_value):
        raise HTTPException(status_code=400, detail="Invalid email format")
    try:
        qty = int(quantity)
    except (ValueError, TypeError, KeyError, IndexError):
        raise HTTPException(status_code=400, detail="quantity must be an integer")
    if qty < 1:
        raise HTTPException(status_code=400, detail="quantity must be greater than 0")
    if qty > API_V2_MAX_QUANTITY:
        raise HTTPException(status_code=400, detail=f"quantity must be in range 1..{API_V2_MAX_QUANTITY}")

    if not product_id_value:
        raise HTTPException(status_code=400, detail="product_id is required")
    selected_product = products.get(product_id_value)
    if not isinstance(selected_product, dict):
        raise HTTPException(status_code=404, detail="product_not_found")
    unit_price, base_unit_price, discount_type, discount_info, _owner_user_id = _api_get_effective_product_price(
        actor, product_id_value, selected_product
    )
    if unit_price <= 0:
        raise HTTPException(status_code=400, detail="invalid_product_price")
    sale_price = unit_price * qty
    base_list_amount = base_unit_price * qty

    partner_name = str(actor.get("partner_name") or "Unknown")

    async def _build_and_save_order(current_partner_name: str):
        order_code = await generate_unique_order_code(
            prefix="ODER-",
            length=8,
            charset=string.ascii_uppercase + string.digits,
        )
        product_data = products.get(product_id_value)
        if not isinstance(product_data, dict):
            raise HTTPException(status_code=404, detail="product_not_found")

        product_name = str(product_data.get("name") or product_id_value)
        requires_gmail = bool(product_data.get("requires_gmail", False))
        items_bought = []
        status_text_value = "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Hoàn thành (API Product)"
        delivery_method = "instant_items"
        link_value = "Store Product"
        actual_qty = qty
        refunded_qty = 0
        refund_amount = 0
        charged_amount = sale_price

        if requires_gmail:
            status_text_value = "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Chờ xử lý manual (API)"
            delivery_method = "manual_pending"
            link_value = f"Manual - {product_name}"
        else:
            stock_result = await consume_local_stock_items(
                product_id_value,
                qty,
                order_code=order_code,
                order_state={
                    "user_id": f"PARTNER_{current_partner_name}",
                    "product_id": product_id_value,
                    "api_customer_email": email_value or "",
                    "api_customer_id": customer_id_value or "",
                },
                persist_tables=(PRODUCTS_FILE,),
                source="api_direct_order",
            )
            if stock_result.get("items") is None:
                raise HTTPException(
                    status_code=409,
                    detail=f"Insufficient stock. available={int(stock_result.get('available', 0) or 0)}, required={qty}"
                )
            items_bought = list(stock_result.get("items") or [])
            actual_qty = int(stock_result.get("actual_delivered") or len(items_bought))
            refunded_qty = int(stock_result.get("refunded_qty") or 0)
            refund_amount = refunded_qty * unit_price
            charged_amount = sale_price - refund_amount
            delivery_method = "stock_items"
            link_value = "Store Product"

        order_data = {
            "user_id": f"PARTNER_{current_partner_name}",
            "order_code": order_code,
            "email": email_value or "api_partner@ref",
            "amount": charged_amount,
            "status": status_text_value,
            "type": "store_product",
            "link": link_value,
            "timestamp": time.time(),
            "coupon_used": f"API-{current_partner_name}",
            "refunded_at": 0,
            "full_name": f"Partner: {current_partner_name}",
            "username": "api_partner",
            "product_id": product_id_value,
            "product_name": product_name,
            "quantity": actual_qty,
            "original_quantity": qty,
            "refunded_qty": refunded_qty,
            "refund_amount": refund_amount,
            "items": items_bought,
            "delivery_method": delivery_method,
            "source": "developer_api_v2",
            "api_partner_ref": safe_partner_ref,
            "api_partner_ref_key": partner_ref_key,
            "api_partner_key_hash": actor.get("key_fingerprint"),
            "api_owner_user_id": _api_get_actor_owner_user_id(actor) or 0,
            "api_customer_email": email_value or "",
            "api_customer_id": customer_id_value or "",
            "api_note": note_value or "",
            "api_send_email": False,
            "unit_price": unit_price,
            "list_unit_price": base_unit_price,
            "list_amount": base_list_amount,
            "discount_type": discount_type or "",
        }
        if isinstance(discount_info, dict):
            try:
                order_data["discount_percent"] = int(discount_info.get("discount_percent", 0) or 0)
            except (ValueError, TypeError, KeyError, IndexError):
                order_data["discount_percent"] = 0
            if discount_type == "partner_tier":
                order_data["partner_tier"] = str(discount_info.get("tier") or "standard")
                order_data["partner_tier_name"] = str(discount_info.get("tier_name") or "Standard")
                order_data["partner_monthly_volume"] = int(discount_info.get("monthly_volume", 0) or 0)
        if requires_gmail:
            order_data["manual_fulfillment"] = True

        db_add_order(order_data)
        await save_data(force=True)
        return order_data

    actor_lock_scope = "admin-master" if actor.get("is_admin") else str(actor.get("key_fingerprint") or actor.get("api_key") or "partner")
    order_ref_lock = await get_api_key_lock(f"__api_order_ref__:{actor_lock_scope}:{partner_ref_key}")
    async with order_ref_lock:
        if actor.get("is_admin"):
            existing_order = _api_find_order_by_partner_ref(actor, safe_partner_ref)
            if existing_order:
                await _api_notify_admin_order(existing_order, partner_name, "unlimited")
                return existing_order, "unlimited", True
            if not db_reserve_partner_ref(actor_lock_scope, partner_ref_key):
                existing_order = _api_find_order_by_partner_ref(actor, safe_partner_ref)
                if existing_order:
                    return existing_order, "unlimited", True
                raise HTTPException(status_code=409, detail="partner_ref is already processing")
            try:
                order_data = await _build_and_save_order(partner_name)
                db_complete_partner_ref(actor_lock_scope, partner_ref_key, order_data["order_code"])
            except HTTPException as create_http_error:
                if create_http_error.status_code == 502:
                    db_mark_partner_ref_review(actor_lock_scope, partner_ref_key)
                else:
                    db_release_partner_ref(actor_lock_scope, partner_ref_key)
                raise
            except (ValueError, TypeError, KeyError, AttributeError) as create_error:
                db_release_partner_ref(actor_lock_scope, partner_ref_key)
                logger.error(f"API V2 Error (admin create): {create_error}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal Server Error")

            logger.info(
                f"API V2 Sell: {order_data['order_code']} - {order_data.get('product_name')} x{order_data.get('quantity', 1)} "
                f"(Partner: {partner_name} - Balance: unlimited)"
            )
            order_data["api_partner_remaining_balance"] = "unlimited"
            await _api_notify_admin_order(order_data, partner_name, "unlimited")
            return order_data, "unlimited", False

        api_key = actor.get("api_key")
        api_key_lock = await get_api_key_lock(api_key)
        async with api_key_lock:
            key_data = _api_normalize_partner_key(api_key)
            if key_data is None:
                raise HTTPException(status_code=401, detail="Invalid API Key")

            partner_name = str(key_data.get("name") or partner_name)
            actor["partner_name"] = partner_name
            actor["key_data"] = key_data
            actor["balance"] = _api_get_partner_display_balance(api_key, key_data)

            existing_order = _api_find_order_by_partner_ref(actor, safe_partner_ref)
            if existing_order:
                remaining_balance = _api_get_partner_display_balance(api_key, key_data)
                if "api_partner_remaining_balance" not in existing_order:
                    existing_order["api_partner_remaining_balance"] = remaining_balance
                await _api_notify_admin_order(existing_order, partner_name, remaining_balance)
                return existing_order, remaining_balance, True

            if not db_reserve_partner_ref(actor_lock_scope, partner_ref_key):
                existing_order = _api_find_order_by_partner_ref(actor, safe_partner_ref)
                if existing_order:
                    remaining_balance = _api_get_partner_display_balance(api_key, key_data)
                    return existing_order, remaining_balance, True
                raise HTTPException(status_code=409, detail="partner_ref is already processing")

            current_balance = _api_get_partner_display_balance(api_key, key_data)
            if current_balance < sale_price:
                db_release_partner_ref(actor_lock_scope, partner_ref_key)
                raise HTTPException(status_code=402, detail=f"Insufficient balance. Your balance: {current_balance:,}")

            _new_balance, key_data = _api_set_partner_effective_balance_unlocked(api_key, key_data, current_balance - sale_price)
            try:
                order_data = await _build_and_save_order(partner_name)
                db_complete_partner_ref(actor_lock_scope, partner_ref_key, order_data["order_code"])
                charged_amount = int(order_data.get("amount", sale_price) or 0)
                if charged_amount != sale_price:
                    _api_set_partner_effective_balance_unlocked(api_key, key_data, current_balance - charged_amount)
                    await save_data(force=True)
                try:
                    db_record_api_partner_ledger(
                        actor.get("key_fingerprint") or _api_key_fingerprint(api_key), partner_name, "usage", -charged_amount,
                        current_balance, current_balance - charged_amount, reference=order_data.get("order_code") or "",
                        reason=f"API order {order_data.get('order_code') or safe_partner_ref}",
                        idempotency_key=f"usage:{order_data.get('order_code') or safe_partner_ref}",
                    )
                except (ValueError, sqlite3.Error) as ledger_error:
                    logger.error("Cannot write API usage ledger for %s: %s", order_data.get("order_code"), ledger_error)
            except HTTPException as create_http_error:
                if create_http_error.status_code == 502:
                    db_mark_partner_ref_review(actor_lock_scope, partner_ref_key)
                else:
                    db_release_partner_ref(actor_lock_scope, partner_ref_key)
                _api_set_partner_effective_balance_unlocked(api_key, key_data, current_balance)
                try:
                    await save_data(force=True)
                except (ValueError, TypeError, KeyError, IndexError) as rollback_error:
                    logger.error(f"❌ CRITICAL: Cannot rollback partner balance after HTTP error: {rollback_error}")
                raise create_http_error
            except (ValueError, TypeError, KeyError, IndexError) as create_error:
                db_release_partner_ref(actor_lock_scope, partner_ref_key)
                _api_set_partner_effective_balance_unlocked(api_key, key_data, current_balance)
                try:
                    await save_data(force=True)
                except (ValueError, TypeError, KeyError, IndexError) as rollback_error:
                    logger.error(f"❌ CRITICAL: Cannot rollback partner balance after create fail: {rollback_error}")
                logger.error(f"API V2 Error (partner create): {create_error}", exc_info=True)
                raise HTTPException(status_code=500, detail="Internal Server Error")

            remaining_balance = _api_get_partner_display_balance(api_key, key_data)

        logger.info(
            f"API V2 Sell: {order_data['order_code']} - {order_data.get('product_name')} x{order_data.get('quantity', 1)} "
            f"(Partner: {partner_name} - Balance: {remaining_balance})"
        )
        order_data["api_partner_remaining_balance"] = remaining_balance
        await _api_notify_admin_order(order_data, partner_name, remaining_balance)
        return order_data, remaining_balance, False


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.get("/api/status")
async def get_status(
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
):
    """Kiểm tra trạng thái bot và kho hàng"""
    actor = _api_require_actor(
        x_api_key=x_api_key,
        x_api_token=x_api_token,
        authorization=authorization,
    )
    status_payload = _api_status_payload(actor)
    return {
        "status": status_payload["status"],
        "maintenance_mode": status_payload["maintenance_mode"],
        "stock_count": status_payload["stock_count"],
        "pending_orders": status_payload["pending_orders"],
        "your_balance": status_payload["your_balance"],
    }

@app.post(
    "/api/buy",
    tags=["Legacy"],
    summary="Legacy: mua link trực tiếp",
    description=(
        "Endpoint cũ để mua 1 link trực tiếp. Với API V2, partner nên dùng `POST /api/v2/orders`; "
        "chỉ endpoint legacy này mới xem `link` là nội dung giao hàng chính."
    ),
)
async def buy_link(
    req: OrderRequest,
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
):
    """Mua link (Lấy 1 link từ kho)"""
    actor = _api_require_actor(
        x_api_key=x_api_key,
        x_api_token=x_api_token,
        authorization=authorization,
    )
    if not req.partner_ref or not req.partner_ref.strip():
        raise HTTPException(status_code=400, detail="partner_ref is required")
    order_data, remaining_balance, idempotent_replay = await _api_create_order(
        actor=actor,
        partner_ref=req.partner_ref,
        customer_email=req.email,
        note="legacy_api_buy",
        product_id=req.product_id,
        quantity=req.quantity or 1,
    )
    return {
        "status": "success",
        "order_code": order_data.get("order_code"),
        "link": order_data.get("link"),
        "price": int(order_data.get("amount", 0) or 0),
        "remaining_balance": remaining_balance,
        "idempotent_replay": bool(idempotent_replay),
    }

@app.get(
    "/api/v2/status",
    tags=["Partner"],
    summary="Kiểm tra trạng thái hệ thống",
    description="Trả trạng thái online, maintenance mode, số sản phẩm hiển thị, pending orders và số dư của partner.",
)
async def api_v2_status(
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
):
    actor = _api_require_actor(
        x_api_key=x_api_key,
        x_api_token=x_api_token,
        authorization=authorization,
    )
    return {
        "ok": True,
        "data": _api_status_payload(actor),
    }


@app.post("/webhook/sepay", include_in_schema=False)
async def sepay_webhook(request: Request):
    """Nhan giao dich ngan hang do SePay push (my.sepay.vn -> Webhooks).

    Xac thuc bang header `Authorization: Apikey <SEPAY_WEBHOOK_API_KEY>`.
    SePay coi moi response khac 200/201 la that bai va se retry trong vai gio.
    Vi vay: payload rac / sai key / chua bat SePay -> van tra 200 (retry
    khong giup gi); chi loi ha tang that su moi de exception bay len thanh 500
    de SePay thu gui lai. Giao dich hop le chi duoc dua vao hang doi
    (sepay_webhook_inbox), _scan_sepay_payments trong payment_monitor.py se
    khop don va cong tien o vong quet ke tiep.
    """
    from app.integrations.sepay_api import (
        sepay_verify_webhook_key,
        sepay_normalize_webhook_payload,
        sepay_webhook_inbox,
    )

    if not sepay_verify_webhook_key(request.headers.get("Authorization")):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"success": False})

    if not ENABLE_PAYMENT_SEPAY:
        logger.warning("SePay webhook: ENABLE_PAYMENT_SEPAY=false -> bo qua payload")
        return {"success": True}

    try:
        body = await request.json()
    except Exception as e:
        logger.warning(f"SePay webhook: body khong phai JSON hop le: {e}")
        return {"success": True}

    normalized = sepay_normalize_webhook_payload(body)
    if normalized:
        sepay_webhook_inbox.append(normalized)
        logger.info(
            f"SePay webhook: nhan giao dich {normalized['transactionID']} "
            f"so tien {normalized['amount']:,}d"
        )
    return {"success": True}


