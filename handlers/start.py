from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, CommandObject
from database.db import get_db
from services.referral_service import generate_referral_code, process_referral
from middlewares.channel_check import check_channels

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user = message.from_user
    db = await get_db()

    # Check if user exists
    existing = await db.execute_fetchall(
        "SELECT user_id, age_verified FROM users WHERE user_id = ?", (user.id,)
    )

    if not existing:
        ref_code = generate_referral_code(user.id)
        await db.execute(
            """INSERT INTO users (user_id, username, full_name, referral_code)
               VALUES (?, ?, ?, ?)""",
            (user.id, user.username or "", user.full_name or "", ref_code)
        )
        await db.commit()

        # Process referral if deep link
        if command.args and command.args.startswith("ref_"):
            referrer_code = command.args[4:]
            await process_referral(user.id, referrer_code)

    # Check age verification
    row = await db.execute_fetchall(
        "SELECT age_verified FROM users WHERE user_id = ?", (user.id,)
    )

    if not row or not row[0][0]:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ I am 18+ years old", callback_data="age_verify")],
            [InlineKeyboardButton(text="❌ I am under 18", callback_data="age_deny")]
        ])
        await message.answer(
            "⚠️ **Age Verification Required**\n\n"
            "This bot is for users aged 18 and above only.\n"
            "Please confirm your age to continue.",
            reply_markup=kb, parse_mode="Markdown"
        )
        return

    # Check forced channels
    not_joined = await check_channels(message.bot, user.id)
    if not_joined:
        buttons = []
        for ch in not_joined:
            buttons.append([InlineKeyboardButton(
                text=f"📢 Join {ch['title']}", url=f"https://t.me/{ch['username']}"
            )])
        buttons.append([InlineKeyboardButton(text="✅ I Joined", callback_data="check_join")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(
            "🔒 **Join Required Channels**\n\nPlease join all channels below to use this bot.",
            reply_markup=kb, parse_mode="Markdown"
        )
        return

    await send_main_menu(message)

async def send_main_menu(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Claim Daily Credits", callback_data="daily_claim")],
        [
            InlineKeyboardButton(text="💰 Wallet", callback_data="wallet"),
            InlineKeyboardButton(text="🎲 Get Collection", callback_data="get_collection")
        ],
        [
            InlineKeyboardButton(text="👥 Referral", callback_data="referral"),
            InlineKeyboardButton(text="🎟 Promo Code", callback_data="enter_promo")
        ],
        [
            InlineKeyboardButton(text="💳 Buy Credits", callback_data="buy_credits"),
            InlineKeyboardButton(text="❓ Help", callback_data="help")
        ]
    ])
    await message.answer(
        "🏠 **Main Menu**\n\nWelcome! Choose an option below:",
        reply_markup=kb, parse_mode="Markdown"
    )

@router.callback_query(F.data == "age_verify")
async def age_verified(callback: CallbackQuery):
    db = await get_db()
    await db.execute(
        "UPDATE users SET age_verified = 1 WHERE user_id = ?", (callback.from_user.id,)
    )
    await db.commit()
    await callback.answer("✅ Age verified!")
    await callback.message.delete()
    await send_main_menu(callback.message)

@router.callback_query(F.data == "age_deny")
async def age_denied(callback: CallbackQuery):
    await callback.answer("❌ You must be 18+ to use this bot.", show_alert=True)

@router.callback_query(F.data == "check_join")
async def check_join_callback(callback: CallbackQuery):
    not_joined = await check_channels(callback.bot, callback.from_user.id)
    if not_joined:
        await callback.answer("❌ You haven't joined all channels yet.", show_alert=True)
        return
    await callback.answer("✅ Verified!")
    await callback.message.delete()
    await send_main_menu(callback.message)

@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.delete()
    await send_main_menu(callback.message)
