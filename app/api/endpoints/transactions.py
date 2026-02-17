from fastapi import APIRouter, Depends, BackgroundTasks
from typing import List
import asyncio
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.audit import AuditLog 
from app.schemas.transaction import TransactionInput, TransactionOutput
from app.core.mail import send_notification_email
from app.agents.normalizer import normalize_transaction
from app.agents.auditor import audit_transaction
import pandas as pd

# Mock History
MOCK_HISTORY_DF = pd.DataFrame([
    {"vendor": "AWS", "amount": 50.00},
    {"vendor": "Netflix", "amount": 15.00},
])

router = APIRouter()
SEM = asyncio.Semaphore(3)

# 🟢 CONFIG: Phrases that indicate a summary line, not a real transaction
IGNORE_PHRASES = [
    "Total Money In", 
    "Total Money Out", 
    "Opening Balance", 
    "Closing Balance",
    "Statement Period",
    "Page 1 of",
    "Brought Forward"
]

async def process_single_transaction(txn: TransactionInput) -> TransactionOutput:
    async with SEM:
        try:
            # Normalize Description
            category_data = await normalize_transaction(txn.description)
            
            if isinstance(category_data, dict):
                category = category_data.get("category", "Uncategorized")
                source = category_data.get("source", "Unknown")
                confidence = category_data.get("confidence", 0.0)
            else:
                category = str(category_data)
                source = "Legacy System"
                confidence = 1.0
        except Exception as e:
            print(f"⚠️ AI Error for '{txn.description}': {e}")
            category = "System Error"
            source = "Fallback"
            confidence = 0.0

    # Auditor Logic
    audit_result = audit_transaction(
        current_amount=txn.amount, 
        vendor=txn.vendor if txn.vendor else "Unknown", 
        history_df=MOCK_HISTORY_DF
    )

    return TransactionOutput(
        date=txn.date,
        description=txn.description,
        amount=txn.amount,
        vendor=txn.vendor,
        category=category,
        category_source=source,
        category_confidence=confidence,
        is_anomaly=(audit_result.get("status") == "ALERT"),
        risk_score=audit_result.get("risk_score", 0.0),
        audit_reason=audit_result.get("note", "None")
    )

async def run_ai_analysis(transactions: List[TransactionInput]) -> List[TransactionOutput]:
    tasks = [process_single_transaction(txn) for txn in transactions]
    results = await asyncio.gather(*tasks)
    return results

@router.post("/analyze", response_model=List[TransactionOutput])
async def analyze_transactions(
    transactions: List[TransactionInput],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 🟢 1. CLEANING STEP: Remove summary lines to prevent double counting
    clean_transactions = [
        t for t in transactions 
        if not any(phrase.lower() in t.description.lower() for phrase in IGNORE_PHRASES)
    ]

    print(f"🚀 Processing {len(clean_transactions)} valid items for {current_user.email} (filtered out {len(transactions) - len(clean_transactions)} summaries)...")
    
    # 🟢 2. Analyze only the clean data
    results = await run_ai_analysis(clean_transactions)
    
    # Log the activity
    log_entry = AuditLog(
        user_id=current_user.id,
        filename="Manual Analysis",
        status="completed",
        details=f"Processed batch of {len(clean_transactions)} transactions.",
    )
    db.add(log_entry)
    db.commit()

    # Send Notification
    background_tasks.add_task(
        send_notification_email, 
        current_user.email, 
        f"Financial Analysis ({len(clean_transactions)} items)"
    )
    
    return results