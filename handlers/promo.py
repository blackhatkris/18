from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import get_db
from services.credit_service import add_credits
from datetime import datetime

router = Router()

class PromoStates(StatesGroup):
    waiting_code = State()

@router.callback_query(F.data == "enter_promo")
async def enter_promo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PromoStates.waiting_code)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        "🎟 **Enter Promo Code**\n\nType your promo code below:",
        reply_markup=kb, parse_mode="Markdown"
    )

@router.message(PromoStates.waiting_code)
async def process_promo(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    db = await get_db()
    user_id = message.from_user.id

    # Check code exists
    row = await db.execute_fetchall(
        "SELECT credits, max_uses, used_count, expires_at, is_active FROM promo_codes WHERE code = ?",
        (code,)
    )
    if not row or not row[0][4]:
        await message.answer("❌ Invalid promo code.")
        await state.clear()
        return

    credits, max_uses, used_count, expires_at, _ = row[0]

    # Check expiry
    if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
        await message.answer("❌ This promo code has expired.")
        await state.clear()
        return

    # Check usage limit
    if used_count >= max_uses:
        await message.answer("❌ This promo code has been fully used.")
        await state.clear()
        return

    # Check if user already used it
    used = await db.execute_fetchall(
        "SELECT id FROM promo_usage WHERE user_id = ? AND code = ?",
        (user_id, code)
    )
    if used:
        await message.answer("❌ You've already used this code.")
        await state.clear()
        return

    # Apply
    await add_credits(user_id, credits, "promo", f"Promo: {code}")
    await db.execute(
        "INSERT INTO promo_usage (user_id, code) VALUES (?, ?)", (user_id, code)
    )
    await db.execute(
        "UPDATE promo_codes SET used_count = used_count + 1 WHERE code = ?", (code,)
    )
    await db.commit()
    await state.clear()
    await message.answer(f"✅ **Promo Applied!**\n\n+{credits} credits added!", parse_mode="Markdown")
