<?php
const SYSTEM_PROMPT = <<<'PROMPT'
You are an expert financial analyst specializing in bank statement analysis for lenders, mortgage brokers, and small business consultants.

Analyze the bank statement text and return ONLY valid JSON — no markdown, no explanation outside the JSON.

Use this exact schema:
{
  "bank_name": "string",
  "account_holder": "string",
  "account_number_last4": "string or null",
  "statement_period": {"from": "string", "to": "string", "months_covered": number},
  "summary": {
    "avg_monthly_deposits": number, "avg_monthly_withdrawals": number,
    "avg_daily_balance": number, "ending_balance": number,
    "lowest_balance": number, "highest_balance": number, "net_cash_flow": number
  },
  "income": {
    "sources": [{"name": "string", "type": "payroll|ach|deposit|transfer|other", "avg_monthly_amount": number, "frequency": "string"}],
    "total_avg_monthly_income": number,
    "income_consistency": "consistent|irregular|declining|increasing"
  },
  "expenses": {
    "categories": [{"category": "string", "avg_monthly_amount": number, "percentage_of_income": number}],
    "total_avg_monthly_expenses": number,
    "largest_expense_category": "string"
  },
  "red_flags": {
    "nsf_count": number, "overdraft_count": number, "overdraft_fees_total": number,
    "mca_loans_detected": boolean,
    "mca_details": [{"merchant": "string", "estimated_daily_payment": number, "detected_from": "string"}],
    "gambling_transactions": boolean, "gambling_total": number,
    "declining_balance_trend": boolean,
    "large_unusual_withdrawals": [{"date": "string", "amount": number, "description": "string"}],
    "risk_score": number,
    "risk_level": "low|medium|high|critical"
  },
  "monthly_breakdown": [
    {"month": "YYYY-MM", "total_deposits": number, "total_withdrawals": number, "ending_balance": number, "nsf_count": number}
  ],
  "lender_summary": "string",
  "approval_recommendation": "approve|review|decline",
  "confidence_score": number
}
PROMPT;

function analyze_with_claude(string $text): array {
    set_time_limit(120);

    $payload = json_encode([
        'model'      => 'claude-haiku-4-5-20251001',
        'max_tokens' => 4096,
        'system'     => [['type' => 'text', 'text' => SYSTEM_PROMPT, 'cache_control' => ['type' => 'ephemeral']]],
        'messages'   => [['role' => 'user', 'content' => "Analyze this bank statement and return the JSON report:\n\n$text"]],
    ]);

    $ch = curl_init('https://api.anthropic.com/v1/messages');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => $payload,
        CURLOPT_TIMEOUT        => 120,
        CURLOPT_HTTPHEADER     => [
            'Content-Type: application/json',
            'x-api-key: ' . ANTHROPIC_API_KEY,
            'anthropic-version: 2023-06-01',
            'anthropic-beta: prompt-caching-2024-07-31',
        ],
    ]);

    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curl_error = curl_error($ch);
    curl_close($ch);

    if ($curl_error) throw new Exception("Connection error: $curl_error");
    if ($http_code !== 200) throw new Exception("API error $http_code: $response");

    $data = json_decode($response, true);
    $raw = $data['content'][0]['text'] ?? '';

    // Strip markdown fences if present
    $raw = preg_replace('/^```(?:json)?\s*/i', '', trim($raw));
    $raw = preg_replace('/\s*```$/', '', $raw);

    $result = json_decode(trim($raw), true);
    if (!$result) throw new Exception("Invalid JSON from AI: " . substr($raw, 0, 200));

    return $result;
}
