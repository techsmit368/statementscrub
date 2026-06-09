"""
Superadmin panel — private control center for managing lenders, users, and platform data.
Access: /superadmin  (separate cookie-based session, no relation to user auth)
"""
import json
import secrets
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.analysis import Analysis
from app.models.lender import LenderInfo, LenderRequirement
from app.models.organization import Organization

router = APIRouter(prefix="/superadmin", tags=["superadmin"])
templates = Jinja2Templates(directory="app/templates")

SA_COOKIE = "sa_session"
SA_TOKEN_VALUE = "sa_authenticated"   # simple token stored in signed cookie


# ── Auth helpers ────────────────────────────────────────────────────────────────

def _is_superadmin(request: Request) -> bool:
    return request.cookies.get(SA_COOKIE) == SA_TOKEN_VALUE


def _require_sa(request: Request):
    if not _is_superadmin(request):
        raise HTTPException(status_code=302, headers={"Location": "/superadmin/login"})


# ── Login ───────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def sa_login_page(request: Request):
    if _is_superadmin(request):
        return RedirectResponse("/superadmin/dashboard", status_code=302)
    return templates.TemplateResponse("superadmin_login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def sa_login_submit(request: Request, password: str = Form(...)):
    if password == settings.superadmin_password:
        response = RedirectResponse("/superadmin/dashboard", status_code=302)
        response.set_cookie(SA_COOKIE, SA_TOKEN_VALUE, httponly=True, max_age=86400 * 7)
        return response
    return templates.TemplateResponse("superadmin_login.html", {"request": request, "error": "Wrong password"})


@router.get("/logout")
async def sa_logout():
    response = RedirectResponse("/superadmin/login", status_code=302)
    response.delete_cookie(SA_COOKIE)
    return response


# ── Dashboard ───────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def sa_dashboard(request: Request, db: Session = Depends(get_db)):
    _require_sa(request)

    total_users = db.query(func.count(User.id)).scalar() or 0
    total_analyses = db.query(func.count(Analysis.id)).scalar() or 0
    total_lenders = db.query(func.count(LenderInfo.id)).scalar() or 0
    total_orgs = db.query(func.count(Organization.id)).scalar() or 0

    # MRR estimate from subscription plans
    plan_prices = {"broker": 49, "pro": 149, "agency": 299,
                   "starter_team": 399, "business_team": 799, "enterprise": 1999}
    subscribers = db.query(User.subscription_plan).filter(User.subscription_plan.isnot(None)).all()
    mrr = sum(plan_prices.get(s[0], 0) for s in subscribers)

    # Recent users
    recent_users = db.query(User).order_by(desc(User.created_at)).limit(10).all()

    # Grade breakdown
    grade_counts = {}
    for grade in ["a", "b", "c", "d"]:
        grade_counts[grade.upper()] = db.query(func.count(LenderInfo.id)).filter(
            LenderInfo.grade == grade, LenderInfo.status == 1
        ).scalar() or 0

    return templates.TemplateResponse("superadmin_dashboard.html", {
        "request": request,
        "total_users": total_users,
        "total_analyses": total_analyses,
        "total_lenders": total_lenders,
        "total_orgs": total_orgs,
        "mrr": mrr,
        "recent_users": recent_users,
        "grade_counts": grade_counts,
        "active_page": "dashboard",
    })


# ── Users ───────────────────────────────────────────────────────────────────────

@router.get("/users", response_class=HTMLResponse)
async def sa_users(request: Request, q: str = "", db: Session = Depends(get_db)):
    _require_sa(request)
    query = db.query(User)
    if q:
        query = query.filter(User.email.ilike(f"%{q}%"))
    users = query.order_by(desc(User.created_at)).limit(200).all()
    return templates.TemplateResponse("superadmin_users.html", {
        "request": request, "users": users, "q": q, "active_page": "users"
    })


@router.post("/users/{user_id}/add-credits")
async def sa_add_credits(
    request: Request, user_id: int,
    credits: int = Form(...),
    db: Session = Depends(get_db)
):
    _require_sa(request)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404)
    user.credits = (user.credits or 0) + credits
    db.commit()
    return RedirectResponse(f"/superadmin/users?msg=Added+{credits}+credits+to+{user.email}", status_code=302)


