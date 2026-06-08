from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, JSON, ForeignKey, func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, default="")
    is_active = Column(Boolean, default=True)
    plan = Column(String, default="free")  # free, starter, pro
    analyses_used = Column(Integer, default=0)
    credits = Column(Integer, default=0)
    stripe_customer_id = Column(String, nullable=True)
    telegram_id = Column(String, nullable=True)
    telegram_token = Column(String, nullable=True)
    api_key = Column(String, nullable=True, unique=True, index=True)
    created_at = Column(DateTime, server_default=func.now())


class UserScorecard(Base):
    """Custom underwriting thresholds per user (Moneythumb-style custom scorecard)."""
    __tablename__ = "user_scorecards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Thresholds
    max_nsf_count = Column(Integer, default=3)
    max_overdraft_count = Column(Integer, default=3)
    min_avg_daily_balance = Column(Float, default=500.0)
    min_months_coverage = Column(Integer, default=3)
    allow_mca = Column(Boolean, default=False)
    auto_decline_gambling = Column(Boolean, default=False)
    max_risk_score = Column(Integer, default=60)       # decline if risk_score > this
    min_monthly_income = Column(Float, default=2000.0)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
