import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from core.database import get_db
from core.models import Monitor, Alert, User
from core.auth import get_current_user
from core import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitors", tags=["monitors"])


class MonitorCreate(BaseModel):
    url: str
    label: Optional[str] = None
    keyword: Optional[str] = None
    css_selector: Optional[str] = None


@router.get("/notifications")
async def get_notifications(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Alert, Monitor)
        .join(Monitor, Alert.monitor_id == Monitor.id)
        .where(Monitor.user_id == user.id, Alert.seen == False)
        .order_by(Alert.detected_at.desc())
        .limit(20)
    )
    rows = result.all()
    return [
        {
            "id": a.id,
            "monitor_id": a.monitor_id,
            "monitor_label": m.label or m.url,
            "detected_at": a.detected_at,
            "new_snippet": a.new_content_snippet,
        }
        for a, m in rows
    ]


@router.post("/notifications/read")
async def mark_notifications_read(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Alert).join(Monitor, Alert.monitor_id == Monitor.id)
        .where(Monitor.user_id == user.id, Alert.seen == False)
    )
    alerts = result.scalars().all()
    for a in alerts:
        a.seen = True
    await db.commit()
    return {"ok": True}


@router.get("/")
async def list_monitors(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Monitor).where(Monitor.user_id == user.id))
        monitors = result.scalars().all()

        monitor_ids = [m.id for m in monitors]
        unseen_map = {}
        if monitor_ids:
            unseen_result = await db.execute(
                select(Alert.monitor_id, func.count(Alert.id))
                .where(Alert.monitor_id.in_(monitor_ids), Alert.seen == False)
                .group_by(Alert.monitor_id)
            )
            unseen_map = {row[0]: row[1] for row in unseen_result.all()}
    except Exception as e:
        logger.error(f"list_monitors error: {traceback.format_exc()}")
        raise HTTPException(500, f"Error loading monitors: {str(e)}")

    return [
        {
            "id": m.id,
            "url": m.url,
            "label": m.label,
            "keyword": m.keyword,
            "css_selector": m.css_selector,
            "is_active": m.is_active,
            "last_checked_at": m.last_checked_at,
            "last_changed_at": m.last_changed_at,
            "created_at": m.created_at,
            "unseen_alerts": unseen_map.get(m.id, 0),
        }
        for m in monitors
    ]


@router.post("/")
async def create_monitor(data: MonitorCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        if not user.is_pro:
            count_result = await db.execute(
                select(func.count()).where(Monitor.user_id == user.id, Monitor.is_active == True)
            )
            count = count_result.scalar()
            if count >= config.FREE_URL_LIMIT:
                raise HTTPException(402, f"Free plan limit: {config.FREE_URL_LIMIT} URLs. Upgrade to Pro for more.")

        monitor = Monitor(user_id=user.id, url=str(data.url), label=data.label, keyword=data.keyword)
        db.add(monitor)
        await db.commit()
        await db.refresh(monitor)
        return {"id": monitor.id, "url": monitor.url, "label": monitor.label}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"create_monitor error: {traceback.format_exc()}")
        raise HTTPException(500, f"Error creating monitor: {str(e)}")


class MonitorUpdate(BaseModel):
    url: Optional[str] = None
    label: Optional[str] = None
    keyword: Optional[str] = None


@router.put("/{monitor_id}")
async def update_monitor(monitor_id: int, data: MonitorUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Monitor).where(Monitor.id == monitor_id, Monitor.user_id == user.id))
    monitor = result.scalar_one_or_none()
    if not monitor:
        raise HTTPException(404, "Monitor no encontrado")
    if data.url is not None:
        monitor.url = str(data.url)
    if data.label is not None:
        monitor.label = data.label or None
    if data.keyword is not None:
        monitor.keyword = data.keyword or None
    await db.commit()
    return {"id": monitor.id, "url": monitor.url, "label": monitor.label, "keyword": monitor.keyword}


@router.delete("/{monitor_id}")
async def delete_monitor(monitor_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Monitor).where(Monitor.id == monitor_id, Monitor.user_id == user.id))
    monitor = result.scalar_one_or_none()
    if not monitor:
        raise HTTPException(404, "Monitor no encontrado")
    await db.delete(monitor)
    await db.commit()
    return {"ok": True}


@router.get("/{monitor_id}/alerts")
async def get_alerts(monitor_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Monitor).where(Monitor.id == monitor_id, Monitor.user_id == user.id))
    monitor = result.scalar_one_or_none()
    if not monitor:
        raise HTTPException(404, "Monitor no encontrado")

    alerts_result = await db.execute(
        select(Alert).where(Alert.monitor_id == monitor_id).order_by(Alert.detected_at.desc()).limit(20)
    )
    alerts = alerts_result.scalars().all()
    return [
        {
            "id": a.id,
            "detected_at": a.detected_at,
            "old_snippet": a.old_content_snippet,
            "new_snippet": a.new_content_snippet,
        }
        for a in alerts
    ]
