from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

router = Router()

HELP_TEXT = """
❓ **Help & Information**

🎁 **Daily Credits**
• Claim 10 free credits every 24 hours
• Build streaks for bonus credits (up to 20/day)
• Credits expire after 30 days if unused

👥 **Referrals**
• Share your referral link with friends
• Earn 20 credits per valid referral
• Max 10 referrals per day (anti-abuse)
• Check leaderboard for top referrers

🎲 **Collections**
• Each collection costs 2 credits (configurable)
• Content is randomized — no repeats
• Auto-deletes after 15 minutes

💳 **Buying Credits**
• Purchase via Amazon Pay gift card
• Submit code → Admin verifies → Credits added
• Usually processed within 24 hours

🎟 **Promo Codes**
• Enter promo codes for bonus credits
• Each code can be used once per user
• Codes may have expiry dates

📜 **Rules**
• Must be 18+ to use this bot
• Join all required channels
• No spam or abuse
• Credits are non-transferable

💬 **Commands**
/start — Main menu
/help — This help message
"""

@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]
    ])
    await callback.message.edit_text(HELP_TEXT, reply_markup=kb, parse_mode="Markdown")

@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(HELP_TEXT, parse_mode="Markdown")
