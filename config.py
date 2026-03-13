import os
from dotenv import load_dotenv

# Load from .env file if it exists locally
load_dotenv()

# Configuration Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WHATSAPP_APP_TOKEN = os.getenv("WHATSAPP_APP_TOKEN")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
SLATE_CALENDAR_URL = os.getenv("SLATE_CALENDAR_URL")

# Destination phone number for outgoing scheduled automated reminders
TARGET_PHONE_NUMBER = os.getenv("TARGET_PHONE_NUMBER")