@router.post("/users/{user_id}/set-plan")
async def sa_set_plan(
    request: Request, user_id: int,
    plan: str = Form(...),
    db: Session = Depends(get_db)
):
    _require_sa(request)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404)
    user.subscription_plan = plan or None
    db.commit()
    return RedirectResponse("/superadmin/users", status_code=302)


@router.post("/users/{user_id}/toggle-active")
async def sa_toggle_active(request: Request, user_id: int, db: Session = Depends(get_db)):
    _require_sa(request)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404)
    user.is_active = not user.is_active
    db.commit()
    return RedirectResponse("/superadmin/users", status_code=302)


# ── Lenders list ────────────────────────────────────────────────────────────────

@router.get("/lenders", response_class=HTMLResponse)
async def sa_lenders(
    request: Request,
    q: str = "", grade: str = "", page: int = 1,
    db: Session = Depends(get_db)
):
    _require_sa(request)
    per_page = 50
    query = db.query(LenderInfo)
    if q:
        query = query.filter(LenderInfo.lender_name.ilike(f"%{q}%"))
    if grade:
        query = query.filter(LenderInfo.grade == grade.lower())

    total = query.count()
    lenders = query.order_by(LenderInfo.grade, LenderInfo.lender_name)\
                   .offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page

    return templates.TemplateResponse("superadmin_lenders.html", {
        "request": request, "lenders": lenders, "q": q, "grade": grade,
        "page": page, "total_pages": total_pages, "total": total,
        "active_page": "lenders",
    })


# ── Add lender ──────────────────────────────────────────────────────────────────

@router.get("/lenders/add", response_class=HTMLResponse)
async def sa_lender_add_page(request: Request):
    _require_sa(request)
    return templates.TemplateResponse("superadmin_lender_form.html", {
        "request": request, "lender": None, "requirements": [], "active_page": "lenders"
    })


@router.post("/lenders/add")
async def sa_lender_add_submit(request: Request, db: Session = Depends(get_db)):
    _require_sa(request)
    form = await request.form()
    lender = LenderInfo(
        lender_name=form.get("lender_name", "").strip(),
        lender_code=form.get("lender_code", "").strip() or None,
        grade=form.get("grade", "b").lower(),
        status=int(form.get("status", 1)),
        email_1=form.get("email_1", "").strip() or None,
        email_2=form.get("email_2", "").strip() or None,
        phone_1=form.get("phone_1", "").strip() or None,
        phone_2=form.get("phone_2", "").strip() or None,
        Web_link=form.get("Web_link", "").strip() or None,
        advance_amount=int(form.get("advance_amount", 0) or 0),
        isorep=form.get("isorep", "").strip() or None,
        notes=form.get("notes", "").strip() or None,
        featured=int(form.get("featured", 0)),
    )
    db.add(lender)
    db.commit()
    db.refresh(lender)
    return RedirectResponse(f"/superadmin/lenders/{lender.id}/edit?msg=Lender+added", status_code=302)


# ── Edit lender ─────────────────────────────────────────────────────────────────

@router.get("/lenders/{lender_id}/edit", response_class=HTMLResponse)
async def sa_lender_edit_page(request: Request, lender_id: int, db: Session = Depends(get_db)):
    _require_sa(request)
    lender = db.query(LenderInfo).filter(LenderInfo.id == lender_id).first()
    if not lender:
        raise HTTPException(404)
    requirements = db.query(LenderRequirement).filter(
        LenderRequirement.lender_id == lender_id
    ).all()
    msg = request.query_params.get("msg", "")
    return templates.TemplateResponse("superadmin_lender_form.html", {
        "request": request, "lender": lender, "requirements": requirements,
        "msg": msg, "active_page": "lenders"
    })


@router.post("/lenders/{lender_id}/edit")
async def sa_lender_edit_submit(request: Request, lender_id: int, db: Session = Depends(get_db)):
    _require_sa(request)
    lender = db.query(LenderInfo).filter(LenderInfo.id == lender_id).first()
    if not lender:
        raise HTTPException(404)
    form = await request.form()
    lender.lender_name = form.get("lender_name", lender.lender_name).strip()
    lender.lender_code = form.get("lender_code", "").strip() or None
    lender.grade = form.get("grade", "b").lower()
    lender.status = int(form.get("status", 1))
    lender.email_1 = form.get("email_1", "").strip() or None
    lender.email_2 = form.get("email_2", "").strip() or None
    lender.phone_1 = form.get("phone_1", "").strip() or None
    lender.phone_2 = form.get("phone_2", "").strip() or None
    lender.Web_link = form.get("Web_link", "").strip() or None
    lender.advance_amount = int(form.get("advance_amount", 0) or 0)
    lender.isorep = form.get("isorep", "").strip() or None
    lender.notes = form.get("notes", "").strip() or None
    lender.featured = int(form.get("featured", 0))
    db.commit()
    return RedirectResponse(f"/superadmin/lenders/{lender_id}/edit?msg=Saved", status_code=302)


