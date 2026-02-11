import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import get_db
from admin.panel import is_admin

router = Router()

class BroadcastStates(StatesGroup):
    waiting_message = State()
    confirm = State()

@router.callback_query(F.data == "adm_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(BroadcastStates.waiting_message)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="adm_menu")]
    ])
    await callback.message.edit_text(
        "📢 **Broadcast**\n\nSend the message you want to broadcast:",
        reply_markup=kb, parse_mode="Markdown"
    )

@router.message(BroadcastStates.waiting_message)
async def preview_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(broadcast_text=message.text)
    await state.set_state(BroadcastStates.confirm)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Send", callback_data="adm_broadcast_confirm"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="adm_menu")
        ]
    ])
    await message.answer(
        f"📢 **Preview:**\n\n{message.text}\n\n—\nConfirm broadcast?",
        reply_markup=kb, parse_mode="Markdown"
    )

@router.callback_query(F.data == "adm_broadcast_confirm")
async def do_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    await state.clear()

    db = await get_db()
    users = await db.execute_fetchall("SELECT user_id FROM users WHERE is_banned = 0")

    success, failed = 0, 0
    await callback.message.edit_text("📢 Broadcasting... please wait.")

    for row in users:
        try:
            await callback.bot.send_message(row[0], text)
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="adm_menu")]
    ])
    await callback.message.edit_text(
        f"📢 **Broadcast Complete**\n\n✅ Sent: {success}\n❌ Failed: {failed}",
        reply_markup=kb, parse_mode="Markdown"
    )
