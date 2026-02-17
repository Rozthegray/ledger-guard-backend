import httpx
from datetime import datetime, timedelta # 🟢 Import these
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.billing import Subscription
from app.schemas.billing import PlanRequest

router = APIRouter()

PAYSTACK_SECRET = settings.PAYSTACK_SECRET_KEY
PAYSTACK_URL = "https://api.paystack.co"

@router.post("/paystack/initialize")
async def initialize_payment(
    plan: PlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 🟢 1. CHECK IF ALREADY ACTIVE
    # We use the property we added to the User model
    if current_user.has_active_plan:
        raise HTTPException(
            status_code=400, 
            detail=f"You already have an active {current_user.plan} plan until {current_user.plan_expires_at.date()}"
        )

    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET}",
            "Content-Type": "application/json"
        }
        
        currency = "NGN" # Force NGN for local testing
        
        payload = {
            "email": current_user.email,
            "amount": int(plan.amount),
            "currency": currency,
            "callback_url": "http://localhost:3000/dashboard/billing", 
            "metadata": { "user_id": current_user.id, "plan_id": plan.plan_id }
        }

        try:
            res = await client.post(f"{PAYSTACK_URL}/transaction/initialize", json=payload, headers=headers)
            if res.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Paystack Error: {res.text}")
            
            data = res.json()["data"]

            new_sub = Subscription(
                user_id=current_user.id,
                plan_name=plan.plan_id,
                amount=plan.amount / 100, 
                currency=currency,
                reference=data["reference"],
                status="pending"
            )
            db.add(new_sub)
            db.commit()

            return {"url": data["authorization_url"], "reference": data["reference"]}
            
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail="Connection failed")

@router.get("/paystack/verify/{reference}")
async def verify_payment(
    reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}"}
        res = await client.get(f"{PAYSTACK_URL}/transaction/verify/{reference}", headers=headers)
        
        if res.status_code != 200: 
            raise HTTPException(status_code=400, detail="Verify failed")
        
        data = res.json()["data"]
        sub = db.query(Subscription).filter(Subscription.reference == reference).first()
        
        if not sub: raise HTTPException(status_code=404, detail="Sub not found")

        if data["status"] == "success":
            # 🟢 2. ACTIVATE PLAN & SET DATES
            now = datetime.utcnow()
            expires = now + timedelta(days=30) # 30 Days from now

            # Update Subscription Record
            sub.status = "success"
            sub.start_date = now
            sub.end_date = expires
            
            # Update User Profile
            current_user.plan = sub.plan_name 
            current_user.plan_expires_at = expires
            
            db.commit()
            return {"status": "success", "new_plan": current_user.plan}
        
        sub.status = "failed"
        db.commit()
        return {"status": "failed"}

@router.get("/history")
def get_billing_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).order_by(Subscription.created_at.desc()).all()