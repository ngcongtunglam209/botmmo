# -- coding: utf-8 --

# ==============================================================================
#  KIỂM TRA VÀ TỰ ĐỘNG CÀI ĐẶT THƯ VIỆN (MODULES) NẾU THIẾU
# ==============================================================================
import sys
import subprocess
import importlib.util
import os

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ALL_PACKAGES = [
    "python-telegram-bot[job-queue]",
    "httpx",
    "google-genai",
    "fastapi",
    "uvicorn",
    "tenacity",
    "aiosqlite",
    "pydantic",
    "python-dotenv",
]

REQUIRED_MODULES = {
    "telegram.ext":    "python-telegram-bot[job-queue]",
    "apscheduler":     "python-telegram-bot[job-queue]",
    "httpx":           "httpx",
    "google.genai":    "google-genai",
    "fastapi":         "fastapi",
    "uvicorn":         "uvicorn",
    "tenacity":        "tenacity",
    "aiosqlite":       "aiosqlite",
    "pydantic":        "pydantic",
    "dotenv":          "python-dotenv",
}

def check_and_install_dependencies():
    missing = {}
    for module_name, pip_name in REQUIRED_MODULES.items():
        top_module = module_name.split(".")[0]
        if importlib.util.find_spec(top_module) is None:
            missing[pip_name] = module_name

    if not missing:
        return

    unique_packages = list(dict.fromkeys(missing.keys()))
    print("\n" + "=" * 60)
    print("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>  THIẾU THƯ VIỆN CẦN THIẾT ĐỂ CHẠY BOT")
    print("=" * 60)
    print("\nCác thư viện cần cài đặt:")
    for i, pkg in enumerate(unique_packages, 1):
        print(f"  {i}. {pkg}")
    print()

    auto_mode = os.getenv("AUTO_INSTALL", "").strip().lower() in ("1", "true", "yes", "on")
    if auto_mode:
        answer = "y"
    else:
        if not bool(getattr(sys.stdin, "isatty", lambda: False)()):
            print("AUTO_INSTALL chua bat. Hay cai requirements.txt hoac chay voi AUTO_INSTALL=1 neu muon tu cai.")
            sys.exit(1)
        try:
            answer = input("<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Bạn có muốn cài đặt tất cả không? (y/n): ").strip().lower()
        except EOFError:
            print("Khong the hoi xac nhan cai dependency. Huy auto-install.")
            sys.exit(1)

    if answer not in ("y", "yes", ""):
        print("❌ Đã hủy. Bot không thể chạy nếu thiếu thư viện.")
        sys.exit(1)

    print("\n<tg-emoji emoji-id=\"5215392879320505675\">🔧</tg-emoji> Đang cài đặt tất cả thư viện...\n")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade"] + ALL_PACKAGES,
            stdout=sys.stdout, stderr=sys.stderr
        )
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Lỗi khi cài đặt: {e}")
        print("Thử cài từng thư viện...")
        for pkg in ALL_PACKAGES:
            try:
                print(f"  [*] Cài {pkg}...")
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pkg],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                print(f"  <tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> {pkg}")
            except subprocess.CalledProcessError:
                print(f"  ❌ Không cài được {pkg} (bỏ qua)")

    print("\n<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Hoàn tất! Đang khởi động lại bot...\n")
    os.execv(sys.executable, [sys.executable] + sys.argv)

try:
    check_and_install_dependencies()
except (ValueError, TypeError, KeyError, IndexError) as e:
    print(f"Không thể chạy trình auto-install: {e}")

# ==============================================================================
#  THƯ VIỆN CẦN THIẾT
# ==============================================================================
import logging
import logging.handlers
import time
import random
import string
import zipfile # NEW: For backup
import io # NEW: For backup
import json
import csv
import asyncio
import smtplib
import warnings
import traceback
import atexit
import html
import hashlib
import hmac
import secrets
import ipaddress
from decimal import Decimal, ROUND_DOWN, ROUND_UP, InvalidOperation
from collections import Counter
from contextlib import closing
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from urllib.parse import quote
from datetime import datetime, timedelta, time as dt_time
from zoneinfo import ZoneInfo
import re
import difflib
from enum import Enum, auto
import functools
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx
import sqlite3
import aiosqlite

