from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.models import Base

DATABASE_URL = "sqlite+aiosqlite:///./sitemonitor.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add new columns if they don't exist (safe migration)
        for col in ("display_name VARCHAR", "alert_emails TEXT"):
            col_name = col.split()[0]
            try:
                await conn.execute(__import__("sqlalchemy").text(
                    f"ALTER TABLE users ADD COLUMN {col}"
                ))
            except Exception:
                pass  # column already exists


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
