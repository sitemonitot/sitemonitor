from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from core.database import AsyncSessionLocal
from core.checker import run_checks
from marketing.scheduler import run_pending_posts
from marketing.monitor import check_reddit_mentions
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def job_check_all():
    async with AsyncSessionLocal() as db:
        logger.info("Ejecutando checks (todos los usuarios)...")
        await run_checks(db, pro_only=False)


async def job_check_pro():
    async with AsyncSessionLocal() as db:
        logger.info("Ejecutando checks rápidos (usuarios Pro)...")
        await run_checks(db, pro_only=True)


async def job_marketing_posts():
    from core import config
    if not config.GROQ_API_KEY:
        return
    async with AsyncSessionLocal() as db:
        logger.info("Publicando posts de marketing pendientes...")
        await run_pending_posts(db)


async def job_reddit_mentions():
    from core import config
    if not config.REDDIT_CLIENT_ID or not config.GROQ_API_KEY:
        return
    async with AsyncSessionLocal() as db:
        logger.info("Revisando menciones en Reddit...")
        await check_reddit_mentions(db)


def start_scheduler():
    # Checks gratuitos: cada 24h
    scheduler.add_job(job_check_all, IntervalTrigger(hours=24), id="check_all", replace_existing=True)
    # Checks Pro: cada hora
    scheduler.add_job(job_check_pro, IntervalTrigger(hours=1), id="check_pro", replace_existing=True)
    # Marketing: revisar posts pendientes cada 30 min
    scheduler.add_job(job_marketing_posts, IntervalTrigger(minutes=30), id="marketing", replace_existing=True)
    # Menciones Reddit: cada 2 horas
    scheduler.add_job(job_reddit_mentions, IntervalTrigger(hours=2), id="reddit_mentions", replace_existing=True)

    scheduler.start()
    logger.info("Scheduler iniciado.")
