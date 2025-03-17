# bot.py
import os
from telethon import TelegramClient
from dotenv import load_dotenv
from database import get_videos_collection, get_users_collection
from handlers.admin import register_admin_handlers
from handlers.user import register_user_handlers
from handlers.common import register_common_handlers
from config import API_ID, API_HASH, BOT_TOKEN, DATABASE_CHANNEL_ID, ADMIN_ID, MONGO_URI
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env if present (optional for local dev), Koyeb will use env vars directly
load_dotenv()

# Verify critical environment variables
required_vars = {
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "BOT_TOKEN": BOT_TOKEN,
    "DATABASE_CHANNEL_ID": DATABASE_CHANNEL_ID,
    "ADMIN_ID": ADMIN_ID,
    "MONGO_URI": MONGO_URI
}
for var_name, var_value in required_vars.items():
    if not var_value:
        logger.error(f"Required environment variable '{var_name}' is not set. Exiting.")
        raise ValueError(f"Required environment variable '{var_name}' is not set.")

client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
videos_collection = get_videos_collection(MONGO_URI)
users_collection = get_users_collection(MONGO_URI)

register_common_handlers(client, DATABASE_CHANNEL_ID, ADMIN_ID, videos_collection, users_collection)
register_admin_handlers(client, DATABASE_CHANNEL_ID, ADMIN_ID, MONGO_URI, videos_collection, users_collection)
register_user_handlers(client, videos_collection, users_collection)

if __name__ == '__main__':
    logger.info("Starting the bot...")
    try:
        client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        raise
