# coding=utf-8
import nest_asyncio
nest_asyncio.apply()

import asyncio
import time
import sys
import logging
from datetime import datetime
import subprocess # For executing shell commands (git pull)

# MongoDB
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Enable logging to see bot activities on console
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# --- Configuration ---
TOKEN = "7608118862:AAHp8Zy8zsQpdx-7zktErHv4N0wBzj8MdrA"  # Replace with your actual token
OWNER = "@rajaraj909" # Bot ka owner username (username, NOT ID)

# MongoDB Configuration
MONGO_URI = "mongodb+srv://pusers:nycreation@nycreation.pd4klp1.mongodb.net/?retryWrites=true&w=majority&appName=NYCREATION" # Replace with your MongoDB connection string (e.g., from Atlas)
DB_NAME = "RoseBotDB"

# ** Sticker IDs (Replace with your actual sticker file IDs) **
DEFAULT_JOIN_STICKER_ID = "CAACAgIAAxkBAAIC3mWZ7WvQzQe5F2l3b3sQ2M1d4QABfQACaQMAAm2YgUrpL3z-X7u4NzQE" # Example ID, replace this
DEFAULT_LEAVE_STICKER_ID = "CAACAgIAAxkBAAIC4WWZ7XCz1e-x_b2p5I3S1Q1j5QABfQACbgMAAm2YgUtjK7t1e6dONzQE" # Example ID, replace this
DEFAULT_START_ANIMATION_STICKER_ID = "CAACAgIAAxkBAAIC6WWZ7fO04r-O9cWwQv4Q3M1d4QABfQACcgMAAm2YgUs-J3t0AAGx-zc0BA" # Example ID, replace this
DEFAULT_START_FINAL_STICKER_ID = "CAACAgIAAxkBAAIC7WWZ7g8_k_jL-fXwR0sQ3M1d4QABfQACdQMAAm2YgUsvI3t0AAGx-Tc0BA" # Example ID, replace this

# --- Upstream Configuration (IMPORTANT: Apne hisaab se badlen) ---
# GitHub repository ka URL jahaan aapka bot code hai
UPSTREAM_REPO_URL = "https://github.com/jkljggggg/r" # ** CHANGE THIS **
# Woh directory jahaan aapne bot ki files rakhi hain
# Agar bot root directory mein hai, toh '.' use karein
REPO_DIR = "." # ** CHANGE THIS to your bot's directory if it's not the current one **

# Global MongoDB Client
mongo_client = None
db = None
chats_collection = None

# --- MongoDB Connection Setup ---
def setup_mongodb():
    global mongo_client, db, chats_collection
    try:
        mongo_client = MongoClient(MONGO_URI)
        mongo_client.admin.command('ping') # Test connection
        db = mongo_client[DB_NAME]
        chats_collection = db["chats"]
        logger.info("💖 𝓜𝓸𝓷𝓰𝓸𝓓𝓑 𝓼𝓮 𝓒𝓸𝓷𝓷𝓮𝓬𝓽 𝓱𝓸 𝓰𝓪𝓲𝓵𝓪\! ✨")
    except ConnectionFailure as e:
        logger.error(f"❌ 𝓜𝓸𝓷𝓰𝓸𝓓𝓑 𝓼𝓮 𝓬𝓸𝓷𝓷𝓮𝓬𝓽 𝓷𝓪 𝓱𝓸 𝓹𝓪𝔂𝓪𝓵: {e} 😥")
        sys.exit(1) # Exit if cannot connect to DB

# --- Utility Functions ---
async def is_admin_or_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Checks if the user is a group administrator or the bot owner."""
    user = update.effective_user
    chat = update.effective_chat

    if chat.type == "private":
        # In private chat, only the bot owner is considered "admin" for bot commands
        return user.username == OWNER.lstrip('@')
        
    try:
        # Get chat administrators
        admins = await context.bot.get_chat_administrators(chat.id)
        admin_ids = {admin.user.id for admin in admins}
        
        # Check if user is among administrators
        if user.id in admin_ids:
            return True

        # Check if user is the bot owner
        if user.username and user.username.lstrip('@') == OWNER.lstrip('@'):
            return True

    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        # In case of error, assume not admin to be safe
        return False
    return False

# --- Chat Settings Management ---
async def get_chat_settings(chat_id):
    settings = chats_collection.find_one({"_id": chat_id})
    if not settings:
        # Default settings if not found
        settings = {
            "_id": chat_id,
            "warn_limit": 3,
            "warns": {}, # {user_id: count}
            "banlink_enabled": True,
            "blocklist": [], # MongoDB doesn't store sets directly, use list
            "blocklist_mode": "mute",
            "locked": {"links": False, "photos": False, "all": False},
            "welcome_enabled": True,
            "welcome_msg": "👋 𝐖𝐞𝐥𝐜𝐨𝐦𝐞\! 𝐌𝐚𝐬𝐭𝐢 𝐤𝐚𝐫𝐨, 𝐣𝐞𝐞\! 🥳",
            "rules_msg": "📜 𝐁𝐞 𝐫𝐞𝐬𝐩𝐞𝐜𝐭𝐟𝐮𝐥\. 𝐍𝐨 𝐬𝐩𝐚𝐦\. 𝐉𝐢𝐲𝐨 𝐚𝐮𝐫 𝐣𝐢𝐧𝐞 𝐝𝐨\! ✨",
            "join_sticker_id": DEFAULT_JOIN_STICKER_ID,
            "leave_sticker_id": DEFAULT_LEAVE_STICKER_ID,
            "start_animation_sticker_id": DEFAULT_START_ANIMATION_STICKER_ID,
            "start_final_sticker_id": DEFAULT_START_FINAL_STICKER_ID,
            "service_message_enabled": True
        }
        chats_collection.insert_one(settings)
        logger.info(f"✨ 𝓝𝓪𝔂𝓪 𝓬𝓱𝓪𝓽 {chat_id} 𝓚𝓮 𝓼𝓮𝓽𝓽𝓲𝓷𝓰𝓼 𝓜𝓸𝓷𝓰𝓸𝓓𝓑 𝓶𝓮𝓲𝓷 𝓭𝓪𝓵 𝓭𝓮𝓮𝓷𝓲\. 🚀")
    return settings

async def update_chat_settings(chat_id, key, value):
    try:
        chats_collection.update_one({"_id": chat_id}, {"$set": {key: value}}, upsert=True)
        logger.info(f"✅ 𝓒𝓱𝓪𝓽 {chat_id} 𝓚𝓮 '{key}' 𝓼𝓮𝓽𝓽𝓲𝓷𝓰 𝓾𝓹𝓭𝓪𝓽𝓮 𝓱𝓸 𝓰𝓪𝓲𝓵\. 💾")
    except OperationFailure as e:
        logger.error(f"❌ 𝓢𝓮𝓽𝓽𝓲𝓷𝓰 𝓾𝓹𝓭𝓪𝓽𝓮 𝓷𝓪 𝓱𝓸 𝓹𝓪𝔂𝓪𝓵 𝓒𝓱𝓪𝓽 {chat_id} 𝓚𝓮: {e} 😥")

async def update_nested_chat_settings(chat_id, outer_key, inner_key, value):
    try:
        chats_collection.update_one({"_id": chat_id}, {"$set": {f"{outer_key}.{inner_key}": value}}, upsert=True)
        logger.info(f"✅ 𝓒𝓱𝓪𝓽 {chat_id} 𝓚𝓮 '{outer_key}.{inner_key}' 𝓼𝓮𝓽𝓽𝓲𝓷𝓰 𝓾𝓹𝓭𝓪𝓽𝓮 𝓱𝓸 𝓰𝓪𝓲𝓵\. 💾")
    except OperationFailure as e:
        logger.error(f"❌ 𝓢𝓮𝓽𝓽𝓲𝓷𝓰 𝓾𝓹𝓭𝓪𝓽𝓮 𝓷𝓪 𝓱𝓸 𝓹𝓪𝔂𝓪𝓵 𝓒𝓱𝓪𝓽 {chat_id} 𝓚𝓮: {e} 😥")

# --- Helper Function to Resolve Target User ID ---
async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            arg = context.args[0].lstrip("@")
            return int(arg)
        except ValueError:
            await update.message.reply_text("🗣️ अरे भाईया, 💎 यूज़र आइडी सही\-सही डालिए न\! 🤓 _\(Isko dekh ke toh lagta hai ki tum abhi bhi naye ho!\)_")
            return None
    else:
        await update.message.reply_text("👀 ई सुनो\! 💬 केकरो मेसेज पर 𝗥𝗲𝗽𝗹𝘆 करो चाहे 🆔 यूज़र आइडी दे दो\! 😎 _\(Itna bhi mushkil nahi hai, Yaar!\)_")
        return None

# --- General Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    username = f"@{user.username}" if user.username else user.full_name
    
    settings = await get_chat_settings(chat.id) # Load chat settings

    # ** Enhanced Starting Animation (Full Bihari Style with Emojis) **
    loading_messages = [
        "💖 𝐋", "💖 𝐋𝐨", "💖 𝐋𝐨𝐚", "💖 𝐋𝐨𝐚𝐝", "💖 𝐋𝐨𝐚𝐝𝐢", "💖 𝐋𝐨𝐚𝐝𝐢𝐧", "💖 𝐋𝐨𝐚𝐝𝐢𝐧𝐠",
        "💖 𝐋𝐨𝐚𝐝𝐢𝐧𝐠\. ⏳", "💖 𝐋𝐨𝐚𝐝𝐢𝐧𝐠\.\. ⌛", "💖 𝐋𝐨𝐚𝐝𝐢𝐧𝐠\.\.\. 💫", "💖 𝐋𝐨𝐚𝐝𝐢𝐧𝐠\.\.\.\. ✨",
        "💫 𝐋𝐨𝐚𝐝 होत है, 𝐘𝐚𝐫\!  تھوڑا صبروا राखअ\.\.\. 🧐", 
        "✨ 𝐒𝐚𝐛 𝐣𝐚𝐝𝐮 𝐜𝐡𝐚𝐥 𝐫𝐚𝐡𝐚 𝐡𝐚𝐢, 💎 रउआ इंतज़ार करीं ज़रा\.\. 🕰️", 
        "🎀 𝐓𝐚𝐢𝐲𝐚𝐫𝐢 𝐛𝐡𝐚𝐫𝐩𝐨𝐨𝐫 𝐜𝐡𝐚𝐥 𝐫𝐚𝐡𝐢 𝐡𝐚𝐢, 🍫 बाबू\.\.\. 🚀",
        "💅 𝐒𝐚𝐛 𝐞𝐤 𝐝𝐚𝐦 𝐅𝐢𝐭 𝐤𝐚𝐫 𝐫𝐚𝐡𝐞 𝐡𝐚𝐢𝐧, 😎 बस आ ही गइनी\.\.\. ✅", 
        "💖 𝐇𝐨 𝐠𝐚𝐢𝐥, 𝐘𝐚𝐫\! 💯 𝐉𝐚𝐥𝐝𝐢 𝐚𝐚𝐲𝐞𝐧𝐠𝐞, 𝐑𝐨𝐜𝐤 𝐤𝐚𝐫𝐧𝐞\.\.\. 🎶"
    ]
    
    lols = await update.message.reply_text("💖 𝐒𝐡𝐮𝐫𝐮 𝐤𝐚𝐫 𝐫𝐚𝐡େ 𝐡𝐚𝐢𝐧, 𝐘𝐚𝐫\! 🚀")
    
    # Send start animation sticker if available
    start_animation_sticker = settings.get("start_animation_sticker_id", DEFAULT_START_ANIMATION_STICKER_ID)
    if start_animation_sticker:
        try:
            await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=start_animation_sticker)
        except Exception as e:
            logger.error(f"Error sending start animation sticker: {e}")

    for text in loading_messages:
        await lols.edit_text(f"**{text}**", parse_mode="MarkdownV2")
        await asyncio.sleep(0.18) # Slightly increased sleep for better readability
    await asyncio.sleep(0.7)
    await lols.delete()

    # Get user profile photo if available
    photos = await context.bot.get_user_profile_photos(user.id, limit=1)
    
    welcome_text = (
        f"👑 *𝐀𝐚𝐡 𝐆𝐚𝐢𝐥𝐚 𝐭𝐮, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\!* 👑\n\n"
        f"• ✨ *𝐍𝐚𝐚𝐦:* `{user.full_name}`\n"
        f"• 🎀 *𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞𝐰𝐚:* `{username}`\n"
        f"• 💖 *𝐔𝐬𝐞𝐫 𝐈𝐃:* `{user.id}`\n"
        f"• 🌸 *𝐊𝐚𝐛 𝐬𝐞 𝐚𝐚𝐲𝐚𝐥 𝐡𝐚:* `{user.language_code if user.language_code else '𝐏𝐚𝐭𝐚𝐚𝐡𝐢 𝐧𝐚𝐡𝐢 𝐛𝐚'}`\n\n"
        f"✨ *𝐇𝐚𝐦𝐫𝐚 {chat.title if chat.title else '𝐞 𝐠𝐫𝐨𝐮𝐩𝐰𝐚'} 𝐦𝐞𝐢𝐧 𝐭𝐨𝐡𝐚𝐫𝐚 𝐬𝐰𝐚𝐠𝐚𝐭 𝐛𝐚\! 𝐌𝐚𝐣𝐚 𝐤𝐚𝐫𝐢𝐲𝐞, 𝐘𝐚𝐫\! 🥳* ✨"
    )
    
    if photos.total_count > 0:
        photo_file = photos.photos[0][0]
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_file.file_id,
            caption=welcome_text,
            parse_mode="MarkdownV2"
        )
    else:
        await update.message.reply_text(welcome_text, parse_mode="MarkdownV2")

    # Send final start sticker if available
    start_final_sticker = settings.get("start_final_sticker_id", DEFAULT_START_FINAL_STICKER_ID)
    if start_final_sticker:
        try:
            await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=start_final_sticker)
        except Exception as e:
            logger.error(f"Error sending final start sticker: {e}")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_list = """
