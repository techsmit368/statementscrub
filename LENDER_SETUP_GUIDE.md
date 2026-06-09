# Lender Management System Setup Guide

## Overview
This guide explains how to set up and use the **Lender Information & Requirements** tables for StatementIQ.

## Database Tables Created

### 1. `lender_infos` Table
Stores lender company information and lending criteria.

**Key Fields:**
- `lender_name`: Name of the lending company
- `lender_code`: Internal code for the lender
- `grade`: A, B, C, or D (risk grade)
- `status`: 1 = active, 0 = inactive
- Contact info: `email_1`, `email_2`, `phone_1`, `phone_2`, `Web_link`
- `advance_amount`: Maximum advance/loan amount
- `default_on_advance`: "Yes" or "No" - whether lender accepts defaulted advances
- Balance/Deposit Fields:
  - `3months_deposits`: "Minimum" or actual value
  - `3months$deposits`: "Minimum" or "Actual"
  - `mos_balances`: "Minimum" or "Actual"
- `monthly_nsfs`: "Total" or "Average"
- `monNegativeDays`: "Total" or actual value
- `itin_filter`: ITIN requirement filter
- Additional fields: `consolidation`, `equipfinancing`, `termloan`, `line_of_credit`, etc.

### 2. `lender_requirements` Table
Stores minimum requirements for each lender.

**Key Fields:**
- `lender_id`: Foreign key to `lender_infos`
- `allow_industry`: JSON array of allowed industries (e.g., `["Retail", "Food Service"]`)
- `allow_state`: JSON array of allowed states (e.g., `["CA", "NY", "TX"]`)
- `time_in_business`: Minimum months in business (e.g., 12)
- `min_deposit`: Minimum number of deposits (e.g., 30)
- `min_avg_deposit`: Minimum average deposit amount in dollars (e.g., 5000)
- `max_position`: Maximum accounts/positions allowed
- `min_position`: Minimum accounts/positions required
- `max_neg_days`: Maximum negative days allowed (e.g., 5)
- `min_daily_balance`: Minimum daily balance required (e.g., 10000)
- `min_credit_score`: Minimum credit score (e.g., 600)
- `nsf_days`: NSF/insufficient funds days limit
- `min_trucks`: Minimum vehicles (for transportation)

## Setup Instructions

### Step 1: Initialize Database
```bash
python init_db.py
```
This will:
- Create the `lender_infos` and `lender_requirements` tables
- Load sample data for testing

### Step 2: Import Your Lender Data

#### Option A: Using CSV Files
Prepare two CSV files:

**1. Lender Info CSV** (`lenders.csv`)
```csv
lender_name,lender_code,grade,status,email_1,phone_1,Web_link,advance_amount,...
QuickFund,QFC001,A,1,support@quickfund.com,1-800-123-4567,https://quickfund.com,500000,...
```

**2. Requirements CSV** (`requirements.csv`)
```csv
lender_id,allow_industry,allow_state,time_in_business,min_deposit,min_avg_deposit,...
1,"[""Retail"", ""Food Service""]","[""CA"", ""NY""]",12,30,5000,...
```

**Import using API:**
```bash
curl -X POST "http://localhost:8000/api/lenders/upload-csv" \
  -F "file=@lenders.csv"

curl -X POST "http://localhost:8000/api/lenders/upload-requirements-csv" \
  -F "file=@requirements.csv"
```

#### Option B: Using the Sample Templates
Modify the included CSV files:
- `sample_lenders.csv` - Edit with your lender information
- `sample_requirements.csv` - Edit with your requirements

Then import them.

## API Endpoints

### Get All Lenders
```bash
GET /api/lenders/
```

### Get Lenders by Grade
```bash
GET /api/lenders/by-grade/A
```

### Get Specific Lender
```bash
GET /api/lenders/{lender_id}
```

### Get Lender Requirements
```bash
GET /api/lenders/{lender_id}/requirements
```

