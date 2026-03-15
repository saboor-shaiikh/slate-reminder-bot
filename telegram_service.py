import logging
from typing import Optional

import requests

from bot_config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)
REQUEST_TIMEOUT = (10, 30)


def _api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"


def _file_url(file_path: str) -> str:
    return f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"


def send_message(chat_id: str, text: str) -> bool:
    """Sends a Telegram text message to the provided chat ID."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not configured.")
        return False

    if not chat_id:
        logger.error("Cannot send Telegram message: chat_id is missing.")
        return False

    payload = {
        "chat_id": str(chat_id),
        "text": text,
    }

    try:
        response = requests.post(
            _api_url("sendMessage"),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            logger.error(f"Telegram sendMessage not ok: {body}")
            return False
        logger.info(f"Successfully sent Telegram message to chat {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def get_file_path(file_id: str) -> Optional[str]:
    """Retrieves Telegram file_path for a file_id using getFile."""
    if not TELEGRAM_BOT_TOKEN or not file_id:
        return None

    try:
        response = requests.get(
            _api_url("getFile"),
            params={"file_id": file_id},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            logger.error(f"Telegram getFile not ok: {body}")
            return None
        return body.get("result", {}).get("file_path")
    except Exception as e:
        logger.error(f"Failed to fetch Telegram file path: {e}")
        return None


def download_file_content(file_path: str) -> Optional[bytes]:
    """Downloads file bytes from Telegram file API using a file_path."""
    if not TELEGRAM_BOT_TOKEN or not file_path:
        return None

    try:
        response = requests.get(_file_url(file_path), timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Failed to download Telegram file content: {e}")
        return None
