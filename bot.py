import os
import asyncio
from aiohttp import web
from telethon import TelegramClient
from dotenv import load_dotenv
from database import get_videos_collection, get_users_collection
from handlers.admin import register_admin_handlers
from handlers.user import register_user_handlers
from handlers.common import register_common_handlers
from config import API_ID, API_HASH, BOT_TOKEN, DATABASE_CHANNEL_ID, ADMIN_ID, MONGO_URI

load_dotenv()

# Initialize Telegram client
client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
videos_collection = get_videos_collection(MONGO_URI)
users_collection = get_users_collection(MONGO_URI)

# Register handlers
register_common_handlers(client, DATABASE_CHANNEL_ID, ADMIN_ID, videos_collection, users_collection)
register_admin_handlers(client, DATABASE_CHANNEL_ID, ADMIN_ID, MONGO_URI, videos_collection, users_collection)
register_user_handlers(client, videos_collection, users_collection)

# Health check endpoint
async def health_check(request):
    return web.Response(text="OK", status=200)

# Set up HTTP server for health check
async def start_http_server():
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    print("Health check server running on port 8000")

# Main function to run both bot and health check
async def main():
    # Start the HTTP server in the background
    await start_http_server()
    # Run the Telegram client with a retry loop
    while True:
        try:
            await client.run_until_disconnected()
        except Exception as e:
            print(f"Bot disconnected: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)  # Wait before reconnecting

if __name__ == '__main__':
    # Run the combined bot and health check server
    asyncio.run(main())