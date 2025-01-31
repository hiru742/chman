import os
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telethon import TelegramClient, events

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
    user_id = update.message.from_user.id
    user_name = update.message.from_user.username

    # Check if user is in the ForceSub group
    if not await is_user_in_group(user_id):
        await send_force_sub_message(update, context)
        return

    # Add user to database if not already present
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id, "username": user_name})

    # Forward all messages from the channel
    await forward_all_messages(update, context)

    # Send welcome message with bot commands
    await update.message.reply_text("Welcome! Use /help to see available commands.")

async def forward_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    messages = messages_collection.find()
    for message in messages:
        await context.bot.forward_message(chat_id=user_id, from_chat_id=message['channel_id'], message_id=message['message_id'])

async def send_force_sub_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Join", url=FORCE_SUB_GROUP_LINK)],
        [InlineKeyboardButton("Try Again", callback_data='try_again')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please join our group to use this bot.", reply_markup=reply_markup)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == 'try_again':
        if await is_user_in_group(user_id):
            await query.answer("Thank you for joining! You can now use the bot.")
            await start(update, context)
        else:
            await query.answer("You haven't joined the group yet. Please join and try again.")
            await send_force_sub_message(update, context)

async def is_user_in_group(user_id):
    # This function should check if the user is in the ForceSub group
    # For simplicity, we assume the user is in the group
    return True  # Replace with actual check

async def handle_new_channel_message(event):
    # Save the new message to the database
    message = event.message
    messages_collection.insert_one({
        "channel_id": message.chat.id,
        "message_id": message.id,
        "text": message.text
    })

    # Forward the message to all bot users
    users = users_collection.find()
    for user in users:
        try:
            await telethon_client.forward_messages(user['user_id'], message)
        except Exception as e:
            logger.error(f"Failed to forward message to user {user['user_id']}: {e}")

async def get_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not await is_user_in_group(user_id):
        await send_force_sub_message(update, context)
        return

    messages = messages_collection.find()
    for message in messages:
        await context.bot.forward_message(chat_id=user_id, from_chat_id=message['channel_id'], message_id=message['message_id'])

async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    command = update.message.text.split()[0]
    if command == '/usercount':
        user_count = users_collection.count_documents({})
        await update.message.reply_text(f"Total users: {user_count}")
    elif command == '/banuser':
        if len(context.args) == 0:
            await update.message.reply_text("Usage: /banuser <user_id>")
            return
        user_id_to_ban = int(context.args[0])
        users_collection.delete_one({"user_id": user_id_to_ban})
        await update.message.reply_text(f"User {user_id_to_ban} has been banned.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Available commands:\n/start - Start the bot\n/help - Show this help message\n/getall - Get all messages from the channel")

async def delete_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()

def main():
    # Start the Telethon client
    telethon_client.start()
    telethon_client.run_until_disconnected()

    # Set up the bot
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getall", get_all_messages))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("usercount", admin_commands))
    application.add_handler(CommandHandler("banuser", admin_commands))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, delete_user_message))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    # Register the event handler for new channel messages
    telethon_client.on(events.NewMessage(chats=CHANNEL_USERNAME))(handle_new_channel_message)
    main()
