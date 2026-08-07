def _api_v1_clean_scalar(value):
    if value is None:
        return ""
    if not isinstance(value, (str, int, float)):
        return ""
    return str(value).strip()


def _api_v1_parse_quantity(raw_quantity):
    normalized_quantity = _api_v1_clean_scalar(raw_quantity)
    if not normalized_quantity:
        return 1
    try:
        quantity = int(normalized_quantity)
    except (ValueError, TypeError, KeyError, IndexError):
        raise HTTPException(status_code=400, detail="quantity must be a positive integer")
    if quantity < 1:
        raise HTTPException(status_code=400, detail="quantity must be a positive integer")
    return quantity


def _api_v1_validate_variant(product_id: str, variant_id: str | None):
    normalized_variant_id = _api_v1_clean_scalar(variant_id)
    if not normalized_variant_id:
        return None

    expected_variant_id = _api_make_synthetic_variant_id(product_id)
    if normalized_variant_id != expected_variant_id:
        raise HTTPException(status_code=400, detail="variantId is invalid for this product")
    return normalized_variant_id


def _api_v1_generate_partner_ref():
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"DMV1_{int(time.time() * 1000)}_{suffix}"


def _api_v1_resolve_partner_ref(order_id: str | None, order_id_alt: str | None, x_idempotency_key: str | None):
    body_ref = _api_v1_clean_scalar(order_id) or _api_v1_clean_scalar(order_id_alt)
    header_ref = _api_v1_clean_scalar(x_idempotency_key)
    if body_ref and header_ref and body_ref != header_ref:
        raise HTTPException(status_code=400, detail="orderId and x-idempotency-key must match")
    return body_ref or header_ref or _api_v1_generate_partner_ref()


def _api_v1_success_response(data, message: str | None = None):
    payload = {
        "success": True,
        "data": data,
    }
    if message is not None:
        payload["message"] = str(message)
    return payload


@app.get("/api/v1/users/profile", tags=["Legacy"], summary="Legacy: kiá»ƒm tra profile partner")
async def api_v1_users_profile(
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
):
    try:
        actor = _api_require_actor(
            x_api_key=x_api_key,
            x_api_token=x_api_token,
            authorization=authorization,
            allow_admin=False,
        )
    except HTTPException as exc:
        return _api_v1_error_response(_api_v1_humanize_error(exc.detail), exc.status_code)

    return _api_v1_success_response(
        {
            "username": str(actor.get("partner_name") or ""),
            "email": _api_get_actor_contact_email(actor),
            "walletBalance": int(_api_get_remaining_balance(actor) or 0),
        }
    )


@app.get("/api/v1/products/info/{product_id}", tags=["Legacy"], summary="Legacy: láº¥y thÃ´ng tin sáº£n pháº©m")
async def api_v1_product_info(
    product_id: str,
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
):
    try:
        actor = _api_require_actor(
            x_api_key=x_api_key,
            x_api_token=x_api_token,
            authorization=authorization,
            allow_admin=False,
        )
        product_data = products.get(product_id)
        if not isinstance(product_data, dict) or not _ctt_is_catalog_visible(product_data):
            raise HTTPException(status_code=404, detail="product_not_found")
    except HTTPException as exc:
        return _api_v1_error_response(_api_v1_humanize_error(exc.detail), exc.status_code)

    return _api_v1_success_response(_api_build_v1_product_payload(product_id, product_data, actor=actor))


@app.get("/api/v1/products/variant/{variant_id}", tags=["Legacy"], summary="Legacy: láº¥y thÃ´ng tin variant")
async def api_v1_variant_info(
    variant_id: str,
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
):
    try:
        actor = _api_require_actor(
            x_api_key=x_api_key,
            x_api_token=x_api_token,
            authorization=authorization,
            allow_admin=False,
        )
        product_id, product_data = _api_get_product_from_synthetic_variant(variant_id)
        if not product_id or not isinstance(product_data, dict) or not _ctt_is_catalog_visible(product_data):
            raise HTTPException(status_code=404, detail="Variant not found")
    except HTTPException as exc:
        return _api_v1_error_response(_api_v1_humanize_error(exc.detail), exc.status_code)

    return _api_v1_success_response(_api_build_v1_variant_payload(product_id, product_data, actor=actor))


