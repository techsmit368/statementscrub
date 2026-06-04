import os
import json
import httpx
from fastapi import APIRouter, Request, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.analysis import Analysis
from app.services.pdf_extractor import extract_text_from_pdf, truncate_for_analysis
from app.services.ai_analyzer import analyze_bank_statement
from app.config import settings

router = APIRouter(prefix="/telegram", tags=["telegram"])

TELEGRAM_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"


async def send_message(chat_id: int, text: str, parse_mode: str = "Markdown"):
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        })


async def download_file(file_id: str) -> bytes:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id})
        file_path = r.json()["result"]["file_path"]
        file_r = await client.get(f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}")
        return file_r.content


def get_user_by_telegram(telegram_id: int) -> User | None:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.telegram_id == str(telegram_id)).first()
    finally:
        db.close()


def get_user_by_token(token: str) -> User | None:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.telegram_token == token).first()
    finally:
        db.close()


async def handle_update(update: dict):
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    document = message.get("document")

    if not chat_id:
        return

    # /start — welcome
    if text == "/start":
        await send_message(chat_id,
            "👋 *Welcome to StatementScrub Bot!*\n\n"
            "I analyze bank statement PDFs instantly.\n\n"
            "To get started:\n"
            "1️⃣ Log in at *statementscrub.com*\n"
            "2️⃣ Go to Dashboard → Connect Telegram\n"
            "3️⃣ Copy your link code and send it here\n\n"
            "Then just send me any bank statement PDF and I'll analyze it! 📊"
        )
        return

    # /help
    if text == "/help":
        await send_message(chat_id,
            "📋 *StatementScrub Bot Help*\n\n"
            "• Send a *PDF bank statement* → get instant analysis\n"
            "• Send up to *4 PDFs at once*\n"
            "• Use `/link YOUR_CODE` to connect your account\n"
            "• Use `/status` to check your plan\n\n"
            "Need help? Visit *statementscrub.com*"
        )
        return

    # /link TOKEN — connect Telegram to account
    if text.startswith("/link "):
        token = text.replace("/link ", "").strip()
        user = get_user_by_token(token)
        if not user:
            await send_message(chat_id, "❌ Invalid code. Please copy the exact code from your StatementScrub dashboard.")
            return
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.id == user.id).first()
            db_user.telegram_id = str(chat_id)
            db.commit()
        finally:
            db.close()
        await send_message(chat_id,
            f"✅ *Account linked successfully!*\n\n"
            f"Welcome, {user.full_name or user.email}!\n"
            f"Plan: *{user.plan.upper()}*\n\n"
            f"Now send me any bank statement PDF to analyze it. 📄"
        )
        return

    # /status
    if text == "/status":
        user = get_user_by_telegram(chat_id)
        if not user:
            await send_message(chat_id, "❌ Account not linked. Use `/link YOUR_CODE` to connect your StatementScrub account.")
            return
        await send_message(chat_id,
            f"👤 *{user.full_name or user.email}*\n"
            f"Plan: *{user.plan.upper()}*\n"
            f"Reports used: *{user.analyses_used}*\n\n"
            f"Send a PDF to analyze it!"
        )
        return

    # PDF document received
    if document and document.get("mime_type") == "application/pdf":
        user = get_user_by_telegram(chat_id)
        if not user:
            await send_message(chat_id,
                "❌ *Account not linked.*\n\n"
                "Please link your StatementScrub account first:\n"
                "1. Go to *statementscrub.com* → Dashboard\n"
                "2. Click *Connect Telegram*\n"
                "3. Send me `/link YOUR_CODE`"
            )
            return

        if user.plan not in ("starter", "pro"):
            await send_message(chat_id,
                "❌ *Telegram bot requires Starter or Pro plan.*\n\n"
                "Upgrade at statementscrub.com to use the bot."
            )
            return

        await send_message(chat_id, "⏳ *Analyzing your bank statement...*\n\nThis takes 15–30 seconds.")

        try:
            pdf_bytes = await download_file(document["file_id"])
            raw_text = extract_text_from_pdf(pdf_bytes)
            text_for_ai = truncate_for_analysis(raw_text)
            result = analyze_bank_statement(text_for_ai)

            rf = result.get("red_flags", {})
            summary = result.get("summary", {})
            income = result.get("income", {})
            risk = rf.get("risk_level", "low").upper()
            rec = result.get("approval_recommendation", "review").upper()
            risk_score = rf.get("risk_score", 0)

            risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}.get(risk, "⚪")
            rec_emoji = {"APPROVE": "✅", "REVIEW": "⚠️", "DECLINE": "❌"}.get(rec, "⚠️")

            report = (
                f"📊 *StatementScrub Analysis*\n"
                f"{'─' * 28}\n"
                f"🏦 *{result.get('bank_name', 'Unknown Bank')}*\n"
                f"👤 {result.get('account_holder', document.get('file_name', 'Unknown'))}\n\n"
                f"💰 Avg Monthly Deposits: *${summary.get('avg_monthly_deposits', 0):,.0f}*\n"
                f"💸 Avg Monthly Expenses: *${summary.get('avg_monthly_withdrawals', 0):,.0f}*\n"
                f"💳 Avg Daily Balance: *${summary.get('avg_daily_balance', 0):,.0f}*\n"
                f"📉 Ending Balance: *${summary.get('ending_balance', 0):,.0f}*\n\n"
                f"🚩 *Risk Flags*\n"
                f"• NSF Events: *{rf.get('nsf_count', 0)}*\n"
                f"• Overdrafts: *{rf.get('overdraft_count', 0)}*\n"
                f"• MCA Loans: *{'⚠️ Detected' if rf.get('mca_loans_detected') else '✅ None'}*\n"
                f"• Gambling: *{'⚠️ Detected' if rf.get('gambling_transactions') else '✅ None'}*\n"
                f"• Declining Trend: *{'⚠️ Yes' if rf.get('declining_balance_trend') else '✅ No'}*\n\n"
                f"{risk_emoji} Risk Score: *{risk_score}/100 — {risk}*\n"
                f"{rec_emoji} Decision: *{rec}*\n\n"
            )

            if result.get("lender_summary"):
                report += f"📋 _{result['lender_summary']}_\n\n"

            # Save analysis to DB
            db = SessionLocal()
            try:
                analysis = Analysis(
                    user_id=user.id,
                    filename=document.get("file_name", "telegram_upload.pdf"),
                    bank_name=result.get("bank_name", ""),
                    account_holder=result.get("account_holder", ""),
                    avg_monthly_deposits=summary.get("avg_monthly_deposits", 0),
                    avg_monthly_withdrawals=summary.get("avg_monthly_withdrawals", 0),
                    avg_daily_balance=summary.get("avg_daily_balance", 0),
                    ending_balance=summary.get("ending_balance", 0),
                    lowest_balance=summary.get("lowest_balance", 0),
                    nsf_count=rf.get("nsf_count", 0),
                    overdraft_count=rf.get("overdraft_count", 0),
                    mca_detected=rf.get("mca_loans_detected", False),
                    result_json=result,
                    status="complete",
                )
                db.add(analysis)
                db_user = db.query(User).filter(User.id == user.id).first()
                db_user.analyses_used += 1
                db.commit()
                db.refresh(analysis)
                report += f"🔗 [View Full Report](https://statementscrub.com/results/{analysis.id})"
            finally:
                db.close()

            await send_message(chat_id, report)

        except Exception as e:
            await send_message(chat_id, f"❌ Analysis failed: {str(e)[:200]}\n\nPlease try again or visit statementscrub.com")

    elif document:
        await send_message(chat_id, "❌ Please send a *PDF* file. Other file types are not supported.")

    elif text and not text.startswith("/"):
        await send_message(chat_id, "📄 Send me a *PDF bank statement* to analyze it.\n\nType /help for more info.")


@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    update = await request.json()
    background_tasks.add_task(handle_update, update)
    return {"ok": True}
