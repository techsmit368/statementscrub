"""
Database initialization script to create tables and seed lender data.
Run: python init_db.py
"""
import json
from app.database import engine, SessionLocal, Base
from app.models.lender import LenderInfo, LenderRequirement

# Create all tables
Base.metadata.create_all(bind=engine)
print("✓ Database tables created successfully")


def seed_sample_data():
    """Add sample lender data for testing"""
    db = SessionLocal()

    try:
        # Check if data already exists
        existing_lenders = db.query(LenderInfo).count()
        if existing_lenders > 0:
            print("✓ Lenders already exist in database. Skipping seed data.")
            return

        # Sample lenders (replace with your actual data)
        sample_lenders = [
            {
                "lender_name": "QuickFund Capital",
                "lender_code": "QFC001",
                "grade": "A",
                "status": 1,
                "email_1": "support@quickfund.com",
                "phone_1": "1-800-QUICK-01",
                "Web_link": "https://quickfund.com",
                "default_on_advance": "No",
                "advance_amount": 500000,
                "months_3_deposits": "Minimum",
                "months_3_dollar_deposits": "Minimum",
                "mos_balances": "Minimum",
                "monthly_nsfs": "Total",
                "monNegativeDays": "Total",
            },
            {
                "lender_name": "MerchantsPlus",
                "lender_code": "MP001",
                "grade": "B",
                "status": 1,
                "email_1": "info@merchantsplus.com",
                "phone_1": "1-888-MERCHANTS",
                "Web_link": "https://merchantsplus.com",
                "default_on_advance": "No",
                "advance_amount": 300000,
                "months_3_deposits": "Minimum",
                "months_3_dollar_deposits": "Actual",
                "mos_balances": "Actual",
                "monthly_nsfs": "Average",
                "monNegativeDays": "Average",
            },
            {
                "lender_name": "SmallBiz Loans",
                "lender_code": "SBL001",
                "grade": "C",
                "status": 1,
                "email_1": "lending@smallbizloans.com",
                "phone_1": "1-855-SMALLBIZ",
                "Web_link": "https://smallbizloans.com",
                "default_on_advance": "Yes",
                "advance_amount": 150000,
                "months_3_deposits": "Actual",
                "months_3_dollar_deposits": "Actual",
                "mos_balances": "Actual",
                "monthly_nsfs": "Total",
                "monNegativeDays": "Total",
            },
        ]

        # Sample requirements for each lender
        sample_requirements = [
            {
                "lender_idx": 0,  # QuickFund Capital
                "allow_industry": json.dumps(["Retail", "Food Service", "Transportation", "Healthcare"]),
                "allow_state": json.dumps(["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]),
                "time_in_business": 12,  # months
                "min_deposit": 30,  # minimum number of deposits
                "min_avg_deposit": 5000,  # $5,000
                "min_position": 1,
                "max_position": 10,
                "max_neg_days": 5,
                "min_daily_balance": 10000,  # $10,000
                "min_credit_score": 600,
                "nsf_days": 3,
            },
            {
                "lender_idx": 1,  # MerchantsPlus
                "allow_industry": json.dumps(["Retail", "Food Service", "E-commerce"]),
                "allow_state": json.dumps(["CA", "NY", "TX", "FL", "IL", "WA", "CO", "AZ"]),
                "time_in_business": 6,
                "min_deposit": 20,
                "min_avg_deposit": 3000,
                "min_position": 1,
                "max_position": 5,
                "max_neg_days": 10,
                "min_daily_balance": 5000,
                "min_credit_score": 550,
                "nsf_days": 5,
            },
            {
                "lender_idx": 2,  # SmallBiz Loans
                "allow_industry": json.dumps(["Retail", "Services", "Transportation"]),
                "allow_state": json.dumps(["CA", "TX", "FL", "NY", "IL", "PA", "OH", "GA", "NC", "MI", "NJ", "VA"]),
                "time_in_business": 3,
                "min_deposit": 10,
                "min_avg_deposit": 1000,
                "min_position": 1,
                "max_position": 3,
                "max_neg_days": 15,
                "min_daily_balance": 2000,
                "min_credit_score": 500,
                "nsf_days": 10,
            },
        ]

        # Add lenders to database
        lenders = []
        for lender_data in sample_lenders:
            lender = LenderInfo(**lender_data)
            db.add(lender)
            lenders.append(lender)

        db.commit()
        print(f"✓ Added {len(lenders)} sample lenders")

        # Add requirements
        for req_data in sample_requirements:
            lender_idx = req_data.pop("lender_idx")
            req_data["lender_id"] = lenders[lender_idx].id
            requirement = LenderRequirement(**req_data)
            db.add(requirement)

        db.commit()
        print(f"✓ Added {len(sample_requirements)} lender requirements")
        print("\n✓ Database initialized successfully!")

    except Exception as e:
        db.rollback()
        print(f"✗ Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing StatementIQ Database...\n")
    seed_sample_data()
