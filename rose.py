# coding=utf-8
import nest_asyncio
nest_asyncio.apply()

import asyncio
import time
import sys
import logging
from datetime import datetime

from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# Enable logging to see bot activities on console
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
TOKEN = "7902720317:AAH-qV2E1qGHG95HG1wvZHgB2L18JD6O2g"  # Replace with your actual token
OWNER = "@bhanuxyz2"
warn_limit = 3
warns = {}
banlink_enabled = True
blocklist = set()
blocklist_mode = "mute"
locked = {"links": False, "photos": False, "all": False}
welcome_enabled = True
welcome_msg = "👋 Welcome!"
rules_msg = "📜 Be respectful. No spam."

# ** Sticker IDs (Replace with your actual sticker file IDs) **
JOIN_STICKER_ID = "CAACAgIAAxkBAAIC3mWZ7WvQzQe5F2l3b3sQ2M1d4QABfQACaQMAAm2YgUrpL3z-X7u4NzQE" # Example ID, replace this
LEAVE_STICKER_ID = "CAACAgIAAxkBAAIC4WWZ7XCz1e-x_b2p5I3S1Q1j5QABfQACbgMAAm2YgUtjK7t1e6dONzQE" # Example ID, replace this


# --- Helper Function to Resolve Target User ID ---
async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            arg = context.args[0].lstrip("@")
            return int(arg)
        except ValueError:
            await update.message.reply_text("🗣️ अरे भाईया, 💎 यूज़र आइडी सही-सही डालिए न! 🤓")
            return None
    else:
        await update.message.reply_text("👀 ई सुनो! 💬 केकरो मेसेज पर 𝗥𝗲𝗽𝗹𝘆 करो चाहे 🆔 यूज़र आइडी दे दो! 😎")
        return None

