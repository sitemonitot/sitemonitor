from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from core.database import get_db
from core.models import User
from core.auth import hash_password, verify_password, create_token
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
