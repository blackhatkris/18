from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import ADMIN_IDS

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    await show_admin_menu(message)

async def show_admin_menu(message_or_callback):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast"),
            InlineKeyboardButton(text="🎟 Create Promo", callback_data="adm_create_promo")
        ],
        [
            InlineKeyboardButton(text="➕ Add Credits", callback_data="adm_add_credits"),
            InlineKeyboardButton(text="📊 Stats", callback_data="adm_stats")
        ],
        [
            InlineKeyboardButton(text="👥 Users", callback_data="adm_users"),
            InlineKeyboardButton(text="➕ Add Channel", callback_data="adm_add_channel")
        ],
        [
            InlineKeyboardButton(text="➖ Remove Channel", callback_data="adm_remove_channel"),
            InlineKeyboardButton(text="📦 Add Collection", callback_data="adm_add_collection")
        ],
        [
            InlineKeyboardButton(text="⚙ Settings", callback_data="adm_settings"),
            InlineKeyboardButton(text="💳 Gift Cards", callback_data="adm_gift_cards")
        ],
        [
            InlineKeyboardButton(text="🔞 Dark Content", callback_data="adm_dark_collections")
        ]
    ])
    text = "🛠 **Admin Panel**\n\nChoose an action:"
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message_or_callback.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "adm_menu")
async def back_admin(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await show_admin_menu(callback)
