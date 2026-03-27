# ================= IMPORTS =================
import asyncio
import logging
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.core.bot_instance import bot, bot_loop
from bot.core.database import db
from bot.core.func_utils import decode, editMessage, sendMessage, new_task
from bot.core.auto_animes import get_animes
from config import Var
from helper_func import *

logger = logging.getLogger(__name__)

# ================= FORCE SUB =================
async def not_joined(client: Client, message: Message):
    temp = await message.reply("Join channels first", quote=True)
    buttons = []

    all_channels = await db.show_channels()
    for chat_id in all_channels:
        if not await is_sub(client, message.from_user.id, chat_id):
            data = await client.get_chat(chat_id)
            link = f"https://t.me/{data.username}" if data.username else (await client.create_chat_invite_link(chat_id)).invite_link
            buttons.append([InlineKeyboardButton(data.title, url=link)])

    await message.reply_photo(
        photo=Var.FORCE_PIC,
        caption="Join all channels to use bot",
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True
    )
    await temp.delete()

# ================= AUTO FETCH + DB =================
async def auto_fetch_and_store():
    while True:
        try:
            animes = await get_animes()

            if animes:
                for anime in animes:
                    title = anime.get("title")

                    if not title:
                        continue

                    exists = await db.anime_collection.find_one({"title": title})

                    if not exists:
                        await db.anime_collection.insert_one({
                            "title": title,
                            "created_at": datetime.utcnow()
                        })

                logger.info(f"Anime Updated: {len(animes)}")

        except Exception as e:
            logger.error(f"AUTO FETCH ERROR: {e}")

        await asyncio.sleep(1800)  # 30 min

# ================= START =================
@bot.on_message(filters.command('start') & filters.private)
@new_task
async def start_msg(client: Client, message: Message):

    user_id = message.from_user.id

    if not await is_subscribed(client, user_id):
        return await not_joined(client, message)

    txt = message.text.split()
    temp = await sendMessage(message, "Please wait...")

    # normal start
    if len(txt) <= 1:
        await temp.delete()
        return await message.reply_photo(
            photo=Var.START_PIC,
            caption="Welcome bro ✅",
            quote=True
        )

    # ================= DECODE =================
    try:
        data = await decode(txt[1])
        arg = data.split('-')
    except:
        return await editMessage(temp, "Invalid link")

    # ================= FILE FIX =================
    try:
        if len(arg) == 2 and arg[0] == "get":

            msg = None

            # try encoded id
            try:
                fid = int(int(arg[1]) / abs(int(Var.FILE_STORE)))
                msg = await client.get_messages(Var.FILE_STORE, fid)
            except:
                pass

            # fallback
            if not msg or msg.empty:
                try:
                    msg = await client.get_messages(Var.FILE_STORE, int(arg[1]))
                except:
                    pass

            if not msg or msg.empty:
                return await editMessage(temp, "File Not Found")

            await msg.copy(
                chat_id=message.chat.id,
                caption=msg.caption if msg.caption else "",
                quote=True
            )

            await temp.delete()

    except Exception as e:
        logger.error(e)
        await editMessage(temp, "File Not Found")

# ================= SEARCH =================
@bot.on_message(filters.command("search") & filters.private)
async def search_anime(client, message):

    if len(message.text.split()) < 2:
        return await message.reply("Anime name do", quote=True)

    query = message.text.split(" ", 1)[1]

    results = await db.anime_collection.find({
        "title": {"$regex": query, "$options": "i"}
    }).to_list(length=10)

    if not results:
        return await message.reply("Anime nahi mila", quote=True)

    text = "🔍 Results:\n\n"
    for anime in results:
        text += f"• {anime.get('title','Unknown')}\n"

    await message.reply(text, quote=True)

# ================= AUTO SEARCH =================
@bot.on_message(filters.text & filters.private)
async def auto_search(client, message):

    if message.text.startswith("/"):
        return

    query = message.text

    results = await db.anime_collection.find({
        "title": {"$regex": query, "$options": "i"}
    }).to_list(length=5)

    if results:
        text = "🔍 Found:\n\n"
        for anime in results:
            text += f"• {anime.get('title','Unknown')}\n"

        await message.reply(text, quote=True)

# ================= COMMAND BUTTON =================
@bot.on_message(filters.command('commands') & filters.private)
async def bcmd(client: Client, message: Message):
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("• CLOSE •", callback_data="close")]
    ])
    await message.reply(
        text="Bot Commands List",
        reply_markup=reply_markup,
        quote=True
    )

# ================= RUN AUTO TASK =================
bot_loop.create_task(auto_fetch_and_store())
