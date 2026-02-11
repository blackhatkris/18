from database.db import get_db
from config import CREDIT_EXPIRY_DAYS, DAILY_CREDITS
from datetime import datetime, timedelta

async def get_balance(user_id: int) -> int:
    db = await get_db()
    row = await db.execute_fetchall(
        """SELECT COALESCE(SUM(amount), 0) as bal FROM credit_transactions
           WHERE user_id = ? AND is_expired = 0
           AND (expires_at IS NULL OR expires_at > datetime('now'))""",
        (user_id,)
    )
    return row[0][0] if row else 0

async def add_credits(user_id: int, amount: int, source: str, desc: str = "", expire: bool = True):
    db = await get_db()
    expires_at = None
    if expire:
        expires_at = (datetime.utcnow() + timedelta(days=CREDIT_EXPIRY_DAYS)).isoformat()
    await db.execute(
        """INSERT INTO credit_transactions (user_id, amount, source, description, expires_at)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, amount, source, desc, expires_at)
    )
    await db.commit()

async def spend_credits(user_id: int, amount: int, source: str = "spend", desc: str = "") -> bool:
    bal = await get_balance(user_id)
    if bal < amount:
        return False
    db = await get_db()
    # FIFO: deduct from oldest non-expired credits
    rows = await db.execute_fetchall(
        """SELECT id, amount FROM credit_transactions
           WHERE user_id = ? AND is_expired = 0 AND amount > 0
           AND (expires_at IS NULL OR expires_at > datetime('now'))
           ORDER BY created_at ASC""",
        (user_id,)
    )
    remaining = amount
    for row in rows:
        if remaining <= 0:
            break
        tx_id, tx_amt = row[0], row[1]
        deduct = min(remaining, tx_amt)
        new_amt = tx_amt - deduct
        if new_amt == 0:
            await db.execute("UPDATE credit_transactions SET amount = 0, is_expired = 1 WHERE id = ?", (tx_id,))
        else:
            await db.execute("UPDATE credit_transactions SET amount = ? WHERE id = ?", (new_amt, tx_id))
        remaining -= deduct
    # Log spend
    await db.execute(
        "INSERT INTO credit_transactions (user_id, amount, source, description) VALUES (?, ?, ?, ?)",
        (user_id, -amount, source, desc)
    )
    await db.commit()
    return True

async def expire_old_credits():
    db = await get_db()
    await db.execute(
        """UPDATE credit_transactions SET is_expired = 1
           WHERE expires_at < datetime('now') AND is_expired = 0 AND amount > 0"""
    )
    await db.commit()

async def get_expiring_soon(user_id: int, days: int = 5):
    db = await get_db()
    cutoff = (datetime.utcnow() + timedelta(days=days)).isoformat()
    rows = await db.execute_fetchall(
        """SELECT SUM(amount) as total, MIN(expires_at) as earliest
           FROM credit_transactions
           WHERE user_id = ? AND is_expired = 0 AND amount > 0
           AND expires_at IS NOT NULL AND expires_at <= ? AND expires_at > datetime('now')""",
        (user_id, cutoff)
    )
    if rows and rows[0][0]:
        return int(rows[0][0]), rows[0][1]
    return 0, None

async def get_streak_bonus(streak: int) -> int:
    if streak >= 7:
        return 20
    elif streak >= 5:
        return 15
    elif streak >= 3:
        return 12
    return DAILY_CREDITS
