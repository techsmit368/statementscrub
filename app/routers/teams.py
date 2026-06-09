"""
Team / multi-seat system for Agency-plan companies.
Roles: partner (owner) > admin > broker
"""
import secrets
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.services.auth import require_user

router = APIRouter(prefix="/team", tags=["teams"])
templates = Jinja2Templates(directory="app/templates")

PLAN_SEATS = {
    "starter_team": 3,
    "business_team": 10,
    "enterprise": 9999,
}

ROLE_ORDER = {"partner": 0, "admin": 1, "broker": 2}


def _get_org(user: User, db: Session):
    """Return user's organization and their membership row, or (None, None)."""
    if not user.org_id:
        return None, None
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    member = db.query(OrganizationMember).filter(
        OrganizationMember.org_id == user.org_id,
        OrganizationMember.user_id == user.id,
    ).first()
    return org, member


def _require_role(member: OrganizationMember, min_role: str):
    if not member or ROLE_ORDER.get(member.role, 99) > ROLE_ORDER.get(min_role, 99):
        raise HTTPException(403, "Insufficient role")


# ── Dashboard ────────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def team_dashboard(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    org, member = _get_org(user, db)
    msg = request.query_params.get("msg", "")

    if not org:
        # Show create-team form
        return templates.TemplateResponse("team_dashboard.html", {
            "request": request, "user": user, "org": None,
            "member": None, "members": [], "msg": msg, "active_page": "team",
        })

    # Load all members with user data
    members_raw = db.query(OrganizationMember).filter(
        OrganizationMember.org_id == org.id
    ).order_by(OrganizationMember.created_at).all()

    member_users = {}
    for m in members_raw:
        if m.user_id:
            u = db.query(User).filter(User.id == m.user_id).first()
            if u:
                member_users[m.id] = u

    seats_used = sum(1 for m in members_raw if m.accepted)
    seats_limit = PLAN_SEATS.get(org.plan, 3)

    return templates.TemplateResponse("team_dashboard.html", {
        "request": request, "user": user, "org": org, "member": member,
        "members": members_raw, "member_users": member_users,
        "seats_used": seats_used, "seats_limit": seats_limit,
        "msg": msg, "active_page": "team",
        "can_manage": member and ROLE_ORDER.get(member.role, 99) <= ROLE_ORDER["admin"],
        "is_partner": member and member.role == "partner",
    })


# ── Create organization ──────────────────────────────────────────────────────────

@router.post("/create")
async def create_team(
    request: Request,
    org_name: str = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if user.org_id:
        return RedirectResponse("/team?msg=already+in+a+team", status_code=302)

    plan = user.subscription_plan or "starter_team"
    seats = PLAN_SEATS.get(plan, 3)

    org = Organization(
        name=org_name.strip(),
        owner_id=user.id,
        plan=plan,
        seats_limit=seats,
        reports_monthly=0,
        reports_pool=user.credits or 0,
    )
    db.add(org)
    db.flush()

    # Add owner as partner
    member = OrganizationMember(
        org_id=org.id,
        user_id=user.id,
        role="partner",
        invited_email=user.email,
        accepted=True,
    )
    db.add(member)

    # Link user to org
    user.org_id = org.id
    user.org_role = "partner"
    db.commit()

    return RedirectResponse("/team?msg=Team+created!", status_code=302)


# ── Invite member ────────────────────────────────────────────────────────────────

@router.post("/invite")
async def invite_member(
    request: Request,
    invited_email: str = Form(...),
    role: str = Form("broker"),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    org, member = _get_org(user, db)
    if not org:
        raise HTTPException(400, "No team found")
    _require_role(member, "admin")

    seats_used = db.query(OrganizationMember).filter(
        OrganizationMember.org_id == org.id, OrganizationMember.accepted == True
    ).count()
    seats_limit = PLAN_SEATS.get(org.plan, 3)
    if seats_used >= seats_limit:
        return RedirectResponse(f"/team?msg=Seat+limit+reached+({seats_limit}+seats)", status_code=302)

    token = secrets.token_urlsafe(32)
    invite = OrganizationMember(
        org_id=org.id,
        user_id=None,
        role=role if role in ("partner", "admin", "broker") else "broker",
        invited_email=invited_email.strip().lower(),
        invite_token=token,
        accepted=False,
    )
    db.add(invite)
    db.commit()

    invite_link = f"{request.base_url}team/accept/{token}"
    return RedirectResponse(f"/team?msg=Invite+sent.+Link:+{invite_link}", status_code=302)


# ── Accept invite ────────────────────────────────────────────────────────────────

@router.get("/accept/{token}", response_class=HTMLResponse)
async def accept_invite(
    token: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    invite = db.query(OrganizationMember).filter(
        OrganizationMember.invite_token == token,
        OrganizationMember.accepted == False,
    ).first()

    if not invite:
        return HTMLResponse("<h2>Invalid or expired invite link.</h2>", status_code=400)

    if user.org_id and user.org_id != invite.org_id:
        return HTMLResponse("<h2>You are already part of another team.</h2>", status_code=400)

    invite.user_id = user.id
    invite.accepted = True
    invite.invite_token = None
    user.org_id = invite.org_id
    user.org_role = invite.role
    db.commit()

    return RedirectResponse("/team?msg=Welcome+to+the+team!", status_code=302)


# ── Change member role ───────────────────────────────────────────────────────────

@router.post("/members/{member_id}/role")
async def change_role(
    member_id: int,
    role: str = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    org, my_member = _get_org(user, db)
    _require_role(my_member, "partner")

    target = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.org_id == org.id,
    ).first()
    if not target or target.role == "partner":
        raise HTTPException(400, "Cannot change partner role")

    if role not in ("admin", "broker"):
        raise HTTPException(400, "Invalid role")

    target.role = role
    if target.user_id:
        u = db.query(User).filter(User.id == target.user_id).first()
        if u:
            u.org_role = role
    db.commit()
    return RedirectResponse("/team?msg=Role+updated", status_code=302)


# ── Remove member ────────────────────────────────────────────────────────────────

@router.post("/members/{member_id}/remove")
async def remove_member(
    member_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    org, my_member = _get_org(user, db)
    _require_role(my_member, "admin")

    target = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.org_id == org.id,
    ).first()
    if not target or target.role == "partner":
        raise HTTPException(400, "Cannot remove partner")

    if target.user_id:
        u = db.query(User).filter(User.id == target.user_id).first()
        if u:
            u.org_id = None
            u.org_role = None
    db.delete(target)
    db.commit()
    return RedirectResponse("/team?msg=Member+removed", status_code=302)
