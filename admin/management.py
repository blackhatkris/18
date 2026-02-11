from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import get_db
from services.credit_service import add_credits
from admin.panel import is_admin

router = Router()

class AddCreditsStates(StatesGroup):
    waiting = State()

class AddChannelStates(StatesGroup):
    waiting = State()

class RemoveChannelStates(StatesGroup):
    waiting = State()

class AddCollectionStates(StatesGroup):
    waiting_tag = State()
    waiting_media = State()

# --- Add Credits to User ---
@router.callback_query(F.data == "adm_add_credits")
async def add_credits_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AddCreditsStates.waiting)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="adm_menu")]])
    await callback.message.edit_text(
        "➕ **Add Credits**\n\nSend: `USER_ID AMOUNT`\nExample: `123456789 100`",
        reply_markup=kb, parse_mode="Markdown"
    )

@router.message(AddCreditsStates.waiting)
async def add_credits_do(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("❌ Format: USER_ID AMOUNT"); return
    try:
        uid, amt = int(parts[0]), int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid numbers."); return
    await add_credits(uid, amt, "admin", f"Added by admin {message.from_user.id}", expire=False)
    await state.clear()
    await message.answer(f"✅ Added {amt} credits to user {uid} (no expiry).")

# --- Add Channel ---
@router.callback_query(F.data == "adm_add_channel")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AddChannelStates.waiting)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="adm_menu")]])
    await callback.message.edit_text(
        "➕ **Add Force-Join Channel**\n\nSend: `CHANNEL_ID CHANNEL_USERNAME`\nExample: `-1001234567890 mychannel`",
        reply_markup=kb, parse_mode="Markdown"
    )

@router.message(AddChannelStates.waiting)
async def add_channel_do(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("❌ Format: CHANNEL_ID USERNAME"); return
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO forced_channels (channel_id, channel_username) VALUES (?, ?)",
        (parts[0], parts[1].replace("@", ""))
    )
    await db.commit()
    await state.clear()
    await message.answer(f"✅ Channel @{parts[1]} added.")

# --- Remove Channel ---
@router.callback_query(F.data == "adm_remove_channel")
async def remove_channel_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    channels = await db.execute_fetchall("SELECT channel_id, channel_username FROM forced_channels")
    if not channels:
        await callback.answer("No channels configured.", show_alert=True); return
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(
            text=f"❌ @{ch[1]}", callback_data=f"adm_rmch_{ch[0]}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="adm_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("➖ **Remove Channel**\n\nTap to remove:", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("adm_rmch_"))
async def remove_channel_do(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    ch_id = callback.data.replace("adm_rmch_", "")
    db = await get_db()
    await db.execute("DELETE FROM forced_channels WHERE channel_id = ?", (ch_id,))
    await db.commit()
    await callback.answer("✅ Channel removed!")
    await remove_channel_start(callback, None)

# --- Add Collection ---
@router.callback_query(F.data == "adm_add_collection")
async def add_collection_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AddCollectionStates.waiting_tag)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="adm_menu")]])
    await callback.message.edit_text(
        "📦 **Add Collection — Step 1**\n\nSend the tag name for this collection.\n\nExample: `premium`",
        reply_markup=kb, parse_mode="Markdown"
    )

@router.message(AddCollectionStates.waiting_tag)
async def add_collection_tag(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    tag = message.text.strip()
    await state.update_data(tag=tag, file_ids=[])
    await state.set_state(AddCollectionStates.waiting_media)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Done", callback_data="adm_collection_done")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="adm_menu")]
    ])
    await message.answer(
        f"📦 **Add Collection — Step 2**\n\n"
        f"Tag: `{tag}`\n\n"
        f"Now send me photos/videos for this collection.\n"
        f"Send them one by one or as an album.\n\n"
        f"Files collected: **0**\n\n"
        f"When done, tap ✅ **Done**.",
        reply_markup=kb, parse_mode="Markdown"
    )

@router.message(AddCollectionStates.waiting_media, F.photo)
async def add_collection_photo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    file_ids = data.get("file_ids", [])
    file_id = message.photo[-1].file_id
    file_ids.append(file_id)
    await state.update_data(file_ids=file_ids)
    await message.answer(f"📸 Photo added! Total files: **{len(file_ids)}**", parse_mode="Markdown")

