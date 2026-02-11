from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_db
from services.credit_service import get_balance, add_credits, get_expiring_soon, get_streak_bonus
from datetime import datetime, timedelta

router = Router()

@router.callback_query(F.data == "daily_claim")
async def daily_claim(callback: CallbackQuery):
    db = await get_db()
    user_id = callback.from_user.id

    row = await db.execute_fetchall(
        "SELECT last_daily_claim_at, daily_streak FROM users WHERE user_id = ?", (user_id,)
    )
    if not row:
        await callback.answer("❌ User not found", show_alert=True)
        return

    last_claim = row[0][0]
    streak = row[0][1] or 0
    now = datetime.utcnow()

    if last_claim:
        last_dt = datetime.fromisoformat(last_claim)
        diff = now - last_dt
        if diff < timedelta(hours=24):
            remaining = timedelta(hours=24) - diff
            hours = int(remaining.total_seconds() // 3600)
            mins = int((remaining.total_seconds() % 3600) // 60)
            await callback.answer(
                f"⏳ Claim again in {hours}h {mins}m", show_alert=True
            )
            return
        # Check streak
        if diff < timedelta(hours=48):
            streak += 1
        else:
            streak = 1
    else:
        streak = 1

    bonus = await get_streak_bonus(streak)
    await add_credits(user_id, bonus, "daily", f"Day {streak} streak")
    await db.execute(
        "UPDATE users SET last_daily_claim_at = ?, daily_streak = ? WHERE user_id = ?",
        (now.isoformat(), streak, user_id)
    )
    await db.commit()

    streak_text = f"🔥 Streak: Day {streak}" if streak > 1 else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        f"🎁 **Daily Credits Claimed!**\n\n"
        f"+ {bonus} credits added\n"
        f"{streak_text}\n\n"
        f"Credits expire in 30 days. Stay active!",
        reply_markup=kb, parse_mode="Markdown"
    )

@router.callback_query(F.data == "wallet")
async def wallet(callback: CallbackQuery):
    user_id = callback.from_user.id
    bal = await get_balance(user_id)
    expiring_amt, expiring_date = await get_expiring_soon(user_id)

    expiry_text = ""
    if expiring_amt:
        expiry_text = f"\n⚠️ {expiring_amt} credits expiring soon!"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Buy More", callback_data="buy_credits")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        f"💰 **Your Wallet**\n\n"
        f"Balance: **{bal}** credits{expiry_text}",
        reply_markup=kb, parse_mode="Markdown"
    )