# --- General Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    username = f"@{user.username}" if user.username else user.full_name
    
    # ** Enhanced Starting Animation (Full Bihari Style with Emojis) **
    loading_messages = [
        "💖 𝐋", "💖 𝐋𝐨", "💖 𝐋𝐨𝐚", "💖 𝐋𝐨𝐚𝐝", "💖 𝐋𝐨𝐚𝐝𝐢", "💖 𝐋𝐨𝐚𝐝𝐢𝐧", "💖 𝐋𝐨𝐚𝐝𝐢𝐧𝐠",
        "💖 𝐋𝐨𝐚𝐝𝐢𝐧𝐠. ⏳", "💖 𝐋𝐨𝐚𝐝𝐢𝐧𝐠.. ⌛", "💖 𝐋𝐨𝐚𝐝𝐢𝐧𝐠... 💫", "💖 𝐋𝐨𝐚𝐝𝐢𝐧𝐠.... ✨",
        "💫 𝐋𝐨𝐚𝐝 होत है, 𝐘𝐚𝐫!  تھوڑا صبروا राखअ... 🧐", 
        "✨ 𝐒𝐚𝐛 𝐣𝐚𝐝𝐮 𝐜𝐡𝐚𝐥 𝐫𝐚𝐡𝐚 𝐡𝐚𝐢, 💎 रउआ इंतज़ार करीं ज़रा... 🕰️", 
        "🎀 𝐓𝐚𝐢𝐲𝐚𝐫𝐢 𝐛𝐡𝐚𝐫𝐩𝐨𝐨𝐫 𝐜𝐡𝐚𝐥 𝐫𝐚𝐡𝐢 𝐡𝐚𝐢, 🍫 बाबू... 🚀",
        "💅 𝐒𝐚𝐛 𝐞𝐤 𝐝𝐚𝐦 𝐅𝐢𝐭 𝐤𝐚𝐫 𝐫𝐚𝐡𝐞 𝐡𝐚𝐢𝐧, 😎 बस आ ही गइनी... ✅", 
        "💖 𝐇𝐨 𝐠𝐚𝐢𝐥, 𝐘𝐚𝐫! 💯 𝐉𝐚𝐥𝐝𝐢 𝐚𝐚𝐲𝐞𝐧𝐠𝐞, 𝐑𝐨𝐜𝐤 𝐤𝐚𝐫𝐧𝐞... 🎶"
    ]
    
    lols = await update.message.reply_text("💖 𝐒𝐡𝐮𝐫𝐮 𝐤𝐚𝐫 𝐫𝐚𝐡େ 𝐡𝐚𝐢𝐧, 𝐘𝐚𝐫! 🚀")
    for text in loading_messages:
        await lols.edit_text(f"**{text}**", parse_mode="Markdown")
        await asyncio.sleep(0.18) # Slightly increased sleep for better readability
    await asyncio.sleep(0.7)
    await lols.delete()

    # Get user profile photo if available
    photos = await context.bot.get_user_profile_photos(user.id, limit=1)
    
    welcome_text = (
        f"👑 **𝐀𝐚𝐡 𝐆𝐚𝐢𝐥𝐚 𝐭𝐮, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣!** 👑\n\n"
        f"• ✨ *𝐍𝐚𝐚𝐦:* `{user.full_name}`\n"
        f"• 🎀 *𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞𝐰𝐚:* `{username}`\n"
        f"• 💖 *𝐔𝐬𝐞𝐫 𝐈𝐃:* `{user.id}`\n"
        f"• 🌸 *𝐊𝐚𝐛 𝐬𝐞 𝐚𝐚𝐲𝐚𝐥 𝐡𝐚:* `{user.language_code if user.language_code else '𝐏𝐚𝐭𝐚𝐚𝐡𝐢 𝐧𝐚𝐡𝐢 𝐛𝐚'}`\n\n"
        f"✨ *𝐇𝐚𝐦𝐫𝐚 {chat.title if chat.title else '𝐞 𝐠𝐫𝐨𝐮𝐩𝐰𝐚'} 𝐦𝐞𝐢𝐧 𝐭𝐨𝐡𝐚𝐫𝐚 𝐬𝐰𝐚𝐠𝐚𝐭 𝐛𝐚! 𝐌𝐚𝐣𝐚 𝐤𝐚𝐫𝐢𝐲𝐞, 𝐘𝐚𝐫! 🥳* ✨"
    )
    
    if photos.total_count > 0:
        photo_file = photos.photos[0][0]
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_file.file_id,
            caption=welcome_text,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_list = """
🧠 💫 *𝐑𝐨𝐬𝐞𝐁𝐨𝐭 𝐤𝐞 𝐒𝐚𝐫𝐤𝐚𝐫𝐢 𝐍𝐢𝐲𝐚𝐦𝐰𝐚 𝐚𝐮𝐫 𝐊𝐚𝐦𝐚𝐧𝐝𝐬* 👑

💎 *𝐆𝐞𝐧𝐞𝐫𝐚𝐥 𝐁𝐚𝐚𝐭:*
  /start - 𝐀𝐩𝐧𝐞 𝐛𝐚𝐚𝐫𝐞 𝐦𝐞𝐢𝐧 𝐛𝐚𝐭𝐚𝐞𝐧𝐠𝐞 𝐚𝐮𝐫 𝐭𝐨𝐡𝐚𝐫𝐚 𝐬𝐰𝐚𝐠𝐚𝐭 𝐤𝐚𝐫𝐞𝐧𝐠𝐞. 👋
  /help - 𝐄 𝐬𝐚𝐛 𝐧𝐢𝐲𝐚𝐦 𝐚𝐮𝐫 𝐤𝐚𝐦𝐚𝐧𝐝𝐬 𝐝𝐞𝐤𝐡𝐚. 📜
  /neo - 𝐁𝐨𝐭 𝐤𝐞 𝐛𝐚𝐚𝐫𝐞 𝐦𝐞𝐢𝐧 𝐣𝐚𝐧𝐚. 🤖
  /ping - 𝐁𝐨𝐭 𝐤𝐞 𝐜𝐡𝐚𝐥𝐚𝐧𝐞 𝐤𝐞 𝐬𝐩𝐞𝐞𝐝 𝐝𝐞𝐤𝐡𝐚. 🚀
  /donate - 𝐏𝐚𝐢𝐬𝐚-𝐤𝐚𝐮𝐝𝐢 𝐝𝐞𝐧𝐚 𝐡𝐚𝐢 𝐭𝐨𝐡 𝐢𝐝𝐡𝐚𝐫 𝐚𝐚𝐨. 💸

💖 *𝐌𝐨𝐝𝐞𝐫𝐚𝐭𝐢𝐨𝐧* (💬 𝐑𝐞𝐩𝐥𝐲 𝐤𝐚𝐫 𝐤𝐞 𝐔𝐬𝐞𝐫 𝐤𝐞 𝐛𝐚𝐭𝐚𝐨 𝐲𝐚 𝐩𝐡𝐢𝐫 🆔 𝐔𝐬𝐞𝐫 𝐈𝐃 𝐝𝐞 𝐝𝐨):
  /warn <user id> - 𝐂𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐝𝐨. ⚠️
  /resetwarns <user id> - 𝐂𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐡𝐚𝐭𝐚𝐨. ✨
  /setwarnlimit <number> - 𝐂𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐤𝐞 𝐥𝐢𝐦𝐢𝐭 𝐬𝐞𝐭 𝐤𝐚𝐫𝐨. 🔢
  /ban <user id> - 𝐍𝐢𝐤𝐚𝐥 𝐟𝐞𝐧𝐤𝐨. 🚫
  /unban <user id> - 𝐖𝐚𝐩𝐚𝐬 𝐛𝐮𝐥𝐚𝐨. 🫂
  /kick <user id> - 𝐋𝐚𝐚𝐭 𝐦𝐚𝐚𝐫 𝐤𝐞 𝐧𝐢𝐤𝐚𝐥𝐨. 👢
  /mute <user id> - 𝟏 𝐠𝐡𝐚𝐧𝐭𝐚 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐜𝐡𝐮𝐩 𝐤𝐚𝐫𝐚 𝐝𝐨. 🔇
  /unmute <user id> - 𝐀𝐚𝐰𝐚𝐚𝐳 𝐰𝐚𝐩𝐚𝐬 𝐝𝐨. 🔊

✨ *𝐁𝐚𝐝𝐤𝐚 𝐋𝐨𝐠 𝐤𝐞 𝐊𝐚𝐚𝐦 (𝐀𝐝𝐦𝐢𝐧 𝐓𝐨𝐨𝐥𝐬):*
  /promote <user id> - 𝐁𝐚𝐝𝐤𝐚 𝐛𝐚𝐧𝐚𝐨. 👑
  /demote <user id> - 𝐂𝐡𝐡𝐨𝐭𝐤𝐚 𝐛𝐚𝐧𝐚𝐨. 📉
  /admins - 𝐒𝐚𝐛 𝐚𝐝𝐦𝐢𝐧 𝐤𝐞 𝐧𝐚𝐚𝐦 𝐝𝐞𝐤𝐡𝐨. 🧑‍⚖️

🔒 *𝐁𝐚𝐧𝐝 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐒𝐲𝐬𝐭𝐞𝐦 (𝐋𝐨𝐜𝐤 𝐒𝐲𝐬𝐭𝐞𝐦):*
  /lock [all|links|photos] - 𝐒𝐚𝐛 𝐛𝐚𝐧𝐝 𝐤𝐚𝐫𝐨. 🔐
  /unlock [all|links|photos] - 𝐒𝐚𝐛 𝐤𝐡𝐨𝐥𝐨. 🔓

🚫 *𝐅𝐚𝐥𝐭𝐮 𝐒𝐚𝐧𝐝𝐞𝐬𝐡 𝐑𝐨𝐤𝐧𝐞 𝐖𝐚𝐥𝐚 (𝐒𝐩𝐚𝐦 𝐅𝐢𝐥𝐭𝐞𝐫):*
  /banlink - 𝐋𝐢𝐧𝐤 𝐛𝐡𝐞𝐣𝐧𝐚 𝐛𝐚𝐧𝐝 𝐤𝐚𝐫𝐨 𝐲𝐚 𝐜𝐡𝐚𝐥𝐮 𝐤𝐚𝐫𝐨. 🔗
  /blocklist <shabd> - 𝐘𝐞 𝐬𝐡𝐚𝐛𝐝 𝐥𝐢𝐬𝐭 𝐦𝐞𝐢𝐧 𝐝𝐚𝐚𝐥𝐨. 📝
  /blocklistmode <mute|ban> - 𝐊𝐚𝐚𝐦 𝐝𝐞𝐤𝐡𝐨 𝐦𝐮𝐭𝐞 𝐲𝐚 𝐛𝐚𝐧. ⚔️

🌸 *𝐒𝐰𝐚𝐠𝐚𝐭 𝐊𝐚𝐫𝐞 𝐊𝐞 𝐒𝐲𝐬𝐭𝐞𝐦 (𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐒𝐲𝐬𝐭𝐞𝐦):*
  /welcome [on|off] - 𝐒𝐰𝐚𝐠𝐚𝐭 𝐬𝐚𝐧𝐝𝐞𝐬𝐡 𝐜𝐡𝐚𝐥𝐮 𝐲𝐚 𝐛𝐚𝐧𝐝 𝐤𝐚𝐫𝐨. 🥳
  /setwelcome <sandesh> - 𝐒𝐰𝐚𝐠𝐚𝐭 𝐬𝐚𝐧𝐝𝐞𝐬𝐡 𝐥𝐢𝐤𝐡𝐨. ✍️
  /cleanwelcome - 𝐒𝐰𝐚𝐠𝐚𝐭 𝐬𝐚𝐧𝐝𝐞𝐬𝐡 𝐦𝐢𝐭𝐚𝐨. 🗑️

📜 *𝐍𝐢𝐲𝐚𝐦 𝐊𝐚𝐧𝐮𝐧 (𝐑𝐮𝐥𝐞𝐬 𝐒𝐲𝐬𝐭𝐞𝐦):*
  /setrules <likh do> - 𝐍𝐢𝐲𝐚𝐦 𝐥𝐢𝐤𝐡 𝐝𝐨. 📄
  /rules - 𝐍𝐢𝐲𝐚𝐦 𝐝𝐞𝐤𝐡𝐨. ⚖️
  /cleanrules - 𝐍𝐢𝐲𝐚𝐦 𝐦𝐢𝐭𝐚 𝐝𝐨. 🧹

🎀 *𝐒𝐚𝐧𝐝𝐞𝐬𝐡 𝐤𝐞 𝐀𝐮𝐳𝐚𝐚𝐫 (𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐓𝐨𝐨𝐥𝐬):*
  /pin - 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐩𝐢𝐧 𝐤𝐚𝐫𝐨. 📌
  /unpin - 𝐏𝐢𝐧 𝐤𝐢𝐲𝐚 𝐡𝐮𝐚 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐡𝐚𝐭𝐚𝐨. 📍
  /del - 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭𝐚𝐨. ❌
  /purge <sankhya> - 𝐁𝐚𝐡𝐮𝐭 𝐬𝐚𝐚𝐫𝐚 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐞𝐤 𝐛𝐚𝐚𝐫 𝐦𝐞𝐢𝐧 𝐦𝐢𝐭𝐚𝐨. 💥
  /cleanservice [on|off] - 𝐒𝐞𝐫𝐯𝐢𝐜𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐬𝐚𝐚𝐟 𝐤𝐚𝐫𝐨. 🧹
"""
    await update.message.reply_text(command_list, parse_mode="Markdown")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t1 = time.time()
    msg = await update.message.reply_text("🏓 𝐏𝐢𝐧𝐠-𝐩𝐨𝐧𝐠 𝐤𝐡𝐞𝐥 𝐫𝐚𝐡𝐞 𝐡𝐚𝐢𝐧... 🎾")
    t2 = time.time()
    await msg.edit_text(f"🏓 𝐏𝐨𝐧𝐠: `{int((t2 - t1) * 1000)}ms` 💫 𝐁𝐚𝐡𝐮𝐭 𝐭𝐞𝐳, 𝐘𝐚𝐫! ⚡", parse_mode="Markdown")

