from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.transactions import Transaction
from app.models.audit import AuditLog 
# Import schemas to ensure data is formatted correctly for the frontend
# (Assuming you have these, otherwise generic dicts will work)

router = APIRouter()

# 🟢 1. GET ALL AUDIT LOGS (This was missing, causing the 404)
@router.get("/audit-logs")
def get_audit_logs(
    skip: int = 0, 
    limit: int = 50, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Fetch list of past audits for the Audit Logs page.
    """
    logs = db.query(AuditLog).filter(
        AuditLog.user_id == current_user.id
    ).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    
    return logs

# 🟢 2. GET DASHBOARD STATS
@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Calculate Date Range (Last 30 Days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # 2. Fetch User's Transactions
    txs = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= thirty_days_ago
    ).all()

    # 3. Calculate Metrics
    total_spend = sum(t.amount for t in txs if t.amount > 0) 
    burn_rate = total_spend  
    
    current_balance = 50000 - total_spend 
    runway_days = int((current_balance / burn_rate) * 30) if burn_rate > 0 else 999

    # 4. Prepare Chart Data
    chart_data = {}
    for t in txs:
        # Format as YYYY-MM-DD for the new Recharts component
        date_str = t.date.strftime("%Y-%m-%d") 
        chart_data[date_str] = chart_data.get(date_str, 0) + t.amount
    
    formatted_chart = [{"date": k, "balance": v} for k, v in chart_data.items()]

    # 5. Get Recent Alerts
    alerts = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.is_anomaly == True
    ).order_by(Transaction.date.desc()).limit(5).all()

    return {
        "metrics": {
            "balance": current_balance, 
            "burn_rate": burn_rate, 
            "runway": runway_days
        }, 
        "chart": formatted_chart, 
        "alerts": alerts
    }

# 🟢 3. GET SINGLE AUDIT LOG
@router.get("/audit-logs/{audit_id}")
def get_single_audit_log(
    audit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    audit = db.query(AuditLog).filter(
        AuditLog.id == audit_id,
        AuditLog.user_id == current_user.id
    ).first()
    
    if not audit:
        raise HTTPException(status_code=404, detail="Audit log not found")
        
    return audit