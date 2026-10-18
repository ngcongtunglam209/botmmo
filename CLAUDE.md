# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Dino Store" / "Lâm Shop" — a Telegram bot selling digital products (MMO services), plus a FastAPI HTTP layer serving an admin web panel and a partner API. Runtime language of the product is Vietnamese; code comments and UI strings are mostly Vietnamese. Users can be served in `vi` / `en` / `zh`.

## Commands

```powershell
python main.py                       # run bot + API server (single process)
pytest                               # full suite (460 tests)
pytest tests/test_business_logic.py -v          # one file
pytest tests/test_i18n.py::test_name -v         # one test
ruff check app/ tests/               # lint (CI gate; line-length 120, E501 ignored)
mypy app/models/ --ignore-missing-imports       # CI only type-checks app/models
python -m compileall -q app tests    # fast syntax check
docker compose up -d --build         # bot + Caddy reverse proxy
```

CI (`.github/workflows/ci.yml`) runs lint → (test, typecheck) on Python 3.12 with `DINO_SUPPRESS_START_BANNER=1`.

`.env` is required and user-managed on the VPS — never write to it. `.env.example` documents every key.

## Architecture

### Two module systems live side by side

This is the single most important thing to know before editing anything under `app/`.

**1. "Section" modules — exec'd, not imported.**
`app/core/section_manifest.py` lists ~58 files in `SECTION_FILES`. `app/core/runtime_loader.py` reads each one, `exec()`s it into a fresh `ModuleType` **sharing one accumulating namespace**, and registers it in `sys.modules`. Consequences:

- These files have *almost no import statements*. `logger`, `Update`, `ContextTypes`, `datetime`, `products`, `app` (the FastAPI instance) etc. arrive from earlier sections via the shared namespace. `app/core/boot_dependencies.py` (first in the list) does the real imports; `config_env.py` and `runtime_state.py` define the globals everything else reads.
- **Order in `SECTION_FILES` is load order and is load-bearing.** A new section file must be inserted after everything it references. Plain `import app.handlers.foo` on a section module gives you a half-built module or `NameError`.
- After each section loads, its public symbols are copied into *every* already-loaded module's `__dict__`. So a global re-binding at runtime does not propagate by itself — use `runtime_loader.sync_runtime_bindings(globals(), ["name", ...])` (see `app/core/lifecycle.py`).
- Ruff sees undefined names here; existing code uses `# noqa: F821` where needed. `pyproject.toml` also ignores `F821`, `F401` and `E402` on every file in `SECTION_FILES`, and `tests/test_lint_config.py` fails if that list and the ignores drift apart.
- **Never run `ruff check --fix` on a section file without `--select`ing the rules yourself.** The `F401` fix deletes "unused" imports, and in `boot_dependencies.py` every import is unused *in that file* — it exists so the other 57 sections can see it. An unrestricted `--fix` emptied that file's import block plus `json` in `config_env.py` and `Decimal` in `games_withdrawals_db.py`, **and the full test suite still passed**. Diff the imported names before and after (`ast.Import` / `ast.ImportFrom`) rather than trusting green tests.

**2. Normal Python packages — regular imports, no loader.**
`app/web/**` (admin panel + partner API), `app/models/**`, `app/state.py`, `app/services/business_logic.py`, `brand_matching.py`, `warranty_history.py`, and `app/core/{runtime_loader,section_manifest}.py`. Write these as ordinary typed modules; they are the direction the codebase is migrating toward.

The only seam between the two is `app/api/web_mount.py`, a section file whose entire job is `from app.web import register; register(app)`.

### Testing against section modules

Tests import normal modules directly. For section modules:

```python
from app.core.runtime_loader import load_modules
modules = load_modules()
payments = modules["app.integrations.payments_core"]
```

Because the loader copies symbols into every module's globals, monkeypatching a shared function must be done **per module** and restored afterwards, or later tests in the session see the patch. `tests/test_rank_and_balance_i18n.py` is the reference pattern.

### State and persistence

- Runtime truth for the bot is a set of in-RAM dicts/lists (`products`, `user_data_db`, `order_history`, `pending_orders`, …) defined in `runtime_state.py`, mirrored into `app/state.py::AppState` (`app_state`) during an in-progress migration.
- Persistence is a SQLite **KV store** (`kv_store` table, one JSON blob per `data_*.json` key) plus real tables for transactions, sessions, partner ledger, API logs — see `app/database/storage.py::init_db`. WAL mode.
- `save_data()` dumps RAM over kv_store. **Therefore a web-side write that only touches SQLite gets erased on the next bot save.** All web writes go through `app/web/bridge.py`: commit SQLite first, then `publish()` to update the matching `app_state` collection *in place* (clear + update, never rebind — legacy modules hold aliases). `KV_TO_STATE` maps kv keys to state fields.
- Docker mounts `./data` and `./logs` as directories, not single files, because WAL writes `-wal`/`-shm` siblings.

