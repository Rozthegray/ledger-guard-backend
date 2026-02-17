from sqlalchemy import Column, Integer, String, JSON, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    company_name = Column(String)
    
    plan = Column(String, default="starter") 
    api_key = Column(String, unique=True, index=True)
    settings = Column(JSON, default={}) 

    # 🟢 VERIFICATION & EXPIRY
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String, nullable=True)
    
    # 🟢 NEW: Track when the plan ends
    plan_expires_at = Column(DateTime, nullable=True)

    # Relationships
    # 🟢 FIX: Typo was "relationshsip" -> changed to "relationship"
    subscriptions = relationship("app.models.billing.Subscription", back_populates="user")
    transactions = relationship("app.models.transactions.Transaction", back_populates="user")
    audit_logs = relationship("app.models.audit.AuditLog", back_populates="user")

    @property
    def has_active_plan(self):
        """Returns True if user has a paid plan that hasn't expired"""
        if self.plan == "starter":
            return False
        if self.plan_expires_at and self.plan_expires_at > datetime.utcnow():
            return True
        return False