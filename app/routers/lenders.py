"""
Lender management and matching API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.lender import LenderInfo, LenderRequirement
from app.services.lender_importer import LenderImporter

router = APIRouter(prefix="/api/lenders", tags=["lenders"])


# Pydantic schemas for responses
from pydantic import BaseModel
from typing import Optional, List as ListType


class LenderRequirementSchema(BaseModel):
    id: int
    lender_id: int
    allow_industry: Optional[str]
    allow_state: Optional[ListType[str]]
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


@router.get("/", response_model=List[LenderInfoSchema])
def get_all_lenders(db: Session = Depends(get_db)):
    """Get all active lenders"""
    lenders = db.query(LenderInfo).filter(LenderInfo.status == 1).all()
    return lenders


@router.get("/by-grade/{grade}", response_model=List[LenderInfoSchema])
def get_lenders_by_grade(grade: str, db: Session = Depends(get_db)):
    """Get lenders by grade (A, B, C, D)"""
    lenders = db.query(LenderInfo).filter(
        LenderInfo.status == 1,
        LenderInfo.grade == grade.lower()
    ).all()
    return lenders


@router.get("/{lender_id}", response_model=LenderInfoSchema)
def get_lender(lender_id: int, db: Session = Depends(get_db)):
    """Get specific lender with requirements"""
    lender = db.query(LenderInfo).filter(LenderInfo.id == lender_id).first()
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")
    return lender


@router.get("/{lender_id}/requirements", response_model=List[LenderRequirementSchema])
def get_lender_requirements(lender_id: int, db: Session = Depends(get_db)):
    """Get requirements for a specific lender"""
    requirements = db.query(LenderRequirement).filter(
        LenderRequirement.lender_id == lender_id
    ).all()
    if not requirements:
        raise HTTPException(status_code=404, detail="No requirements found for this lender")
    return requirements


@router.post("/upload-csv")
def upload_lender_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload lenders CSV file"""
    try:
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            content = file.file.read()
            tmp.write(content)
            tmp_path = tmp.name

        count, status = LenderImporter.import_lenders_from_csv(tmp_path, db)
        os.unlink(tmp_path)

        if status != "success":
            raise HTTPException(status_code=400, detail=status)

        return {"status": "success", "imported": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload-requirements-csv")
def upload_requirements_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload lender requirements CSV file"""
    try:
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            content = file.file.read()
            tmp.write(content)
            tmp_path = tmp.name

        count, status = LenderImporter.import_requirements_from_csv(tmp_path, db)
        os.unlink(tmp_path)

        if status != "success":
            raise HTTPException(status_code=400, detail=status)

        return {"status": "success", "imported": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/search", response_model=List[LenderInfoSchema])
def search_lenders(
    industry: Optional[str] = None,
    state: Optional[str] = None,
    grade: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Search lenders by criteria"""
    query = db.query(LenderInfo).filter(LenderInfo.status == 1)

    if grade:
        query = query.filter(LenderInfo.grade == grade.upper())

    lenders = query.all()

    # Filter by industry and state in Python (since allow_industry is JSON text)
    if industry or state:
        filtered = []
        for lender in lenders:
            if lender.requirements:
                req = lender.requirements[0]
                match = True
                if industry and req.allow_industry:
                    if industry not in req.allow_industry:
                        match = False
                if state and req.allow_state:
                    if state not in req.allow_state:
                        match = False
                if match:
                    filtered.append(lender)
        return filtered

    return lenders