@app.get("/api/v1/orders/buy", tags=["Legacy"], summary="Legacy: táº¡o Ä‘Æ¡n báº±ng query string")
async def api_v1_buy_order(
    productId: str | None = None,
    quantity: str | None = None,
    variantId: str | None = None,
    orderId: str | None = None,
    order_id: str | None = None,
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
    x_idempotency_key: str = Header(None),
):
    try:
        actor = _api_require_actor(
            x_api_key=x_api_key,
            x_api_token=x_api_token,
            authorization=authorization,
            allow_admin=False,
        )
        product_id = str(productId or "").strip()
        if not product_id:
            raise HTTPException(status_code=400, detail="productId is required")
        product_data = products.get(product_id)
        if not isinstance(product_data, dict) or not _ctt_is_catalog_visible(product_data):
            raise HTTPException(status_code=404, detail="product_not_found")
        _api_v1_validate_variant(product_id, variantId)
        partner_ref = _api_v1_resolve_partner_ref(orderId, order_id, x_idempotency_key)
        parsed_quantity = _api_v1_parse_quantity(quantity)
        order_data, _remaining_balance, _idempotent_replay = await _api_create_order(
            actor=actor,
            partner_ref=partner_ref,
            product_id=product_id,
            quantity=parsed_quantity,
        )
    except HTTPException as exc:
        return _api_v1_error_response(_api_v1_humanize_error(exc.detail), exc.status_code)

    return _api_v1_success_response(
        [_api_build_v1_order_summary_payload(order_data)],
        message="Order processing complete",
    )


@app.post("/api/v1/orders", tags=["Legacy"], summary="Legacy: táº¡o Ä‘Æ¡n")
async def api_v1_create_order(
    payload: dict | None = Body(default=None),
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
    x_idempotency_key: str = Header(None),
):
    raw_payload = payload if isinstance(payload, dict) else {}
    try:
        actor = _api_require_actor(
            x_api_key=x_api_key,
            x_api_token=x_api_token,
            authorization=authorization,
            allow_admin=False,
        )
        product_id = str(raw_payload.get("productId") or "").strip()
        if not product_id:
            raise HTTPException(status_code=400, detail="productId is required")
        product_data = products.get(product_id)
        if not isinstance(product_data, dict) or not _ctt_is_catalog_visible(product_data):
            raise HTTPException(status_code=404, detail="product_not_found")
        _api_v1_validate_variant(product_id, raw_payload.get("variantId"))
        partner_ref = _api_v1_resolve_partner_ref(
            raw_payload.get("orderId"),
            raw_payload.get("order_id"),
            x_idempotency_key,
        )
        parsed_quantity = _api_v1_parse_quantity(raw_payload.get("quantity"))
        order_data, _remaining_balance, _idempotent_replay = await _api_create_order(
            actor=actor,
            partner_ref=partner_ref,
            product_id=product_id,
            quantity=parsed_quantity,
        )
    except HTTPException as exc:
        return _api_v1_error_response(_api_v1_humanize_error(exc.detail), exc.status_code)

    return _api_v1_success_response(
        [_api_build_v1_order_summary_payload(order_data)],
        message="Order processing complete",
    )


@app.get("/api/v1/orders/{order_id}", tags=["Legacy"], summary="Legacy: xem chi tiáº¿t Ä‘Æ¡n")
async def api_v1_order_detail(
    order_id: str,
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
):
    try:
        actor = _api_require_actor(
            x_api_key=x_api_key,
            x_api_token=x_api_token,
            authorization=authorization,
            allow_admin=False,
        )
        normalized_order_id = str(order_id or "").strip().upper()
        order_data = order_index.get(normalized_order_id)
        if not order_data or not _api_order_belongs_to_actor(order_data, actor):
            raise HTTPException(status_code=404, detail="Order not found")
    except HTTPException as exc:
        return _api_v1_error_response(_api_v1_humanize_error(exc.detail), exc.status_code)

    return _api_v1_success_response(_api_build_v1_order_detail_payload(order_data))


