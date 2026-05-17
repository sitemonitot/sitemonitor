import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from core.database import init_db
from core.scheduler import start_scheduler
from core.routes_auth import router as auth_router
from core.routes_monitors import router as monitors_router
from core.routes_stripe import router as stripe_router
from chatbot.bot import router as chat_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

TEMPLATES = Path(__file__).parent / "frontend" / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield


app = FastAPI(title="SiteMonitor", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(auth_router)
app.include_router(monitors_router)
app.include_router(stripe_router)
app.include_router(chat_router)


def html(name: str) -> HTMLResponse:
    return HTMLResponse((TEMPLATES / name).read_text())


@app.get("/", response_class=HTMLResponse)
async def landing():
    return html("index.html")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return html("dashboard.html")


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return html("login.html")


@app.get("/register", response_class=HTMLResponse)
async def register_page():
    return html("register.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug-env")
async def debug_env():
    import os
    return {
        "GROQ_API_KEY": bool(os.getenv("GROQ_API_KEY")),
        "DEVTO_API_KEY": bool(os.getenv("DEVTO_API_KEY")),
        "BLUESKY_HANDLE": os.getenv("BLUESKY_HANDLE", ""),
        "BASE_URL": os.getenv("BASE_URL", ""),
        "SECRET_KEY": bool(os.getenv("SECRET_KEY")),
    }
