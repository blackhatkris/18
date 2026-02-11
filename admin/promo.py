from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import get_db
from admin.panel import is_admin

router = Router()

class PromoCreateStates(StatesGroup):
    waiting_details = State()

@router.callback_query(F.data == "adm_create_promo")
async def create_promo_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(PromoCreateStates.waiting_details)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="adm_menu")]
    ])
    await callback.message.edit_text(
        "🎟 **Create Promo Code**\n\n"
        "Send in format:\n`CODE CREDITS MAX_USES`\n\n"
        "Example: `WELCOME50 50 100`",
        reply_markup=kb, parse_mode="Markdown"
    )

@router.message(PromoCreateStates.waiting_details)
async def create_promo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.answer("❌ Format: CODE CREDITS MAX_USES")
        return

    code = parts[0].upper()
    try:
        credits = int(parts[1])
        max_uses = int(parts[2])
    except ValueError:
        await message.answer("❌ Credits and max_uses must be numbers.")
        return

    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO promo_codes (code, credits, max_uses) VALUES (?, ?, ?)",
            (code, credits, max_uses)
        )
        await db.commit()
        await state.clear()
        await message.answer(
            f"✅ **Promo Created!**\n\nCode: `{code}`\nCredits: {credits}\nMax Uses: {max_uses}",
            parse_mode="Markdown"
        )
    except Exception:
        await message.answer("❌ Code already exists or error occurred.")
        await state.clear()
