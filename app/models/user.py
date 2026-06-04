from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
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
    stripe_customer_id = Column(String, nullable=True)
    telegram_id = Column(String, nullable=True)
    telegram_token = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
