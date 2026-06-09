import json
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

# Team subscription plans (separate from individual plans)
TEAM_SUBSCRIPTIONS = {
    "starter_team": {
        "seats": 3,
        "reports_monthly": 150,
        "price_cents": 39900,
        "label": "Starter Team — 3 seats, 150 reports/month",
        "description": "3 broker seats + 150 shared analyses/month. Partner/Admin/Broker roles.",
    },
    "business_team": {
        "seats": 10,
        "reports_monthly": 500,
        "price_cents": 79900,
        "label": "Business Team — 10 seats, 500 reports/month",
        "description": "10 broker seats + 500 shared analyses/month. Full role management.",
    },
    "enterprise": {
        "seats": 9999,
        "reports_monthly": 2000,
        "price_cents": 199900,
        "label": "Enterprise — Unlimited seats, 2000 reports/month",
        "description": "Unlimited seats + 2000 shared analyses/month. Dedicated support.",
    },
}
templates = Jinja2Templates(directory="app/templates")

stripe.api_key = settings.stripe_secret_key

# One-time credit packs (legacy — not shown in UI, kept for direct API use)
PACKS = {
    "starter":  {"credits": 10,  "price_cents": 1490,  "label": "Starter Pack — 10 Credits"},
    "standard": {"credits": 50,  "price_cents": 5490,  "label": "Standard Pack — 50 Credits"},
    "scale":    {"credits": 500, "price_cents": 49990, "label": "Scale Pack — 500 Credits"},
}

# Monthly subscription plans — 3 tiers
SUBSCRIPTIONS = {
    "broker": {
        "credits_per_month": 25,
        "price_cents": 4900,
        "label": "Broker Plan — 25 reports/month",
        "description": "25 bank statement analyses per month ($2/report), auto-renewed. Cancel any time.",
    },
    "pro": {
        "credits_per_month": 100,
        "price_cents": 14900,
        "label": "Pro Plan — 100 reports/month",
        "description": "100 bank statement analyses per month ($1.50/report), auto-renewed. Cancel any time.",
    },
    "agency": {
        "credits_per_month": 300,
        "price_cents": 29900,
        "label": "Agency Plan — 300 reports/month",
        "description": "300 bank statement analyses per month ($1/report), auto-renewed. Cancel any time.",
    },
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


@router.post("/subscribe")
async def create_subscription(
    request: Request,
    plan: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    if plan not in SUBSCRIPTIONS:
        raise HTTPException(status_code=400, detail="Invalid plan")

    s = SUBSCRIPTIONS[plan]
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "unit_amount": s["price_cents"],
                "recurring": {"interval": "month"},
                "product_data": {
                    "name": s["label"],
                    "description": s["description"],
                },
            },
            "quantity": 1,
        }],
        mode="subscription",
        customer_email=user.email,
        subscription_data={
            "metadata": {
                "user_id": str(user.id),
                "sub_plan": plan,
                "credits_per_month": str(s["credits_per_month"]),
            }
        },
        metadata={"user_id": str(user.id), "sub_plan": plan, "credits_per_month": str(s["credits_per_month"])},
        success_url=f"{settings.app_url}/billing/success?sub={plan}",
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
        event = json.loads(payload)

    etype = event["type"]

    # ── One-time payment completed ─────────────────────────────────────
    if etype == "checkout.session.completed":
        session = event["data"]["object"]
        meta = session.get("metadata", {})
        user_id = int(meta.get("user_id", 0))
        mode = session.get("mode")

        if mode == "payment":
            credits_to_add = int(meta.get("credits", 0))
            if user_id and credits_to_add:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.credits = (user.credits or 0) + credits_to_add
                    user.stripe_customer_id = session.get("customer")
                    db.commit()

        elif mode == "subscription":
            # Store subscription ID + customer ID; credits added on invoice.payment_succeeded
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.stripe_customer_id = session.get("customer")
                    user.stripe_subscription_id = session.get("subscription")
                    user.subscription_plan = meta.get("sub_plan")
                    db.commit()

    # ── Subscription invoice paid (first month + every renewal) ────────
    elif etype == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        subscription_id = invoice.get("subscription")
        if not subscription_id:
            return {"status": "ok"}

        # Fetch subscription to get metadata
        try:
            sub = stripe.Subscription.retrieve(subscription_id)
        except Exception:
            return {"status": "ok"}

        sub_meta = sub.get("metadata", {})
        user_id = int(sub_meta.get("user_id", 0))
        credits_per_month = int(sub_meta.get("credits_per_month", 0))
        sub_plan = sub_meta.get("sub_plan", "")

        if user_id and credits_per_month:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.credits = (user.credits or 0) + credits_per_month
                user.subscription_plan = sub_plan
                db.commit()

    # ── Subscription cancelled ─────────────────────────────────────────
    elif etype == "customer.subscription.deleted":
        sub = event["data"]["object"]
        sub_meta = sub.get("metadata", {})
        user_id = int(sub_meta.get("user_id", 0))
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.stripe_subscription_id = None
                user.subscription_plan = None
                db.commit()

    return {"status": "ok"}


@router.post("/team-subscribe")
async def create_team_subscription(
    request: Request,
    plan: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    if plan not in TEAM_SUBSCRIPTIONS:
        raise HTTPException(status_code=400, detail="Invalid team plan")

    s = TEAM_SUBSCRIPTIONS[plan]
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "unit_amount": s["price_cents"],
                "recurring": {"interval": "month"},
                "product_data": {
                    "name": s["label"],
                    "description": s["description"],
                },
            },
            "quantity": 1,
        }],
        mode="subscription",
        customer_email=user.email,
        subscription_data={
            "metadata": {
                "user_id": str(user.id),
                "sub_plan": plan,
                "credits_per_month": str(s["reports_monthly"]),
            }
        },
        metadata={"user_id": str(user.id), "sub_plan": plan, "credits_per_month": str(s["reports_monthly"])},
        success_url=f"{settings.app_url}/billing/success?sub={plan}",
        cancel_url=f"{settings.app_url}/credits#teams",
    )
    return RedirectResponse(session.url, status_code=303)


@router.get("/plans", response_class=HTMLResponse)
async def billing_plans(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    return templates.TemplateResponse("billing_plans.html", {"request": request, "user": user, "active_page": "credits"})


@router.get("/success", response_class=HTMLResponse)
async def billing_success(
    request: Request,
    pack: str = "",
    sub: str = "",
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    pack_info = PACKS.get(pack)
    sub_info = SUBSCRIPTIONS.get(sub)
    return templates.TemplateResponse(
        "billing_success.html",
        {"request": request, "user": user, "pack": pack_info, "sub": sub_info},
    )
