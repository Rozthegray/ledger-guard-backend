from fastapi import APIRouter, UploadFile, File, Form, Depends, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from typing import List
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import check_subscription_tier
from app.models.audit import AuditLog
from app.core.mail import send_notification_email
from datetime import datetime

from app.agents.extractor import text_to_transactions
from app.schemas.transaction import TransactionInput
# Import the shared logic from the file we just fixed
from app.api.endpoints.transactions import run_ai_analysis 

import pdfplumber
import io

router = APIRouter()

async def process_file_background(audit_id: int, file_content: bytes, filename: str, db: Session, email: str):
    print(f"🚀 Starting background process for {filename}")
    try:
        # 1. Extract Text
        text = ""
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        
        # 🟢 CRITICAL FIX: Guard Clause for Empty PDFs
        # If text is empty, it means the PDF is an image scan.
        if len(text.strip()) < 50:
            raise ValueError("No text found. This appears to be a scanned image PDF. OCR is required.")

        # 2. Run Extractor Agent
        print(f"👀 Extractor: Analyzing {len(text)} chars...")
        structured_data = await text_to_transactions(text)
        
        if not structured_data:
             raise ValueError("AI could not find any transactions in the document.")

        # 3. Prepare Inputs
        tx_inputs = [TransactionInput(**item) for item in structured_data]
        
        # 4. Run AI Analysis
        final_report = await run_ai_analysis(tx_inputs)

        # 5. Update Database
        # Re-fetch audit to attach to current session
        audit = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
        if audit:
            audit.status = "completed"
            
            # Convert objects to JSON-safe format
            audit.findings = jsonable_encoder(final_report) 
            
            audit.completed_at = datetime.utcnow()
            
            # Calculate Risk Score
            anomalies = [t for t in final_report if t.is_anomaly]
            audit.risk_score = min(100, len(anomalies) * 20)

            db.commit()
        
        # 6. Email User
        await send_notification_email(email, f"Audit Finished: {filename}")
        print(f"✅ Audit {audit_id} Completed Successfully")

    except Exception as e:
        print(f"❌ Audit {audit_id} Failed: {e}")
        db.rollback() 
        
        audit = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
        if audit:
            audit.status = "failed"
            # Optional: You can save the error message to a 'details' column if you have one
            db.commit()

@router.post("/universal")
async def ingest_anything(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    tier: dict = Depends(check_subscription_tier)
):
    user = tier["user"]
    file = files[0]
    content = await file.read() 

    # 1. Create 'Processing' Log
    audit = AuditLog(user_id=user.id, filename=file.filename, status="processing")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    # 2. Hand off to background task
    background_tasks.add_task(process_file_background, audit.id, content, file.filename, db, user.email)

    return {"status": "processing", "message": "Upload started", "audit_id": audit.id}