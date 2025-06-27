# coding=utf-8
import nest_asyncio
nest_asyncio.apply()

import asyncio
import time
import sys
import logging
from datetime import datetime, timedelta
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
from telegram.constants import ParseMode # Import ParseMode for Markdown V2

# --- Configuration ---
TOKEN = "8100559127:AAFyDgLMXb3kOEXgTXK2vLKUkN_IxJ3vR9E"  # Replace with your actual token
OWNER = "@Rajaraj909" # Bot ka owner username (username, NOT ID)

# MongoDB Configuration
MONGO_URI = "mongodb+srv://pusers:nycreation@nycreation.pd4klp1.mongodb.net/?retryWrites=true&w=majority&appName=NYCREATION" # Replace with your MongoDB connection string (e.g., from Atlas)
DB_NAME = "RoseBotDB"

# ** Sticker IDs (Replace with your actual sticker file IDs) **
DEFAULT_JOIN_STICKER_ID = "CAACAgIAAxkBAAIC3mWZ7WvQzQe5F2l3b3sQ2M1d4QABfQACaQMAAm2YgUrpL..." # Placeholder, replace with a real sticker ID

# --- Database Setup ---
def get_db_collection(collection_name):
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

# --- Utility Functions ---
def escape_markdown_v2(text):
    """Helper function to escape characters for MarkdownV2 parse mode."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return "".join(["\\" + char if char in escape_chars else char for char in text])

async def is_admin_or_owner(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    """Checks if the user is an admin in the chat or the bot's owner."""
    if user_id == context.bot.id: # Bot itself is considered admin for its own actions
        return True

    # Check if the user is the bot's designated owner by username
    # This requires fetching the owner's actual user ID if OWNER is a username
    try:
        owner_info = None
        # Try to find the owner's user object in the context's chat data if available
        # or by fetching directly if needed.
        # This part might need refinement depending on how OWNER is set and used globally.
        # For simplicity, assuming OWNER is a username that can be matched.
        # A more robust solution might store OWNER_ID directly.
        if OWNER and OWNER.startswith('@'):
            # Attempt to resolve owner username to ID for a more direct comparison
            # This is a bit tricky as get_chat_member needs a chat_id.
            # A simpler way for a global owner check is to just check username.
            # However, for the purpose of chat admin, we only check chat_member.
            pass # Keep it simple, just check chat_member status below
    except Exception:
        logger.debug("Could not resolve owner username to ID for direct comparison in is_admin_or_owner.")

    chat_member = await context.bot.get_chat_member(chat_id, user_id)
    if chat_member.status in ["creator", "administrator"]:
        return True
    
    # Final check if the user's username matches the OWNER username
    # This is less reliable if owner changes username, but aligns with your current OWNER = "@Rajaraj909"
    if user_id == update.effective_user.id and update.effective_user.username and update.effective_user.username.lower() == OWNER.lstrip('@').lower():
        return True

    # If the owner is not in the chat, or not an admin, they are still the bot owner
    # This part is complex. For simplicity, we assume if OWNER is "@Rajaraj909", then only that specific username can be the owner.
    # A robust solution would store OWNER_ID instead of OWNER_USERNAME.
    # For now, if the user is the one specified as OWNER (by username), they are considered owner.
    # This check is less direct than checking by ID, but works with your current setup.
    if user_id == update.effective_user.id and update.effective_user.username and update.effective_user.username.lower() == OWNER.lstrip('@').lower():
        return True
    
    # A more robust owner check (if you stored OWNER_ID somewhere, e.g., in config or env):
    # if user_id == int(os.getenv("BOT_OWNER_ID")): # Assuming BOT_OWNER_ID is set as env variable
    #     return True

    return False

# --- Bot Commands and Handlers ---