🧠 💫 *𝐑𝐨𝐬𝐞𝐁𝐨𝐭 𝐤𝐞 𝐒𝐚𝐫𝐤𝐚𝐫𝐢 𝐍𝐢𝐲𝐚𝐦𝐰𝐚 𝐚𝐮𝐫 𝐊𝐚𝐦𝐚𝐧𝐝𝐬* 👑
_ \(𝐄𝐤 𝐝𝐚𝐦 𝐅𝐮𝐥𝐥 𝐏𝐨𝐰𝐞𝐫 𝐌𝐨𝐝𝐞 𝐦𝐞𝐢𝐧\)\!_

💎 *𝐆𝐞𝐧𝐞𝐫𝐚𝐥 𝐁𝐚𝐚𝐭:*
  /start \- 𝐀𝐩𝐧𝐞 𝐛𝐚𝐚𝐫𝐞 𝐦𝐞𝐢𝐧 𝐛𝐚𝐭𝐚𝐞𝐧𝐠𝐞 𝐚𝐮𝐫 𝐭𝐨𝐡𝐚𝐫𝐚 𝐬𝐰𝐚𝐠𝐚𝐭 𝐤𝐚𝐫𝐞𝐧𝐠𝐞\. 👋
  /help \- 𝐄 𝐬𝐚𝐛 𝐧𝐢𝐲𝐚𝐦 𝐚𝐮𝐫 𝐤𝐚𝐦𝐚𝐧𝐝𝐬 𝐝𝐞𝐤𝐡𝐚\. 📜 _\(Agar dimaag me ghus jaata toh kya baat thi!\)_
  /ROSE \- 𝐁𝐨𝐭 𝐤𝐞 𝐛𝐚𝐚𝐫𝐞 𝐦𝐞𝐢𝐧 𝐣𝐚𝐧𝐚\. 🤖 _\(Hum hai kaun, ye toh jaan lo!\)_
  /ping \- 𝐁𝐨𝐭 𝐤𝐞 𝐜𝐡𝐚𝐥𝐚𝐧𝐞 𝐤𝐞 𝐬𝐩𝐞𝐞𝐝 𝐝𝐞𝐤𝐡𝐚\. 🚀 _\(Rocket se bhi tez!\)_
  /donate \- 𝐏𝐚𝐢𝐬𝐚\-𝐤𝐚𝐮𝐝𝐢 𝐝𝐞𝐧𝐚 𝐡𝐚𝐢 𝐭𝐨𝐡 𝐢𝐝𝐡𝐚𝐫 𝐚𝐚𝐨\. 💸 _\(Thoda pyaar aur paisa to banta hai na!\)_
  /id \- 𝐆𝐫𝐨𝐮𝐩 𝐚𝐮𝐫 𝐚𝐩𝐧𝐚 𝐔𝐬𝐞𝐫 𝐈𝐃 𝐝𝐞𝐤𝐡𝐚\. 🆔 _\(Apni pehchan toh zaroori hai!\)_
  /stickerid \- 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐚𝐮𝐫 𝐋𝐞𝐚𝐯𝐞 𝐬𝐭𝐢𝐜𝐤𝐞𝐫 𝐤𝐢 𝐈𝐃 𝐝𝐞𝐤𝐡𝐚\. 🖼️ _\(Kuch naya try karna hai kya?\)_
  /getstickerid \- 𝐑𝐞𝐩𝐥𝐲 𝐤𝐚𝐫𝐨 𝐤𝐢𝐬𝐢 𝐬𝐭𝐢𝐜𝐤𝐞𝐫 𝐩𝐚𝐫 𝐮𝐬𝐤𝐚 𝐈𝐃 𝐩𝐚𝐚𝐧𝐞 𝐤𝐞 𝐥𝐢𝐲𝐞\. 🌠 _\(Jadui sticker ka raaz!\)_
  /update \- 𝐁𝐨𝐭 𝐤𝐞 𝐜𝐨𝐝𝐞 𝐤𝐨 𝐥𝐚𝐭𝐞𝐬𝐭 𝐯𝐞𝐫𝐬𝐢𝐨𝐧 𝐩𝐚𝐫 𝐮𝐩𝐝𝐚𝐭𝐞 𝐤𝐚𝐫𝐨\. 🔄 _\(Sirf Owner ke liye, bade logon ka kaam!\)_

💖 *𝐌𝐨𝐝𝐞𝐫𝐚𝐭𝐢𝐨𝐧* \(💬 𝐑𝐞𝐩𝐥𝐲 𝐤𝐚𝐫 𝐤𝐞 𝐔𝐬𝐞𝐫 𝐤𝐞 𝐛𝐚𝐭𝐚𝐨 𝐲𝐚 𝐩𝐡𝐢𝐫 🆔 𝐔𝐬𝐞𝐫 𝐈𝐃 𝐝𝐞 𝐝𝐨\):
  /warn <user id> \- 𝐂𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐝𝐨\. ⚠️ _\(Sudhar jao, varna pakde jaoge!\)_
  /resetwarns <user id> \- 𝐂𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐡𝐚𝐭𝐚𝐨\. ✨ _\(Ek aur chance mil gaya!\)_
  /setwarnlimit <number> \- 𝐂𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐤𝐞 𝐥𝐢𝐦𝐢𝐭 𝐬𝐞𝐭 𝐤𝐚𝐫𝐨\. 🔢 _\(Kitni baar maaf karein tumhe?\)_
  /ban <user id> \- 𝐍𝐢𝐤𝐚𝐥 𝐟𝐞𝐧𝐤𝐨\. 🚫 _\(Bye\-bye, tata, goodbye!\)_
  /unban <user id> \- 𝐖𝐚𝐩𝐚𝐬 𝐛𝐮𝐥𝐚𝐨\. 🫂 _\(Dil bada hai apna, aa jao wapas!\)_
  /kick <user id> \- 𝐋𝐚𝐚𝐭 𝐦𝐚𝐚𝐫 𝐤𝐞 𝐧𝐢𝐤𝐚𝐥𝐨\. 👢 _\(Jaldi se bhago yahan se!\)_
  /mute <user id> \- 𝟏 𝐠𝐡𝐚𝐧𝐭𝐚 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐜𝐡𝐮𝐩 𝐤𝐚𝐫𝐚 𝐝𝐨\. 🔇 _\(Ab awaaz mat nikalna!\)_
  /unmute <user id> \- 𝐀𝐚𝐰𝐚𝐚𝐳 𝐰𝐚𝐩𝐚𝐬 𝐝𝐨\. 🔊 _\(Bolna hai toh ab bolo!\)_

✨ *𝐁𝐚𝐝𝐤𝐚 𝐋𝐨𝐠 𝐤𝐞 𝐊𝐚𝐚𝐦 \(𝐀𝐝𝐦𝐢𝐧 𝐓𝐨𝐨𝐥𝐬\):*
  /promote <user id> \- 𝐁𝐚𝐝𝐤𝐚 𝐛𝐚𝐧𝐚𝐨\. 👑 _\(Power aa gayi, ab jao raaj karo!\)_
  /demote <user id> \- 𝐂𝐡𝐡𝐨𝐭𝐤𝐚 𝐛𝐚𝐧𝐚𝐨\. 📉 _\(Zameen par aa jao, Maharaj!\)_
  /admins \- 𝐒𝐚𝐛 𝐚𝐝𝐦𝐢𝐧 𝐤𝐞 𝐧𝐚𝐚𝐦 𝐝𝐞𝐤𝐡𝐨\. 🧑‍⚖️ _\(Ye hain asli khiladi!\)_

🔒 *𝐁𝐚𝐧𝐝 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐒𝐲𝐬𝐭𝐞𝐦 \(𝐋𝐨𝐜𝐤 𝐒𝐲𝐬𝐭𝐞𝐦\):*
  /lock \[all\|links\|photos\] \- 𝐒𝐚𝐛 𝐛𝐚𝐧𝐝 𝐤𝐚𝐫𝐨\. 🔐 _\(Ab koi harkat nahi!\)_
  /unlock \[all\|links\|photos\] \- 𝐒𝐚𝐛 𝐤𝐡𝐨𝐥𝐨\. 🔓 _\(Freedom mil gayi!\)_

🚫 *𝐅𝐚𝐥𝐭𝐮 𝐒𝐚𝐧𝐝𝐞𝐬𝐡 𝐑𝐨𝐤𝐧𝐞 𝐖𝐚𝐥𝐚 \(𝐒𝐩𝐚𝐦 𝐅𝐢𝐥𝐭𝐞𝐫\):*
  /banlink \[on\|off\] \- 𝐋𝐢𝐧𝐤 𝐛𝐡𝐞𝐣𝐧𝐚 𝐛𝐚𝐧𝐝 𝐤𝐚𝐫𝐨 𝐲𝐚 𝐜𝐡𝐚𝐥𝐮 𝐤𝐚𝐫𝐨\. 🔗 _\(No promotion, only pure masti!\)_
  /blocklist \[add\|remove\] <shabd> \- 𝐘𝐞 𝐬𝐡𝐚𝐛𝐝 𝐥𝐢𝐬𝐭 𝐦𝐞𝐢𝐧 𝐝𝐚𝐚𝐥𝐨 𝐲𝐚 𝐡𝐚𝐭𝐚𝐨\. 📝 _\(Gande shabdon ko hatao!\)_
  /blocklistmode <mute\|ban> \- 𝐊𝐚𝐚𝐦 𝐝𝐞𝐤𝐡𝐨 𝐦𝐮𝐭𝐞 𝐲𝐚 𝐛𝐚𝐧\. ⚔️ _\(Saza kya deni hai, decide karo!\)_