### HTTP layer (`app/web`)

Mounted into the same FastAPI app the bot serves (`app/api/server.py` runs uvicorn in the bot's event loop).

- `/admin` — Jinja2 + HTMX panel. Routers in `app/web/routers/`, data access in `app/web/repo/` (SQLite is source of truth, per-request reads), auth/CSRF/same-origin in `app/web/security.py` + `deps.py`.
- `/api/v1`, `/api/v2` — partner API (`app/web/api/`), `x-api-key` header auth. `/docs`, `/reference` are the public partner docs.
- Admin login brute-force protection trusts `X-Forwarded-For`, so **the bot port must not be publicly reachable** — Caddy (`Caddyfile`, `docker-compose.yml`) terminates TLS and is the only exposed listener. Uvicorn runs with `proxy_headers=True` / `forwarded_allow_ips=TRUSTED_PROXY_IPS`.

### Telegram layer

`app/legacy_entry.py::register_handlers` wires every handler and job; `main()` builds the `Application` and polls. `app/main.py::run` wraps it in a 50-attempt crash-restart loop.

- Store, wallet, and all personal commands are restricted to `filters.ChatType.PRIVATE` (a group reply would leak balances/orders and let anyone run another user's command). Only giveaway handling and the Chinese-language guard run in groups.
- Handler groups: `-3` priority callbacks, `-2` group guard, `-1` priority email capture, then the normal handlers.
- A single-instance file lock (`bot.instance.lock`) guards against `Conflict: terminated by other getUpdates`.

### Payments

Three independently toggled rails, all polled/reconciled by `app/jobs/payment_monitor.py`:

- **GPM Pay** (`ENABLE_PAYMENT_GPMPAY`) — VND bank transfer. Webhook at `/webhook/gpmpay` signed HMAC-SHA256 (`X-GPMPay-Signature: t=,v1=`) with `GPMPAY_WEBHOOK_SECRET`; only `source=REAL` incoming transfers count (`test` pings and SIMULATED are ignored); `GPMPAY_API_TOKEN` polling is fallback only. VietQR images are generated locally by `app/utils/vietqr.py` (NAPAS EMVCo payload + CRC16, rendered with `segno`); `BANK_BIN` overrides the BIN looked up from `BANK_ID`. Only the partner API's `build_partner_api_topup_qr_url` still hands out an img.vietqr.io URL, because partners consume a link, not bytes.
- **NOWPayments** (`ENABLE_PAYMENT_NOWPAYMENTS`) — USDT, multi-currency (`NOWPAYMENTS_CURRENCIES`). IPN at `/webhook/nowpayments` signed HMAC-SHA512 with `NOWPAYMENTS_IPN_SECRET`; per-payment polling is fallback only. A "Coin khác" button opens a hosted NOWPayments invoice (`POST /v1/invoice`, sentinel currency `any` through the same `nowpaynet_` / `topup_npnet:` callbacks) so the customer can pay in any coin; it is only offered when `PUBLIC_API_URL` is set, because the invoice's `payment_id` is learned from its first IPN (`nowpayments_remember_payment_id`) and the underpay tolerance applies to stablecoins only.
- **Binance Pay** (`ENABLE_PAYMENT_BINANCE_PAY`) — matched by amount + time leeway against a merchant history feed.

Orders and wallet top-ups share the same payment-generation path (`app/handlers/payment_generation.py`, `app/handlers/user_topup.py`).

## Conventions

- **Premium emoji markup**: user-facing strings embed `<tg-emoji emoji-id="...">🦖</tg-emoji>`. `app/core/emoji_runtime.py` scans project sources to build the glyph→id map and `strip_tg_emoji()` cleans them for console logs. Keep the tag form when adding strings that Telegram renders.
- **i18n**: `app/utils/i18n.py` holds `STRINGS` for `vi`/`en`/`zh`. Anything shown to a customer resolves language via `get_user_lang(user_id)` — do not hardcode Vietnamese in new user-facing paths.
- **Env access**: use `get_env_str/int/float/bool` from `config_env.py`, not `os.getenv`. `.env` loads with `override=True`, so an empty `KEY=` line would otherwise silently beat the default.
- Comments in section modules and Vietnamese-facing code are written in Vietnamese; match the surrounding file.
