from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import get_db
from admin.panel import is_admin

router = Router()


class AddDarkCollectionStates(StatesGroup):
    waiting_name = State()
    waiting_price = State()
    waiting_description = State()


class DarkDeliverStates(StatesGroup):
    waiting_message = State()


# ===== Admin: Add Dark Collection =====

@router.callback_query(F.data == "adm_dark_collections")
async def dark_admin_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT id, name, price, is_active FROM dark_collections ORDER BY created_at DESC"
    )
    text = "🔞 **Dark Collections Manager**\n\n"
    if rows:
        for r in rows:
            status = "✅" if r[3] else "❌"
            text += f"{status} #{r[0]} — **{r[1]}** — ₹{r[2]}\n"
    else:
        text += "_No collections yet._\n"

    pending = await db.execute_fetchall(
        "SELECT COUNT(*) FROM dark_purchases WHERE status = 'pending'"
    )
    pending_count = pending[0][0] if pending else 0

    buttons = [
        [InlineKeyboardButton(text="➕ Add Dark Collection", callback_data="adm_dark_add")],
        [InlineKeyboardButton(text=f"📬 Pending Orders ({pending_count})", callback_data="adm_dark_orders")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="adm_menu")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "adm_dark_add")
async def dark_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AddDarkCollectionStates.waiting_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="adm_dark_collections")]
    ])
    await callback.message.edit_text(
        "📝 **Add Dark Collection — Step 1**\n\nSend the collection name:",
        reply_markup=kb, parse_mode="Markdown"
    )


@router.message(AddDarkCollectionStates.waiting_name)
async def dark_add_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.update_data(name=message.text.strip())
    await state.set_state(AddDarkCollectionStates.waiting_price)
    await message.answer(
        "💰 **Step 2**\n\nSend the price in ₹ (number only):\nExample: `29`",
        parse_mode="Markdown"
    )


@router.message(AddDarkCollectionStates.waiting_price)
async def dark_add_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        price = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Send a valid number."); return
    await state.update_data(price=price)
    await state.set_state(AddDarkCollectionStates.waiting_description)
    await message.answer(
        "📄 **Step 3**\n\nSend a short description (or send `-` to skip):",
        parse_mode="Markdown"
    )


@router.message(AddDarkCollectionStates.waiting_description)
async def dark_add_desc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    desc = message.text.strip()
    if desc == "-":
        desc = ""
    data = await state.get_data()
    name, price = data["name"], data["price"]

    db = await get_db()
    await db.execute(
        "INSERT INTO dark_collections (name, price, description) VALUES (?, ?, ?)",
        (name, price, desc)
    )
    await db.commit()
    await state.clear()
    await message.answer(
        f"✅ **Dark Collection Created!**\n\n"
        f"Name: **{name}**\n"
        f"Price: ₹{price}\n"
        f"Description: {desc or 'None'}",
        parse_mode="Markdown"
    )


# ===== Admin: View & Deliver Pending Orders =====

@router.callback_query(F.data == "adm_dark_orders")
async def dark_orders_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    db = await get_db()
    rows = await db.execute_fetchall(
        """SELECT dp.id, dp.user_id, dc.name, dc.price, dp.gift_code, dp.created_at
           FROM dark_purchases dp
           JOIN dark_collections dc ON dc.id = dp.collection_id
           WHERE dp.status = 'pending'
           ORDER BY dp.created_at LIMIT 10"""
    )
    if not rows:
        await callback.answer("No pending orders.", show_alert=True); return

    text = "📬 **Pending Dark Orders**\n\n"
    buttons = []
    for r in rows:
        text += (
            f"#{r[0]} | User: `{r[1]}`\n"
            f"Collection: **{r[2]}** (₹{r[3]})\n"
            f"Code: `{r[4]}`\n\n"
        )
        buttons.append([
            InlineKeyboardButton(text=f"✅ Deliver #{r[0]}", callback_data=f"adm_dark_deliver_{r[0]}"),
            InlineKeyboardButton(text=f"❌ Reject #{r[0]}", callback_data=f"adm_dark_reject_{r[0]}")
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="adm_dark_collections")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("adm_dark_deliver_"))
async def dark_deliver_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    order_id = int(callback.data.split("_")[-1])
    await state.update_data(dark_order_id=order_id)
    await state.set_state(DarkDeliverStates.waiting_message)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="adm_dark_orders")]
    ])
    await callback.message.edit_text(
        f"📦 **Deliver Order #{order_id}**\n\n"
        f"Send the message/link to deliver to the user.\n"
        f"This will be sent directly to the buyer.",
        reply_markup=kb, parse_mode="Markdown"
    )


@router.message(DarkDeliverStates.waiting_message)
async def dark_deliver_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    order_id = data.get("dark_order_id")
    admin_msg = message.text.strip()

    db = await get_db()
    row = await db.execute_fetchall(
        """SELECT dp.user_id, dc.name FROM dark_purchases dp
           JOIN dark_collections dc ON dc.id = dp.collection_id
           WHERE dp.id = ? AND dp.status = 'pending'""",
        (order_id,)
    )
    if not row:
        await message.answer("❌ Order not found or already processed.")
        await state.clear()
        return

    uid, col_name = row[0][0], row[0][1]

    await db.execute(
        """UPDATE dark_purchases SET status = 'delivered', admin_message = ?,
           reviewed_by = ?, reviewed_at = datetime('now') WHERE id = ?""",
        (admin_msg, message.from_user.id, order_id)
    )
    await db.commit()
    await state.clear()

    # Send to user
    try:
        await message.bot.send_message(
            uid,
            f"🔓 **Your Dark Content is Ready!**\n\n"
            f"Collection: **{col_name}**\n\n"
            f"{admin_msg}",
            parse_mode="Markdown"
        )
        await message.answer(f"✅ Delivered to user `{uid}` successfully!", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"⚠️ Marked as delivered but failed to send to user: {e}")


@router.callback_query(F.data.startswith("adm_dark_reject_"))
async def dark_reject(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    order_id = int(callback.data.split("_")[-1])
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT user_id FROM dark_purchases WHERE id = ? AND status = 'pending'", (order_id,)
    )
    if not row:
        await callback.answer("Not found.", show_alert=True); return
    uid = row[0][0]
    await db.execute(
        "UPDATE dark_purchases SET status = 'rejected', reviewed_by = ?, reviewed_at = datetime('now') WHERE id = ?",
        (callback.from_user.id, order_id)
    )
    await db.commit()
    await callback.answer("❌ Rejected.")
    try:
        await callback.bot.send_message(uid, "❌ Your dark content request was rejected. Contact support if needed.")
    except: pass
    await dark_orders_list(callback)
