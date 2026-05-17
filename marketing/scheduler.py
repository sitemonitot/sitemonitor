import random
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.models import MarketingPost
from marketing.content_generator import (
    generate_reddit_post,
    generate_devto_post,
    generate_bluesky_post,
    REDDIT_SUBREDDITS,
)
from marketing.publishers import publish_reddit, publish_devto, publish_bluesky

logger = logging.getLogger(__name__)

# Horarios óptimos para publicar (hora UTC)
REDDIT_BEST_HOURS = [13, 14, 15, 16, 17]  # 9am-1pm ET
DEVTO_BEST_HOURS = [9, 10, 11]
BLUESKY_BEST_HOURS = [12, 13, 14, 15, 16, 17, 18]

# Frecuencia máxima por plataforma (días entre posts)
MIN_DAYS_BETWEEN_REDDIT = 3
MIN_DAYS_BETWEEN_DEVTO = 7
MIN_DAYS_BETWEEN_BLUESKY = 1


async def schedule_next_posts(db: AsyncSession):
    now = datetime.utcnow()

    # Reddit
    result = await db.execute(
        select(MarketingPost)
        .where(MarketingPost.platform == "reddit", MarketingPost.status == "published")
        .order_by(MarketingPost.published_at.desc())
        .limit(1)
    )
    last_reddit = result.scalar_one_or_none()
    if not last_reddit or (now - last_reddit.published_at).days >= MIN_DAYS_BETWEEN_REDDIT:
        subreddit, hint = random.choice(REDDIT_SUBREDDITS)
        try:
            post_data = await generate_reddit_post(subreddit, hint)
            scheduled = now.replace(hour=random.choice(REDDIT_BEST_HOURS), minute=random.randint(0, 59), second=0)
            if scheduled < now:
                scheduled += timedelta(days=1)
            mp = MarketingPost(
                platform="reddit",
                title=post_data["title"],
                content=post_data["body"],
                subreddit=subreddit,
                status="pending",
                scheduled_at=scheduled,
            )
            db.add(mp)
            await db.commit()
            logger.info(f"Post de Reddit programado para {scheduled} en r/{subreddit}")
        except Exception as e:
            logger.error(f"Error generando post Reddit: {e}")

    # Dev.to
    result = await db.execute(
        select(MarketingPost)
        .where(MarketingPost.platform == "devto", MarketingPost.status == "published")
        .order_by(MarketingPost.published_at.desc())
        .limit(1)
    )
    last_devto = result.scalar_one_or_none()
    if not last_devto or (now - last_devto.published_at).days >= MIN_DAYS_BETWEEN_DEVTO:
        try:
            post_data = await generate_devto_post()
            scheduled = now.replace(hour=random.choice(DEVTO_BEST_HOURS), minute=random.randint(0, 59), second=0)
            if scheduled < now:
                scheduled += timedelta(days=1)
            mp = MarketingPost(
                platform="devto",
                title=post_data["title"],
                content=post_data["body_markdown"],
                status="pending",
                scheduled_at=scheduled,
            )
            db.add(mp)
            await db.commit()
            logger.info(f"Artículo Dev.to programado para {scheduled}")
        except Exception as e:
            logger.error(f"Error generando post Dev.to: {e}")

    # Bluesky
    result = await db.execute(
        select(MarketingPost)
        .where(MarketingPost.platform == "bluesky", MarketingPost.status == "published")
        .order_by(MarketingPost.published_at.desc())
        .limit(1)
    )
    last_bluesky = result.scalar_one_or_none()
    if not last_bluesky or (now - last_bluesky.published_at).days >= MIN_DAYS_BETWEEN_BLUESKY:
        try:
            text = await generate_bluesky_post()
            scheduled = now.replace(hour=random.choice(BLUESKY_BEST_HOURS), minute=random.randint(0, 59), second=0)
            if scheduled < now:
                scheduled += timedelta(days=1)
            mp = MarketingPost(
                platform="bluesky",
                content=text,
                status="pending",
                scheduled_at=scheduled,
            )
            db.add(mp)
            await db.commit()
            logger.info(f"Post Bluesky programado para {scheduled}")
        except Exception as e:
            logger.error(f"Error generando post Bluesky: {e}")


async def run_pending_posts(db: AsyncSession):
    now = datetime.utcnow()
    result = await db.execute(
        select(MarketingPost).where(
            MarketingPost.status == "pending",
            MarketingPost.scheduled_at <= now,
        )
    )
    posts = result.scalars().all()

    for post in posts:
        try:
            url = None
            if post.platform == "reddit":
                import json
                tags = []
                url = await publish_reddit(post.subreddit, post.title, post.content)
            elif post.platform == "devto":
                url = await publish_devto(post.title, post.content, ["webdev", "productivity", "tools"])
            elif post.platform == "bluesky":
                url = await publish_bluesky(post.content)

            post.status = "published"
            post.published_at = now
            post.post_url = url
        except Exception as e:
            post.status = "failed"
            post.error = str(e)
            logger.error(f"Error publicando post {post.id} en {post.platform}: {e}")

        await db.commit()

    # Programar nuevos posts para el futuro
    await schedule_next_posts(db)
