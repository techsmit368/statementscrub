import stripe
from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/billing", tags=["billing"])
templates = Jinja2Templates(directory="app/templates")

stripe.api_key = settings.stripe_secret_key

PACKS = {
    "starter":  {"credits": 10,  "price_cents": 1490,  "label": "Starter Pack — 10 Credits"},
    "basic":    {"credits": 25,  "price_cents": 2790,  "label": "Basic Pack — 25 Credits"},
    "standard": {"credits": 50,  "price_cents": 5490,  "label": "Standard Pack — 50 Credits"},
    "business": {"credits": 100, "price_cents": 10490, "label": "Business Pack — 100 Credits"},
    "growth":   {"credits": 250, "price_cents": 26290, "label": "Growth Pack — 250 Credits"},
    "scale":    {"credits": 500, "price_cents": 49990, "label": "Scale Pack — 500 Credits"},
}


@router.post("/checkout")
async def create_checkout(
    request: Request,
    pack: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    if pack not in PACKS:
        raise HTTPException(status_code=400, detail="Invalid pack")

    p = PACKS[pack]
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "unit_amount": p["price_cents"],
                "product_data": {
                    "name": p["label"],
                    "description": f"{p['credits']} bank statement analysis credits — never expire",
                },
            },
            "quantity": 1,
        }],
        mode="payment",
        customer_email=user.email,
        metadata={"user_id": str(user.id), "pack": pack, "credits": str(p["credits"])},
        success_url=f"{settings.app_url}/billing/success?pack={pack}",
        cancel_url=f"{settings.app_url}/credits",
    )
    return RedirectResponse(session.url, status_code=303)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    if settings.stripe_webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        import json
        event = json.loads(payload)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        meta = session.get("metadata", {})
        user_id = int(meta.get("user_id", 0))
        credits_to_add = int(meta.get("credits", 0))

        if user_id and credits_to_add:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.credits = (user.credits or 0) + credits_to_add
                db.commit()

    return {"status": "ok"}


@router.get("/success", response_class=HTMLResponse)
async def billing_success(
    request: Request,
    pack: str = "",
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    pack_info = PACKS.get(pack)
    return templates.TemplateResponse(
        "billing_success.html",
        {"request": request, "user": user, "pack": pack_info},
    )
