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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

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

client = TelegramClient("session_name", API_ID, API_HASH)

videos_collection = get_videos_collection(MONGO_URI)
users_collection = get_users_collection(MONGO_URI)

register_common_handlers(client, DATABASE_CHANNEL_ID, ADMIN_ID, videos_collection, users_collection)
register_admin_handlers(client, DATABASE_CHANNEL_ID, ADMIN_ID, MONGO_URI, videos_collection, users_collection)
register_user_handlers(client, videos_collection, users_collection)

async def health_check(request):
    return web.Response(text="OK")

app = web.Application()
app.add_routes([web.get("/", health_check)])

async def start_bot():
    await client.start(bot_token=BOT_TOKEN)
    await client.run_until_disconnected()

async def start_web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()

async def main():
    await asyncio.gather(start_bot(), start_web_server())

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
