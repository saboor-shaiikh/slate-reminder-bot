import os
from dotenv import load_dotenv

# Load from .env file if it exists locally
load_dotenv()

# Configuration Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
DATABASE_URL = os.getenv("DATABASE_URL")
