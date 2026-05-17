import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.models import Base

_raw_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sitemonitor.db")

IS_POSTGRES = _raw_url.startswith("postgresql://") or _raw_url.startswith("postgres://")

if IS_POSTGRES:
    DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1).replace("postgres://", "postgresql+asyncpg://", 1)
    DATABASE_URL = DATABASE_URL.replace("sslmode=require", "ssl=require")
    _connect_args = {}
else:
    DATABASE_URL = _raw_url
    _connect_args = {}

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _add_column_if_missing(conn, table: str, col_name: str, col_type: str):
    """Add a column without breaking the transaction if it already exists."""
    if IS_POSTGRES:
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
    else:
        # SQLite doesn't support IF NOT EXISTS on ALTER TABLE
        try:
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))
        except Exception:
            pass


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # monitors
        for col_name, col_type in [
            ("keyword", "VARCHAR"),
            ("css_selector", "VARCHAR"),
            ("label", "VARCHAR"),
        ]:
            await _add_column_if_missing(conn, "monitors", col_name, col_type)

        # alerts
        await _add_column_if_missing(conn, "alerts", "seen", "BOOLEAN DEFAULT FALSE")

        # users (some added after initial deploy)
        for col_name, col_type in [
            ("display_name", "VARCHAR"),
            ("alert_emails", "TEXT"),
            ("reset_token", "VARCHAR"),
            ("reset_token_expires", "TIMESTAMP"),
            ("is_verified", "BOOLEAN DEFAULT TRUE"),
            ("verification_token", "VARCHAR"),
        ]:
            await _add_column_if_missing(conn, "users", col_name, col_type)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