🌸 *𝐒𝐰𝐚𝐠𝐚𝐭 𝐊𝐚𝐫𝐞 𝐊𝐞 𝐒𝐲𝐬𝐭𝐞𝐦 \(𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐒𝐲𝐬𝐭𝐞𝐦\):*
  /welcome \[on\|off\] \- 𝐒𝐰𝐚𝐠𝐚𝐭 𝐬𝐚𝐧𝐝𝐞𝐬𝐡 𝐜𝐡𝐚𝐥𝐮 𝐲𝐚 𝐛𝐚𝐧𝐝 𝐤𝐚𝐫𝐨\. 🥳 _\(Welcome party ka mood hai ya nahi!\)_
  /setwelcome <sandesh> \- 𝐒𝐰𝐚𝐠𝐚𝐭 𝐬𝐚𝐧𝐝𝐞𝐬𝐡 𝐥𝐢𝐤𝐡𝐨\. ✍️ _\(Apni marzi ka welcome!\)_
  /cleanwelcome \- 𝐒𝐰𝐚𝐠𝐚𝐭 𝐬𝐚𝐧𝐝𝐞𝐬𝐡 𝐦𝐢𝐭𝐚𝐨\. 🗑️ _\(Back to basics!\)_
  /setwelcomesticker <sticker\_id> \- 𝐒𝐰𝐚𝐠𝐚𝐭 𝐬𝐭𝐢𝐜𝐤𝐞𝐫 𝐛𝐚𝐝𝐥𝐨\. 💖 _\(Naye sticker se swagat!\)_
  /setleavesticker <sticker\_id> \- 𝐉𝐚𝐚𝐧𝐞 𝐰𝐚𝐥𝐚 𝐬𝐭𝐢𝐜𝐤𝐞𝐫 𝐛𝐚𝐝𝐥𝐨\. 💔 _\(Alvida kehne ka style!\)_

📜 *𝐍𝐢𝐲𝐚𝐦 𝐊𝐚𝐧𝐮𝐧 \(𝐑𝐮𝐥𝐞𝐬 𝐒𝐲𝐬𝐭𝐞𝐦\):*
  /setrules <likh do> \- 𝐍𝐢𝐲𝐚𝐦 𝐥𝐢𝐤𝐡 𝐝𝐨\. 📄 _\(Apne rules, apni marzi!\)_
  /rules \- 𝐍𝐢𝐲𝐚𝐦 𝐝𝐞𝐤𝐡𝐨\. ⚖️ _\(Pehle padho, phir baat karo!\)_
  /cleanrules \- 𝐍𝐢𝐲𝐚𝐦 𝐦𝐢𝐭𝐚 𝐝𝐨\. 🧹 _\(Rules break karne ka bahana nahi!\)_

🎀 *𝐒𝐚𝐧𝐝𝐞𝐬𝐡 𝐤𝐞 𝐀𝐮𝐳𝐚𝐚𝐫 \(𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐓𝐨𝐨𝐥𝐬\):*
  /pin \- 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐩𝐢𝐧 𝐤𝐚𝐫𝐨\. 📌 _\(Important hai, sabko dikhna chahiye!\)_
  /unpin \- 𝐏𝐢𝐧 𝐤𝐢𝐲𝐚 𝐡𝐮𝐚 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐡𝐚𝐭𝐚𝐨\. 📍 _\(Ab ho gaya kaam!\)_
  /del \- 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭𝐚𝐨\. ❌ _\(Gayab\! Jaise kabhi tha hi nahi!\)_
  /purge \[count\] \- 𝐁𝐚𝐡𝐮𝐭 𝐬𝐚𝐚𝐫𝐚 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭𝐚𝐨 \(𝐑𝐞𝐩𝐥𝐲 𝐲𝐚 𝐜𝐨𝐮𝐧𝐭 𝐝𝐨\)\. 💥 _\(Clean sweep\!)\_
  /cleanservice \[on\|off\] \- 𝐒𝐞𝐫𝐯𝐢𝐜𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐬𝐚𝐚𝐟 𝐤𝐚𝐫𝐨\. 🧹 _\(Extra stuff nahi chahiye!\)_
