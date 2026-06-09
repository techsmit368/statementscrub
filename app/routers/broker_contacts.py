"""
Per-broker ISO rep contact layer.
Each broker maintains their own lender contacts overlaid on the master directory.
"""
from urllib.parse import quote
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.broker_contact import BrokerLenderContact
from app.models.lender import LenderInfo
from app.services.auth import require_user
from app.models.user import User

router = APIRouter(prefix="/broker/contacts", tags=["broker-contacts"])
templates = Jinja2Templates(directory="app/templates")


def _get_contact(user_id: int, lender_id: int, db: Session):
    return db.query(BrokerLenderContact).filter(
        BrokerLenderContact.user_id == user_id,
        BrokerLenderContact.lender_id == lender_id,
    ).first()


# ── List all contacts ────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def contacts_page(
    request: Request,
    q: str = "",
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    contacts = (
        db.query(BrokerLenderContact)
        .filter(BrokerLenderContact.user_id == user.id)
        .all()
    )
    lender_ids = {c.lender_id for c in contacts}
    lenders_map = {}
    if lender_ids:
        for l in db.query(LenderInfo).filter(LenderInfo.id.in_(lender_ids)).all():
            lenders_map[l.id] = l

    # Merge: list of (contact, lender)
    rows = [(c, lenders_map.get(c.lender_id)) for c in contacts]
    if q:
        rows = [(c, l) for c, l in rows if l and q.lower() in l.lender_name.lower()]

    # All active lenders for the "add contact" dropdown
    all_lenders = db.query(LenderInfo).filter(LenderInfo.status == 1)\
                    .order_by(LenderInfo.lender_name).all()

    return templates.TemplateResponse("broker_contacts.html", {
        "request": request, "user": user,
        "rows": rows, "all_lenders": all_lenders,
        "q": q, "active_page": "contacts",
    })


# ── Save / update contact ────────────────────────────────────────────────────────

@router.post("/save")
async def save_contact(
    request: Request,
    lender_id: int = Form(...),
    iso_rep_name: str = Form(""),
    iso_rep_email: str = Form(""),
    iso_rep_phone: str = Form(""),
    notes: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    contact = _get_contact(user.id, lender_id, db)
    if contact:
        contact.iso_rep_name = iso_rep_name.strip() or None
        contact.iso_rep_email = iso_rep_email.strip() or None
        contact.iso_rep_phone = iso_rep_phone.strip() or None
        contact.notes = notes.strip() or None
    else:
        contact = BrokerLenderContact(
            user_id=user.id,
            lender_id=lender_id,
            iso_rep_name=iso_rep_name.strip() or None,
            iso_rep_email=iso_rep_email.strip() or None,
            iso_rep_phone=iso_rep_phone.strip() or None,
            notes=notes.strip() or None,
        )
        db.add(contact)
    db.commit()
    return RedirectResponse("/broker/contacts?msg=saved", status_code=302)


# ── Delete contact ───────────────────────────────────────────────────────────────

@router.post("/{contact_id}/delete")
async def delete_contact(
    contact_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    contact = db.query(BrokerLenderContact).filter(
        BrokerLenderContact.id == contact_id,
        BrokerLenderContact.user_id == user.id,
    ).first()
    if contact:
        db.delete(contact)
        db.commit()
    return RedirectResponse("/broker/contacts", status_code=302)


# ── Email mailto redirect ────────────────────────────────────────────────────────

@router.get("/email/{contact_id}")
async def email_contact(
    request: Request,
    contact_id: int,
    merchant: str = "",
    industry: str = "",
    state: str = "",
    deposits: str = "",
    balance: str = "",
    nsf: str = "",
    time_in_biz: str = "",
    positions: str = "",
    credit_score: str = "",
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    contact = db.query(BrokerLenderContact).filter(
        BrokerLenderContact.id == contact_id,
        BrokerLenderContact.user_id == user.id,
    ).first()
    if not contact or not contact.iso_rep_email:
        raise HTTPException(400, "No email address saved for this contact")

    lender = db.query(LenderInfo).filter(LenderInfo.id == contact.lender_id).first()
    lender_name = lender.lender_name if lender else "your program"

    broker_name = user.full_name or user.email

    subject = f"Deal Submission — {merchant} | {industry} | {state}"
    body = f"""Hi {contact.iso_rep_name or 'there'},

I have a deal that matches your guidelines. Details below:

Business: {merchant}
Industry: {industry}
State: {state}
Time in Business: {time_in_biz} months
Avg Monthly Deposits: ${deposits}
Avg Daily Balance: ${balance}
NSF Count: {nsf}
Current MCA Positions: {positions}
Credit Score: {credit_score or 'Not provided'}

This merchant qualifies under your {lender_name} program.

Please let me know if you need additional documents or the full bank statement.

{broker_name}
{user.email}
"""
    mailto = f"mailto:{contact.iso_rep_email}?subject={quote(subject)}&body={quote(body)}"
    return RedirectResponse(mailto, status_code=302)


# ── API: get contact for a specific lender (used by lender match page JS) ────────

@router.get("/api/{lender_id}")
async def get_contact_api(
    lender_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    contact = _get_contact(user.id, lender_id, db)
    if not contact:
        return {"contact": None}
    return {"contact": {
        "id": contact.id,
        "iso_rep_name": contact.iso_rep_name,
        "iso_rep_email": contact.iso_rep_email,
        "iso_rep_phone": contact.iso_rep_phone,
        "notes": contact.notes,
    }}
