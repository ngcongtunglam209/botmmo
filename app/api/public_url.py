"""Do tim Base URL cong khai cho API server.

Cac route v1/v2 da chuyen sang app/web/api/routers. File nay chi con phan
do tim public IP ma server.py dung luc khoi dong.
"""

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
    """Auto resolve PUBLIC_API_URL từ IP public khi chưa cấu hình.
    force_refresh=True sẽ bỏ qua URL hiện có và thử detect lại từ đầu.
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
                logger.info(f"<tg-emoji emoji-id=\"5231489647946768652\">🌐</tg-emoji> Auto-detected PUBLIC_API_URL: {PUBLIC_API_URL}")
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

    logger.warning("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Không tự lấy được IP public. Hãy set PUBLIC_API_URL hoặc cấu hình domain/IP public cho API.")
    return ""
