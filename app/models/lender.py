from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class LenderInfo(Base):
    __tablename__ = "lender_infos"

    id = Column(Integer, primary_key=True, index=True)
    lender_name = Column(String(255), nullable=True)
    lender_code = Column(String(255), nullable=True)
    email_1 = Column(String(255), nullable=True)
    email_2 = Column(String(255), nullable=True)
    email_3 = Column(String(255), nullable=True)
    email_4 = Column(String(255), nullable=True)
    phone_1 = Column(String(255), nullable=True)
    phone_2 = Column(String(255), nullable=True)
    Web_link = Column(String(255), nullable=True)
    grade = Column(String(255), nullable=True)  # A, B, C, D
    default_on_advance = Column(String(255), nullable=True)
    bankruptcy = Column(String(255), nullable=True)
    advance_amount = Column(Integer, default=0)
    consolidation = Column(String(255), nullable=True)
    months_3_deposits = Column(String(255), nullable=True)  # "Minimum" or actual value
    months_3_dollar_deposits = Column(String(255), nullable=True)
    mos_balances = Column(String(255), nullable=True)  # "Minimum" or actual value
    equipfinancing = Column(String(255), nullable=True)
    termloan = Column(String(255), nullable=True)
    line_of_credit = Column(String(255), nullable=True)
    monthly_nsfs = Column(String(255), nullable=True)  # "Total" or "Average"
    monNegativeDays = Column(String(255), nullable=True)  # "Total" or actual value
    itin_filter = Column(String(125), nullable=True)
    home_based = Column(String(255), nullable=True)
    status = Column(Integer, default=1)  # 1 = active, 0 = inactive
    funding_cutoff_time = Column(String(255), nullable=True)
    contracts_BV_cutoff_time = Column(String(255), nullable=True)
    bank_product = Column(String(125), nullable=True)
    notes = Column(Text, nullable=True)
    isorep = Column(String(125), nullable=True)
    website_link = Column(String(125), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    requirements = relationship("LenderRequirement", back_populates="lender", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LenderInfo(id={self.id}, name={self.lender_name}, grade={self.grade})>"


class LenderRequirement(Base):
    __tablename__ = "lender_requirements"

    id = Column(Integer, primary_key=True, index=True)
    lender_id = Column(Integer, ForeignKey("lender_infos.id", ondelete="CASCADE"), nullable=False)
    allow_industry = Column(Text, nullable=True)  # JSON array of industries
    allow_state = Column(JSON, nullable=True)  # JSON array of states
    time_in_business = Column(Integer, default=0)  # months
    min_deposit = Column(Integer, default=0)  # minimum number of deposits
    min_avg_deposit = Column(Integer, default=0)  # minimum average deposit amount
    max_position = Column(Integer, default=0)  # maximum accounts/positions
    min_position = Column(Integer, default=0)  # minimum accounts/positions
    max_neg_days = Column(Integer, default=0)  # maximum negative/NSF days
    min_daily_balance = Column(Integer, default=0)  # minimum daily balance
    min_trucks = Column(Integer, default=0)  # minimum vehicles (for transport businesses)
    min_credit_score = Column(Integer, default=0)  # minimum credit score
    nsf_days = Column(Integer, default=0)  # NSF/negative days limit
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lender = relationship("LenderInfo", back_populates="requirements")

    def __repr__(self):
        return f"<LenderRequirement(id={self.id}, lender_id={self.lender_id})>"
