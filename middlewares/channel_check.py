from aiogram import Bot
from database.db import get_db

async def check_channels(bot: Bot, user_id: int) -> list:
    db = await get_db()
    channels = await db.execute_fetchall("SELECT channel_id, channel_username, channel_title FROM forced_channels")
    not_joined = []
    for ch in channels:
        try:
            chat_id = int(ch[0])
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ("left", "kicked"):
                not_joined.append({"id": ch[0], "username": ch[1], "title": ch[2] or ch[1]})
        except Exception:
            not_joined.append({"id": ch[0], "username": ch[1], "title": ch[2] or ch[1]})
    return not_joined
