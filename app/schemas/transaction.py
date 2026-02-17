from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
import dateparser # Ensure you pip installed this

class TransactionInput(BaseModel):
    date: datetime  # The target type is datetime
    description: str
    amount: float
    vendor: Optional[str] = None

    # 🟢 FIX: This Validator runs BEFORE standard validation
    @field_validator("date", mode="before")
    def parse_flexible_date(cls, value):
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            # Clean string and parse
            parsed = dateparser.parse(value.strip())
            if parsed:
                return parsed
            
        raise ValueError(f"Could not parse date: {value}")

class TransactionOutput(BaseModel):
    date: datetime
    description: str
    amount: float
    vendor: Optional[str] = None
    category: str
    category_source: str = "Unknown"
    category_confidence: float = 0.0
    is_anomaly: bool = False
    risk_score: float = 0.0
    audit_reason: str = "None"