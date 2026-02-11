from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import get_db

router = Router()

class PurchaseStates(StatesGroup):
    waiting_gift_code = State()

CREDIT_PACKAGES = [
    {"credits": 50, "label": "50 Credits — ₹49"},
    {"credits": 150, "label": "150 Credits — ₹99"},
    {"credits": 500, "label": "500 Credits — ₹249"},
]

@router.callback_query(F.data == "buy_credits")
async def buy_credits(callback: CallbackQuery):
    buttons = []
    for i, pkg in enumerate(CREDIT_PACKAGES):
        buttons.append([InlineKeyboardButton(
            text=f"💎 {pkg['label']}", callback_data=f"buy_pkg_{i}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        "💳 **Buy Credits**\n\n"
        "Choose a package below.\n"
        "Payment via Amazon Pay Gift Card.\n\n"
        "After purchase, send us the gift card code.",
        reply_markup=kb, parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("buy_pkg_"))
async def select_package(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[2])
    pkg = CREDIT_PACKAGES[idx]
    await state.update_data(package=pkg)
    await state.set_state(PurchaseStates.waiting_gift_code)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        f"📦 **{pkg['label']}**\n\n"
        f"Send your Amazon Pay gift card code below.\n"
        f"Admin will verify and add credits within 24hrs.",
        reply_markup=kb, parse_mode="Markdown"
    )

@router.message(PurchaseStates.waiting_gift_code)
async def receive_gift_code(message: Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()
    pkg = data.get("package", {})
    db = await get_db()
    user_id = message.from_user.id

    # Check duplicate code
    existing = await db.execute_fetchall(
        "SELECT id FROM gift_card_submissions WHERE code = ?", (code,)
    )
    if existing:
        await message.answer("❌ This gift card code has already been submitted.")
        await state.clear()
        return

    await db.execute(
        """INSERT INTO gift_card_submissions (user_id, code, credits_requested)
           VALUES (?, ?, ?)""",
        (user_id, code, pkg.get("credits", 0))
    )
    await db.commit()
    await state.clear()

    await message.answer(
        "✅ **Code Submitted!**\n\n"
        "Your gift card code is under review.\n"
        "Credits will be added after admin approval.",
        parse_mode="Markdown"
    )
