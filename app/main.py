from __future__ import annotations

import time

import httpx
from telegram.error import NetworkError, TelegramError, TimedOut

from .core.runtime_loader import load_modules


def run() -> None:
    modules = load_modules()
    entry_module = modules["app.legacy_entry"]
    state_module = modules["app.core.runtime_state"]

    main_func = entry_module.main
    logger = state_module.logger

    max_retries = 50
    retry_delay = 10

    for attempt in range(1, max_retries + 1):
        try:
            main_func()
            logger.info("Bot đã dừng bình thường.")
            break
        except KeyboardInterrupt:
            logger.info("Bot dừng bởi user (Ctrl+C).")
            break
        except SystemExit:
            break
        except (
            TimedOut,
            NetworkError,
            TelegramError,
            httpx.HTTPError,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
        ) as exc:
            logger.critical(
                f"❌ Bot crash lần {attempt}/{max_retries}: {type(exc).__name__}: {exc}"
            )
            if attempt < max_retries:
                logger.info(f"<tg-emoji emoji-id=\"5462956611033117422\">🔄</tg-emoji> Tự động restart sau {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.critical("❌ Quá nhiều lần crash liên tiếp. Bot dừng hẳn.")


if __name__ == "__main__":
    run()
