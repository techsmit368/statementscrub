from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request, "user": None})


@router.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request, "user": None})


@router.get("/how-it-works", response_class=HTMLResponse)
async def how_it_works(request: Request):
    return templates.TemplateResponse("how_it_works.html", {"request": request, "user": None})


@router.get("/testimonials", response_class=HTMLResponse)
async def testimonials(request: Request):
    return templates.TemplateResponse("testimonials.html", {"request": request, "user": None})


@router.get("/contact", response_class=HTMLResponse)
async def contact_get(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request, "user": None, "success": False})


@router.post("/contact", response_class=HTMLResponse)
async def contact_post(
    request: Request,
    name: str = Form(""),
    email: str = Form(""),
    company: str = Form(""),
    phone: str = Form(""),
    role: str = Form(""),
    message: str = Form(""),
):
    return templates.TemplateResponse("contact.html", {"request": request, "user": None, "success": True})


@router.get("/demo", response_class=HTMLResponse)
async def demo_get(request: Request):
    return templates.TemplateResponse("demo.html", {"request": request, "user": None, "success": False})


@router.post("/demo", response_class=HTMLResponse)
async def demo_post(
    request: Request,
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    company: str = Form(""),
    phone: str = Form(""),
    role: str = Form(""),
    volume: str = Form(""),
    preferred_time: str = Form(""),
):
    return templates.TemplateResponse("demo.html", {"request": request, "user": None, "success": True})
