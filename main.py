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
STATIC = Path(__file__).parent / "frontend" / "static"


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

app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/sitemap.xml")
async def sitemap():
    from fastapi.responses import FileResponse
    return FileResponse(STATIC / "sitemap.xml", media_type="application/xml")


@app.get("/robots.txt")
async def robots():
    from fastapi.responses import FileResponse
    return FileResponse(STATIC / "robots.txt", media_type="text/plain")


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


@app.get("/terms", response_class=HTMLResponse)
async def terms_page():
    return html("terms.html")


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page():
    return html("privacy.html")


@app.get("/profile", response_class=HTMLResponse)
async def profile_page():
    return html("profile.html")


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page():
    return html("forgot-password.html")


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page():
    return html("reset-password.html")


@app.get("/health")
async def health():
    return {"status": "ok"}
