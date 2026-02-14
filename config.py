import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DAILY_CREDITS = int(os.getenv("DAILY_CREDITS", "10"))
REFERRAL_CREDITS = int(os.getenv("REFERRAL_CREDITS", "20"))
COLLECTION_COST = int(os.getenv("COLLECTION_COST", "2"))
CREDIT_EXPIRY_DAYS = int(os.getenv("CREDIT_EXPIRY_DAYS", "30"))
AUTO_DELETE_MINUTES = int(os.getenv("AUTO_DELETE_MINUTES", "15"))

# Persistent DB path — use absolute path to survive restarts
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "bot.db"))
