import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from core.database import get_db
from core.models import User
from core.auth import hash_password, verify_password, create_token, get_current_user
from core.emailer import send_welcome_email, send_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Email ya registrado")
    if len(data.password) < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres")
    user = User(email=data.email, hashed_password=hash_password(data.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await send_welcome_email(user.email)
    return {"token": create_token(user.id), "email": user.email, "is_pro": user.is_pro}


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Credenciales incorrectas")
    return {"token": create_token(user.id), "email": user.email, "is_pro": user.is_pro}


@router.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    alert_emails = [e.strip() for e in (user.alert_emails or "").split(",") if e.strip()]
    return {
        "email": user.email,
        "display_name": user.display_name or "",
        "is_pro": user.is_pro,
        "alert_emails": alert_emails,
        "stripe_subscription_id": user.stripe_subscription_id,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    alert_emails: Optional[list[str]] = None


@router.put("/profile")
async def update_profile(data: ProfileUpdateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user.id))
    db_user = result.scalar_one()
    if data.display_name is not None:
        db_user.display_name = data.display_name.strip() or None
    if data.alert_emails is not None:
        clean = [e.strip() for e in data.alert_emails if e.strip() and "@" in e]
        db_user.alert_emails = ",".join(clean) if clean else None
    await db.commit()
    return {"ok": True}


@router.delete("/account")
async def delete_account(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user.id))
    db_user = result.scalar_one()
    await db.delete(db_user)
    await db.commit()
    return {"ok": True}


@router.get("/export")
async def export_data(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from core.models import Monitor, Alert
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(User).options(selectinload(User.monitors).selectinload(Monitor.alerts)).where(User.id == user.id)
    )
    u = result.scalar_one()
    data = {
        "account": {
            "email": u.email,
            "display_name": u.display_name,
            "is_pro": u.is_pro,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "alert_emails": [e.strip() for e in (u.alert_emails or "").split(",") if e.strip()],
        },
        "monitors": [
            {
                "url": m.url,
                "label": m.label,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "last_checked_at": m.last_checked_at.isoformat() if m.last_checked_at else None,
                "alerts": [
                    {"detected_at": a.detected_at.isoformat() if a.detected_at else None}
                    for a in m.alerts
                ],
            }
            for m in u.monitors
        ],
    }
    return JSONResponse(content=data, headers={"Content-Disposition": "attachment; filename=my_data.json"})


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    # Always return OK to avoid email enumeration
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        await db.commit()
        await send_reset_email(user.email, token)
    return {"ok": True}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.reset_token == data.token))
    user = result.scalar_one_or_none()
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        raise HTTPException(400, "Invalid or expired token")
    if len(data.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    user.hashed_password = hash_password(data.password)
    user.reset_token = None
    user.reset_token_expires = None
    await db.commit()
    return {"ok": True}
