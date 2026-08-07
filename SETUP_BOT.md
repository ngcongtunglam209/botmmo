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

