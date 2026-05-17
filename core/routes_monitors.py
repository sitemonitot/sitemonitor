from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from core.database import get_db
from core.models import Monitor, Alert, User
from core.auth import get_current_user
from core import config

router = APIRouter(prefix="/monitors", tags=["monitors"])


class MonitorCreate(BaseModel):
    url: str
    label: Optional[str] = None
    keyword: Optional[str] = None
    css_selector: Optional[str] = None


@router.get("/")
async def list_monitors(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Monitor).where(Monitor.user_id == user.id))
    monitors = result.scalars().all()
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
        }
        for m in monitors
    ]


@router.post("/")
async def create_monitor(data: MonitorCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user.is_pro:
        count_result = await db.execute(
            select(func.count()).where(Monitor.user_id == user.id, Monitor.is_active == True)
        )
        count = count_result.scalar()
        if count >= config.FREE_URL_LIMIT:
            raise HTTPException(402, f"Límite del plan gratuito: {config.FREE_URL_LIMIT} URLs. Actualiza a Pro para más.")

    monitor = Monitor(user_id=user.id, url=str(data.url), label=data.label, keyword=data.keyword, css_selector=data.css_selector)
    db.add(monitor)
    await db.commit()
    await db.refresh(monitor)
    return {"id": monitor.id, "url": monitor.url, "label": monitor.label}


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
