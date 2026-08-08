# Tài liệu tích hợp API USDT

Base URL: https://api.rpay.vn/api

## API tạo hóa đơn thanh toán

POST / GET https://api.rpay.vn/api/AddInvoice

### Request Parameters
- merchant_id: Bắt buộc. ID cửa hàng. Chỉ dùng ở server, không nhúng trong frontend public.
- api_key: Bắt buộc. API KEY của cửa hàng. Chỉ dùng ở server, không để lộ ra trình duyệt.
- name: Bắt buộc. Tên hóa đơn.
- description: Tùy chọn. Mô tả hóa đơn.
- amount: Bắt buộc. Số lượng USDT cần thu.
- token: Tùy chọn. Token cần thu, mặc định USDT. Hỗ trợ USDT hoặc USDC theo ví đã cấu hình.
- network: Tùy chọn. Mã mạng nhận tiền, ví dụ bsc, tron, polygon, base. Nên truyền khi cửa hàng có ví ở nhiều network.
- address: Tùy chọn. Địa chỉ ví nhận cụ thể. Cần truyền nếu trong cùng network/token có nhiều ví active.
- expireMinutes: Tùy chọn. Số phút hóa đơn được thanh toán, từ 1 đến 1440. Có thể dùng alias expire_minutes, ttlMinutes hoặc timeoutMinutes.
- request_id: Bắt buộc. ID giao dịch bí mật của hệ thống bạn, dùng để xác minh khi callback.
- callback_url: Bắt buộc. URL nhận kết quả giao dịch.
- success_url: Tùy chọn. URL chuyển hướng sau khi thanh toán thành công.
- cancel_url: Tùy chọn. URL chuyển hướng sau khi thanh toán không thành công hoặc hết hạn.

### Response (Success)
```json
{
  "data": {
    "trans_id": "TX26045710525431",
    "amount": "12.001",
    "status": "waiting",
    "url_payment": "https://api.rpay.vn/invoice/usdt/TX26045710525431",
    "address": "0x83846bb147B4a07B81C99298E76e43416A18DC45",
    "network": "bsc",
    "network_name": "BNB Smart Chain (BEP20)",
    "token": "USDT",
    "token_address": "0x55d398326f99059ff775485246999027b3197955",
    "expires_at": "2026-05-28 12:30:00",
    "expire_minutes": 30,
    "qr_content": "0x83846bb147B4a07B81C99298E76e43416A18DC45",
    "qrcode": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
  },
  "status": "success",
  "msg": "Invoice creation successful!"
}
```

Lưu ý: `qrcode` là ảnh PNG dạng data URL, `qr_content` là nội dung gốc để merchant tự tạo QR nếu cần.

### cURL
```bash
curl -X POST https://api.rpay.vn/api/AddInvoice \
  -d "merchant_id=YOUR_MERCHANT_ID" \
  -d "api_key=YOUR_API_KEY" \
  -d "name=Invoice Name" \
  -d "description=Invoice Description" \
  -d "amount=12" \
  -d "token=USDT" \
  -d "network=bsc" \
  -d "address=0x83846bb147B4a07B81C99298E76e43416A18DC45" \
  -d "expireMinutes=30" \
  -d "request_id=unique_transaction_id" \
  -d "callback_url=https://yourwebsite.com/callback" \
  -d "success_url=https://yourwebsite.com/success" \
  -d "cancel_url=https://yourwebsite.com/cancel"
```

## Callback xác minh giao dịch

Callback sẽ được gửi về callback_url khi tạo hóa đơn.

- request_id: Luôn có. Mã giao dịch bí mật của hệ thống bạn.
- trans_id: Luôn có. Mã giao dịch của hóa đơn.
- merchant_id: Luôn có. ID cửa hàng tạo hóa đơn.
- api_key: Luôn có. API KEY của cửa hàng. Chỉ dùng để xác minh ở server.
- amount: Luôn có. Số lượng USDT yêu cầu thanh toán.
- received: Luôn có. Số lượng USDT thực nhận được.
- status: Luôn có. waiting, expired hoặc completed.
- from_address: Completed. Địa chỉ USDT gửi tiền, chỉ có khi completed.
- transaction_id: Completed. Mã giao dịch blockchain, chỉ có khi completed.

