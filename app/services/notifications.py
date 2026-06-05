import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


def _send(subject: str, html: str) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        print(f"[notify] SMTP not configured — skipping: {subject}")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"StatementScrub <{settings.smtp_user}>"
        msg["To"] = settings.notify_email
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, settings.notify_email, msg.as_string())
        print(f"[notify] Sent: {subject}")
    except Exception as e:
        print(f"[notify] Failed to send '{subject}': {e}")


def notify_new_registration(email: str, full_name: str) -> None:
    _send(
        subject=f"🎉 New Registration — {email}",
        html=f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto;background:#f8fafc;padding:32px;border-radius:12px">
          <div style="background:linear-gradient(135deg,#0ea5e9,#6366f1);padding:20px 24px;border-radius:8px;margin-bottom:24px">
            <h2 style="color:white;margin:0;font-size:18px">🎉 New User Registered</h2>
          </div>
          <table style="width:100%;border-collapse:collapse">
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Name</td><td style="padding:8px 0;font-weight:600;color:#0f172a">{full_name or '—'}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Email</td><td style="padding:8px 0;font-weight:600;color:#0f172a">{email}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Plan</td><td style="padding:8px 0;font-weight:600;color:#0ea5e9">Free</td></tr>
          </table>
          <div style="margin-top:20px;padding:12px;background:#e0f2fe;border-radius:8px;font-size:13px;color:#0369a1">
            Go say hi — convert them to a paid plan 💪
          </div>
        </div>
        """,
    )


def notify_analysis_complete(user_email: str, bank_name: str, account_holder: str,
                              risk_level: str, risk_score: int, recommendation: str,
                              avg_deposits: float, nsf_count: int, mca_detected: bool) -> None:
    risk_colors = {"low": "#22c55e", "medium": "#f59e0b", "high": "#f97316", "critical": "#ef4444"}
    rec_colors = {"approve": "#22c55e", "review": "#f59e0b", "decline": "#ef4444"}
    color = risk_colors.get(risk_level.lower(), "#64748b")
    rec_color = rec_colors.get(recommendation.lower(), "#64748b")

    _send(
        subject=f"📊 Analysis Complete — {account_holder} ({bank_name})",
        html=f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto;background:#f8fafc;padding:32px;border-radius:12px">
          <div style="background:#0f172a;padding:20px 24px;border-radius:8px;margin-bottom:24px">
            <h2 style="color:white;margin:0;font-size:18px">📊 New Analysis Completed</h2>
            <p style="color:#94a3b8;margin:6px 0 0;font-size:13px">User: {user_email}</p>
          </div>
          <table style="width:100%;border-collapse:collapse">
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Account Holder</td><td style="padding:8px 0;font-weight:600;color:#0f172a">{account_holder}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Bank</td><td style="padding:8px 0;font-weight:600;color:#0f172a">{bank_name}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Avg Monthly Deposits</td><td style="padding:8px 0;font-weight:600;color:#0f172a">${avg_deposits:,.0f}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">NSF Count</td><td style="padding:8px 0;font-weight:600;color:#{'ef4444' if nsf_count > 0 else '22c55e'}">{nsf_count}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">MCA Detected</td><td style="padding:8px 0;font-weight:600;color:#{'f97316' if mca_detected else '22c55e'}">{'Yes ⚠️' if mca_detected else 'No ✓'}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Risk Score</td><td style="padding:8px 0;font-weight:700;color:{color}">{risk_score}/100 — {risk_level.upper()}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Recommendation</td><td style="padding:8px 0;font-weight:700;color:{rec_color}">{recommendation.upper()}</td></tr>
          </table>
        </div>
        """,
    )


def notify_contact_form(name: str, email: str, company: str, role: str, message: str) -> None:
    _send(
        subject=f"📬 Contact Form — {name} ({company or email})",
        html=f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto;background:#f8fafc;padding:32px;border-radius:12px">
          <div style="background:linear-gradient(135deg,#0ea5e9,#6366f1);padding:20px 24px;border-radius:8px;margin-bottom:24px">
            <h2 style="color:white;margin:0;font-size:18px">📬 New Contact Form Submission</h2>
          </div>
          <table style="width:100%;border-collapse:collapse">
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px;width:100px">Name</td><td style="padding:8px 0;font-weight:600;color:#0f172a">{name}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Email</td><td style="padding:8px 0;font-weight:600;color:#0ea5e9">{email}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Company</td><td style="padding:8px 0;font-weight:600;color:#0f172a">{company or '—'}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Role</td><td style="padding:8px 0;font-weight:600;color:#0f172a">{role or '—'}</td></tr>
          </table>
          <div style="margin-top:16px;padding:16px;background:white;border:1px solid #e2e8f0;border-radius:8px;font-size:14px;color:#334155;line-height:1.6">
            {message}
          </div>
          <a href="mailto:{email}" style="display:inline-block;margin-top:16px;background:#0ea5e9;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">
            Reply to {name} →
          </a>
        </div>
        """,
    )


def notify_demo_request(first_name: str, last_name: str, email: str, company: str,
                         role: str, volume: str, preferred_time: str) -> None:
    _send(
        subject=f"🗓️ Demo Request — {first_name} {last_name} ({company or email})",
        html=f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto;background:#f8fafc;padding:32px;border-radius:12px">
          <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:20px 24px;border-radius:8px;margin-bottom:24px">
            <h2 style="color:white;margin:0;font-size:18px">🗓️ New Demo Request</h2>
            <p style="color:#c4b5fd;margin:6px 0 0;font-size:13px">Book a call with this lead!</p>
          </div>
          <table style="width:100%;border-collapse:collapse">
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px;width:130px">Name</td><td style="padding:8px 0;font-weight:600;color:#0f172a">{first_name} {last_name}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Email</td><td style="padding:8px 0;font-weight:600;color:#0ea5e9">{email}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Company</td><td style="padding:8px 0;font-weight:600;color:#0f172a">{company or '—'}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Role</td><td style="padding:8px 0;font-weight:600;color:#0f172a">{role or '—'}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Monthly Volume</td><td style="padding:8px 0;font-weight:600;color:#6366f1">{volume or '—'} statements/mo</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px">Best Time</td><td style="padding:8px 0;font-weight:600;color:#0f172a">{preferred_time or 'Any time'}</td></tr>
          </table>
          <a href="mailto:{email}" style="display:inline-block;margin-top:20px;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">
            Schedule Demo with {first_name} →
          </a>
        </div>
        """,
    )
