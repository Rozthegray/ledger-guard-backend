from celery import Celery
from app.core.database import SessionLocal
from app.models.audit import AuditLog
# Import your EXISTING agents
from app.agents.extractor import text_to_transactions
from app.agents.transactions import analyze_transactions 
import asyncio

celery = Celery(__name__, broker="redis://localhost:6379/0", backend="redis://localhost:6379/0")

@celery.task(name="process_audit")
def process_audit_task(audit_id: int, raw_text: str):
    db = SessionLocal()
    audit = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
    
    try:
        # 1. Update Status
        audit.status = "processing"
        db.commit()

        # 2. Run your AI Agents (Wrap async in sync for Celery)
        # Note: You might need asgiref.sync_to_async if reusing async code directly
        loop = asyncio.get_event_loop()
        transactions = loop.run_until_complete(text_to_transactions(raw_text))
        
        # 3. Analyze
        # (Assuming you refactor analyze_transactions to accept raw list)
        # analysis_result = ... 

        # 4. Save Result
        audit.status = "completed"
        audit.result_summary = {"count": len(transactions), "risk_score": 0.8} # Mock result
        db.commit()
        
        # 5. Trigger Notification (Email/Bell)
        # send_notification(audit.user_id, "Audit Complete")

    except Exception as e:
        audit.status = "failed"
        db.commit()
    finally:
        db.close()