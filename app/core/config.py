from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ledger Guard"
    API_V1_STR: str = "/api/v1"
    
    # 🟢 AUTH KEY (Keep this hardcoded)
    SECRET_KEY: str = "super-secret-fixed-key-1234567890"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8 
    
    DATABASE_URL: str = "sqlite:///./ledger_guard.db"
    
    # 🟢 PAYSTACK KEY (Paste your sk_test_... key here directly)
    # Go to Paystack Dashboard -> Settings -> API Keys & Webhooks to find it.
    PAYSTACK_SECRET_KEY: str = "sk_test_53ec15c9140b353e0e9acf5bc1e7876b91141aac"
    
    # Optional Keys
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_SERVER: Optional[str] = None
    
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_INDEX_NAME: Optional[str] = None
    REDIS_URL: Optional[str] = None

    class Config:
        case_sensitive = True
        extra = "ignore"

settings = Settings()

# 🟢 DEBUG PRINT: Verify keys on startup
print(f"\n{'='*40}")
print(f"🔑 AUTH KEY:     {settings.SECRET_KEY}")
print(f"💳 PAYSTACK KEY: {settings.PAYSTACK_SECRET_KEY}")
print(f"{'='*40}\n")