from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.database import Base


class BrokerLenderContact(Base):
    """Per-broker ISO rep contact info overlaid on master lender directory."""
    __tablename__ = "broker_lender_contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lender_id = Column(Integer, ForeignKey("lender_infos.id"), nullable=False, index=True)
    iso_rep_name = Column(String, nullable=True)
    iso_rep_email = Column(String, nullable=True)
    iso_rep_phone = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
