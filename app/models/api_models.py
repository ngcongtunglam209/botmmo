# ==============================================================================
#  API SERVER (FASTAPI)
# ==============================================================================
API_DESCRIPTION = r"""
# Lâm Shop Partner API

API dùng chung **API key** và **ví partner**, nhưng tách hai luồng để catalog nhẹ,
dễ đồng bộ và tránh nhầm field.

## Xác thực

Gửi một trong hai header:

```http
x-api-key: YOUR_API_KEY
```

```http
Authorization: Bearer YOUR_API_KEY
```

## Sản phẩm thường — `/api/v2/*`

1. `GET /api/v2/me` — kiểm tra key và số dư dùng chung.
2. `GET /api/v2/catalog` — lấy account, stock local và manual.
3. `POST /api/v2/orders` — tạo đơn sản phẩm thường.
4. Tra đơn bằng `/api/v2/orders/{order_code}` hoặc
   `/api/v2/orders/by-ref/{partner_ref}`.

## Social Media — `/api/social/*`

1. `GET /api/social/catalog` — chỉ lấy dịch vụ social.
2. Đọc `minimum_order_quantity`, `maximum_order_quantity` và
   `social_input_fields` của dịch vụ.
3. `POST /api/social/orders` — tạo đơn social.
4. Tra trạng thái nguồn bằng `/api/social/orders/{order_code}` hoặc
   `/api/social/orders/by-ref/{partner_ref}`.

```bash
curl -H "x-api-key: YOUR_API_KEY" \
  "https://api.example.com/api/social/catalog?available_only=true&limit=50"
```

```bash
curl -X POST "https://api.example.com/api/social/orders" \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -H "x-idempotency-key: SOCIAL-2026-000001" \
  -d '{
    "partner_ref": "SOCIAL-2026-000001",
    "product_id": "prod_8786",
    "quantity": 100,
    "target_link": "https://www.facebook.com/example"
  }'
```

`partner_ref` phải duy nhất. Khi timeout, retry nguyên request và nguyên mã;
không tạo mã mới. Đơn social có `supplier_status`, `supplier_remains`,
`supplier_charge` và `supplier_status_refreshed_at`.

## Mã lỗi chính

| HTTP | Ý nghĩa |
|---:|---|
| `400` | Thiếu/sai field hoặc dùng nhầm nhóm endpoint |
| `401` | API key sai |
| `402` | Không đủ số dư |
| `404` | Không thấy sản phẩm/đơn |
| `409` | `partner_ref` đang xử lý |
| `422` | JSON sai kiểu dữ liệu |
| `502` | Nguồn cung cấp chưa xác nhận |
| `503` | Hệ thống bảo trì |
"""

try:
    from pydantic import Field
except Exception:
    def Field(default=None, **_kwargs):
        return default

