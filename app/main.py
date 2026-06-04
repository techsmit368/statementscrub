from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.routers import auth, upload, telegram
from app.services.auth import get_current_user
from app.database import get_db
import app.models


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="StatementScrub", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(telegram.router)

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