## API lấy trạng thái giao dịch

POST / GET https://api.rpay.vn/api/GetInvoiceStatus

- merchant_id: Bắt buộc. ID cửa hàng. Chỉ dùng ở server, không để lộ ra ngoài.
- api_key: Bắt buộc. API KEY của cửa hàng. Chỉ dùng ở server, không để lộ ra ngoài.
- trans_id: Bắt buộc. Mã giao dịch của hóa đơn, được trả về khi tạo hóa đơn.

### Response
```json
{
  "data": {
    "trans_id": "TX2604571052543841",
    "request_id": "unique_transaction_id",
    "amount": "12.001",
    "received": "12.001",
    "status": "waiting",
    "address": "0x83846bb147B4a07B81C99298E76e43416A18DC45",
    "network": "bsc",
    "network_name": "BNB Smart Chain (BEP20)",
    "token": "USDT",
    "token_address": "0x55d398326f99059ff775485246999027b3197955",
    "expires_at": "2026-05-28 12:30:00",
    "expire_minutes": 30,
    "qr_content": "0x83846bb147B4a07B81C99298E76e43416A18DC45",
    "qrcode": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "from_address": null,
    "transaction_id": null,
    "create_gettime": "2026-05-28 12:00:00",
    "update_gettime": "2026-05-28 12:00:00"
  },
  "status": "success",
  "msg": "Get invoice status successful!"
}
```

## API lấy lịch sử hóa đơn

POST / GET https://api.rpay.vn/api/GetInvoiceHistory

- merchant_id: Bắt buộc. ID cửa hàng. Chỉ dùng ở server.
- api_key: Bắt buộc. API KEY của cửa hàng. Chỉ dùng ở server.
- status: Tùy chọn. waiting, completed, expired, canceled hoặc all.
- network: Tùy chọn. Lọc theo mã mạng, ví dụ bsc, tron, polygon, base.
- token: Tùy chọn. Lọc theo USDT hoặc USDC.
- address: Tùy chọn. Lọc theo địa chỉ ví nhận.
- from_date: Tùy chọn. Ngày bắt đầu: YYYY-MM-DD, DD/MM/YYYY hoặc RFC3339.
- to_date: Tùy chọn. Ngày kết thúc: YYYY-MM-DD, DD/MM/YYYY hoặc RFC3339.
- page: Tùy chọn. Trang hiện tại, mặc định 1.
- limit: Tùy chọn. Số dòng mỗi trang, mặc định 20, tối đa 100.
- include_qrcode: Tùy chọn. true để trả thêm qrcode base64 cho từng hóa đơn. Mặc định false để response nhẹ hơn.

### Response
```json
{
  "data": {
    "items": [
      {
        "trans_id": "TX2604571052543841",
        "request_id": "unique_transaction_id",
        "amount": "12.001",
        "received": "12.001",
        "status": "completed",
        "url_payment": "https://rpay.vn/invoice/usdt/TX2604571052543841",
        "address": "0x83846bb147B4a07B81C99298E76e43416A18DC45",
        "network": "bsc",
        "network_name": "BNB Smart Chain (BEP20)",
        "token": "USDT",
        "token_address": "0x55d398326f99059ff775485246999027b3197955",
        "qr_content": "0x83846bb147B4a07B81C99298E76e43416A18DC45",
        "from_address": "0x1234...abcd",
        "transaction_id": "0xabcd...1234",
        "expires_at": "2026-05-28 12:30:00",
        "expire_minutes": 30,
        "create_gettime": "2026-05-28 12:00:00",
        "update_gettime": "2026-05-28 12:10:00"
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 20,
    "pages": 1
  },
  "status": "success",
  "msg": "Get invoice history successful!"
}
```

## API lấy danh sách network

POST / GET https://api.rpay.vn/api/GetNetworks

### Response
```json
{
  "data": {
    "items": [
      {
        "key": "bsc",
        "name": "BNB Smart Chain (BEP20)",
        "status": "active",
        "fee": "0.2%",
        "tokens": [
          {
            "symbol": "USDT",
            "name": "Binance-Peg BSC-USD",
            "decimal": 18
          }
        ]
      }
    ],
    "total": 16
  },
  "status": "success",
  "msg": "Get networks successful!"
}
```