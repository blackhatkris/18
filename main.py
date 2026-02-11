import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database.db import init_db, close_db
from scheduler.tasks import setup_scheduler, shutdown_scheduler

# Handlers
from handlers.start import router as start_router
from handlers.credits import router as credits_router
from handlers.referral import router as referral_router
from handlers.collection import router as collection_router
from handlers.promo import router as promo_router
from handlers.purchase import router as purchase_router
from handlers.help import router as help_router

# Admin
from admin.panel import router as admin_panel_router
from admin.stats import router as admin_stats_router
from admin.broadcast import router as admin_broadcast_router
from admin.promo import router as admin_promo_router
from admin.management import router as admin_mgmt_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_routers(
        start_router,
        credits_router,
        referral_router,
        collection_router,
        promo_router,
        purchase_router,
        help_router,
        admin_panel_router,
        admin_stats_router,
        admin_broadcast_router,
        admin_promo_router,
        admin_mgmt_router,
    )

    await init_db()
    await setup_scheduler()
    logger.info("Bot starting...")

    try:
        await dp.start_polling(bot)
    finally:
        await shutdown_scheduler()
        await close_db()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
