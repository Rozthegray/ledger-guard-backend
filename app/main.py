from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base

# Import Models
from app.models.user import User
from app.models.billing import Subscription
from app.models.transactions import Transaction
from app.models.audit import AuditLog 

# Import Routers
from app.api.endpoints import auth, user, billing, transactions, dashboard, ingest

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 🟢 CORRECT ROUTER REGISTRATION ---

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/user", tags=["User Settings"])
app.include_router(billing.router, prefix="/billing", tags=["Billing"]) 

# Transactions & Ingest
app.include_router(transactions.router, prefix=settings.API_V1_STR, tags=["Transactions"]) 
app.include_router(ingest.router, prefix=f"{settings.API_V1_STR}/ingest", tags=["Ingest"])

# 🟢 DASHBOARD (Fixed: Moved under API V1 to match Frontend)
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["Dashboard"])

@app.get("/")
def health_check():
    return {"status": "operational", "db": "connected"}