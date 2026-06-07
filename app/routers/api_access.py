"""
REST API — Moneythumb-equivalent programmatic access.
Auth: X-API-Key header or ?api_key= query param.
Endpoints:
  GET  /api/v1/me
  POST /api/v1/analyze
  GET  /api/v1/analyses
  GET  /api/v1/analyses/{id}
  POST /api/v1/key/generate
"""
import secrets
from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.analysis import Analysis
from app.services.pdf_extractor import extract_text_from_pdf, truncate_for_analysis
from app.services.ai_analyzer import analyze_bank_statement
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["api"])


def _get_api_user(
    x_api_key: str | None = Header(default=None),
    api_key: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> User:
    key = x_api_key or api_key
    if not key:
        raise HTTPException(status_code=401, detail="API key required. Pass X-API-Key header or ?api_key= param.")
    user = db.query(User).filter(User.api_key == key, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key.")
    return user


@router.get("/me")
def api_me(user: User = Depends(_get_api_user)):
    """Return account info for the authenticated API key."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "plan": user.plan,
        "analyses_used": user.analyses_used,
    }


@router.post("/analyze")
async def api_analyze(
    file: UploadFile = File(..., description="Bank statement PDF"),
    user: User = Depends(_get_api_user),
    db: Session = Depends(get_db),
):
    """Upload a bank statement PDF and receive a full structured JSON report."""
    # Check plan limits (same as web upload)
    from app.services.auth import check_usage_limit
    if not check_usage_limit(user):
        raise HTTPException(status_code=402, detail=f"Usage limit reached for {user.plan} plan.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.max_upload_size_mb}MB.")

    analysis = Analysis(user_id=user.id, filename=file.filename, status="processing")
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    try:
        raw_text = extract_text_from_pdf(content)
        truncated = truncate_for_analysis(raw_text)
        result = analyze_bank_statement(truncated)

        summary = result.get("summary", {})
        red_flags = result.get("red_flags", {})
        period = result.get("statement_period", {})

        analysis.bank_name = result.get("bank_name", "")
        analysis.account_holder = result.get("account_holder", "")
        analysis.statement_period = f"{period.get('from', '')} to {period.get('to', '')}"
        analysis.avg_monthly_deposits = summary.get("avg_monthly_deposits", 0)
        analysis.avg_monthly_withdrawals = summary.get("avg_monthly_withdrawals", 0)
        analysis.avg_daily_balance = summary.get("avg_daily_balance", 0)
        analysis.ending_balance = summary.get("ending_balance", 0)
        analysis.lowest_balance = summary.get("lowest_balance", 0)
        analysis.nsf_count = red_flags.get("nsf_count", 0)
        analysis.overdraft_count = red_flags.get("overdraft_count", 0)
        analysis.mca_detected = red_flags.get("mca_loans_detected", False)
        analysis.result_json = result
        analysis.raw_text = raw_text[:5000]
        analysis.status = "complete"
        user.analyses_used += 1
        db.commit()
    except Exception as e:
        analysis.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    return {
        "analysis_id": analysis.id,
        "status": "complete",
        "result": result,
    }


@router.get("/analyses")
def api_list_analyses(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(_get_api_user),
    db: Session = Depends(get_db),
):
    """List your analyses, newest first."""
    rows = (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": db.query(Analysis).filter(Analysis.user_id == user.id).count(),
        "offset": offset,
        "limit": limit,
        "analyses": [
            {
                "id": a.id,
                "filename": a.filename,
                "bank_name": a.bank_name,
                "account_holder": a.account_holder,
                "statement_period": a.statement_period,
                "avg_monthly_deposits": a.avg_monthly_deposits,
                "nsf_count": a.nsf_count,
                "mca_detected": a.mca_detected,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in rows
        ],
    }


@router.get("/analyses/{analysis_id}")
def api_get_analysis(
    analysis_id: int,
    user: User = Depends(_get_api_user),
    db: Session = Depends(get_db),
):
    """Get the full JSON report for a specific analysis."""
    a = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return {
        "id": a.id,
        "filename": a.filename,
        "status": a.status,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "result": a.result_json,
    }


@router.post("/key/generate")
def api_generate_key(
    user: User = Depends(_get_api_user),
    db: Session = Depends(get_db),
):
    """Rotate (re-generate) your API key. Old key is immediately invalidated."""
    user.api_key = f"ss_{secrets.token_hex(24)}"
    db.commit()
    return {"api_key": user.api_key, "note": "Store this key securely — it won't be shown again."}
