class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan_id = Column(String) # "plan_growth", "plan_enterprise"
    status = Column(String, default="active") # active, past_due
    paystack_customer_code = Column(String)
    paystack_auth_code = Column(String) # For recurring charges
    next_billing_date = Column(DateTime)
    user = relationship("User", back_populates="subscription")