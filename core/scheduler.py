from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from core.database import AsyncSessionLocal
from core.checker import run_checks
from marketing.scheduler import run_pending_posts
from marketing.monitor import check_reddit_mentions
import logging
from datetime import datetime, timezone

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


async def job_producthunt_launch():
    from marketing.publishers import publish_bluesky, publish_devto
    text = (
        "We just launched on Product Hunt! GetURLMonitor monitors any URL "
        "and sends you email alerts when content changes — prices, jobs, stock, competitors. "
        "Free plan included. Check it out and support us! "
        "https://www.geturlmonitor.com"
    )
    try:
        await publish_bluesky(text)
        logger.info("Product Hunt launch post publicado en Bluesky")
    except Exception as e:
        logger.error(f"Error publicando launch post: {e}")

    title = "I built a URL monitoring tool that emails you when any website changes – launching on Product Hunt today"
    body = """I've been building **GetURLMonitor** over the past few weeks and today we're live on Product Hunt!

## What it does

It monitors any URL you give it and sends you an email alert the moment the content changes.

## Use cases

- **Price tracking** – get notified when a product drops in price
- **Job alerts** – watch a company's careers page and be first to apply
- **Stock availability** – sold-out items, limited drops
- **Competitor monitoring** – track changes on competitor sites
- **Policy/legal changes** – terms of service, government pages

## How it works

You paste a URL, set a label, and that's it. The tool checks the page on a schedule and diffs the content. If anything changed, you get an email with a before/after comparison.

## Plans

- **Free**: 3 URLs, checks every 24h
- **Pro ($5/mo)**: unlimited URLs, checks every hour

## Links

- [Live site](https://www.geturlmonitor.com)
- [Product Hunt launch](https://www.producthunt.com)

Would love any feedback from the dev community!
"""
    tags = ["webdev", "saas", "productivity", "python"]
    try:
        await publish_devto(title, body, tags)
        logger.info("Product Hunt launch article publicado en Dev.to")
    except Exception as e:
        logger.error(f"Error publicando launch article en Dev.to: {e}")


def start_scheduler():
    # Checks gratuitos: cada 24h
    scheduler.add_job(job_check_all, IntervalTrigger(hours=24), id="check_all", replace_existing=True)
    # Checks Pro: cada hora
    scheduler.add_job(job_check_pro, IntervalTrigger(hours=1), id="check_pro", replace_existing=True)
    # Marketing: revisar posts pendientes cada 30 min
    scheduler.add_job(job_marketing_posts, IntervalTrigger(minutes=30), id="marketing", replace_existing=True)
    # Menciones Reddit: cada 2 horas
    scheduler.add_job(job_reddit_mentions, IntervalTrigger(hours=2), id="reddit_mentions", replace_existing=True)

    # Product Hunt launch: martes 19 mayo 2026 a las 08:00 UTC (00:00 PT + algo de margen)
    launch_time = datetime(2026, 5, 19, 8, 0, 0, tzinfo=timezone.utc)
    if datetime.now(timezone.utc) < launch_time:
        scheduler.add_job(
            job_producthunt_launch,
            DateTrigger(run_date=launch_time),
            id="producthunt_launch",
            replace_existing=True,
        )
        logger.info(f"Product Hunt launch post programado para {launch_time}")

    scheduler.start()
    logger.info("Scheduler iniciado.")
