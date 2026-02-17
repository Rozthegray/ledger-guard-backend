from pydantic import BaseModel

class PlanRequest(BaseModel):
    plan_id: str  # <--- Changed from 'String' to 'str'
    amount: int   # Amount in cents/kobo (e.g. 2900)
    currency: str = "NGN" # <--- Ensure this is also 'str'

class PaystackInitResponse(BaseModel):
    authorization_url: str
    access_code: str
    reference: str