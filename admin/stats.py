from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_db
from admin.panel import is_admin

router = Router()

@router.callback_query(F.data == "adm_stats")
async def stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    db = await get_db()
    total = await db.execute_fetchall("SELECT COUNT(*) FROM users")
    today = await db.execute_fetchall(
        "SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')"
    )
    active = await db.execute_fetchall(
        "SELECT COUNT(*) FROM users WHERE last_daily_claim_at IS NOT NULL AND date(last_daily_claim_at) >= date('now', '-7 days')"
    )
    total_credits = await db.execute_fetchall(
        "SELECT COALESCE(SUM(amount), 0) FROM credit_transactions WHERE amount > 0 AND is_expired = 0"
    )
    referrals = await db.execute_fetchall(
        "SELECT COUNT(*) FROM users WHERE referred_by IS NOT NULL"
    )
    pending_gc = await db.execute_fetchall(
        "SELECT COUNT(*) FROM gift_card_submissions WHERE status = 'pending'"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="adm_menu")]
    ])
    await callback.message.edit_text(
        f"📊 **Bot Statistics**\n\n"
        f"👥 Total Users: **{total[0][0]}**\n"
        f"📅 New Today: **{today[0][0]}**\n"
        f"🟢 Active (7d): **{active[0][0]}**\n"
        f"💰 Total Credits: **{total_credits[0][0]}**\n"
        f"👥 Referrals: **{referrals[0][0]}**\n"
        f"💳 Pending Gift Cards: **{pending_gc[0][0]}**",
        reply_markup=kb, parse_mode="Markdown"
    )