async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💸 𝐇𝐮𝐦𝐤𝐞 𝐤𝐮𝐜𝐡 𝐩𝐚𝐢𝐬𝐚-𝐤𝐚𝐮𝐝𝐢 𝐝𝐞𝐛𝐚? 𝐈𝐝𝐡𝐚𝐫 𝐛𝐡𝐞𝐣𝐨: @NEOBLADE71 💖 𝐃𝐡𝐚𝐧𝐲𝐚𝐰𝐚𝐝! 🙏", parse_mode="Markdown")

async def neo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💠 *𝐇𝐮𝐦 𝐡𝐚𝐢𝐧 𝐑𝐨𝐬𝐞𝐁𝐨𝐭: 𝐄𝐡𝐢 𝐤𝐞 𝐛𝐚𝐚𝐫𝐞 𝐦𝐞𝐢𝐧 𝐛𝐚𝐚𝐭 𝐡𝐨 𝐫𝐚𝐡𝐚 𝐡𝐚𝐢* 🌟\n\n𝐁𝐚𝐧𝐚𝐰𝐚𝐥 𝐠𝐞𝐞𝐥 𝐛𝐚 {OWNER} 𝐤𝐞 𝐭𝐚𝐫𝐚𝐟 𝐬𝐞 ✨ 𝐋𝐞𝐠𝐞𝐧𝐝 𝐡𝐚𝐢 𝐡𝐮𝐦! 🏆", parse_mode="Markdown")

# --- Moderation Commands ---
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = await get_target_user(update, context)
    if uid is None:
        return
    warns[uid] = warns.get(uid, 0) + 1
    if warns[uid] >= warn_limit:
        await context.bot.ban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text(f"🚫 𝐄 𝐔𝐬𝐞𝐫 (𝐈𝐃: {uid}) 𝐤𝐞 {warn_limit} 𝐜𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐀𝐛 𝐧𝐢𝐤𝐚𝐥𝐨 𝐢𝐬𝐤𝐨, 𝐘𝐚𝐫! 💔 𝐓𝐚𝐭𝐚 𝐛𝐲𝐞-𝐛𝐲𝐞! 👋")
    else:
        await update.message.reply_text(f"⚠️ 𝐄 𝐔𝐬𝐞𝐫 (𝐈𝐃: {uid}) 𝐤𝐞 𝐜𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐦𝐢𝐥𝐚𝐥 𝐛𝐚! [{warns[uid]}/{warn_limit}] 𝐓𝐡𝐨𝐝𝐚 𝐝𝐡𝐲𝐚𝐧 𝐫𝐚𝐤𝐡𝐨, 𝐌𝐢𝐭𝐫𝐚! 🎀 𝐀𝐠𝐥𝐢 𝐛𝐚𝐚𝐫 𝐬𝐞 𝐧𝐚𝐡𝐢! 🚫")

async def resetwarns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = await get_target_user(update, context)
    if uid is None:
        return
    warns[uid] = 0
    await update.message.reply_text("✅ 𝐂𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐬𝐚𝐚𝐟 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐅𝐫𝐞𝐬𝐡 𝐬𝐭𝐚𝐫𝐭 𝐤𝐚𝐫𝐨, 𝐣𝐞𝐞! ✨ 𝐀𝐛 𝐤𝐨𝐢 𝐛𝐚𝐭𝐚 𝐧𝐚𝐡𝐢! 🥳")

async def setwarnlimit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global warn_limit
    if context.args:
        try:
            warn_limit = int(context.args[0])
            await update.message.reply_text(f"✅ 𝐂𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐤𝐞 𝐥𝐢𝐦𝐢𝐭 {warn_limit} 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐀𝐜𝐡𝐡𝐚 𝐬𝐞 𝐫𝐚𝐡𝐧𝐚, 𝐘𝐚𝐫! 💖 𝐒𝐚𝐦𝐚𝐣𝐡𝐚? 🤓")
        except ValueError:
            await update.message.reply_text("❌ 𝐒𝐚𝐡𝐢-𝐬𝐚𝐡𝐢 𝐧𝐮𝐦𝐛𝐞𝐫𝐰𝐚 𝐝𝐚𝐚𝐥, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣. 💅 𝐄𝐡 𝐤𝐚 𝐤𝐚𝐫 𝐫𝐚𝐡𝐚 𝐡𝐨? 🤦‍♀️")
    else:
        await update.message.reply_text(f"𝐀𝐛𝐡𝐢 𝐤𝐞 𝐜𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐥𝐢𝐦𝐢𝐭 {warn_limit} 𝐛𝐚. ✨ 𝐈𝐬𝐢 𝐩𝐞 𝐜𝐡𝐚𝐥𝐨! 🤝")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = await get_target_user(update, context)
    if uid is None:
        return
    await context.bot.ban_chat_member(update.effective_chat.id, uid)
    await update.message.reply_text(f"🚫 𝐄 𝐔𝐬𝐞𝐫 (𝐈𝐃: {uid}) 𝐤𝐞 𝐠𝐫𝐨𝐮𝐩 𝐬𝐞 𝐧𝐢𝐤𝐚𝐥 𝐝𝐞𝐞𝐧𝐢. 𝐂𝐡𝐚𝐥 𝐧𝐢𝐤𝐚𝐥, 𝐁𝐨𝐫𝐢𝐲𝐚-𝐛𝐢𝐬𝐭𝐚𝐫𝐚 𝐥𝐞 𝐤𝐞! 💔 👋")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = await get_target_user(update, context)
    if uid is None:
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text(f"✅ 𝐄 𝐔𝐬𝐞𝐫 (𝐈𝐃: {uid}) 𝐤𝐞 𝐰𝐚𝐩𝐚𝐬 𝐛𝐮𝐥𝐚 𝐥𝐢𝐲𝐚𝐢𝐧𝐢. 𝐀𝐚 𝐣𝐚𝐨, 𝐘𝐚𝐫! 💖 𝐌𝐢𝐥 𝐤𝐞 𝐫𝐚𝐡𝐞𝐧𝐠𝐞! 🫂")
    except Exception as e:
        await update.message.reply_text(f"❌ 𝐔𝐧𝐛𝐚𝐧 𝐧𝐚 𝐡𝐨 𝐩𝐚𝐲𝐚𝐥, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣: {e} 😥 𝐊𝐮𝐜𝐡 𝐠𝐚𝐝𝐛𝐚𝐝 𝐛𝐚! 🤷‍♀️")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = await get_target_user(update, context)
    if uid is None:
        return
    await context.bot.kick_chat_member(update.effective_chat.id, uid)
    await update.message.reply_text(f"👢 𝐄 𝐔𝐬𝐞𝐫 (𝐈𝐃: {uid}) 𝐤𝐞 𝐥𝐚𝐚𝐭 𝐦𝐚𝐚𝐫 𝐤𝐞 𝐧𝐢𝐤𝐚𝐥 𝐝𝐞𝐞𝐧𝐢. 𝐁𝐡𝐚𝐠𝐨, 𝐝𝐮𝐬𝐫𝐚 𝐝𝐮𝐧𝐢𝐲𝐚 𝐦𝐞𝐢𝐧! 👋")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = await get_target_user(update, context)
    if uid is None:
        return
    until_date = int(time.time()) + 3600
    perms = ChatPermissions(can_send_messages=False)
    await context.bot.restrict_chat_member(update.effective_chat.id, uid, permissions=perms, until_date=until_date)
    await update.message.reply_text(f"🔇 𝐄 𝐔𝐬𝐞𝐫 (𝐈𝐃: {uid}) 𝐤𝐞 𝟏 𝐠𝐡𝐚𝐧𝐭𝐚 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐜𝐡𝐮𝐩 𝐤𝐚𝐫𝐚 𝐝𝐞𝐞𝐧𝐢. 𝐒𝐡𝐡𝐡... 🤫 𝐍𝐨 𝐛𝐨𝐥-𝐛𝐚𝐜𝐡𝐚𝐧! 🙅‍♂️")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = await get_target_user(update, context)
    if uid is None:
        return
    perms = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True)
    await context.bot.restrict_chat_member(update.effective_chat.id, uid, permissions=perms)
    await update.message.reply_text(f"🔊 𝐄 𝐔𝐬𝐞𝐫 (𝐈𝐃: {uid}) 𝐤𝐞 𝐚𝐚𝐰𝐚𝐚𝐳 𝐰𝐚𝐩𝐚𝐬 𝐚𝐚 𝐠𝐚𝐢𝐥. 𝐀𝐛 𝐛𝐨𝐥 𝐬𝐚𝐤𝐨 𝐡𝐨, 𝐘𝐚𝐫! 🎤 𝐆𝐮𝐩𝐬𝐡𝐮𝐩 𝐤𝐚𝐫𝐨! 🗣️")

