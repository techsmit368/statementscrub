import uuid
import os
import csv
import io
import secrets
from urllib.parse import unquote
from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserScorecard
from app.models.analysis import Analysis
from app.services.auth import require_user, check_usage_limit
from app.services.pdf_extractor import extract_text_from_pdf, truncate_for_analysis
from app.services.ai_analyzer import analyze_bank_statement
from app.config import settings
from app.services.notifications import notify_analysis_complete

router = APIRouter(tags=["upload"])
templates = Jinja2Templates(directory="app/templates")


def _build_merchants(analyses):
    """Group analyses by account_holder into merchant summary dicts."""
    merchants = {}
    for a in analyses:
        key = (a.account_holder or "").strip() or "Unknown"
        if key not in merchants:
            merchants[key] = {
                "name": key,
                "bank": a.bank_name,
                "statements": [],
                "total_nsf": 0,
                "sum_deposits": 0,
                "sum_balance": 0,
                "latest_risk": "low",
                "latest_rec": None,
                "latest_summary": None,
                "latest_date": None,
                "latest_id": None,
                "mca_detected": False,
            }
        m = merchants[key]
        m["statements"].append(a)
        m["total_nsf"] += int(a.nsf_count or 0)
        m["sum_deposits"] += float(a.avg_monthly_deposits or 0)
        m["sum_balance"] += float(a.avg_daily_balance or 0)
        if a.mca_detected:
            m["mca_detected"] = True
        if a.created_at and (m["latest_date"] is None or a.created_at > m["latest_date"]):
            m["latest_date"] = a.created_at
            m["latest_id"] = a.id
            if a.result_json:
                rf = a.result_json.get("red_flags", {})
                m["latest_risk"] = rf.get("risk_level", "low") or "low"
                m["latest_rec"] = a.result_json.get("approval_recommendation")
                m["latest_summary"] = a.result_json.get("lender_summary", "")

    result = []
    for name, m in merchants.items():
        count = len(m["statements"])
        m["count"] = count
        m["avg_deposits"] = m["sum_deposits"] / count if count else 0
        m["avg_balance"] = m["sum_balance"] / count if count else 0
        result.append(m)

    result.sort(key=lambda x: x["latest_date"] or __import__("datetime").datetime(2000, 1, 1), reverse=True)
    return result


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
        .all()
    )
    merchants = _build_merchants(analyses)
    recent = analyses[:5]  # last 5 for sidebar
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "merchants": merchants, "recent": recent, "active_page": "dashboard"},
    )


