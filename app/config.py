import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
META_VERIFY_TOKEN = os.environ["META_VERIFY_TOKEN"]
META_ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]
META_PHONE_NUMBER_ID = os.environ["META_PHONE_NUMBER_ID"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
MAX_RESPONSE_MINUTES = int(os.getenv("MAX_RESPONSE_MINUTES", "30"))

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chats")