# --- Admin Commands ---
async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text(f"✅ 𝐄 𝐔𝐬𝐞𝐫 (𝐈𝐃: {uid}) 𝐤𝐞 𝐛𝐚𝐝𝐤𝐚 𝐛𝐚𝐧𝐚 𝐝𝐞𝐞𝐧𝐢! 👑 𝐉𝐚𝐢 𝐡𝐨 𝐌𝐚𝐡𝐚𝐫𝐚𝐣! 🌟")
    except Exception as e:
        await update.message.reply_text(f"❌ 𝐁𝐚𝐝𝐤𝐚 𝐧𝐚 𝐛𝐚𝐧 𝐩𝐚𝐲𝐚𝐥, 𝐘𝐚𝐫: {e} 💔 𝐊𝐮𝐜𝐡 𝐝𝐢𝐤𝐤𝐚𝐭 𝐛𝐚! 🤷‍♂️")

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text(f"✅ 𝐄 𝐔𝐬𝐞𝐫 (𝐈𝐃: {uid}) 𝐤𝐞 𝐜𝐡𝐡𝐨𝐭𝐤𝐚 𝐛𝐚𝐧𝐚 𝐝𝐞𝐞𝐧𝐢. 𝐀𝐛 𝐭𝐡𝐢𝐤 𝐬𝐞 𝐫𝐚𝐡𝐨, 𝐘𝐚𝐫! 💅 𝐍𝐢𝐲𝐚𝐦 𝐬𝐞 𝐜𝐡𝐚𝐥𝐨! 🚶‍♀️")
    except Exception as e:
        await update.message.reply_text(f"❌ 𝐂𝐡𝐡𝐨𝐭𝐤𝐚 𝐧𝐚 𝐛𝐚𝐧 𝐩𝐚𝐲𝐚𝐥, 𝐘𝐚𝐫: {e} 😥 𝐘𝐞 𝐭𝐨𝐡 𝐛𝐮𝐫𝐚 𝐡𝐮𝐚! 😔")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        admin_list = "\n".join([f"- {admin.user.full_name} ✨" for admin in admins])
        await update.message.reply_text(f"👑 𝐄 𝐠𝐫𝐨𝐮𝐩𝐰𝐚 𝐤𝐞 𝐬𝐚𝐛 𝐌𝐚𝐡𝐚𝐫𝐚𝐣 𝐚𝐮𝐫 𝐌𝐚𝐡𝐚𝐫𝐚𝐧𝐢 𝐡𝐚𝐢𝐧:\n{admin_list} 🤩")
    except Exception as e:
        await update.message.reply_text(f"❌ 𝐀𝐝𝐦𝐢𝐧 𝐤𝐞 𝐥𝐢𝐬𝐭 𝐧𝐚 𝐧𝐢𝐤𝐚𝐥 𝐩𝐚𝐲𝐚𝐥: {e} 😥 𝐀𝐟𝐬𝐨𝐬! 😞")

# --- Lock System Commands ---
async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🗣️ 𝐊𝐚 𝐛𝐚𝐧𝐝 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐛𝐚? [𝐚𝐥𝐥|𝐥𝐢𝐧𝐤𝐬|𝐩𝐡𝐨𝐭𝐨𝐬] 𝐃𝐡𝐚𝐧𝐠 𝐬𝐞 𝐛𝐚𝐭𝐚𝐨 𝐧𝐚! 🔒")
        return
    arg = context.args[0].lower()
    if arg in locked:
        locked[arg] = True
        await update.message.reply_text(f"🔒 {arg.capitalize()} 𝐛𝐚𝐧𝐝 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐒𝐮𝐫𝐚𝐤𝐬𝐡𝐢𝐭 𝐛𝐚, 𝐘𝐚𝐫! 🔐 𝐊𝐨𝐢 𝐟𝐢𝐤𝐚𝐫 𝐧𝐚𝐡𝐢! 💪")
    elif arg == "all":
        for key in locked:
            locked[key] = True
        await update.message.reply_text("🔒 𝐒𝐚𝐛 𝐤𝐮𝐜𝐡 𝐛𝐚𝐧𝐝 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐊𝐮𝐜𝐡 𝐧𝐚 𝐜𝐡𝐡𝐮𝐭𝐢! 💖 𝐅𝐮𝐥𝐥 𝐬𝐞𝐜𝐮𝐫𝐢𝐭𝐲! 🛡️")
    else:
        await update.message.reply_text("🤦‍♀️ 𝐆𝐚𝐥𝐚𝐭 𝐛𝐚𝐚𝐭 𝐛𝐨𝐥𝐚𝐭 𝐡𝐨, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣. '𝐚𝐥𝐥', '𝐥𝐢𝐧𝐤𝐬', 𝐲𝐚 '𝐩𝐡𝐨𝐭𝐨𝐬' 𝐛𝐨𝐥 𝐧𝐚. 💅")

