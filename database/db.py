import os
import shutil
import aiosqlite
from config import DB_PATH

_db = None

async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None or not _db._running:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA synchronous=NORMAL")
    return _db

async def backup_db():
    if os.path.exists(DB_PATH):
        backup_path = DB_PATH + ".backup"
        try:
            shutil.copy2(DB_PATH, backup_path)
        except Exception:
            pass

async def init_db():
    db = await get_db()
    await backup_db()
    await db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        age_verified INTEGER DEFAULT 0,
        last_daily_claim_at TEXT,
        daily_streak INTEGER DEFAULT 0,
        referred_by INTEGER,
        referral_code TEXT UNIQUE,
        created_at TEXT DEFAULT (datetime('now')),
        is_banned INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS credit_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        source TEXT NOT NULL,
        description TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        expires_at TEXT,
        is_expired INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    CREATE TABLE IF NOT EXISTS forced_channels (
        channel_id TEXT PRIMARY KEY,
        channel_username TEXT NOT NULL,
        channel_title TEXT,
        join_type TEXT DEFAULT 'join',
        added_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS join_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        channel_id TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, channel_id)
    );
    CREATE TABLE IF NOT EXISTS promo_codes (
        code TEXT PRIMARY KEY,
        credits INTEGER NOT NULL,
        max_uses INTEGER DEFAULT 1,
        used_count INTEGER DEFAULT 0,
        expires_at TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        is_active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS promo_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        used_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, code)
    );
    CREATE TABLE IF NOT EXISTS collections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tag TEXT NOT NULL,
        file_ids TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        is_active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS collection_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        collection_id INTEGER NOT NULL,
        delivered_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS gift_card_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        code TEXT NOT NULL UNIQUE,
        credits_requested INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        reviewed_by INTEGER,
        created_at TEXT DEFAULT (datetime('now')),
        reviewed_at TEXT
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS moderators (
        user_id INTEGER PRIMARY KEY,
        added_by INTEGER,
        added_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS dark_collections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        description TEXT DEFAULT '',
        file_ids TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS dark_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        collection_id INTEGER NOT NULL,
        gift_code TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        admin_message TEXT,
        reviewed_by INTEGER,
        created_at TEXT DEFAULT (datetime('now')),
        reviewed_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (collection_id) REFERENCES dark_collections(id)
    );
    CREATE INDEX IF NOT EXISTS idx_credit_tx_user ON credit_transactions(user_id);
    CREATE INDEX IF NOT EXISTS idx_credit_tx_expiry ON credit_transactions(expires_at, is_expired);
    CREATE INDEX IF NOT EXISTS idx_join_requests_user ON join_requests(user_id, channel_id);
    """)
    try:
        await db.execute("ALTER TABLE forced_channels ADD COLUMN join_type TEXT DEFAULT 'join'")
        await db.commit()
    except:
        pass
    await db.commit()

async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None
