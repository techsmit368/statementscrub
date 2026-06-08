"""
Lender management and matching API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.lender import LenderInfo, LenderRequirement
from app.models.analysis import Analysis
from app.services.lender_importer import LenderImporter
from app.services.lender_matcher import match_lenders, get_all_industries
from app.services.auth import require_user
from app.models.user import User

router = APIRouter(tags=["lenders"])
templates = Jinja2Templates(directory="app/templates")

# Pydantic schemas for responses
from pydantic import BaseModel
from typing import Optional, List as ListType


class LenderRequirementSchema(BaseModel):
    id: int
    lender_id: int
    allow_industry: Optional[str]
    allow_state: Optional[ListType[Optional[str]]]
    time_in_business: int
    min_deposit: int
    min_avg_deposit: int
    max_position: int
    min_position: int
    max_neg_days: int
    min_daily_balance: int
    min_trucks: int
    min_credit_score: int
    nsf_days: int

    class Config:
        from_attributes = True


class LenderInfoSchema(BaseModel):
    id: int
    lender_name: str
    lender_code: Optional[str]
    grade: Optional[str]
    status: int
    email_1: Optional[str]
    phone_1: Optional[str]
    Web_link: Optional[str]
    advance_amount: int
    requirements: ListType[LenderRequirementSchema] = []

    class Config:
        from_attributes = True


US_STATES = [
    ("AL","Alabama"),("AK","Alaska"),("AZ","Arizona"),("AR","Arkansas"),("CA","California"),
    ("CO","Colorado"),("CT","Connecticut"),("DE","Delaware"),("DC","Washington DC"),("FL","Florida"),
    ("GA","Georgia"),("HI","Hawaii"),("ID","Idaho"),("IL","Illinois"),("IN","Indiana"),("IA","Iowa"),
    ("KS","Kansas"),("KY","Kentucky"),("LA","Louisiana"),("ME","Maine"),("MD","Maryland"),
    ("MA","Massachusetts"),("MI","Michigan"),("MN","Minnesota"),("MS","Mississippi"),("MO","Missouri"),
    ("MT","Montana"),("NE","Nebraska"),("NV","Nevada"),("NH","New Hampshire"),("NJ","New Jersey"),
    ("NM","New Mexico"),("NY","New York"),("NC","North Carolina"),("ND","North Dakota"),("OH","Ohio"),
    ("OK","Oklahoma"),("OR","Oregon"),("PA","Pennsylvania"),("PR","Puerto Rico"),("RI","Rhode Island"),
    ("SC","South Carolina"),("SD","South Dakota"),("TN","Tennessee"),("TX","Texas"),("UT","Utah"),
    ("VT","Vermont"),("VA","Virginia"),("WA","Washington"),("WV","West Virginia"),("WI","Wisconsin"),("WY","Wyoming"),
]


# ─── HTML page ─────────────────────────────────────────────────────────────────

@router.get("/lender-match", response_class=HTMLResponse)
async def lender_match_page(
    request: Request,
    analysis_id: Optional[int] = None,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Lender matching page — optionally pre-filled from an analysis."""
    industries = get_all_industries(db)
    prefill = {}

    if analysis_id:
        analysis = db.query(Analysis).filter(
            Analysis.id == analysis_id, Analysis.user_id == user.id
        ).first()
        if analysis:
            rf = (analysis.result_json or {}).get("red_flags", {})
            prefill = {
                "avg_monthly_deposits": int(analysis.avg_monthly_deposits or 0),
                "avg_daily_balance": int(analysis.avg_daily_balance or 0),
                "nsf_count": int(analysis.nsf_count or 0),
                "analysis_id": analysis_id,
                "account_holder": analysis.account_holder,
            }

    return templates.TemplateResponse(
        "lender_match.html",
        {
            "request": request,
            "user": user,
            "industries": industries,
            "states": US_STATES,
            "prefill": prefill,
            "results": None,
            "active_page": "lender_match",
        },
    )


@router.post("/lender-match", response_class=HTMLResponse)
async def lender_match_submit(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Process lender match form and return results."""
    form = await request.form()

    industry = form.get("industry", "").strip()
    state = form.get("state", "").strip()
    avg_monthly_deposits = float(form.get("avg_monthly_deposits", 0) or 0)
    avg_daily_balance = float(form.get("avg_daily_balance", 0) or 0)
    nsf_count = int(form.get("nsf_count", 0) or 0)
    time_in_business = int(form.get("time_in_business", 12) or 12)
    current_positions = int(form.get("current_positions", 0) or 0)
    credit_score = int(form.get("credit_score", 0) or 0)

    results = match_lenders(
        db=db,
        industry=industry,
        state=state,
        avg_monthly_deposits=avg_monthly_deposits,
        avg_daily_balance=avg_daily_balance,
        nsf_count=nsf_count,
        time_in_business=time_in_business,
        current_positions=current_positions,
        credit_score=credit_score,
    )

    industries = get_all_industries(db)
    prefill = {
        "industry": industry,
        "state": state,
        "avg_monthly_deposits": int(avg_monthly_deposits),
        "avg_daily_balance": int(avg_daily_balance),
        "nsf_count": nsf_count,
        "time_in_business": time_in_business,
        "current_positions": current_positions,
        "credit_score": credit_score,
    }

    return templates.TemplateResponse(
        "lender_match.html",
        {
            "request": request,
            "user": user,
            "industries": industries,
            "states": US_STATES,
            "prefill": prefill,
            "results": results,
            "active_page": "lender_match",
        },
    )


# ─── API endpoints ──────────────────────────────────────────────────────────────

@router.get("/api/lenders/industries")
def list_industries(db: Session = Depends(get_db)):
    return {"industries": get_all_industries(db)}


@router.get("/api/lenders/", response_model=List[LenderInfoSchema])
def get_all_lenders(db: Session = Depends(get_db)):
    lenders = db.query(LenderInfo).filter(LenderInfo.status == 1).all()
    return lenders


@router.get("/api/lenders/by-grade/{grade}", response_model=List[LenderInfoSchema])
def get_lenders_by_grade(grade: str, db: Session = Depends(get_db)):
    lenders = db.query(LenderInfo).filter(
        LenderInfo.status == 1,
        LenderInfo.grade == grade.lower()
    ).all()
    return lenders


@router.get("/api/lenders/{lender_id}", response_model=LenderInfoSchema)
def get_lender(lender_id: int, db: Session = Depends(get_db)):
    lender = db.query(LenderInfo).filter(LenderInfo.id == lender_id).first()
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")
    return lender


@router.get("/api/lenders/{lender_id}/requirements", response_model=List[LenderRequirementSchema])
def get_lender_requirements(lender_id: int, db: Session = Depends(get_db)):
    requirements = db.query(LenderRequirement).filter(
        LenderRequirement.lender_id == lender_id
    ).all()
    if not requirements:
        raise HTTPException(status_code=404, detail="No requirements found for this lender")
    return requirements


@router.post("/api/lenders/upload-csv")
def upload_lender_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name
        count, status = LenderImporter.import_lenders_from_csv(tmp_path, db)
        os.unlink(tmp_path)
        if status != "success":
            raise HTTPException(status_code=400, detail=status)
        return {"status": "success", "imported": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/lenders/upload-requirements-csv")
def upload_requirements_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name
        count, status = LenderImporter.import_requirements_from_csv(tmp_path, db)
        os.unlink(tmp_path)
        if status != "success":
            raise HTTPException(status_code=400, detail=status)
        return {"status": "success", "imported": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
