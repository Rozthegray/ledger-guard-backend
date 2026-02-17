from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    plan_name = Column(String) 
    amount = Column(Float) # Changed to Float for easier math if needed
    currency = Column(String, default="NGN")
    
    reference = Column(String, unique=True, index=True) 
    status = Column(String, default="pending") 
    
    # 🟢 NEW: Billing Cycle Dates
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("app.models.user.User", back_populates="subscriptions")