### Search Lenders
```bash
GET /api/lenders/search?industry=Retail&state=CA&grade=A
```

### Upload CSV File
```bash
POST /api/lenders/upload-csv
POST /api/lenders/upload-requirements-csv
```

## Data Field Mappings

### Deposit Value Selection
The system supports dynamic deposit value selection based on lender preferences:

- If `3months$deposits = "Minimum"` → Use `request.previous_three_months_minimum_deposite`
- If `3months$deposits = "Actual"` → Use `request.noOfDepositeMoney`

### Balance Value Selection
- If `mos_balances = "Minimum"` → Use `request.daily_balance_three_months_minimum`
- If `mos_balances = "Actual"` → Use `request.dailyBalance`

### NSF/Negative Days Selection
- If `monthly_nsfs = "Total"` → Use `request.nsfs_three_months_total`
- If `monthly_nsfs = "Average"` → Use `request.nsfs_three_months_average`

## Lender Matching Algorithm

The system matches merchants to lenders based on:

1. **State Validation** - Must be in `allow_state`
2. **Industry Validation** - Must be in `allow_industry`
3. **Time in Business** - Must meet minimum months
4. **Deposit Count** - Must have minimum number of deposits
5. **Average Deposit** - Must meet minimum average deposit
6. **Daily Balance** - Must meet minimum daily balance
7. **Negative Days** - Must not exceed maximum negative days
8. **NSF Days** - Must not exceed maximum NSF days
9. **Credit Score** - Must meet minimum credit score
10. **Account Positions** - Must be within min/max range

## JSON Field Format

### allow_industry
```json
["Retail", "Food Service", "Transportation", "Healthcare"]
```

### allow_state
```json
["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
```

## Example: Adding a New Lender Programmatically

```python
from app.database import SessionLocal
from app.models.lender import LenderInfo, LenderRequirement
import json

db = SessionLocal()

# Create lender
lender = LenderInfo(
    lender_name="Fast Capital",
    lender_code="FC001",
    grade="A",
    status=1,
    email_1="support@fastcapital.com",
    phone_1="1-800-FAST-NOW",
    Web_link="https://fastcapital.com",
    advance_amount=500000,
    months_3_deposits="Minimum",
    months_3_dollar_deposits="Minimum",
    mos_balances="Minimum"
)
db.add(lender)
db.flush()  # Get the ID

# Create requirement
requirement = LenderRequirement(
    lender_id=lender.id,
    allow_industry=json.dumps(["Retail", "Food Service"]),
    allow_state=json.dumps(["CA", "NY", "TX"]),
    time_in_business=12,
    min_deposit=30,
    min_avg_deposit=5000,
    min_daily_balance=10000,
    min_credit_score=600,
    max_neg_days=5
)
db.add(requirement)
db.commit()
db.close()
```

## State-Specific Requirements

Different states may have varying requirements. You can manage this by:

1. Creating separate requirement records for the same lender with different state lists
2. Filtering by state in the matching algorithm
3. Storing state-specific notes in the `notes` field

## Bank Statement Requirements by State

This will be configured during the **Bank Statement Upload** module setup, where you'll map states to required number of statements (3 vs 4 months).

## Troubleshooting

### CSV Import Fails
- Check encoding is UTF-8
- Ensure headers match exactly
- Verify JSON arrays are properly formatted in CSV (use quotes: `"[...]"`)
- Check for special characters in lender names

### Lender Not Appearing in Results
- Verify `status = 1`
- Check if merchant meets ALL requirements
- Verify `allow_state` and `allow_industry` contain the merchant's values
- Check numeric fields (must be >= minimum requirements)

## Next Steps

1. **Prepare your lender data** in CSV format
2. **Import data** using the API endpoints
3. **Test lender matching** with sample merchant data
4. **Build Bank Statement Parser** to extract merchant data
5. **Create Matching API** for the full lender qualification flow
