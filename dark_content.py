from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import get_db

router = Router()

class DarkPurchaseStates(StatesGroup):
    waiting_gift_code = State()


@router.callback_query(F.data == "dark_content")
async def dark_content_menu(callback: CallbackQuery):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT id, name, price, description FROM dark_collections WHERE is_active = 1 ORDER BY created_at DESC"
    )
    if not rows:
        await callback.answer("🚫 No dark collections available right now.", show_alert=True)
        return

    buttons = []
    text = "🔞 **Dark Content**\n\n🔥 Exclusive premium collections:\n\n"
    for r in rows:
        cid, name, price, desc = r[0], r[1], r[2], r[3]
        text += f"• **{name}** — ₹{price}\n"
        if desc:
            text += f"  _{desc}_\n"
        text += "\n"
        buttons.append([InlineKeyboardButton(
            text=f"🔓 {name} — ₹{price}", callback_data=f"dark_buy_{cid}"
        )])

    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("dark_buy_"))
async def dark_buy_select(callback: CallbackQuery, state: FSMContext):
    cid = int(callback.data.split("_")[2])
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT id, name, price FROM dark_collections WHERE id = ? AND is_active = 1", (cid,)
    )
    if not row:
        await callback.answer("❌ Collection not found.", show_alert=True)
        return

    name, price = row[0][1], row[0][2]
    await state.update_data(dark_collection_id=cid, dark_name=name, dark_price=price)
    await state.set_state(DarkPurchaseStates.waiting_gift_code)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="dark_content")]
    ])
    await callback.message.edit_text(
        f"🔓 **{name}** — ₹{price}\n\n"
        f"💳 Send your **Amazon Pay Gift Card** code below.\n\n"
        f"Admin will verify and deliver the collection within 24hrs.",
        reply_markup=kb, parse_mode="Markdown"
    )


@router.message(DarkPurchaseStates.waiting_gift_code)
async def dark_receive_code(message: Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()
    cid = data.get("dark_collection_id")
    name = data.get("dark_name", "Unknown")
    db = await get_db()

    # Check duplicate
    existing = await db.execute_fetchall(
        "SELECT id FROM dark_purchases WHERE gift_code = ?", (code,)
    )
    if existing:
        await message.answer("❌ This gift card code has already been submitted.")
        await state.clear()
        return

    await db.execute(
        "INSERT INTO dark_purchases (user_id, collection_id, gift_code) VALUES (?, ?, ?)",
        (message.from_user.id, cid, code)
    )
    await db.commit()
    await state.clear()

    await message.answer(
        f"✅ **Request Submitted!**\n\n"
        f"Collection: **{name}**\n"
        f"Code: `{code}`\n\n"
        f"⏳ Admin will review and deliver your content soon.",
        parse_mode="Markdown"
    )