async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🗣️ 𝐊𝐚 𝐤𝐡𝐨𝐥𝐞 𝐤𝐞 𝐛𝐚? [𝐚𝐥𝐥|𝐥𝐢𝐧𝐤𝐬|𝐩𝐡𝐨𝐭𝐨𝐬] 𝐃𝐡𝐚𝐧𝐠 𝐬𝐞 𝐛𝐚𝐭𝐚𝐨 𝐧𝐚! 🔓")
        return
    arg = context.args[0].lower()
    if arg in locked:
        locked[arg] = False
        await update.message.reply_text(f"🔓 {arg.capitalize()} 𝐤𝐡𝐮𝐥 𝐠𝐚𝐢𝐥. 𝐀𝐚𝐳𝐚𝐝𝐢, 𝐘𝐚𝐫! ✨ 𝐉𝐢𝐲𝐨 𝐚𝐮𝐫 𝐣𝐢𝐧𝐞 𝐝𝐨! 🕊️")
    elif arg == "all":
        for key in locked:
            locked[key] = False
        await update.message.reply_text("🔓 𝐒𝐚𝐛 𝐤𝐮𝐜𝐡 𝐤𝐡𝐮𝐥 𝐠𝐚𝐢𝐥. 𝐀𝐛 𝐜𝐡𝐚𝐦𝐤𝐨, 𝐡𝐨! 💖 𝐏𝐚𝐫𝐭𝐲 𝐡𝐨 𝐣𝐚𝐲𝐞! 🥳")
    else:
        await update.message.reply_text("🤦‍♀️ 𝐆𝐚𝐥𝐚𝐭 𝐛𝐚𝐚𝐭 𝐛𝐨𝐥𝐚𝐭 𝐡𝐨, 𝐒𝐰𝐞𝐞𝐭𝐢𝐞. '𝐚𝐥𝐥', '𝐥𝐢𝐧𝐤𝐬', 𝐲𝐚 '𝐩𝐡𝐨𝐭𝐨𝐬' 𝐛𝐨𝐥 𝐧𝐚. 🎀")

# --- Spam Filter Commands ---
async def banlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global banlink_enabled
    banlink_enabled = not banlink_enabled
    state = "𝐂𝐡𝐚𝐥𝐮 𝐡𝐨 𝐠𝐚𝐢𝐥 ✅" if banlink_enabled else "𝐁𝐚𝐧𝐝 𝐡𝐨 𝐠𝐚𝐢𝐥 ❌"
    await update.message.reply_text(f"🔗 𝐋𝐢𝐧𝐤 𝐟𝐢𝐥𝐭𝐞𝐫 𝐚𝐛 {state} 𝐛𝐚. 𝐊𝐨𝐢 𝐟𝐚𝐥𝐭𝐮 𝐥𝐢𝐧𝐤 𝐧𝐚 𝐛𝐡𝐞𝐣𝐞𝐠𝐚! 🚫 𝐒𝐚𝐦𝐚𝐣𝐡𝐚 𝐤𝐢 𝐧𝐚𝐡𝐢? 🧐", parse_mode="Markdown")

async def blocklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        current = ", ".join(blocklist) if blocklist else "𝐊𝐡𝐚𝐥𝐢 𝐛𝐚"
        await update.message.reply_text(f"𝐀𝐛𝐡𝐢 𝐤𝐞 𝐛𝐥𝐨𝐜𝐤𝐥𝐢𝐬𝐭: {current}. 𝐒𝐚𝐚𝐟-𝐬𝐮𝐭𝐡𝐫𝐚 𝐫𝐚𝐤𝐡𝐨, 𝐘𝐚𝐫! 🧹 𝐍𝐨 𝐠𝐚𝐧𝐝𝐚 𝐛𝐚𝐚𝐭! 🤬")
        return
    word = context.args[0].lower()
    blocklist.add(word)
    await update.message.reply_text(f"✅ '{word}' 𝐛𝐥𝐨𝐜𝐤𝐥𝐢𝐬𝐭 𝐦𝐞𝐢𝐧 𝐝𝐚𝐚𝐥 𝐝𝐞𝐞𝐧𝐢. 𝐍𝐚𝐤𝐚𝐫𝐚𝐭𝐦𝐚𝐤𝐭𝐚 𝐧𝐚𝐡𝐢 𝐜𝐡𝐚𝐥𝐞𝐠𝐢, 𝐣𝐞𝐞! 💅 𝐅𝐮𝐥𝐥 𝐩𝐨𝐬𝐢𝐭𝐢𝐯𝐢𝐭𝐲! 💖")

async def blocklistmode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global blocklist_mode
    if not context.args:
        await update.message.reply_text(f"𝐀𝐛𝐡𝐢 𝐤𝐞 𝐛𝐥𝐨𝐜𝐤𝐥𝐢𝐬𝐭 𝐦𝐨𝐝𝐞: {blocklist_mode}. 𝐂𝐡𝐮𝐧𝐨 𝐝𝐡𝐲𝐚𝐧 𝐬𝐞, 𝐘𝐚𝐫! 🤔 𝐆𝐚𝐝𝐛𝐚𝐝 𝐧𝐚 𝐡𝐨𝐧𝐚 𝐜𝐡𝐚𝐡𝐢𝐲𝐞! 🚫")
        return
    mode = context.args[0].lower()
    if mode in ["mute", "ban"]:
        blocklist_mode = mode
        await update.message.reply_text(f"✅ 𝐁𝐥𝐨𝐜𝐤𝐥𝐢𝐬𝐭 𝐦𝐨𝐝𝐞 {mode} 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐒𝐮𝐫𝐚𝐤𝐬𝐡𝐚 𝐜𝐡𝐚𝐥𝐮! 🛡️ 𝐀𝐛 𝐬𝐚𝐛 𝐬𝐞𝐟 𝐛𝐚! 🔐")
    else:
        await update.message.reply_text("🤦‍♀️ 𝐆𝐚𝐥𝐚𝐭 𝐦𝐨𝐝𝐞 𝐛𝐨𝐥𝐚𝐭 𝐡𝐨, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣. '𝐦𝐮𝐭𝐞' 𝐲𝐚 '𝐛𝐚𝐧' 𝐛𝐨𝐥. 💖 𝐊𝐨𝐢 𝐝𝐢𝐤𝐤𝐚𝐭 𝐧𝐚𝐡𝐢! 👍")

