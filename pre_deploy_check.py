import argparse
import datetime
from typing import List, Tuple

import psycopg2
import requests

from bot_config import (
    DATABASE_URL,
    TARGET_CHAT_ID,
    TELEGRAM_BOT_TOKEN,
)
from telegram_service import send_message

REQUEST_TIMEOUT = (10, 30)


def _ok(message: str):
    print(f"[PASS] {message}")


def _warn(message: str):
    print(f"[WARN] {message}")


def _fail(message: str):
    print(f"[FAIL] {message}")


def check_required_env() -> Tuple[bool, List[str]]:
    missing = []
    if not DATABASE_URL:
        missing.append("DATABASE_URL")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TARGET_CHAT_ID:
        missing.append("TARGET_CHAT_ID")

    if missing:
        _fail(f"Missing required environment variables: {', '.join(missing)}")
        return False, missing

    _ok("Required environment variables are present.")
    return True, []


def check_database() -> bool:
    if not DATABASE_URL:
        _fail("DATABASE_URL is missing.")
        return False

    try:
        with psycopg2.connect(DATABASE_URL, connect_timeout=10) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT NOW(), current_database()")
                now_value, db_name = cursor.fetchone()

        _ok(f"Database connection successful (db={db_name}, now={now_value}).")

        if "sslmode=require" not in DATABASE_URL.lower():
            _warn("DATABASE_URL does not explicitly include sslmode=require.")
        else:
            _ok("DATABASE_URL includes sslmode=require.")

        return True
    except Exception as exc:
        _fail(f"Database connectivity check failed: {exc}")
        return False


def check_telegram_config() -> bool:
    if not TELEGRAM_BOT_TOKEN:
        _fail("TELEGRAM_BOT_TOKEN is missing.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            _fail(
                "Telegram credential check failed: "
                f"HTTP {response.status_code} - {response.text}"
            )
            return False

        data = response.json()
        if not data.get("ok"):
            _fail(f"Telegram credential check failed: {data}")
            return False
        bot_user = data.get("result", {})
        bot_id = bot_user.get("id", "unknown")
        bot_username = bot_user.get("username", "unknown")
        _ok(
            "Telegram Bot API access successful "
            f"(bot_id={bot_id}, username=@{bot_username})."
        )
        return True
    except Exception as exc:
        _fail(f"Telegram credential check failed: {exc}")
        return False


def send_telegram_test_message() -> bool:
    if not TARGET_CHAT_ID:
        _fail("Cannot send test message: TARGET_CHAT_ID is missing.")
        return False

    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    text = (
        "Slate Reminder Bot pre-deploy check message. "
        f"Timestamp: {timestamp}"
    )
    sent = send_message(TARGET_CHAT_ID, text)
    if sent:
        _ok("Telegram test message sent successfully.")
    else:
        _fail("Telegram test message failed to send.")
    return sent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pre-deployment integration check for DB and Telegram setup."
    )
    parser.add_argument(
        "--send-test-message",
        action="store_true",
        help="Also send a real Telegram message to TARGET_CHAT_ID.",
    )
    args = parser.parse_args()

    print("== Slate Reminder Bot Pre-Deploy Check ==")
    env_ok, _ = check_required_env()

    db_ok = check_database() if env_ok else False
    tg_ok = check_telegram_config() if env_ok else False

    msg_ok = True
    if args.send_test_message:
        msg_ok = send_telegram_test_message() if env_ok and tg_ok else False

    all_ok = env_ok and db_ok and tg_ok and msg_ok
    print("-----------------------------------------")
    if all_ok:
        _ok("Pre-deploy integration check completed successfully.")
        return 0

    _fail("Pre-deploy integration check failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
