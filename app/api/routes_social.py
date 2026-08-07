@app.get(
    "/api/social/catalog",
    tags=["Social Media"],
    summary="Lấy catalog dịch vụ social",
    description="Chỉ trả dịch vụ social. Đọc giới hạn số lượng và `social_input_fields` trước khi tạo đơn.",
)
async def api_social_catalog(
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
    limit: int | None = None,
    offset: int = 0,
    search: str | None = None,
    available_only: bool = False,
):
    actor = _api_require_actor(x_api_key=x_api_key, x_api_token=x_api_token, authorization=authorization)
    catalog_products, total_products, filtered_products, safe_limit, safe_offset = _api_catalog_payload(
        actor,
        limit=limit,
        offset=offset,
        search=search,
        available_only=available_only,
        social_only=True,
    )
    return {
        "ok": True,
        "data": {
            "version": API_V2_VERSION,
            "products": catalog_products,
            "total_products": total_products,
            "filtered_products": filtered_products,
            "returned_products": len(catalog_products),
            "pagination": {
                "limit": safe_limit,
                "offset": safe_offset,
                "returned": len(catalog_products),
                "total": filtered_products,
                "has_more": bool(safe_limit and safe_offset + len(catalog_products) < filtered_products),
            },
            "partner_name": actor.get("partner_name"),
        },
    }


@app.post(
    "/api/social/orders",
    tags=["Social Media"],
    summary="Tạo đơn social",
    description="Tạo đơn social bằng `partner_ref` duy nhất. Retry phải giữ nguyên `x-idempotency-key`.",
)
async def api_social_create_order(
    req: SocialOrderRequest,
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
    x_idempotency_key: str = Header(None),
):
    actor = _api_require_actor(x_api_key=x_api_key, x_api_token=x_api_token, authorization=authorization)
    partner_ref = str(req.partner_ref or x_idempotency_key or "").strip()
    header_ref = str(x_idempotency_key or "").strip()
    if partner_ref and header_ref and partner_ref != header_ref:
        raise HTTPException(status_code=400, detail="partner_ref and x-idempotency-key must match")
    if not partner_ref:
        raise HTTPException(status_code=400, detail="partner_ref is required")

    order_data, remaining_balance, idempotent_replay = await _api_create_order(
        actor=actor,
        partner_ref=partner_ref,
        customer_id=req.customer_id,
        note=req.note,
        product_id=req.product_id,
        quantity=req.quantity,
        target_link=req.target_link,
        comments=req.comments,
        send_email=False,
        expected_social=True,
    )
    return {
        "ok": True,
        "message": "Existing order returned (idempotent replay)." if idempotent_replay else "Social order created successfully.",
        "data": _api_order_payload(order_data, remaining_balance=remaining_balance, idempotent_replay=idempotent_replay),
    }


@app.get(
    "/api/social/orders",
    tags=["Social Media"],
    summary="Lấy lịch sử đơn social",
    description="Chỉ trả đơn social của API key hiện tại. Không refresh hàng loạt trạng thái nguồn.",
)
async def api_social_list_orders(
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
    search: str | None = None,
):
    actor = _api_require_actor(x_api_key=x_api_key, x_api_token=x_api_token, authorization=authorization)
    safe_limit = max(1, min(API_V2_MAX_HISTORY_LIMIT, int(limit or 20)))
    safe_offset = max(0, int(offset or 0))
    orders_page, total_orders = _api_get_orders_for_actor(
        actor,
        limit=safe_limit,
        offset=safe_offset,
        status_filter=status,
        search=search,
        social_only=True,
    )
    return {
        "ok": True,
        "data": {
            "orders": [_api_order_payload(order_data) for order_data in orders_page],
            "pagination": {
                "limit": safe_limit,
                "offset": safe_offset,
                "returned": len(orders_page),
                "total": total_orders,
                "has_more": safe_offset + len(orders_page) < total_orders,
            },
            "remaining_balance": _api_get_remaining_balance(actor),
            "partner_name": actor.get("partner_name"),
        },
    }


@app.get(
    "/api/social/orders/by-ref/{partner_ref}",
    tags=["Social Media"],
    summary="Tra đơn social theo partner_ref",
)
async def api_social_get_order_by_ref(
    partner_ref: str,
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
):
    actor = _api_require_actor(x_api_key=x_api_key, x_api_token=x_api_token, authorization=authorization)
    order_data = _api_find_order_by_partner_ref(actor, partner_ref)
    if not order_data or not order_data.get("is_social_source_service"):
        raise HTTPException(status_code=404, detail="Social order not found")
    await refresh_ctt_order_status(order_data)
    return {"ok": True, "data": _api_order_payload(order_data, remaining_balance=_api_get_remaining_balance(actor), idempotent_replay=True)}


@app.get(
    "/api/social/orders/{order_code}",
    tags=["Social Media"],
    summary="Tra và refresh trạng thái đơn social",
)
async def api_social_get_order(
    order_code: str,
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
):
    actor = _api_require_actor(x_api_key=x_api_key, x_api_token=x_api_token, authorization=authorization)
    order_data = find_order_by_code_or_supplier_id(str(order_code or "").strip().upper())
    if not order_data or not _api_order_belongs_to_actor(order_data, actor) or not order_data.get("is_social_source_service"):
        raise HTTPException(status_code=404, detail="Social order not found")
    await refresh_ctt_order_status(order_data)
    return {"ok": True, "data": _api_order_payload(order_data, remaining_balance=_api_get_remaining_balance(actor))}