# --- Welcome System Commands ---
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global welcome_enabled
    if not context.args:
        await update.message.reply_text("𝐒𝐰𝐚𝐠𝐚𝐭 𝐬𝐚𝐧𝐝𝐞𝐬𝐡 𝐜𝐡𝐚𝐥𝐮 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐛𝐚 𝐲𝐚 𝐛𝐚𝐧𝐝? [𝐨𝐧|𝐨𝐟𝐟] 𝐃𝐡𝐚𝐧𝐠 𝐬𝐞 𝐛𝐚𝐭𝐚𝐨! 🌸")
        return
    arg = context.args[0].lower()
    if arg == "on":
        welcome_enabled = True
        await update.message.reply_text("✅ 𝐒𝐰𝐚𝐠𝐚𝐭 𝐬𝐚𝐧𝐝𝐞𝐬𝐡 𝐜𝐡𝐚𝐥𝐮 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐋𝐞𝐭's 𝐩𝐚𝐫𝐭𝐲! 🥳")
    elif arg == "off":
        welcome_enabled = False
        await update.message.reply_text("❌ 𝐒𝐰𝐚𝐠𝐚𝐭 𝐬𝐚𝐧𝐝𝐞𝐬𝐡 𝐛𝐚𝐧𝐝 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐂𝐡𝐮𝐩𝐜𝐡𝐚𝐚𝐩 𝐫𝐚𝐡𝐨! 🤫 𝐍𝐨 𝐦𝐨𝐫𝐞 𝐰𝐞𝐥𝐜𝐨𝐦𝐞! 🤐")
    else:
        await update.message.reply_text("🤦‍♀️ 𝐆𝐚𝐥𝐚𝐭 𝐛𝐚𝐚𝐭 𝐛𝐨𝐥𝐚𝐭 𝐡𝐨, 𝐃𝐚𝐫𝐥𝐢𝐧𝐠. '𝐨𝐧' 𝐲𝐚 '𝐨𝐟𝐟' 𝐛𝐨𝐥. 🎀 𝐒𝐚𝐦𝐚𝐣𝐡𝐚 𝐤𝐢 𝐧𝐚𝐡𝐢? 🧐")

async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global welcome_msg
    if not context.args:
        await update.message.reply_text("𝐊𝐚 𝐰𝐞𝐥𝐜𝐨𝐦𝐞 𝐬𝐚𝐧𝐝𝐞𝐬𝐡 𝐥𝐢𝐤𝐡𝐞 𝐤𝐞 𝐛𝐚? 𝐋𝐢𝐤𝐡 𝐝𝐨 𝐧𝐚! 💖 𝐒𝐮𝐧𝐝𝐚𝐫 𝐬𝐚 𝐥𝐢𝐤𝐡𝐧𝐚! ✍️")
        return
    welcome_msg = " ".join(context.args)
    await update.message.reply_text(f"✅ 𝐒𝐰𝐚𝐠𝐚𝐭 𝐬𝐚𝐧𝐝𝐞𝐬𝐡 𝐬𝐞𝐭 𝐡𝐨 𝐠𝐚𝐢𝐥:\n{welcome_msg}\n\n𝐁𝐚𝐡𝐮𝐭 𝐬𝐮𝐧𝐝𝐚𝐫, 𝐘𝐚𝐫! ✨ 𝐄𝐤 𝐝𝐚𝐦 𝐅𝐢𝐭! 👍")

async def cleanwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global welcome_msg
    welcome_msg = ""
    await update.message.reply_text("✅ 𝐒𝐰𝐚𝐠𝐚𝐭 𝐬𝐚𝐧𝐝𝐞𝐬𝐡 𝐬𝐚𝐚𝐟 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐍𝐚𝐲𝐚 𝐬𝐡𝐮𝐫𝐮 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐛𝐚! 🎨 𝐅𝐫𝐞𝐬𝐡 𝐩𝐚𝐠𝐞! 📄")

# --- Rules System Commands ---
async def setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global rules_msg
    if not context.args:
        await update.message.reply_text("𝐍𝐢𝐲𝐚𝐦 𝐤𝐚𝐧𝐮𝐧 𝐥𝐢𝐤𝐡𝐨 𝐧𝐚! 📜 𝐒𝐚𝐛 𝐤𝐞 𝐥𝐢𝐲𝐞 𝐳𝐚𝐫𝐨𝐨𝐫𝐢 𝐛𝐚! 📝")
        return
    rules_msg = " ".join(context.args)
    await update.message.reply_text(f"✅ 𝐍𝐢𝐲𝐚𝐦 𝐬𝐞𝐭 𝐡𝐨 𝐠𝐚𝐢𝐥:\n{rules_msg}\n\n𝐒𝐚𝐛 𝐦𝐢𝐥 𝐤𝐞 𝐫𝐚𝐡𝐨, 𝐘𝐚𝐫! 🤝 𝐃𝐢𝐬𝐜𝐢𝐩𝐥𝐢𝐧𝐞 𝐢𝐦𝐩𝐨𝐫𝐭𝐚𝐧𝐭 𝐛𝐚! 😌")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📜 𝐇𝐚𝐦𝐫𝐚 𝐧𝐢𝐲𝐚𝐦 𝐤𝐚𝐧𝐮𝐧:\n{rules_msg}\n\n𝐅𝐨𝐥𝐥𝐨𝐰 𝐤𝐚𝐫𝐨 𝐚𝐮𝐫 𝐜𝐡𝐚𝐦𝐤𝐨, 𝐣𝐞𝐞! ✨ 𝐍𝐨 𝐠𝐚𝐝𝐛𝐚𝐝𝐢! 🙅‍♀️")

async def cleanrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global rules_msg
    rules_msg = ""
    await update.message.reply_text("✅ 𝐍𝐢𝐲𝐚𝐦 𝐤𝐚𝐧𝐮𝐧 𝐬𝐚𝐚𝐟 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐍𝐚𝐲𝐚 𝐚𝐝𝐯𝐞𝐧𝐭𝐮𝐫𝐞! 🌟 𝐀𝐛 𝐬𝐚𝐛 𝐤𝐡𝐮𝐥𝐥𝐚 𝐛𝐚! 🚀")

# --- Message Tool Commands ---
async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("𝐊𝐚𝐮𝐧 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐩𝐢𝐧 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐛𝐚? 𝐑𝐞𝐩𝐥𝐲 𝐤𝐚𝐫𝐨! 📌 𝐁𝐡𝐮𝐥𝐢𝐲𝐨 𝐦𝐚𝐭! 💡")
        return
    try:
        await update.message.reply_to_message.pin()
        await update.message.reply_text("📌 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐩𝐢𝐧 𝐡𝐨 𝐠𝐚𝐢𝐥! 𝐁𝐚𝐡𝐮𝐭 𝐳𝐚𝐫𝐨𝐨𝐫𝐢 𝐛𝐚𝐚𝐭! ✨")
    except Exception as e:
        await update.message.reply_text(f"𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐩𝐢𝐧 𝐧𝐚 𝐡𝐨 𝐩𝐚𝐲𝐚𝐥: {e} 😥 𝐊𝐮𝐜𝐡 𝐝𝐢𝐤𝐤𝐚𝐭 𝐛𝐚! 😔")

async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.unpin_chat_message(update.effective_chat.id)
        await update.message.reply_text("📍 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐮𝐧𝐩𝐢𝐧 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐒𝐚𝐛 𝐜𝐥𝐞𝐚𝐫! 💖 𝐅𝐫𝐞𝐞 𝐡𝐨 𝐠𝐚𝐢𝐥! 🥳")
    except Exception as e:
        await update.message.reply_text(f"𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐮𝐧𝐩𝐢𝐧 𝐧𝐚 𝐡𝐨 𝐩𝐚𝐲𝐚𝐥: {e} 😥 𝐊𝐮𝐜𝐡 𝐭𝐞𝐜𝐡𝐧𝐢𝐜𝐚𝐥 𝐢𝐬𝐬𝐮𝐞 𝐛𝐚! 👨‍💻")

