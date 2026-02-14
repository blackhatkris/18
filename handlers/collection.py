import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.credit_service import spend_credits, get_balance
from services.collection_service import get_random_collection
from middlewares.channel_check import check_channels
from config import COLLECTION_COST, AUTO_DELETE_MINUTES

router = Router()

@router.callback_query(F.data == "get_collection")
async def get_collection_handler(callback: CallbackQuery):
    user_id = callback.from_user.id

    # ===== FORCE JOIN CHECK (closes loophole) =====
    not_joined = await check_channels(callback.bot, user_id)
    if not_joined:
        buttons = []
        for ch in not_joined:
            join_type = ch.get("join_type", "join")
            if join_type == "request":
                buttons.append([InlineKeyboardButton(
                    text=f"📩 Request to Join {ch['title']}", url=f"https://t.me/{ch['username']}"
                )])
            else:
                buttons.append([InlineKeyboardButton(
                    text=f"📢 Join {ch['title']}", url=f"https://t.me/{ch['username']}"
                )])
        buttons.append([InlineKeyboardButton(text="✅ I Joined / Requested", callback_data="check_join")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(
            "🔒 **You left a required channel!**\n\n"
            "Please join all channels below to continue:",
            reply_markup=kb, parse_mode="Markdown"
        )
        return

    # ===== BALANCE CHECK =====
    bal = await get_balance(user_id)

    if bal < COLLECTION_COST:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Daily Reward", callback_data="daily_claim")],
            [InlineKeyboardButton(text="👥 Refer & Earn", callback_data="referral")],
            [InlineKeyboardButton(text="📋 Menu", callback_data="full_menu")]
        ])
        await callback.message.edit_text(
            f"❌ **Not enough credits!**\n\n"
            f"You need **{COLLECTION_COST}** credits.\nYour balance: **{bal}**\n\n"
            f"Earn credits below:",
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

    await callback.message.delete()

    sent_messages = []
    for file_id in collection["file_ids"]:
        try:
            msg = await callback.message.answer_photo(file_id)
            sent_messages.append(msg)
        except Exception:
            try:
                msg = await callback.message.answer_video(file_id)
                sent_messages.append(msg)
            except Exception:
                try:
                    msg = await callback.message.answer_document(file_id)
                    sent_messages.append(msg)
                except Exception:
                    pass

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 More Collection", callback_data="get_collection")]
    ])
    final_msg = await callback.message.answer(
        f"🔥 **LEAK COLLECTION**\n\n⚠️ Auto-deletes in {AUTO_DELETE_MINUTES} minutes.",
        reply_markup=kb, parse_mode="Markdown"
    )
    sent_messages.append(final_msg)

    if sent_messages:
        asyncio.create_task(_auto_delete(sent_messages, AUTO_DELETE_MINUTES * 60))

async def _auto_delete(messages, delay: int):
    await asyncio.sleep(delay)
    for msg in messages:
        try:
            await msg.delete()
        except Exception:
            pass
