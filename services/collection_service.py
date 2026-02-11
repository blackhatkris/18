import random
from database.db import get_db

async def get_random_collection(user_id: int):
    db = await get_db()
    # Get collections not recently seen by user
    rows = await db.execute_fetchall(
        """SELECT c.id, c.tag, c.file_ids FROM collections c
           WHERE c.is_active = 1
           AND c.id NOT IN (
               SELECT collection_id FROM collection_history
               WHERE user_id = ? ORDER BY delivered_at DESC LIMIT 20
           )
           ORDER BY RANDOM() LIMIT 1""",
        (user_id,)
    )
    if not rows:
        # Fallback: any active collection
        rows = await db.execute_fetchall(
            "SELECT id, tag, file_ids FROM collections WHERE is_active = 1 ORDER BY RANDOM() LIMIT 1"
        )
    if not rows:
        return None
    cid, tag, file_ids_str = rows[0][0], rows[0][1], rows[0][2]
    # Log delivery
    await db.execute(
        "INSERT INTO collection_history (user_id, collection_id) VALUES (?, ?)",
        (user_id, cid)
    )
    await db.commit()
    file_ids = [f.strip() for f in file_ids_str.split(",") if f.strip()]
    return {"id": cid, "tag": tag, "file_ids": file_ids}