async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("𝐊𝐚𝐮𝐧 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭𝐚𝐰𝐞 𝐤𝐞 𝐛𝐚? 𝐑𝐞𝐩𝐥𝐲 𝐤𝐚𝐫𝐨! 𝐏𝐨𝐨𝐟! 🪄")
        return
    try:
        await update.message.reply_to_message.delete()
        await update.message.reply_text("🗑️ 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭 𝐠𝐚𝐢𝐥. 𝐉𝐚𝐢𝐬𝐞 𝐤𝐚𝐛𝐡𝐢 𝐭𝐡𝐚 𝐡𝐢 𝐧𝐚𝐡𝐢! ✨ 𝐆𝐚𝐲𝐚 𝐯𝐨! 💨")
    except Exception as e:
        await update.message.reply_text(f"𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭𝐚𝐧𝐞 𝐦𝐞𝐢𝐧 𝐝𝐢𝐤𝐤𝐚𝐭: {e} 😥 𝐎𝐡 𝐧𝐨! 😨")

async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("𝐊𝐞𝐤𝐚𝐫𝐚 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭𝐚𝐧𝐞 𝐤𝐞 𝐛𝐚? 𝐒𝐚𝐧𝐤𝐡𝐲𝐚 𝐛𝐚𝐭𝐚𝐨 𝐧𝐚! 🧹 𝐊𝐢𝐭𝐧𝐚 𝐬𝐚𝐚𝐟 𝐤𝐚𝐫𝐞𝐧? 🧐")
        return
    try:
        num = int(context.args[0])
        chat_id = update.effective_chat.id
        
        await update.message.reply_text(f"🧹 {num} 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭𝐚𝐧𝐚 𝐬𝐡𝐮𝐫𝐮 𝐡𝐨 𝐫𝐚𝐡𝐚 𝐡𝐚𝐢... ✨")
        for i in range(num + 1): # Include the purge command itself
            try:
                await context.bot.delete_message(chat_id, update.message.message_id - i)
            except Exception:
                pass 
        await update.message.reply_text("✅ 𝐒𝐚𝐛 𝐬𝐚𝐚𝐟 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐂𝐡𝐚𝐦𝐜𝐡𝐚𝐦𝐚𝐭𝐚! 💖 𝐄𝐤 𝐝𝐚𝐦 𝐧𝐚𝐲𝐚! 💫")
    except Exception as e:
        await update.message.reply_text(f"𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐦𝐢𝐭𝐚𝐧𝐞 𝐦𝐞𝐢𝐧 𝐠𝐚𝐝𝐛𝐚𝐝: {e} 😥 𝐘𝐞 𝐭𝐨𝐡 𝐛𝐮𝐫𝐚 𝐡𝐮𝐚! 😔")

async def cleanservice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("𝐒𝐞𝐫𝐯𝐢𝐜𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐬𝐚𝐚𝐟 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐛𝐚 𝐲𝐚 𝐧𝐚𝐡𝐢? [𝐨𝐧|𝐨𝐟𝐟] 𝐃𝐡𝐚𝐧𝐠 𝐬𝐞 𝐛𝐚𝐭𝐚𝐨! 🧹")
        return
    arg = context.args[0].lower()
    if arg == "on":
        await update.message.reply_text("✅ 𝐒𝐞𝐫𝐯𝐢𝐜𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐬𝐚𝐚𝐟 𝐤𝐚𝐫𝐧𝐚 𝐜𝐡𝐚𝐥𝐮 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐊𝐨𝐧𝐨 𝐠𝐚𝐝𝐛𝐚𝐝 𝐧𝐚𝐡𝐢! 🧼 𝐅𝐮𝐥𝐥 𝐜𝐥𝐞𝐚𝐧𝐢𝐧𝐠! 💖")
    elif arg == "off":
        await update.message.reply_text("✅ 𝐒𝐞𝐫𝐯𝐢𝐜𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐬𝐚𝐚𝐟 𝐤𝐚𝐫𝐧𝐚 𝐛𝐚𝐧𝐝 𝐡𝐨 𝐠𝐚𝐢𝐥. 𝐀𝐛 𝐬𝐚𝐛 𝐝𝐞𝐤𝐡𝐨! 🤪 𝐌𝐚𝐬𝐭𝐢 𝐤𝐚𝐫𝐨! 😂")
    else:
        await update.message.reply_text("🤦‍♀️ 𝐆𝐚𝐥𝐚𝐭 𝐛𝐚𝐚𝐭 𝐛𝐨𝐥𝐚𝐭 𝐡𝐨, 𝐏𝐲𝐚𝐚𝐫𝐞. '𝐨𝐧' 𝐲𝐚 '𝐨𝐟𝐟' 𝐛𝐨𝐥. 🎀 𝐒𝐚𝐦𝐚𝐣𝐡 𝐧𝐚𝐡𝐢 𝐚𝐚𝐭𝐚 𝐤𝐢 𝐤𝐲𝐚? 🙄")

# --- New Member Handler ---
async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not welcome_enabled:
        return
        
    for user in update.message.new_chat_members:
        # ** Send Join Sticker **
        if JOIN_STICKER_ID:
            try:
                await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=JOIN_STICKER_ID)
            except Exception as e:
                logger.error(f"Error sending join sticker: {e}")

        # ** Dynamic Welcome Animation (Bihari Tone) **
        intro_messages = [
            f"💖 𝐀𝐚𝐡 𝐠𝐚𝐢𝐥𝐚 𝐭𝐮, 💎 {user.mention_html()}! 💖",
            "✨ 𝐇𝐚𝐦𝐫𝐚 𝐞 𝐠𝐫𝐨𝐮𝐩𝐰𝐚 𝐦𝐞𝐢𝐧 𝐭𝐨𝐡𝐚𝐫𝐚 𝐬𝐰𝐚𝐠𝐚𝐭 𝐛𝐚, 𝐑𝐚𝐣𝐚! ✨",
            "🌸 𝐌𝐢𝐥𝐤𝐞 𝐝𝐡𝐚𝐦𝐚𝐚𝐥 𝐦𝐚𝐜𝐡𝐚𝐰𝐞 𝐤𝐞 𝐛𝐚! 🥳",
            "💅 𝐓𝐚𝐢𝐲𝐚𝐫 𝐡𝐨 𝐣𝐚, 𝐦𝐚𝐬𝐭𝐢 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐛𝐚! 😎",
            "💋 𝐏𝐲𝐚𝐚𝐫 𝐚𝐮𝐫 𝐦𝐚𝐮𝐣 𝐦𝐚𝐬𝐭𝐢 𝐜𝐡𝐚𝐡𝐢𝐲𝐞, 𝐘𝐚𝐫! 🍫",
            "🎀 𝐁𝐚𝐡𝐮𝐭 𝐤𝐡𝐮𝐬𝐡 𝐡𝐚𝐢𝐧 𝐤𝐢 𝐭𝐮 𝐚𝐚𝐲𝐚𝐥 𝐡𝐨, 𝐉𝐚𝐚𝐧𝐚! 💯",
            "🌟 𝐀𝐛 𝐜𝐡𝐚𝐦𝐚𝐤𝐧𝐞 𝐤𝐞 𝐛𝐚𝐚𝐫𝐢 𝐭𝐨𝐡𝐚𝐫𝐚 𝐛𝐚! 💫",
            "🎉 𝐏𝐚𝐫𝐭𝐲 𝐬𝐡𝐮𝐫𝐮 𝐡𝐨𝐭𝐚𝐚, 𝐝𝐞𝐫 𝐤𝐚𝐡𝐞 𝐤𝐞? 🎶"
        ]

        # Front lining animation
        front_line_msg = await update.message.reply_text("💖 𝐒𝐰𝐚𝐠𝐚𝐭 𝐤𝐚𝐫𝐞 𝐤𝐞 𝐢𝐧𝐭𝐳𝐚𝐚𝐦 𝐜𝐡𝐚𝐥 𝐫𝐚𝐡𝐚 𝐡𝐚𝐢... 🚀")
        for i, msg_text in enumerate(intro_messages):
            await front_line_msg.edit_text(msg_text, parse_mode="HTML")
            await asyncio.sleep(0.3) # Slightly increased sleep for better animation
        await asyncio.sleep(0.7)
        await front_line_msg.delete()
        
        # Original welcome text after animation
        username = f"@{user.username}" if user.username else user.full_name
        join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        welcome_text = (
            f"👑 **𝐀𝐚𝐡 𝐆𝐚𝐢𝐥𝐚 𝐭𝐮, {user.full_name} 𝐌𝐚𝐡𝐚𝐫𝐚𝐣!** 👑\n\n"
            f"• ✨ *𝐍𝐚𝐚𝐦:* `{user.full_name}`\n"
            f"• 🎀 *𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞𝐰𝐚:* `{username}`\n"
            f"• 💖 *𝐔𝐬𝐞𝐫 𝐈𝐃:* `{user.id}`\n"
            f"• 🌸 *𝐊𝐚𝐛 𝐬𝐞 𝐚𝐚𝐲𝐚𝐥 𝐡𝐚:* `{join_date}`\n\n"
            f"✨ 𝐇𝐚𝐦𝐫𝐚 𝐞 𝐠𝐫𝐨𝐮𝐩𝐰𝐚 𝐦𝐞𝐢𝐧 𝐭𝐨𝐡𝐚𝐫𝐚 𝐬𝐰𝐚𝐠𝐚𝐭 𝐛𝐚! 𝐍𝐢𝐲𝐚𝐦𝐰𝐚 𝐩𝐚𝐝𝐡 𝐥𝐢𝐲𝐨 /rules, 𝐚𝐮𝐫 𝐤𝐡𝐨𝐨𝐛 𝐜𝐡𝐚𝐦𝐤𝐨, 𝐘𝐚𝐫! 🌟 𝐌𝐚𝐬𝐭𝐢 𝐤𝐚𝐫𝐨! 😄"
        )
        
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            photo_file = photos.photos[0][0]
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo_file.file_id,
                caption=welcome_text,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(welcome_text, parse_mode="Markdown")

