import logging
import threading
from flask import Flask
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from pymongo import MongoClient
import os

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
FORCESUB_GROUP_ID = int(os.getenv("FORCESUB_GROUP_ID"))
FORCESUB_INVITE_LINK = os.getenv("FORCESUB_INVITE_LINK")

# MongoDB Setup
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
users_collection = db["users"]

# Logging Setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

async def start(update: Update, context: CallbackContext):
    """Handles /start command"""
    user = update.effective_user
    chat_id = user.id

    member = await context.bot.get_chat_member(FORCESUB_GROUP_ID, chat_id)
    if member.status in ["left", "kicked"]:
        keyboard = [
            [InlineKeyboardButton("Join Group", url=FORCESUB_INVITE_LINK)],
            [InlineKeyboardButton("Try Again", callback_data="check_subscription")]
        ]
        await update.message.reply_text(
            "⚠️ You must join our group to use this bot.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if not users_collection.find_one({"user_id": chat_id}):
        users_collection.insert_one({"user_id": chat_id})
    
    await update.message.delete()

async def check_subscription(update: Update, context: CallbackContext):
    """Handles the Try Again button"""
    query = update.callback_query
    chat_id = query.from_user.id

    member = await context.bot.get_chat_member(FORCESUB_GROUP_ID, chat_id)
    if member.status in ["member", "administrator", "creator"]:
        await query.message.edit_text("✅ You have joined the group! You can now use the bot.")
    else:
        await query.answer("❌ You haven't joined yet. Please join and try again.", show_alert=True)

async def forward_channel_message(update: Update, context: CallbackContext):
    """Forwards messages from the channel to all users"""
    message = update.channel_post
    text = message.text or message.caption

    if text:
        users = users_collection.find({})
        for user in users:
            chat_id = user["user_id"]
            try:
                await context.bot.send_message(chat_id, text, disable_web_page_preview=True)
            except:
                pass

async def user_count(update: Update, context: CallbackContext):
    """Admin command to check total user count"""
    if update.effective_user.id not in [123456789]:  
        return

    count = users_collection.count_documents({})
    await update.message.reply_text(f"👥 Total Users: {count}")
    await update.message.delete()

async def ban_user(update: Update, context: CallbackContext):
    """Admin command to ban a user"""
    if update.effective_user.id not in [123456789]:  
        return

    try:
        target_user_id = int(context.args[0])
        users_collection.delete_one({"user_id": target_user_id})
        await context.bot.ban_chat_member(FORCESUB_GROUP_ID, target_user_id)
        await update.message.reply_text(f"🚫 User {target_user_id} has been banned!")
    except:
        await update.message.reply_text("❌ Invalid User ID.")
    await update.message.delete()

async def delete_user_messages(update: Update, context: CallbackContext):
    """Deletes user messages immediately"""
    try:
        await update.message.delete()
    except:
        pass

async def restrict_message_forwarding(update: Update, context: CallbackContext):
    """Prevents users from forwarding, copying, or saving bot messages"""
    await update.message.reply_text(
        "❌ Forwarding, copying, and saving messages is not allowed.",
        disable_notification=True
    )

def start_http_server():
    """Starts a dummy HTTP server for TCP health checks"""
    app = Flask(__name__)

    @app.route("/")
    def health_check():
        return "Bot is running", 200

    app.run(host="0.0.0.0", port=8080)

def main():
    """Main function to start the bot"""
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("usercount", user_count))
    app.add_handler(CommandHandler("banuser", ban_user, filters=filters.ChatType.PRIVATE))
    app.add_handler(MessageHandler(filters.Chat(CHANNEL_ID), forward_channel_message))
    app.add_handler(MessageHandler(filters.ALL & ~filters.Chat(CHANNEL_ID), delete_user_messages))
    app.add_handler(MessageHandler(filters.FORWARDED, restrict_message_forwarding))
    app.add_handler(MessageHandler(filters.Regex("check_subscription"), check_subscription))

    threading.Thread(target=start_http_server, daemon=True).start()  

    app.run_polling()

if __name__ == "__main__":
    main()
