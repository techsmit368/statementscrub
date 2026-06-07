from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.database import engine, Base
from app.routers import auth, upload, telegram, blog, pages
from app.routers import api_access
from app.services.auth import get_current_user
from app.database import get_db
import app.models


def _run_migrations():
    """Add new columns/tables to existing DB without Alembic."""
    with engine.connect() as conn:
        for sql in [
            "ALTER TABLE users ADD COLUMN api_key VARCHAR",
        ]:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # Column already exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    yield


app = FastAPI(title="StatementScrub", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(telegram.router)
app.include_router(blog.router)
app.include_router(pages.router)
app.include_router(api_access.router)

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        user = get_current_user(request, db)
    finally:
        db.close()
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.get("/sitemap.xml")
async def sitemap():
    return FileResponse("static/sitemap.xml", media_type="application/xml")


@app.get("/robots.txt")
async def robots():
    return FileResponse("static/robots.txt", media_type="text/plain")


@app.get("/google63008f57257cc8ac.html")
async def google_verify():
    return FileResponse("static/google63008f57257cc8ac.html", media_type="text/html")