@app.get(
    "/api/v2/catalog",
    tags=["Partner"],
    summary="Láº¥y catalog sáº£n pháº©m",
    description=(
        "Tráº£ danh sÃ¡ch sáº£n pháº©m Ä‘ang bÃ¡n. Vá»›i dá»‹ch vá»¥ social, response cÃ³ "
        "`delivery_mode='social_service'`, `social_input_fields`, giá»›i háº¡n sá»‘ lÆ°á»£ng, "
        "`supplier_service_id` vÃ  thÃ´ng tin pricing Ä‘á»ƒ partner biáº¿t cáº§n gá»­i `target_link`/`comments`."
    ),
)
async def api_v2_catalog(
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
    limit: int | None = None,
    offset: int = 0,
    search: str | None = None,
    available_only: bool = False,
):
    actor = _api_require_actor(
        x_api_key=x_api_key,
        x_api_token=x_api_token,
        authorization=authorization,
    )
    catalog_products, total_products, filtered_products, safe_limit, safe_offset = _api_catalog_payload(
        actor,
        limit=limit,
        offset=offset,
        search=search,
        available_only=available_only,
        social_only=False,
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
                "has_more": bool(safe_limit and (safe_offset + len(catalog_products)) < filtered_products),
            },
            "maintenance_mode": MAINTENANCE_MODE,
            "partner_name": actor.get("partner_name"),
        },
    }


@app.get(
    "/api/v2/me",
    tags=["Partner"],
    summary="Kiá»ƒm tra API key vÃ  sá»‘ dÆ° vÃ­ chung",
    description="DÃ¹ng endpoint nÃ y trÆ°á»›c khi táº¡o Ä‘Æ¡n Ä‘á»ƒ xÃ¡c nháº­n key há»£p lá»‡, sá»‘ dÆ° hiá»‡n táº¡i vÃ  háº¡ng chiáº¿t kháº¥u.",
)
async def api_v2_me(
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
):
    actor = _api_require_actor(
        x_api_key=x_api_key,
        x_api_token=x_api_token,
        authorization=authorization,
    )
    owner_user_id = _api_get_actor_owner_user_id(actor)
    rank_info = get_user_rank(owner_user_id) if owner_user_id else None
    current_balance = _api_get_remaining_balance(actor)
    return {
        "ok": True,
        "data": {
            "version": API_V2_VERSION,
            "partner_name": actor.get("partner_name"),
            "is_admin": bool(actor.get("is_admin")),
            "balance": current_balance,
            "maintenance_mode": MAINTENANCE_MODE,
            "rank_name": (re.sub(r"<[^>]+>", "", str(rank_info.get("rank", {}).get("name", "") or "")).strip() if rank_info else ""),
            "rank_discount_percent": 0,
        },
    }


@app.post(
    "/api/v2/orders",
    tags=["Partner"],
    summary="Táº¡o Ä‘Æ¡n hÃ ng",
    description=(
        "Táº¡o Ä‘Æ¡n báº±ng `partner_ref` duy nháº¥t. NÃªn gá»­i cÃ¹ng giÃ¡ trá»‹ trong header "
        "`x-idempotency-key` Ä‘á»ƒ retry khÃ´ng táº¡o trÃ¹ng. Vá»›i social service, gá»­i `target_link` "
        "vÃ  `comments` theo `social_input_fields` tá»« catalog."
    ),
)
async def api_v2_create_order(
    req: DeveloperOrderRequest,
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
    x_idempotency_key: str = Header(None),
):
    actor = _api_require_actor(
        x_api_key=x_api_key,
        x_api_token=x_api_token,
        authorization=authorization,
    )

    partner_ref = (req.partner_ref or "").strip()
    header_ref = (x_idempotency_key or "").strip()
    if not partner_ref and header_ref:
        partner_ref = header_ref
    if partner_ref and header_ref and partner_ref != header_ref:
        raise HTTPException(status_code=400, detail="partner_ref and x-idempotency-key must match")
    if not partner_ref:
        raise HTTPException(status_code=400, detail="partner_ref is required")

    customer_email = req.customer_email or req.email
    order_data, remaining_balance, idempotent_replay = await _api_create_order(
        actor=actor,
        partner_ref=partner_ref,
        customer_email=customer_email,
        send_email=bool(req.send_email),
        customer_id=req.customer_id,
        note=req.note,
        product_id=req.product_id,
        quantity=req.quantity,
        expected_social=False,
    )

    message = "Existing order returned (idempotent replay)." if idempotent_replay else "Order created successfully."
    return {
        "ok": True,
        "message": message,
        "data": _api_order_payload(order_data, remaining_balance=remaining_balance, idempotent_replay=idempotent_replay),
    }


