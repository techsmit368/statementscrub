"""
Core lender matching engine.
Matches merchant financial criteria against lender requirements.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.lender import LenderInfo, LenderRequirement


def match_lenders(
    db: Session,
    industry: str,
    state: str,
    avg_monthly_deposits: float,
    avg_daily_balance: float,
    nsf_count: int,
    time_in_business: int,      # months
    current_positions: int,
    credit_score: int = 0,
) -> Dict[str, Any]:
    """
    Returns dict with matching lenders grouped by grade, plus fail reasons per lender.
    A lender qualifies if ANY of its requirement rows matches all criteria.
    """
    industry_upper = (industry or "").strip().upper()
    state_upper = (state or "").strip().upper()

    lenders = (
        db.query(LenderInfo)
        .filter(LenderInfo.status == 1)
        .filter(LenderInfo.grade.in_(["a", "b", "c", "d"]))
        .all()
    )

    matched = []
    declined = []

    for lender in lenders:
        if not lender.requirements:
            continue

        qualified = False
        fail_reasons = []

        for req in lender.requirements:
            req_industry = (req.allow_industry or "").strip().upper()

            # Industry filter
            if industry_upper and req_industry and req_industry not in ("N\\A", "N/A", "OTHER"):
                if req_industry != industry_upper:
                    continue  # this requirement row is for a different industry

            # State filter
            if state_upper and req.allow_state:
                allowed_states = [s for s in req.allow_state if s]
                if state_upper not in allowed_states:
                    continue  # this requirement row doesn't cover this state

            # Financial checks — collect all failures for this row
            row_fails = []

            if req.min_avg_deposit > 0 and avg_monthly_deposits < req.min_avg_deposit:
                row_fails.append(f"Min avg deposits ${req.min_avg_deposit:,.0f} (yours ${avg_monthly_deposits:,.0f})")

            if req.min_daily_balance > 0 and avg_daily_balance < req.min_daily_balance:
                row_fails.append(f"Min daily balance ${req.min_daily_balance:,.0f} (yours ${avg_daily_balance:,.0f})")

            if req.max_neg_days > 0 and nsf_count > req.max_neg_days:
                row_fails.append(f"Max NSF days {req.max_neg_days} (yours {nsf_count})")

            if req.nsf_days > 0 and nsf_count > req.nsf_days:
                row_fails.append(f"Max NSF count {req.nsf_days} (yours {nsf_count})")

            if req.time_in_business > 0 and time_in_business < req.time_in_business:
                row_fails.append(f"Min {req.time_in_business} months in business (yours {time_in_business})")

            if req.max_position > 0 and current_positions > req.max_position:
                row_fails.append(f"Max {req.max_position} positions (yours {current_positions})")

            if credit_score > 0 and req.min_credit_score > 0 and credit_score < req.min_credit_score:
                row_fails.append(f"Min credit score {req.min_credit_score} (yours {credit_score})")

            if not row_fails:
                qualified = True
                break  # one passing requirement row is enough

            fail_reasons = row_fails  # keep last row's failures for display

        grade = (lender.grade or "").lower()
        entry = {
            "id": lender.id,
            "lender_name": lender.lender_name,
            "lender_code": lender.lender_code,
            "grade": grade.upper(),
            "email_1": lender.email_1,
            "email_2": lender.email_2,
            "phone_1": lender.phone_1,
            "phone_2": lender.phone_2,
            "Web_link": lender.Web_link,
            "advance_amount": lender.advance_amount,
            "notes": lender.notes,
            "isorep": lender.isorep,
            "default_on_advance": lender.default_on_advance,
            "consolidation": lender.consolidation,
        }

        if qualified:
            matched.append(entry)
        else:
            entry["fail_reasons"] = fail_reasons
            declined.append(entry)

    # Group matched by grade
    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    matched.sort(key=lambda x: (grade_order.get(x["grade"], 9), x["lender_name"]))

    by_grade = {"A": [], "B": [], "C": [], "D": []}
    for lender in matched:
        g = lender["grade"]
        if g in by_grade:
            by_grade[g].append(lender)

    return {
        "total_matched": len(matched),
        "total_lenders_checked": len(lenders),
        "by_grade": by_grade,
        "all_matched": matched,
        "declined_sample": declined[:20],
    }


def get_all_industries(db: Session) -> List[str]:
    """Return sorted unique industry list from requirements."""
    rows = db.query(LenderRequirement.allow_industry).distinct().all()
    industries = set()
    for row in rows:
        val = (row[0] or "").strip()
        if val and val not in ("N\\A", "N/A", ""):
            industries.add(val.upper())
    return sorted(industries)