"""
    await update.message.reply_text(command_list, parse_mode="MarkdownV2")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t1 = time.time()
    msg = await update.message.reply_text("🏓 𝐏𝐢𝐧𝐠\-𝐩𝐨𝐧𝐠 𝐤𝐡𝐞𝐥 𝐫𝐚𝐡𝐞 𝐡𝐚𝐢𝐧\.\.\. 🎾 _\(Dekhte hain kaun jeet\-ta hai!\)_")
    t2 = time.time()
    await msg.edit_text(f"🏓 𝐏𝐨𝐧𝐠: `\{int\((t2 \- t1\) \* 1000\)}\ms` 💫 𝐁𝐚𝐡𝐮𝐭 𝐭𝐞𝐳, 𝐘𝐚𝐫\! ⚡ _\(Humse tez koi nahi!\)_", parse_mode="MarkdownV2")

async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💸 𝐇𝐮𝐦𝐤𝐞 𝐤𝐮𝐜𝐡 𝐩𝐚𝐢𝐬𝐚\-𝐤𝐚𝐮𝐝𝐢 𝐝𝐞𝐛𝐚\? 𝐈𝐝𝐡𝐚𝐫 𝐛𝐡𝐞𝐣𝐨: @RAJARAJ909 💖 𝐃𝐡𝐚𝐧𝐲𝐚𝐰𝐚𝐝\! 🙏 _\(Thoda pyaar dikhaoge toh hum aur mast kaam karenge!\)_", parse_mode="MarkdownV2")

async def ROSE(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💠 *𝐇𝐮𝐦 𝐡𝐚𝐢𝐧 𝐑𝐨𝐬𝐞𝐁𝐨𝐭: 𝐄𝐡𝐢 𝐤𝐞 𝐛𝐚𝐚𝐫𝐞 𝐦𝐞𝐢𝐧 𝐛𝐚𝐚𝐭 𝐡𝐨 𝐫𝐚𝐡𝐚 𝐡𝐚𝐢* 🌟\n\n𝐁𝐚𝐧𝐚𝐰𝐚𝐥 𝐠𝐞𝐞𝐥 𝐛𝐚 {OWNER} 𝐤𝐞 𝐭𝐚𝐫𝐚𝐟 𝐬𝐞 ✨ 𝐋𝐞𝐠𝐞𝐧𝐝 𝐡𝐚𝐢 𝐡𝐮𝐦\! 🏆 _\(Aise hi thodi na hum itne cool hain!\)_", parse_mode="MarkdownV2")

# --- Moderation Commands ---
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    warn_limit = settings.get("warn_limit", 3)
    warns = settings.get("warns", {})

    uid = await get_target_user(update, context)
    if uid is None:
        return
    
    warns[str(uid)] = warns.get(str(uid), 0) + 1 # Store user ID as string for MongoDB keys
    await update_chat_settings(chat_id, "warns", warns)

    if warns[str(uid)] >= warn_limit:
        await context.bot.ban_chat_member(chat_id, uid)
        await update.message.reply_text(f"🚫 𝐄 𝐔𝐬𝐞𝐫 \(𝐈𝐃: `{uid}`\) 𝐤𝐞 `{warn_limit}` 𝐜𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐀𝐛 𝐧𝐢𝐤𝐚𝐥𝐨 𝐢𝐬𝐤𝐨, 𝐘𝐚𝐫\! 💔 𝐓𝐚𝐭𝐚 𝐛𝐲𝐞\-𝐛𝐲𝐞\! 👋 _\(Agli baar se aane ki sochna bhi mat!\)_")
        # Reset warns after ban
        warns[str(uid)] = 0
        await update_chat_settings(chat_id, "warns", warns)
    else:
        await update.message.reply_text(f"⚠️ 𝐄 𝐔𝐬𝐞𝐫 \(𝐈𝐃: `{uid}`\) 𝐤𝐞 𝐜𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐦𝐢𝐥𝐚𝐚𝐥 𝐛𝐚\! \[`{warns[str(uid)]}`/`{warn_limit}`\] 𝐓𝐡𝐨𝐝𝐚 𝐝𝐡𝐲𝐚𝐧 𝐫𝐚𝐤𝐡𝐨, 𝐌𝐢𝐭𝐫𝐚\! 🎀 𝐀𝐠𝐥𝐢 𝐛𝐚𝐚𝐫 𝐬𝐞 𝐧𝐚𝐡𝐢\! 🚫 _\(Sudhar jao, abhi bhi mauka hai!\)_", parse_mode="MarkdownV2")

async def resetwarns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    warns = settings.get("warns", {})

    uid = await get_target_user(update, context)
    if uid is None:
        return
    
    warns[str(uid)] = 0
    await update_chat_settings(chat_id, "warns", warns)
    await update.message.reply_text("✅ 𝐂𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐬𝐚𝐚𝐟 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐅𝐫𝐞𝐬𝐡 𝐬𝐭𝐚𝐫𝐭 𝐤𝐚𝐫𝐨, 𝐣𝐞𝐞\! ✨ 𝐀𝐛 𝐤𝐨𝐢 𝐛𝐚𝐚𝐭 𝐧𝐚𝐡𝐢\! 🥳 _\(Nayi shuruaat, naya जोश!\)_")

async def setwarnlimit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)

    if context.args:
        try:
            new_limit = int(context.args[0])
            await update_chat_settings(chat_id, "warn_limit", new_limit)
            await update.message.reply_text(f"✅ 𝐂𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐤𝐞 𝐥𝐢𝐦𝐢𝐭 `{new_limit}` 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐀𝐜𝐡𝐡𝐚 𝐬𝐞 𝐫𝐚𝐡𝐧𝐚, 𝐘𝐚𝐫\! 💖 𝐒𝐚𝐦𝐚𝐣𝐡𝐚\? 🤓 _\(Rules are rules, my friend!\)_", parse_mode="MarkdownV2")
        except ValueError:
            await update.message.reply_text("❌ 𝐒𝐚𝐡𝐢\-𝐬𝐚hi 𝐧𝐮𝐦𝐛𝐞𝐫𝐰𝐚 𝐝𝐚𝐚𝐥, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\. 💅 𝐄𝐡 𝐤𝐚 𝐤𝐚𝐫 𝐫𝐚𝐡𝐚 𝐡𝐨\? 🤦‍♀️ _\(Lagta hai tum calculator bhool gaye!\)_")
    else:
        await update.message.reply_text(f"𝐀𝐛𝐡𝐢 𝐤𝐞 𝐜𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐥𝐢𝐦𝐢𝐭 `{settings.get('warn_limit', 3)}` 𝐛𝐚\. ✨ 𝐈𝐬𝐢 𝐩𝐞 𝐜𝐡𝐚𝐥𝐨\! 🤝 _\(Zyaada mat socho!\)_", parse_mode="MarkdownV2")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    uid = await get_target_user(update, context)
    if uid is None:
        return
    await context.bot.ban_chat_member(update.effective_chat.id, uid)
    await update.message.reply_text(f"🚫 𝐄 𝐔𝐬𝐞𝐫 \(𝐈𝐃: `{uid}`\) 𝐤𝐞 𝐠𝐫𝐨𝐮𝐩 𝐬𝐞 𝐧𝐢𝐤𝐚𝐥 𝐝𝐞𝐞𝐧𝐢\. 𝐂𝐡𝐚𝐥 𝐧𝐢𝐤𝐚𝐥, 𝐁𝐨𝐫𝐢𝐲𝐚\-𝐛𝐢𝐬𝐭𝐚𝐫𝐚 𝐥𝐞 𝐤𝐞\! 💔 👋 _\(Ab is group mein tumhara koi kaam nahi!\)_", parse_mode="MarkdownV2")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    uid = await get_target_user(update, context)
    if uid is None:
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text(f"✅ 𝐄 𝐔𝐬𝐞𝐫 \(𝐈𝐃: `{uid}`\) 𝐤𝐞 𝐰𝐚𝐩𝐚𝐬 𝐛𝐮𝐥𝐚 𝐥𝐢𝐲𝐚𝐢𝐧𝐢\. 𝐀𝐚 𝐣𝐚𝐨, 𝐘𝐚𝐫\! 💖 𝐌𝐢𝐥 𝐤𝐞 𝐫𝐚𝐡𝐞𝐧𝐠𝐞\! 🫂 _\(Dil bada hai apna, aa jao wapas!\)_", parse_mode="MarkdownV2")
    except Exception as e:
        await update.message.reply_text(f"❌ 𝐔𝐧𝐛𝐚𝐧 𝐧𝐚 𝐡𝐨 𝐩𝐚𝐲𝐚𝐥, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣: `{e}` 😥 𝐊𝐮𝐜𝐡 𝐠𝐚𝐝𝐛𝐚𝐝 𝐛𝐚\! 🤷‍♀️ _\(Lagta hai kismat saath nahi de rahi!\)_", parse_mode="MarkdownV2")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    uid = await get_target_user(update, context)
    if uid is None:
        return
    await context.bot.kick_chat_member(update.effective_chat.id, uid)
    await update.message.reply_text(f"👢 𝐄 𝐔𝐬𝐞𝐫 \(𝐈𝐃: `{uid}`\) 𝐤𝐞 𝐥𝐚𝐚𝐭 𝐦𝐚𝐚𝐫 𝐤𝐞 𝐧𝐢𝐤𝐚𝐥 𝐝𝐞𝐞𝐧𝐢\. 𝐁𝐡𝐚𝐠𝐨, 𝐝𝐮𝐬𝐫𝐚 𝐝𝐮𝐧𝐢𝐲𝐚 𝐦𝐞𝐢𝐧\! 👋 _\(Samajh lo warning thi, ab bhago!\)_", parse_mode="MarkdownV2")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    uid = await get_target_user(update, context)
    if uid is None:
        return
    until_date = int(time.time()) + 3600
    perms = ChatPermissions(can_send_messages=False)
    await context.bot.restrict_chat_member(update.effective_chat.id, uid, permissions=perms, until_date=until_date)
    await update.message.reply_text(f"🔇 𝐄 𝐔𝐬𝐞𝐫 \(𝐈𝐃: `{uid}`\) 𝐤𝐞 𝟏 𝐠𝐡𝐚𝐧𝐭𝐚 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐜𝐡𝐮𝐩 𝐤𝐚𝐫𝐚 𝐝𝐞𝐞𝐧𝐢\. 𝐒𝐡𝐡𝐡\.\.\. 🤫 𝐍𝐨 𝐛𝐨𝐥\-𝐛𝐚𝐜𝐡𝐚𝐧\! 🙅‍♂️ _\(Ab baatein band!\)_", parse_mode="MarkdownV2")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    uid = await get_target_user(update, context)
    if uid is None:
        return
    perms = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True)
    await context.bot.restrict_chat_member(update.effective_chat.id, uid, permissions=perms)
    await update.message.reply_text(f"🔊 𝐄 𝐔𝐬𝐞𝐫 \(𝐈𝐃: `{uid}`\) 𝐤𝐞 𝐚𝐚𝐰𝐚𝐚𝐳 𝐰𝐚𝐩𝐚𝐬 𝐚𝐚 𝐠𝐚𝐢𝐥\. 𝐀𝐛 𝐛𝐨𝐥 𝐬𝐚𝐤𝐨 𝐡𝐨, 𝐘𝐚𝐫\! 🎤 𝐆𝐮𝐩𝐬𝐡𝐮𝐩 𝐤𝐚𝐫𝐨\! 🗣️ _\(Ab shuru ho jao apni kahani!\)_", parse_mode="MarkdownV2")

# --- Admin Commands ---
async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    uid = await get_target_user(update, context)
    if uid is None:
        return
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, uid,
            can_change_info=True, can_post_messages=True,
            can_edit_messages=True, can_delete_messages=True,
            can_invite_users=True, can_restrict_members=True,
            can_pin_messages=True, can_promote_members=True
        )
        await update.message.reply_text(f"✅ 𝐄 𝐔𝐬𝐞𝐫 \(𝐈𝐃: `{uid}`\) 𝐤𝐞 𝐛𝐚𝐝𝐤𝐚 𝐛𝐚𝐧𝐚 𝐝𝐞𝐞𝐧𝐢\! 👑 𝐉𝐚𝐢 𝐡𝐨 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\! 🌟 _\(Ab tum ho is group ke shaan!\)_", parse_mode="MarkdownV2")
    except Exception as e:
        await update.message.reply_text(f"❌ 𝐁𝐚𝐝𝐤𝐚 𝐧𝐚 𝐛𝐚𝐧 𝐩𝐚𝐲𝐚𝐥, 𝐘𝐚𝐫: `{e}` 💔 𝐊𝐮𝐜𝐡 𝐝𝐢𝐤𝐤𝐚𝐭 𝐛𝐚\! 🤷‍♂️ _\(Lagta hai abhi aur mehnat karni padegi!\)_", parse_mode="MarkdownV2")

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    uid = await get_target_user(update, context)
    if uid is None:
        return
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, uid,
            can_change_info=False, can_post_messages=False,
            can_edit_messages=False, can_delete_messages=False,
            can_invite_users=False, can_restrict_members=False,
            can_pin_messages=False, can_promote_members=False
        )
        await update.message.reply_text(f"✅ 𝐄 𝐔𝐬𝐞𝐫 \(𝐈𝐃: `{uid}`\) 𝐤𝐞 𝐜𝐡𝐡𝐨𝐭𝐤𝐚 𝐛𝐚𝐧𝐚 𝐝𝐞𝐞𝐧𝐢\. 𝐀𝐛 𝐭𝐡𝐢𝐤 𝐬𝐞 𝐫𝐚𝐡𝐨, 𝐘𝐚𝐫\! 💅 𝐍𝐢𝐲𝐚𝐦 𝐬𝐞 𝐜𝐡𝐚𝐥𝐨\! 🚶‍♀️ _\(Zameen par aa jao, Maharaj!\)_", parse_mode="MarkdownV2")
    except Exception as e:
        await update.message.reply_text(f"❌ 𝐂𝐡𝐡𝐨𝐭𝐤𝐚 𝐧𝐚 𝐛𝐚𝐧 𝐩𝐚𝐲𝐚𝐥, 𝐘𝐚𝐫: `{e}` 😥 𝐘𝐞 𝐭𝐨𝐡 𝐛𝐮𝐫𝐚 𝐡𝐮𝐚\! 😔 _\(Kismat ka khel hai, babu bhaiya!\)_", parse_mode="MarkdownV2")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Admins/owner and regular users can use this to see admins
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        admin_list = "\n".join([f"\- {admin.user.full_name} ✨" for admin in admins])
        await update.message.reply_text(f"👑 𝐄 𝐠𝐫𝐨𝐮𝐩𝐰𝐚 𝐤𝐞 𝐬𝐚𝐛 𝐌𝐚𝐡𝐚𝐫𝐚𝐣 𝐚𝐮𝐫 𝐌𝐚𝐡𝐚𝐫𝐚𝐧𝐢 𝐡𝐚𝐢𝐧:\n{admin_list} 🤩 _\(Inse panga mat lena!\)_", parse_mode="MarkdownV2")
    except Exception as e:
        await update.message.reply_text(f"❌ 𝐀𝐝𝐦𝐢𝐧 𝐤𝐞 𝐥𝐢𝐬𝐭 𝐧𝐚 𝐧𝐢𝐤𝐚𝐥 𝐩𝐚𝐲𝐚𝐥: `{e}` 😥 𝐀𝐟𝐬𝐨𝐬\! 😞 _\(Lagta hai kuch gadbad hai!\)_", parse_mode="MarkdownV2")

# --- Lock System Commands ---
async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    locked_features = settings.get("locked", {})

    if not context.args:
        await update.message.reply_text("🗣️ 𝐊𝐚 𝐛𝐚𝐧𝐝 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐛𝐚\? `\[all\|links\|photos\]` 𝐃𝐡𝐚𝐧𝐠 𝐬𝐞 𝐛𝐚𝐭𝐚𝐨 𝐧𝐚\! 🔒 _\(Kya, samajh nahi aaya kya?\)_", parse_mode="MarkdownV2")
        return
    arg = context.args[0].lower()
    if arg in locked_features:
        locked_features[arg] = True
        await update_chat_settings(chat_id, "locked", locked_features)
        await update.message.reply_text(f"🔒 `{arg.capitalize()}` 𝐛𝐚𝐧𝐝 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐒𝐮𝐫𝐚𝐤𝐬𝐡𝐢𝐭 𝐛𝐚, 𝐘𝐚𝐫\! 🔐 𝐊𝐨𝐢 𝐟𝐢𝐤𝐚𝐫 𝐧𝐚𝐡𝐢\! 💪 _\(Ab koi chhed chhad nahi!\)_", parse_mode="MarkdownV2")
    elif arg == "all":
        for key in locked_features:
            locked_features[key] = True
        await update_chat_settings(chat_id, "locked", locked_features)
        await update.message.reply_text("🔒 𝐒𝐚𝐛 𝐤𝐮𝐜𝐡 𝐛𝐚𝐧𝐝 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐊𝐮𝐜𝐡 𝐧𝐚 𝐜𝐡𝐡𝐮𝐭𝐢\! 💖 𝐅𝐮𝐥𝐥 𝐬𝐞𝐜𝐮𝐫𝐢𝐭𝐲\! 🛡️ _\(Ab koi harkat nahi chalegi!\)_")
    else:
        await update.message.reply_text("🤦‍♀️ 𝐆𝐚𝐥𝐚𝐭 𝐛𝐚𝐚𝐭 𝐛𝐨𝐥𝐚𝐭 𝐡𝐨, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\. '`all`', '`links`', 𝐲𝐚 '`photos`' 𝐛𝐨𝐥 𝐧𝐚\. 💅 _\(Itna bhi mushkil nahi hai!\)_", parse_mode="MarkdownV2")

async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    locked_features = settings.get("locked", {})

    if not context.args:
        await update.message.reply_text("🗣️ 𝐊𝐚 𝐤𝐡𝐨𝐥𝐞 𝐤𝐞 𝐛𝐚\? `\[all\|links\|photos\]` 𝐃𝐡𝐚𝐧𝐠 𝐬𝐞 𝐛𝐚𝐭𝐚𝐨 𝐧𝐚\! 🔓 _\(Jaldi batao, time nahi hai!\)_", parse_mode="MarkdownV2")
        return
    arg = context.args[0].lower()
    if arg in locked_features:
        locked_features[arg] = False
        await update_chat_settings(chat_id, "locked", locked_features)
        await update.message.reply_text(f"🔓 `{arg.capitalize()}` 𝐤𝐡𝐮𝐥 𝐠𝐚𝐢𝐥\. 𝐀𝐚𝐳𝐚𝐝𝐢, 𝐘𝐚𝐫\! ✨ 𝐉𝐢𝐲𝐨 𝐚𝐮𝐫 𝐣𝐢𝐧𝐞 𝐝𝐨\! 🕊️ _\(Ab jashn manaao!\)_", parse_mode="MarkdownV2")
    elif arg == "all":
        for key in locked_features:
            locked_features[key] = False
        await update_chat_settings(chat_id, "locked", locked_features)
        await update.message.reply_text("🔓 𝐒𝐚𝐛 𝐤𝐮𝐜𝐡 𝐤𝐡𝐮𝐥 𝐠𝐚𝐢𝐥\. 𝐀𝐛 𝐜𝐡𝐚𝐦𝐤𝐨, 𝐡𝐨\! 💖 𝐏𝐚𝐫𝐭𝐲 𝐡𝐨 𝐣𝐚𝐲𝐞\! 🥳 _\(Full on masti!\)_")
    else:
        await update.message.reply_text("🤦‍♀️ 𝐆𝐚𝐥𝐚𝐭 𝐛𝐚𝐚𝐭 𝐛𝐨𝐥𝐚𝐭 𝐡𝐨, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\. '`all`', '`links`', 𝐲𝐚 '`photos`' 𝐛𝐨𝐥 𝐧𝐚\. 🎀 _\(Seedha seedha bolo na!\)_", parse_mode="MarkdownV2")

# --- Spam Filter Commands ---
async def banlink_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    banlink_enabled = settings.get("banlink_enabled", True)

    if not context.args:
        await update.message.reply_text(f"🔗 𝐋𝐢𝐧𝐤 𝐟𝐢𝐥𝐭𝐞𝐫 𝐚𝐛𝐡𝐢 {'𝐜𝐡𝐚𝐥𝐮 𝐛𝐚' if banlink_enabled else '𝐛𝐚𝐧𝐝 𝐛𝐚'}\. 𝐂𝐡𝐚𝐥𝐮 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐥𝐢𝐲𝐞 '`/banlink on`' 𝐚𝐮𝐫 𝐛𝐚𝐧𝐝 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐥𝐢𝐲𝐞 '`/banlink off`' 𝐮𝐬𝐞 𝐤𝐚𝐫𝐨\. 💬 _\(Samajh lo, phir bolo!\)_", parse_mode="MarkdownV2")
        return
    
    state = context.args[0].lower()
    if state == "on":
        await update_chat_settings(chat_id, "banlink_enabled", True)
        await update.message.reply_text("✅ 𝐋𝐢𝐧𝐤 𝐟𝐢𝐥𝐭𝐞𝐫 𝐜𝐡𝐚𝐥𝐮 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐀𝐛 𝐤𝐨𝐢 𝐥𝐢𝐧𝐤 𝐧𝐚 𝐛𝐡𝐞𝐣𝐞𝐠𝐚\! 🚫 𝐒𝐚𝐟𝐚𝐢 𝐡𝐨 𝐠𝐚𝐢𝐥\! ✨ _\(No promotions allowed!\)_")
    elif state == "off":
        await update.message.reply_text("❌ 𝐋𝐢𝐧𝐤 𝐟𝐢𝐥𝐭𝐞𝐫 𝐛𝐚𝐧𝐝 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐀𝐛 𝐥𝐢𝐧𝐤 𝐛𝐡𝐞𝐣 𝐬𝐚𝐤𝐨 𝐡𝐨\! 🥳 𝐅𝐫𝐞𝐞𝐝𝐨𝐦\! 🔓 _\(Ab jo man kare, bhejo!\)_")
        await update_chat_settings(chat_id, "banlink_enabled", False)
    else:
        await update.message.reply_text("🤦‍♀️ 𝐆𝐚𝐥𝐚𝐭 𝐛𝐚𝐚𝐭 𝐛𝐨𝐥𝐚𝐭 𝐡𝐨, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\. '`on`' 𝐲𝐚 '`off`' 𝐛𝐨𝐥 𝐧𝐚\. 💅 _\(Kya yaar, itna bhi nahi pata?\)_", parse_mode="MarkdownV2")

async def blocklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    blocklist_words = set(settings.get("blocklist", [])) # Convert list from DB to set for operations

    if not context.args:
        if not blocklist_words:
            await update.message.reply_text("📝 𝐁𝐥𝐨𝐜𝐤𝐥𝐢𝐬𝐭 𝐚𝐛𝐡𝐢 𝐤𝐡𝐚𝐥𝐢 𝐛𝐚\. 𝐊𝐨𝐢 𝐬𝐡𝐚𝐛𝐝 𝐧𝐚𝐡𝐢 𝐛𝐚\! 🚫 _\(Sab saaf hai abhi!\)_")
        else:
            words = ", ".join(blocklist_words)
            await update.message.reply_text(f"📝 𝐁𝐥𝐨𝐜𝐤𝐥𝐢𝐬𝐭 𝐦𝐞𝐢𝐧 𝐲𝐞 𝐬𝐡𝐚𝐛𝐝 𝐡𝐚𝐢𝐧: `{words}`\. 𝐈𝐧𝐬𝐞 𝐝𝐮𝐫 𝐫𝐚𝐡𝐨\! ⚔️ _\(Bach ke rehna, babu!\)_", parse_mode="MarkdownV2")
        return

    action = context.args[0].lower()
    word = " ".join(context.args[1:]).lower()

    if action == "add":
        if word:
            blocklist_words.add(word)
            await update_chat_settings(chat_id, "blocklist", list(blocklist_words)) # Convert back to list for MongoDB
            await update.message.reply_text(f"✅ '`{word}`' 𝐛𝐥𝐨𝐜𝐤𝐥𝐢𝐬𝐭 𝐦𝐞𝐢𝐧 𝐝𝐚𝐥 𝐝𝐞𝐞𝐧𝐢\. 𝐀𝐛 𝐲𝐞 𝐬𝐡𝐚𝐛𝐝 𝐧𝐚 𝐜𝐡𝐚𝐥𝐞𝐠𝐚\! 🚫 _\(Ab dek देखते हैं कैसे बोलते हो!\)_", parse_mode="MarkdownV2")
        else:
            await update.message.reply_text("🤦‍♀️ 𝐊𝐚 𝐬𝐡𝐚𝐛𝐝 𝐝𝐚𝐚𝐥𝐞 𝐤𝐞 𝐛𝐚\? 𝐁𝐚𝐭𝐚𝐨 𝐧𝐚\! 💬 _\(Hawa me baat kar rahe ho kya?\)_")
    elif action == "remove":
        if word in blocklist_words:
            blocklist_words.remove(word)
            await update_chat_settings(chat_id, "blocklist", list(blocklist_words)) # Convert back to list for MongoDB
            await update.message.reply_text(f"✅ '`{word}`' 𝐛𝐥𝐨𝐜𝐤𝐥𝐢𝐬𝐭 𝐬𝐞 𝐡𝐚𝐭𝐚 𝐝𝐞𝐞𝐧𝐢\. 𝐀𝐛 𝐲𝐞 𝐬𝐡𝐚𝐛𝐝 𝐜𝐡𝐚𝐥 𝐬𝐚𝐤𝐭𝐚 𝐡𝐚\! 🥳 _\(Chalo, ek aur chance!\)_", parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(f"❌ '`{word}`' 𝐛𝐥𝐨𝐜𝐤𝐥𝐢𝐬𝐭 𝐦𝐞𝐢𝐧 𝐧𝐚𝐡𝐢 𝐛𝐚\. 𝐊𝐚𝐚𝐡𝐞 𝐡𝐚𝐭𝐚𝐞𝐛𝐚\? 🤔 _\(Jo hai hi nahi, use kaise hataoge?\)_", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("🤦‍♀️ 𝐆𝐚𝐥𝐚𝐭 𝐤𝐚𝐦𝐚𝐧𝐝 𝐛𝐚, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\. '`add`' 𝐲𝐚 '`remove`' 𝐮𝐬𝐞 𝐤𝐚𝐫𝐨\. 💅 _\(Seekh ke aao, phir baat karna!\)_", parse_mode="MarkdownV2")

async def blocklist_mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    blocklist_mode = settings.get("blocklist_mode", "mute")

    if not context.args:
        await update.message.reply_text(f"⚔️ 𝐁𝐥𝐨𝐜𝐤𝐥𝐢𝐬𝐭 𝐦𝐨𝐝𝐞 𝐚𝐛𝐡𝐢 '`{blocklist_mode}`' 𝐛𝐚\. '`mute`' 𝐲𝐚 '`ban`' 𝐬𝐞 𝐛𝐚𝐝𝐥𝐨\. 💬 _\(Kya chahiye, saza ya chup!\)_", parse_mode="MarkdownV2")
        return
    
    mode = context.args[0].lower()
    if mode in ["mute", "ban"]:
        await update_chat_settings(chat_id, "blocklist_mode", mode)
        await update.message.reply_text(f"✅ 𝐁𝐥𝐨𝐜𝐤𝐥𝐢𝐬𝐭 𝐦𝐨𝐝𝐞 '`{mode}`' 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐀𝐛 𝐝𝐞𝐤𝐡𝐚 𝐤𝐚 𝐡𝐨𝐭𝐚 𝐡𝐚𝐢\! 💥 _\(Ab toh game shuru hoga!\)_", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("🤦‍♀️ 𝐆𝐚𝐥𝐚𝐭 𝐦𝐨𝐝𝐞 𝐛𝐨𝐥𝐚𝐭 𝐡𝐨, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\. '`mute`' 𝐲𝐚 '`ban`' 𝐛𝐨𝐥 𝐧𝐚\. 💅 _\(Confused ho kya?\)_", parse_mode="MarkdownV2")

# --- Welcome System Commands ---
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    welcome_enabled = settings.get("welcome_enabled", True)

    if not context.args:
        await update.message.reply_text(f"👋 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐚𝐛𝐡𝐢 {'𝐜𝐡𝐚𝐥𝐮 𝐛𝐚' if welcome_enabled else '𝐛𝐚𝐧𝐝 𝐛𝐚'}\. 𝐂𝐡𝐚𝐥𝐮 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐥𝐢𝐲𝐞 '`/welcome on`' 𝐚𝐮𝐫 𝐛𝐚𝐧𝐝 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐥𝐢𝐲𝐞 '`/welcome off`' 𝐮𝐬𝐞 𝐤𝐚𝐫𝐨\. 💬 _\(Samajh lo, phir bolo!\)_", parse_mode="MarkdownV2")
        return
    
    state = context.args[0].lower()
    if state == "on":
        await update_chat_settings(chat_id, "welcome_enabled", True)
        await update.message.reply_text("✅ 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐜𝐡𝐚𝐥𝐮 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐀𝐛 𝐬𝐚𝐛𝐤𝐨 𝐬𝐰𝐚𝐠𝐚𝐭 𝐦𝐢𝐥𝐞𝐠𝐚\! 🥳 _\(Party shuru!\)_")
    elif state == "off":
        await update_chat_settings(chat_id, "welcome_enabled", False)
        await update.message.reply_text("❌ 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐛𝐚𝐧𝐝 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐀𝐛 𝐬𝐡𝐚𝐧𝐭𝐢 𝐫𝐚𝐡𝐞𝐠𝐢\. 🤫 _\(No entry, no exit!\)_")
    else:
        await update.message.reply_text("🤦‍♀️ 𝐆𝐚𝐥𝐚𝐭 𝐛𝐚𝐚𝐭 𝐛𝐨𝐥𝐚𝐭 𝐡𝐨, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\. '`on`' 𝐲𝐚 '`off`' 𝐛𝐨𝐥 𝐧𝐚\. 💅 _\(Arey, simple hai!\)_", parse_mode="MarkdownV2")

async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    welcome_msg = settings.get("welcome_msg", "👋 𝐖𝐞𝐥𝐜𝐨𝐦𝐞\! 𝐌𝐚𝐬𝐭𝐢 𝐤𝐚𝐫𝐨, 𝐣𝐞𝐞\! 🥳")

    if context.args:
        new_welcome_msg = " ".join(context.args)
        await update_chat_settings(chat_id, "welcome_msg", new_welcome_msg)
        await update.message.reply_text(f"✅ 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐛𝐚𝐝𝐚𝐥 𝐝𝐞𝐞𝐧𝐢: '`{new_welcome_msg}`'\. 𝐍𝐚𝐲𝐚 𝐬𝐚𝐧𝐝𝐞𝐬𝐡\! ✨ _\(Ab har koi impress hoga!\)_", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text(f"👋 𝐀𝐛𝐡𝐢 𝐤𝐞 𝐰𝐞𝐥𝐜𝐨𝐦𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐡𝐚𝐢: '`{welcome_msg}`'\. 𝐍𝐚𝐲𝐚 𝐤𝐚 𝐥𝐢𝐤𝐡𝐚𝐢\? ✍️ _\(Kuch naya socho!\)_", parse_mode="MarkdownV2")

async def cleanwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    await update_chat_settings(chat_id, "welcome_msg", "👋 𝐖𝐞𝐥𝐜𝐨𝐦𝐞\! 𝐌𝐚𝐬𝐭𝐢 𝐤𝐚𝐫𝐨, 𝐣𝐞𝐞\! 🥳")
    await update.message.reply_text("✅ 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐬𝐚𝐚𝐟 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐃𝐞𝐟𝐚𝐮𝐥𝐭 𝐩𝐚𝐫 𝐚𝐚 𝐠𝐚𝐢𝐥𝐚\! 🗑️ _\(Back to zero!\)_")

async def set_welcome_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    if context.args:
        new_sticker_id = context.args[0]
        await update_chat_settings(chat_id, "join_sticker_id", new_sticker_id)
        await update.message.reply_text(f"✅ 𝐍𝐚𝐲𝐚 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐒𝐭𝐢𝐜𝐤𝐞𝐫 𝐈𝐃 𝐬𝐞𝐭 𝐤𝐚𝐫 𝐝𝐞𝐞𝐧𝐢: '`{new_sticker_id}`'\. 💖 𝐌𝐚𝐣𝐚 𝐤𝐚𝐫𝐨\! 🎉 _\(Ab entry bohot stylish hogi!\)_", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("𝐊𝐫𝐢𝐩𝐲𝐚 𝐬𝐭𝐢𝐜𝐤𝐞𝐫 𝐈𝐃 𝐝𝐞𝐢𝐧 𝐣𝐢𝐬𝐞 𝐰𝐞𝐥𝐜𝐨𝐦𝐞 𝐬𝐭𝐢𝐜𝐤𝐞𝐫 𝐤𝐞 𝐫𝐮𝐩 𝐦𝐞𝐢𝐧 𝐬𝐞𝐭 𝐤𝐚𝐫𝐧𝐚 𝐡𝐚𝐢\. 💖 _\(Dedo na yaar, kaunsa mushkil hai!\)_")

async def set_leave_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    if context.args:
        new_sticker_id = context.args[0]
        await update_chat_settings(chat_id, "leave_sticker_id", new_sticker_id)
        await update.message.reply_text(f"✅ 𝐍𝐚𝐲𝐚 𝐋𝐞𝐚𝐯𝐞 𝐒𝐭𝐢𝐜𝐤𝐞𝐫 𝐈𝐃 𝐬𝐞𝐭 𝐤𝐚𝐫 𝐝𝐞𝐞𝐧𝐢: '`{new_sticker_id}`'\. 💔 𝐀𝐛 𝐣𝐚𝐨\! 🚪 _\(Alvida, phir milenge!\)_", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("𝐊𝐫𝐢𝐩𝐲𝐚 𝐬𝐭𝐢𝐜𝐤𝐞𝐫 𝐈𝐃 𝐝𝐞𝐢𝐧 𝐣𝐢𝐬𝐞 𝐥𝐞𝐚𝐯𝐞 𝐬𝐭𝐢𝐜𝐤𝐞𝐫 𝐤𝐞 𝐫𝐮𝐩 𝐦𝐞𝐢𝐧 𝐬𝐞𝐭 𝐤𝐚𝐫𝐧𝐚 𝐡𝐚𝐢\. 💔 _\(Chalo, jaldi karo!\)_")

# --- Rules System Commands ---
async def setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    rules_msg = settings.get("rules_msg", "📜 𝐁𝐞 𝐫𝐞𝐬𝐩𝐞𝐜𝐭𝐟𝐮𝐥\. 𝐍𝐨 𝐬𝐩𝐚𝐦\. 𝐉𝐢𝐲𝐨 𝐚𝐮𝐫 𝐣𝐢𝐧𝐞 𝐝𝐨\! ✨")

    if context.args:
        new_rules_msg = " ".join(context.args)
        await update_chat_settings(chat_id, "rules_msg", new_rules_msg)
        await update.message.reply_text(f"✅ 𝐍𝐢𝐲𝐚𝐦 𝐛𝐚𝐝𝐚𝐥 𝐝𝐞𝐞𝐧𝐢: '`{new_rules_msg}`'\. 𝐍𝐚𝐲𝐚 𝐧𝐢𝐲𝐚𝐦 𝐚𝐛 𝐥𝐚𝐚𝐠𝐮 𝐡𝐨𝐠𝐚\! 📜 _\(Ab toh follow karna padega!\)_", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text(f"📜 𝐀𝐛𝐡𝐢 𝐤𝐞 𝐧𝐢𝐲𝐚𝐦 𝐡𝐚𝐢: '`{rules_msg}`'\. 𝐍𝐚𝐲𝐚 𝐤𝐚 𝐥𝐢𝐤𝐡𝐚𝐢\? ✍️ _\(Kuch aur add karna hai kya?\)_", parse_mode="MarkdownV2")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Anyone can see the rules
    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    rules_msg = settings.get("rules_msg", "📜 𝐁𝐞 𝐫𝐞𝐬𝐩𝐞𝐜𝐭𝐟𝐮𝐥\. 𝐍𝐨 𝐬𝐩𝐚𝐦\. 𝐉𝐢𝐲𝐨 𝐚𝐮𝐫 𝐣𝐢𝐧𝐞 𝐝𝐨\! ✨")
    await update.message.reply_text(f"📜 𝐇𝐮𝐦𝐫𝐚 𝐠𝐫𝐨𝐮𝐩𝐰𝐚 𝐤𝐞 𝐧𝐢𝐲𝐚𝐦 𝐲𝐞 𝐛𝐚:\n\n'`{rules_msg}`'\n\n𝐒𝐚𝐦𝐚𝐣𝐡 𝐤𝐞 𝐫𝐚𝐡𝐨, 𝐘𝐚𝐫\! ⚖️ _\(Todne ki sochna bhi mat!\)_", parse_mode="MarkdownV2")

async def cleanrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    await update_chat_settings(chat_id, "rules_msg", "📜 𝐁𝐞 𝐫𝐞𝐬𝐩𝐞𝐜𝐭𝐟𝐮𝐥\. 𝐍𝐨 𝐬𝐩𝐚𝐦\. 𝐉𝐢𝐲𝐨 𝐚𝐮𝐫 𝐣𝐢𝐧𝐞 𝐝𝐨\! ✨")
    await update.message.reply_text("✅ 𝐍𝐢𝐲𝐚𝐦 𝐬𝐚𝐚𝐟 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐃𝐞𝐟𝐚𝐮𝐥𝐭 𝐩𝐚𝐫 𝐚𝐚 𝐠𝐚𝐢𝐥𝐚\! 🧹 _\(Ab naye rules banao!\)_")

# --- Message Tool Commands ---
async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    if update.message.reply_to_message:
        try:
            await update.message.reply_to_message.pin()
            await update.message.reply_text("📌 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐩𝐢𝐧 𝐤𝐚𝐫 𝐝𝐞𝐞𝐧𝐢\. 𝐒𝐚𝐛𝐤𝐨 𝐝𝐢𝐤𝐡𝐞𝐠𝐚\! ⬆️ _\(Ab koi bahana nahi chalega!\)_")
        except Exception as e:
            await update.message.reply_text(f"𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐩𝐢𝐧 𝐧𝐚 𝐡𝐨 𝐩𝐚𝐲𝐚𝐥: `{e}` 😥 𝐊𝐮𝐜𝐡 𝐝𝐢𝐤𝐤𝐚𝐭 𝐛𝐚\! 😔 _\(Lagta hai network issue hai!\)_", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("💬 𝐊𝐞𝐤𝐚 𝐩𝐢𝐧 𝐤𝐚𝐫େ 𝐤𝐞 𝐛𝐚\? 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐩𝐚𝐫 𝐑𝐞𝐩𝐥𝐲 𝐤𝐚𝐫𝐨 𝐧𝐚\! 👀 _\(Kya yaar, itna bhi nahi pata?\)_")

async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    try:
        # Unpinning the latest pinned message in the chat
        await context.bot.unpin_chat_message(chat_id=update.effective_chat.id)
        await update.message.reply_text("📍 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐮𝐧𝐩𝐢𝐧 𝐤𝐚𝐫 𝐝𝐞𝐞𝐧𝐢\. 𝐀𝐛 𝐜𝐡𝐡𝐮𝐩 𝐣𝐚𝐲𝐞𝐠𝐚\! ⬇️ _\(Ab kaam ho gaya!\)_")
    except Exception as e:
        await update.message.reply_text(f"𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐮𝐧𝐩𝐢𝐧 𝐧𝐚 𝐡𝐨 𝐩𝐚𝐲𝐚𝐥: `{e}` 😥 𝐊𝐮𝐜𝐡 𝐭𝐞𝐜𝐡𝐧𝐢𝐜𝐚𝐥 𝐢𝐬𝐬𝐮𝐞 𝐛𝐚\! 👨‍💻 _\(Thoda time lagega!\)_", parse_mode="MarkdownV2")

async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    if update.message.reply_to_message:
        try:
            await update.message.reply_to_message.delete()
            await update.message.delete() # Also delete the command message
            await update.message.reply_text("❌ 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭𝐚 𝐝𝐞𝐞𝐧𝐢\. 𝐒𝐚𝐚𝐟 𝐡𝐨 𝐠𝐚𝐢𝐥\! 🗑️ _\(Jaise kabhi tha hi nahi!\)_")
        except Exception as e:
            await update.message.reply_text(f"𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭𝐚𝐧𝐞 𝐦𝐞𝐢𝐧 𝐝𝐢𝐤𝐤𝐚𝐭: `{e}` 😥 𝐎𝐡 𝐧𝐨\! 😨 _\(Kuch toh gadbad hai!\)_", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("💬 𝐊𝐞𝐤𝐚 𝐦𝐢𝐭𝐚𝐞 𝐤𝐞 𝐛𝐚\? 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐩𝐚𝐫 𝐑𝐞𝐩𝐥𝐲 𝐤𝐚𝐫𝐨 𝐧𝐚\! 👀 _\(Are, jaldi karo na!\)_")

async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    if not update.message.reply_to_message and not context.args:
        await update.message.reply_text("𝐊𝐞𝐤𝐚𝐫𝐚 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭𝐚𝐧𝐞 𝐤𝐞 𝐛𝐚\? 𝐒𝐚𝐧𝐤𝐡𝐲𝐚 𝐛𝐚𝐭𝐚𝐨 𝐧𝐚 𝐲𝐚 𝐑𝐞𝐩𝐥𝐲 𝐤𝐚𝐫𝐨\! 🧹 _\(Itna bhi nahi pata!\)_")
        return

    chat_id = update.effective_chat.id
    messages_to_delete = []

    if update.message.reply_to_message:
        # If replying to a message, delete from the replied message up to the current command
        start_message_id = update.message.reply_to_message.message_id
        end_message_id = update.message.message_id
        # Iterate backwards from current message to replied message for deletion
        for i in range(end_message_id, start_message_id - 1, -1):
            messages_to_delete.append(i)
    elif context.args:
        try:
            num = int(context.args[0])
            # Delete 'num' messages including the purge command itself
            for i in range(num + 1):
                messages_to_delete.append(update.message.message_id - i)
        except ValueError:
            await update.message.reply_text("❌ 𝐒𝐚𝐡𝐢\-𝐬𝐚hi 𝐧𝐮𝐦𝐛𝐞𝐫𝐰𝐚 𝐝𝐚𝐚𝐥, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\. 💅 _\(Ab count karna padega kya?\)_")
            return
    else:
        # This case should ideally not be reached due to the initial check
        await update.message.reply_text("𝐊𝐞𝐤𝐚𝐫𝐚 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭𝐚𝐧𝐞 𝐤𝐞 𝐛𝐚\? 𝐒𝐚𝐧𝐤𝐡𝐲𝐚 𝐛𝐚𝐭𝐚𝐨 𝐧𝐚 𝐲𝐚 𝐑𝐞𝐩𝐥𝐲 𝐤𝐚𝐫𝐨\! 🧹 _\(Kya yaar, fir se!\)_")
        return

    await update.message.reply_text(f"🧹 `{len(messages_to_delete)}` 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭𝐚𝐧𝐚 𝐬𝐡𝐮𝐫𝐮 𝐡𝐨 𝐫𝐚𝐡𝐚 𝐡𝐚𝐢\.\.\. ✨ _\(Ab dekho magic!\)_", parse_mode="MarkdownV2")
    for msg_id in messages_to_delete:
        try:
            await context.bot.delete_message(chat_id, msg_id)
        except Exception as e:
            logger.warning(f"Could not delete message {msg_id}: {e}") # Log, but continue
    await update.message.reply_text("✅ 𝐒𝐚𝐛 𝐬𝐚𝐚𝐟 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐂𝐡𝐚𝐦𝐜𝐡𝐚𝐦𝐚𝐭𝐚\! 💖 𝐄𝐤 𝐝𝐚𝐦 𝐧𝐚𝐲𝐚\! 💫 _\(Ab group chamak raha hai!\)_")


async def cleanservice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only admins/owner can use this
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐀𝐝𝐦𝐢𝐧 𝐚𝐮𝐫 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    service_message_enabled = settings.get("service_message_enabled", True)

    if not context.args:
        await update.message.reply_text(f"🧹 𝐒𝐞𝐫𝐯𝐢𝐜𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐚𝐛𝐡𝐢 {'𝐜𝐡𝐚𝐥𝐮 𝐛𝐚' if service_message_enabled else '𝐛𝐚𝐧𝐝 𝐛𝐚'}\. '`on`' 𝐲𝐚 '`off`' 𝐬𝐞 𝐛𝐚𝐝𝐥𝐨\. 💬 _\(Tumhari marzi, meri marzi!\)_", parse_mode="MarkdownV2")
        return
    
    state = context.args[0].lower()
    if state == "on":
        await update_chat_settings(chat_id, "service_message_enabled", True)
        await update.message.reply_text("✅ 𝐒𝐞𝐫𝐯𝐢𝐜𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐬𝐚𝐚𝐟 𝐤𝐚𝐫𝐧𝐚 𝐜𝐡𝐚𝐥𝐮 𝐡𝐨 𝐠𝐚𝐢𝐥\. 🧹 𝐆𝐫𝐨𝐮𝐩 𝐬𝐚𝐚𝐟 𝐫𝐚𝐡𝐞𝐠𝐚\! ✨ _\(No extra baggage!\)_")
    elif state == "off":
        await update_chat_settings(chat_id, "service_message_enabled", False)
        await update.message.reply_text("❌ 𝐒𝐞𝐫𝐯𝐢𝐜𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐬𝐚𝐚𝐟 𝐤𝐚𝐫𝐧𝐚 𝐛𝐚𝐧𝐝 𝐡𝐨 𝐠𝐚𝐢𝐥\. 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐝𝐢𝐤𝐡𝐞𝐧𝐠𝐞\. 👁️ _\(Ab sab kuch dikhega!\)_")
    else:
        await update.message.reply_text("🤦‍♀️ 𝐆𝐚𝐥𝐚𝐭 𝐛𝐚𝐚𝐭 𝐛𝐨𝐥𝐚𝐭 𝐡𝐨, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\. '`on`' 𝐲𝐚 '`off`' 𝐛𝐨𝐥 𝐧𝐚\. 💅 _\(Seedha seedha bolo na!\)_", parse_mode="MarkdownV2")

# --- New Command: /id ---
async def get_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    response_text = (
        f"🆔 *𝐈𝐃 𝐝𝐞𝐤𝐡𝐨, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\!* 🆔\n\n"
        f"• ✨ *𝐆𝐫𝐨𝐮𝐩 𝐈𝐃:* `{chat_id}`\n"
        f"• 💖 *𝐓𝐨𝐡𝐚𝐫𝐚 𝐔𝐬𝐞𝐫 𝐈𝐃:* `{user_id}`\n\n"
        f"𝐄 𝐥𝐨, 𝐚𝐩𝐧𝐚 𝐩𝐚𝐡𝐜𝐡𝐚𝐧 𝐣𝐚𝐚𝐧 𝐥𝐢𝐲𝐨\! 😎 _\(Ab confusion nahi hoga!\)_"
    )
    await update.message.reply_text(response_text, parse_mode="MarkdownV2")

# --- New Command: /stickerid ---
async def get_sticker_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    
    response_text = (
        f"🖼️ *𝐒𝐭𝐢𝐜𝐤𝐞𝐫 𝐈𝐃𝐬 𝐝𝐞𝐤𝐡𝐚, 𝐘𝐚𝐫\!* 🖼️\n\n"
        f"• 💖 *𝐉𝐨𝐢𝐧 𝐒𝐭𝐢𝐜𝐤𝐞𝐫 𝐈𝐃:* `{settings.get('join_sticker_id', DEFAULT_JOIN_STICKER_ID)}`\n"
        f"• 💔 *𝐋𝐞𝐚𝐯𝐞 𝐒𝐭𝐢𝐜𝐤𝐞𝐫 𝐈𝐃:* `{settings.get('leave_sticker_id', DEFAULT_LEAVE_STICKER_ID)}`\n"
        f"• 🚀 *𝐒𝐭𝐚𝐫𝐭 𝐀𝐧𝐢𝐦𝐚𝐭𝐢𝐨𝐧 𝐒𝐭𝐢𝐜𝐤𝐞𝐫 𝐈𝐃:* `{settings.get('start_animation_sticker_id', DEFAULT_START_ANIMATION_STICKER_ID)}`\n"
        f"• 🎉 *𝐒𝐭𝐚𝐫𝐭 𝐅𝐢𝐧𝐚𝐥 𝐒𝐭𝐢𝐜𝐤𝐞𝐫 𝐈𝐃:* `{settings.get('start_final_sticker_id', DEFAULT_START_FINAL_STICKER_ID)}`\n\n"
        f"𝐄 𝐥𝐨, 𝐭𝐨𝐡𝐚𝐫𝐚 𝐩𝐚𝐬𝐚𝐧𝐝𝐢𝐝𝐚 𝐬𝐭𝐢𝐜𝐤𝐞𝐫 𝐤𝐢 𝐈𝐃𝐬\! ✨ _\(Ab toh sab clear hai!\)_"
    )
    await update.message.reply_text(response_text, parse_mode="MarkdownV2")

# --- New Command: /getstickerid (reply to a sticker) ---
async def get_sticker_id_from_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message and update.message.reply_to_message.sticker:
        sticker_id = update.message.reply_to_message.sticker.file_id
        await update.message.reply_text(f"🌠 𝐄 𝐬𝐭𝐢𝐜𝐤𝐞𝐫 𝐤𝐚 𝐈𝐃 𝐡𝐚𝐢: '`{sticker_id}`'\. 𝐀𝐛 𝐢𝐬𝐞 𝐮𝐬𝐞 𝐤𝐚𝐫𝐨, 𝐘𝐚𝐫\! ✨ _\(Jadui sticker mil gaya!\)_", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("🤦‍♀️ 𝐊𝐫𝐢𝐩𝐲𝐚 𝐤𝐢𝐬𝐢 𝐬𝐭𝐢𝐜𝐤𝐞𝐫 𝐩𝐚𝐫 𝐫𝐞𝐩𝐥𝐲 𝐤𝐚𝐫େ𝐢𝐧 𝐈𝐃 𝐩𝐚𝐚𝐧𝐞 𝐤𝐞 𝐥𝐢𝐲𝐞\. 💌 _\(Arey, reply karna bhool gaye kya?\)_")


# --- New Member Handler ---
async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    
    if not settings.get("welcome_enabled", True):
        return
        
    for user in update.message.new_chat_members:
        # ** Send Join Sticker **
        join_sticker = settings.get("join_sticker_id", DEFAULT_JOIN_STICKER_ID)
        if join_sticker:
            try:
                await context.bot.send_sticker(chat_id=chat_id, sticker=join_sticker)
            except Exception as e:
                logger.error(f"Error sending join sticker: {e}")

        # ** Dynamic Welcome Animation (Bihari Tone) **
        intro_messages = [
            f"💖 𝐀𝐚𝐡 𝐠𝐚𝐢𝐥𝐚 𝐭𝐮, 💎 {user.mention_html()}\! 💖",
            "✨ 𝐇𝐚𝐦𝐫𝐚 𝐞 𝐠𝐫𝐨𝐮𝐩𝐰𝐚 𝐦𝐞𝐢𝐧 𝐭𝐨𝐡𝐚𝐫𝐚 𝐬𝐰𝐚𝐠𝐚𝐭 𝐛𝐚, 𝐑𝐚𝐣𝐚\! ✨",
            "🌸 𝐌𝐢𝐥𝐤𝐞 𝐝𝐡𝐚𝐦𝐚𝐚𝐥 𝐦𝐚𝐜𝐡𝐚𝐰𝐞 𝐤𝐞 𝐛𝐚\! 🥳",
            "💅 𝐓𝐚𝐢𝐲𝐚𝐫 𝐡𝐨 𝐣𝐚, 𝐦𝐚𝐬𝐭𝐢 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐛𝐚\! 😎",
            "💋 𝐏𝐲𝐚𝐚𝐫 𝐚𝐮𝐫 𝐦𝐚𝐮𝐣 𝐦𝐚𝐬𝐭𝐢 𝐜𝐡𝐚𝐡𝐢𝐲𝐞, 𝐘𝐚𝐫\! 🍫",
            "🎀 𝐁𝐚𝐡𝐮𝐭 𝐤𝐡𝐮𝐬𝐡 𝐡𝐚𝐢𝐧 𝐤𝐢 𝐭𝐮 𝐚𝐚𝐲𝐚𝐥 𝐡𝐨, 𝐉𝐚𝐚𝐧𝐚\! 💯",
            "🌟 𝐀𝐛 𝐜𝐡𝐚𝐦𝐚𝐤𝐧𝐞 𝐤𝐞 𝐛𝐚𝐚𝐫𝐢 𝐭𝐨𝐡𝐚𝐫𝐚 𝐛𝐚\! 💫",
            "🎉 𝐏𝐚𝐫𝐭𝐲 𝐬𝐡𝐮𝐫𝐮 𝐡𝐨𝐭𝐚𝐚, 𝐝𝐞𝐫 𝐤𝐚𝐡𝐞 𝐤𝐞\? 🎶"
        ]

        # Front lining animation
        front_line_msg = await update.message.reply_text("💖 𝐒𝐰𝐚𝐠𝐚𝐭 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐢𝐧𝐭𝐳𝐚𝐚𝐦 𝐜𝐡𝐚𝐥 𝐫𝐚𝐡𝐚 𝐡𝐚𝐢\.\.\. 🚀")
        for i, msg_text in enumerate(intro_messages):
            await front_line_msg.edit_text(msg_text, parse_mode="HTML") # HTML for user.mention_html()
            await asyncio.sleep(0.3) # Slightly increased sleep for better animation
        await asyncio.sleep(0.7)
        await front_line_msg.delete()
        
        # Original welcome text after animation
        username = f"@{user.username}" if user.username else user.full_name
        join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        welcome_msg_text = settings.get("welcome_msg", "👋 𝐖𝐞𝐥𝐜𝐨𝐦𝐞\! 𝐌𝐚𝐬𝐭𝐢 𝐤𝐚𝐫𝐨, 𝐣𝐞𝐞\! 🥳")
        
        final_welcome_caption = (
            f"👑 *𝐀𝐚𝐡 𝐆𝐚𝐢𝐥𝐚 𝐭𝐮, {user.full_name} 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\!* 👑\n\n"
            f"• ✨ *𝐍𝐚𝐚𝐦:* `{user.full_name}`\n"
            f"• 🎀 *𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞𝐰𝐚:* `{username}`\n"
            f"• 💖 *𝐔𝐬𝐞𝐫 𝐈𝐃:* `{user.id}`\n"
            f"• 🌸 *𝐊𝐚𝐛 𝐬𝐞 𝐚𝐚𝐲𝐚𝐥 𝐡𝐚:* `{join_date}`\n\n"
            f"✨ {welcome_msg_text} 𝐍𝐢𝐲𝐚𝐦𝐰𝐚 𝐩𝐚𝐝𝐡 𝐥𝐢𝐲𝐨 /rules, 𝐚𝐮𝐫 𝐤𝐡𝐨𝐨𝐛 𝐜𝐡𝐚𝐦𝐤𝐨, 𝐘𝐚𝐫\! 🌟 𝐌𝐚𝐬𝐭𝐢 𝐤𝐚𝐫𝐨\! 😄 _\(Ab toh full on mazza aayega!\)_"
        )
        
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            photo_file = photos.photos[0][0]
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo_file.file_id,
                caption=final_welcome_caption,
                parse_mode="MarkdownV2"
            )
        else:
            await update.message.reply_text(final_welcome_caption, parse_mode="MarkdownV2")

# --- Left Member Handler ---
async def left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    
    user = update.message.left_chat_member
    username = f"@{user.username}" if user.username else user.full_name
    left_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ** Send Leave Sticker **
    leave_sticker = settings.get("leave_sticker_id", DEFAULT_LEAVE_STICKER_ID)
    if leave_sticker:
        try:
            await context.bot.send_sticker(chat_id=chat_id, sticker=leave_sticker)
        except Exception as e:
            logger.error(f"Error sending leave sticker: {e}")
    
    left_text = (
        f"💔 *𝐀𝐫𝐫𝐞 𝐫𝐞, 𝐞𝐤 𝐝𝐢𝐥 𝐭𝐨𝐝 𝐤𝐞 𝐜𝐡𝐚𝐥 𝐠𝐚𝐢𝐥\.\.\.* 😭\n\n"
        f"• 👤 *𝐍𝐚𝐚𝐦:* {user.full_name}\n"
        f"• 🎀 *𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞𝐰𝐚:* {username}\n"
        f"• 💖 *𝐔𝐬𝐞𝐫 𝐈𝐃:* `{user.id}`\n"
        f"• 🌸 *𝐊𝐚𝐛 𝐠𝐚𝐢𝐥𝐚:* {left_date}\n\n"
        f"𝐓𝐨𝐡𝐚𝐫𝐚 𝐤𝐚𝐦𝐢 𝐤𝐡𝐚𝐥𝐞𝐠𝐚, 𝐘𝐚𝐫\! ✨ 𝐉𝐚𝐥𝐝𝐢 𝐰𝐚𝐩𝐚𝐬 𝐚𝐚𝐢𝐲𝐨\! 🌈 𝐌𝐢𝐬𝐬 𝐲𝐨𝐮\! 🥺 _\(Yaad aayegi tumhari!\)_"
    )
    
    await update.message.reply_text(left_text, parse_mode="MarkdownV2")

# --- Auto Link Filter Handler ---
async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    settings = await get_chat_settings(chat_id)
    
    banlink_enabled = settings.get("banlink_enabled", True)
    blocklist_words = set(settings.get("blocklist", []))
    blocklist_mode = settings.get("blocklist_mode", "mute")

    # Check if the sender is an admin or the bot owner
    is_sender_admin = await is_admin_or_owner(update, context)

    # Link Filter
    if update.message.text and (update.message.parse_entities(types="url") or update.message.parse_entities(types="text_link")):
        if banlink_enabled:
            if not is_sender_admin: # Only delete if sender is NOT an admin/owner
                try:
                    await update.message.delete()
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="🚫 𝐘𝐚𝐫, 𝐞 𝐠𝐫𝐨𝐮𝐩𝐰𝐚 𝐦𝐞𝐢𝐧 𝐥𝐢𝐧𝐤 𝐛𝐡𝐞𝐣𝐧𝐚 𝐦𝐚𝐧𝐚 𝐛𝐚\! 𝐑𝐮𝐥𝐞𝐬 𝐟𝐨𝐥𝐥𝐨𝐰 𝐤𝐚𝐫𝐨, 𝐣𝐞𝐞\! 😠 _\(Zyaada chalaki nahi!\)_"
                    )
                except Exception as e:
                    logger.error(f"Error deleting link message: {e}")
            else:
                logger.info(f"Admin/Owner {user.id} posted a link, not deleting.") # Log that an admin posted a link
    
    # Blocklist filter
    if update.message.text:
        text = update.message.text.lower()
        for word in blocklist_words:
            if word in text:
                if not is_sender_admin: # Only act if sender is NOT an admin/owner
                    try:
                        if blocklist_mode == "mute":
                            until_date = int(time.time()) + 3600
                            perms = ChatPermissions(can_send_messages=False)
                            await context.bot.restrict_chat_member(chat_id, update.effective_user.id, permissions=perms, until_date=until_date)
                            await update.message.reply_text(f"🔇 𝐀𝐩𝐧𝐞 𝐠𝐚𝐥𝐚𝐭 𝐬𝐡𝐚𝐛𝐝 𝐛𝐨𝐥𝐚𝐥, 𝐢𝐬𝐥𝐢𝐲𝐞 𝟏 𝐠𝐡𝐚𝐧𝐭𝐚 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐜𝐡𝐮𝐩 𝐤𝐚𝐫𝐚 𝐝𝐞𝐞𝐧𝐢\. 🤫 𝐒𝐚𝐦𝐚𝐣𝐡 𝐤𝐞 𝐛𝐨𝐥𝐨\! 🤐 _\(Ab baatein band!\)_")
                        elif blocklist_mode == "ban":
                            await context.bot.ban_chat_member(chat_id, update.effective_user.id)
                            await update.message.reply_text(f"🚫 𝐀𝐩𝐧𝐞 𝐠𝐚𝐥𝐚𝐭 𝐬𝐡𝐚𝐛𝐝 𝐛𝐨𝐥𝐚𝐥, 𝐢𝐬𝐥𝐢𝐲𝐞 𝐧𝐢𝐤𝐚𝐥 𝐝𝐞𝐞𝐧𝐢\. 𝐂𝐡𝐚𝐥 𝐧𝐢𝐤𝐚𝐥\! 💔 👋 _\(Ab tumhara yahan kaam nahi!\)_")
                        await update.message.delete()
                    except Exception as e:
                        logger.error(f"Error handling blocklist: {e}")
                    break # Only act on the first blocked word found
                else:
                    logger.info(f"Admin/Owner {user.id} used a blocklisted word, not taking action.") # Log that an admin used a blocklisted word


async def fallback_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and "help" in update.message.text.lower():
        await help_cmd(update, context)

# --- Update Functionality ---
async def update_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only the bot's owner can use this command (check based on username)
    if update.effective_user.username != OWNER.lstrip('@'):
        await update.message.reply_text("🚨 𝐀𝐫𝐞 𝐛𝐚𝐛𝐮, 𝐞 𝐤𝐚𝐦𝐚𝐧𝐝 𝐭𝐨𝐡 𝐛𝐚𝐬 𝐌𝐚𝐥𝐢𝐤 \(𝐎𝐰𝐧𝐞𝐫\) 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐛𝐚\! 🚫 𝐓𝐮𝐦𝐡𝐚𝐫𝐞 𝐥𝐢𝐲𝐞 𝐧𝐚𝐡𝐢\! 🤷‍♀️ _\(Aukaat me raho!\)_")
        return

    await update.message.reply_text("🔄 𝐔𝐩𝐝𝐚𝐭𝐞 𝐬𝐡𝐮𝐫𝐮 𝐡𝐨 𝐫𝐚𝐡𝐚 𝐡𝐚𝐢\.\.\. 𝐆𝐢𝐭𝐇𝐮𝐛 𝐬𝐞 𝐧𝐚𝐲𝐚 𝐜𝐨𝐝𝐞 𝐤𝐡𝐞𝐞𝐧𝐜𝐡 𝐫𝐚𝐡𝐞 𝐡𝐚𝐢𝐧\! 🚀 𝐓𝐡𝐨𝐝𝐚 𝐬𝐚𝐛𝐚𝐫 𝐤𝐚𝐫𝐨\! ⏳ _\(Bada kaam ho raha hai!\)_")
    
    try:
        # PULL_COMMAND ko execute karein
        process = subprocess.run(
            ["git", "pull", UPSTREAM_REPO_URL], 
            cwd=REPO_DIR, # Bot ki directory mein command chalao
            capture_output=True, 
            text=True, 
            check=True
        )
        await update.message.reply_text(f"✅ 𝐔𝐩𝐝𝐚𝐭𝐞 𝐬𝐚𝐟𝐚𝐥 𝐡𝐨 𝐠𝐚𝐢𝐥\! 𝐒𝐚𝐛 𝐧𝐚𝐲𝐚 𝐜𝐨𝐝𝐞 𝐚𝐚 𝐠𝐚𝐢𝐥\! ✨\n\n`{process.stdout}`", parse_mode="MarkdownV2")
        await update.message.reply_text("🔄 𝐁𝐨𝐭 𝐚𝐛 𝐫𝐞𝐬𝐭𝐚𝐫𝐭 𝐡𝐨𝐠𝐚 𝐭𝐚𝐚𝐤𝐢 𝐧𝐚𝐲𝐚 𝐜𝐨𝐝𝐞 𝐜𝐡𝐚𝐥𝐮 𝐡𝐨 𝐬𝐚𝐤𝐞\. 𝐓𝐡𝐨𝐝𝐢 𝐝𝐞𝐫 𝐦𝐞𝐢𝐧 𝐰𝐚𝐩𝐚𝐬 𝐚𝐚 𝐣𝐚𝐚𝐞𝐧𝐠𝐞\! 💖 _\(Phir se aayenge, dhamaka karne!\)_")
        
        # Ek chhota delay takki message send ho sake, phir bot ko exit kar do
        await asyncio.sleep(2)
        sys.exit(0) # Bot ko exit kar dega, jisse system use restart kar sake

    except subprocess.CalledProcessError as e:
        await update.message.reply_text(f"❌ 𝐔𝐩𝐝𝐚𝐭𝐞 𝐧𝐚 𝐡𝐨 𝐩𝐚𝐲𝐚𝐥, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣\! 𝐊𝐮𝐜𝐡 𝐞𝐫𝐫𝐨𝐫 𝐛𝐚\! 💔\n\n`{e.stderr}`", parse_mode="MarkdownV2")
        logger.error(f"Git pull failed: {e.stderr}")
    except FileNotFoundError:
        await update.message.reply_text("❌ 𝐘𝐚𝐫, '`git`' 𝐜𝐨𝐦𝐦𝐚𝐧𝐝 𝐧𝐚𝐡𝐢 𝐦𝐢𝐥𝐚\! 𝐒𝐞𝐫𝐯𝐞𝐫 𝐩𝐚𝐫 '`git`' 𝐢𝐧𝐬𝐭𝐚𝐥𝐥 𝐤𝐚𝐫𝐨 𝐧𝐚\! 🤦‍♀️ _\(Pehle tools theek karo!\)_", parse_mode="MarkdownV2")
    except Exception as e:
        await update.message.reply_text(f"❌ 𝐊𝐮𝐜𝐡 𝐚𝐮𝐫 𝐠𝐚𝐝𝐛𝐚𝐝 𝐡𝐨 𝐠𝐚𝐢𝐥: `{e}` 😥 𝐏𝐚𝐫𝐞𝐬𝐡𝐚𝐧𝐢 𝐡𝐚𝐢\! 😔 _\(Kismat hi kharab hai lagta hai!\)_", parse_mode="MarkdownV2")


# --- Main function to set up the bot ---
async def main():
    # Setup MongoDB connection at the start
    setup_mongodb()

    # Build the application
    app = ApplicationBuilder().token(TOKEN).build()

    # General commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ROSE", ROSE))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("donate", donate))
    app.add_handler(CommandHandler("id", get_ids))
    app.add_handler(CommandHandler("stickerid", get_sticker_ids))
    app.add_handler(CommandHandler("getstickerid", get_sticker_id_from_reply, filters=filters.REPLY))
    app.add_handler(CommandHandler("update", update_bot)) # No filters here, restriction is inside the function

    # Member join/leave handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, left_member))

    # Moderation commands - now admin restricted
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("resetwarns", resetwarns))
    app.add_handler(CommandHandler("setwarnlimit", setwarnlimit))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("kick", kick_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))

    # Admin commands - now admin restricted (except for /admins itself)
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))
    app.add_handler(CommandHandler("admins", list_admins)) # This one remains publicly accessible to list admins

    # Lock system commands - now admin restricted
    app.add_handler(CommandHandler("lock", lock))
    app.add_handler(CommandHandler("unlock", unlock))

    # Spam filter commands - now admin restricted
    app.add_handler(CommandHandler("banlink", banlink_toggle))
    app.add_handler(CommandHandler("blocklist", blocklist_cmd)) 
    app.add_handler(CommandHandler("blocklistmode", blocklist_mode_cmd)) 

    # Welcome system commands - now admin restricted
    app.add_handler(CommandHandler("welcome", welcome))
    app.add_handler(CommandHandler("setwelcome", setwelcome))
    app.add_handler(CommandHandler("cleanwelcome", cleanwelcome))
    app.add_handler(CommandHandler("setwelcomesticker", set_welcome_sticker))
    app.add_handler(CommandHandler("setleavesticker", set_leave_sticker))

    # Rules system commands - now admin restricted (except for /rules itself)
    app.add_handler(CommandHandler("setrules", setrules))
    app.add_handler(CommandHandler("rules", rules)) # This one remains publicly accessible to view rules
    app.add_handler(CommandHandler("cleanrules", cleanrules))

    # Message tool commands - now admin restricted
    app.add_handler(CommandHandler("pin", pin))
    app.add_handler(CommandHandler("unpin", unpin))
    app.add_handler(CommandHandler("del", delete_message))
    app.add_handler(CommandHandler("purge", purge))
    app.add_handler(CommandHandler("cleanservice", cleanservice))

    # Auto link filter and fallback help in group chats
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_links))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, fallback_help))
    
    # Run polling without closing the event loop.
    await app.run_polling(close_loop=False)

# --- Launcher ---
async def launch():
    try:
        await main()
    except Exception as e:
        print(f"Bot crashed: {e}", file=sys.stderr)

if __name__ == "__main__":
    try:
        # Check if an event loop is already running, if not, create a new one
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(main())
        except RuntimeError:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            new_loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot stopped by user.", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred during bot launch: {e}", file=sys.stderr)