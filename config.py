import os
from dotenv import load_dotenv

# Load from .env file if it exists locally
load_dotenv()

# Configuration Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WHATSAPP_APP_TOKEN = os.getenv("WHATSAPP_APP_TOKEN")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
TARGET_PHONE_NUMBER = os.getenv("TARGET_PHONE_NUMBER")
DATABASE_URL = os.getenv("DATABASE_URL")
SLATE_CALENDAR_URL = os.getenv("SLATE_CALENDAR_URL")

# Cloudflare bypass credentials (cookie & matching browser user-agent)
CF_CLEARANCE = os.getenv("CF_CLEARANCE", "")
CF_USER_AGENT = os.getenv("CF_USER_AGENT", "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36")

# Destination phone number for outgoing scheduled automated reminders
TARGET_PHONE_NUMBER = os.getenv("TARGET_PHONE_NUMBER")
