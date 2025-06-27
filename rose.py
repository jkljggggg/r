# coding=utf-8
import nest_asyncio
nest_asyncio.apply()

import asyncio
import time
import sys
import logging
from datetime import datetime, timedelta
import subprocess # For executing shell commands (git pull)
import random # For dynamic welcome messages

# MongoDB
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Enable logging to see bot activities on console
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from telegram import Update, ChatPermissions, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from telegram.constants import ParseMode # Import ParseMode for Markdown V2

# --- Configuration ---
TOKEN = "8100559127:AAFyDgLMXb3kOEXgTXK2vLKUkN_Ix3vR9E"  # Replace with your actual token
OWNER = "@Rajaraj909" # Bot ka owner username (username, NOT ID)

# MongoDB Configuration
MONGO_URI = "mongodb+srv://pusers:nycreation@nycreation.pd4klp1.mongodb.net/?retryWrites=true&w=majority&appName=NYCREATION" # Replace with your MongoDB connection string (e.g., from Atlas)
DB_NAME = "RoseBotDB"

# ** Sticker IDs (Replace with your actual sticker file IDs) **
# IMPORTANT: Replace this with a valid sticker file ID. If not, sticker sending will fail.
DEFAULT_JOIN_STICKER_ID = "CAACAgIAAxkBAAIC3mWZ7WvQzQe5F2l3b3sQ2M1d4QABfQACaQMAAm2YgUrpL" # Placeholder, replace with a real sticker ID

# --- Database Setup ---
def get_db_collection(collection_name):
    """Initializes and returns a MongoDB collection."""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        return db[collection_name]
    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        return None
    except OperationFailure as e:
        logger.error(f"MongoDB operation failed: {e}")
        return None

# Collections
warns_collection = get_db_collection("warns")
rules_collection = get_db_collection("rules")
welcomes_collection = get_db_collection("welcomes")
global_bans_collection = get_db_collection("global_bans") # For global bans
chat_settings_collection = get_db_collection("chat_settings") # To store settings like autolink

# --- Utility Functions ---
def escape_markdown_v2(text):
    """Helper function to escape characters for MarkdownV2 parse mode."""
    if not isinstance(text, str):
        text = str(text)
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return "".join(["\\" + char if char in escape_chars else char for char in text])

