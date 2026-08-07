# Huong Dan Setup BotMMO

Tai lieu nay huong dan setup source bot sau khi da lam sach secret, data cu va cac API nguon ngoai. Mac dinh source chi con bot Telegram, API server noi bo va tuy chon thanh toan MBBank.

## 1. Yeu Cau

- Python 3.11 tro len
- Windows PowerShell hoac terminal tuong duong
- Token bot Telegram tu BotFather
- Neu dung thanh toan ngan hang: thong tin MBBank API hop le

Kiem tra Python:

```powershell
python --version
```

## 2. Tao Moi Truong Ao

Tai thu muc project:

```powershell
cd C:\Users\lequo\Downloads\botmmo\botmmo
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Neu muon chay test:

```powershell
pip install -r requirements-dev.txt
```

## 3. Cau Hinh `.env`

Copy file mau:

```powershell
Copy-Item .env.example .env
```

Mo `.env` va dien cac bien can thiet.

### Cau hinh bat buoc

```env
TELEGRAM_TOKEN=TOKEN_BOT_CUA_BAN
ADMIN_USER_ID=123456789
ADMIN_USERNAME=username_admin
BOT_USERNAME=username_bot
API_SECRET_KEY=mot_chuoi_secret_ngau_nhien
```

Lay `TELEGRAM_TOKEN` trong BotFather. `ADMIN_USER_ID` la Telegram numeric ID cua admin.

### Cau hinh web admin

File `.env.admin` dung cho tai khoan/session web admin. Neu chua co, co the de trong cac secret; app se tu tao `ADMIN_WEB_SESSION_SECRET` khi chay.

```env
ADMIN_WEB_USERNAME=
ADMIN_WEB_SESSION_HOURS=8
ADMIN_WEB_PASSWORD_HASH=
ADMIN_WEB_SESSION_SECRET=
TELEGRAM_LOGIN_CLIENT_ID=
TELEGRAM_LOGIN_CLIENT_SECRET=
TELEGRAM_LOGIN_REDIRECT_URI=
```

### Bat/tat MBBank

Mac dinh nen de tat neu chua cau hinh:

```env
ENABLE_PAYMENT_MBBANK=false
```

Khi muon bat:

```env
ENABLE_PAYMENT_MBBANK=true
BANK_API_PASSWORD=...
BANK_API_TOKEN=...
BANK_LOGIN_USERNAME=...
BANK_ID=MB
BANK_ACCOUNT_NUMBER=...
ACCOUNT_NAME=...
```

### Bat SePay (khuyen nghi hon MBBank)

MBBank scrape doi hoi luu mat khau Internet Banking that trong `.env` - rui ro.
SePay dung webhook chinh thuc (SePay tu push giao dich ve server), khong can
mat khau ngan hang. Poll chi la du phong khi webhook bi mat (VPS restart,
mang loi) hoac chua kip cau hinh webhook.

1. Vao `my.sepay.vn` -> lien ket tai khoan ngan hang can nhan tien.
2. Lay 2 gia tri:
   - **API Token** (my.sepay.vn -> API Token): dung cho poll du phong.
   - **Webhook API Key** (my.sepay.vn -> Webhooks -> tao Webhook moi, dat API Key rieng): dung de xac thuc request SePay gui toi bot.
3. Cau hinh webhook tren dashboard SePay, URL tro ve:
   ```
   https://<domain-hoac-subdomain-cua-ban>/webhook/sepay
   ```
   (can HTTPS that su - dung Cloudflare proxy hoac Caddy/nginx + certbot truoc VPS).
4. Dien `.env`:
   ```env
   ENABLE_PAYMENT_SEPAY=true
   SEPAY_WEBHOOK_API_KEY=<API Key webhook o buoc 2>
   SEPAY_API_TOKEN=<API Token o buoc 2>
   SEPAY_ACCOUNT_NUMBER=<so tai khoan da lien ket SePay>
   ```
5. Sau khi xac nhan webhook nhan on dinh, tat MBBank de khong con luu mat khau ngan hang:
   ```env
   ENABLE_PAYMENT_MBBANK=false
   ```

Ma QR chuyen khoan (`create_vietqr_link`) da dung san endpoint anh mien phi cua
SePay tu truoc, khong can doi gi them buoc nay.

### Bat buoc tham gia nhom

Neu khong can ep user vao nhom:

```env
SUPPORT_GROUP_LINK=
REQUIRED_GROUP_ID=0
```

Neu can ep join group:

```env
SUPPORT_GROUP_LINK=https://t.me/ten_nhom
REQUIRED_GROUP_ID=-100xxxxxxxxxx
```

## 4. Khoi Tao Data Sach

Source hien da duoc lam sach data cu. Cac file sau co the de rong, bot se tao lai du lieu khi chay:

```text
database.sqlite
bot.log
bot.instance.lock
```

Neu can reset lai lan nua, dung:

```powershell
Clear-Content database.sqlite
Clear-Content bot.log
Clear-Content bot.instance.lock
```

## 5. Chay Bot

Chay truc tiep:

```powershell
python main.py
```

Neu chay thanh cong, terminal se hien banner khoi dong va bot bat dau polling Telegram.

API server noi bo mac dinh chay port:

```env
API_SERVER_PORT=8080
```

Neu port bi trung, doi trong `.env`.

## 6. Chay Test

```powershell
pytest
```

Neu chi muon kiem tra syntax nhanh:

```powershell
python -m compileall -q app tests
```

## 7. Docker Tuy Chon

Neu muon chay bang Docker:

```powershell
docker compose up --build
```

Dam bao `.env` da duoc dien truoc khi build/chay.

## 7b. Reverse Proxy (Cloudflare + Caddy)

Can thiet de co HTTPS that cho admin panel, webhook SePay, va Telegram OAuth
callback. `docker-compose.yml` da co san service `caddy` dung lam reverse
proxy - port 8080 cua bot khong con public truc tiep ra VPS nua, chi Caddy
(80/443) moi public. Ly do bat buoc: `_admin_web_client_ip()` tin thang
header `X-Forwarded-For` de ghi log/chong brute-force dang nhap admin - neu
con ai cung goi thang duoc port 8080, ho gia mao duoc IP de qua mat khoa
brute-force. Dong port do lai la phan bat buoc cua fix, khong chi la tuy chon.

1. Tren Cloudflare dashboard: `SSL/TLS` -> `Overview` -> chon mode **Full (strict)**.
2. `SSL/TLS` -> `Origin Server` -> `Create Certificate` -> giu mac dinh (RSA, 15 nam) -> Create.
   Cloudflare hien 2 khoi text: **Origin Certificate** va **Private Key**.
3. Tren VPS, trong thu muc project, tao 2 file tu 2 khoi text do:
   ```bash
   nano cloudflare-origin.pem       # dan Origin Certificate vao
   nano cloudflare-origin-key.pem   # dan Private Key vao
   ```
4. DNS: `DNS` -> `Records` -> A record tro `lamtung.dev` ve IP VPS, **Proxy status: Proxied** (may cam mau cam bat).
5. Mo firewall dung 2 port nay, dong han port bot:
   ```bash
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw deny 8080/tcp
   ```
6. Chay lai:
   ```bash
   docker compose up -d --build
   docker compose logs -f caddy
   ```
   Thay `caddy` boot xong khong loi la ok - khong can cho ACME/Let's Encrypt gi ca vi dung thang cert Cloudflare cap.
7. Cap nhat `.env`:
   ```env
   PUBLIC_API_URL=https://lamtung.dev
   AUTO_PUBLIC_IP_DETECT=false
   ```

Neu doi domain khac subdomain, sua dong dau tien trong `Caddyfile` (`lamtung.dev {`) cho khop, va `TELEGRAM_LOGIN_REDIRECT_URI` trong `.env` cho khop domain moi.

## 8. Loi Thuong Gap

### Thieu bien moi truong

Neu terminal bao thieu `TELEGRAM_TOKEN`, `API_SECRET_KEY` hoac bien bank, hay kiem tra `.env`.

Neu chua dung bank, dat:

```env
ENABLE_PAYMENT_MBBANK=false
```

### Conflict getUpdates

Loi nay thuong do co process bot khac dang chay cung token.

Cach xu ly:

```powershell
Get-Process python
```

Tat process cu, roi chay lai:

```powershell
python main.py
```

### Webhook dang bat

Bot co co che tu xoa webhook khi khoi dong. Neu van loi, vao BotFather hoac dung Telegram API de xoa webhook, sau do chay lai bot.

## 9. Luu Y Bao Mat

- Khong commit `.env` va `.env.admin` len Git.
- Doi ngay token/secret neu tung bi lo.
- Khong dung lai token, bank password, API secret cu.
- Neu chia source cho nguoi khac, chi gui source da scrub va `.env.example`, khong gui `.env` that.

