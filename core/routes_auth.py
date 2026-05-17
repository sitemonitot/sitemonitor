from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from core.database import get_db
from core.models import User
from core.auth import hash_password, verify_password, create_token, get_current_user
from core.emailer import send_welcome_email

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