@router.post("/lenders/{lender_id}/delete")
async def sa_lender_delete(request: Request, lender_id: int, db: Session = Depends(get_db)):
    _require_sa(request)
    lender = db.query(LenderInfo).filter(LenderInfo.id == lender_id).first()
    if lender:
        db.delete(lender)
        db.commit()
    return RedirectResponse("/superadmin/lenders", status_code=302)


# ── Requirements CRUD (inline from lender edit page) ────────────────────────────

@router.post("/lenders/{lender_id}/requirements/add")
async def sa_req_add(request: Request, lender_id: int, db: Session = Depends(get_db)):
    _require_sa(request)
    form = await request.form()

    raw_states = form.get("allow_state", "")
    try:
        states = json.loads(raw_states) if raw_states.strip().startswith("[") else \
                 [s.strip() for s in raw_states.split(",") if s.strip()]
    except Exception:
        states = []

    req = LenderRequirement(
        lender_id=lender_id,
        allow_industry=form.get("allow_industry", "").strip() or None,
        allow_state=states,
        time_in_business=int(form.get("time_in_business", 0) or 0),
        min_avg_deposit=int(form.get("min_avg_deposit", 0) or 0),
        min_daily_balance=int(form.get("min_daily_balance", 0) or 0),
        max_neg_days=int(form.get("max_neg_days", 999) or 999),
        nsf_days=int(form.get("nsf_days", 999) or 999),
        max_position=int(form.get("max_position", 99) or 99),
        min_credit_score=int(form.get("min_credit_score", 0) or 0),
    )
    db.add(req)
    db.commit()
    return RedirectResponse(f"/superadmin/lenders/{lender_id}/edit?msg=Requirement+added", status_code=302)


@router.post("/lenders/{lender_id}/requirements/{req_id}/delete")
async def sa_req_delete(request: Request, lender_id: int, req_id: int, db: Session = Depends(get_db)):
    _require_sa(request)
    req = db.query(LenderRequirement).filter(LenderRequirement.id == req_id).first()
    if req:
        db.delete(req)
        db.commit()
    return RedirectResponse(f"/superadmin/lenders/{lender_id}/edit?msg=Requirement+removed", status_code=302)


# ── Export lenders ──────────────────────────────────────────────────────────────

@router.get("/export", response_class=HTMLResponse)
async def sa_export_page(request: Request, db: Session = Depends(get_db)):
    _require_sa(request)
    from app.services.lender_matcher import get_all_industries
    industries = get_all_industries(db)
    from app.routers.lenders import US_STATES
    return templates.TemplateResponse("superadmin_export.html", {
        "request": request, "industries": industries, "states": US_STATES,
        "active_page": "export"
    })


@router.get("/export/csv")
async def sa_export_csv(
    request: Request,
    grade: str = "", industry: str = "", state: str = "",
    db: Session = Depends(get_db)
):
    _require_sa(request)
    import csv, io
    from fastapi.responses import StreamingResponse

    query = db.query(LenderInfo).filter(LenderInfo.status == 1)
    if grade:
        query = query.filter(LenderInfo.grade == grade.lower())

    lenders = query.order_by(LenderInfo.grade, LenderInfo.lender_name).all()

    # Filter by industry/state via requirements
    if industry or state:
        filtered = []
        for l in lenders:
            for req in l.requirements:
                industry_ok = (not industry) or (req.allow_industry and industry.lower() in req.allow_industry.lower())
                state_ok = (not state) or (req.allow_state and state in req.allow_state)
                if industry_ok and state_ok:
                    filtered.append(l)
                    break
        lenders = filtered

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Code", "Grade", "Email", "Phone", "ISO Rep", "Max Advance", "Notes", "Portal"])
    for l in lenders:
        writer.writerow([
            l.lender_name, l.lender_code or "", l.grade or "",
            l.email_1 or "", l.phone_1 or "", l.isorep or "",
            l.advance_amount or "", l.notes or "", l.Web_link or ""
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=lenders_export.csv"}
    )
