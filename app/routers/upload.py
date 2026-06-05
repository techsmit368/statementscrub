import uuid
import os
import secrets
from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.analysis import Analysis
from app.services.auth import require_user, check_usage_limit
from app.services.pdf_extractor import extract_text_from_pdf, truncate_for_analysis
from app.services.ai_analyzer import analyze_bank_statement
from app.config import settings
from app.services.notifications import notify_analysis_complete

router = APIRouter(tags=["upload"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .limit(20)
        .all()
    )
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "analyses": analyses},
    )


@router.post("/upload")
async def upload_statement(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not check_usage_limit(user):
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": user,
                "error": f"You've reached your {user.plan} plan limit. Please upgrade.",
                "analyses": [],
            },
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.max_upload_size_mb}MB.")

    # Create analysis record
    analysis = Analysis(
        user_id=user.id,
        filename=file.filename,
        status="processing",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    try:
        raw_text = extract_text_from_pdf(content)
        truncated = truncate_for_analysis(raw_text)

        result = analyze_bank_statement(truncated)

        # Persist structured results
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
        analysis.raw_text = raw_text[:5000]  # Store first 5k chars for reference
        analysis.status = "complete"

        user.analyses_used += 1
        db.commit()

        background_tasks.add_task(
            notify_analysis_complete,
            user.email,
            analysis.bank_name or "Unknown Bank",
            analysis.account_holder or "Unknown",
            red_flags.get("risk_level", "unknown"),
            red_flags.get("risk_score", 0),
            result.get("approval_recommendation", "review"),
            summary.get("avg_monthly_deposits", 0),
            red_flags.get("nsf_count", 0),
            red_flags.get("mca_loans_detected", False),
        )

    except Exception as e:
        analysis.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    return RedirectResponse(f"/results/{analysis.id}", status_code=302)


@router.get("/results/{analysis_id}", response_class=HTMLResponse)
async def view_results(
    analysis_id: int,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id, Analysis.user_id == user.id
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Report not found.")

    result = analysis.result_json or {}
    return templates.TemplateResponse(
        "results.html",
        {"request": request, "user": user, "analysis": analysis, "result": result},
    )


@router.post("/results/{analysis_id}/delete")
async def delete_analysis(
    analysis_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id, Analysis.user_id == user.id
    ).first()
    if analysis:
        db.delete(analysis)
        db.commit()
    return RedirectResponse("/dashboard", status_code=302)


@router.post("/telegram/connect")
async def telegram_connect(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not user.telegram_token:
        user.telegram_token = secrets.token_hex(8)
        db.commit()
        db.refresh(user)
    return RedirectResponse("/dashboard", status_code=302)