@app.get(
    "/api/v2/orders",
    tags=["Partner"],
    summary="Láº¥y lá»‹ch sá»­ Ä‘Æ¡n API",
    description=(
        "Tráº£ danh sÃ¡ch Ä‘Æ¡n cá»§a API key hiá»‡n táº¡i, cÃ³ phÃ¢n trang vÃ  filter. Endpoint list chá»‰ tráº£ tráº¡ng thÃ¡i Ä‘Ã£ lÆ°u; "
        "khÃ´ng gá»i nguá»“n social hÃ ng loáº¡t Ä‘á»ƒ trÃ¡nh spam API nguá»“n."
    ),
)
async def api_v2_list_orders(
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
    search: str | None = None,
):
    actor = _api_require_actor(
        x_api_key=x_api_key,
        x_api_token=x_api_token,
        authorization=authorization,
    )
    safe_limit = max(1, min(API_V2_MAX_HISTORY_LIMIT, int(limit or 20)))
    safe_offset = max(0, int(offset or 0))
    orders_page, total_orders = _api_get_orders_for_actor(
        actor,
        limit=safe_limit,
        offset=safe_offset,
        status_filter=status,
        search=search,
        social_only=False,
    )
    now_ts = time.time()
    refreshed_ctt = False
    for order_data in orders_page:
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
        if last_refreshed_at and (now_ts - last_refreshed_at) < 180:
            continue
        try:
            refresh_result = await refresh_ctt_order_status(order_data, persist=False)
        except Exception:
            logger.exception("API v2 list SOCIAL_SOURCE status refresh failed")
            continue
        if refresh_result.get("changed"):
            refreshed_ctt = True
    if refreshed_ctt:
        await save_data(force=True, tables=[HISTORY_FILE])
    remaining_balance = _api_get_remaining_balance(actor)
    has_more = (safe_offset + len(orders_page)) < total_orders

    return {
        "ok": True,
        "data": {
            "orders": [_api_order_payload(order_data) for order_data in orders_page],
            "pagination": {
                "limit": safe_limit,
                "offset": safe_offset,
                "returned": len(orders_page),
                "total": total_orders,
                "has_more": has_more,
            },
            "filters": {
                "status": str(status or ""),
                "search": str(search or ""),
            },
            "partner_name": actor.get("partner_name"),
            "remaining_balance": remaining_balance,
        },
    }


@app.get(
    "/api/v2/orders/{order_code}",
    tags=["Partner"],
    summary="Xem chi tiáº¿t Ä‘Æ¡n theo mÃ£ Ä‘Æ¡n",
    description=(
        "Tráº£ chi tiáº¿t Ä‘Æ¡n. Vá»›i Ä‘Æ¡n social, endpoint nÃ y refresh live tráº¡ng thÃ¡i nguá»“n trÆ°á»›c khi tráº£ response "
        "vÃ  cÃ³ thá»ƒ tra báº±ng cáº£ `order_code` hoáº·c `supplier_order_id`."
    ),
)
async def api_v2_get_order(
    order_code: str,
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
):
    actor = _api_require_actor(
        x_api_key=x_api_key,
        x_api_token=x_api_token,
        authorization=authorization,
    )
    normalized_order_code = str(order_code or "").strip().upper()
    order_data = find_order_by_code_or_supplier_id(normalized_order_code)
    if not order_data or not _api_order_belongs_to_actor(order_data, actor):
        raise HTTPException(status_code=404, detail="Order not found")
    if order_data.get("is_social_source_service"):
        raise HTTPException(status_code=400, detail="Use /api/social/orders/{order_code} for social orders")

    remaining_balance = _api_get_remaining_balance(actor)

    return {
        "ok": True,
        "data": _api_order_payload(order_data, remaining_balance=remaining_balance),
    }


@app.get(
    "/api/v2/orders/by-ref/{partner_ref}",
    tags=["Partner"],
    summary="Xem chi tiáº¿t Ä‘Æ¡n theo partner_ref",
    description=(
        "DÃ¹ng khi há»‡ thá»‘ng partner lÆ°u mÃ£ ná»™i bá»™ cá»§a mÃ¬nh. Vá»›i Ä‘Æ¡n social, endpoint nÃ y refresh live tráº¡ng thÃ¡i nguá»“n "
        "trÆ°á»›c khi tráº£ response."
    ),
)
async def api_v2_get_order_by_ref(
    partner_ref: str,
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
):
    actor = _api_require_actor(
        x_api_key=x_api_key,
        x_api_token=x_api_token,
        authorization=authorization,
    )
    order_data = _api_find_order_by_partner_ref(actor, partner_ref)
    if not order_data:
        raise HTTPException(status_code=404, detail="Order not found")
    if order_data.get("is_social_source_service"):
        raise HTTPException(status_code=400, detail="Use /api/social/orders/by-ref/{partner_ref} for social orders")
    remaining_balance = _api_get_remaining_balance(actor)

    return {
        "ok": True,
        "data": _api_order_payload(order_data, remaining_balance=remaining_balance, idempotent_replay=True),
    }


