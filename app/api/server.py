async def run_api_server():
    """Chay uvicorn server va dung PUBLIC_API_URL/public IP da cau hinh."""
    global PUBLIC_API_URL

    if not FASTAPI_ENABLED or not uvicorn:
        logger.warning("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> FastAPI/Uvicorn khong kha dung, API server se bi vo hieu hoa.")
        return

    PUBLIC_API_URL = _normalize_public_api_url(PUBLIC_API_URL)
    if not PUBLIC_API_URL:
        fallback_url = await auto_detect_public_api_url(force_refresh=True)
        if fallback_url:
            PUBLIC_API_URL = fallback_url
        else:
            PUBLIC_API_URL = f"http://127.0.0.1:{API_SERVER_PORT}"
            logger.warning(
                f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Chua cau hinh PUBLIC_API_URL, tam dung Base URL local: {PUBLIC_API_URL}"
            )

    logger.info("==========================================================")
    logger.info(f"<tg-emoji emoji-id=\"5231489647946768652\">🌐</tg-emoji> API Base URL hien tai: {PUBLIC_API_URL}")
    logger.info(f"<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> API STATUS: {PUBLIC_API_URL}/api/status")
    logger.info(f"<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> API V2 STATUS: {PUBLIC_API_URL}/api/v2/status")
    logger.info(f"<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> API V2 ORDERS: {PUBLIC_API_URL}/api/v2/orders")
    logger.info("<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> API auth: dung header x-api-key da cau hinh.")
    logger.info("==========================================================")

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=API_SERVER_PORT,
        log_level="warning",
        access_log=False,
        use_colors=False,
        # Caddy terminates TLS and forwards over the Docker network, so the peer
        # address is never 127.0.0.1 (uvicorn's default trust list). Without this
        # every request looks like plain http and the same-origin check rejects
        # the admin forms. The container port is only reachable from Caddy.
        proxy_headers=True,
        forwarded_allow_ips=TRUSTED_PROXY_IPS,
    )
    server = uvicorn.Server(config)
    await server.serve()
    if not server.should_exit:
        raise RuntimeError("Uvicorn server stopped unexpectedly")
