import hashlib
from database.db import get_db
from config import REFERRAL_CREDITS
from services.credit_service import add_credits

def generate_referral_code(user_id: int) -> str:
    return hashlib.md5(f"ref_{user_id}".encode()).hexdigest()[:8]

async def process_referral(new_user_id: int, referrer_code: str) -> bool:
    db = await get_db()
    # Find referrer
    row = await db.execute_fetchall(
        "SELECT user_id FROM users WHERE referral_code = ?", (referrer_code,)
    )
    if not row:
        return False
    referrer_id = row[0][0]
    if referrer_id == new_user_id:
        return False
    # Check if already referred
    check = await db.execute_fetchall(
        "SELECT referred_by FROM users WHERE user_id = ?", (new_user_id,)
    )
    if check and check[0][0]:
        return False
    # Anti-abuse: limit referrals per day from same referrer
    today_count = await db.execute_fetchall(
        """SELECT COUNT(*) FROM users WHERE referred_by = ?
           AND date(created_at) = date('now')""",
        (referrer_id,)
    )
    if today_count and today_count[0][0] >= 10:
        return False
    # Update new user
    await db.execute(
        "UPDATE users SET referred_by = ? WHERE user_id = ?",
        (referrer_id, new_user_id)
    )
    await add_credits(referrer_id, REFERRAL_CREDITS, "referral", f"Referred user {new_user_id}")
    await db.commit()
    return True

async def get_referral_stats(user_id: int):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)
    )
    return rows[0][0] if rows else 0

async def get_leaderboard(limit: int = 10):
    db = await get_db()
    rows = await db.execute_fetchall(
        """SELECT u.user_id, u.username, u.full_name, COUNT(r.user_id) as refs
           FROM users u LEFT JOIN users r ON r.referred_by = u.user_id
           GROUP BY u.user_id HAVING refs > 0
           ORDER BY refs DESC LIMIT ?""",
        (limit,)
    )
    return rows
