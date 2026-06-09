from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from app.database import Base


class Organization(Base):
    """A company/ISO shop account with multiple broker seats."""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan = Column(String, default="starter_team")  # starter_team, business_team, enterprise
    seats_limit = Column(Integer, default=3)
    reports_monthly = Column(Integer, default=150)   # credits added per renewal
    reports_pool = Column(Integer, default=0)         # current available credits
    stripe_subscription_id = Column(String, nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class OrganizationMember(Base):
    """Maps users to an organization with a role."""
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)   # null until invite accepted
    role = Column(String, default="broker")                             # partner, admin, broker
    invited_email = Column(String, nullable=False)
    invite_token = Column(String, nullable=True, unique=True)
    accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
