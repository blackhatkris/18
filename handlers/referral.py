from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_db
from services.referral_service import get_referral_stats, get_leaderboard
from config import REFERRAL_CREDITS

router = Router()

@router.callback_query(F.data == "referral")
async def referral_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT referral_code FROM users WHERE user_id = ?", (user_id,)
    )
    code = row[0][0] if row else "N/A"
    count = await get_referral_stats(user_id)
    bot_info = await callback.bot.get_me()

    link = f"https://t.me/{bot_info.username}?start=ref_{code}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Leaderboard", callback_data="ref_leaderboard")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        f"👥 **Referral Program**\n\n"
        f"Your link:\n`{link}`\n\n"
        f"Referrals: **{count}**\n"
        f"Reward: **{REFERRAL_CREDITS}** credits per referral",
        reply_markup=kb, parse_mode="Markdown"
    )

@router.callback_query(F.data == "ref_leaderboard")
async def leaderboard(callback: CallbackQuery):
    rows = await get_leaderboard()
    text = "🏆 **Referral Leaderboard**\n\n"
    if not rows:
        text += "No referrals yet."
    else:
        for i, r in enumerate(rows, 1):
            name = r[2] or r[1] or f"User {r[0]}"
            text += f"{i}. {name} — {r[3]} referrals\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="referral")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
