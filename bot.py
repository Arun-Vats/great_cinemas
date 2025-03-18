# bot.py
import os
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv
from database import get_videos_collection, get_users_collection
from handlers.admin import register_admin_handlers
from handlers.user import register_user_handlers
from handlers.common import register_common_handlers
from config import API_ID, API_HASH, BOT_TOKEN, DATABASE_CHANNEL_ID, ADMIN_ID, MONGO_URI
import logging
from aiohttp import web

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

# Initialize Telegram bot
client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
videos_collection = get_videos_collection(MONGO_URI)
users_collection = get_users_collection(MONGO_URI)

# Register handlers
register_common_handlers(client, DATABASE_CHANNEL_ID, ADMIN_ID, videos_collection, users_collection)
register_admin_handlers(client, DATABASE_CHANNEL_ID, ADMIN_ID, MONGO_URI, videos_collection, users_collection)
register_user_handlers(client, videos_collection, users_collection)

# Dummy HTTP server for Koyeb health check
async def health_check(request):
    return web.Response(text="OK")

app = web.Application()
app.add_routes([web.get("/", health_check)])

# Start bot and health check server
async def main():
    await client.run_until_disconnected()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(web._run_app(app, port=8000))  # Dummy HTTP server for Koyeb
    loop.run_until_complete(main())
