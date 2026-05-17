import httpx
import hashlib
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.models import Monitor, Alert, User
from core.emailer import send_change_alert

logger = logging.getLogger(__name__)


def _parse_html(html: str, css_selector: str | None = None) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if css_selector:
        el = soup.select_one(css_selector)
        return el.get_text(strip=True) if el else ""
    for tag in soup(["script", "style", "nav", "footer", "head"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)[:5000]


async def _fetch_with_httpx(url: str) -> str | None:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text
    except Exception:
        return None


async def _fetch_with_playwright(url: str) -> str | None:
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            content = await page.content()
            await browser.close()
            return content
    except Exception as e:
        logger.warning(f"Playwright falló para {url}: {e}")
        return None


async def fetch_content(url: str, css_selector: str | None = None) -> str | None:
    html = await _fetch_with_httpx(url)
    if html:
        text = _parse_html(html, css_selector)
        # Si hay poco texto, probablemente la página usa JS → intentar con Playwright
        if len(text.split()) < 50:
            logger.info(f"Poco contenido en {url} ({len(text.split())} palabras), intentando Playwright...")
            html_js = await _fetch_with_playwright(url)
            if html_js:
                text_js = _parse_html(html_js, css_selector)
                if len(text_js.split()) > len(text.split()):
                    return text_js
        return text or None
    # httpx falló completamente → intentar con Playwright
    logger.info(f"httpx falló para {url}, intentando Playwright...")
    html_js = await _fetch_with_playwright(url)
    if html_js:
        return _parse_html(html_js, css_selector) or None
    return None


def extract_keyword_context(content: str, keyword: str) -> str:
    lower = content.lower()
    kw_lower = keyword.lower()
    occurrences = lower.count(kw_lower)
    if occurrences == 0:
        return f"['{keyword}' NOT FOUND on page]"
    # Extraer contexto alrededor de la primera aparición
    idx = lower.find(kw_lower)
    start = max(0, idx - 150)
    end = min(len(content), idx + len(keyword) + 150)
    context = content[start:end].strip()
    return f"['{keyword}' found {occurrences}x] ...{context}..."


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def snippet(content: str, length: int = 300) -> str:
    return content[:length] + "..." if len(content) > length else content


async def check_monitor(monitor: Monitor, db: AsyncSession):
    new_content = await fetch_content(monitor.url, monitor.css_selector)
    if new_content is None:
        return

    # Si hay palabra clave, reducir el contenido a rastrear
    if monitor.keyword:
        new_content = extract_keyword_context(new_content, monitor.keyword)

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
            extra = [e.strip() for e in (user.alert_emails or "").split(",") if e.strip()]
            await send_change_alert(user.email, monitor.url, monitor.label, old_snippet, new_snippet, extra_emails=extra)
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
        try:
            await check_monitor(monitor, db)
        except Exception as e:
            logger.error(f"Error checking monitor {monitor.id}: {e}")
