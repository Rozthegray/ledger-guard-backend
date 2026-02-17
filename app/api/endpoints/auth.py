import random
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.database import get_db

# 🟢 FIX: Split the imports. 
# get_current_user now comes from deps, while the token/password functions stay in security.
from app.core.security import create_access_token, get_password_hash, verify_password
from app.api.deps import get_current_user

from app.models.user import User
from app.schemas.auth import UserCreate, Token
from app.core.mail import send_verification_email

router = APIRouter()

class VerifyRequest(BaseModel):
    code: str

@router.post("/signup", response_model=Token)
async def signup(
    user_in: UserCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # 🟢 FIX: Force Lowercase
    email = user_in.email.lower()

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    code = str(random.randint(100000, 999999))

    new_user = User(
        email=email, 
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        company_name=user_in.company_name,
        is_verified=False,
        verification_code=code
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    background_tasks.add_task(send_verification_email, new_user.email, code)
    
    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/verify-email")
def verify_email(
    req: VerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.is_verified:
        return {"msg": "Already verified"}

    if current_user.verification_code != req.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    current_user.is_verified = True
    current_user.verification_code = None 
    db.commit()
    return {"msg": "Verified"}

@router.post("/resend-code")
async def resend_code(
    user_email: str, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # 🟢 FIX: Lowercase search
    user = db.query(User).filter(User.email == user_email.lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_code = str(random.randint(100000, 999999))
    user.verification_code = new_code
    db.commit()

    background_tasks.add_task(send_verification_email, user.email, new_code)
    return {"msg": "Code resent"}

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 🟢 FIX: Lowercase email
    email = form_data.username.lower()

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}