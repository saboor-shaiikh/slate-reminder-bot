import requests
import logging
from typing import Optional
from bot_config import WHATSAPP_API_TOKEN, WHATSAPP_PHONE_NUMBER_ID

logger = logging.getLogger(__name__)

def send_message(phone_number: str, text: str):
    """
    Sends a WhatsApp text message containing the reminder or chat text to a target phone number
    via the Meta/WhatsApp Graph Cloud API.
    """
    # ... existing implementation ...
    if not WHATSAPP_API_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("WhatsApp API token or Phone Number ID not configured.")
        return False
        
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    clean_number = phone_number.replace("+", "")
    
    payload = {
        "messaging_product": "whatsapp",
        "to": clean_number,
        "type": "text",
        "text": {
            "body": text
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"Successfully sent WhatsApp message to {clean_number}")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send WhatsApp message: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"WhatsApp API Response: {e.response.text}")
        return False

def get_media_url(media_id: str) -> Optional[str]:
    """Retrieves the direct download URL for a media item from the WhatsApp API."""
    url = f"https://graph.facebook.com/v18.0/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_API_TOKEN}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("url")
    except Exception as e:
        logger.error(f"Failed to retrieve media URL for {media_id}: {e}")
        return None

def download_media_content(media_url: str) -> Optional[bytes]:
    """Downloads the actual file content from the retrieved media URL."""
    headers = {"Authorization": f"Bearer {WHATSAPP_API_TOKEN}"}
    
    try:
        response = requests.get(media_url, headers=headers)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Failed to download media from {media_url}: {e}")
        return None
