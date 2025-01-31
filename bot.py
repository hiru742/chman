import os
import logging
from pymongo import MongoClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient, events
from aiohttp import web

# Configuration
BOT_TOKEN = "8033242534:AAFN1AniUtwL7cz56B05XKxYgeZVTiyNRZY"
MONGODB_URI = "mongodb+srv://sahanran:Akuressa123@channel.71p4z.mongodb.net/?retryWrites=true&w=majority&appName=channel"
FORCE_SUB_GROUP_LINK = "https://t.me/Iraselfpromoting18"
ADMIN_USER_ID = "1053942430"
API_ID = "22903347"
API_HASH = "d4164bdce355a4f5864e1e9be667df08"
CHANNEL_USERNAME = "@Nadanansitiyehusmaobamage"

# MongoDB setup
client = MongoClient(MONGODB_URI)
db = client.telegram_bot
users_collection = db.users
messages_collection = db.messages

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Telethon client
telethon_client = TelegramClient('session_name', API_ID, API_HASH)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot started!")

async def handle_new_channel_message(event):
    # Forward new channel messages to bot users
    users = users_collection.find()
    for user in users:
        try:
            await telethon_client.forward_messages(user['user_id'], event.message)
        except Exception as e:
            logger.error(f"Failed to forward message to user {user['user_id']}: {e}")

async def health_check(request):
    return web.Response(text="OK")

def main():
    # Start the Telethon client
    telethon_client.start()
    telethon_client.run_until_disconnected()

    # Set up the bot
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))

    # Register the event handler for new channel messages
    telethon_client.on(events.NewMessage(chats=CHANNEL_USERNAME))(handle_new_channel_message)

    # Start the HTTP server for health checks
    app = web.Application()
    app.router.add_get('/health', health_check)
    web.run_app(app, port=8000)

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
