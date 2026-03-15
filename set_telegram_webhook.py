import argparse

import requests

from bot_config import TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET

REQUEST_TIMEOUT = (10, 30)


def build_webhook_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if TELEGRAM_WEBHOOK_SECRET:
        return f"{base}/telegram/webhook/{TELEGRAM_WEBHOOK_SECRET}"
    return f"{base}/telegram/webhook"


def main() -> int:
    parser = argparse.ArgumentParser(description="Set Telegram webhook for this bot.")
    parser.add_argument(
        "--base-url",
        required=True,
        help="Public base URL of your deployed app, e.g. https://your-app.onrender.com",
    )
    args = parser.parse_args()

    if not TELEGRAM_BOT_TOKEN:
        print("[FAIL] TELEGRAM_BOT_TOKEN is missing.")
        return 1

    webhook_url = build_webhook_url(args.base_url)
    endpoint = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"

    try:
        response = requests.post(
            endpoint,
            json={"url": webhook_url},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            print(f"[FAIL] setWebhook failed: {payload}")
            return 1

        print(f"[PASS] Telegram webhook configured: {webhook_url}")
        return 0
    except Exception as exc:
        print(f"[FAIL] setWebhook request failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