warnings.filterwarnings(
    "ignore",
    message=r"'_UnionGenericAlias' is deprecated.*",
    category=DeprecationWarning,
    module=r"google\.genai\.types",
)

try:
    from google import genai
    from google.genai import types
    AI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    AI_AVAILABLE = False

# FIX Phase 3: Sửa exception types cho FastAPI import — httpx.HTTPError không đúng ở đây
FASTAPI_ENABLED = True
FASTAPI_IMPORT_ERROR = None
try:
    import uvicorn
    from fastapi import FastAPI, Header, HTTPException, Body, Request, UploadFile, File, Form
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.responses import HTMLResponse, Response
    from pydantic import BaseModel
except ImportError as e:
    FASTAPI_ENABLED = False
    FASTAPI_IMPORT_ERROR = f"{type(e).__name__}: {e}"
    uvicorn = None

    class HTTPException(Exception):
        def __init__(self, status_code=500, detail="Internal Server Error"):
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)

    class BaseModel:
        pass

    def Header(default=None):
        return default

    def Body(default=None):
        return default

    class Request:
        headers = {}
        query_params = {}

    class HTMLResponse(str):
        pass

    class Response(str):
        pass

    class GZipMiddleware:
        pass

    class FastAPI:
        """Fallback no-op FastAPI object so bot can run without API stack."""
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

        def post(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

# Import thư viện Telegram và các thành phần runtime chính
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ApplicationHandlerStop
)
from telegram.request import HTTPXRequest
from telegram.error import TelegramError, Forbidden, BadRequest, Conflict, NetworkError, RetryAfter, TimedOut
from telegram.constants import ParseMode, ChatAction
from telegram.warnings import PTBUserWarning

# Silence known benign PTB warning for ConversationHandler callback tracking
warnings.filterwarnings(
    "ignore",
    message=r"If 'per_message=False', 'CallbackQueryHandler' will not be tracked for every message\..*",
    category=PTBUserWarning,
)

# ==============================================================================
#  EMOJI CONSTANTS (Custom Telegram Emoji)
# ==============================================================================
E_LOADING  = '<tg-emoji emoji-id="5350752364246606166">✍️</tg-emoji>'
E_LIMIT    = '<tg-emoji emoji-id="5424857974784925603">🚫</tg-emoji>'
E_SUCCESS  = '<tg-emoji emoji-id="6269163801178804220">✅</tg-emoji>'
E_ERROR    = '<tg-emoji emoji-id="5318840353510408444">🔴</tg-emoji>'
E_TIP      = '<tg-emoji emoji-id="5460753627817723162">💡</tg-emoji>'
E_MENU     = '<tg-emoji emoji-id="6124902618574625426">👑</tg-emoji>'
E_USER     = '<tg-emoji emoji-id="5350778980158956492">👤</tg-emoji>'
E_ID       = '<tg-emoji emoji-id="5334890573281114250">🆔</tg-emoji>'
E_TAG      = '<tg-emoji emoji-id="6260059243605398502">🏷️</tg-emoji>'
E_STAT     = '<tg-emoji emoji-id="6059654836918423763">📊</tg-emoji>'
E_GLOBE    = '<tg-emoji emoji-id="5231489647946768652">🌐</tg-emoji>'
E_SOS      = '<tg-emoji emoji-id="6301027265899661025">🆘</tg-emoji>'
E_SHIELD   = '<tg-emoji emoji-id="5197288647275071607">🛡️</tg-emoji>'
E_CALENDAR = '<tg-emoji emoji-id="5413879192267805083">📅</tg-emoji>'
E_STAR     = '⭐️'
E_LOCK     = '🔐'
E_IOS      = '<tg-emoji emoji-id="5350556204500263431">🍏</tg-emoji>'
E_ANDROID  = '<tg-emoji emoji-id="5303145396254563405">🤖</tg-emoji>'
E_CRY      = '<tg-emoji emoji-id="6178962311072456422">😭</tg-emoji>'
E_GRIN     = '<tg-emoji emoji-id="6179337489350663129">😁</tg-emoji>'
E_SANTA    = '<tg-emoji emoji-id="6174520215376763867">🤶</tg-emoji>'
