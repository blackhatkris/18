from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.credit_service import expire_old_credits

scheduler = AsyncIOScheduler()

async def setup_scheduler():
    scheduler.add_job(expire_old_credits, "interval", hours=1, id="expire_credits")
    scheduler.start()

async def shutdown_scheduler():
    scheduler.shutdown(wait=False)