async def is_admin_or_owner(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    """Checks if the user is an admin in the chat or the bot's owner."""
    if user_id == context.bot.id: # Bot itself is considered admin for its own actions
        return True

    # Check if the user is the bot's designated owner by username
    if update.effective_user.username and update.effective_user.username.lower() == OWNER.lstrip('@').lower():
        return True
    
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status in ["creator", "administrator"]:
            return True
    except Exception as e:
        logger.debug(f"Could not get chat member status for {user_id} in {chat_id}: {e}")
        # If bot can't get chat member (e.g., user left, or bot not admin), treat as not admin
        return False
    
    return False

async def _get_user_display_info(user) -> dict:
    """
    Fetches user's display name, username, and profile picture.
    Returns a dictionary with 'full_name', 'username', 'user_id', 'profile_pic_file_id'.
    """
    full_name = escape_markdown_v2(user.full_name)
    username = escape_markdown_v2(f"@{user.username}") if user.username else "_N/A_"
    user_id = user.id
    profile_pic_file_id = None

    try:
        photos = await user.get_profile_photos(limit=1)
        if photos.photos and photos.photos[0]:
            # Get the largest available photo size
            largest_photo = max(photos.photos[0], key=lambda p: p.width * p.height)
            profile_pic_file_id = largest_photo.file_id
    except Exception as e:
        logger.warning(f"Could not fetch profile picture for user {user.id}: {e}")
        # If fetching fails, we'll just proceed without the picture

    return {
        "full_name": full_name,
        "username": username,
        "user_id": user_id,
        "profile_pic_file_id": profile_pic_file_id
    }

# --- Bot Commands and Handlers ---

# START COMMAND
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    user_info = await _get_user_display_info(user)

    # Prepare user identity string
    identity_parts = []
    identity_parts.append(f"*नाम:* {user_info['full_name']}")
    identity_parts.append(f"*उपयोगकर्ता नाम:* {user_info['username']}")
    identity_parts.append(f"*उपयोगकर्ता ID:* `{user_info['user_id']}`")
    user_identity_str = escape_markdown_v2(" | ").join(identity_parts)

    if chat.type == "private":
        # Send profile picture first if available
        if user_info['profile_pic_file_id']:
            try:
                await update.message.reply_photo(
                    photo=user_info['profile_pic_file_id'],
                    caption=f"🌟 आप यहाँ हैं, एक चमकते सितारे की तरह!\n\n{user_identity_str}\n\n",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            except Exception as e:
                logger.error(f"Error sending profile picture for user {user.id}: {e}")
                # Fallback to just text if photo sending fails
                await update.message.reply_text(
                    f"🌟 आप यहाँ हैं, एक चमकते सितारे की तरह!\n\n{user_identity_str}\n\n",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
        else:
            await update.message.reply_text(
                f"🌟 आप यहाँ हैं, एक चमकते सितारे की तरह!\n\n{user_identity_str}\n\n",
                parse_mode=ParseMode.MARKDOWN_V2
            )

        await update.message.reply_text(
            f"मैं *रोज*, आपके चैट्स को सुरक्षित और व्यवस्थित रखने के लिए डिज़ाइन किया गया एक शक्तिशाली ग्रुप मैनेजमेंट बॉट हूँ!\n"
            f"मैं आपकी मदद कर सकता हूँ:\n"
            f"✨ मॉडरेटिंग टूल्स जैसे कि बैन, किक, म्यूट, वॉर्न\n"
            f"🔒 एंटी-स्पैम और एंटी-लिंक फीचर्स\n"
            f"⚙️ कस्टमाइजेबल वेलकम मैसेज और नियम\n"
            f"…और भी बहुत कुछ!\n\n"
            f"शुरू करने के लिए तैयार हैं? मुझे अपने ग्रुप में जोड़ें और मुझे एक एडमिन बनाएं!\n"
            f"सभी कमांड्स की सूची के लिए, /help टाइप करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        # Group chat response
        await update.message.reply_text(
            f"नमस्ते, *{escape_markdown_v2(user.first_name)}*! मैं यहाँ पहले से ही सक्रिय हूँ! 🎉\n"
            f"इस समूह के लिए मैं क्या कर सकता हूँ यह देखने के लिए /help टाइप करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# HELP COMMAND
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        help_text = (
            f"🌹 *रोज बॉट सहायता मेनू* 🌹\n\n"
            f"यहाँ उन कमांड्स की सूची दी गई है जिनका आप उपयोग कर सकते हैं:\n\n"
            f"*🛠️ एडमिन कमांड्स:*\n"
            f"  `/ban <reply or username>` \\- एक उपयोगकर्ता को समूह से बैन करें\\.\n"
            f"  `/kick <reply or username>` \\- एक उपयोगकर्ता को समूह से किक करें\\.\n"
            f"  `/mute <reply or username> [time]` \\- एक उपयोगकर्ता को अस्थायी या स्थायी रूप से म्यूट करें\\.\n"
            f"  `/unmute <reply or username>` \\- एक उपयोगकर्ता को अनम्यूट करें\\.\n"
            f"  `/warn <reply or username> [reason]` \\- एक उपयोगकर्ता को चेतावनी दें\\.\n"
            f"  `/warns <reply or username>` \\- एक उपयोगकर्ता की चेतावनियों की जाँच करें\\.\n"
            f"  `/resetwarns <reply or username>` \\- एक उपयोगकर्ता की चेतावनियों को रीसेट करें\\.\n"
            f"  `/pin` \\- रिप्लाई किए गए संदेश को पिन करें\\.\n"
            f"  `/unpin` \\- रिप्लाई किए गए संदेश को अनपिन करें\\.\n"
            f"  `/del` \\- रिप्लाई किए गए संदेश को हटाएँ\\.\n"
            f"  `/purge` \\- रिप्लाई किए गए संदेश से ऊपर के संदेशों को हटाएँ\\.\n"
            f"  `/setrules <text>` \\- समूह के नियम सेट करें\\.\n"
            f"  `/rules` \\- समूह के नियम प्राप्त करें\\.\n"
            f"  `/cleanrules` \\- समूह के नियम साफ करें\\.\n"
            f"  `/cleanservice` \\- सेवा संदेशों को हटाएँ \\(जैसे, सदस्य शामिल हुए/छोड़ गए\\)\\.\n"
            f"  `/autolink <on/off>` \\- ऑटो लिंक विलोपन को टॉगल करें\\.\n"
            f"  `/setwelcome <text>` \\- कस्टम स्वागत संदेश सेट करें \\(उपयोग करें `{{first}}`, `{{last}}`, `{{fullname}}`, `{{chatname}}`\\)\\.\n"
            f"  `/resetwelcome` \\- स्वागत संदेश को डिफ़ॉल्ट पर रीसेट करें\\.\n"
            f"  `/welcome` \\- स्वागत संदेश का परीक्षण करें\\.\n\n"
            f"*👑 केवल मालिक कमांड्स:*\n"
            f"  `/gban <reply or username>` \\- एक उपयोगकर्ता को वैश्विक रूप से बैन करें\\.\n"
            f"  `/ungban <reply or username>` \\- एक उपयोगकर्ता को वैश्विक रूप से अनबैन करें\\.\n"
            f"  `/gblacklist <id>` \\- एक उपयोगकर्ता को वैश्विक ब्लैकलिस्ट में जोड़ें\\.\n"
            f"  `/ungblacklist <id>` \\- एक उपयोगकर्ता को वैश्विक ब्लैकलिस्ट से हटाएँ\\.\n"
            f"  `/blacklist_list` \\- वैश्विक ब्लैकलिस्ट दिखाएँ\\.\n\n"
            f"*✨ सामान्य कमांड्स:*\n"
            f"  `/id` \\- अपनी उपयोगकर्ता ID या रिप्लाई किए गए उपयोगकर्ता की ID प्राप्त करें\\.\n"
            f"  `/chatid` \\- वर्तमान चैट की ID प्राप्त करें\\.\n"
            f"  `/info <reply or username>` \\- एक उपयोगकर्ता के बारे में जानकारी प्राप्त करें\\.\n"
            f"  `/about` \\- रोज बॉट के बारे में और जानें\\.\n"
            f"  `/ping` \\- बॉट की प्रतिक्रिया समय की जाँच करें\\.\n\n"
            f"अधिक सहायता चाहिए? हमारे [समर्थन समूह](https://t.me/{escape_markdown_v2('Rajaraj909')}) में शामिल हों! 💬\n\n" # Replace with your actual support group link
            f"🌸 रोज का उपयोग करने के लिए धन्यवाद! 🌸"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
    else:
        await update.message.reply_text(
            f"नमस्ते *{escape_markdown_v2(update.effective_user.first_name)}*! 👋\n\n"
            f"मैं स्पैम से बचने के लिए समूह चैट में पूर्ण सहायता मेनू नहीं भेज सकता हूँ.\n"
            f"सुविधाओं की पूरी सूची के लिए कृपया मेरे साथ एक निजी चैट खोलें और वहाँ /help कमांड का उपयोग करें!\n\n"
            f"मुझसे निजी चैट शुरू करने के लिए बस [यहां](https://t.me/{context.bot.username}) क्लिक करें.",
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )

# KICK COMMAND
async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"इस कमांड का उपयोग करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_chat_member = await context.bot.get_chat_member(chat.id, user_id)
            target_user = target_chat_member.user
        except ValueError:
            await update.message.reply_text(
                f"❌ किसी को किक करने के लिए कृपया एक वैध उपयोगकर्ता ID प्रदान करें या एक संदेश पर रिप्लाई करें.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ इस चैट में प्रदान की गई ID वाले उपयोगकर्ता को नहीं ढूँढा जा सका.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 किसी को किक करने के लिए, कृपया उनके संदेश पर रिप्लाई करें या उनकी उपयोगकर्ता ID प्रदान करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if target_user.id == user.id:
        await update.message.reply_text(
            f"😅 आप खुद को किक नहीं कर सकते, सिली!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if await is_admin_or_owner(update, context, chat.id, target_user.id):
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        if target_chat_member.status in ["creator", "administrator"] or \
           (target_user.username and target_user.username.lower() == OWNER.lstrip('@').lower()):
            await update.message.reply_text(
                f"🔒 मैं एक *एडमिन* या *बॉट मालिक* को किक नहीं कर सकता.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

    try:
        await context.bot.kick_chat_member(chat.id, target_user.id)
        await update.message.reply_text(
            f"👋 *{escape_markdown_v2(target_user.first_name)}* को समूह से किक कर दिया गया है!\n"
            f"_अलविदा_! 👋",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error kicking user {target_user.id}: {e}")
        await update.message.reply_text(
            f"⚠️ *{escape_markdown_v2(target_user.first_name)}* को किक करने में विफल रहा.\n"
            f"सुनिश्चित करें कि मेरे पास आवश्यक अनुमतियाँ हैं! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# BAN COMMAND
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"इस कमांड का उपयोग करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_chat_member = await context.bot.get_chat_member(chat.id, user_id)
            target_user = target_chat_member.user
        except ValueError:
            await update.message.reply_text(
                f"❌ किसी को बैन करने के लिए कृपया एक वैध उपयोगकर्ता ID प्रदान करें या एक संदेश पर रिप्लाई करें.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ इस चैट में प्रदान की गई ID वाले उपयोगकर्ता को नहीं ढूँढा जा सका.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 किसी को बैन करने के लिए, कृपया उनके संदेश पर रिप्लाई करें या उनकी उपयोगकर्ता ID प्रदान करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if target_user.id == user.id:
        await update.message.reply_text(
            f"😅 आप खुद को बैन नहीं कर सकते, सिली!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if await is_admin_or_owner(update, context, chat.id, target_user.id):
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        if target_chat_member.status in ["creator", "administrator"] or \
           (target_user.username and target_user.username.lower() == OWNER.lstrip('@').lower()):
            await update.message.reply_text(
                f"🔒 मैं एक *एडमिन* या *बॉट मालिक* को बैन नहीं कर सकता.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

    try:
        await context.bot.ban_chat_member(chat.id, target_user.id)
        await update.message.reply_text(
            f"⛓️ *{escape_markdown_v2(target_user.first_name)}* को समूह से बैन कर दिया गया है!\n"
            f"वे अब वापस नहीं आ सकते! 🚫",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error banning user {target_user.id}: {e}")
        await update.message.reply_text(
            f"⚠️ *{escape_markdown_v2(target_user.first_name)}* को बैन करने में विफल रहा.\n"
            f"सुनिश्चित करें कि मेरे पास आवश्यक अनुमतियाँ हैं! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# PIN COMMAND
async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"इस कमांड का उपयोग करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            f"📌 कृपया संदेश को पिन करने के लिए उस पर रिप्लाई करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        await context.bot.pin_chat_message(
            chat_id=chat.id,
            message_id=update.message.reply_to_message.message_id
        )
        await update.message.reply_text(
            f"📌 संदेश सफलतापूर्वक पिन हो गया! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error pinning message: {e}")
        await update.message.reply_text(
            f"⚠️ संदेश को पिन करने में विफल रहा.\n"
            f"सुनिश्चित करें कि मेरे पास आवश्यक अनुमतियाँ हैं! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# UNPIN COMMAND
async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"इस कमांड का उपयोग करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            f"📍 कृपया पिन किए गए संदेश को अनपिन करने के लिए उस पर रिप्लाई करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        await context.bot.unpin_chat_message(
            chat_id=chat.id,
            message_id=update.message.reply_to_message.message_id
        )
        await update.message.reply_text(
            f"📍 संदेश सफलतापूर्वक अनपिन हो गया! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error unpinning message: {e}")
        await update.message.reply_text(
            f"⚠️ संदेश को अनपिन करने में विफल रहा.\n"
            f"सुनिश्चित करें कि मेरे पास आवश्यक अनुमतियाँ हैं! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# DELETE MESSAGE COMMAND
async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"इस कमांड का उपयोग करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            f"🗑️ कृपया संदेश को हटाने के लिए उस पर रिप्लाई करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        await update.message.reply_to_message.delete()
        await update.message.delete() # Delete the command message as well
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        await update.message.reply_text(
            f"⚠️ संदेश को हटाने में विफल रहा.\n"
            f"सुनिश्चित करें कि मेरे पास आवश्यक अनुमतियाँ हैं! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# PURGE COMMAND
async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"इस कमांड का उपयोग करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            f"🧹 कृपया उस *पहले संदेश* पर रिप्लाई करें जहाँ से आप हटाना चाहते हैं.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    first_message_id = update.message.reply_to_message.message_id
    last_message_id = update.message.message_id
    messages_to_delete = []

    for msg_id in range(first_message_id, last_message_id + 1):
        messages_to_delete.append(msg_id)

    try:
        await context.bot.delete_messages(chat.id, messages_to_delete)
        # Inform about the purge (optional, can be deleted after a few seconds)
        purge_confirmation = await update.message.reply_text(
            f"🧹 *{len(messages_to_delete)}* संदेश सफलतापूर्वक हटा दिए गए! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await asyncio.sleep(3) # Delete confirmation after 3 seconds
        await purge_confirmation.delete()
    except Exception as e:
        logger.error(f"Error purging messages: {e}")
        await update.message.reply_text(
            f"⚠️ संदेशों को हटाने में विफल रहा.\n"
            f"सुनिश्चित करें कि मेरे पास आवश्यक अनुमतियाँ हैं! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# GET CHAT ID COMMAND
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"🆔 इस समूह के लिए चैट ID है: `{escape_markdown_v2(str(chat_id))}`\n"
        f"_यह ID कुछ बॉट कॉन्फ़िगरेशन के लिए उपयोगी है._",
        parse_mode=ParseMode.MARKDOWN_V2
    )

# WARN COMMAND
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"इस कमांड का उपयोग करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_chat_member = await context.bot.get_chat_member(chat.id, user_id)
            target_user = target_chat_member.user
        except ValueError:
            await update.message.reply_text(
                f"❌ किसी को चेतावनी देने के लिए कृपया एक वैध उपयोगकर्ता ID प्रदान करें या एक संदेश पर रिप्लाई करें.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ इस चैट में प्रदान की गई ID वाले उपयोगकर्ता को नहीं ढूँढा जा सका.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 किसी को चेतावनी देने के लिए, कृपया उनके संदेश पर रिप्लाई करें या उनकी उपयोगकर्ता ID प्रदान करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if target_user.id == user.id:
        await update.message.reply_text(
            f"😅 आप खुद को चेतावनी नहीं दे सकते, सिली!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if await is_admin_or_owner(update, context, chat.id, target_user.id):
        await update.message.reply_text(
            f"🔒 मैं एक *एडमिन* या *बॉट मालिक* को चेतावनी नहीं दे सकता.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "कोई कारण नहीं दिया गया"

    current_warns_data = warns_collection.find_one({"chat_id": chat.id, "user_id": target_user.id})
    warn_count = current_warns_data["warn_count"] + 1 if current_warns_data else 1
    
    warns_collection.update_one(
        {"chat_id": chat.id, "user_id": target_user.id},
        {"$set": {"warn_count": warn_count, "last_warn_reason": reason}},
        upsert=True
    )

    await update.message.reply_text(
        f"⚠️ *{escape_markdown_v2(target_user.first_name)}* को चेतावनी दी गई है! "
        f"वर्तमान चेतावनियाँ: `{warn_count}`.\n"
        f"कारण: _{escape_markdown_v2(reason)}_\n\n"
        f"🚨 बहुत अधिक चेतावनियाँ किक या बैन का कारण बन सकती हैं! कृपया सावधान रहें! 🚨",
        parse_mode=ParseMode.MARKDOWN_V2
    )

# UNWARN COMMAND
async def unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"इस कमांड का उपयोग करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_chat_member = await context.bot.get_chat_member(chat.id, user_id)
            target_user = target_chat_member.user
        except ValueError:
            await update.message.reply_text(
                f"❌ किसी को अनवॉर्न करने के लिए कृपया एक वैध उपयोगकर्ता ID प्रदान करें या एक संदेश पर रिप्लाई करें.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ इस चैट में प्रदान की गई ID वाले उपयोगकर्ता को नहीं ढूँढा जा सका.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 किसी को अनवॉर्न करने के लिए, कृपया उनके संदेश पर रिप्लाई करें या उनकी उपयोगकर्ता ID प्रदान करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if target_user.id == user.id:
        await update.message.reply_text(
            f"😅 आप खुद को अनवॉर्न नहीं कर सकते, सिली!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    result = warns_collection.delete_one({"chat_id": chat.id, "user_id": target_user.id})

    if result.deleted_count > 0:
        await update.message.reply_text(
            f"✅ *{escape_markdown_v2(target_user.first_name)}* की चेतावनियाँ साफ कर दी गई हैं! "
            f"वे अब एक साफ स्लेट पर हैं! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await update.message.reply_text(
            f"🤷‍♀️ *{escape_markdown_v2(target_user.first_name)}* के पास इस चैट में कोई सक्रिय चेतावनी नहीं है जिसे साफ किया जा सके.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# WARNS COMMAND
async def warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"इस कमांड का उपयोग करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_chat_member = await context.bot.get_chat_member(chat.id, user_id)
            target_user = target_chat_member.user
        except ValueError:
            await update.message.reply_text(
                f"❌ चेतावनियों की जाँच करने के लिए कृपया एक वैध उपयोगकर्ता ID प्रदान करें या एक संदेश पर रिप्लाई करें.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ इस चैट में प्रदान की गई ID वाले उपयोगकर्ता को नहीं ढूँढा जा सका.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 चेतावनियों की जाँच करने के लिए, कृपया उनके संदेश पर रिप्लाई करें या उनकी उपयोगकर्ता ID प्रदान करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    warn_data = warns_collection.find_one({"chat_id": chat.id, "user_id": target_user.id})

    if warn_data:
        warn_count = warn_data.get("warn_count", 0)
        last_reason = warn_data.get("last_warn_reason", "N/A")
        await update.message.reply_text(
            f"📊 *{escape_markdown_v2(target_user.first_name)}* के इस समूह में `{warn_count}` चेतावनियाँ हैं.\n"
            f"अंतिम कारण: _{escape_markdown_v2(last_reason)}_\n\n"
            f"_उनकी चेतावनियों को रीसेट करने के लिए, `/resetwarns` का उपयोग करें_",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await update.message.reply_text(
            f"✅ *{escape_markdown_v2(target_user.first_name)}* के इस समूह में कोई सक्रिय चेतावनी नहीं है!\n"
            f"_वे एक अच्छे सदस्य हैं_. 👍",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# MUTE COMMAND
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"इस कमांड का उपयोग करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_chat_member = await context.bot.get_chat_member(chat.id, user_id)
            target_user = target_chat_member.user
        except ValueError:
            await update.message.reply_text(
                f"❌ किसी को म्यूट करने के लिए कृपया एक वैध उपयोगकर्ता ID प्रदान करें या एक संदेश पर रिप्लाई करें.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ इस चैट में प्रदान की गई ID वाले उपयोगकर्ता को नहीं ढूँढा जा सका.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 किसी को म्यूट करने के लिए, कृपया उनके संदेश पर रिप्लाई करें या उनकी उपयोगकर्ता ID प्रदान करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if target_user.id == user.id:
        await update.message.reply_text(
            f"😅 आप खुद को म्यूट नहीं कर सकते, सिली!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if await is_admin_or_owner(update, context, chat.id, target_user.id):
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        if target_chat_member.status in ["creator", "administrator"] or \
           (target_user.username and target_user.username.lower() == OWNER.lstrip('@').lower()):
            await update.message.reply_text(
                f"🔒 मैं एक *एडमिन* या *बॉट मालिक* को म्यूट नहीं कर सकता.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

    mute_duration = None
    mute_duration_str = "स्थायी रूप से"
    if len(context.args) > 1:
        try:
            duration_str = context.args[1]
            if duration_str.endswith("m"):
                mute_duration = timedelta(minutes=int(duration_str[:-1]))
                mute_duration_str = f"{int(duration_str[:-1])} मिनट के लिए"
            elif duration_str.endswith("h"):
                mute_duration = timedelta(hours=int(duration_str[:-1]))
                mute_duration_str = f"{int(duration_str[:-1])} घंटे के लिए"
            elif duration_str.endswith("d"):
                mute_duration = timedelta(days=int(duration_str[:-1]))
                mute_duration_str = f"{int(duration_str[:-1])} दिनों के लिए"
            else:
                await update.message.reply_text(
                    f"❌ अमान्य म्यूट अवधि प्रारूप.\n"
                    f"मिनट के लिए `[संख्या]m`, घंटे के लिए `[संख्या]h`, या दिनों के लिए `[संख्या]d` का उपयोग करें.",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                return
        except ValueError:
            await update.message.reply_text(
                f"❌ अमान्य म्यूट अवधि मान.\n"
                f"मिनट के लिए `[संख्या]m`, घंटे के लिए `[संख्या]h`, या दिनों के लिए `[संख्या]d` का उपयोग करें.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

    permissions = ChatPermissions(can_send_messages=False)
    until_date = datetime.now() + mute_duration if mute_duration else None

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_user.id,
            permissions=permissions,
            until_date=until_date
        )
        await update.message.reply_text(
            f"🔇 *{escape_markdown_v2(target_user.first_name)}* को {escape_markdown_v2(mute_duration_str)} म्यूट कर दिया गया है! 🤫\n"
            f"_कुछ देर के लिए अब कोई बात नहीं_! 👋",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error muting user {target_user.id}: {e}")
        await update.message.reply_text(
            f"⚠️ *{escape_markdown_v2(target_user.first_name)}* को म्यूट करने में विफल रहा.\n"
            f"सुनिश्चित करें कि मेरे पास आवश्यक अनुमतियाँ हैं! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# UNMUTE COMMAND
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"इस कमांड का उपयोग करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_chat_member = await context.bot.get_chat_member(chat.id, user_id)
            target_user = target_chat_member.user
        except ValueError:
            await update.message.reply_text(
                f"❌ किसी को अनम्यूट करने के लिए कृपया एक वैध उपयोगकर्ता ID प्रदान करें या एक संदेश पर रिप्लाई करें.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ इस चैट में प्रदान की गई ID वाले उपयोगकर्ता को नहीं ढूँढा जा सका.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 किसी को अनम्यूट करने के लिए, कृपया उनके संदेश पर रिप्लाई करें या उनकी उपयोगकर्ता ID प्रदान करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if target_user.id == user.id:
        await update.message.reply_text(
            f"😅 यदि आप इस कमांड का उपयोग कर सकते हैं तो आप पहले से ही अनम्यूट हैं, सिली!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_audios=True,
        can_send_documents=True,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_change_info=False, # Admins only
        can_invite_users=True,
        can_pin_messages=False, # Admins only
        can_manage_topics=False # For forum groups, admins only
    )

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_user.id,
            permissions=permissions
        )
        await update.message.reply_text(
            f"🎤 *{escape_markdown_v2(target_user.first_name)}* को अनम्यूट कर दिया गया है! 🎉\n"
            f"_बातचीत में आपका स्वागत है_! 🤗",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error unmuting user {target_user.id}: {e}")
        await update.message.reply_text(
            f"⚠️ *{escape_markdown_v2(target_user.first_name)}* को अनम्यूट करने में विफल रहा.\n"
            f"सुनिश्चित करें कि मेरे पास आवश्यक अनुमतियाँ हैं! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# ABOUT COMMAND
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🌸 *रोज बॉट के बारे में* 🌸\n\n"
        f"मैं एक शक्तिशाली और बहुमुखी समूह प्रबंधन बॉट हूँ जिसे आपके टेलीग्राम समूहों को सुरक्षित, स्वच्छ और आकर्षक रखने में मदद करने के लिए डिज़ाइन किया गया है! ✨\n\n"
        f"**मुख्य विशेषताएं:**\n"
        f"  •  उन्नत मॉडरेशन उपकरण \\(किक, बैन, म्यूट, वॉर्न\\)\n"
        f"  •  कस्टमाइजेबल स्वागत संदेश और समूह नियम\n"
        f"  •  एंटी-स्पैम और एंटी-लिंक तंत्र\n"
        f"  •  लगातार समस्या पैदा करने वालों के लिए वैश्विक बैन प्रणाली\n"
        f"  •  और भी बहुत कुछ! 🚀\n\n"
        f"{OWNER} द्वारा ❤️ के साथ विकसित\n"
        f"संस्करण: `1.0.0`\n" # You can add a version number here
        f"अपडेट और चर्चा के लिए मेरे [समर्थन चैनल](https://t.me/{escape_markdown_v2('Rajaraj909')}) में शामिल हों! 📣", # Replace with your actual channel link
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True
    )

# PING COMMAND
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    ping_message = await update.message.reply_text(
        f"🏓 पोंग! विलंबता माप रहा है..",
        parse_mode=ParseMode.MARKDOWN_V2
    )
    end_time = time.time()
    latency = round((end_time - start_time) * 1000) # in milliseconds
    await ping_message.edit_text(
        f"🏓 पोंग! विलंबता: `{latency}`ms.\n"
        f"_मैं पलक झपकते ही तेज़ हूँ_! ✨",
        parse_mode=ParseMode.MARKDOWN_V2
    )

# GLOBAL BAN COMMAND (OWNER ONLY)
async def gban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username.lower() != OWNER.lstrip('@').lower():
        await update.message.reply_text(
            f"🚫 *पहुँच अस्वीकृत* 🚫\n"
            f"इस कमांड का उपयोग केवल *बॉट मालिक* ही कर सकता है.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user_id = None
    target_username = None
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        target_username = update.message.reply_to_message.from_user.username or update.message.reply_to_message.from_user.first_name
    elif context.args:
        try:
            target_user_id = int(context.args[0])
            try:
                target_user_chat_info = await context.bot.get_chat(target_user_id)
                target_username = target_user_chat_info.username or target_user_chat_info.first_name
            except Exception:
                target_username = f"उपयोगकर्ता ID: {target_user_id}"
        except ValueError:
            await update.message.reply_text(
                f"❌ किसी को वैश्विक रूप से बैन करने के लिए कृपया एक वैध उपयोगकर्ता ID प्रदान करें या एक संदेश पर रिप्लाई करें.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 किसी को वैश्विक रूप से बैन करने के लिए, कृपया उनके संदेश पर रिप्लाई करें या उनकी उपयोगकर्ता ID प्रदान करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not target_user_id:
        await update.message.reply_text(
            f"❌ वैश्विक रूप से बैन करने के लिए उपयोगकर्ता निर्धारित नहीं किया जा सका.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if target_user_id == user.id:
        await update.message.reply_text(
            f"😅 आप खुद को वैश्विक रूप से बैन नहीं कर सकते, सिली!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        global_bans_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"banned_by": user.id, "banned_at": datetime.now()}},
            upsert=True
        )
        await update.message.reply_text(
            f"⛔️ *{escape_markdown_v2(str(target_username))}* \\(ID: `{target_user_id}`\\) को *वैश्विक रूप से बैन* कर दिया गया है! 🚫\n"
            f"_वे अब मेरे उपस्थित सभी समूहों से प्रतिबंधित हैं._",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error global banning user {target_user_id}: {e}")
        await update.message.reply_text(
            f"⚠️ *{escape_markdown_v2(str(target_username))}* को वैश्विक रूप से बैन करने में विफल रहा.\n"
            f"एक त्रुटि हुई: _{escape_markdown_v2(str(e))}_",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# UNGBAN COMMAND (OWNER ONLY)
async def ungban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username.lower() != OWNER.lstrip('@').lower():
        await update.message.reply_text(
            f"🚫 *पहुँच अस्वीकृत* 🚫\n"
            f"इस कमांड का उपयोग केवल *बॉट मालिक* ही कर सकता है.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user_id = None
    target_username = None
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        target_username = update.message.reply_to_message.from_user.username or update.message.reply_to_message.from_user.first_name
    elif context.args:
        try:
            target_user_id = int(context.args[0])
            try:
                target_user_chat_info = await context.bot.get_chat(target_user_id)
                target_username = target_user_chat_info.username or target_user_chat_info.first_name
            except Exception:
                target_username = f"उपयोगकर्ता ID: {target_user_id}"
        except ValueError:
            await update.message.reply_text(
                f"❌ किसी को वैश्विक रूप से अनबैन करने के लिए कृपया एक वैध उपयोगकर्ता ID प्रदान करें.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 किसी को वैश्विक रूप से अनबैन करने के लिए, कृपया उनके संदेश पर रिप्लाई करें या उनकी उपयोगकर्ता ID प्रदान करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not target_user_id:
        await update.message.reply_text(
            f"❌ वैश्विक रूप से अनबैन करने के लिए उपयोगकर्ता निर्धारित नहीं किया जा सका.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        result = global_bans_collection.delete_one({"user_id": target_user_id})
        if result.deleted_count > 0:
            await update.message.reply_text(
                f"✅ *{escape_markdown_v2(str(target_username))}* \\(ID: `{target_user_id}`\\) को *वैश्विक रूप से अनबैन* कर दिया गया है! 🎉\n"
                f"_वे अब उन समूहों में शामिल हो सकते हैं जहाँ मैं उपस्थित हूँ._",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            await update.message.reply_text(
                f"🤷‍♀️ उपयोगकर्ता \\(ID: `{target_user_id}`\\) वर्तमान में वैश्विक रूप से बैन नहीं है.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
    except Exception as e:
        logger.error(f"Error unglobal banning user {target_user_id}: {e}")
        await update.message.reply_text(
            f"⚠️ *{escape_markdown_v2(str(target_username))}* को वैश्विक रूप से अनबैन करने में विफल रहा.\n"
            f"एक त्रुटि हुई: _{escape_markdown_v2(str(e))}_",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# GBLACKLIST COMMAND (OWNER ONLY - Similar to Gban, but can be managed by ID for persistent users)
async def gblacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username.lower() != OWNER.lstrip('@').lower():
        await update.message.reply_text(
            f"🚫 *पहुँच अस्वीकृत* 🚫\n"
            f"इस कमांड का उपयोग केवल *बॉट मालिक* ही कर सकता है.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            f"❌ वैश्विक ब्लैकलिस्ट में जोड़ने के लिए कृपया एक वैध *उपयोगकर्ता ID* प्रदान करें.\n"
            f"उदाहरण: `/gblacklist 123456789`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user_id = int(context.args[0])

    if target_user_id == user.id:
        await update.message.reply_text(
            f"😅 आप खुद को ब्लैकलिस्ट नहीं कर सकते, सिली!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        global_bans_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"banned_by": user.id, "banned_at": datetime.now(), "is_blacklist": True}},
            upsert=True
        )
        await update.message.reply_text(
            f"🚨 उपयोगकर्ता ID: `{target_user_id}` को *वैश्विक ब्लैकलिस्ट* में जोड़ दिया गया है! ⛔️\n"
            f"_वे अब किसी भी समूह में शामिल नहीं हो पाएंगे जहाँ मैं सक्रिय हूँ._",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error global blacklisting user {target_user_id}: {e}")
        await update.message.reply_text(
            f"⚠️ उपयोगकर्ता ID: `{target_user_id}` को वैश्विक ब्लैकलिस्ट में जोड़ने में विफल रहा.\n"
            f"एक त्रुटि हुई: _{escape_markdown_v2(str(e))}_",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# UNGBLACKLIST COMMAND (OWNER ONLY)
async def ungblacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username.lower() != OWNER.lstrip('@').lower():
        await update.message.reply_text(
            f"🚫 *पहुँच अस्वीकृत* 🚫\n"
            f"इस कमांड का उपयोग केवल *बॉट मालिक* ही कर सकता है.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            f"❌ वैश्विक ब्लैकलिस्ट से हटाने के लिए कृपया एक वैध *उपयोगकर्ता ID* प्रदान करें.\n"
            f"उदाहरण: `/ungblacklist 123456789`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user_id = int(context.args[0])

    try:
        result = global_bans_collection.delete_one({"user_id": target_user_id, "is_blacklist": True})
        if result.deleted_count > 0:
            await update.message.reply_text(
                f"✅ उपयोगकर्ता ID: `{target_user_id}` को वैश्विक ब्लैकलिस्ट से *हटा दिया गया* है! 🎉\n"
                f"_वे अब उन समूहों में शामिल हो सकते हैं जहाँ मैं सक्रिय हूँ._",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            await update.message.reply_text(
                f"🤷‍♀️ उपयोगकर्ता ID: `{target_user_id}` वर्तमान में वैश्विक ब्लैकलिस्ट में नहीं है.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
    except Exception as e:
        logger.error(f"Error unglobal blacklisting user {target_user_id}: {e}")
        await update.message.reply_text(
            f"⚠️ उपयोगकर्ता ID: `{target_user_id}` को वैश्विक ब्लैकलिस्ट से हटाने में विफल रहा.\n"
            f"एक त्रुटि हुई: _{escape_markdown_v2(str(e))}_",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# BLACKLIST LIST COMMAND (OWNER ONLY)
async def blacklist_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username.lower() != OWNER.lstrip('@').lower():
        await update.message.reply_text(
            f"🚫 *पहुँच अस्वीकृत* 🚫\n"
            f"इस कमांड का उपयोग केवल *बॉट मालिक* ही कर सकता है.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    blacklisted_users = list(global_bans_collection.find({"is_blacklist": True}))

    if blacklisted_users:
        response = "📋 *वैश्विक ब्लैकलिस्टेड उपयोगकर्ता:*\n\n"
        for entry in blacklisted_users:
            user_id = entry.get("user_id")
            banned_at = entry.get("banned_at", "N/A").strftime("%Y-%m-%d %H:%M:%S") if entry.get("banned_at") != "N/A" else "N/A"
            response += f"•  उपयोगकर्ता ID: `{user_id}` \\| बैन किया गया: _{banned_at}_\n"
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(
            f"✅ वर्तमान में *वैश्विक ब्लैकलिस्ट* में कोई उपयोगकर्ता नहीं हैं. सूची साफ है! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# RULES COMMANDS
async def setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"नियम सेट करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not context.args:
        await update.message.reply_text(
            f"❌ कमांड के बाद कृपया नियम पाठ प्रदान करें.\n"
            f"उदाहरण: `/setrules दयालु रहें, टेलीग्राम TOS का पालन करें.`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    rules_text = " ".join(context.args)
    rules_collection.update_one(
        {"chat_id": chat.id},
        {"$set": {"rules_text": rules_text}},
        upsert=True
    )
    await update.message.reply_text(
        f"📜 समूह के नियम *सफलतापूर्वक सेट* हो गए हैं! ✨\n"
        f"सदस्य अब उन्हें `/rules` का उपयोग करके देख सकते हैं.",
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    rules_data = rules_collection.find_one({"chat_id": chat.id})

    if rules_data and rules_data.get("rules_text"):
        rules_text = rules_data["rules_text"]
        await update.message.reply_text(
            f"📜 *{escape_markdown_v2(chat.title)} के लिए समूह के नियम:*\n\n"
            f"{escape_markdown_v2(rules_text)}\n\n"
            f"_कृपया सभी के लिए एक सुखद वातावरण सुनिश्चित करने के लिए इन नियमों का पालन करें._ 😇",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await update.message.reply_text(
            f"🤷‍♀️ इस समूह के लिए अभी तक कोई नियम निर्धारित नहीं किए गए हैं.\n"
            f"_एडमिन `/setrules <text>` का उपयोग करके नियम सेट कर सकते हैं._",
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def cleanrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"नियम साफ करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    result = rules_collection.delete_one({"chat_id": chat.id})
    if result.deleted_count > 0:
        await update.message.reply_text(
            f"🗑️ समूह के नियम *सफलतापूर्वक साफ* हो गए हैं! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await update.message.reply_text(
            f"🤷‍♀️ इस समूह के लिए शुरू से ही कोई नियम निर्धारित नहीं किए गए थे.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# AUTO LINK FILTER
async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message

    chat_settings = chat_settings_collection.find_one({"chat_id": chat.id})
    if not chat_settings or not chat_settings.get("auto_link_filter", False):
        return # Do nothing if auto link filter is off

    if message.from_user and await is_admin_or_owner(update, context, chat.id, message.from_user.id):
        return

    if message.text and (message.entities or message.caption_entities):
        has_url = False
        for entity in (message.entities or []) + (message.caption_entities or []):
            if entity.type in ["url", "text_link"]:
                has_url = True
                break

        if has_url:
            try:
                await message.delete()
                await context.bot.send_message(
                    chat.id,
                    f"🔗 लिंक यहाँ अनुमति नहीं हैं, *{escape_markdown_v2(message.from_user.first_name)}*! 🙅‍♀️",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            except Exception as e:
                logger.warning(f"लिंक संदेश को हटाने या चेतावनी भेजने में विफल रहा: {e}")

# FALLBACK HELP FOR UNKNOWN COMMANDS
async def fallback_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "group" and update.effective_message.text and update.effective_message.text.startswith('/'):
        # This checks if it's a command that the bot received.
        # A more robust check would involve iterating through registered command handlers,
        # but for simplicity, we assume if it starts with '/' it's an intended command.
        command_text = update.effective_message.text.split(' ')[0]
        if command_text.lower() not in context.application.handlers: # This is a conceptual check, handlers are not directly accessible this way.
            # A simpler way is to let this handler be the last CommandHandler or a general MessageHandler that checks for '/'
            await update.message.reply_text(
                f"❓ मैं उस कमांड से परिचित नहीं हूँ, *{escape_markdown_v2(update.effective_user.first_name)}*.\n"
                f"कमांड्स की सूची के लिए, कृपया मेरे साथ एक निजी चैट में /help का उपयोग करें.",
                parse_mode=ParseMode.MARKDOWN_V2
            )

# CLEAN SERVICE MESSAGES
async def cleanservice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"इस कमांड का उपयोग करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return
    
    await update.message.reply_text(
        f"🧹 यह कमांड पूर्ण स्वचालन के लिए विकास के अधीन है.\n"
        f"_वर्तमान में, आप सेवा संदेशों को मैन्युअल रूप से हटा सकते हैं या समूह सेटिंग्स कॉन्फ़िगर कर सकते हैं._",
        parse_mode=ParseMode.MARKDOWN_V2
    )

# AUTO LINK TOGGLE
async def autolink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"ऑटो लिंक फिल्टर को टॉगल करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not context.args or context.args[0].lower() not in ["on", "off"]:
        await update.message.reply_text(
            f"❌ ऑटो लिंक फिल्टर को टॉगल करने के लिए कृपया `on` या `off` निर्दिष्ट करें.\n"
            f"उदाहरण: `/autolink on` या `/autolink off`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    action = context.args[0].lower()
    if action == "on":
        chat_settings_collection.update_one({"chat_id": chat.id}, {"$set": {"auto_link_filter": True}}, upsert=True)
        await update.message.reply_text(
            f"✅ ऑटो लिंक विलोपन इस समूह के लिए *सक्षम* कर दिया गया है! 🔗\n"
            f"_मैं अब लिंक वाले संदेशों को स्वचालित रूप से हटा दूंगा._",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        chat_settings_collection.update_one({"chat_id": chat.id}, {"$set": {"auto_link_filter": False}}, upsert=True)
        await update.message.reply_text(
            f"🚫 ऑटो लिंक विलोपन इस समूह के लिए *अक्षम* कर दिया गया है! 🔓\n"
            f"_लिंक अब स्वचालित रूप से हटाए नहीं जाएंगे._",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# WELCOME MESSAGE
async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"स्वागत संदेश सेट करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not context.args:
        await update.message.reply_text(
            f"❌ कमांड के बाद कृपया स्वागत संदेश पाठ प्रदान करें.\n"
            f"आप प्लेसहोल्डर्स का उपयोग कर सकते हैं: `{{first}}`, `{{last}}`, `{{fullname}}`, `{{chatname}}`\\.\n"
            f"उदाहरण: `/setwelcome {{first}} का {{chatname}} में स्वागत है!`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    welcome_text = " ".join(context.args)
    welcomes_collection.update_one(
        {"chat_id": chat.id},
        {"$set": {"welcome_message": welcome_text}},
        upsert=True
    )
    await update.message.reply_text(
        f"🎉 कस्टम स्वागत संदेश *सफलतापूर्वक सेट* हो गया है! ✨\n"
        f"_नए सदस्यों को अब यह संदेश दिखाई देगा._",
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def resetwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *अनुमति नहीं* 🚫\n"
            f"स्वागत संदेश रीसेट करने के लिए आपको एक *एडमिन* होना चाहिए.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    result = welcomes_collection.delete_one({"chat_id": chat.id})
    if result.deleted_count > 0:
        await update.message.reply_text(
            f"↩️ कस्टम स्वागत संदेश *डिफ़ॉल्ट पर रीसेट* हो गया है! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await update.message.reply_text(
            f"🤷‍♀️ इस समूह के लिए कोई कस्टम स्वागत संदेश सेट नहीं किया गया था.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    welcome_data = welcomes_collection.find_one({"chat_id": chat.id})
    
    welcome_message_text = welcome_data.get("welcome_message") if welcome_data else (
        "👋 स्वागत है, {fullname}, {chatname} में!"
    )

    simulated_user = update.effective_user
    formatted_message = welcome_message_text.replace("{first}", escape_markdown_v2(simulated_user.first_name))\
                                            .replace("{last}", escape_markdown_v2(simulated_user.last_name or ""))\
                                            .replace("{fullname}", escape_markdown_v2(simulated_user.full_name))\
                                            .replace("{chatname}", escape_markdown_v2(chat.title))

    await update.message.reply_text(
        f"📝 *{escape_markdown_v2(simulated_user.first_name)}* के लिए स्वागत संदेश का परीक्षण कर रहा है:\n\n"
        f"{formatted_message}",
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def new_member_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            # Bot joined the group
            await update.message.reply_text(
                f"🎉 सभी को नमस्ते! मैं *रोज*, आपकी नई समूह प्रबंधक हूँ! 🌹\n"
                f"सुनिश्चित करें कि आप मुझे एक *एडमिन* बनाएं ताकि मैं इस चैट को अद्भुत बनाए रखने में मदद कर सकूं! 💪",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        chat = update.effective_chat
        welcome_data = welcomes_collection.find_one({"chat_id": chat.id})
        
        # Dynamic welcome message variations
        default_welcome_templates = [
            "👋 {fullname} का {chatname} में स्वागत है! हमें आपको पाकर खुशी हुई! 🎉",
            "✨ {fullname} ने अभी-अभी {chatname} में प्रवेश किया! मज़े करें! 🥳",
            "🚀 एक नए सदस्य ने उड़ान भरी: {fullname}! {chatname} में आपका स्वागत है! 👋",
            "🌟 {fullname} का {chatname} में स्वागत है! हम आपके शामिल होने से उत्साहित हैं! 😊",
            "💖 {fullname}, {chatname} के परिवार में आपका स्वागत है! हम आपके साथ जुड़कर खुश हैं! 🤗"
        ]
        
        welcome_message_text = welcome_data.get("welcome_message") if welcome_data else random.choice(default_welcome_templates)

        formatted_message = welcome_message_text.replace("{first}", escape_markdown_v2(member.first_name))\
                                                .replace("{last}", escape_markdown_v2(member.last_name or ""))\
                                                .replace("{fullname}", escape_markdown_v2(member.full_name))\
                                                .replace("{chatname}", escape_markdown_v2(chat.title))

        # Add user's details uniquely for welcome
        user_info = await _get_user_display_info(member)
        details_text = (
            f"\n\n"
            f"🔗 *आपका विवरण:*\n"
            f"  •  नाम: {user_info['full_name']}\n"
            f"  •  उपयोगकर्ता ID: `{user_info['user_id']}`\n"
            f"  •  उपयोगकर्ता नाम: {user_info['username']}"
        )
        formatted_message += details_text


        try:
            # Send profile picture if available
            if user_info['profile_pic_file_id']:
                await update.message.reply_photo(
                    photo=user_info['profile_pic_file_id'],
                    caption=formatted_message,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            else:
                # Fallback to sticker then text
                await update.message.reply_sticker(DEFAULT_JOIN_STICKER_ID)
                await update.message.reply_text(formatted_message, parse_mode=ParseMode.MARKDOWN_V2)
        except Exception as e:
            logger.error(f"स्वागत स्टिकर या संदेश भेजने में विफल रहा: {e}")
            # Final fallback to just text if both fail
            await update.message.reply_text(formatted_message, parse_mode=ParseMode.MARKDOWN_V2) 

# LEFT MEMBER ANNOUNCEMENT
async def left_member_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.message.left_chat_member
    chat = update.effective_chat

    if member.id == context.bot.id:
        # Bot was removed from the group, no need to announce its own departure
        logger.info(f"Bot was removed from chat {chat.id} ({chat.title})")
        return

    # Dynamic goodbye message variations
    goodbye_templates = [
        "👋 अलविदा, *{fullname}*! हमें उम्मीद है कि आप फिर से मिलेंगे. 😥",
        "💔 *{fullname}* ने समूह छोड़ दिया. हम उन्हें याद करेंगे. 😢",
        "🚶‍♂️ *{fullname}* ने {chatname} से विदा ली. सुरक्षित रहें! 🌟",
        "🚪 *{fullname}* चला गया. विदाई! 👋",
        "😔 एक सदस्य चला गया: *{fullname}*. आपकी कमी खलेगी."
    ]

    goodbye_message_text = random.choice(goodbye_templates)

    formatted_message = goodbye_message_text.replace("{first}", escape_markdown_v2(member.first_name))\
                                            .replace("{last}", escape_markdown_v2(member.last_name or ""))\
                                            .replace("{fullname}", escape_markdown_v2(member.full_name))\
                                            .replace("{chatname}", escape_markdown_v2(chat.title))

    # Add user's details for farewell
    details_text = (
        f"\n\n"
        f"🔗 *विवरण:*\n"
        f"  •  नाम: {escape_markdown_v2(member.full_name)}\n"
        f"  •  उपयोगकर्ता ID: `{member.id}`\n"
        f"  •  उपयोगकर्ता नाम: {escape_markdown_v2(f'@{member.username}') if member.username else '_N/A_'}"
    )
    formatted_message += details_text

    try:
        await update.message.reply_text(
            formatted_message,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"सदस्य के जाने का संदेश भेजने में विफल रहा: {e}")


# INFO COMMAND
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_chat_member = await context.bot.get_chat_member(chat.id, user_id)
            target_user = target_chat_member.user
        except ValueError:
            await update.message.reply_text(
                f"❌ उपयोगकर्ता जानकारी प्राप्त करने के लिए कृपया एक वैध उपयोगकर्ता ID प्रदान करें या एक संदेश पर रिप्लाई करें.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ इस चैट में प्रदान की गई ID वाले उपयोगकर्ता को नहीं ढूँढा जा सका या उनकी जानकारी प्राप्त नहीं की जा सकी.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        target_user = user # If no target, show info about the command issuer

    if not target_user:
        await update.message.reply_text(
            f"🤔 उपयोगकर्ता जानकारी प्राप्त करने के लिए, कृपया उनके संदेश पर रिप्लाई करें या उनकी उपयोगकर्ता ID प्रदान करें.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    is_chat_admin = await is_admin_or_owner(update, context, chat.id, target_user.id)
    warn_data = warns_collection.find_one({"chat_id": chat.id, "user_id": target_user.id})
    warn_count = warn_data.get("warn_count", 0) if warn_data else 0

    user_info_display = await _get_user_display_info(target_user)

    user_info_text = (
        f"👤 *उपयोगकर्ता जानकारी* 👤\n\n"
        f"•  *नाम:* {user_info_display['full_name']}\n"
        f"•  *उपयोगकर्ता ID:* `{user_info_display['user_id']}`\n"
        f"•  *उपयोगकर्ता नाम:* {user_info_display['username']}\n"
        f"•  *बॉट है:* {'हाँ' if target_user.is_bot else 'नहीं'}\n"
        f"•  *इस चैट में एडमिन है:* {'हाँ' if is_chat_admin else 'नहीं'}\n"
        f"•  *इस चैट में चेतावनियाँ:* `{warn_count}`\n\n"
        f"_विशिष्ट चेतावनी विवरण की जाँच के लिए `/warns` का उपयोग करें._"
    )

    # Send profile picture if available, then text
    if user_info_display['profile_pic_file_id']:
        try:
            await update.message.reply_photo(
                photo=user_info_display['profile_pic_file_id'],
                caption=user_info_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"उपयोगकर्ता {target_user.id} के लिए प्रोफ़ाइल तस्वीर भेजने में विफल रहा: {e}")
            await update.message.reply_text(user_info_text, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(user_info_text, parse_mode=ParseMode.MARKDOWN_V2)

# ID COMMAND
async def get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        user_name = update.message.reply_to_message.from_user.full_name
        await update.message.reply_text(
            f"👤 *{escape_markdown_v2(user_name)}* की उपयोगकर्ता ID: `{user_id}`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        user_id = update.effective_user.id
        user_name = update.effective_user.full_name
        await update.message.reply_text(
            f"👤 आपकी उपयोगकर्ता ID, *{escape_markdown_v2(user_name)}*, है: `{user_id}`",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# --- Main Function to Run the Bot ---
async def main():
    try:
        app = ApplicationBuilder().token(TOKEN).build()
        logger.info("बॉट शुरू हो रहा है...")

        # Commands
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("kick", kick))
        app.add_handler(CommandHandler("ban", ban))
        app.add_handler(CommandHandler("mute", mute))
        app.add_handler(CommandHandler("unmute", unmute))
        app.add_handler(CommandHandler("warn", warn))
        app.add_handler(CommandHandler("warns", warns))
        app.add_handler(CommandHandler("unwarn", unwarn))
        app.add_handler(CommandHandler("resetwarns", unwarn)) # Alias for unwarn/resetwarns for simplicity
        app.add_handler(CommandHandler("id", get_user_id))
        app.add_handler(CommandHandler("chatid", get_chat_id))
        app.add_handler(CommandHandler("about", about))
        app.add_handler(CommandHandler("ping", ping))
        app.add_handler(CommandHandler("info", info)) # Added info command

        # Owner Only Commands (GLOBAL MODERATION)
        app.add_handler(CommandHandler("gban", gban))
        app.add_handler(CommandHandler("ungban", ungban))
        app.add_handler(CommandHandler("gblacklist", gblacklist))
        app.add_handler(CommandHandler("ungblacklist", ungblacklist))
        app.add_handler(CommandHandler("blacklist_list", blacklist_list))

        # Welcome/Rules - Admin/Owner restricted
        app.add_handler(CommandHandler("setrules", setrules))
        app.add_handler(CommandHandler("rules", rules))
        app.add_handler(CommandHandler("cleanrules", cleanrules))
        app.add_handler(CommandHandler("setwelcome", setwelcome))
        app.add_handler(CommandHandler("resetwelcome", resetwelcome))
        app.add_handler(CommandHandler("welcome", welcome))
        
        # New member and left member handlers
        app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member_welcome))
        app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, left_member_announcement))


        # Message tool commands - admin restricted
        app.add_handler(CommandHandler("pin", pin))
        app.add_handler(CommandHandler("unpin", unpin))
        app.add_handler(CommandHandler("del", delete_message))
        app.add_handler(CommandHandler("purge", purge))
        app.add_handler(CommandHandler("cleanservice", cleanservice))
        app.add_handler(CommandHandler("autolink", autolink))


        # Auto link filter and fallback help in group chats
        app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_links))
        # This fallback_help should be the last MessageHandler for text in groups
        app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, fallback_help)) 
        
        # Run polling without closing the event loop.
        await app.run_polling(close_loop=False)

    except Exception as e:
        logger.error(f"मुख्य फ़ंक्शन में त्रुटि: {e}")

# --- Launcher ---
async def launch():
    try:
        await main()
    except Exception as e:
        print(f"बॉट क्रैश हो गया: {e}", file=sys.stderr)

if __name__ == "__main__":
    try:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(main())
        except RuntimeError:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            new_loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("उपयोगकर्ता द्वारा बॉट रोका गया.", file=sys.stderr)
    except Exception as e:
        print(f"स्टार्टअप के दौरान एक अप्रत्याशित त्रुटि हुई: {e}", file=sys.stderr)
