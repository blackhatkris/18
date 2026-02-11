import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.credit_service import spend_credits, get_balance
from services.collection_service import get_random_collection
from config import COLLECTION_COST, AUTO_DELETE_MINUTES

router = Router()

@router.callback_query(F.data == "get_collection")
async def get_collection_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    bal = await get_balance(user_id)

    if bal < COLLECTION_COST:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Claim Daily Credits", callback_data="daily_claim")],
            [
                InlineKeyboardButton(text="👥 Referral", callback_data="referral"),
                InlineKeyboardButton(text="🎟 Promo Code", callback_data="enter_promo")
            ],
            [
                InlineKeyboardButton(text="💳 Buy Credits", callback_data="buy_credits"),
                InlineKeyboardButton(text="💰 Wallet", callback_data="wallet")
            ],
            [InlineKeyboardButton(text="❓ Help", callback_data="help")]
        ])
        await callback.message.edit_text(
            f"❌ **Not enough credits!**\n\n"
            f"You need **{COLLECTION_COST}** credits.\nYour balance: **{bal}**\n\n"
            f"Earn or buy credits below:",
            reply_markup=kb, parse_mode="Markdown"
        )
        return

    collection = await get_random_collection(user_id)
    if not collection:
        await callback.answer("📭 No collections available right now.", show_alert=True)
        return

    success = await spend_credits(user_id, COLLECTION_COST, "spend", f"Collection #{collection['id']}")
    if not success:
        await callback.answer("❌ Failed to spend credits.", show_alert=True)
        return

    new_bal = await get_balance(user_id)
    await callback.message.edit_text(
        f"🎲 **Collection Delivered!**\n\n"
        f"Tag: #{collection['tag']}\n"
        f"Items: {len(collection['file_ids'])}\n"
        f"Remaining balance: **{new_bal}** credits\n\n"
        f"⚠️ Content will auto-delete in {AUTO_DELETE_MINUTES} minutes.",
        parse_mode="Markdown"
    )

    sent_messages = []
    for file_id in collection["file_ids"]:
        try:
            msg = await callback.message.answer_photo(file_id)
            sent_messages.append(msg)
        except Exception:
            try:
                msg = await callback.message.answer_document(file_id)
                sent_messages.append(msg)
            except Exception:
                pass

    if sent_messages:
        asyncio.create_task(_auto_delete(sent_messages, AUTO_DELETE_MINUTES * 60))

async def _auto_delete(messages, delay: int):
    await asyncio.sleep(delay)
    for msg in messages:
        try:
            await msg.delete()
        except Exception:
            pass
