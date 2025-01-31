import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pymongo import MongoClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient, events

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGODB_URI = os.getenv('MONGODB_URI')
FORCE_SUB_GROUP_LINK = os.getenv('FORCE_SUB_GROUP_LINK')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID'))
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')

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

# Dummy HTTP server for health checks
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

def run_http_server():
    server_address = ('', 8000)  # Listen on all interfaces, port 8000
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logger.info("Starting dummy HTTP server on port 8000...")
    httpd.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received /start command from user {update.message.from_user.id}")
    await update.message.reply_text("Bot started!")

async def handle_new_channel_message(event):
    logger.info(f"New message in channel: {event.message.text}")
    # Forward new channel messages to bot users
    users = users_collection.find()
    for user in users:
        try:
            await telethon_client.forward_messages(user['user_id'], event.message)
            logger.info(f"Forwarded message to user {user['user_id']}")
        except Exception as e:
            logger.error(f"Failed to forward message to user {user['user_id']}: {e}")

def main():
    # Start the HTTP server in a separate thread
    http_thread = threading.Thread(target=run_http_server)
    http_thread.daemon = True  # Daemonize thread to exit when the main program exits
    http_thread.start()

    # Start the Telethon client
    logger.info("Starting Telethon client...")
    telethon_client.start()
    logger.info("Telethon client started.")
    telethon_client.run_until_disconnected()

    # Set up the bot
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    logger.info("Bot application initialized.")

    # Handlers
    application.add_handler(CommandHandler("start", start))
    logger.info("Command handlers registered.")

    # Register the event handler for new channel messages
    telethon_client.on(events.NewMessage(chats=CHANNEL_USERNAME))(handle_new_channel_message)
    logger.info("Telethon event handler registered.")

    # Start the bot
    logger.info("Starting bot polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
