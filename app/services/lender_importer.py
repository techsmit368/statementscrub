"""
Service to import and manage lender data
"""
import json
import csv
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.lender import LenderInfo, LenderRequirement


class LenderImporter:
    """Import lender data from CSV or JSON"""

    @staticmethod
    def import_lenders_from_csv(file_path: str, db: Session):
        """Import lenders from CSV file"""
        lenders = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    lender = LenderInfo(
                        lender_name=row.get('lender_name'),
                        lender_code=row.get('lender_code'),
                        email_1=row.get('email_1'),
                        email_2=row.get('email_2'),
                        email_3=row.get('email_3'),
                        email_4=row.get('email_4'),
                        phone_1=row.get('phone_1'),
                        phone_2=row.get('phone_2'),
                        Web_link=row.get('Web_link'),
                        grade=row.get('grade'),
                        default_on_advance=row.get('default_on_advance'),
                        bankruptcy=row.get('bankruptcy'),
                        advance_amount=int(row.get('advance_amount', 0)),
                        consolidation=row.get('consolidation'),
                        months_3_deposits=row.get('3months_deposits'),
                        months_3_dollar_deposits=row.get('3months$deposits'),
                        mos_balances=row.get('mos_balances'),
                        equipfinancing=row.get('equipfinancing'),
                        termloan=row.get('termloan'),
                        line_of_credit=row.get('line_of_credit'),
                        monthly_nsfs=row.get('monthly_nsfs'),
                        monNegativeDays=row.get('monNegativeDays'),
                        itin_filter=row.get('itin_filter'),
                        home_based=row.get('home_based'),
                        status=int(row.get('status', 1)),
                        funding_cutoff_time=row.get('funding_cutoff_time'),
                        contracts_BV_cutoff_time=row.get('contracts_BV_cutoff_time'),
                        bank_product=row.get('bank_product'),
                        notes=row.get('notes'),
                        isorep=row.get('isorep'),
                        website_link=row.get('website_link'),
                    )
                    lenders.append(lender)
                    db.add(lender)

            db.commit()
            return len(lenders), "success"
        except Exception as e:
            db.rollback()
            return 0, str(e)

    @staticmethod
    def import_requirements_from_csv(file_path: str, db: Session):
        """Import lender requirements from CSV file"""
        requirements = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    lender_id = int(row.get('lender_id'))

                    # Parse JSON fields
                    allow_industry = row.get('allow_industry')
                    allow_state = row.get('allow_state')
                    if isinstance(allow_state, str) and allow_state.startswith('['):
                        allow_state = json.loads(allow_state)

                    req = LenderRequirement(
                        lender_id=lender_id,
                        allow_industry=allow_industry,
                        allow_state=allow_state,
                        time_in_business=int(row.get('time_in_business', 0)),
                        min_deposit=int(row.get('min_deposit', 0)),
                        min_avg_deposit=int(row.get('min_avg_deposit', 0)),
                        max_position=int(row.get('max_position', 0)),
                        min_position=int(row.get('min_position', 0)),
                        max_neg_days=int(row.get('max_neg_days', 0)),
                        min_daily_balance=int(row.get('min_daily_balance', 0)),
                        min_trucks=int(row.get('min_trucks', 0)),
                        min_credit_score=int(row.get('min_credit_score', 0)),
                        nsf_days=int(row.get('nsf_days', 0)),
                    )
                    requirements.append(req)
                    db.add(req)

            db.commit()
            return len(requirements), "success"
        except Exception as e:
            db.rollback()
            return 0, str(e)

    @staticmethod
    def import_from_json(lenders_data: List[Dict[str, Any]], requirements_data: List[Dict[str, Any]], db: Session):
        """Import lenders and requirements from JSON data"""
        try:
            lenders = []
            for lender_data in lenders_data:
                lender = LenderInfo(**lender_data)
                db.add(lender)
                lenders.append(lender)

            db.commit()

            # Now add requirements with proper lender IDs
            for i, req_data in enumerate(requirements_data):
                if i < len(lenders):
                    req_data['lender_id'] = lenders[i].id
                    req = LenderRequirement(**req_data)
                    db.add(req)

            db.commit()
            return len(lenders), len(requirements_data), "success"
        except Exception as e:
            db.rollback()
            return 0, 0, str(e)