@app.get(
    "/api/v2/admin/local-stock-integrity",
    tags=["Admin"],
    summary="Admin: kiá»ƒm tra trÃ¹ng kho local",
    description="Chá»‰ admin API key dÃ¹ng Ä‘Æ°á»£c. Endpoint readonly Ä‘á»ƒ xem bÃ¡o cÃ¡o integrity kho local.",
)
async def api_v2_admin_local_stock_integrity(
    x_api_key: str = Header(None),
    x_api_token: str = Header(None),
    authorization: str = Header(None),
    refresh: bool = False,
):
    actor = _api_require_actor(
        x_api_key=x_api_key,
        x_api_token=x_api_token,
        authorization=authorization,
    )
    if not actor.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin API key required")

    report = get_last_local_stock_integrity_report()
    if refresh or not isinstance(report, dict):
        report = await audit_local_stock_integrity(source="api_readonly")

    return {
        "ok": True,
        "data": report or {
            "generated_at": time.time(),
            "products_scanned": 0,
            "products_with_duplicates": 0,
            "duplicate_item_count": 0,
            "products": [],
            "duplicate_items": [],
        },
    }

def _public_ip_probe_urls() -> list[str]:
    raw = os.getenv("PUBLIC_IP_PROBE_URLS", "").strip()
    if raw:
        urls = [u.strip() for u in re.split(r"[,\s;]+", raw) if u.strip()]
        if urls:
            return urls
    return [
        "https://api.ipify.org",
        "https://ipv4.icanhazip.com",
        "https://ifconfig.me/ip",
        "https://checkip.amazonaws.com",
    ]

async def auto_detect_public_api_url(force_refresh: bool = False) -> str:
    """Auto resolve PUBLIC_API_URL tá»« IP public khi chÆ°a cáº¥u hÃ¬nh.
    force_refresh=True sáº½ bá» qua URL hiá»‡n cÃ³ vÃ  thá»­ detect láº¡i tá»« Ä‘áº§u.
    """
    global PUBLIC_API_URL

    if force_refresh:
        PUBLIC_API_URL = ""

    normalized = _normalize_public_api_url(PUBLIC_API_URL)
    if normalized and not force_refresh:
        PUBLIC_API_URL = normalized
        return normalized

    if not AUTO_PUBLIC_IP_DETECT:
        return ""

    client = _get_http_client(timeout=8.0)
    should_close_client = bool(client is not http_client)

    try:
        for probe_url in _public_ip_probe_urls():
            try:
                resp = await client.get(probe_url, follow_redirects=True)
                if resp.status_code != 200:
                    continue

                ip_text = (resp.text or "").strip()
                if not ip_text:
                    continue

                ip_obj = ipaddress.ip_address(ip_text)
                if not ip_obj.is_global:
                    continue

                host = f"[{ip_text}]" if ip_obj.version == 6 else ip_text
                scheme = "https" if PUBLIC_API_SCHEME == "https" else "http"
                PUBLIC_API_URL = f"{scheme}://{host}:{API_SERVER_PORT}"
                logger.info(f"<tg-emoji emoji-id=\"5231489647946768652\">ðŸŒ</tg-emoji> Auto-detected PUBLIC_API_URL: {PUBLIC_API_URL}")
                return PUBLIC_API_URL
            except (httpx.HTTPError, ValueError, KeyError) as probe_err:
                logger.debug(f"Public IP probe failed ({probe_url}): {probe_err}")
                continue
    finally:
        if should_close_client:
            try:
                await client.aclose()
            except (httpx.HTTPError, ValueError, KeyError):
                logger.debug("Suppressed error at L15592")

    logger.warning("<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> KhÃ´ng tá»± láº¥y Ä‘Æ°á»£c IP public. HÃ£y set PUBLIC_API_URL hoáº·c cáº¥u hÃ¬nh domain/IP public cho API.")
    return ""


