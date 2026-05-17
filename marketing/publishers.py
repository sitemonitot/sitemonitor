import praw
import httpx
import json
import logging
from core import config

logger = logging.getLogger(__name__)


# ── Reddit ──────────────────────────────────────────────────────────────────

def get_reddit_client():
    if not config.REDDIT_CLIENT_ID:
        return None
    return praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        username=config.REDDIT_USERNAME,
        password=config.REDDIT_PASSWORD,
        user_agent=config.REDDIT_USER_AGENT,
    )


async def publish_reddit(subreddit: str, title: str, body: str) -> str | None:
    reddit = get_reddit_client()
    if not reddit:
        logger.warning("Reddit no configurado - simulando publicación")
        return f"https://reddit.com/r/{subreddit}/SIMULADO"
    try:
        sub = reddit.subreddit(subreddit)
        submission = sub.submit(title, selftext=body)
        url = f"https://reddit.com{submission.permalink}"
        logger.info(f"Post publicado en Reddit: {url}")
        return url
    except Exception as e:
        logger.error(f"Error publicando en Reddit: {e}")
        raise


async def reply_reddit_comment(comment_id: str, reply_text: str) -> bool:
    reddit = get_reddit_client()
    if not reddit:
        logger.warning(f"[SIMULADO] Reply a comentario {comment_id}: {reply_text[:50]}...")
        return True
    try:
        comment = reddit.comment(comment_id)
        comment.reply(reply_text)
        return True
    except Exception as e:
        logger.error(f"Error respondiendo comentario Reddit: {e}")
        return False


# ── Dev.to ──────────────────────────────────────────────────────────────────

async def publish_devto(title: str, body_markdown: str, tags: list[str]) -> str | None:
    if not config.DEVTO_API_KEY:
        logger.warning("Dev.to no configurado - simulando publicación")
        return "https://dev.to/SIMULADO"
    # Dev.to: máx 4 tags, solo letras/números/guiones, sin espacios
    clean_tags = [t.lower().replace(" ", "")[:20] for t in tags[:4]]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://dev.to/api/articles",
            headers={"api-key": config.DEVTO_API_KEY, "Content-Type": "application/json"},
            json={"article": {"title": title, "body_markdown": body_markdown, "tags": clean_tags, "published": True}},
        )
        resp.raise_for_status()
        data = resp.json()
        url = data.get("url", "")
        logger.info(f"Artículo publicado en Dev.to: {url}")
        return url


# ── Bluesky ─────────────────────────────────────────────────────────────────

async def _bluesky_login() -> tuple[str, str] | None:
    if not config.BLUESKY_HANDLE:
        return None
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": config.BLUESKY_HANDLE, "password": config.BLUESKY_PASSWORD},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["accessJwt"], data["did"]


async def publish_bluesky(text: str) -> str | None:
    creds = await _bluesky_login()
    if not creds:
        logger.warning("Bluesky no configurado - simulando publicación")
        return "https://bsky.app/SIMULADO"
    token, did = creds
    from datetime import datetime, timezone
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://bsky.social/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": {
                    "$type": "app.bsky.feed.post",
                    "text": text,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                },
            },
        )
        resp.raise_for_status()
        uri = resp.json().get("uri", "")
        logger.info(f"Post publicado en Bluesky: {uri}")
        return f"https://bsky.app/profile/{config.BLUESKY_HANDLE}"
