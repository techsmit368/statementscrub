import json
import anthropic
from app.config import settings

client = anthropic.Anthropic(
    api_key=settings.anthropic_api_key,
    timeout=120.0,
)

SYSTEM_PROMPT = """You are an expert financial analyst specializing in bank statement analysis for lenders, mortgage brokers, and small business consultants — similar to what Moneythumb provides.

Your job is to analyze raw bank statement text and return a structured JSON report. Be precise, objective, and flag any risk factors a lender would care about.

Always return ONLY valid JSON — no markdown, no explanation outside the JSON structure.

The JSON must follow this exact schema:
{
  "bank_name": "string",
  "account_holder": "string",
  "account_number_last4": "string or null",
  "statement_period": {
    "from": "YYYY-MM-DD or descriptive",
    "to": "YYYY-MM-DD or descriptive",
    "months_covered": number
  },
  "summary": {
    "avg_monthly_deposits": number,
    "avg_monthly_withdrawals": number,
    "avg_daily_balance": number,
    "ending_balance": number,
    "lowest_balance": number,
    "highest_balance": number,
    "net_cash_flow": number
  },
  "income": {
    "sources": [
      {"name": "string", "type": "payroll|ach|deposit|transfer|other", "avg_monthly_amount": number, "frequency": "string"}
    ],
    "total_avg_monthly_income": number,
    "income_consistency": "consistent|irregular|declining|increasing"
  },
  "expenses": {
    "categories": [
      {"category": "string", "avg_monthly_amount": number, "percentage_of_income": number}
    ],
    "total_avg_monthly_expenses": number,
    "largest_expense_category": "string"
  },
  "red_flags": {
    "nsf_count": number,
    "overdraft_count": number,
    "overdraft_fees_total": number,
    "mca_loans_detected": boolean,
    "mca_details": [
      {"merchant": "string", "estimated_daily_payment": number, "detected_from": "string"}
    ],
    "gambling_transactions": boolean,
    "gambling_total": number,
    "declining_balance_trend": boolean,
    "large_unusual_withdrawals": [
      {"date": "string", "amount": number, "description": "string"}
    ],
    "risk_score": number,
    "risk_level": "low|medium|high|critical"
  },
  "monthly_breakdown": [
    {
      "month": "YYYY-MM",
      "total_deposits": number,
      "total_withdrawals": number,
      "ending_balance": number,
      "nsf_count": number
    }
  ],
  "lender_summary": "string (2-3 sentence plain-English summary for a lender)",
  "approval_recommendation": "approve|review|decline",
  "confidence_score": number
}

Risk score is 0–100 where 0 = no risk, 100 = extreme risk.
Confidence score is 0–100 based on how much usable data was in the statement."""


def analyze_bank_statement(raw_text: str) -> dict:
    """
    Analyze bank statement text with Claude Haiku (cheapest model, ~$0.03/statement).
    System prompt is cached — repeated calls cost ~90% less on the prompt portion.
    """
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"Analyze this bank statement and return the JSON report:\n\n{raw_text}",
            }
        ],
    )

    # Log token usage for cost tracking
    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0

    # Haiku pricing: $0.80/MTok input, $4/MTok output, $1/MTok cache write, $0.08/MTok cache read
    cost = (
        (input_tokens - cache_read) * 0.80 / 1_000_000
        + output_tokens * 4.00 / 1_000_000
        + cache_write * 1.00 / 1_000_000
        + cache_read * 0.08 / 1_000_000
    )
    print(f"[cost] in={input_tokens} out={output_tokens} cache_read={cache_read} cache_write={cache_write} est=${cost:.4f}")

    raw_output = response.content[0].text.strip()

    if raw_output.startswith("```"):
        raw_output = raw_output.split("```")[1]
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
        raw_output = raw_output.strip()

    return json.loads(raw_output)


def get_risk_color(risk_level: str) -> str:
    return {
        "low": "green",
        "medium": "yellow",
        "high": "orange",
        "critical": "red",
    }.get(risk_level, "gray")