# --- Left Member Handler ---
async def left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.left_chat_member
    username = f"@{user.username}" if user.username else user.full_name
    left_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ** Send Leave Sticker **
    if LEAVE_STICKER_ID:
        try:
            await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=LEAVE_STICKER_ID)
        except Exception as e:
            logger.error(f"Error sending leave sticker: {e}")
    
    left_text = (
        f"💔 *𝐀𝐫𝐫𝐞 𝐫𝐞, 𝐞𝐤 𝐝𝐢𝐥 𝐭𝐨𝐝 𝐤𝐞 𝐜𝐡𝐚𝐥 𝐠𝐚𝐢𝐥...* 😭\n\n"
        f"• 👤 *𝐍𝐚𝐚𝐦:* {user.full_name}\n"
        f"• 🎀 *𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞𝐰𝐚:* {username}\n"
        f"• 💖 *𝐔𝐬𝐞𝐫 𝐈𝐃:* `{user.id}`\n"
        f"• 🌸 *𝐊𝐚𝐛 𝐠𝐚𝐢𝐥𝐚:* {left_date}\n\n"
        f"𝐓𝐨𝐡𝐚𝐫𝐚 𝐤𝐚𝐦𝐢 𝐤𝐡𝐚𝐥𝐞𝐠𝐚, 𝐘𝐚𝐫! ✨ 𝐉𝐚𝐥𝐝𝐢 𝐰𝐚𝐩𝐚𝐬 𝐚𝐚𝐢𝐲𝐨! 🌈 𝐌𝐢𝐬𝐬 𝐲𝐨𝐮! 🥺"
    )
    
    await update.message.reply_text(left_text, parse_mode="Markdown")

# --- Auto Link Filter Handler ---
async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not banlink_enabled or not update.effective_message or not update.message.text:
        return
    msg = update.effective_message
    if any(link in msg.text.lower() for link in ["http://", "https://", "t.me/", "telegram.me/"]):
        user = msg.from_user
        uid = user.id
        username = f"@{user.username}" if user.username else user.full_name
        try:
            await msg.delete()
        except Exception:
                pass
        warns[uid] = warns.get(uid, 0) + 1
        if warns[uid] >= warn_limit:
            try:
                await context.bot.ban_chat_member(msg.chat.id, uid)
                await context.bot.send_message(msg.chat.id, f"🚫 {username} 𝐤𝐞 {warn_limit} 𝐜𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐤𝐞 𝐛𝐚𝐚𝐝 𝐧𝐢𝐤𝐚𝐥 𝐝𝐞𝐞𝐧𝐢. 𝐋𝐢𝐧𝐤 𝐛𝐡𝐞𝐣𝐧𝐚 𝐦𝐚𝐧𝐚 𝐡𝐚𝐢, 𝐌𝐚𝐡𝐚𝐫𝐚𝐣! 🙅‍♀️ 𝐑𝐮𝐥𝐞 𝐭𝐨𝐝𝐚! 💥")
            except Exception:
                pass
        else:
            await context.bot.send_message(msg.chat.id, f"⚠️ {username} 𝐤𝐞 𝐥𝐢𝐧𝐤 𝐛𝐡𝐞𝐣𝐥𝐞 𝐩𝐚𝐫 𝐜𝐡𝐞𝐭𝐚𝐰𝐚𝐧𝐢 𝐦𝐢𝐥𝐚𝐥! [{warns[uid]}/{warn_limit}] 𝐋𝐢𝐧𝐤 𝐦𝐚𝐭 𝐛𝐡𝐞𝐣𝐨, 𝐌𝐢𝐭𝐫𝐚! 🎀 𝐀𝐠𝐥𝐢 𝐛𝐚𝐚𝐫 𝐬𝐞 𝐧𝐚𝐡𝐢! 🚫")

# --- Fallback Help for "help" in Group Chats ---
async def fallback_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower().strip() == "help":
        await help_cmd(update, context)

# --- Main Bot Launcher ---
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # General commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("neo", neo))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("donate", donate))

    # Member join/leave handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, left_member))

    # Moderation commands
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("resetwarns", resetwarns))
    app.add_handler(CommandHandler("setwarnlimit", setwarnlimit))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user)) 
    app.add_handler(CommandHandler("kick", kick_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))

    # Admin commands
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))
    app.add_handler(CommandHandler("admins", list_admins))

    # Lock system commands
    app.add_handler(CommandHandler("lock", lock))
    app.add_handler(CommandHandler("unlock", unlock))

    # Spam filter commands
    app.add_handler(CommandHandler("banlink", banlink))
    app.add_handler(CommandHandler("blocklist", blocklist_cmd))
    app.add_handler(CommandHandler("blocklistmode", blocklistmode_cmd))

    # Welcome system commands
    app.add_handler(CommandHandler("welcome", welcome))
    app.add_handler(CommandHandler("setwelcome", setwelcome))
    app.add_handler(CommandHandler("cleanwelcome", cleanwelcome))

    # Rules system commands
    app.add_handler(CommandHandler("setrules", setrules))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("cleanrules", cleanrules))

    # Message tool commands
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
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(main())
        except RuntimeError:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            new_loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