app = FastAPI(
    title="Lâm Shop Partner API",
    description=API_DESCRIPTION,
    version="2.0",
    contact={"name": "Lâm Shop"},
    openapi_tags=[
        {"name": "Partner", "description": "Sản phẩm thường: catalog, tạo đơn và tra cứu đơn."},
        {"name": "Social Media", "description": "Dịch vụ social: catalog riêng, tạo đơn và trạng thái supplier."},
        {"name": "Legacy", "description": "Endpoint cũ để mua link trực tiếp."},
        {"name": "Admin", "description": "Endpoint quản trị, yêu cầu admin API key."},
    ],
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
)
if FASTAPI_ENABLED:
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.middleware("http")
    async def partner_api_security_middleware(request: Request, call_next):
        path = str(request.url.path or "")
        protected = path.startswith("/api/") and not path.startswith("/api/admin/")
        if not protected:
            return await call_next(request)

        started = time.perf_counter()
        direct_ip = str(getattr(request.client, "host", "") or "")
        trust_proxy = os.getenv("API_TRUST_PROXY_HEADERS", "").strip().lower() in {"1", "true", "yes", "on"}
        forwarded = str(request.headers.get("x-forwarded-for") or "").split(",", 1)[0].strip()
        client_ip = forwarded if trust_proxy and forwarded else direct_ip
        token = _api_extract_token(
            x_api_key=request.headers.get("x-api-key"),
            x_api_token=request.headers.get("x-api-token"),
            authorization=request.headers.get("authorization"),
        )
        key_data = _api_normalize_partner_key(token) if token and not hmac.compare_digest(token, API_SECRET_KEY or "") else None
        fingerprint = _api_key_fingerprint(token) if isinstance(key_data, dict) else ""
        partner_name = str((key_data or {}).get("name") or "")

        blocked_status = 0
        blocked_detail = ""
        if isinstance(key_data, dict) and key_data.get("enabled") is not False:
            if not _api_partner_ip_allowed(key_data, client_ip):
                blocked_status, blocked_detail = 403, "Client IP is not allowed for this API key"
            else:
                rate_limit = _api_partner_rate_limit(key_data)
                used = await asyncio.to_thread(db_api_request_count_since, fingerprint, time.time() - 60)
                if used >= rate_limit:
                    blocked_status, blocked_detail = 429, "Rate limit exceeded"

        if blocked_status:
            from fastapi.responses import JSONResponse
            response = JSONResponse({"detail": blocked_detail}, status_code=blocked_status)
            if blocked_status == 429:
                response.headers["Retry-After"] = "60"
        else:
            response = await call_next(request)

        elapsed_ms = (time.perf_counter() - started) * 1000
        await asyncio.to_thread(
            db_record_api_request,
            fingerprint,
            partner_name,
            client_ip,
            request.method,
            path,
            response.status_code,
            elapsed_ms,
        )
        return response


class OrderRequest(BaseModel):
    partner_ref: str = Field(
        ...,
        description="Mã đơn duy nhất bên hệ thống đối tác. Dùng để chống tạo trùng khi retry.",
        examples=["ORDER_20260426_0001"],
    )
    email: str | None = Field(
        None,
        description="Email khách nhận link với endpoint legacy `/api/buy`.",
        examples=["customer@example.com"],
    )


class DeveloperOrderRequest(BaseModel):
    partner_ref: str | None = Field(None, description="Mã đơn duy nhất của partner.", examples=["ORDER_20260426_0001"])
    product_id: str | None = Field(None, description="ID từ `GET /api/v2/catalog`.", examples=["netflix_1"])
    quantity: int = Field(1, description="Số lượng sản phẩm.", examples=[1])
    email: str | None = Field(None, description="Alias cũ của `customer_email`.")
    customer_email: str | None = Field(None, description="Email khách cuối nếu cần.")
    customer_id: str | None = Field(None, description="ID khách cuối phía partner.")
    note: str | None = Field(None, description="Ghi chú nội bộ, tối đa 200 ký tự.")
    send_email: bool = Field(True, description="Gửi email khi luồng sản phẩm hỗ trợ.")


class SocialOrderRequest(BaseModel):
    partner_ref: str | None = Field(None, description="Mã đơn social duy nhất của partner.", examples=["SOCIAL_20260718_0001"])
    product_id: str | None = Field(None, description="ID từ `GET /api/v2/catalog`.", examples=["prod_8786"])
    quantity: int = Field(1, description="Số lượng tương tác theo giới hạn catalog.", examples=[100])
    target_link: str | None = Field(None, description="Link mục tiêu; bắt buộc khi `social_input_fields` có `link`.", examples=["https://www.facebook.com/example"])
    comments: str | None = Field(None, description="Danh sách comment, mỗi dòng một nội dung, khi dịch vụ yêu cầu.")
    customer_id: str | None = Field(None, description="ID khách cuối phía partner.")
    note: str | None = Field(None, description="Ghi chú nội bộ, tối đa 200 ký tự.")


API_V2_VERSION = "2.0"
API_V2_MAX_PARTNER_REF_LEN = 64
API_V2_MAX_CUSTOMER_ID_LEN = 64
API_V2_MAX_NOTE_LEN = 200
API_V2_MAX_PRODUCT_ID_LEN = 64
API_V2_MAX_QUANTITY = 200
API_V2_MAX_HISTORY_LIMIT = 100


def _api_key_fingerprint(api_key: str) -> str:
    raw = str(api_key or "").encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:16]
