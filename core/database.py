import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.models import Base

_raw_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sitemonitor.db")

# Neon/PostgreSQL connection strings use postgresql:// — convert for asyncpg
if _raw_url.startswith("postgresql://") or _raw_url.startswith("postgres://"):
    DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1).replace("postgres://", "postgresql+asyncpg://", 1)
    # asyncpg uses ssl=require instead of sslmode=require
    DATABASE_URL = DATABASE_URL.replace("sslmode=require", "ssl=require")
    _connect_args = {}
else:
    DATABASE_URL = _raw_url
    _connect_args = {}

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for col in ("keyword VARCHAR", "css_selector VARCHAR", "label VARCHAR"):
            try:
                await conn.execute(__import__("sqlalchemy").text(f"ALTER TABLE monitors ADD COLUMN {col}"))
            except Exception:
                pass
        for col in ("seen BOOLEAN DEFAULT FALSE",):
            try:
                await conn.execute(__import__("sqlalchemy").text(f"ALTER TABLE alerts ADD COLUMN {col}"))
            except Exception:
                pass
        # SQLite-only: add columns that may be missing in existing databases
        if DATABASE_URL.startswith("sqlite"):
            for col in ("display_name VARCHAR", "alert_emails TEXT", "reset_token VARCHAR", "reset_token_expires DATETIME"):
                try:
                    await conn.execute(__import__("sqlalchemy").text(f"ALTER TABLE users ADD COLUMN {col}"))
                except Exception:
                    pass
            for col in ("keyword VARCHAR",):
                try:
                    await conn.execute(__import__("sqlalchemy").text(f"ALTER TABLE monitors ADD COLUMN {col}"))
                except Exception:
                    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