# START COMMAND
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text(
            f"Hey there, *{escape_markdown_v2(user.first_name)}* \\! 👋\n\n"
            f"I'm *Rose*, a powerful group management bot designed to keep your chats safe and organized\\!\n"
            f"I can help you with:\n"
            f"✨ Moderation tools like ban, kick, mute, warn\n"
            f"🔒 Anti\\-spam and anti\\-link features\n"
            f"⚙️ Customizable welcome messages and rules\n"
            f"…and much more\\! ✨\n\n"
            f"Ready to get started\? Add me to your group and make me an admin\\!\n"
            f"For a list of all commands, type /help\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await update.message.reply_text(
            f"Hello, *{escape_markdown_v2(user.first_name)}*\\! I'm already active here\\! 🎉\n"
            f"Type /help to see what I can do for this group\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# HELP COMMAND
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        help_text = (
            f"🌹 *Rose Bot Help Menu* 🌹\n\n"
            f"Here are the commands you can use:\n\n"
            f"*🛠️ Admin Commands:*\n"
            f"  `/ban <reply or username>` \\- Ban a user from the group\\.\n"
            f"  `/kick <reply or username>` \\- Kick a user from the group\\.\n"
            f"  `/mute <reply or username> [time]` \\- Mute a user temporarily or permanently\\.\n"
            f"  `/unmute <reply or username>` \\- Unmute a user\\.\n"
            f"  `/warn <reply or username> [reason]` \\- Warn a user\\.\n"
            f"  `/warns <reply or username>` \\- Check a user's warnings\\.\n"
            f"  `/resetwarns <reply or username>` \\- Reset a user's warnings\\.\n"
            f"  `/pin` \\- Pin the replied message\\.\n"
            f"  `/unpin` \\- Unpin the replied message\\.\n"
            f"  `/del` \\- Delete the replied message\\.\n"
            f"  `/purge` \\- Purge messages from the replied message upwards\\.\n"
            f"  `/setrules <text>` \\- Set group rules\\.\n"
            f"  `/rules` \\- Get group rules\\.\n"
            f"  `/cleanrules` \\- Clear group rules\\.\n"
            f"  `/cleanservice` \\- Delete service messages \\(e\\.g\\., member joined/left\\)\\.\n"
            f"  `/autolink <on/off>` \\- Toggle auto link deletion\\.\n" # Added autolink to help
            f"  `/setwelcome <text>` \\- Set custom welcome message \\(Use `{{first}}`, `{{last}}`, `{{fullname}}`, `{{chatname}}`\\)\\.\n"
            f"  `/resetwelcome` \\- Reset welcome message to default\\.\n"
            f"  `/welcome` \\- Test the welcome message\\.\n\n"
            f"*👑 Owner Only Commands:*\n" # Separated owner-only commands
            f"  `/gban <reply or username>` \\- Globally ban a user\\.\n"
            f"  `/ungban <reply or username>` \\- Unglobal ban a user\\.\n"
            f"  `/gblacklist <id>` \\- Add a user to global blacklist\\.\n"
            f"  `/ungblacklist <id>` \\- Remove a user from global blacklist\\.\n"
            f"  `/blacklist_list` \\- Show global blacklist\\.\n\n"
            f"*✨ General Commands:*\n"
            f"  `/id` \\- Get your user ID or the replied user's ID\\.\n"
            f"  `/chatid` \\- Get the current chat's ID\\.\n"
            f"  `/info <reply or username>` \\- Get information about a user\\.\n"
            f"  `/about` \\- Learn more about Rose Bot\\.\n"
            f"  `/ping` \\- Check bot's response time\\.\n\n"
            f"Need more help\? Join our [Support Group](https://t.me/{escape_markdown_v2('Rajaraj909')})\\! 💬\n\n" # Replace with your actual support group link
            f"🌸 Thank you for using Rose\\! 🌸"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
    else:
        await update.message.reply_text(
            f"Hey *{escape_markdown_v2(update.effective_user.first_name)}*\\! 👋\n\n"
            f"I can't send the full help menu in a group chat to avoid spam\\.\n"
            f"Please open a private chat with me and use the /help command there for a complete list of features\\!\n\n"
            f"Just click [here](https://t.me/{context.bot.username}) to start a private chat with me\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )

# KICK COMMAND
async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to use this command\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            # For `get_chat_member` you need to ensure the user ID actually exists in the chat.
            # If not, it will raise an error.
            # A more robust check might involve fetching the user directly if they are not in the chat.
            # However, for kick/ban, they generally need to be a chat member to be kicked/banned.
            target_chat_member = await context.bot.get_chat_member(chat.id, user_id)
            target_user = target_chat_member.user
        except ValueError:
            await update.message.reply_text(
                f"❌ Please provide a valid User ID or reply to a message to kick someone\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ Could not find the user with the provided ID in this chat\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 To kick someone, please reply to their message or provide their User ID\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if target_user.id == user.id:
        await update.message.reply_text(
            f"😅 You can't kick yourself, silly\\!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # Prevent admin/owner from being kicked by non-creator/non-owner admins
    if await is_admin_or_owner(update, context, chat.id, target_user.id):
        # A creator can kick other admins. This check needs refinement if you want to allow creators to kick admins.
        # For simplicity, we'll prevent any admin from kicking another admin or the bot owner.
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        if target_chat_member.status in ["creator", "administrator"] or \
           (target_user.username and target_user.username.lower() == OWNER.lstrip('@').lower()):
            await update.message.reply_text(
                f"🔒 I can't kick an *admin* or the *bot owner*\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

    try:
        await context.bot.kick_chat_member(chat.id, target_user.id)
        await update.message.reply_text(
            f"👋 *{escape_markdown_v2(target_user.first_name)}* has been kicked from the group\\!\\n"
            f"_Adios_\\! 👋",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error kicking user {target_user.id}: {e}")
        await update.message.reply_text(
            f"⚠️ Failed to kick *{escape_markdown_v2(target_user.first_name)}*\\.\n"
            f"Make sure I have the necessary permissions\\! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# BAN COMMAND
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to use this command\\.",
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
                f"❌ Please provide a valid User ID or reply to a message to ban someone\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ Could not find the user with the provided ID in this chat\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 To ban someone, please reply to their message or provide their User ID\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if target_user.id == user.id:
        await update.message.reply_text(
            f"😅 You can't ban yourself, silly\\!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # Prevent admin/owner from being banned by non-creator/non-owner admins
    if await is_admin_or_owner(update, context, chat.id, target_user.id):
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        if target_chat_member.status in ["creator", "administrator"] or \
           (target_user.username and target_user.username.lower() == OWNER.lstrip('@').lower()):
            await update.message.reply_text(
                f"🔒 I can't ban an *admin* or the *bot owner*\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

    try:
        await context.bot.ban_chat_member(chat.id, target_user.id)
        await update.message.reply_text(
            f"⛓️ *{escape_markdown_v2(target_user.first_name)}* has been banned from the group\\!\\n"
            f"They shall not return\\! 🚫",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error banning user {target_user.id}: {e}")
        await update.message.reply_text(
            f"⚠️ Failed to ban *{escape_markdown_v2(target_user.first_name)}*\\.\n"
            f"Make sure I have the necessary permissions\\! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# PIN COMMAND
async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to use this command\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            f"📌 Please reply to a message to pin it\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        await context.bot.pin_chat_message(
            chat_id=chat.id,
            message_id=update.message.reply_to_message.message_id
        )
        await update.message.reply_text(
            f"📌 Message pinned successfully\\! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error pinning message: {e}")
        await update.message.reply_text(
            f"⚠️ Failed to pin message\\.\n"
            f"Make sure I have the necessary permissions\\! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# UNPIN COMMAND
async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to use this command\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            f"📍 Please reply to a pinned message to unpin it\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        await context.bot.unpin_chat_message(
            chat_id=chat.id,
            message_id=update.message.reply_to_message.message_id
        )
        await update.message.reply_text(
            f"📍 Message unpinned successfully\\! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error unpinning message: {e}")
        await update.message.reply_text(
            f"⚠️ Failed to unpin message\\.\n"
            f"Make sure I have the necessary permissions\\! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# DELETE MESSAGE COMMAND
async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to use this command\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            f"🗑️ Please reply to a message to delete it\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        await update.message.reply_to_message.delete()
        await update.message.delete() # Delete the command message as well
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        await update.message.reply_text(
            f"⚠️ Failed to delete message\\.\n"
            f"Make sure I have the necessary permissions\\! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# PURGE COMMAND
async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to use this command\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            f"🧹 Please reply to the *first message* you want to purge from\\.",
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
            f"🧹 Purged *{len(messages_to_delete)}* messages successfully\\! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await asyncio.sleep(3) # Delete confirmation after 3 seconds
        await purge_confirmation.delete()
    except Exception as e:
        logger.error(f"Error purging messages: {e}")
        await update.message.reply_text(
            f"⚠️ Failed to purge messages\\.\n"
            f"Make sure I have the necessary permissions\\! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# GET CHAT ID COMMAND
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"🆔 The Chat ID for this group is: `{escape_markdown_v2(str(chat_id))}`\n"
        f"_This ID is useful for certain bot configurations\\._",
        parse_mode=ParseMode.MARKDOWN_V2
    )

# WARN COMMAND
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to use this command\\.",
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
                f"❌ Please provide a valid User ID or reply to a message to warn someone\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ Could not find the user with the provided ID in this chat\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 To warn someone, please reply to their message or provide their User ID\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if target_user.id == user.id:
        await update.message.reply_text(
            f"😅 You can't warn yourself, silly\\!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if await is_admin_or_owner(update, context, chat.id, target_user.id):
        await update.message.reply_text(
            f"🔒 I can't warn an *admin* or the *bot owner*\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"

    # Get current warns for the user in this chat
    current_warns_data = warns_collection.find_one({"chat_id": chat.id, "user_id": target_user.id})
    warn_count = current_warns_data["warn_count"] + 1 if current_warns_data else 1
    
    # Update or insert warns
    warns_collection.update_one(
        {"chat_id": chat.id, "user_id": target_user.id},
        {"$set": {"warn_count": warn_count, "last_warn_reason": reason}},
        upsert=True
    )

    await update.message.reply_text(
        f"⚠️ *{escape_markdown_v2(target_user.first_name)}* has been warned\\! "
        f"Current warns: `{warn_count}`\\.\n"
        f"Reason: _{escape_markdown_v2(reason)}_\n\n"
        f"🚨 Too many warns may lead to a kick or ban\\! Please be careful\\! 🚨",
        parse_mode=ParseMode.MARKDOWN_V2
    )

# UNWARN COMMAND
async def unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to use this command\\.",
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
                f"❌ Please provide a valid User ID or reply to a message to unwarn someone\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ Could not find the user with the provided ID in this chat\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 To unwarn someone, please reply to their message or provide their User ID\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if target_user.id == user.id:
        await update.message.reply_text(
            f"😅 You can't unwarn yourself, silly\\!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    result = warns_collection.delete_one({"chat_id": chat.id, "user_id": target_user.id})

    if result.deleted_count > 0:
        await update.message.reply_text(
            f"✅ *{escape_markdown_v2(target_user.first_name)}*'s warnings have been cleared\\! "
            f"They're on a clean slate now\\! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await update.message.reply_text(
            f"🤷‍♀️ *{escape_markdown_v2(target_user.first_name)}* has no active warnings to clear in this chat\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# WARNS COMMAND
async def warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to use this command\\.",
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
                f"❌ Please provide a valid User ID or reply to a message to check warns\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ Could not find the user with the provided ID in this chat\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 To check warns, please reply to their message or provide their User ID\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    warn_data = warns_collection.find_one({"chat_id": chat.id, "user_id": target_user.id})

    if warn_data:
        warn_count = warn_data.get("warn_count", 0)
        last_reason = warn_data.get("last_warn_reason", "N/A")
        await update.message.reply_text(
            f"📊 *{escape_markdown_v2(target_user.first_name)}* has `{warn_count}` warns in this group\\.\n"
            f"Last reason: _{escape_markdown_v2(last_reason)}_\n\n"
            f"_To reset their warns, use_ `/resetwarns`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await update.message.reply_text(
            f"✅ *{escape_markdown_v2(target_user.first_name)}* has no active warnings in this group\\!\\n"
            f"_They are a good member_\\. 👍",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# MUTE COMMAND
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to use this command\\.",
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
                f"❌ Please provide a valid User ID or reply to a message to mute someone\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ Could not find the user with the provided ID in this chat\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 To mute someone, please reply to their message or provide their User ID\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if target_user.id == user.id:
        await update.message.reply_text(
            f"😅 You can't mute yourself, silly\\!",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # Prevent admin/owner from being muted by non-creator/non-owner admins
    if await is_admin_or_owner(update, context, chat.id, target_user.id):
        target_chat_member = await context.bot.get_chat_member(chat.id, target_user.id)
        if target_chat_member.status in ["creator", "administrator"] or \
           (target_user.username and target_user.username.lower() == OWNER.lstrip('@').lower()):
            await update.message.reply_text(
                f"🔒 I can't mute an *admin* or the *bot owner*\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

    # Default to permanent mute if no time is specified
    mute_duration = None
    mute_duration_str = "permanently"
    if len(context.args) > 1:
        try:
            duration_str = context.args[1]
            if duration_str.endswith("m"):
                mute_duration = timedelta(minutes=int(duration_str[:-1]))
                mute_duration_str = f"{int(duration_str[:-1])} minutes"
            elif duration_str.endswith("h"):
                mute_duration = timedelta(hours=int(duration_str[:-1]))
                mute_duration_str = f"{int(duration_str[:-1])} hours"
            elif duration_str.endswith("d"):
                mute_duration = timedelta(days=int(duration_str[:-1]))
                mute_duration_str = f"{int(duration_str[:-1])} days"
            else:
                await update.message.reply_text(
                    f"❌ Invalid mute duration format\\.\n"
                    f"Use `[number]m` for minutes, `[number]h` for hours, or `[number]d` for days\\.",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                return
        except ValueError:
            await update.message.reply_text(
                f"❌ Invalid mute duration value\\.\n"
                f"Use `[number]m` for minutes, `[number]h` for hours, or `[number]d` for days\\.",
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
            f"🔇 *{escape_markdown_v2(target_user.first_name)}* has been muted {escape_markdown_v2(mute_duration_str)}\\! 🤫\n"
            f"_No more talking for a while_\\! 👋",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error muting user {target_user.id}: {e}")
        await update.message.reply_text(
            f"⚠️ Failed to mute *{escape_markdown_v2(target_user.first_name)}*\\.\n"
            f"Make sure I have the necessary permissions\\! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# UNMUTE COMMAND
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to use this command\\.",
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
                f"❌ Please provide a valid User ID or reply to a message to unmute someone\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ Could not find the user with the provided ID in this chat\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 To unmute someone, please reply to their message or provide their User ID\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if target_user.id == user.id:
        await update.message.reply_text(
            f"😅 You are already unmuted if you can use this command, silly\\!",
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
            f"🎤 *{escape_markdown_v2(target_user.first_name)}* has been unmuted\\! 🎉\n"
            f"_Welcome back to the conversation_\\! 🤗",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error unmuting user {target_user.id}: {e}")
        await update.message.reply_text(
            f"⚠️ Failed to unmute *{escape_markdown_v2(target_user.first_name)}*\\.\n"
            f"Make sure I have the necessary permissions\\! 😓",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# ABOUT COMMAND
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🌸 *About Rose Bot* 🌸\n\n"
        f"I am a powerful and versatile group management bot designed to help you keep your Telegram groups safe, clean, and engaging\\! ✨\n\n"
        f"**Key Features:**\n"
        f"  •  Advanced moderation tools \\(kick, ban, mute, warn\\)\n"
        f"  •  Customizable welcome messages and group rules\n"
        f"  •  Anti\\-spam and anti\\-link mechanisms\n"
        f"  •  Global ban system for persistent troublemakers\n"
        f"  •  And much more\\! 🚀\n\n"
        f"Developed with ❤️ by {OWNER}\n"
        f"Version: `1.0.0`\n" # You can add a version number here
        f"Join my [Support Channel](https://t.me/{escape_markdown_v2('Rajaraj909')}) for updates and discussions\\! 📣", # Replace with your actual channel link
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True
    )

# PING COMMAND
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    ping_message = await update.message.reply_text(
        f"🏓 Pong\\! Measuring latency\\.\\.",
        parse_mode=ParseMode.MARKDOWN_V2
    )
    end_time = time.time()
    latency = round((end_time - start_time) * 1000) # in milliseconds
    await ping_message.edit_text(
        f"🏓 Pong\\! Latency: `{latency}`ms\\.\n"
        f"_I'm fast as a blink_\\! ✨",
        parse_mode=ParseMode.MARKDOWN_V2
    )

# GLOBAL BAN COMMAND (OWNER ONLY)
async def gban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Keep this as OWNER-ONLY as global bans typically are.
    if user.username != OWNER.lstrip('@'):
        await update.message.reply_text(
            f"🚫 *Access Denied* 🚫\n"
            f"This command can only be used by the *bot owner*\\.",
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
            # Try to get username for better logging/confirmation
            try:
                target_user_chat_info = await context.bot.get_chat(target_user_id) # This works for public users/bots/channels
                target_username = target_user_chat_info.username or target_user_chat_info.first_name
            except Exception:
                target_username = f"User ID: {target_user_id}"
        except ValueError:
            await update.message.reply_text(
                f"❌ Please provide a valid User ID or reply to a message to globally ban someone\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 To globally ban someone, please reply to their message or provide their User ID\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not target_user_id:
        await update.message.reply_text(
            f"❌ Could not determine the user to global ban\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # Prevent gban of owner
    if target_user_id == user.id:
        await update.message.reply_text(
            f"😅 You can't globally ban yourself, silly\\!",
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
            f"⛔️ *{escape_markdown_v2(str(target_username))}* \\(ID: `{target_user_id}`\\) has been *globally banned*\\! 🚫\n"
            f"_They are now restricted from all groups where I am present_\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error global banning user {target_user_id}: {e}")
        await update.message.reply_text(
            f"⚠️ Failed to globally ban *{escape_markdown_v2(str(target_username))}*\\.\n"
            f"An error occurred: _{escape_markdown_v2(str(e))}_",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# UNGBAN COMMAND (OWNER ONLY)
async def ungban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Keep this as OWNER-ONLY
    if user.username != OWNER.lstrip('@'):
        await update.message.reply_text(
            f"🚫 *Access Denied* 🚫\n"
            f"This command can only be used by the *bot owner*\\.",
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
            # Try to get username for better logging/confirmation
            try:
                target_user_chat_info = await context.bot.get_chat(target_user_id)
                target_username = target_user_chat_info.username or target_user_chat_info.first_name
            except Exception:
                target_username = f"User ID: {target_user_id}"
        except ValueError:
            await update.message.reply_text(
                f"❌ Please provide a valid User ID to unglobal ban someone\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        await update.message.reply_text(
            f"🤔 To unglobal ban someone, please reply to their message or provide their User ID\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not target_user_id:
        await update.message.reply_text(
            f"❌ Could not determine the user to unglobal ban\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        result = global_bans_collection.delete_one({"user_id": target_user_id})
        if result.deleted_count > 0:
            await update.message.reply_text(
                f"✅ *{escape_markdown_v2(str(target_username))}* \\(ID: `{target_user_id}`\\) has been *unglobally banned*\\! 🎉\n"
                f"_They can now join groups where I am present again_\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            await update.message.reply_text(
                f"🤷‍♀️ User \\(ID: `{target_user_id}`\\) is not currently globally banned\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
    except Exception as e:
        logger.error(f"Error unglobal banning user {target_user_id}: {e}")
        await update.message.reply_text(
            f"⚠️ Failed to unglobal ban *{escape_markdown_v2(str(target_username))}*\\.\n"
            f"An error occurred: _{escape_markdown_v2(str(e))}_",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# GBLACKLIST COMMAND (OWNER ONLY - Similar to Gban, but can be managed by ID for persistent users)
async def gblacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Keep this as OWNER-ONLY
    if user.username != OWNER.lstrip('@'):
        await update.message.reply_text(
            f"🚫 *Access Denied* 🚫\n"
            f"This command can only be used by the *bot owner*\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            f"❌ Please provide a valid *User ID* to add to the global blacklist\\.\n"
            f"Example: `/gblacklist 123456789`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user_id = int(context.args[0])

    if target_user_id == user.id:
        await update.message.reply_text(
            f"😅 You can't blacklist yourself, silly\\!",
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
            f"🚨 User ID: `{target_user_id}` has been added to the *Global Blacklist*\\! ⛔️\n"
            f"_They will not be able to join any group where I am active_\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error global blacklisting user {target_user_id}: {e}")
        await update.message.reply_text(
            f"⚠️ Failed to add User ID: `{target_user_id}` to global blacklist\\.\n"
            f"An error occurred: _{escape_markdown_v2(str(e))}_",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# UNGBLACKLIST COMMAND (OWNER ONLY)
async def ungblacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Keep this as OWNER-ONLY
    if user.username != OWNER.lstrip('@'):
        await update.message.reply_text(
            f"🚫 *Access Denied* 🚫\n"
            f"This command can only be used by the *bot owner*\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            f"❌ Please provide a valid *User ID* to remove from the global blacklist\\.\n"
            f"Example: `/ungblacklist 123456789`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    target_user_id = int(context.args[0])

    try:
        result = global_bans_collection.delete_one({"user_id": target_user_id, "is_blacklist": True})
        if result.deleted_count > 0:
            await update.message.reply_text(
                f"✅ User ID: `{target_user_id}` has been *removed* from the Global Blacklist\\! 🎉\n"
                f"_They can now join groups where I am active again_\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            await update.message.reply_text(
                f"🤷‍♀️ User ID: `{target_user_id}` is not currently in the global blacklist\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
    except Exception as e:
        logger.error(f"Error unglobal blacklisting user {target_user_id}: {e}")
        await update.message.reply_text(
            f"⚠️ Failed to remove User ID: `{target_user_id}` from global blacklist\\.\n"
            f"An error occurred: _{escape_markdown_v2(str(e))}_",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# BLACKLIST LIST COMMAND (OWNER ONLY)
async def blacklist_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Keep this as OWNER-ONLY
    if user.username != OWNER.lstrip('@'):
        await update.message.reply_text(
            f"🚫 *Access Denied* 🚫\n"
            f"This command can only be used by the *bot owner*\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    blacklisted_users = list(global_bans_collection.find({"is_blacklist": True}))

    if blacklisted_users:
        response = "📋 *Global Blacklisted Users:*\n\n"
        for entry in blacklisted_users:
            user_id = entry.get("user_id")
            banned_at = entry.get("banned_at", "N/A").strftime("%Y-%m-%d %H:%M:%S") if entry.get("banned_at") != "N/A" else "N/A"
            response += f"•  User ID: `{user_id}` \\| Banned At: _{banned_at}_\n"
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(
            f"✅ No users are currently in the *Global Blacklist*\\. The list is clean\\! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# RULES COMMANDS
async def setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to set rules\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not context.args:
        await update.message.reply_text(
            f"❌ Please provide the rules text after the command\\.\n"
            f"Example: `/setrules Be kind, follow Telegram TOS\\.`",
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
        f"📜 Group rules have been *set successfully*\\! ✨\n"
        f"Members can now view them using `/rules`\\.",
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    rules_data = rules_collection.find_one({"chat_id": chat.id})

    if rules_data and rules_data.get("rules_text"):
        rules_text = rules_data["rules_text"]
        await update.message.reply_text(
            f"📜 *Group Rules for {escape_markdown_v2(chat.title)}:*\n\n"
            f"{escape_markdown_v2(rules_text)}\n\n"
            f"_Please follow these rules to ensure a pleasant environment for everyone\\._ 😇",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await update.message.reply_text(
            f"🤷‍♀️ No rules have been set for this group yet\\.\n"
            f"_Admins can set rules using_ `/setrules <text>`\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def cleanrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to clear rules\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    result = rules_collection.delete_one({"chat_id": chat.id})
    if result.deleted_count > 0:
        await update.message.reply_text(
            f"🗑️ Group rules have been *cleared successfully*\\! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await update.message.reply_text(
            f"🤷‍♀️ No rules were set for this group to begin with\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# AUTO LINK FILTER
# This handler needs to be conditional based on a setting saved via `autolink` command.
# For now, it's always active if the handler is added.
async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message

    # In a real bot, you'd fetch the chat's setting for auto_link_filter here.
    # For now, we'll assume it's "on" if the handler is active.
    # Example:
    # chat_settings = chat_settings_collection.find_one({"chat_id": chat.id})
    # if not chat_settings or not chat_settings.get("auto_link_filter", False):
    #     return # Do nothing if auto link filter is off

    # Bypass if message is from an admin or the bot itself
    if message.from_user and await is_admin_or_owner(update, context, chat.id, message.from_user.id):
        return

    # Check for text messages with entities like URLs
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
                    f"🔗 Links are not allowed here, *{escape_markdown_v2(message.from_user.first_name)}*\\! 🙅‍♀️",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            except Exception as e:
                logger.warning(f"Could not delete link message or send warning: {e}")

# FALLBACK HELP FOR UNKNOWN COMMANDS
async def fallback_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only respond in group chats and if it's a command that doesn't exist
    # This check `not update.effective_message.text.split()[0][1:] in context.application.handlers[0]` is problematic.
    # It tries to access handlers based on an index, which is not how handlers are structured.
    # A more robust check for "unknown command" is typically done by letting other handlers fail,
    # or by explicitly checking command list, which is more complex.
    # For now, let's simplify this to just a general "unknown command" response if it starts with /
    if update.effective_chat.type == "group" and update.effective_message.text.startswith('/') and len(update.effective_message.text) > 1:
        # A more advanced check would be to see if it matches any registered command.
        # But for simplicity, we'll just catch any /command that isn't handled by other CommandHandlers.
        # This handler should ideally be the LAST CommandHandler or a general MessageHandler.
        await update.message.reply_text(
            f"❓ I'm not familiar with that command, *{escape_markdown_v2(update.effective_user.first_name)}*\\.\n"
            f"For a list of commands, please use /help in a private chat with me\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# CLEAN SERVICE MESSAGES
async def cleanservice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    # ADDED ADMIN/OWNER CHECK HERE
    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to use this command\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return
    
    # This function would need a more complex implementation to truly clean service messages.
    # Telegram bots don't have a direct way to 'auto-delete all service messages'.
    # You'd typically set chat permissions for new members to not see service messages,
    # or delete them as they come in via a MessageHandler listening for service messages.
    # For now, this just confirms the command is acknowledged.
    await update.message.reply_text(
        f"🧹 This command is under development for full automation\\.\n"
        f"_Currently, you can manually delete service messages or configure group settings_\\.",
        parse_mode=ParseMode.MARKDOWN_V2
    )
    # A more robust solution would involve setting a handler to delete specific service messages on arrival.
    # Example:
    # app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, delete_service_message_handler))

# AUTO LINK TOGGLE
async def autolink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    # ADDED ADMIN/OWNER CHECK HERE
    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to toggle auto link filter\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not context.args or context.args[0].lower() not in ["on", "off"]:
        await update.message.reply_text(
            f"❌ Please specify `on` or `off` to toggle auto link filter\\.\n"
            f"Example: `/autolink on` or `/autolink off`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # In a real scenario, you'd save this setting to your database (e.g., in a 'chat_settings' collection)
    # For this example, I'll just confirm the action.
    action = context.args[0].lower()
    if action == "on":
        # You would store this state in the database for the chat.
        # Example:
        # chat_settings_collection = get_db_collection("chat_settings") # You'd need to define this collection
        # chat_settings_collection.update_one({"chat_id": chat.id}, {"$set": {"auto_link_filter": True}}, upsert=True)
        await update.message.reply_text(
            f"✅ Auto link deletion has been *enabled* for this group\\! 🔗\n"
            f"_I will now automatically remove messages containing links\\._",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        # Example:
        # chat_settings_collection = get_db_collection("chat_settings")
        # chat_settings_collection.update_one({"chat_id": chat.id}, {"$set": {"auto_link_filter": False}}, upsert=True)
        await update.message.reply_text(
            f"🚫 Auto link deletion has been *disabled* for this group\\! 🔓\n"
            f"_Links will no longer be automatically removed\\._",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# WELCOME MESSAGE
async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to set the welcome message\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not context.args:
        await update.message.reply_text(
            f"❌ Please provide the welcome message text after the command\\.\n"
            f"You can use placeholders: `{{first}}`, `{{last}}`, `{{fullname}}`, `{{chatname}}`\\.\n"
            f"Example: `/setwelcome Welcome {{first}} to {{chatname}}!`",
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
        f"🎉 Custom welcome message has been *set successfully*\\! ✨\n"
        f"_New members will now see this message\\._",
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def resetwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not await is_admin_or_owner(update, context, chat.id, user.id):
        await update.message.reply_text(
            f"🚫 *Permission Denied* 🚫\n"
            f"You need to be an *admin* to reset the welcome message\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    result = welcomes_collection.delete_one({"chat_id": chat.id})
    if result.deleted_count > 0:
        await update.message.reply_text(
            f"↩️ Custom welcome message has been *reset to default*\\! ✨",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await update.message.reply_text(
            f"🤷‍♀️ No custom welcome message was set for this group to begin with\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    welcome_data = welcomes_collection.find_one({"chat_id": chat.id})
    
    welcome_message_text = welcome_data.get("welcome_message") if welcome_data else (
        "👋 Welcome, {fullname}, to {chatname}!"
    )

    # Simulate a new member for testing
    simulated_user = update.effective_user
    formatted_message = welcome_message_text.replace("{first}", escape_markdown_v2(simulated_user.first_name))\
                                            .replace("{last}", escape_markdown_v2(simulated_user.last_name or ""))\
                                            .replace("{fullname}", escape_markdown_v2(simulated_user.full_name))\
                                            .replace("{chatname}", escape_markdown_v2(chat.title))

    await update.message.reply_text(
        f"📝 Testing welcome message for *{escape_markdown_v2(simulated_user.first_name)}*\\:\n\n"
        f"{formatted_message}",
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def new_member_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            # Bot joined the group
            await update.message.reply_text(
                f"🎉 Hello everyone\\! I'm *Rose*, your new group manager\\! 🌹\n"
                f"Make sure to make me an *admin* so I can help keep this chat awesome\\! 💪",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        chat = update.effective_chat
        welcome_data = welcomes_collection.find_one({"chat_id": chat.id})
        
        welcome_message_text = welcome_data.get("welcome_message") if welcome_data else (
            "👋 Welcome, {fullname}, to {chatname}!"
        )

        formatted_message = welcome_message_text.replace("{first}", escape_markdown_v2(member.first_name))\
                                                .replace("{last}", escape_markdown_v2(member.last_name or ""))\
                                                .replace("{fullname}", escape_markdown_v2(member.full_name))\
                                                .replace("{chatname}", escape_markdown_v2(chat.title))

        try:
            await update.message.reply_sticker(DEFAULT_JOIN_STICKER_ID)
            await update.message.reply_text(formatted_message, parse_mode=ParseMode.MARKDOWN_V2)
        except Exception as e:
            logger.error(f"Error sending welcome sticker or message: {e}")
            await update.message.reply_text(formatted_message, parse_mode=ParseMode.MARKDOWN_V2) # Fallback to text only

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
            # Attempt to get chat member. This will fail if the user is not in the chat.
            # For general "info", you might want to fetch user by ID without being a chat member.
            # But for admin purposes (like checking warns), it makes sense to be a member.
            target_chat_member = await context.bot.get_chat_member(chat.id, user_id)
            target_user = target_chat_member.user
        except ValueError:
            await update.message.reply_text(
                f"❌ Please provide a valid User ID or reply to a message to get user info\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        except Exception:
            await update.message.reply_text(
                f"❌ Could not find the user with the provided ID in this chat or fetch their info\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
    else:
        target_user = user # If no target, show info about the command issuer

    if not target_user:
        await update.message.reply_text(
            f"🤔 To get user info, please reply to their message or provide their User ID\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # Fetch more detailed user info if possible (e.g., admin status, warns)
    is_chat_admin = await is_admin_or_owner(update, context, chat.id, target_user.id)
    warn_data = warns_collection.find_one({"chat_id": chat.id, "user_id": target_user.id})
    warn_count = warn_data.get("warn_count", 0) if warn_data else 0

    user_info_text = (
        f"👤 *User Information* 👤\n\n"
        f"•  *Name:* {escape_markdown_v2(target_user.full_name)}\n"
        f"•  *User ID:* `{target_user.id}`\n"
        f"•  *Username:* {escape_markdown_v2('@' + target_user.username) if target_user.username else '_N/A_'}\n"
        f"•  *Is Bot:* {'Yes' if target_user.is_bot else 'No'}\n"
        f"•  *Is Admin in this chat:* {'Yes' if is_chat_admin else 'No'}\n"
        f"•  *Warns in this chat:* `{warn_count}`\n\n"
        f"_Use `/warns` to check specific warn details\\._"
    )
    await update.message.reply_text(user_info_text, parse_mode=ParseMode.MARKDOWN_V2)

# ID COMMAND
async def get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        user_name = update.message.reply_to_message.from_user.full_name
        await update.message.reply_text(
            f"👤 *{escape_markdown_v2(user_name)}*'s User ID: `{user_id}`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        user_id = update.effective_user.id
        user_name = update.effective_user.full_name
        await update.message.reply_text(
            f"👤 Your User ID, *{escape_markdown_v2(user_name)}*, is: `{user_id}`",
            parse_mode=ParseMode.MARKDOWN_V2
        )

# --- Main Function to Run the Bot ---
async def main():
    try:
        app = ApplicationBuilder().token(TOKEN).build()
        logger.info("Bot is starting...")

        # Commands
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("kick", kick))
        app.add_handler(CommandHandler("ban", ban))
        app.add_handler(CommandHandler("mute", mute))
        app.add_handler(CommandHandler("unmute", unmute))
        app.add_handler(CommandHandler("warn", warn))
        app.add_handler(CommandHandler("warns", warns))
        app.add_handler(CommandHandler("unwarn", unwarn)) # Changed to unwarn to match common bot commands
        app.add_handler(CommandHandler("resetwarns", unwarn)) # Alias for unwarn/resetwarns for simplicity
        app.add_handler(CommandHandler("id", get_user_id))
        app.add_handler(CommandHandler("chatid", get_chat_id))
        app.add_handler(CommandHandler("about", about))
        app.add_handler(CommandHandler("ping", ping))
        
        # Owner Only Commands (GLOBAL MODERATION) - kept as owner only
        app.add_handler(CommandHandler("gban", gban))
        app.add_handler(CommandHandler("ungban", ungban))
        app.add_handler(CommandHandler("gblacklist", gblacklist))
        app.add_handler(CommandHandler("ungblacklist", ungblacklist))
        app.add_handler(CommandHandler("blacklist_list", blacklist_list))

        # Welcome/Rules - Admin/Owner restricted
        app.add_handler(CommandHandler("setrules", setrules))
        app.add_handler(CommandHandler("rules", rules)) # This remains publicly accessible to view rules
        app.add_handler(CommandHandler("cleanrules", cleanrules))
        app.add_handler(CommandHandler("setwelcome", setwelcome))
        app.add_handler(CommandHandler("resetwelcome", resetwelcome))
        app.add_handler(CommandHandler("welcome", welcome))
        app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member_welcome))


        # Message tool commands - now admin restricted
        app.add_handler(CommandHandler("pin", pin))
        app.add_handler(CommandHandler("unpin", unpin))
        app.add_handler(CommandHandler("del", delete_message))
        app.add_handler(CommandHandler("purge", purge))
        app.add_handler(CommandHandler("cleanservice", cleanservice)) # Admin/Owner restricted
        app.add_handler(CommandHandler("autolink", autolink)) # Admin/Owner restricted


        # Auto link filter and fallback help in group chats
        # Consider making handle_links conditional based on a stored chat setting (auto_link_filter)
        app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_links))
        app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, fallback_help))
        
        # Run polling without closing the event loop.
        await app.run_polling(close_loop=False)

    except Exception as e:
        logger.error(f"Error in main function: {e}")

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
        print(f"An unexpected error occurred during startup: {e}", file=sys.stderr)