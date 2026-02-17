from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

# 1. The Transaction Table (Financial Data)
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) 
    date = Column(Date, nullable=False)
    description = Column(String, index=True)
    vendor = Column(String, index=True)
    amount = Column(Float, nullable=False)
    
    # AI Enrichment Fields
    category = Column(String)
    is_anomaly = Column(Boolean, default=False)
    risk_score = Column(Float, default=0.0)
    audit_note = Column(String)

    # Relationship to User
    user = relationship("app.models.user.User", back_populates="transactions")