@router.message(AddCollectionStates.waiting_media, F.video)
async def add_collection_video(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    file_ids = data.get("file_ids", [])
    file_id = message.video.file_id
    file_ids.append(file_id)
    await state.update_data(file_ids=file_ids)
    await message.answer(f"🎥 Video added! Total files: **{len(file_ids)}**", parse_mode="Markdown")

@router.message(AddCollectionStates.waiting_media, F.document)
async def add_collection_document(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    file_ids = data.get("file_ids", [])
    file_id = message.document.file_id
    file_ids.append(file_id)
    await state.update_data(file_ids=file_ids)
    await message.answer(f"📎 File added! Total files: **{len(file_ids)}**", parse_mode="Markdown")

@router.callback_query(F.data == "adm_collection_done", AddCollectionStates.waiting_media)
async def add_collection_done(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    data = await state.get_data()
    tag = data.get("tag", "unknown")
    file_ids = data.get("file_ids", [])
    if not file_ids:
        await callback.answer("❌ No files added! Send at least one photo/video.", show_alert=True)
        return
    file_ids_str = ",".join(file_ids)
    db = await get_db()
    await db.execute(
        "INSERT INTO collections (tag, file_ids) VALUES (?, ?)", (tag, file_ids_str)
    )
    await db.commit()
    await state.clear()
    await callback.message.edit_text(
        f"✅ **Collection Created!**\n\n"
        f"Tag: `{tag}`\n"
        f"Files: **{len(file_ids)}**",
        parse_mode="Markdown"
    )

# --- Gift Card Review ---
@router.callback_query(F.data == "adm_gift_cards")
async def gift_cards_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT id, user_id, code, credits_requested, created_at FROM gift_card_submissions WHERE status = 'pending' ORDER BY created_at LIMIT 10"
    )
    if not rows:
        await callback.answer("No pending gift cards.", show_alert=True); return
    buttons = []
    text = "💳 **Pending Gift Cards**\n\n"
    for r in rows:
        text += f"#{r[0]} | User: {r[1]} | {r[3]} credits\nCode: `{r[2]}`\n\n"
        buttons.append([
            InlineKeyboardButton(text=f"✅ Approve #{r[0]}", callback_data=f"adm_gc_approve_{r[0]}"),
            InlineKeyboardButton(text=f"❌ Reject #{r[0]}", callback_data=f"adm_gc_reject_{r[0]}")
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="adm_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("adm_gc_approve_"))
async def approve_gc(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    gc_id = int(callback.data.split("_")[-1])
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT user_id, credits_requested FROM gift_card_submissions WHERE id = ? AND status = 'pending'", (gc_id,)
    )
    if not row:
        await callback.answer("Not found or already processed.", show_alert=True); return
    uid, credits = row[0][0], row[0][1]
    await add_credits(uid, credits, "purchase", f"Gift card #{gc_id}", expire=False)
    await db.execute(
        "UPDATE gift_card_submissions SET status = 'approved', reviewed_by = ?, reviewed_at = datetime('now') WHERE id = ?",
        (callback.from_user.id, gc_id)
    )
    await db.commit()
    await callback.answer(f"✅ Approved! {credits} credits added to {uid}.")
    try:
        await callback.bot.send_message(uid, f"✅ Your gift card has been approved! +{credits} credits added.")
    except: pass
    await gift_cards_list(callback)

@router.callback_query(F.data.startswith("adm_gc_reject_"))
async def reject_gc(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    gc_id = int(callback.data.split("_")[-1])
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT user_id FROM gift_card_submissions WHERE id = ? AND status = 'pending'", (gc_id,)
    )
    if not row:
        await callback.answer("Not found.", show_alert=True); return
    uid = row[0][0]
    await db.execute(
        "UPDATE gift_card_submissions SET status = 'rejected', reviewed_by = ?, reviewed_at = datetime('now') WHERE id = ?",
        (callback.from_user.id, gc_id)
    )
    await db.commit()
    await callback.answer("❌ Rejected.")
    try:
        await callback.bot.send_message(uid, "❌ Your gift card submission was rejected. Contact support if needed.")
    except: pass
    await gift_cards_list(callback)

# --- Users list ---
@router.callback_query(F.data == "adm_users")
async def users_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT user_id, username, full_name, created_at FROM users ORDER BY created_at DESC LIMIT 20"
    )
    text = "👥 **Recent Users**\n\n"
    for r in rows:
        name = r[2] or r[1] or str(r[0])
        text += f"• {name} (`{r[0]}`) — {r[3][:10]}\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="adm_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

# --- Settings placeholder ---
@router.callback_query(F.data == "adm_settings")
async def settings_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="adm_menu")]
    ])
    await callback.message.edit_text(
        "⚙ **Settings**\n\n"
        "Configure via environment variables:\n"
        "• `DAILY_CREDITS` — daily reward\n"
        "• `REFERRAL_CREDITS` — referral reward\n"
        "• `COLLECTION_COST` — cost per collection\n"
        "• `CREDIT_EXPIRY_DAYS` — expiry period\n"
        "• `AUTO_DELETE_MINUTES` — auto-delete timer",
        reply_markup=kb, parse_mode="Markdown"
    )