@router.get("/merchant/{merchant_name}", response_class=HTMLResponse)
async def merchant_detail(
    merchant_name: str,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    name = unquote(merchant_name)
    all_analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )
    statements = [
        a for a in all_analyses
        if ((a.account_holder or "").strip() or "Unknown") == name
    ]
    if not statements:
        return RedirectResponse("/dashboard", status_code=302)

    # Build combined stats
    total_nsf = sum(int(a.nsf_count or 0) for a in statements)
    avg_deposits = sum(float(a.avg_monthly_deposits or 0) for a in statements) / len(statements)
    avg_balance = sum(float(a.avg_daily_balance or 0) for a in statements) / len(statements)
    mca = any(a.mca_detected for a in statements)

    latest = statements[0]
    latest_risk = "low"
    latest_rec = None
    latest_summary = None
    if latest.result_json:
        rf = latest.result_json.get("red_flags", {})
        latest_risk = rf.get("risk_level", "low") or "low"
        latest_rec = latest.result_json.get("approval_recommendation")
        latest_summary = latest.result_json.get("lender_summary", "")

    # Date range string
    dates = sorted([a.created_at for a in statements if a.created_at])
    date_range = None
    if dates:
        if len(dates) > 1:
            date_range = f"{dates[0].strftime('%b %Y')} – {dates[-1].strftime('%b %Y')}"
        else:
            date_range = dates[0].strftime("%b %Y")

    banks = list({a.bank_name for a in statements if a.bank_name})
    combined = {
        "avg_deposits": avg_deposits,
        "avg_balance": avg_balance,
        "total_nsf": total_nsf,
        "mca_detected": mca,
        "latest_risk": latest_risk,
        "latest_rec": latest_rec,
        "latest_summary": latest_summary,
        "bank": banks[0] if len(banks) == 1 else (", ".join(banks[:2]) if banks else None),
        "date_range": date_range,
    }

    return templates.TemplateResponse(
        "merchant.html",
        {
            "request": request,
            "user": user,
            "merchant_name": name,
            "statements": statements,
            "combined": combined,
        },
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

    merchant_slug = (analysis.account_holder or "").strip() or "Unknown"
    from urllib.parse import quote
    return RedirectResponse(f"/merchant/{quote(merchant_slug, safe='')}", status_code=302)


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
    scorecard = db.query(UserScorecard).filter(UserScorecard.user_id == user.id).first()
    return templates.TemplateResponse(
        "results.html",
        {"request": request, "user": user, "analysis": analysis, "result": result, "scorecard": scorecard},
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


# ─── Print (PDF) export ────────────────────────────────────────────────────────

@router.get("/results/{analysis_id}/print", response_class=HTMLResponse)
async def print_report(
    analysis_id: int,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Print-friendly HTML report — browser prints/saves as PDF."""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id, Analysis.user_id == user.id
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Report not found.")
    result = analysis.result_json or {}
    return templates.TemplateResponse(
        "print_report.html",
        {"request": request, "user": user, "analysis": analysis, "result": result},
    )


# ─── CSV export ────────────────────────────────────────────────────────────────

@router.get("/results/{analysis_id}/export/csv")
async def export_csv(
    analysis_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Download the monthly cashflow breakdown as a CSV file."""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id, Analysis.user_id == user.id
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Report not found.")

    result = analysis.result_json or {}
    summary = result.get("summary", {})
    rf = result.get("red_flags", {})
    monthly = result.get("monthly_breakdown", [])

    output = io.StringIO()
    writer = csv.writer(output)

    # Header block
    writer.writerow(["StatementScrub — Bank Statement Analysis Report"])
    writer.writerow(["Account Holder", result.get("account_holder", "")])
    writer.writerow(["Bank", result.get("bank_name", "")])
    writer.writerow(["Statement Period", analysis.statement_period or ""])
    writer.writerow(["Report ID", analysis.id])
    writer.writerow(["Generated", analysis.created_at.strftime("%Y-%m-%d") if analysis.created_at else ""])
    writer.writerow([])

    # Summary block
    writer.writerow(["SUMMARY"])
    writer.writerow(["Avg Monthly Deposits", summary.get("avg_monthly_deposits", 0)])
    writer.writerow(["Avg Monthly Withdrawals", summary.get("avg_monthly_withdrawals", 0)])
    writer.writerow(["Avg Daily Balance", summary.get("avg_daily_balance", 0)])
    writer.writerow(["Ending Balance", summary.get("ending_balance", 0)])
    writer.writerow(["Lowest Balance", summary.get("lowest_balance", 0)])
    writer.writerow(["Highest Balance", summary.get("highest_balance", 0)])
    writer.writerow(["Net Cash Flow", summary.get("net_cash_flow", 0)])
    writer.writerow([])

    # Risk flags block
    writer.writerow(["RISK FLAGS"])
    writer.writerow(["NSF Count", rf.get("nsf_count", 0)])
    writer.writerow(["Overdraft Count", rf.get("overdraft_count", 0)])
    writer.writerow(["Overdraft Fees Total", rf.get("overdraft_fees_total", 0)])
    writer.writerow(["MCA Loans Detected", rf.get("mca_loans_detected", False)])
    writer.writerow(["Gambling Transactions", rf.get("gambling_transactions", False)])
    writer.writerow(["Structuring Risk", rf.get("structuring_risk", False)])
    writer.writerow(["Circular Deposits", rf.get("circular_deposits_detected", False)])
    writer.writerow(["Account Cycling", rf.get("account_cycling_detected", False)])
    writer.writerow(["Velocity Spike", rf.get("velocity_spike_detected", False)])
    writer.writerow(["ACH Returns", rf.get("ach_returns_count", 0)])
    writer.writerow(["Risk Score", rf.get("risk_score", 0)])
    writer.writerow(["Risk Level", rf.get("risk_level", "")])
    writer.writerow(["Recommendation", result.get("approval_recommendation", "")])
    writer.writerow([])

    # Monthly breakdown
    if monthly:
        writer.writerow(["MONTHLY BREAKDOWN"])
        writer.writerow(["Month", "Total Deposits", "Total Withdrawals", "Ending Balance", "NSF Count"])
        for mo in monthly:
            writer.writerow([
                mo.get("month", ""),
                mo.get("total_deposits", 0),
                mo.get("total_withdrawals", 0),
                mo.get("ending_balance", 0),
                mo.get("nsf_count", 0),
            ])
        writer.writerow([])

    # Income sources
    sources = result.get("income", {}).get("sources", [])
    if sources:
        writer.writerow(["INCOME SOURCES"])
        writer.writerow(["Name", "Type", "Avg Monthly Amount", "Frequency"])
        for src in sources:
            writer.writerow([
                src.get("name", ""),
                src.get("type", ""),
                src.get("avg_monthly_amount", 0),
                src.get("frequency", ""),
            ])

    output.seek(0)
    filename = f"statementiq_report_{analysis_id}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─── Batch upload ──────────────────────────────────────────────────────────────

@router.post("/upload/batch")
async def batch_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Upload and analyze multiple bank statement PDFs at once."""
    if not files or all(f.filename == "" for f in files):
        return RedirectResponse("/dashboard", status_code=302)

    processed = 0
    failed = 0

    for file in files:
        if not file.filename:
            continue
        if not check_usage_limit(user):
            break  # Hit plan limit — stop processing

        if not file.filename.lower().endswith(".pdf"):
            failed += 1
            continue

        content = await file.read()
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            failed += 1
            continue

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
            processed += 1

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
        except Exception:
            analysis.status = "failed"
            db.commit()
            failed += 1

    return RedirectResponse(f"/dashboard?batch_done={processed}&batch_failed={failed}", status_code=302)


# ─── Custom Scorecard ──────────────────────────────────────────────────────────

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    scorecard = db.query(UserScorecard).filter(UserScorecard.user_id == user.id).first()
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "user": user, "scorecard": scorecard},
    )


@router.post("/settings/scorecard")
async def save_scorecard(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    form = await request.form()
    scorecard = db.query(UserScorecard).filter(UserScorecard.user_id == user.id).first()
    if not scorecard:
        scorecard = UserScorecard(user_id=user.id)
        db.add(scorecard)

    scorecard.max_nsf_count = int(form.get("max_nsf_count", 3))
    scorecard.max_overdraft_count = int(form.get("max_overdraft_count", 3))
    scorecard.min_avg_daily_balance = float(form.get("min_avg_daily_balance", 500))
    scorecard.min_months_coverage = int(form.get("min_months_coverage", 3))
    scorecard.allow_mca = form.get("allow_mca") == "on"
    scorecard.auto_decline_gambling = form.get("auto_decline_gambling") == "on"
    scorecard.max_risk_score = int(form.get("max_risk_score", 60))
    scorecard.min_monthly_income = float(form.get("min_monthly_income", 2000))
    db.commit()
    return RedirectResponse("/settings?saved=1", status_code=302)


@router.post("/settings/api-key")
async def generate_api_key(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    user.api_key = f"ss_{secrets.token_hex(24)}"
    db.commit()
    return RedirectResponse("/settings?key_generated=1", status_code=302)
