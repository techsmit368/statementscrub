import secrets
from fastapi import APIRouter, Request, Form, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.auth import get_current_user, verify_password, hash_password
from app.services.notifications import notify_contact_form, notify_demo_request

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/compare", response_class=HTMLResponse)
async def compare(request: Request):
    return templates.TemplateResponse("compare.html", {"request": request, "user": None})


@router.get("/credits", response_class=HTMLResponse)
async def credits(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return templates.TemplateResponse("billing_plans.html", {"request": request, "user": user, "active_page": "credits"})
    return templates.TemplateResponse("credits.html", {"request": request, "user": None})


# ─── Profile ──────────────────────────────────────────────────────────────────

@router.get("/profile", response_class=HTMLResponse)
async def profile_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    saved    = request.query_params.get("saved") == "1"
    pw_saved = request.query_params.get("pw_saved") == "1"
    return templates.TemplateResponse("profile.html", {
        "request": request, "user": user, "active_page": "profile",
        "saved": saved, "pw_saved": pw_saved, "pw_error": None,
    })


@router.post("/profile", response_class=HTMLResponse)
async def profile_post(
    request: Request,
    db: Session = Depends(get_db),
    full_name: str = Form(""),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    user.full_name = full_name.strip()
    db.commit()
    return RedirectResponse("/profile?saved=1", status_code=302)


@router.post("/profile/password", response_class=HTMLResponse)
async def profile_password(
    request: Request,
    db: Session = Depends(get_db),
    current_password: str = Form(""),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    def render_err(msg):
        return templates.TemplateResponse("profile.html", {
            "request": request, "user": user, "active_page": "profile",
            "saved": False, "pw_saved": False, "pw_error": msg,
        })

    if not verify_password(current_password, user.hashed_password):
        return render_err("Current password is incorrect.")
    if len(new_password) < 8:
        return render_err("New password must be at least 8 characters.")
    if new_password != confirm_password:
        return render_err("Passwords do not match.")

    user.hashed_password = hash_password(new_password)
    db.commit()
    return RedirectResponse("/profile?pw_saved=1", status_code=302)


# ─── Support ──────────────────────────────────────────────────────────────────

@router.get("/support", response_class=HTMLResponse)
async def support_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    return templates.TemplateResponse("support.html", {
        "request": request, "user": user, "active_page": "support",
        "submitted": False, "ticket_id": None,
    })


@router.post("/support", response_class=HTMLResponse)
async def support_post(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    category: str = Form(""),
    subject: str = Form(""),
    priority: str = Form("medium"),
    message: str = Form(""),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    ticket_id = secrets.token_hex(4).upper()
    full_message = (
        f"[SUPPORT TICKET #{ticket_id}]\n"
        f"User: {user.email}\n"
        f"Category: {category}\n"
        f"Priority: {priority}\n"
        f"Subject: {subject}\n\n"
        f"{message}"
    )
    background_tasks.add_task(
        notify_contact_form,
        user.full_name or user.email,
        user.email,
        f"StatementScrub Ticket #{ticket_id}",
        category,
        full_message,
    )
    return templates.TemplateResponse("support.html", {
        "request": request, "user": user, "active_page": "support",
        "submitted": True, "ticket_id": ticket_id,
    })


# ─── Static pages ─────────────────────────────────────────────────────────────

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
    background_tasks: BackgroundTasks,
    name: str = Form(""),
    email: str = Form(""),
    company: str = Form(""),
    phone: str = Form(""),
    role: str = Form(""),
    message: str = Form(""),
):
    background_tasks.add_task(notify_contact_form, name, email, company, role, message)
    return templates.TemplateResponse("contact.html", {"request": request, "user": None, "success": True})


@router.get("/demo", response_class=HTMLResponse)
async def demo_get(request: Request):
    return templates.TemplateResponse("demo.html", {"request": request, "user": None, "success": False})


@router.post("/demo", response_class=HTMLResponse)
async def demo_post(
    request: Request,
    background_tasks: BackgroundTasks,
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    company: str = Form(""),
    phone: str = Form(""),
    role: str = Form(""),
    volume: str = Form(""),
    preferred_time: str = Form(""),
):
    background_tasks.add_task(notify_demo_request, first_name, last_name, email, company, role, volume, preferred_time)
    return templates.TemplateResponse("demo.html", {"request": request, "user": None, "success": True})
