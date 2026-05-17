import httpx
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.models import Monitor, Alert, User
from core import config
from core.emailer import send_change_alert


async def fetch_content(url: str, css_selector: str | None = None) -> str | None:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SiteMonitorBot/1.0)"}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            if css_selector:
                el = soup.select_one(css_selector)
                return el.get_text(strip=True) if el else None
            # Por defecto: texto del body sin scripts/styles
            for tag in soup(["script", "style", "nav", "footer", "head"]):
                tag.decompose()
            return soup.get_text(separator=" ", strip=True)[:5000]
    except Exception:
        return None


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def snippet(content: str, length: int = 300) -> str:
    return content[:length] + "..." if len(content) > length else content


async def check_monitor(monitor: Monitor, db: AsyncSession):
    new_content = await fetch_content(monitor.url, monitor.css_selector)
    if new_content is None:
        return

    now = datetime.utcnow()
    monitor.last_checked_at = now

    if monitor.last_content is None:
        monitor.last_content = new_content
        await db.commit()
        return

    if content_hash(new_content) != content_hash(monitor.last_content):
        old_snippet = snippet(monitor.last_content)
        new_snippet = snippet(new_content)

        alert = Alert(
            monitor_id=monitor.id,
            old_content_snippet=old_snippet,
            new_content_snippet=new_snippet,
            detected_at=now,
        )
        db.add(alert)
        monitor.last_content = new_content
        monitor.last_changed_at = now
        await db.commit()

        result = await db.execute(select(User).where(User.id == monitor.user_id))
        user = result.scalar_one_or_none()
        if user:
            await send_change_alert(user.email, monitor.url, monitor.label, old_snippet, new_snippet)
            alert.email_sent = True
            await db.commit()


async def run_checks(db: AsyncSession, pro_only: bool = False):
    from sqlalchemy.orm import selectinload
    query = select(Monitor).where(Monitor.is_active == True)
    result = await db.execute(query)
    monitors = result.scalars().all()

    for monitor in monitors:
        user_result = await db.execute(select(User).where(User.id == monitor.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            continue
        if pro_only and not user.is_pro:
            continue
        await check_monitor(monitor, db)
